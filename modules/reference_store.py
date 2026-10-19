import hashlib
import numpy as np
from modules.file_manager import get_video_path, get_reference_path


def video_digest(filename):
    with get_video_path(filename).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_reference(filename):
    with np.load(get_reference_path(filename), allow_pickle=False) as saved:
        if str(saved['backend']) != 'mediapipe_coco17_pixels_v1':
            raise ValueError('Incompatible pose backend')
        if str(saved['video_sha256']) != video_digest(filename):
            raise ValueError('Video changed; regenerate reference')
        data, times = saved['skeleton'], saved['timestamps']
    if (data.ndim != 3 or data.shape[1:] != (17, 3) or not len(data)
            or times.shape != (len(data),) or not np.isfinite(data).all()
            or not np.isfinite(times).all() or times[0] < 0
            or np.any(np.diff(times) <= 0)):
        raise ValueError('Invalid reference timeline/data')
    return data, times


def reference_valid(filename):
    try:
        load_reference(filename)
        return True
    except (OSError, ValueError, KeyError):
        return False
