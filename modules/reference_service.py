import numpy as np
import os
from modules.reference_store import video_digest, reference_valid

from modules.pose_processor import (
    extract_skeleton,
    normalize_skeleton
)

from modules.file_manager import (
    get_video_path,
    get_reference_path
)


processing_status = {}


def process_reference(filename):

    try:

        processing_status[filename] = {
            "status": "Processing"
        }

        video_path = get_video_path(
            filename
        )

        if not video_path.exists():

            raise FileNotFoundError(
                "Video not found"
            )

        print()
        print("========================")
        print("Processing:", filename)
        print("========================")

        digest = video_digest(filename)
        def report_progress(done, total):
            processing_status[filename] = {
                'status': 'Processing',
                'progress': min(98, int(98 * done / total)) if total > 0 else None,
                'frames_processed': done,
                'total_frames': int(total),
            }
        raw, timestamps = extract_skeleton(
            video_path, return_timestamps=True,
            progress_callback=report_progress
        )

        print(
            "Raw shape:",
            raw.shape
        )

        normalized = normalize_skeleton(
            raw
        )
        processing_status[filename] = {'status': 'Processing', 'progress': 99}

        print(
            "Normalized shape:",
            normalized.shape
        )

        output_path = get_reference_path(
            filename
        )

        if digest != video_digest(filename):
            raise ValueError('Video changed during processing')
        temporary = output_path.with_suffix('.tmp.npz')
        np.savez_compressed(temporary, skeleton=normalized, raw_skeleton=raw, timestamps=timestamps,
                            backend='mediapipe_coco17_pixels_v1', video_sha256=digest)
        os.replace(temporary, output_path)

        processing_status[filename] = {
            "status": "Saved",
            "progress": 100,
            "reference": output_path.name
        }

        print(
            "Reference saved:",
            output_path
        )

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        processing_status[filename] = {
            "status": "Error",
            "error": str(e)
        }


def get_status(filename):

    if processing_status.get(filename, {}).get('status') != 'Processing' and reference_valid(filename):
        return {'status': 'Saved'}

    if processing_status.get(filename, {}).get('status') == 'Saved':
        return {'status': 'Not Saved'}

    return processing_status.get(
        filename,
        {
            "status": "Not Saved"
        }
    )


def set_not_saved(filename):

    processing_status[filename] = {
        "status": "Not Saved"
    }

def get_playlist_status(filenames):

    result = []

    for filename in filenames:

        status = get_status(filename)

        result.append({
            "filename": filename,
            "status": status.get(
                "status",
                "Not Saved"
            )
        })

    return result
