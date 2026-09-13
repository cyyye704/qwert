"""Audit Q3 forecast timestamps, executed-prefix locking, and cross-day use."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

import dispatch_core as core
from config import RELEASES, SOC_INITIAL, STEPS_PER_HOUR


def main() -> None:
    fixed, variable, load, pv, dates, forecasts = core.load_data()
    date = pd.Timestamp("2025-03-20")
    i = int(np.flatnonzero(dates == date)[0])
    key_date = date.strftime("%Y-%m-%d")

    endpoint_checks = []
    for release in RELEASES:
        values = forecasts[(key_date, release)]
        observed = 0.0 if release == 0 else float(pv[i, release * STEPS_PER_HOUR - 1])
        grid = core.attachment_forecast_to_grid(values, release, observed)
        usable = 24 - release
        for lead in range(1, usable + 1):
            slot = (release + lead) * STEPS_PER_HOUR - 1
            assert grid[slot] == values[lead - 1]
        endpoint_checks.append({
            "release": f"{release:02d}:00",
            "lead_1_endpoint": str(date + pd.Timedelta(hours=release + 1)),
            "lead_6_endpoint": str(date + pd.Timedelta(hours=release + 6)),
            "lead_24_endpoint": str(date + pd.Timedelta(hours=release + 24)),
            "same_day_leads_used": usable,
            "cross_day_leads_discarded": 24 - usable,
        })

    bundle = core.build_causal_forecasts(load, pv, variable, dates, forecasts, fixed)
    release_prices = core.fixed_release_forecasts(fixed, len(dates))
    base = core.run_q3_day(
        i, dates, load, pv, release_prices, bundle, SOC_INITIAL,
        update_hours=(6, 12, 18), recourse_plan=True,
    )
    prefix_checks = []
    for release, next_release in zip(RELEASES[1:], (*RELEASES[2:], 24)):
        cut = release * STEPS_PER_HOUR
        end = next_release * STEPS_PER_HOUR
        probes = []
        for replacement in (0.0, 5000.0):
            realtime = dict(bundle.pv_realtime)
            changed_release = realtime[release].copy()
            changed_release[i, cut:] = replacement
            realtime[release] = changed_release
            changed_bundle = replace(bundle, pv_realtime=realtime)
            trial = core.run_q3_day(
                i, dates, load, pv, release_prices, changed_bundle, SOC_INITIAL,
                update_hours=(6, 12, 18), recourse_plan=True,
            )
            probes.append((
                float(np.max(np.abs(base["final_purchase"][:cut] - trial["final_purchase"][:cut]))),
                float(np.max(np.abs(base["final_purchase"][cut:end] - trial["final_purchase"][cut:end]))),
            ))
        prefix_delta = max(x[0] for x in probes)
        segment_delta = max(x[1] for x in probes)
        assert prefix_delta == 0.0
        prefix_checks.append({"release": f"{release:02d}:00", "executed_prefix_max_change_kwh": prefix_delta,
                              "next_segment_max_change_kwh": segment_delta,
                              "note": "The executed prefix is invariant; suffix sensitivity is reported rather than required because storage and surplus can absorb a forecast perturbation."})

    cross_day = dict(forecasts)
    changed_18 = forecasts[(key_date, 18)].copy()
    changed_18[6:] += 10000.0
    cross_day[(key_date, 18)] = changed_18
    changed_bundle = core.build_causal_forecasts(load, pv, variable, dates, cross_day, fixed)
    cross_day_trial = core.run_q3_day(
        i, dates, load, pv, release_prices, changed_bundle, SOC_INITIAL,
        update_hours=(6, 12, 18), recourse_plan=True,
    )
    cross_day_effect = float(np.max(np.abs(base["final_purchase"] - cross_day_trial["final_purchase"])))
    assert cross_day_effect == 0.0

    out = {
        "conclusion": "The implementation matches the problem's day-bounded purchasing strategy: hourly endpoints and executed-prefix locking are correct, and forecasts after midnight are left to the next day's 00:00 plan.",
        "problem_statement_basis": "Problem 3 asks for the current day's planned and adjusted purchasing strategy, while Attachment 3 supplies the next 24 hourly forecast points.",
        "hourly_endpoint_mapping": endpoint_checks,
        "executed_prefix_checks": prefix_checks,
        "first_hour_resampling_policy": "Before the first +1 h point, its value is held constant; later 10-minute points are linearly interpolated.",
        "cross_day_test": {
            "mutation": "Changed only leads 7-24 of the 18:00 forecast, which correspond to next-day 01:00-18:00.",
            "maximum_change_in_current_day_decisions_kwh": cross_day_effect,
            "finding": "These values do not enter the current-day optimization and cannot leak into past decisions; the next day uses its own 00:00 forecast.",
        },
        "model_scope": "Each update optimizes the remaining part of the current day; this follows the problem's repeated requirement to formulate the current day's purchasing strategy.",
        "verdict": "No Q3 timestamp or cross-day leakage defect was found. The first-hour 10-minute resampling rule is a documented modeling choice because the problem supplies only hourly forecast points.",
    }
    path = ROOT / "results" / "q3_forecast_alignment_audit.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
