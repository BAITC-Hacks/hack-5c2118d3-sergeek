"""Smoke tests for the submission contract and dashboard data."""

from __future__ import annotations

import unittest

import pandas as pd

from api.main import CASE_DIR, _run_agent


class AgentContractTests(unittest.TestCase):
    def test_agent_respects_contract_across_seeds(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                run = _run_agent(seed)
                result = run["result"]

                self.assertEqual(result["status"], "PASS")
                self.assertGreaterEqual(run["final_campaign_count"], 1)
                self.assertLessEqual(run["final_campaign_count"], 10)
                self.assertGreater(run["pilot_count"], 0)
                self.assertLessEqual(run["pilot_count"], 20)
                self.assertLessEqual(result["total_contacts"], 15_000)
                self.assertLessEqual(result["total_cost"], 100_000)

                cells = set()
                for campaign in run["campaigns"]:
                    self.assertLessEqual(campaign["audience_size"], 5_000)
                    self.assertGreater(campaign["pilot_sample_size"], 0)
                    self.assertIsNotNone(campaign["standard_error"])
                    self.assertIsNotNone(campaign["lower_bound"])
                    cell = (
                        campaign["current_tariff"],
                        campaign["arpu_segment"],
                    )
                    self.assertNotIn(cell, cells)
                    cells.add(cell)

    def test_submission_has_required_columns(self):
        submission = pd.read_csv(CASE_DIR / "submission.csv")
        self.assertGreaterEqual(len(submission), 1)
        self.assertLessEqual(len(submission), 10)
        self.assertTrue({"target_tariff", "channel"}.issubset(submission.columns))
        self.assertFalse(submission[["target_tariff", "channel"]].isna().any().any())


if __name__ == "__main__":
    unittest.main()
