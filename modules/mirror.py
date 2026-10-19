import numpy as np


LEFT_RIGHT_PAIRS = [
    (1, 2),    # Eyes
    (3, 4),    # Ears
    (5, 6),    # Shoulders
    (7, 8),    # Elbows
    (9, 10),   # Wrists
    (11, 12),  # Hips
    (13, 14),  # Knees
    (15, 16)   # Ankles
]


def mirror_skeleton(skeleton):
    """
    Mirror one normalized COCO-17 skeleton.

    Input shape:
        (17, 3)

    Output shape:
        (17, 3)
    """

    mirrored = skeleton.copy()

    # Mirror X around x = 0
    mirrored[:, 0] *= -1

    # Swap Left <-> Right keypoints
    for left, right in LEFT_RIGHT_PAIRS:

        temp = mirrored[left].copy()

        mirrored[left] = mirrored[right]
        mirrored[right] = temp

    return mirrored
