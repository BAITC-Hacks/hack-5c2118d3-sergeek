"""Build robust tariff-transition priors from the supplied history.

This module is intentionally offline-only. It lets us compare an automatic
shortlist with the hand-curated production priors before changing agent.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ARPU_BINS = [-np.inf, 1000, 5000, np.inf]
ARPU_LABELS = ["LOW", "MID", "HIGH"]


def generate_candidates(
    history: pd.DataFrame,
    profile: pd.DataFrame,
    tariffs: pd.DataFrame,
    *,
    limit: int = 30,
    effect_prior_strength: float = 25.0,
    conversion_prior_strength: float = 20.0,
) -> pd.DataFrame:
    """Return automatically ranked candidate transitions with shrinkage."""
    required_history = {
        "AVG_ARPU_PREV_3M",
        "AVG_ARPU_NEXT_3M",
        "ID_NUMBER",
        "tariff_plan_code_from",
        "tariff_plan_code_to",
    }
    required_profile = {
        "current_tariff",
        "arpu_segment",
        "predicted_arpu",
    }
    required_tariffs = {
        "tariff_plan_code",
        "Data_in_PKG",
        "Min_another_operator_in_PKG",
        "Min_another_operator_and_city_in_PKG",
    }
    if missing := required_history - set(history.columns):
        raise ValueError(f"History is missing columns: {sorted(missing)}")
    if missing := required_profile - set(profile.columns):
        raise ValueError(f"Profile is missing columns: {sorted(missing)}")
    if missing := required_tariffs - set(tariffs.columns):
        raise ValueError(f"Tariffs are missing columns: {sorted(missing)}")

    clean = history.copy()
    clean = clean[clean["AVG_ARPU_PREV_3M"] >= 100].copy()
    clean["arpu_segment"] = pd.cut(
        clean["AVG_ARPU_PREV_3M"], bins=ARPU_BINS, labels=ARPU_LABELS
    )
    clean["arpu_change_pct"] = (
        (clean["AVG_ARPU_NEXT_3M"] - clean["AVG_ARPU_PREV_3M"])
        / clean["AVG_ARPU_PREV_3M"]
    ).clip(-1, 3)
    clean = clean.dropna(
        subset=[
            "tariff_plan_code_from",
            "tariff_plan_code_to",
            "arpu_segment",
            "arpu_change_pct",
        ]
    )

    keys = ["tariff_plan_code_from", "tariff_plan_code_to", "arpu_segment"]
    grouped = (
        clean.groupby(keys, observed=True)
        .agg(
            historical_effect=("arpu_change_pct", "mean"),
            historical_count=("ID_NUMBER", "size"),
        )
        .reset_index()
    )
    cell_keys = ["tariff_plan_code_from", "arpu_segment"]
    cell = (
        clean.groupby(cell_keys, observed=True)
        .agg(
            cell_effect=("arpu_change_pct", "mean"),
            cell_total=("ID_NUMBER", "size"),
        )
        .reset_index()
    )
    grouped = grouped.merge(cell, on=cell_keys, validate="many_to_one")

    target_prior = clean["tariff_plan_code_to"].value_counts(normalize=True)
    grouped["target_prior"] = grouped["tariff_plan_code_to"].map(target_prior).fillna(0.0)
    grouped["shrunk_effect"] = (
        grouped["historical_count"] * grouped["historical_effect"]
        + effect_prior_strength * grouped["cell_effect"]
    ) / (grouped["historical_count"] + effect_prior_strength)
    grouped["shrunk_conversion"] = (
        grouped["historical_count"]
        + conversion_prior_strength * grouped["target_prior"]
    ) / (grouped["cell_total"] + conversion_prior_strength)
    grouped["prior_push_lift"] = (
        grouped["shrunk_effect"] * grouped["shrunk_conversion"] * 0.50
    )

    audience = (
        profile.dropna(subset=["current_tariff", "arpu_segment", "predicted_arpu"])
        .groupby(["current_tariff", "arpu_segment"], observed=True)
        .agg(
            audience_size=("predicted_arpu", "size"),
            audience_arpu=("predicted_arpu", "sum"),
        )
        .reset_index()
        .rename(columns={"current_tariff": "tariff_plan_code_from"})
    )
    grouped = grouped.merge(audience, on=cell_keys, how="inner", validate="many_to_one")

    package_columns = [
        "Data_in_PKG",
        "Min_another_operator_in_PKG",
        "Min_another_operator_and_city_in_PKG",
    ]
    package = tariffs.set_index("tariff_plan_code")[package_columns].astype(float)

    def package_compatibility(row: pd.Series) -> float:
        source = row["tariff_plan_code_from"]
        target = row["tariff_plan_code_to"]
        if source not in package.index or target not in package.index:
            return 0.0
        source_values = package.loc[source].to_numpy(dtype=float)
        target_values = package.loc[target].to_numpy(dtype=float)
        scale = np.maximum(np.maximum(source_values, target_values), 1.0)
        return float(np.mean(np.clip((target_values - source_values) / scale, -1, 1)))

    grouped["package_compatibility"] = grouped.apply(package_compatibility, axis=1)
    reachable_arpu = grouped["audience_arpu"] * np.minimum(
        1.0, 5000.0 / grouped["audience_size"].clip(lower=1)
    )
    base_value = grouped["prior_push_lift"] * reachable_arpu
    grouped["ranking_score"] = base_value * (
        1.0 + 0.05 * grouped["package_compatibility"]
    )

    known_tariffs = set(tariffs["tariff_plan_code"])
    grouped = grouped[
        grouped["tariff_plan_code_from"].isin(known_tariffs)
        & grouped["tariff_plan_code_to"].isin(known_tariffs)
        & (grouped["tariff_plan_code_from"] != grouped["tariff_plan_code_to"])
        & (grouped["prior_push_lift"] > 0)
    ].copy()
    grouped["arpu_segment"] = grouped["arpu_segment"].astype(str)
    grouped = grouped.sort_values(
        ["ranking_score", "historical_count"], ascending=[False, False]
    ).head(limit)
    return grouped.reset_index(drop=True)


def candidate_tuples(candidates: pd.DataFrame) -> list[tuple[str, str, str]]:
    return list(
        candidates[
            ["tariff_plan_code_from", "arpu_segment", "tariff_plan_code_to"]
        ].itertuples(index=False, name=None)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    case_dir = root / "beeline_case_participants (1)"
    generated = generate_candidates(
        pd.read_csv(case_dir / "data" / "change_tariff.csv"),
        pd.read_csv(case_dir / "customer_profile.csv"),
        pd.read_csv(case_dir / "data" / "dict_tariff.csv"),
        limit=args.limit,
    )
    columns = [
        "tariff_plan_code_from",
        "arpu_segment",
        "tariff_plan_code_to",
        "historical_count",
        "shrunk_effect",
        "shrunk_conversion",
        "prior_push_lift",
        "ranking_score",
    ]
    print(generated[columns].to_string(index=False))


if __name__ == "__main__":
    main()
