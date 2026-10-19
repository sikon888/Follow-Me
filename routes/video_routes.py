from flask import (
    Blueprint,
    render_template,
    request,
    send_from_directory,
    jsonify,
    redirect,
    url_for
)

from pathlib import Path
from modules.reference_names import get_reference_name

from modules.file_manager import (
    UPLOAD_FOLDER,
    get_video_path,
    delete_video_and_reference
)

from modules.reference_service import (
    get_status,
    set_not_saved
)


video_bp = Blueprint(
    "video",
    __name__
)


# =========================================
# UPLOAD VIDEO
# =========================================

@video_bp.route(
    "/upload",
    methods=["POST"]
)
def upload_file():

    if "song" not in request.files:

        return "ไม่พบไฟล์", 400


    file = request.files["song"]


    if file.filename == "":

        return "ยังไม่ได้เลือกไฟล์", 400


    filename = Path(
        file.filename
    ).name


    if not filename.lower().endswith(
        ".mp4"
    ):

        return "รองรับเฉพาะ MP4", 400


    save_path = (
        UPLOAD_FOLDER /
        filename
    )


    file.save(
        save_path
    )


    set_not_saved(
        filename
    )


    print(
        "Uploaded:",
        filename
    )


    return redirect(

        url_for(
            "video.open_video",
            filename=filename
        )

    )


# =========================================
# VIDEO PAGE
# =========================================

@video_bp.route(
    "/video/<path:filename>"
)
def open_video(filename):

    filename = Path(
        filename
    ).name


    video_path = get_video_path(
        filename
    )


    if not video_path.is_file():

        return "Video not found", 404


    status = get_status(
        filename
    )


    return render_template(

        "uploaded.html",

        filename=filename,
        reference_name=get_reference_name(filename),

        current_status=status.get(
            "status",
            "Not Saved"
        )

    )


# =========================================
# SERVE VIDEO
# =========================================

@video_bp.route(
    "/uploads/<path:filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================================
# DELETE
# =========================================

@video_bp.route(
    "/delete/<path:filename>",
    methods=["POST"]
)
def delete_video(filename):

    try:

        filename = Path(
            filename
        ).name


        if not filename.lower().endswith(
            ".mp4"
        ):

            return jsonify({
                "status": "Error",
                "error": "Invalid filename"
            }), 400


        result = (
            delete_video_and_reference(
                filename
            )
        )


        return jsonify({

            "status":
                "Deleted",

            "video_deleted":
                result["video"],

            "reference_deleted":
                result["reference"]

        })


    except Exception as error:

        print(
            "DELETE ERROR:",
            error
        )


        return jsonify({
            "status": "Error",
            "error": str(error)
        }), 500
