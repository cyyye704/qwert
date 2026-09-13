"""Q2: stochastic day-ahead purchase plus causal rule dispatch."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
import dispatch_core as core  # noqa: E402
from config import (MODEL_VERSION, RESIDUAL_SCENARIOS, SOC_SAFETY_MARGIN_KWH,
                    TERMINAL_VALUE_YUAN_PER_KWH)  # noqa: E402
from reporting import annual_summary, plot_typical, typical_day_payload, write_json  # noqa: E402
from result_workbooks import export_records  # noqa: E402
from scenario_cache import run_continuous  # noqa: E402


def run_problem2(use_cache: bool=True, data=None, bundle=None):
    if data is None:
        data=core.load_data()
    fixed,variable,load,pv,dates,forecasts=data
    if bundle is None:
        bundle=core.build_causal_forecasts(load,pv,variable,dates,forecasts,fixed)
    records_all=run_continuous("q2_fixed",{"model":MODEL_VERSION,"price":"attachment1"},len(dates)-1,
        lambda i,soc: core.run_q2_day(i,dates,load,pv,fixed,bundle,soc),use_cache=use_cache)
    ids=core.decision_indices(dates); records=[records_all[i] for i in ids]
    frame=pd.DataFrame([core.q2_metrics(r,fixed) for r in records])
    (ROOT/"results").mkdir(exist_ok=True); frame.to_csv(ROOT/"results/problem2_daily.csv",index=False,encoding="utf-8-sig")
    summary={"model_version":MODEL_VERSION,
        "method":"日前预测 + 最近10日残差场景 + 两阶段随机LP + 300kWh安全裕度 + 因果规则调度",
        "parameters":{"residual_scenarios":RESIDUAL_SCENARIOS,"soc_safety_margin_kwh":SOC_SAFETY_MARGIN_KWH,
                      "terminal_value_yuan_per_kwh":TERMINAL_VALUE_YUAN_PER_KWH,
                      "load_forecast":"最近3个同类型日均值","pv_forecast":"最近5日均值"},
        "forecast_accuracy":{"load_mae_kw":float(np.mean(np.abs(bundle.load_day_ahead[ids]-load[ids]))),
                             "load_rmse_kw":float(np.sqrt(np.mean((bundle.load_day_ahead[ids]-load[ids])**2))),
                             "pv_mae_kw":float(np.mean(np.abs(bundle.pv_history[ids]-pv[ids]))),
                             "pv_rmse_kw":float(np.sqrt(np.mean((bundle.pv_history[ids]-pv[ids])**2)))},
        "annual":annual_summary(frame,records),"typical_days":typical_day_payload(records,frame)}
    summary["figures"]=plot_typical(records,load,pv,dates,"P2")
    write_json(ROOT/"results/problem2.json",summary)
    export_records(records,frame,"result2.xlsx",rolling=False)
    return records_all,records,frame,summary,bundle,(fixed,variable,load,pv,dates,forecasts)


def main():
    _,_,_,summary,_,_=run_problem2()
    print(summary["annual"])


if __name__=="__main__": main()
