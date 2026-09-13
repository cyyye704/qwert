"""Stage-B isolated typical-day validation before any annual run."""
from __future__ import annotations

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
import dispatch_core as core  # noqa: E402
from config import SOC_INITIAL, SPECIFIED  # noqa: E402
from scenario_cache import audit_record  # noqa: E402


def _payload(record,metric):
    a=record["actual"]
    return {"metrics":metric,"plan_purchase_kwh":record["plan"]["purchase"].tolist(),
        "final_purchase_kwh":record["final_purchase"].tolist(),"charge_kwh":a["charge"].tolist(),
        "discharge_kwh":a["discharge"].tolist(),"soc_kwh":a["soc"].tolist(),
        "emergency_kwh":a["emergency"].tolist(),"waste_kwh":a["waste"].tolist(),
        "energy_balance_max_abs_kwh":float(np.abs(a["residual"]).max())}


def main():
    fixed,variable,load,pv,dates,forecasts=core.load_data()
    bundle=core.build_causal_forecasts(load,pv,variable,dates,forecasts,fixed)
    fixed_releases=core.fixed_release_forecasts(fixed,len(dates))
    causal_releases=core.price_release_forecasts(variable,bundle.price_day_ahead)
    output={"note":"阶段B为隔离典型日检查，统一以SOC=6000启动；正式结果使用1月热身及逐日SOC连续传递。","days":{}}
    for date in SPECIFIED:
        i=int(np.flatnonzero(dates==pd.Timestamp(date))[0])
        q2=core.run_q2_day(i,dates,load,pv,fixed,bundle,SOC_INITIAL)
        q3=core.run_q3_day(i,dates,load,pv,fixed_releases,bundle,SOC_INITIAL,(6,12,18),True)
        q42=core.run_q2_day(i,dates,load,pv,causal_releases[0][i],bundle,SOC_INITIAL)
        q43=core.run_q3_day(i,dates,load,pv,causal_releases,bundle,SOC_INITIAL,(6,12,18),True)
        for r in (q2,q3,q42,q43): audit_record(r)
        output["days"][date]={"q2":_payload(q2,core.q2_metrics(q2,fixed)),
            "q3":_payload(q3,core.q3_metrics(q3,fixed)),
            "q4_2_causal":_payload(q42,core.q2_metrics(q42,variable[i])),
            "q4_3_causal":_payload(q43,core.q3_metrics(q43,variable[i]))}
    path=ROOT/"results/c_spec_typical_day_validation.json"; path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({d:{k:round(v["metrics"]["total_cost_yuan"],2) for k,v in x.items()} for d,x in output["days"].items()},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
