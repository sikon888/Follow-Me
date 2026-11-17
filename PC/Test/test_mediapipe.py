import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from modules.pose_processor import landmarks_to_coco, COCO_FROM_MEDIAPIPE, normalize_skeleton
from modules.mirror import mirror_skeleton
from modules.scoring import compare_pose, frame_at


class PoseTests(unittest.TestCase):
    def test_mapping_and_units(self):
        points = [SimpleNamespace(x=i/100, y=i/200, visibility=.9, presence=.7) for i in range(33)]
        result = landmarks_to_coco(points, 800, 600)
        np.testing.assert_allclose(result[:, 0], np.array(COCO_FROM_MEDIAPIPE)*8)
        np.testing.assert_allclose(result[:, 1], np.array(COCO_FROM_MEDIAPIPE)*3)
        np.testing.assert_allclose(result[:, 2], .7)
        self.assertEqual(result.dtype, np.float32)
        self.assertFalse(landmarks_to_coco(None, 800, 600).any())

    def test_normalization_mirror_and_missing(self):
        pose = np.zeros((17, 3), np.float32)
        pose[:, 2] = .9
        pose[5, :2] = (100, 100)
        pose[6, :2] = (200, 100)
        pose[11, :2] = (120, 200)
        pose[12, :2] = (180, 200)
        data = np.array([pose, np.zeros_like(pose), pose])
        normalized = normalize_skeleton(data)
        self.assertEqual(normalized.shape, (3, 17, 3))
        self.assertFalse(normalized[1].any())
        np.testing.assert_allclose(normalized[0, 5, :2], [-.5, -1])
        np.testing.assert_array_equal(mirror_skeleton(mirror_skeleton(normalized[0])), normalized[0])
        self.assertEqual(compare_pose(normalized[0], normalized[0]), 100)
        self.assertEqual(compare_pose(normalized[0], normalized[1]), 0)
        self.assertIsNone(compare_pose(normalized[1], normalized[0]))

    def test_timeline(self):
        times = np.array([0, .033, .08, .12])
        self.assertEqual(frame_at(times, .09), 2)
        self.assertEqual(frame_at(times, 0), 0)
        self.assertEqual(frame_at(times, 10), 3)

    def test_extraction_keeps_empty_frames(self):
        from modules.pose_processor import extract_skeleton
        import cv2
        class Capture:
            index = 0
            released = False
            def isOpened(self): return True
            def read(self):
                self.index += 1
                return (True, np.zeros((20, 30, 3), np.uint8)) if self.index <= 3 else (False, None)
            def get(self, prop):
                if prop == cv2.CAP_PROP_FPS: return 25
                if prop == cv2.CAP_PROP_FRAME_COUNT: return 3
                return (self.index - 1) * 40
            def release(self): self.released = True
        capture = Capture()
        with patch('modules.pose_processor.cv2.VideoCapture', return_value=capture), patch('modules.pose_processor.PoseDetector') as detector:
            detector.return_value.detect.side_effect = [np.ones((17, 3)), np.zeros((17, 3)), np.ones((17, 3))]
            data, times = extract_skeleton('fake.mp4', return_timestamps=True)
            self.assertEqual(len(data), 3)
            self.assertFalse(data[1].any())
            np.testing.assert_allclose(times, [0, .04, .08])
            self.assertTrue(capture.released)
            detector.return_value.close.assert_called_once()

    def test_flask_legacy_reference_rejected(self):
        from app import app
        client = app.test_client()
        self.assertEqual(client.get('/').status_code, 200)
        # Readiness must not depend on which local videos have been rebuilt.
        with patch('routes.game_routes.get_video_path') as video, \
                patch('routes.game_routes.reference_exists', return_value=False):
            video.return_value.is_file.return_value = True
            self.assertEqual(client.get('/play/legacy.mp4').status_code, 400)
            video.return_value.is_file.return_value = False
            self.assertEqual(client.get('/play/missing.mp4').status_code, 404)
        self.assertEqual(client.post('/api/player/unknown.mp4', data={'time': 'nan'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
