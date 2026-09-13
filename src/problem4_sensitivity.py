"""Separate Q4 intraday price-volatility sensitivity experiment.

This module does not change the main Q4 calculation.  It creates counterfactual
price paths with the same daily arithmetic mean and scaled log-price
deviations, then runs the unchanged causal Q4-2 and Q4-3 pipelines.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import dispatch_core as core  # noqa: E402
from config import MODEL_VERSION  # noqa: E402
from reporting import annual_summary, write_json  # noqa: E402
from scenario_cache import run_continuous  # noqa: E402

FACTORS = (0.50, 0.75, 1.00, 1.25, 1.50)
METHOD = "daily centered log-price deviations scaled; daily arithmetic mean restored"


def stress_prices(actual: np.ndarray, factor: float) -> np.ndarray:
    """Scale intraday volatility while preserving each day's arithmetic mean."""
    price = np.asarray(actual, dtype=float)
    if price.ndim != 2 or not np.isfinite(price).all() or np.any(price <= 0):
        raise AssertionError("actual prices must be a finite positive day-by-slot matrix")
    if factor <= 0:
        raise AssertionError("volatility factor must be positive")
    if factor == 1.0:
        return price.copy()
    daily_mean = price.mean(axis=1, keepdims=True)
    log_price = np.log(price)
    centered = log_price - log_price.mean(axis=1, keepdims=True)
    stressed = np.exp(factor * centered)
    stressed *= daily_mean / stressed.mean(axis=1, keepdims=True)
    if not np.isfinite(stressed).all() or np.any(stressed <= 0):
        raise AssertionError(f"invalid stressed price path for factor={factor}")
    np.testing.assert_allclose(stressed.mean(axis=1), daily_mean[:, 0], rtol=0, atol=2e-15)
    return stressed


def _formal(records_all: list[dict], ids: list[int], prices: np.ndarray, rolling: bool):
    records = [records_all[i] for i in ids]
    metric = core.q3_metrics if rolling else core.q2_metrics
    frame = pd.DataFrame([metric(record, prices[i]) for record, i in zip(records, ids)])
    return annual_summary(frame, records)


def _run_factor(factor: float, data, use_cache: bool) -> dict:
    fixed, variable, load, pv, dates, forecasts = data
    stressed = stress_prices(variable, factor)
    bundle = core.build_causal_forecasts(load, pv, stressed, dates, forecasts, fixed)
    releases = core.price_release_forecasts(stressed, bundle.price_day_ahead)
    token = f"f{int(round(factor * 100)):03d}"
    if factor == 1.0:
        q2_label = "q4_causal_q2"
        q2_options = {"model": MODEL_VERSION, "price": "causal"}
        q3_label = "q4_causal_q3"
        q3_options = {"model": MODEL_VERSION, "price": "causal", "updates": [6, 12, 18], "recourse": True}
    else:
        common = {"model": MODEL_VERSION, "experiment": "q4_price_volatility_v1",
                  "volatility_factor": factor, "transformation": METHOD}
        q2_label = f"q4_sensitivity_q2_{token}"
        q2_options = {**common, "scheme": "causal_q4_2"}
        q3_label = f"q4_sensitivity_q3_{token}"
        q3_options = {**common, "scheme": "causal_q4_3", "updates": [6, 12, 18], "recourse": True}

    q2_all = run_continuous(
        q2_label, q2_options, len(dates) - 1,
        lambda i, soc: core.run_q2_day(i, dates, load, pv, releases[0][i], bundle, soc),
        use_cache=use_cache,
    )
    q3_all = run_continuous(
        q3_label, q3_options, len(dates) - 1,
        lambda i, soc: core.run_q3_day(i, dates, load, pv, releases, bundle, soc, (6, 12, 18), True),
        use_cache=use_cache,
    )
    ids = core.decision_indices(dates)
    q2 = _formal(q2_all, ids, stressed, False)
    q3 = _formal(q3_all, ids, stressed, True)
    daily_mean_error = float(np.max(np.abs(stressed.mean(axis=1) - variable.mean(axis=1))))
    mean_cv = float(np.mean(stressed.std(axis=1) / stressed.mean(axis=1)))
    return {
        "volatility_factor": factor,
        "mean_daily_price_cv": mean_cv,
        "maximum_daily_mean_price_error_yuan_per_kwh": daily_mean_error,
        "minimum_stressed_price_yuan_per_kwh": float(stressed.min()),
        "maximum_stressed_price_yuan_per_kwh": float(stressed.max()),
        "q4_2_total_cost_yuan": q2["total_cost_yuan"],
        "q4_2_plan_cost_yuan": q2["plan_cost_yuan"],
        "q4_2_emergency_cost_yuan": q2["emergency_cost_yuan"],
        "q4_2_emergency_kwh": q2["emergency_kwh"],
        "q4_3_total_cost_yuan": q3["total_cost_yuan"],
        "q4_3_plan_cost_yuan": q3["plan_cost_yuan"],
        "q4_3_adjustment_cost_yuan": q3["adjustment_cost_yuan"],
        "q4_3_emergency_cost_yuan": q3["emergency_cost_yuan"],
        "q4_3_emergency_kwh": q3["emergency_kwh"],
        "q4_2_cross_day_soc_continuous": q2["cross_day_soc_continuous"],
        "q4_3_cross_day_soc_continuous": q3["cross_day_soc_continuous"],
        "q4_2_max_balance_residual_kwh": q2["max_balance_residual_kwh"],
        "q4_3_max_balance_residual_kwh": q3["max_balance_residual_kwh"],
    }


