"""Read-only demo API for the Sergeek Campaign Agent dashboard."""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "beeline_case_participants (1)"
sys.path.insert(0, str(CASE_DIR))

from agent import Agent  # noqa: E402
from mock_environment import (  # noqa: E402
    CHANNELS,
    MAX_TOTAL_CONTACTS,
    TOTAL_BUDGET,
    _mock_fallback,
    _mock_impact_model,
    make_mock_env,
)
from scoring_core import (  # noqa: E402
    MAX_CAMPAIGNS,
    MAX_CUSTOMERS_PER_CAMPAIGN,
    score_campaigns,
    sanitize_campaigns,
)


app = FastAPI(
    title="Sergeek Campaign Agent API",
    version="0.1.0",
    description="Demo API backed by the official local mock environment.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    runs: int = Field(default=10, ge=1, le=100)
    seed_start: int = Field(default=0, ge=0, le=1_000_000)


_latest_lock = Lock()
_latest_summary = {
    "runs": 100,
    "positive_runs": 100,
    "median_net": 3_628_771.0,
    "min_net": 2_021_670.0,
    "max_net": 4_107_664.0,
    "mean_net": None,
    "seed_start": 0,
    "source": "verified local mock run",
    "is_mock": True,
}


def _make_env(seed: int):
    return make_mock_env(
        seed=seed,
        data_dir=str(CASE_DIR / "data"),
        profile_path=str(CASE_DIR / "customer_profile.csv"),
    )


def _run_agent(seed: int) -> dict:
    env, internals = _make_env(seed)
    final_campaigns = sanitize_campaigns(Agent().act(env), env.tariffs)[:MAX_CAMPAIGNS]
    pilot_campaigns = internals.executed_pilot_campaigns()
    all_campaigns = pd.DataFrame(pilot_campaigns + final_campaigns)
    for column in [
        "filter_arpu_segment",
        "filter_data_segment",
        "filter_call_segment",
        "filter_current_tariff",
        "explicit_ids",
    ]:
        if column not in all_campaigns.columns:
            all_campaigns[column] = None

    profile = env.customer_profile
    impact_model = _mock_impact_model(pd.read_csv(CASE_DIR / "data" / "change_tariff.csv"))
    result = score_campaigns(
        all_campaigns,
        profile,
        impact_model,
        env.tariffs,
        float(profile["predicted_arpu"].sum()),
        _mock_fallback,
        team_id="sergeek",
    )

    pilot_history = []
    for campaign, observation in zip(pilot_campaigns, env.pilot_history):
        pilot_history.append({
            "name": campaign["campaign_name"],
            "current_tariff": campaign.get("filter_current_tariff"),
            "arpu_segment": campaign.get("filter_arpu_segment"),
            "target_tariff": campaign["target_tariff"],
            "channel": campaign["channel"],
            "customers": observation["n_customers"],
            "observed_lift_ratio": observation["observed_lift_ratio"],
            "cost": observation["cost"],
        })

    final_details = result["campaigns_detail"][len(pilot_campaigns):]
    campaigns = []
    for campaign, detail in zip(final_campaigns, final_details):
        campaigns.append({
            "campaign_name": campaign["campaign_name"],
            "current_tariff": campaign.get("filter_current_tariff"),
            "arpu_segment": campaign.get("filter_arpu_segment"),
            "target_tariff": campaign["target_tariff"],
            "channel": campaign["channel"],
            "audience_size": detail["n_contacts"],
            "communication_cost": detail["cost"],
            "gross_lift": detail["gross_lift"],
            "net_gain": detail["gross_lift"] - detail["cost"],
            "status": "selected",
        })

    return {
        "seed": seed,
        "result": result,
        "campaigns": campaigns,
        "pilots": pilot_history,
        "final_campaign_count": len(final_campaigns),
        "pilot_count": len(pilot_campaigns),
    }


def _public_result(run: dict) -> dict:
    result = run["result"]
    return {
        "seed": run["seed"],
        "status": result["status"],
        "baseline_arpu": result["baseline_total_arpu"],
        "gross_lift": result["gross_arpu_lift"],
        "total_cost": result["total_cost"],
        "net_gain": result["net_arpu_gain"],
        "growth_pct": result["growth_vs_baseline_pct"],
        "total_contacts": result["total_contacts"],
        "unique_customers": result["unique_customers_targeted"],
        "roi": result["roi"],
        "risk_score_pct": result["risk_score_pct"],
        "pilot_count": run["pilot_count"],
        "final_campaign_count": run["final_campaign_count"],
        "is_mock": True,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "sergeek-api"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    run = _run_agent(seed=42)
    return {
        **_public_result(run),
        "limits": {
            "budget": TOTAL_BUDGET,
            "contacts": MAX_TOTAL_CONTACTS,
            "pilots": 20,
            "campaigns": MAX_CAMPAIGNS,
            "customers_per_campaign": MAX_CUSTOMERS_PER_CAMPAIGN,
        },
        "channels": CHANNELS,
        "audience_size": len(_make_env(42)[0].customer_profile),
        "disclaimer": "Local mock simulation; final judging uses hidden effects.",
    }


@app.get("/api/campaigns")
def campaigns(seed: int = 42) -> dict:
    run = _run_agent(seed)
    return {"seed": seed, "items": run["campaigns"], "is_mock": True}


@app.get("/api/pilots")
def pilots(seed: int = 42) -> dict:
    run = _run_agent(seed)
    return {"seed": seed, "items": run["pilots"], "is_mock": True}


@app.get("/api/simulations/latest")
def latest_simulation() -> dict:
    with _latest_lock:
        return dict(_latest_summary)


@app.post("/api/simulations/run")
def run_simulations(request: SimulationRequest) -> dict:
    try:
        values = [
            _run_agent(seed)["result"]["net_arpu_gain"]
            for seed in range(request.seed_start, request.seed_start + request.runs)
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc

    series = pd.Series(values, dtype=float)
    summary = {
        "runs": request.runs,
        "positive_runs": int((series > 0).sum()),
        "median_net": float(series.median()),
        "min_net": float(series.min()),
        "max_net": float(series.max()),
        "mean_net": float(series.mean()),
        "seed_start": request.seed_start,
        "values": values,
        "source": "live local mock run",
        "is_mock": True,
    }
    with _latest_lock:
        _latest_summary.clear()
        _latest_summary.update(summary)
    return summary
