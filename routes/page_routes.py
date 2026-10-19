from flask import (
    Blueprint,
    render_template
)

from modules.file_manager import (
    get_playlist_data
)


page_bp = Blueprint(
    "page",
    __name__
)


# =========================================
# HOME / PLAYLIST
# =========================================

@page_bp.route("/")
def home():

    playlist = get_playlist_data()

    return render_template(
        "index.html",
        playlist=playlist
    )


# =========================================
# UPLOAD PAGE
# =========================================

@page_bp.route("/upload-page")
def upload_page():

    return render_template(
        "upload.html"
    )