"""Latest Pi camera frame, kept in memory and expired after three seconds."""
import threading
import time
import math
import uuid
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
CLOCK_ID = uuid.uuid4().hex
FRAME_TIMEOUT = 3.0


@pi_bp.get('/api/camera/clock')
def camera_clock():
    return jsonify(server_time=time.monotonic(), clock_id=CLOCK_ID)


@pi_bp.post('/api/camera/frame')
def upload_camera_frame():
    global _frame, _received, _sequence, _captured_at, _timing_source, _clock_uncertainty
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
    with _frame_lock:
        _frame = encoded
        _received = received
        _captured_at = captured
        _timing_source = source
        _clock_uncertainty = uncertainty
        _sequence += 1
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
    return Response(encoded, mimetype='image/jpeg', headers={
        'X-Frame-Id': str(sequence), 'Cache-Control': 'no-store',
        'X-Captured-At': str(captured), 'X-Server-Time': str(time.monotonic()),
        'X-Timing-Source': source, 'X-Clock-Uncertainty': str(uncertainty)})
