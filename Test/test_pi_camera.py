import io
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from app import app
from routes import pi_routes


class PiCameraTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        pi_routes._frame = None
        pi_routes._sequence = 0
        self.jpeg = cv2.imencode('.jpg', np.zeros((480, 640, 3), np.uint8))[1].tobytes()

    def tearDown(self):
        pi_routes._frame = None

    def test_connect_frame_and_timeout(self):
        self.assertFalse(self.client.get('/api/camera/status').json['connected'])
        self.assertEqual(self.client.get('/api/camera/frame').status_code, 503)
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            self.assertEqual(self.client.post('/api/camera/frame', data=self.jpeg).status_code, 200)
            self.assertTrue(self.client.get('/api/camera/status').json['connected'])
            result = self.client.get('/api/camera/frame')
            self.assertEqual(result.data, self.jpeg)
            self.assertEqual(result.headers['X-Frame-Id'], '1')
        with patch('routes.pi_routes.time.monotonic', return_value=14):
            self.assertFalse(self.client.get('/api/camera/status').json['connected'])
            self.assertEqual(self.client.get('/api/camera/frame').status_code, 503)

    def test_invalid_frames_do_not_connect(self):
        self.assertEqual(self.client.post('/api/camera/frame', data=b'broken').status_code, 400)
        self.assertEqual(self.client.post('/api/camera/frame', data=b'x' * 2_000_001).status_code, 413)
        self.assertFalse(self.client.get('/api/camera/status').json['connected'])

    def test_pi_image_pose_and_scoring_response(self):
        reference = np.zeros((1, 17, 3), np.float32)
        reference[:, :, 2] = 1
        raw = np.zeros((17, 3), np.float32)
        raw[:, 2] = 1
        raw[5, :2], raw[6, :2] = (100, 100), (200, 100)
        raw[11, :2], raw[12, :2] = (120, 200), (180, 200)
        with patch('routes.player_routes.load_reference', return_value=(reference, np.array([0.]))), \
                patch('routes.player_routes.PoseDetector') as detector:
            detector.return_value.detect.return_value = raw
            result = self.client.post('/api/player/test.mp4', data={
                'time': '0', 'frame': (io.BytesIO(self.jpeg), 'pi.jpg')})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['skeleton'], raw.tolist())
        self.assertEqual(result.json['width'], 640)
        self.assertTrue(result.json['detected'])
        self.assertIsInstance(result.json['accuracy'], float)


if __name__ == '__main__':
    unittest.main()
