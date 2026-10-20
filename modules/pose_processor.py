"""MediaPipe Tasks adapter. Public skeletons use COCO-17 pixel x,y,confidence."""
from pathlib import Path
import os
import cv2
import numpy as np

COCO_FROM_MEDIAPIPE = (0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)
LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP = 5, 6, 11, 12
CONF_THRESHOLD = 0.3
MODEL_PATH = Path(os.environ.get("MEDIAPIPE_POSE_MODEL", str(Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_full.task")))


def landmarks_to_coco(landmarks, width, height):
    output = np.zeros((17, 3), dtype=np.float32)
    if not landmarks:
        return output
    for i, source in enumerate(COCO_FROM_MEDIAPIPE):
        point = landmarks[source]
        confidence = min(point.visibility or 0.0, point.presence or 0.0)
        values = (point.x * width, point.y * height, confidence)
        if np.isfinite(values).all():
            output[i] = (*values[:2], np.clip(confidence, 0, 1))
    return output


class PoseDetector:
    def __init__(self, image_mode=False, max_dimension=640):
        self.image_mode = image_mode
        self.max_dimension = max_dimension
        if not MODEL_PATH.is_file():
            raise RuntimeError(f"MediaPipe model missing: {MODEL_PATH}. See README.md")
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt before using MediaPipe") from exc
        self.mp = mp
        self.task = mp.tasks.vision.PoseLandmarker.create_from_options(
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
                running_mode=(mp.tasks.vision.RunningMode.IMAGE if image_mode else mp.tasks.vision.RunningMode.VIDEO), num_poses=1,
                min_pose_detection_confidence=0.5, min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5))
        self.last_timestamp = -1

    def detect(self, frame, timestamp_ms):
        height, width = frame.shape[:2]
        if self.max_dimension and max(height, width) > self.max_dimension:
            ratio = self.max_dimension / max(height, width)
            frame = cv2.resize(frame, (round(width * ratio), round(height * ratio)))
        timestamp_ms = max(self.last_timestamp + 1, int(round(timestamp_ms)))
        self.last_timestamp = timestamp_ms
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = self.task.detect(image) if self.image_mode else self.task.detect_for_video(image, timestamp_ms)
        return landmarks_to_coco(result.pose_landmarks[0] if result.pose_landmarks else None,
                                 width, height)

    def close(self):
        self.task.close()


def extract_skeleton(video_path, return_timestamps=False, target_fps=None, progress_callback=None):
    capture = cv2.VideoCapture(str(video_path))
    detector = None
    frames, times = [], []
    decoded = 0
    previous_timestamp = None
    try:
        if not capture.isOpened():
            raise ValueError("Cannot open video")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError("Video has no valid FPS")
        # Independent full-resolution detections avoid temporal smoothing lag
        # in the saved reference, at the cost of a slower build.
        detector = PoseDetector(image_mode=True, max_dimension=None)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            # Decoder presentation timestamps retain VFR timing. Fall back only
            # when the backend does not supply increasing timestamps.
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if not np.isfinite(timestamp) or timestamp < 0 or (previous_timestamp is not None and timestamp <= previous_timestamp):
                timestamp = previous_timestamp + 1 / fps if previous_timestamp is not None else 0.0
            previous_timestamp = timestamp
            decoded += 1
            if progress_callback:
                progress_callback(decoded, count)
            if target_fps and times and timestamp - times[-1] < 1 / target_fps - 1e-6:
                continue
            times.append(timestamp)
            frames.append(detector.detect(frame, timestamp * 1000))
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if count > 0 and decoded < int(count):
            raise ValueError("Video decoding ended early; reference was not saved")
        if not frames:
            raise ValueError("Video has no decoded frames")
    finally:
        capture.release()
        if detector is not None:
            detector.close()
    data = np.asarray(frames, dtype=np.float32)
    return (data, np.asarray(times, dtype=np.float64)) if return_timestamps else data


def shoulder_scale(data):
    valid = (data[:, 5, 2] >= CONF_THRESHOLD) & (data[:, 6, 2] >= CONF_THRESHOLD)
    widths = np.linalg.norm(data[:, 5, :2] - data[:, 6, :2], axis=1)
    widths = widths[valid & np.isfinite(widths) & (widths > 1)]
    if not len(widths):
        raise ValueError("Cannot find valid shoulder width")
    return float(np.median(widths))


def normalize_skeleton(data, body_scale=None):
    data = np.asarray(data, dtype=np.float32)
    if data.ndim != 3 or data.shape[1:] != (17, 3):
        raise ValueError("Expected (frames, 17, 3)")
    scale = shoulder_scale(data) if body_scale is None else body_scale
    if not np.isfinite(scale) or scale <= 1:
        raise ValueError("Invalid pixel shoulder scale")
    normalized = np.zeros_like(data)
    for i, frame in enumerate(data):
        if min(frame[11, 2], frame[12, 2]) < CONF_THRESHOLD:
            continue
        valid = (frame[:, 2] >= CONF_THRESHOLD) & np.isfinite(frame).all(axis=1)
        normalized[i, valid, :2] = (frame[valid, :2] - (frame[11, :2] + frame[12, :2]) / 2) / scale
        normalized[i, valid, 2] = frame[valid, 2]
    return normalized
