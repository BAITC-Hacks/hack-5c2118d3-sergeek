"""Evaluate the submitted agent under synthetic hidden-model shifts.

This is not an alternative scorer. It keeps the official mechanics and changes
only the unknown impact table to test whether a strategy is overly dependent
on the supplied local mock ranking.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "beeline_case_participants (1)"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CASE_DIR))

from agent import Agent  # noqa: E402
from experiments.agent_variants import (  # noqa: E402
    BroadExplorationAgent,
    CallEnabledAgent,
    DiverseExplorationAgent,
    ExpandedExplorationAgent,
)
from environment import make_environment  # noqa: E402
from mock_environment import (  # noqa: E402
    CHANNELS,
    MAX_TOTAL_CONTACTS,
    TOTAL_BUDGET,
    _mock_fallback,
    _mock_impact_model,
)
from scoring_core import MAX_CAMPAIGNS, sanitize_campaigns, score_campaigns  # noqa: E402


FILTER_COLUMNS = [
    "filter_arpu_segment",
    "filter_data_segment",
    "filter_call_segment",
    "filter_current_tariff",
    "explicit_ids",
]
SCENARIOS = (
    "base",
    "effect_noise",
    "sign_flip",
    "ranking_shuffle",
    "weak_history",
    "combined_shift",
)
AGENTS = {
    "current": Agent,
    "expanded": ExpandedExplorationAgent,
    "broad": BroadExplorationAgent,
    "diverse": DiverseExplorationAgent,
    "call": CallEnabledAgent,
}


def shifted_model(base: pd.DataFrame, scenario: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    model = base.copy()
    effect = model["arpu_change_pct"].to_numpy(dtype=float).copy()
    conversion = model["conversion_rate"].to_numpy(dtype=float).copy()

    if scenario == "base":
        pass
    elif scenario == "effect_noise":
        effect += rng.normal(0.0, 0.18, len(effect))
    elif scenario == "sign_flip":
        mask = rng.random(len(effect)) < 0.20
        effect[mask] *= -1
    elif scenario == "ranking_shuffle":
        effect = rng.permutation(effect)
        conversion = rng.permutation(conversion)
    elif scenario == "weak_history":
        global_effect = float(np.median(effect))
        effect = 0.30 * effect + 0.70 * global_effect
        conversion *= rng.uniform(0.65, 1.15, len(conversion))
    elif scenario == "combined_shift":
        effect += rng.normal(0.0, 0.12, len(effect))
        flip_mask = rng.random(len(effect)) < 0.12
        effect[flip_mask] *= -1
        shuffle_mask = rng.random(len(effect)) < 0.25
        effect[shuffle_mask] = rng.permutation(effect[shuffle_mask])
        conversion *= rng.uniform(0.55, 1.25, len(conversion))
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    model["arpu_change_pct"] = np.clip(effect, -1.0, 3.0)
    model["conversion_rate"] = np.clip(conversion, 0.0, 1.0)
    return model


def evaluate(agent, profile, tariffs, impact_model, pilot_seed: int) -> dict:
    env, internals = make_environment(
        customer_profile=profile,
        impact_model=impact_model,
        dict_tariff=tariffs,
        channels=CHANNELS,
        total_budget=TOTAL_BUDGET,
        max_total_contacts=MAX_TOTAL_CONTACTS,
        fallback_predict=_mock_fallback,
        seed=pilot_seed,
    )
    final_campaigns = sanitize_campaigns(agent.act(env), env.tariffs)[:MAX_CAMPAIGNS]
    pilots = internals.executed_pilot_campaigns()
    strategy = pd.DataFrame(pilots + final_campaigns)
    for column in FILTER_COLUMNS:
        if column not in strategy.columns:
            strategy[column] = None
    result = score_campaigns(
        strategy,
        profile,
        impact_model,
        tariffs,
        float(profile["predicted_arpu"].sum()),
        _mock_fallback,
        team_id="stress",
    )
    result["final_campaigns"] = len(final_campaigns)
    result["pilots"] = len(pilots)
    return result


def summarize(values: list[float]) -> dict:
    series = pd.Series(values, dtype=float)
    return {
        "runs": len(series),
        "positive_pct": 100.0 * float((series > 0).mean()),
        "median": float(series.median()),
        "p10": float(series.quantile(0.10)),
        "minimum": float(series.min()),
        "mean": float(series.mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-seeds", type=int, default=5)
    parser.add_argument("--pilot-seeds", type=int, default=10)
    parser.add_argument(
        "--agents",
        default="current",
        help="Comma-separated agent names: current,expanded,broad,diverse,call",
    )
    parser.add_argument(
        "--scenarios",
        default=",".join(SCENARIOS),
        help="Comma-separated scenario names",
    )
    args = parser.parse_args()

    profile = pd.read_csv(CASE_DIR / "customer_profile.csv")
    tariffs = pd.read_csv(CASE_DIR / "data" / "dict_tariff.csv")
    history = pd.read_csv(CASE_DIR / "data" / "change_tariff.csv")
    base = _mock_impact_model(history)

    selected_agents = [name.strip() for name in args.agents.split(",") if name.strip()]
    selected_scenarios = [
        name.strip() for name in args.scenarios.split(",") if name.strip()
    ]
    unknown_agents = set(selected_agents) - set(AGENTS)
    unknown_scenarios = set(selected_scenarios) - set(SCENARIOS)
    if unknown_agents or unknown_scenarios:
        raise ValueError(
            f"Unknown agents={sorted(unknown_agents)}, scenarios={sorted(unknown_scenarios)}"
        )

    rows = []
    for agent_name in selected_agents:
        for scenario in selected_scenarios:
            net_values = []
            for model_seed in range(args.model_seeds):
                model = shifted_model(base, scenario, seed=10_000 + model_seed)
                for pilot_seed in range(args.pilot_seeds):
                    result = evaluate(
                        AGENTS[agent_name](), profile, tariffs, model, pilot_seed
                    )
                    net_values.append(float(result["net_arpu_gain"]))
            rows.append(
                {
                    "agent": agent_name,
                    "scenario": scenario,
                    **summarize(net_values),
                }
            )

    output = pd.DataFrame(rows)
    for column in ["median", "p10", "minimum", "mean"]:
        output[column] = output[column].round(0).astype(int)
    output["positive_pct"] = output["positive_pct"].round(1)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