def _plot(frame: pd.DataFrame) -> str:
    baseline = frame.loc[np.isclose(frame.volatility_factor, 1.0)].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    axes[0].plot(frame.volatility_factor, frame.q4_2_total_cost_yuan / 1e4, marker="o", label="Q4-2")
    axes[0].plot(frame.volatility_factor, frame.q4_3_total_cost_yuan / 1e4, marker="s", label="Q4-3")
    axes[0].set(xlabel="电价日内波动系数", ylabel="全年总费用（万元）", xticks=list(FACTORS))
    axes[0].legend()
    axes[1].plot(frame.volatility_factor,
                 (frame.q4_2_total_cost_yuan / baseline.q4_2_total_cost_yuan - 1) * 100,
                 marker="o", label="Q4-2")
    axes[1].plot(frame.volatility_factor,
                 (frame.q4_3_total_cost_yuan / baseline.q4_3_total_cost_yuan - 1) * 100,
                 marker="s", label="Q4-3")
    axes[1].axhline(0, color="#666666", linestyle=":", linewidth=1)
    axes[1].set(xlabel="电价日内波动系数", ylabel="相对基准费用变化（%）", xticks=list(FACTORS))
    axes[1].legend()
    path = ROOT / "figures" / "P4_price_volatility_sensitivity.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return str(path.relative_to(ROOT))


def run_problem4_sensitivity(use_cache: bool = True, data=None) -> dict:
    if data is None:
        data = core.load_data()
    rows = []
    for factor in FACTORS:
        print(f"Q4电价波动灵敏度: {factor:.2f}", flush=True)
        rows.append(_run_factor(factor, data, use_cache))
    frame = pd.DataFrame(rows)
    baseline = frame.loc[np.isclose(frame.volatility_factor, 1.0)].iloc[0]
    q4 = json.loads((ROOT / "results" / "problem4.json").read_text(encoding="utf-8"))
    q4_rows = {row["scenario"]: row for row in q4["scenarios"]}
    q2_error = abs(float(baseline.q4_2_total_cost_yuan) - q4_rows["causal Q4-2"]["total_cost_yuan"])
    q3_error = abs(float(baseline.q4_3_total_cost_yuan) - q4_rows["causal Q4-3"]["total_cost_yuan"])
    assert q2_error < 1e-8 and q3_error < 1e-8
    assert frame.maximum_daily_mean_price_error_yuan_per_kwh.max() < 3e-15
    assert frame.minimum_stressed_price_yuan_per_kwh.min() > 0
    assert frame[["q4_2_cross_day_soc_continuous", "q4_3_cross_day_soc_continuous"]].to_numpy().all()
    assert frame[["q4_2_max_balance_residual_kwh", "q4_3_max_balance_residual_kwh"]].to_numpy().max() < 1e-7

    figure = _plot(frame)
    frame.to_csv(ROOT / "results" / "problem4_price_volatility_sensitivity.csv", index=False, encoding="utf-8-sig")
    payload = {
        "run_id": os.environ.get("FINAL_RUN_ID", "unbound-manual-run"),
        "model_version": MODEL_VERSION,
        "experiment": "Q4 intraday price-volatility sensitivity",
        "status": "separate counterfactual stress test; main Q4 results are unchanged",
        "transformation": METHOD,
        "controls": {
            "daily_arithmetic_mean_price_preserved": True,
            "load_pv_soc_prediction_dispatch_and_settlement_logic_unchanged": True,
            "causal_information_policy_recomputed_for_each_stressed_price_world": True,
        },
        "factors": list(FACTORS),
        "baseline_match": {
            "q4_2_absolute_error_yuan": q2_error,
            "q4_3_absolute_error_yuan": q3_error,
            "pass": True,
        },
        "rows": frame.to_dict("records"),
        "figures": [figure],
    }
    write_json(ROOT / "results" / "problem4_price_volatility_sensitivity.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    run_problem4_sensitivity()
