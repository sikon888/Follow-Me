import numpy as np


# Distances are measured in shoulder widths after skeleton normalization.
POSE_TOLERANCE = 0.08
POSE_FALLOFF = 0.65
HAND_MATCH_TOLERANCE = 0.5  # Half a shoulder width, in normalized coordinates.


def compare_pose(reference, player):
    expected = reference[5:, 2] >= 0.3
    if expected.sum() < 6:
        return None
    visible = expected & (player[5:, 2] >= 0.3)
    quality = np.zeros(12)
    distance = np.linalg.norm(reference[5:, :2] - player[5:, :2], axis=1)
    # Easy hands earn up to 40 points, independently of the strict body score.
    hand_quality = 0.0
    for wrist in (4, 5):
        if visible[wrist] and np.isfinite(distance[wrist]):
            hand_quality = max(hand_quality, float(np.clip(
                1 - max(0, distance[wrist] - HAND_MATCH_TOLERANCE) / 0.75, 0, 1)))
    hand_points = 40 * hand_quality
    # Matching the torso alone must not pay for unrelated arms or seated legs.
    extremities = np.array([10, 11])  # ankles; hands are scored separately
    required = extremities[expected[extremities]]
    legs = np.array([8, 9, 10, 11])
    leg_visible = legs[visible[legs]]
    if (not np.isfinite(distance[visible]).all() or
            visible.sum() < expected.sum() * 0.65 or
            np.any(~visible[required]) or
            np.any(distance[required] > 0.65) or
            (len(leg_visible) >= 2 and distance[leg_visible].mean() > 0.65)):
        return float(hand_points)
    # Small pose differences earn full credit; larger differences lose points
    # gradually beyond the tolerance. Missing joints still earn no credit.
    excess = np.maximum(distance[visible] - POSE_TOLERANCE, 0)
    quality[visible] = np.clip(1 - excess / POSE_FALLOFF, 0, 1)
    weights = np.array([0.5, 0.5, 1, 1, 0, 0, 0.5, 0.5, 1, 1, 2, 2])
    match = float(np.average(quality[expected], weights=weights[expected]))
    # No points for a weak overall resemblance; grade good matches sharply.
    return float(hand_points + 60 * np.clip((match - 0.6) / 0.4, 0, 1) ** 2)


def frame_at(times, seconds):
    return max(0, min(len(times) - 1, int(np.searchsorted(times, seconds, side='right') - 1)))
