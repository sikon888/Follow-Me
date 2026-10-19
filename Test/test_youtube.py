import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from app import app


class YoutubeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_query_validation(self):
        self.assertEqual(self.client.get('/api/youtube/search?q=').status_code, 400)
        self.assertEqual(self.client.get('/api/youtube/search?q=' + 'x'*201).status_code, 400)

    def test_missing_key_fallback(self):
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}), \
                patch('routes.youtube_routes.search_without_key', side_effect=ImportError):
            r = self.client.get('/api/youtube/search?q=dance')
        self.assertEqual(r.status_code, 503)
        self.assertIn('youtube.com/results?', r.json['youtube_url'])

    def test_search_without_api_key(self):
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}), \
                patch('routes.youtube_routes.search_without_key', return_value=[{'title': 'Dance'}]):
            r = self.client.get('/api/youtube/search?q=dance')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['videos'][0]['title'], 'Dance')

    def test_results(self):
        payload = {'items': [{'id': {'videoId': 'abcdefghijk'}, 'snippet': {
            'title': 'Dance &amp; music', 'channelTitle': 'Example'}}]}
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test-key'}), \
                patch('routes.youtube_routes.urllib.request.urlopen') as remote:
            remote.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
            r = self.client.get('/api/youtube/search?q=dance')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['videos'][0]['title'], 'Dance & music')
        self.assertNotIn('test-key', r.get_data(as_text=True))

    def test_google_error_reason_and_key_redaction(self):
        payload = {'error': {'message': 'API test-key disabled',
                            'errors': [{'reason': 'accessNotConfigured'}]}}
        failure = HTTPError('https://www.googleapis.com', 403, 'Forbidden', {},
                            io.BytesIO(json.dumps(payload).encode()))
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test-key'}), \
                patch('routes.youtube_routes.urllib.request.urlopen', side_effect=failure):
            result = self.client.get('/api/youtube/search?q=dance')
        self.assertEqual(result.status_code, 502)
        self.assertIn('accessNotConfigured', result.json['error'])
        self.assertIn('Enable YouTube Data API v3', result.json['error'])
        self.assertNotIn('test-key', result.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
