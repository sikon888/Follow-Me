"""YouTube search via the official Data API; the key stays on the server."""
import html
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from flask import Blueprint, jsonify, request

youtube_bp = Blueprint('youtube', __name__)


@youtube_bp.post('/api/youtube/download/<video_id>')
def download_video(video_id):
    from modules.youtube_downloads import start
    try:
        result = start(video_id)
        return jsonify(result), 200 if result['status'] == 'Saved' else 202
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 409


@youtube_bp.get('/api/youtube/download/<video_id>')
def download_status(video_id):
    from modules.youtube_downloads import status
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        return jsonify(error='Invalid YouTube video ID'), 400
    return jsonify(status(video_id))


def search_without_key(query):
    from yt_dlp import YoutubeDL
    options = dict(quiet=True, no_warnings=True, extract_flat=True,
                   skip_download=True, socket_timeout=8, retries=0,
                   extractor_retries=0, playlistend=12)
    with YoutubeDL(options) as client:
        result = client.extract_info('ytsearch12:' + query, download=False)
    videos = []
    for item in (result or {}).get('entries', []):
        if not item:
            continue
        video_id = item.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            continue
        videos.append(dict(id=video_id, title=item.get('title') or 'YouTube video',
            channel=item.get('channel') or item.get('uploader') or '',
            thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
            url=f'https://www.youtube.com/watch?v={video_id}'))
    return videos


@youtube_bp.get('/api/youtube/search')
def youtube_search():
    query = request.args.get('q', '').strip()
    if not query or len(query) > 200:
        return jsonify(error='Enter a search between 1 and 200 characters.'), 400
    key = os.environ.get('YOUTUBE_API_KEY', '').strip()
    fallback = 'https://www.youtube.com/results?' + urllib.parse.urlencode({'search_query': query})
    if not key:
        try:
            return jsonify(videos=search_without_key(query), youtube_url=fallback)
        except ImportError:
            return jsonify(error='YouTube search setup is incomplete: install yt-dlp on the server, then retry.',
                           youtube_url=fallback), 503
        except Exception:
            return jsonify(error='Cannot search YouTube right now. Check the server internet connection or try again later.',
                           youtube_url=fallback), 502
    params = urllib.parse.urlencode(dict(part='snippet', type='video', maxResults=12,
                                        q=query, key=key))
    try:
        with urllib.request.urlopen('https://www.googleapis.com/youtube/v3/search?' + params, timeout=10) as response:
            data = json.load(response)
        videos = []
        for item in data.get('items', []):
            video_id = item.get('id', {}).get('videoId', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                continue
            snippet = item.get('snippet', {})
            videos.append(dict(id=video_id, title=html.unescape(snippet.get('title', 'YouTube video')),
                channel=html.unescape(snippet.get('channelTitle', '')),
                thumbnail=f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
                url=f'https://www.youtube.com/watch?v={video_id}'))
        return jsonify(videos=videos, youtube_url=fallback)
    except urllib.error.HTTPError as exc:
        reason = ''
        detail = ''
        try:
            error = json.loads(exc.read(64_000)).get('error', {})
            detail = str(error.get('message', ''))
            reasons = [item.get('reason', '') for item in error.get('errors', [])]
            reasons += [item.get('reason', '') for item in error.get('details', [])]
            reason = next((str(value) for value in reasons if value), '')
        except (ValueError, TypeError, AttributeError):
            pass
        # Google may include credential values in error messages. Never echo the key.
        for secret in (key, urllib.parse.quote(key, safe=''), urllib.parse.quote_plus(key)):
            detail = detail.replace(secret, '[redacted]')
            reason = reason.replace(secret, '[redacted]')
        fixes = {
            'accessNotConfigured': 'Enable YouTube Data API v3 in the project that owns this key.',
            'SERVICE_DISABLED': 'Enable YouTube Data API v3 in the project that owns this key.',
            'keyInvalid': 'Replace YOUTUBE_API_KEY with a valid Google API key, then restart the server.',
            'API_KEY_INVALID': 'Replace YOUTUBE_API_KEY with a valid Google API key, then restart the server.',
            'quotaExceeded': 'The YouTube search quota is exhausted. Check the project quota in Google Cloud.',
            'dailyLimitExceeded': 'The daily YouTube quota is exhausted. Check the project quota in Google Cloud.',
            'ipRefererBlocked': 'This server request does not match the API key application restrictions. Check them in Google Cloud.',
            'API_KEY_HTTP_REFERRER_BLOCKED': 'A browser-restricted key cannot be used by this Flask server. Use a separate server key restricted to YouTube Data API v3.',
            'API_KEY_SERVICE_BLOCKED': 'Allow YouTube Data API v3 in this key API restrictions.',
            'API_KEY_IP_ADDRESS_BLOCKED': 'Allow the server public outbound IP in this key IP restrictions.',
        }
        message = f'YouTube rejected the request (HTTP {exc.code}' + (f', {reason[:100]}' if reason else '') + ').'
        if detail:
            message += ' ' + detail[:1200]
        if reason in fixes:
            message += ' ' + fixes[reason]
        return jsonify(error=message, youtube_url=fallback), 502
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return jsonify(error='Cannot reach YouTube right now. Try again.', youtube_url=fallback), 502
