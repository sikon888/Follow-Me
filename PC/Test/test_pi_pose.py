import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from app import app
from routes import pi_routes
from collections import OrderedDict


class PiPoseTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.state = patch.multiple(pi_routes, _frame=None, _sequence=0, _pose=None,
                                    _pose_frames=OrderedDict(), _captured_at=0.)
        self.state.start()
        self.addCleanup(self.state.stop)
        self.clock = patch('routes.pi_routes.time.monotonic', return_value=10.)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.jpeg = cv2.imencode('.jpg', np.zeros((360, 480, 3), np.uint8))[1].tobytes()
        self.pose = np.zeros((17, 3), np.float32)
        self.pose[:, 2] = 1
        self.pose[5, :2], self.pose[6, :2] = (100, 100), (200, 100)
        self.pose[11, :2], self.pose[12, :2] = (120, 200), (180, 200)

    def upload(self, pose=None):
        return self.client.post('/api/camera/frame', data=self.jpeg, headers={
            'X-Pose-Skeleton': json.dumps(self.pose.tolist() if pose is None else pose),
            'X-Captured-At': '9.9', 'X-Clock-Id': pi_routes.CLOCK_ID})

    def score(self, **overrides):
        payload = dict(time=0, frame_id=1, clock_id=pi_routes.CLOCK_ID)
        payload.update(overrides)
        with patch('routes.player_routes.load_reference', return_value=(self.pose[None], np.array([0.]))), \
                patch('routes.player_routes.PoseDetector') as detector:
            result = self.client.post('/api/player/test.mp4', json=payload)
            detector.assert_not_called()
        return result

    def test_exact_frame_is_scored_without_pc_inference(self):
        self.assertEqual(self.upload().status_code, 200)
        frame = self.client.get('/api/camera/frame')
        self.assertEqual(frame.headers['X-Pose-Backend'], 'pi')
        self.assertEqual(frame.headers['X-Clock-Id'], pi_routes.CLOCK_ID)
        self.assertEqual(self.upload(np.zeros((17, 3)).tolist()).status_code, 200)
        result = self.score()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['skeleton'], self.pose.tolist())
        self.assertEqual((result.json['width'], result.json['height']), (480, 360))

    def test_missing_pose_is_valid_and_does_not_invoke_pc(self):
        self.upload(np.zeros((17, 3)).tolist())
        result = self.score()
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json['detected'])

    def test_bad_skeleton_does_not_replace_valid_frame(self):
        self.upload()
        for invalid in ([[1, 2, 1]], [[0, 0, 2]] * 17, [[float('nan'), 0, 1]] * 17):
            self.assertEqual(self.upload(invalid).status_code, 400)
        self.assertEqual(pi_routes._sequence, 1)

    def test_unknown_stale_and_previous_server_frames_rejected(self):
        self.upload()
        self.assertEqual(self.score(frame_id=99).status_code, 400)
        self.assertEqual(self.score(clock_id='old-server').status_code, 400)
        with patch('routes.pi_routes.time.monotonic', return_value=13):
            self.assertEqual(self.score().status_code, 400)

    def test_camera_only_sender_clears_pi_mode(self):
        self.upload()
        self.client.post('/api/camera/frame', data=self.jpeg)
        self.assertEqual(self.client.get('/api/camera/frame').headers['X-Pose-Backend'], 'pc')

    def test_invalid_json_does_not_crash(self):
        for payload in (None, [], {'time': None}, {'time': 0, 'frame_id': [], 'clock_id': 'x'}):
            response = self.client.post('/api/player/test.mp4', data=json.dumps(payload),
                                        content_type='application/json')
            self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
