import numpy as np


def compare_pose(reference, player):
    expected = reference[5:, 2] >= 0.3
    if expected.sum() < 6:
        return None
    visible = expected & (player[5:, 2] >= 0.3)
    quality = np.zeros(12)
    distance = np.linalg.norm(reference[5:, :2] - player[5:, :2], axis=1)
    quality[visible] = np.clip(1 - distance[visible] / 1.5, 0, 1)
    return float(100 * quality[expected].mean())


def frame_at(times, seconds):
    return max(0, min(len(times) - 1, int(np.searchsorted(times, seconds, side='right') - 1)))
