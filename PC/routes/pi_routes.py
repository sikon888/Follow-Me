"""Latest Pi camera frame, kept in memory and expired after three seconds."""
import threading
import time
import math
import uuid
import json
from collections import OrderedDict
import cv2
import numpy as np
from flask import Blueprint, Response, jsonify, request

pi_bp = Blueprint('pi', __name__)
_frame_lock = threading.Lock()
_frame = None
_received = 0.0
_sequence = 0
_captured_at = 0.0
_timing_source = 'received'
_clock_uncertainty = 0.0
_pose_frames = OrderedDict()
_pose = None
CLOCK_ID = uuid.uuid4().hex
FRAME_TIMEOUT = 3.0


def get_pose_frame(frame_id, clock_id):
    """Return the exact uploaded pose shown by the browser, never the latest pose."""
    with _frame_lock:
        if clock_id != CLOCK_ID:
            raise ValueError('Camera clock changed; fetch a new frame')
        entry = _pose_frames.get(frame_id)
        if entry is None or time.monotonic() - entry['captured_at'] >= FRAME_TIMEOUT:
            raise ValueError('Pi pose expired; fetch a new frame')
        return entry


@pi_bp.get('/api/camera/clock')
def camera_clock():
    return jsonify(server_time=time.monotonic(), clock_id=CLOCK_ID)


@pi_bp.post('/api/camera/frame')
def upload_camera_frame():
    global _frame, _received, _sequence, _captured_at, _timing_source, _clock_uncertainty, _pose
    received = time.monotonic()
    captured = received
    source = 'received'
    uncertainty = 0.0
    if 'X-Captured-At' in request.headers:
        if request.headers.get('X-Clock-Id') != CLOCK_ID:
            return jsonify(error='Camera clock changed; synchronize again'), 409
        try:
            captured = float(request.headers['X-Captured-At'])
            uncertainty = float(request.headers.get('X-Clock-Uncertainty', '0'))
            if not math.isfinite(captured) or not math.isfinite(uncertainty) or not 0 <= uncertainty <= 0.25:
                raise ValueError
        except ValueError:
            return jsonify(error='Invalid camera timestamp'), 400
        if captured > received + uncertainty + 0.05 or received - captured >= FRAME_TIMEOUT:
            return jsonify(error='Camera timestamp is stale or in the future; synchronize again'), 409
        captured = min(captured, received)
        source = 'sensor' if request.headers.get('X-Timing-Source') == 'sensor' else 'estimated'
    if request.content_length and request.content_length > 2_000_000:
        return jsonify(error='Frame too large'), 413
    encoded = request.stream.read(2_000_001)
    if len(encoded) > 2_000_000:
        return jsonify(error='Frame too large'), 413
    image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
    if image is None or max(image.shape[:2]) > 1920:
        return jsonify(error='Invalid camera JPEG (maximum dimension 1920)'), 400
    pose = None
    if 'X-Pose-Skeleton' in request.headers:
        try:
            if len(request.headers['X-Pose-Skeleton']) > 4096:
                raise ValueError
            raw = np.asarray(json.loads(request.headers['X-Pose-Skeleton']), dtype=np.float32)
            if (raw.shape != (17, 3) or not np.isfinite(raw).all() or
                    np.any(raw[:, 2] < 0) or np.any(raw[:, 2] > 1)):
                raise ValueError
            pose = raw.tolist()
        except (ValueError, TypeError, OverflowError):
            return jsonify(error='Invalid Pi skeleton; expected finite COCO-17 x,y,confidence'), 400
    with _frame_lock:
        _frame = encoded
        _received = received
        _captured_at = captured
        _timing_source = source
        _clock_uncertainty = uncertainty
        _sequence += 1
        _pose = pose
        # Bound memory and retain older frames while a browser request is in flight.
        for key in list(_pose_frames):
            if received - _pose_frames[key]['captured_at'] >= FRAME_TIMEOUT:
                del _pose_frames[key]
        if pose is not None:
            _pose_frames[_sequence] = dict(skeleton=pose, width=image.shape[1],
                                         height=image.shape[0], captured_at=captured)
        while len(_pose_frames) > 90:
            _pose_frames.popitem(last=False)
    return jsonify(connected=True)


@pi_bp.get('/api/camera/status')
def camera_status():
    with _frame_lock:
        connected = _frame is not None and time.monotonic() - _captured_at < FRAME_TIMEOUT
    return jsonify(connected=connected)


@pi_bp.get('/api/camera/frame')
def camera_frame():
    with _frame_lock:
        now = time.monotonic()
        if _frame is None or now - _captured_at >= FRAME_TIMEOUT:
            return jsonify(connected=False, error='Disconnected'), 503
        encoded, sequence = _frame, _sequence
        captured, source, uncertainty = _captured_at, _timing_source, _clock_uncertainty
        pose = _pose
    headers = {
        'X-Frame-Id': str(sequence), 'Cache-Control': 'no-store',
        'X-Captured-At': str(captured), 'X-Server-Time': str(time.monotonic()),
        'X-Timing-Source': source, 'X-Clock-Uncertainty': str(uncertainty),
        'X-Clock-Id': CLOCK_ID, 'X-Pose-Backend': 'pi' if pose is not None else 'pc'}
    return Response(encoded, mimetype='image/jpeg', headers=headers)
