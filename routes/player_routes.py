from pathlib import Path
import threading
import cv2
import numpy as np
from flask import Blueprint, request, jsonify
from modules.pose_processor import PoseDetector, normalize_skeleton
from modules.reference_store import load_reference
from modules.mirror import mirror_skeleton
from modules.scoring import compare_pose, frame_at

player_bp = Blueprint('player', __name__)
lock = threading.Lock()
live_detector = None


@player_bp.post('/api/player/<path:filename>')
def player_frame(filename):
    global live_detector
    try:
        seconds = float(request.form['time'])
        if not np.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid video time')
        reference, times = load_reference(Path(filename).name)
        encoded = request.files['frame'].read(2_000_001)
        if len(encoded) > 2_000_000:
            raise ValueError('Frame too large')
        image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
        if image is None or max(image.shape[:2]) > 1920:
            raise ValueError('Invalid camera frame')
        # IMAGE mode reuses model weights without tracking across users/seeks.
        with lock:
            if live_detector is None:
                live_detector = PoseDetector(image_mode=True)
            raw = live_detector.detect(image, 0)
        try:
            player = normalize_skeleton(raw[None])[0]
        except ValueError:
            player = np.zeros((17, 3), np.float32)
        index = frame_at(times, seconds)
        accuracy = compare_pose(mirror_skeleton(reference[index]), player)
        return jsonify(accuracy=accuracy, detected=bool(np.any(player[:, 2])),
                       frame=index, time=seconds, skeleton=raw.tolist(),
                       width=image.shape[1], height=image.shape[0])
    except (ValueError, OSError, KeyError) as exc:
        return jsonify(error=str(exc)), 400
    except (RuntimeError, ImportError) as exc:
        return jsonify(error=str(exc)), 503
