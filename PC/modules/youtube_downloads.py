"""Import completed YouTube MP4s into the local playlist."""
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path
import cv2
from modules.file_manager import UPLOAD_FOLDER
from modules.reference_names import set_reference_name

_jobs = {}
_lock = threading.Lock()


def find_ffmpeg():
    executable = shutil.which('ffmpeg')
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        executable = imageio_ffmpeg.get_ffmpeg_exe()
        return executable if Path(executable).is_file() else None
    except (ImportError, RuntimeError, OSError):
        return None


def update(video_id, **values):
    with _lock:
        _jobs[video_id] = {**_jobs.get(video_id, {}), **values}


def status(video_id):
    with _lock:
        return dict(_jobs.get(video_id, {'status': 'Not started'}))


def start(video_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Invalid YouTube video ID')
    filename = f'youtube_{video_id}.mp4'
    with _lock:
        if (UPLOAD_FOLDER / filename).is_file():
            return dict(status='Saved', filename=filename, progress=100)
        if _jobs.get(video_id, {}).get('status') == 'Downloading':
            return dict(_jobs[video_id])
        if any(job.get('status') == 'Downloading' for job in _jobs.values()):
            raise RuntimeError('Another video is downloading. Wait for it to finish.')
        _jobs[video_id] = dict(status='Downloading', progress=0)
    threading.Thread(target=download, args=(video_id,), daemon=True).start()
    return status(video_id)


def download(video_id):
    def progress(event):
        if event.get('status') == 'downloading':
            size = event.get('total_bytes') or event.get('total_bytes_estimate')
            percent = min(99, round(100 * event.get('downloaded_bytes', 0) / size)) if size else 0
            update(video_id, progress=percent)
    try:
        from yt_dlp import YoutubeDL
        with tempfile.TemporaryDirectory(prefix='youtube-', dir=UPLOAD_FOLDER) as folder:
            combined = 'b[ext=mp4][vcodec^=avc1][acodec^=mp4a]'
            ffmpeg = find_ffmpeg()
            selection = ('bv[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/' + combined
                         if ffmpeg else combined)
            options = dict(format=selection, outtmpl=str(Path(folder) / 'video.%(ext)s'),
                merge_output_format='mp4', noplaylist=True, quiet=True, no_warnings=True,
                socket_timeout=15, retries=1, fragment_retries=1, progress_hooks=[progress])
            if ffmpeg:
                options['ffmpeg_location'] = ffmpeg
            with YoutubeDL(options) as client:
                info = client.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
            path = Path(folder) / 'video.mp4'
            if not path.is_file():
                raise ValueError('No playable MP4 was produced.')
            capture = cv2.VideoCapture(str(path))
            try:
                ok, _ = capture.read()
                if not ok:
                    raise ValueError('Downloaded video could not be decoded.')
            finally:
                capture.release()
            filename = f'youtube_{video_id}.mp4'
            title = str((info or {}).get('title') or filename)
            title = ''.join(c for c in title if ord(c) >= 32).strip()[:120] or filename
            set_reference_name(filename, title)
            os.replace(path, UPLOAD_FOLDER / filename)
        update(video_id, status='Saved', filename=filename, progress=100)
    except Exception as exc:
        message = str(exc)
        if '10013' in message:
            message = 'The server cannot connect to YouTube. Start it from your own Windows PowerShell window.'
        elif 'Requested format is not available' in message:
            message = ('A compatible MP4 is unavailable. Install imageio-ffmpeg in the server Python environment and retry.'
                       if not find_ffmpeg() else 'YouTube did not offer a compatible H.264/AAC video. Try another video or update yt-dlp.')
        elif 'Sign in' in message or 'confirm' in message:
            message = 'YouTube requires sign-in or verification for this video. Try another video.'
        elif isinstance(exc, ImportError):
            message = 'Install yt-dlp in the server Python environment first.'
        else:
            message = 'Download failed. The video may be unavailable or YouTube may be blocking the request.'
        update(video_id, status='Error', error=message)
