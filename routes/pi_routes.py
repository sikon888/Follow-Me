"""Latest Pi camera frame, kept in memory and expired after three seconds."""
import threading
import time
import cv2
import numpy as np
from flask import Blueprint, Response, jsonify, request

pi_bp = Blueprint('pi', __name__)
_frame_lock = threading.Lock()
_frame = None
_received = 0.0
_sequence = 0
FRAME_TIMEOUT = 3.0


@pi_bp.post('/api/camera/frame')
def upload_camera_frame():
    global _frame, _received, _sequence
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
        _received = time.monotonic()
        _sequence += 1
    return jsonify(connected=True)


@pi_bp.get('/api/camera/status')
def camera_status():
    with _frame_lock:
        connected = _frame is not None and time.monotonic() - _received < FRAME_TIMEOUT
    return jsonify(connected=connected)


@pi_bp.get('/api/camera/frame')
def camera_frame():
    with _frame_lock:
        if _frame is None or time.monotonic() - _received >= FRAME_TIMEOUT:
            return jsonify(connected=False, error='Disconnected'), 503
        encoded, sequence = _frame, _sequence
    return Response(encoded, mimetype='image/jpeg', headers={
        'X-Frame-Id': str(sequence), 'Cache-Control': 'no-store'})
