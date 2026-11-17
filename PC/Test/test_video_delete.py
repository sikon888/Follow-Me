import unittest
from unittest.mock import Mock, patch

from app import app
from modules.file_manager import unlink_with_retry, delete_video_and_reference


def sharing_error():
    error = PermissionError('File is in use')
    error.winerror = 32
    return error


class VideoDeleteTests(unittest.TestCase):
    def test_retries_sharing_violation_until_stream_closes(self):
        path = Mock()
        path.unlink.side_effect = [sharing_error(), None]
        with patch('modules.file_manager.time.sleep') as sleep:
            unlink_with_retry(path)
        self.assertEqual(path.unlink.call_count, 2)
        sleep.assert_called_once_with(.1)

    def test_does_not_retry_unrelated_permission_error(self):
        path = Mock()
        path.unlink.side_effect = PermissionError('Access denied')
        with patch('modules.file_manager.time.sleep') as sleep:
            with self.assertRaises(PermissionError):
                unlink_with_retry(path)
        sleep.assert_not_called()

    def test_locked_video_preserves_reference_and_name(self):
        with patch('modules.file_manager.get_video_path') as video, \
                patch('modules.file_manager.get_reference_path') as reference, \
                patch('modules.reference_names.name_path') as name, \
                patch('modules.file_manager.time.sleep'):
            video.return_value.is_file.return_value = True
            video.return_value.unlink.side_effect = sharing_error()
            with self.assertRaises(PermissionError):
                delete_video_and_reference('test.mp4')
            reference.return_value.unlink.assert_not_called()
            name.assert_not_called()

    def test_building_video_is_not_deleted(self):
        with patch('routes.video_routes.get_status', return_value={'status': 'Processing'}), \
                patch('routes.video_routes.delete_video_and_reference') as delete:
            result = app.test_client().post('/delete/test.mp4')
        self.assertEqual(result.status_code, 409)
        delete.assert_not_called()

    def test_busy_file_returns_actionable_error(self):
        with patch('routes.video_routes.get_status', return_value={'status': 'Saved'}), \
                patch('routes.video_routes.delete_video_and_reference', side_effect=sharing_error()):
            result = app.test_client().post('/delete/test.mp4')
        self.assertEqual(result.status_code, 409)
        self.assertIn('other tabs', result.json['error'])


if __name__ == '__main__':
    unittest.main()
