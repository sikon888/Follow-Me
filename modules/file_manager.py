from pathlib import Path
import time


def unlink_with_retry(path):
    """Allow a cancelled browser stream a short time to close on Windows."""
    for attempt in range(10):
        try:
            path.unlink(missing_ok=True)
            return
        except OSError as error:
            if getattr(error, 'winerror', None) not in (32, 33) or attempt == 9:
                raise
            time.sleep(0.1)


# =========================================
# FOLDERS
# =========================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_FOLDER = BASE_DIR / "uploads"

REFERENCE_FOLDER = (
    BASE_DIR /
    "reference_library" / "mediapipe_v1"
)


# สร้าง Folder ถ้ายังไม่มี
UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

REFERENCE_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================
# GET ALL UPLOADED VIDEOS
# =========================================

def get_uploaded_videos():

    videos = []

    for file in UPLOAD_FOLDER.glob("*.mp4"):

        if file.is_file():

            videos.append(
                file.name
            )

    return sorted(videos)


# =========================================
# GET VIDEO PATH
# =========================================

def get_video_path(filename):

    safe_filename = Path(
        filename
    ).name

    return (
        UPLOAD_FOLDER /
        safe_filename
    )


# =========================================
# GET REFERENCE PATH
# =========================================

def get_reference_path(filename):

    video_path = get_video_path(
        filename
    )

    reference_name = (
        video_path.name
        + "_mediapipe_v1.npz"
    )

    return (
        REFERENCE_FOLDER /
        reference_name
    )


# =========================================
# CHECK REFERENCE
# =========================================

def reference_exists(filename):

    reference_path = (
        get_reference_path(
            filename
        )
    )

    from modules.reference_store import reference_valid
    return reference_valid(filename)


# =========================================
# PLAYLIST DATA
# =========================================

def get_playlist_data():

    from modules.reference_names import get_reference_name

    videos = (
        get_uploaded_videos()
    )

    playlist = []


    for filename in videos:

        reference_path = (
            get_reference_path(
                filename
            )
        )


        playlist.append({

            "filename":
                filename,

            "display_name": get_reference_name(filename),

            "ready":
                reference_exists(filename),

            "reference":
                reference_path.name

        })


    return playlist


# =========================================
# DELETE VIDEO + REFERENCE
# =========================================

def delete_video_and_reference(
    filename
):

    safe_filename = Path(
        filename
    ).name

    from modules.reference_names import name_path


    video_path = (
        get_video_path(
            safe_filename
        )
    )


    reference_path = (
        get_reference_path(
            safe_filename
        )
    )


    result = {

        "video":
            False,

        "reference":
            False

    }


    # -------------------------------------
    # DELETE VIDEO
    # -------------------------------------

    if video_path.is_file():

        unlink_with_retry(video_path)

        result["video"] = True

        print(
            "Deleted video:",
            video_path
        )


    # -------------------------------------
    # DELETE REFERENCE
    # -------------------------------------

    if reference_path.is_file():

        unlink_with_retry(reference_path)

        result["reference"] = True

        print(
            "Deleted reference:",
            reference_path
        )


    name_path(safe_filename).unlink(missing_ok=True)
    return result
