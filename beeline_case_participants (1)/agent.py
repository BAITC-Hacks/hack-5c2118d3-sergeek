"""Adaptive campaign agent for the Beeline tariff marketing case.

The agent uses historical analysis only to define a compact candidate set.  At
runtime every decision is driven by pilots on the current audience.  Push is
used for exploration and the first production version because it is free and
therefore robust to noisy or shifted effects.
"""

from __future__ import annotations

from collections import defaultdict
from math import sqrt

import pandas as pd


PER_CUSTOMER_STD = 0.804

# Ranked offline from the supplied historical sample using the same safeguards
# as the mock environment: previous ARPU >= 100 and relative change clipped to
# [-1, 3].  These are hypotheses, not hard-coded answers; pilots determine the
# final campaigns.
PRIOR_CANDIDATES = [
    ("tariff_4", "MID", "tariff_8"),
    ("tariff_13", "MID", "tariff_8"),
    ("tariff_8", "MID", "tariff_10"),
    ("tariff_8", "LOW", "tariff_9"),
    ("tariff_13", "LOW", "tariff_8"),
    ("tariff_12", "MID", "tariff_8"),
    ("tariff_4", "LOW", "tariff_9"),
    ("tariff_14", "LOW", "tariff_9"),
    ("tariff_11", "LOW", "tariff_8"),
    ("tariff_12", "LOW", "tariff_8"),
    ("tariff_10", "MID", "tariff_11"),
    ("tariff_10", "LOW", "tariff_9"),
    ("tariff_8", "MID", "tariff_11"),
    ("tariff_10", "MID", "tariff_8"),
    ("tariff_8", "HIGH", "tariff_10"),
]


class Agent:
    """Explore promising tariff transitions and exploit robust winners."""

    def act(self, env) -> list[dict]:
        profile = env.customer_profile
        known_tariffs = set(env.tariffs["tariff_plan_code"])

        candidates = self._available_candidates(profile, known_tariffs)
        if not candidates:
            return self._safe_fallback(profile, known_tariffs)

        observations: dict[tuple[str, str, str], list[tuple[int, float]]] = defaultdict(list)

        # Broad exploration: enough observations to reject clearly weak arms,
        # while preserving most of the 15k contact limit for final campaigns.
        for candidate in candidates[:10]:
            self._pilot(env, candidate, 120, observations)

        # Confirm the most promising observations with the maximum pilot size.
        first_pass = self._rank(candidates, observations, profile)
        for candidate in first_pass[:4]:
            self._pilot(env, candidate, 200, observations)

        ranked = self._rank(candidates, observations, profile)
        campaigns = []
        used_cells: set[tuple[str, str]] = set()

        # A current-tariff/ARPU cell is used at most once, so final campaigns do
        # not compete for the same customers.  Prefer arms with a positive
        # uncertainty-adjusted effect; retain a deterministic fallback below.
        for candidate in ranked:
            current, arpu_segment, target = candidate
            stats = self._stats(observations.get(candidate, []))
            if stats is None or stats["lower_bound"] <= 0:
                continue
            cell = (current, arpu_segment)
            if cell in used_cells:
                continue
            campaigns.append(self._campaign(candidate, len(campaigns) + 1))
            used_cells.add(cell)
            if len(campaigns) >= 5:
                break

        # The submission contract requires at least one final campaign.  If a
        # very unlucky exploration round makes every confidence bound negative,
        # use the best observed arm with free push rather than failing outright.
        if not campaigns and ranked:
            campaigns.append(self._campaign(ranked[0], 1))

        return campaigns

    @staticmethod
    def _available_candidates(profile: pd.DataFrame, known_tariffs: set[str]):
        available_cells = set(
            profile.dropna(subset=["current_tariff", "arpu_segment"])
            [["current_tariff", "arpu_segment"]]
            .itertuples(index=False, name=None)
        )
        return [
            candidate
            for candidate in PRIOR_CANDIDATES
            if (candidate[0], candidate[1]) in available_cells
            and candidate[2] in known_tariffs
            and candidate[0] != candidate[2]
        ]

    @staticmethod
    def _pilot(env, candidate, requested_n, observations):
        if env.pilots_left <= 0 or env.remaining_contacts < 10:
            return
        current, arpu_segment, target = candidate
        n_customers = min(requested_n, env.remaining_contacts, 200)
        if n_customers < 10:
            return
        try:
            result = env.run_pilot(
                target_tariff=target,
                channel="push",
                n_customers=n_customers,
                filter_arpu_segment=arpu_segment,
                filter_current_tariff=current,
            )
        except (RuntimeError, ValueError):
            return
        observations[candidate].append(
            (int(result["n_customers"]), float(result["observed_lift_ratio"]))
        )

    def _rank(self, candidates, observations, profile):
        cell_value = (
            profile.dropna(subset=["current_tariff", "arpu_segment"])
            .groupby(["current_tariff", "arpu_segment"], observed=True)["predicted_arpu"]
            .sum()
            .to_dict()
        )

        def score(candidate):
            stats = self._stats(observations.get(candidate, []))
            if stats is None:
                return float("-inf")
            current, segment, _ = candidate
            # Expected portfolio contribution with a modest uncertainty penalty.
            return stats["lower_bound"] * float(cell_value.get((current, segment), 0.0))

        return sorted(candidates, key=score, reverse=True)

    @staticmethod
    def _stats(samples):
        if not samples:
            return None
        total_n = sum(n for n, _ in samples)
        mean = sum(n * ratio for n, ratio in samples) / total_n
        standard_error = PER_CUSTOMER_STD / sqrt(total_n)
        return {
            "mean": mean,
            "standard_error": standard_error,
            # 0.75 is deliberately less strict than a 95% bound: the pilot
            # budget is small and false negatives also have a real opportunity
            # cost. Repeated pilots naturally tighten this value.
            "lower_bound": mean - 0.75 * standard_error,
        }

    @staticmethod
    def _campaign(candidate, number):
        current, arpu_segment, target = candidate
        return {
            "campaign_name": f"adaptive_{number}_{current}_{target}_{arpu_segment.lower()}",
            "filter_arpu_segment": arpu_segment,
            "filter_current_tariff": current,
            "target_tariff": target,
            "channel": "push",
        }

    @staticmethod
    def _safe_fallback(profile, known_tariffs):
        valid = profile.dropna(subset=["current_tariff", "arpu_segment"])
        if valid.empty:
            return []
        cell = (
            valid.groupby(["current_tariff", "arpu_segment"], observed=True)
            .size()
            .sort_values(ascending=False)
            .index[0]
        )
        current, segment = cell
        target = next((t for t in sorted(known_tariffs) if t != current), None)
        if target is None:
            return []
        return [{
            "campaign_name": "safe_fallback",
            "filter_arpu_segment": segment,
            "filter_current_tariff": current,
            "target_tariff": target,
            "channel": "push",
        }]
