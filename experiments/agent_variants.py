"""Experimental agents used only by stress_eval.py."""

from __future__ import annotations

from collections import defaultdict

from agent import Agent, MAX_FINAL_CAMPAIGNS


class CallEnabledAgent(Agent):
    """Submitted exploration policy with conservative call economics."""

    production_channels = ("push", "sms", "digital_ads", "call")


class StagedExplorationAgent(Agent):
    """Configurable two-stage exploration policy for offline experiments."""

    initial_count = 15
    initial_size = 80
    confirmation_count = 5
    confirmation_size = 160

    def _initial_candidates(self, candidates):
        return candidates[: self.initial_count]

    def act(self, env) -> list[dict]:
        profile = env.customer_profile
        known_tariffs = set(env.tariffs["tariff_plan_code"])
        candidates = self._available_candidates(profile, known_tariffs)
        if not candidates:
            return self._safe_fallback(profile, known_tariffs)

        observations = defaultdict(list)

        for candidate in self._initial_candidates(candidates):
            self._pilot(env, candidate, self.initial_size, observations)

        first_pass = self._rank(candidates, observations, profile)
        for candidate in first_pass[: self.confirmation_count]:
            self._pilot(env, candidate, self.confirmation_size, observations)

        ranked = self._rank(candidates, observations, profile)
        selected = []
        used_cells = set()
        for candidate in ranked:
            current, arpu_segment, _ = candidate
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
        if not campaigns and ranked:
            campaigns.append(self._campaign(ranked[0], 1, "push"))
        return campaigns


class ExpandedExplorationAgent(StagedExplorationAgent):
    """Explore two extra priors with the same 2,000-contact pilot reach."""

    initial_count = 12
    initial_size = 100
    confirmation_count = 5
    confirmation_size = 160


class GeneratedCandidateAgent(ExpandedExplorationAgent):
    """Use an automatically generated offline shortlist for exploration."""

    def __init__(self, candidates):
        self.candidates = list(candidates)

    def _available_candidates(self, profile, known_tariffs):
        available_cells = set(
            profile.dropna(subset=["current_tariff", "arpu_segment"])
            [["current_tariff", "arpu_segment"]]
            .itertuples(index=False, name=None)
        )
        return [
            candidate
            for candidate in self.candidates
            if candidate[:2] in available_cells
            and candidate[2] in known_tariffs
            and candidate[0] != candidate[2]
        ]

    def _initial_candidates(self, candidates):
        # The generator may rank several targets for one audience highly. Test
        # the best target for distinct cells first, then spend spare arms on
        # alternative targets. This protects exploration breadth.
        selected = []
        used_cells = set()
        for candidate in candidates:
            cell = candidate[:2]
            if cell in used_cells:
                continue
            selected.append(candidate)
            used_cells.add(cell)
            if len(selected) >= self.initial_count:
                return selected
        for candidate in candidates:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) >= self.initial_count:
                break
        return selected


class BroadExplorationAgent(StagedExplorationAgent):
    """Explore all fifteen priors with the same 2,000-contact pilot reach."""


class DiverseExplorationAgent(StagedExplorationAgent):
    """Explore every unique current-tariff/ARPU audience cell once."""

    initial_count = 13
    initial_size = 92
    confirmation_count = 5
    confirmation_size = 160

    def _initial_candidates(self, candidates):
        selected = []
        cells = set()
        for candidate in candidates:
            cell = candidate[:2]
            if cell in cells:
                continue
            selected.append(candidate)
            cells.add(cell)
            if len(selected) >= self.initial_count:
                break
        return selected
