from flask import (
    Blueprint,
    jsonify,
    request
)

from pathlib import Path
from threading import Thread

from modules.file_manager import (
    get_video_path
)

from modules.reference_service import (
    process_reference,
    get_status
)


reference_bp = Blueprint(
    "reference",
    __name__
)


@reference_bp.post('/api/reference-name/<path:filename>')
def rename_reference(filename):
    from modules.reference_names import set_reference_name
    filename = Path(filename).name
    if not get_video_path(filename).is_file():
        return jsonify(error='Video not found'), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Enter a reference name'), 400
    try:
        return jsonify(name=set_reference_name(filename, data.get('name')))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@reference_bp.get('/api/reference-skeleton/<path:filename>')
def reference_skeleton(filename):
    import numpy as np
    from modules.file_manager import get_reference_path
    from modules.reference_store import load_reference

    filename = Path(filename).name
    if not get_video_path(filename).is_file():
        return jsonify(error='Video not found'), 404
    try:
        _, timestamps = load_reference(filename)
        with np.load(get_reference_path(filename), allow_pickle=False) as saved:
            if 'raw_skeleton' not in saved:
                return jsonify(error='Rebuild Reference once to enable the skeleton overlay.'), 400
            skeleton = saved['raw_skeleton']
    except (OSError, ValueError, KeyError):
        return jsonify(error='Reference not ready. Save or rebuild the reference first.'), 400
    return jsonify(skeleton=skeleton.tolist(), timestamps=timestamps.tolist())


# =========================================
# SAVE REFERENCE
# =========================================

@reference_bp.route(
    "/save/<path:filename>",
    methods=["POST"]
)
def save_reference(filename):

    filename = Path(
        filename
    ).name


    video_path = get_video_path(
        filename
    )


    if not video_path.is_file():

        return jsonify({
            "status": "Error",
            "error": "Video not found"
        }), 404


    current = get_status(
        filename
    )


    if (
        current.get("status")
        == "Processing"
    ):

        return jsonify(
            current
        )


    thread = Thread(

        target=process_reference,

        args=(
            filename,
        ),

        daemon=True

    )


    from modules.reference_service import processing_status
    processing_status[filename] = {'status': 'Processing'}
    thread.start()


    return jsonify({
        "status": "Processing"
    })


# =========================================
# STATUS
# =========================================

@reference_bp.route(
    "/status/<path:filename>"
)
def check_status(filename):

    filename = Path(
        filename
    ).name


    return jsonify(
        get_status(filename)
    )
