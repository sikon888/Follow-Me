"""Run Pi pose inference in an isolated Python, leaving Picamera2 on OS Python.

The Pi 4 uses Python 3.12 + MediaPipe 0.10.18; newer ARM wheels require AES.
Frames cross a local pipe as BGR bytes. stdout is reserved for JSON replies.
"""
import json
from pathlib import Path
import subprocess
import sys


class PoseWorker:
    def __init__(self, python, model):
        self.process = subprocess.Popen(
            [str(python), '-u', str(Path(__file__).resolve()), str(model)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            if self._reply().get('ready') is not True:
                raise RuntimeError('Pi pose worker failed to initialize')
        except Exception:
            self.close()
            raise

    def _reply(self):
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Pi pose worker stopped; check model and Python dependencies')
        result = json.loads(line)
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result

    def detect(self, image, timestamp_ms):
        import numpy as np
        image = np.ascontiguousarray(image)
        header = json.dumps(dict(shape=list(image.shape), timestamp_ms=timestamp_ms)).encode() + b'\n'
        try:
            self.process.stdin.write(header)
            self.process.stdin.write(image.tobytes())
            self.process.stdin.flush()
            return np.asarray(self._reply()['skeleton'], dtype=np.float32)
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError('Pi pose worker pipe failed') from exc

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


def serve(model):
    import numpy as np
    # Both the downloaded folder and installed layout contain the adapter.
    base = Path(__file__).resolve().parent
    sys.path.insert(0, str(base))
    from modules.pose_processor import PoseDetector
    detector = PoseDetector(image_mode=False, model_path=model)
    print(json.dumps({'ready': True}), flush=True)
    try:
        while line := sys.stdin.buffer.readline():
            try:
                header = json.loads(line)
                height, width, channels = header['shape']
                if not (0 < height <= 1920 and 0 < width <= 1920 and channels == 3):
                    raise ValueError('Invalid worker image dimensions')
                size = height * width * channels
                data = sys.stdin.buffer.read(size)
                if len(data) != size:
                    break
                image = np.frombuffer(data, np.uint8).reshape(height, width, channels)
                pose = detector.detect(image, header['timestamp_ms'])
                print(json.dumps({'skeleton': pose.tolist()}, allow_nan=False), flush=True)
            except Exception as exc:
                print(json.dumps({'error': str(exc)}), flush=True)
                break
    finally:
        detector.close()


if __name__ == '__main__':
    serve(sys.argv[1])
