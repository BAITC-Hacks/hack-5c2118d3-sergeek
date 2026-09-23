"""Adaptive campaign agent for the Beeline tariff marketing case.

The agent uses historical analysis only to define a compact candidate set. At
runtime every decision is driven by pilots on the current audience. Push is
used for exploration; final channels are allocated jointly under the live
budget and contact limits.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import product
from math import sqrt

import pandas as pd


PER_CUSTOMER_STD = 0.804
PRODUCTION_CHANNELS = ("push", "sms", "digital_ads")
MAX_FINAL_CAMPAIGNS = 5
MAX_CUSTOMERS_PER_CAMPAIGN = 5000

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
        selected = []
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
            selected.append(candidate)
            used_cells.add(cell)
            if len(selected) >= MAX_FINAL_CAMPAIGNS:
                break

        campaigns = self._allocate_channels(selected, observations, profile, env)

        # The submission contract requires at least one final campaign. If a
        # very unlucky exploration round makes every confidence bound negative,
        # use the best observed arm with free push rather than failing outright.
        if not campaigns and ranked:
            campaigns.append(self._campaign(ranked[0], 1, "push"))

        return campaigns

    def _allocate_channels(self, candidates, observations, profile, env):
        """Jointly choose campaigns and channels within the remaining limits."""
        if not candidates:
            return []

        push_multiplier = float(env.channels["push"]["conversion_multiplier"])
        choices = (None,) + tuple(
            channel for channel in PRODUCTION_CHANNELS if channel in env.channels
        )
        economics = []

        for candidate in candidates:
            current, segment, _ = candidate
            audience = profile[
                (profile["current_tariff"] == current)
                & (profile["arpu_segment"] == segment)
            ].sort_values("ID_NUMBER").head(MAX_CUSTOMERS_PER_CAMPAIGN)
            stats = self._stats(observations.get(candidate, []))
            if audience.empty or stats is None:
                continue

            n_customers = len(audience)
            mean_arpu = float(audience["predicted_arpu"].mean())
            channel_values = {}
            for channel in choices[1:]:
                channel_config = env.channels[channel]
                relative_multiplier = (
                    float(channel_config["conversion_multiplier"]) / push_multiplier
                )
                cost_per_contact = float(channel_config["cost_per_contact"])
                conservative_net = n_customers * (
                    mean_arpu * stats["lower_bound"] * relative_multiplier
                    - cost_per_contact
                )
                channel_values[channel] = {
                    "cost": n_customers * cost_per_contact,
                    "net": conservative_net,
                }
            economics.append((candidate, n_customers, channel_values))

        best_score = float("-inf")
        best_assignment = None
        for assignment in product(choices, repeat=len(economics)):
            if all(channel is None for channel in assignment):
                continue
            contacts = 0
            cost = 0.0
            score = 0.0
            for (_, n_customers, channel_values), channel in zip(economics, assignment):
                if channel is None:
                    continue
                contacts += n_customers
                cost += channel_values[channel]["cost"]
                score += channel_values[channel]["net"]
            if contacts > env.remaining_contacts or cost > env.remaining_budget:
                continue
            if score > best_score:
                best_score = score
                best_assignment = assignment

        if best_assignment is None:
            return []

        campaigns = []
        for (candidate, _, _), channel in zip(economics, best_assignment):
            if channel is not None:
                campaigns.append(self._campaign(candidate, len(campaigns) + 1, channel))
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
    def _campaign(candidate, number, channel):
        current, arpu_segment, target = candidate
        return {
            "campaign_name": f"adaptive_{number}_{current}_{target}_{arpu_segment.lower()}",
            "filter_arpu_segment": arpu_segment,
            "filter_current_tariff": current,
            "target_tariff": target,
            "channel": channel,
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
