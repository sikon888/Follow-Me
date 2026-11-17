"""Run on Raspberry Pi OS: python3 pi_camera.py --server http://PC_IP:5001"""
import argparse
import json
import math
import time
import urllib.request
import urllib.error
import cv2
from pathlib import Path


def synchronize_clock(server, attempts=3):
    """Map the Pi monotonic clock to the server using the lowest-RTT sample."""
    best = None
    for _ in range(attempts):
        before = time.monotonic()
        with urllib.request.urlopen(server.rstrip('/') + '/api/camera/clock', timeout=3) as response:
            result = json.load(response)
        after = time.monotonic()
        server_time = float(result['server_time'])
        if not math.isfinite(server_time):
            raise ValueError('Invalid server clock')
        sample = (after - before, server_time - (before + after) / 2, result['clock_id'])
        if best is None or sample[0] < best[0]:
            best = sample
    if best[0] > 0.5:
        raise ValueError('Camera clock sync is too slow; retrying')
    return best[1], best[2], best[0] / 2


def capture_timestamp(metadata, fallback):
    """Use the same request's sensor readout time, adjusted to mid-exposure."""
    try:
        captured = float(metadata['SensorTimestamp']) / 1e9 - float(metadata.get('ExposureTime', 0)) / 2e6
        if not math.isfinite(captured) or not 0 <= fallback - captured < 3:
            raise ValueError
        return captured, 'sensor'
    except (KeyError, ValueError, TypeError):
        return fallback, 'estimated'


def main():
    parser = argparse.ArgumentParser(description='Detect poses on the Pi and send paired camera frames to the game')
    parser.add_argument('--server', required=True, help='Example: http://192.168.1.20:5001')
    parser.add_argument('--fps', type=float, default=24)
    parser.add_argument('--size', choices=['320x240', '480x360', '640x480'], default='480x360')
    parser.add_argument('--check', action='store_true', help='Check server and capture one frame, then exit')
    parser.add_argument('--camera-only', action='store_true', help='Legacy mode: let the PC detect poses')
    parser.add_argument('--model', default=str(Path(__file__).resolve().parent / 'models' / 'pose_landmarker_lite.task'))
    parser.add_argument('--pose-python', default=str(Path(__file__).resolve().parent / '.pose-venv' / 'bin' / 'python'),
                        help='Isolated MediaPipe Python executable (Pi 4: Python 3.12)')
    args = parser.parse_args()
    width, height = map(int, args.size.split('x'))
    if not 0 < args.fps <= 30:
        parser.error('--fps must be between 0 and 30')
    detector = None
    if not args.camera_only:
        from pose_worker import PoseWorker
        detector = PoseWorker(args.pose_python, args.model)
        print('Pose detection: Pi (MediaPipe VIDEO tracking)', flush=True)
    from picamera2 import Picamera2
    if args.check:
        offset, clock_id, uncertainty = synchronize_clock(args.server)
        print(f'Server reachable; clock uncertainty {uncertainty:.3f}s', flush=True)
    camera = Picamera2()
    # Keep the widest field of view even when transmitting a small image.
    modes = camera.sensor_modes
    mode = min(modes, key=lambda m: (-m['crop_limits'][2] * m['crop_limits'][3],
                                    m['size'][0] * m['size'][1], -m['bit_depth']))
    camera.configure(camera.create_video_configuration(
        sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
        main={'size': (width, height), 'format': 'RGB888'}, buffer_count=2,
        controls={'FrameRate': args.fps}, queue=False))
    camera.start()
    endpoint = args.server.rstrip('/') + '/api/camera/frame'
    offset = None
    synced_at = 0
    print('Sending camera to', endpoint, '(Ctrl+C to stop)', flush=True)
    frames_sent = 0
    report_at = time.monotonic()
    inference_total = 0.0
    try:
        while True:
            started = time.monotonic()
            try:
                if offset is None or started - synced_at >= 30:
                    offset, clock_id, uncertainty = synchronize_clock(args.server)
                    synced_at = time.monotonic()
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
                print('Clock sync failed; retrying:', error, flush=True)
                offset = None
                time.sleep(1)
                continue
            # Picamera2 RGB888 arrays have BGR byte order, as required by OpenCV.
            camera_request = camera.capture_request()
            try:
                image = camera_request.make_array('main')
                captured, source = capture_timestamp(camera_request.get_metadata(), time.monotonic())
            finally:
                camera_request.release()
            image = cv2.rotate(image, cv2.ROTATE_180)
            pose = None
            if detector is not None:
                inference_started = time.monotonic()
                pose = detector.detect(image, captured * 1000)
                inference_total += time.monotonic() - inference_started
            ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                if args.check:
                    raise RuntimeError('Camera JPEG encoding failed')
                continue
            headers = {'Content-Type': 'image/jpeg',
                         'X-Captured-At': str(captured + offset),
                         'X-Clock-Id': clock_id, 'X-Timing-Source': source,
                         'X-Clock-Uncertainty': str(uncertainty)}
            if pose is not None:
                headers['X-Pose-Skeleton'] = json.dumps(pose.round(4).tolist(), separators=(',', ':'), allow_nan=False)
            request = urllib.request.Request(endpoint, data=encoded.tobytes(), headers=headers, method='POST')
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    response.read()
                if args.check:
                    print(f'Camera capture, {"Pi pose detection, " if detector else ""}and upload OK ({args.size}).', flush=True)
                    return
                frames_sent += 1
                elapsed = time.monotonic() - report_at
                if elapsed >= 10:
                    print(f'Sent {frames_sent / elapsed:.1f} FPS; inference {inference_total / frames_sent * 1000:.0f} ms/frame', flush=True)
                    frames_sent, inference_total, report_at = 0, 0.0, time.monotonic()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if args.check:
                    raise
                if isinstance(error, urllib.error.HTTPError) and error.code == 409:
                    offset = None
                print('Disconnected; retrying:', error, flush=True)
                time.sleep(1)
            time.sleep(max(0, 1 / args.fps - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        camera.close()
        if detector is not None:
            detector.close()


if __name__ == '__main__':
    main()
