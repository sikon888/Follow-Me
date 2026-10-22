import unittest
import numpy as np
from modules.scoring import compare_pose


class StrictScoringTests(unittest.TestCase):
    def setUp(self):
        self.pose = np.zeros((17, 3), np.float32)
        self.pose[:, 2] = 1
        self.pose[5:, :2] = [(-.5, -1), (.5, -1), (-.7, -.5), (.7, -.5),
                             (-.8, 0), (.8, 0), (-.3, 0), (.3, 0),
                             (-.3, 1), (.3, 1), (-.3, 2), (.3, 2)]

    def test_perfect_pose_and_small_jitter(self):
        self.assertEqual(compare_pose(self.pose, self.pose), 100)
        jitter = self.pose.copy()
        jitter[:, :2] += .03
        self.assertEqual(compare_pose(self.pose, jitter), 100)

    def test_wrong_legs_without_a_hand_match_get_zero(self):
        sitting = self.pose.copy()
        sitting[13:17, 1] -= 1
        sitting[9:11, 1] += 2
        self.assertEqual(compare_pose(self.pose, sitting), 0)

    def test_wrong_arms_and_hidden_feet_lose_credit(self):
        wrong = self.pose.copy()
        wrong[9:11, 1] += 1
        self.assertLess(compare_pose(self.pose, wrong), 80)
        hidden = self.pose.copy()
        hidden[15:17, 2] = 0
        hidden[9:11, 1] += 1
        self.assertLess(compare_pose(self.pose, hidden), 70)

    def test_moderate_errors_reduce_score_sharply(self):
        offset = self.pose.copy()
        offset[7:11, 0] += .6
        self.assertGreater(compare_pose(self.pose, offset), 0)
        self.assertLess(compare_pose(self.pose, offset), 80)

    def test_matching_seated_reference_is_valid(self):
        sitting = self.pose.copy()
        sitting[13:17, 1] -= 1
        self.assertEqual(compare_pose(sitting, sitting), 100)

    def test_either_nearby_hand_earns_only_hand_points_with_wrong_body(self):
        for wrist in (9, 10):
            player = self.pose.copy()
            player[5:, :2] += 2  # Other joints deliberately do not match.
            player[wrist] = self.pose[wrist]
            player[wrist, 0] += .45
            self.assertEqual(compare_pose(self.pose, player), 40)

    def test_seated_legs_cannot_earn_body_points_even_with_matching_hands(self):
        seated = self.pose.copy()
        seated[13:17, 1] -= 1
        self.assertEqual(compare_pose(self.pose, seated), 40)

    def test_missing_or_invalid_hand_does_not_unlock_full_score(self):
        for confidence, x in [(0, 0), (1, float('nan'))]:
            player = self.pose.copy()
            player[5:, :2] += 2
            player[9] = self.pose[9]
            player[9, 2] = confidence
            player[9, 0] = x
            self.assertEqual(compare_pose(self.pose, player), 0)
