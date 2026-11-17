import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from app import app
from modules import youtube_downloads as downloads


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.path_patch = patch.object(downloads, 'UPLOAD_FOLDER', self.root)
        self.path_patch.start()
        downloads._jobs.clear()

    def tearDown(self):
        self.path_patch.stop()
        self.folder.cleanup()
        downloads._jobs.clear()

    def test_validation_and_duplicate_start(self):
        client = app.test_client()
        self.assertEqual(client.post('/api/youtube/download/invalid').status_code, 400)
        with patch.object(downloads.threading, 'Thread') as thread:
            first = client.post('/api/youtube/download/abcdefghijk')
            second = client.post('/api/youtube/download/abcdefghijk')
            self.assertEqual(first.status_code, 202)
            self.assertEqual(second.status_code, 202)
            thread.assert_called_once()
            self.assertEqual(client.post('/api/youtube/download/12345678901').status_code, 409)

    def test_complete_import_and_existing_video(self):
        def fake_extract(url, download):
            self.assertTrue(download)
            folder = next(self.root.iterdir())
            writer = cv2.VideoWriter(str(folder / 'video.mp4'), cv2.VideoWriter_fourcc(*'mp4v'),
                                     10, (64, 64))
            writer.write(np.zeros((64, 64, 3), np.uint8))
            writer.release()
            return {'title': 'My Dance'}
        with patch('yt_dlp.YoutubeDL') as downloader, \
                patch.object(downloads, 'set_reference_name') as rename:
            downloader.return_value.__enter__.return_value.extract_info.side_effect = fake_extract
            downloads.download('abcdefghijk')
            rename.assert_called_once_with('youtube_abcdefghijk.mp4', 'My Dance')
        self.assertEqual(downloads.status('abcdefghijk')['status'], 'Saved')
        self.assertTrue((self.root / 'youtube_abcdefghijk.mp4').is_file())
        self.assertEqual(downloads.start('abcdefghijk')['status'], 'Saved')
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_failed_import_keeps_playlist_clean(self):
        with patch('yt_dlp.YoutubeDL') as downloader:
            downloader.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError('network')
            downloads.download('abcdefghijk')
        self.assertEqual(downloads.status('abcdefghijk')['status'], 'Error')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_bundled_ffmpeg_used_for_merge(self):
        with patch.object(downloads, 'find_ffmpeg', return_value='C:/tools/ffmpeg.exe'), \
                patch('yt_dlp.YoutubeDL') as downloader:
            downloader.return_value.__enter__.return_value.extract_info.side_effect = RuntimeError('network')
            downloads.download('abcdefghijk')
            options = downloader.call_args.args[0]
        self.assertEqual(options['ffmpeg_location'], 'C:/tools/ffmpeg.exe')
        self.assertIn('+ba[ext=m4a]', options['format'])
