from pathlib import Path
import sys
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "beeline_case_participants (1)"
sys.path.insert(0, str(ROOT))

from experiments.candidate_generator import candidate_tuples, generate_candidates


class CandidateGeneratorTests(unittest.TestCase):
    def test_generator_returns_valid_ranked_candidates(self):
        history = pd.read_csv(CASE_DIR / "data" / "change_tariff.csv")
        profile = pd.read_csv(CASE_DIR / "customer_profile.csv")
        tariffs = pd.read_csv(CASE_DIR / "data" / "dict_tariff.csv")

        result = generate_candidates(history, profile, tariffs, limit=30)
        tuples = candidate_tuples(result)
        available_cells = set(
            profile.dropna(subset=["current_tariff", "arpu_segment"])
            [["current_tariff", "arpu_segment"]]
            .itertuples(index=False, name=None)
        )
        known_tariffs = set(tariffs["tariff_plan_code"])

        self.assertGreaterEqual(len(result), 15)
        self.assertLessEqual(len(result), 30)
        self.assertTrue(result["ranking_score"].is_monotonic_decreasing)
        self.assertTrue(result["prior_push_lift"].gt(0).all())
        self.assertEqual(len(tuples), len(set(tuples)))
        self.assertTrue(all(candidate[:2] in available_cells for candidate in tuples))
        self.assertTrue(all(candidate[2] in known_tariffs for candidate in tuples))
        self.assertTrue(all(candidate[0] != candidate[2] for candidate in tuples))


if __name__ == "__main__":
    unittest.main()
