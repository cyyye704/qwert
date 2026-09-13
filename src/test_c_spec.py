"""Bottom-layer and causality tests for c建模说明与结果.txt."""
from __future__ import annotations

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
import dispatch_core as core  # noqa: E402
from config import DT, ENERGY_LIMIT, ETA, N, SOC_LOWER, SOC_UPPER  # noqa: E402
from scenario_cache import audit_record  # noqa: E402
from time_axis import all_slot_labels, interval_start_index, right_endpoint_hours  # noqa: E402


def main():
    tests={}
    labels=all_slot_labels()
    expected={0:"0:00-0:10",35:"5:50-6:00",36:"6:00-6:10",60:"10:00-10:10",
              72:"12:00-12:10",108:"18:00-18:10",143:"23:50-0:00+1"}
    assert len(labels)==144 and all(labels[position]==label for position,label in expected.items())
    assert interval_start_index(10)==60 and abs(right_endpoint_hours()[60]-10-1/6)<1e-12
    tests["right_endpoint_time_axis"]=True
    assert abs(5000*DT-ENERGY_LIMIT)<1e-12 and abs(DT-1/6)<1e-12
    tests["power_to_energy_and_interval_limit"]=True

    purchase=np.zeros(N); load=np.zeros(N); pv=np.zeros(N)
    purchase[0]=100; load[1]=600
    executed=core.execute_causal_rule(purchase,load,pv,6000)
    assert abs(executed["charge"][0]-100)<1e-10 and abs(executed["soc"][1]-(6000+ETA*100))<1e-10
    assert abs(executed["discharge"][1]-100)<1e-10 and abs(executed["soc"][2]-(6090-100/ETA))<1e-10
    assert np.max(np.abs(executed["residual"]))<1e-10
    assert executed["charge"].max()<=ENERGY_LIMIT and executed["discharge"].max()<=ENERGY_LIMIT
    assert executed["soc"].min()>=SOC_LOWER and executed["soc"].max()<=SOC_UPPER
    tests["soc_efficiency_bounds_emergency_waste_balance"]=True

    fixed,variable,loads,pvs,dates,forecasts=core.load_data()
    bundle=core.build_causal_forecasts(loads,pvs,variable,dates,forecasts,fixed)
    assert fixed.shape==(144,) and loads.shape==pvs.shape==variable.shape==(365,144)
    tests["attachment_shapes_and_alignment"]=True

    formal=dates>=pd.Timestamp("2025-02-01")
    load_error=bundle.load_day_ahead[formal]-loads[formal]
    assert abs(float(np.mean(np.abs(load_error)))-137.30554657975716)<1e-8
    assert abs(float(np.sqrt(np.mean(load_error**2)))-189.8257485774864)<1e-8
    assert core.day_type(pd.Timestamp("2025-01-03"))==1  # Friday: low load
    assert core.day_type(pd.Timestamp("2025-01-04"))==1  # Saturday: low load
    assert core.day_type(pd.Timestamp("2025-01-05"))==0  # Sunday: ordinary load in Attachment 2
    tests["same_type_day_forecast_definition"]=True

    i=int(np.flatnonzero(dates==pd.Timestamp("2025-02-01"))[0])
    changed_load=loads.copy(); changed_pv=pvs.copy(); changed_price=variable.copy()
    changed_load[i:,60:]*=3; changed_pv[i:,60:]*=.1; changed_price[i:,60:]*=4
    changed=core.build_causal_forecasts(changed_load,changed_pv,changed_price,dates,forecasts,fixed)
    np.testing.assert_allclose(bundle.load_day_ahead[i],changed.load_day_ahead[i],atol=0,rtol=0)
    np.testing.assert_allclose(bundle.pv_history[i],changed.pv_history[i],atol=0,rtol=0)
    np.testing.assert_allclose(bundle.price_day_ahead[i],changed.price_day_ahead[i],atol=0,rtol=0)
    tests["zero_hour_excludes_current_and_future_actuals"]=True

    np.testing.assert_allclose(bundle.load_realtime[6][i],changed.load_realtime[6][i],atol=0,rtol=0)
    np.testing.assert_allclose(bundle.pv_realtime[6][i],changed.pv_realtime[6][i],atol=0,rtol=0)
    original_scenarios=core.scenario_pair(bundle,loads,pvs,i,6,True)
    changed_scenarios=core.scenario_pair(changed,changed_load,changed_pv,i,6,True)
    np.testing.assert_allclose(original_scenarios[0],changed_scenarios[0],atol=0,rtol=0)
    np.testing.assert_allclose(original_scenarios[1],changed_scenarios[1],atol=0,rtol=0)
    tests["six_hour_excludes_future_load_and_pv"]=True

    price_updates=core.price_release_forecasts(variable,bundle.price_day_ahead)
    changed_updates=core.price_release_forecasts(changed_price,bundle.price_day_ahead)
    np.testing.assert_allclose(price_updates[6][i,36:],changed_updates[6][i,36:],atol=1e-14,rtol=0)
    assert np.max(np.abs(price_updates[12][i,72:]-changed_updates[12][i,72:]))>0
    tests["price_updates_use_observed_prefix_only"]=True

    sample=int(np.flatnonzero(dates==pd.Timestamp("2025-03-20"))[0])
    rec=core.run_q2_day(sample,dates,loads,pvs,fixed,bundle,6000.0); audit_record(rec)
    assert abs(rec["actual"]["soc"][-1]-6000)>1e-6
    next_rec=core.run_q2_day(sample+1,dates,loads,pvs,fixed,bundle,float(rec["actual"]["soc"][-1])); audit_record(next_rec)
    assert abs(rec["actual"]["soc"][-1]-next_rec["actual"]["soc"][0])<1e-9
    tests["cross_day_soc_without_terminal_target"]=True

    releases=core.fixed_release_forecasts(fixed,len(dates))
    rolling=core.run_q3_day(sample,dates,loads,pvs,releases,bundle,6000.0,(6,12,18),True); audit_record(rolling)
    assert [u["observed_prefix_end"] for u in rolling["updates"]]==[36,72,108]
    tests["rolling_update_boundaries_and_constraints"]=True

    price=np.full(N,1.0); base=np.full(N,10.0); final=base.copy(); final[50]=8; final[80]=13
    fake={"date":"x","plan":{"purchase":base,"seconds":0},"final_purchase":final,
          "actual":{"charge":np.zeros(N),"discharge":np.zeros(N),"emergency":np.ones(N),"waste":np.zeros(N),
                    "soc":np.full(N+1,6000.0),"residual":np.zeros(N)}}
    metric=core.q3_metrics(fake,price)
    assert abs(metric["adjustment_cost_yuan"]-(-.5*2+1.5*3))<1e-9
    assert abs(metric["emergency_cost_yuan"]-5*N)<1e-9
    tests["settlement_formula"]=True

    out=ROOT/"results/c_spec_unit_tests.json"; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(tests,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
