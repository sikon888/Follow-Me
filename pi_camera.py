"""Run on Raspberry Pi OS: python3 pi_camera.py --server http://PC_IP:5001"""
import argparse
import json
import math
import time
import urllib.request
import urllib.error
import cv2


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
    from picamera2 import Picamera2
    parser = argparse.ArgumentParser(description='Send Pi Camera frames to the dance game')
    parser.add_argument('--server', required=True, help='Example: http://192.168.1.20:5001')
    parser.add_argument('--fps', type=float, default=8)
    args = parser.parse_args()
    if not 0 < args.fps <= 30:
        parser.error('--fps must be between 0 and 30')
    camera = Picamera2()
    camera.configure(camera.create_video_configuration(
        main={'size': (640, 480), 'format': 'RGB888'}, buffer_count=2))
    camera.start()
    endpoint = args.server.rstrip('/') + '/api/camera/frame'
    offset = None
    synced_at = 0
    print('Sending camera to', endpoint, '(Ctrl+C to stop)', flush=True)
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
            ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            request = urllib.request.Request(endpoint, data=encoded.tobytes(),
                headers={'Content-Type': 'image/jpeg',
                         'X-Captured-At': str(captured + offset),
                         'X-Clock-Id': clock_id, 'X-Timing-Source': source,
                         'X-Clock-Uncertainty': str(uncertainty)}, method='POST')
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
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


if __name__ == '__main__':
    main()
