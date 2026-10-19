from flask import (
    Blueprint,
    render_template
)

from pathlib import Path
from modules.reference_names import get_reference_name

from modules.file_manager import (
    reference_exists,
    get_video_path,
    get_reference_path
)


game_bp = Blueprint(
    "game",
    __name__
)


# =========================================
# GAME PAGE
# =========================================

@game_bp.route(
    "/play/<path:filename>"
)
def play_game(filename):

    filename = Path(filename).name

    video_path = get_video_path(
        filename
    )

    reference_path = get_reference_path(
        filename
    )


    # Video ไม่มี
    if not video_path.is_file():

        return "Video not found", 404


    # Reference ยังไม่มี
    if not reference_exists(filename):

        return "Reference not ready", 400


    return render_template(
        "game.html",
        filename=filename,
        reference_name=get_reference_name(filename)
    )
