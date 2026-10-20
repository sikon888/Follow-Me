import io
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from modules.pose_processor import extract_skeleton
from modules.reference_store import load_reference, _load_reference


class ProcessingTests(unittest.TestCase):
    def test_sampling_preserves_timestamps_and_reports_decoded_progress(self):
        class Capture:
            index = 0
            def isOpened(self): return True
            def read(self):
                self.index += 1
                return (True, np.zeros((20, 30, 3), np.uint8)) if self.index <= 60 else (False, None)
            def get(self, prop):
                if prop == cv2.CAP_PROP_FPS: return 60
                if prop == cv2.CAP_PROP_FRAME_COUNT: return 60
                return (self.index - 1) * 1000 / 60
            def release(self): pass

        updates = []
        with patch('modules.pose_processor.cv2.VideoCapture', return_value=Capture()), \
                patch('modules.pose_processor.PoseDetector') as detector:
            detector.return_value.detect.return_value = np.zeros((17, 3))
            poses, times = extract_skeleton('fake', True, target_fps=15,
                                           progress_callback=lambda done, total: updates.append((done, total)))
        self.assertEqual(len(poses), 15)
        np.testing.assert_allclose(times, np.arange(15) / 15)
        self.assertEqual(updates[-1], (60, 60))

    def test_live_model_is_reused_without_video_tracking(self):
        from app import app
        import routes.player_routes as route
        pose = np.zeros((17, 3), np.float32)
        pose[:, 2] = 1
        pose[6, 0] = 100
        _, jpeg = cv2.imencode('.jpg', np.zeros((20, 30, 3), np.uint8))
        with patch.object(route, 'live_detector', None), \
                patch.object(route, 'load_reference', return_value=(pose[None], np.array([0]))), \
                patch.object(route, 'PoseDetector') as detector:
            detector.return_value.detect.return_value = pose
            for _ in range(2):
                result = app.test_client().post('/api/player/fake.mp4', data={
                    'time': '0', 'frame': (io.BytesIO(jpeg.tobytes()), 'frame.jpg')})
                self.assertEqual(result.status_code, 200)
            detector.assert_called_once_with(image_mode=True)
            self.assertEqual(detector.return_value.detect.call_count, 2)

    def test_cache_refreshes_when_file_changes(self):
        from types import SimpleNamespace
        stat = SimpleNamespace(st_size=1, st_mtime_ns=1, st_ctime_ns=1)
        _load_reference.cache_clear()
        with patch('modules.reference_store.get_video_path') as video, \
                patch('modules.reference_store.get_reference_path') as reference, \
                patch('modules.reference_store.np.load') as reader, \
                patch('modules.reference_store.video_digest', return_value='digest') as digest:
            video.return_value.stat.return_value = stat
            reference.return_value.stat.return_value = stat
            reader.return_value.__enter__.return_value = {
                'backend': 'mediapipe_coco17_pixels_v1', 'video_sha256': 'digest',
                'skeleton': np.zeros((1, 17, 3)), 'timestamps': np.array([0.])}
            load_reference('fake')
            load_reference('fake')
            self.assertEqual(digest.call_count, 1)
            video.return_value.stat.return_value = SimpleNamespace(st_size=2, st_mtime_ns=2, st_ctime_ns=2)
            load_reference('fake')
            self.assertEqual(digest.call_count, 2)
        _load_reference.cache_clear()


if __name__ == '__main__':
    unittest.main()
