import io
import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from app import app
from routes import pi_routes
from pi_camera import synchronize_clock, capture_timestamp


class CaptureTimingTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.state = patch.multiple(pi_routes, _frame=None, _sequence=0,
                                    _captured_at=0., _timing_source='received')
        self.state.start()
        self.addCleanup(self.state.stop)
        self.jpeg = cv2.imencode('.jpg', np.zeros((20, 30, 3), np.uint8))[1].tobytes()

    def headers(self, captured=9.8):
        return {'X-Captured-At': str(captured), 'X-Clock-Id': pi_routes.CLOCK_ID,
                'X-Timing-Source': 'sensor', 'X-Clock-Uncertainty': '0.01'}

    def test_clock_endpoint(self):
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            result = self.client.get('/api/camera/clock')
        self.assertEqual(result.json, {'server_time': 10, 'clock_id': pi_routes.CLOCK_ID})

    def test_timestamp_survives_upload_and_fetch(self):
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            self.assertEqual(self.client.post('/api/camera/frame', data=self.jpeg,
                                             headers=self.headers()).status_code, 200)
        with patch('routes.pi_routes.time.monotonic', return_value=10.4):
            result = self.client.get('/api/camera/frame')
        self.assertEqual(float(result.headers['X-Captured-At']), 9.8)
        self.assertEqual(float(result.headers['X-Server-Time']), 10.4)
        self.assertEqual(result.headers['X-Timing-Source'], 'sensor')

    def test_stale_future_and_invalid_timestamps_rejected(self):
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            for timestamp, status in [(6, 409), (11, 409), ('nan', 400), ('inf', 400)]:
                result = self.client.post('/api/camera/frame', data=self.jpeg,
                                          headers=self.headers(timestamp))
                self.assertEqual(result.status_code, status)
        self.assertIsNone(pi_routes._frame)

    def test_server_restart_requires_resync(self):
        headers = self.headers()
        headers['X-Clock-Id'] = 'previous-server'
        result = self.client.post('/api/camera/frame', data=self.jpeg, headers=headers)
        self.assertEqual(result.status_code, 409)

    def test_expiration_uses_capture_time(self):
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            self.client.post('/api/camera/frame', data=self.jpeg, headers=self.headers(8))
        with patch('routes.pi_routes.time.monotonic', return_value=11.1):
            self.assertFalse(self.client.get('/api/camera/status').json['connected'])
            self.assertEqual(self.client.get('/api/camera/frame').status_code, 503)

    def test_legacy_sender_is_explicitly_marked_estimated(self):
        with patch('routes.pi_routes.time.monotonic', return_value=10):
            self.client.post('/api/camera/frame', data=self.jpeg)
            result = self.client.get('/api/camera/frame')
        self.assertEqual(result.headers['X-Timing-Source'], 'received')
        self.assertEqual(float(result.headers['X-Captured-At']), 10)

    def test_clock_sync_uses_fastest_round_trip_and_handles_clock_offset(self):
        def response(value):
            return io.BytesIO(json.dumps({'server_time': value, 'clock_id': 'clock'}).encode())
        with patch('pi_camera.time.monotonic', side_effect=[1, 1.2, 2, 2.02, 3, 3.1]), \
                patch('pi_camera.urllib.request.urlopen', side_effect=[response(101.1), response(102.01), response(103.05)]):
            offset, clock_id, uncertainty = synchronize_clock('http://pc')
        self.assertAlmostEqual(offset, 100)
        self.assertAlmostEqual(uncertainty, .01)
        self.assertEqual(clock_id, 'clock')

    def test_sensor_timestamp_and_missing_metadata(self):
        captured, source = capture_timestamp({'SensorTimestamp': 9_900_000_000,
                                              'ExposureTime': 10000}, 10)
        self.assertAlmostEqual(captured, 9.895)
        self.assertEqual(source, 'sensor')
        self.assertEqual(capture_timestamp({}, 10), (10, 'estimated'))
        self.assertEqual(capture_timestamp({'SensorTimestamp': float('nan')}, 10), (10, 'estimated'))


if __name__ == '__main__':
    unittest.main()
