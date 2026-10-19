"""Run on Raspberry Pi OS: python3 pi_camera.py --server http://PC_IP:5001"""
import argparse
import time
import urllib.request
import urllib.error
import cv2
from picamera2 import Picamera2


def main():
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
    print('Sending camera to', endpoint, '(Ctrl+C to stop)', flush=True)
    try:
        while True:
            started = time.monotonic()
            # Picamera2 RGB888 arrays have BGR byte order, as required by OpenCV.
            image = camera.capture_array('main')
            ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            request = urllib.request.Request(endpoint, data=encoded.tobytes(),
                headers={'Content-Type': 'image/jpeg'}, method='POST')
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
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
