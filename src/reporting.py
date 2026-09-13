"""Shared summaries and figures for the c-spec implementation."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd

mpl.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
mpl.rcParams["axes.unicode_minus"] = False

from config import CAPACITY_KWH, DT, ENERGY_LIMIT, SOC_LOWER, SOC_UPPER, SPECIFIED

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/"figures"; RES=ROOT/"results"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


def annual_summary(frame: pd.DataFrame, records: list[dict]) -> dict:
    continuous=all(abs(a["actual"]["soc"][-1]-b["actual"]["soc"][0])<1e-7 for a,b in zip(records,records[1:]))
    return {"days":int(len(frame)),"total_cost_yuan":float(frame.total_cost_yuan.sum()),
        "plan_cost_yuan":float(frame.plan_cost_yuan.sum()),
        "adjustment_cost_yuan":float(frame.adjustment_cost_yuan.sum()),
        "emergency_cost_yuan":float(frame.emergency_cost_yuan.sum()),
        "plan_kwh":float(frame.plan_kwh.sum()),"final_purchase_kwh":float(frame.final_purchase_kwh.sum()),
        "emergency_kwh":float(frame.emergency_kwh.sum()),"emergency_days":int((frame.emergency_kwh>1e-8).sum()),
        "waste_kwh":float(frame.waste_kwh.sum()),"charge_kwh":float(frame.charge_kwh.sum()),
        "discharge_kwh":float(frame.discharge_kwh.sum()),
        "average_daily_storage_throughput_percent":float(
            (frame.charge_kwh.sum()+frame.discharge_kwh.sum())/len(frame)/CAPACITY_KWH*100),
        "annual_equivalent_full_cycles":float(
            (frame.charge_kwh.sum()+frame.discharge_kwh.sum())/(2*CAPACITY_KWH)),
        "soc_min_kwh":float(frame.soc_min_kwh.min()),"soc_max_kwh":float(frame.soc_max_kwh.max()),
        "max_charge_kwh":float(frame.max_charge_kwh.max()),"max_discharge_kwh":float(frame.max_discharge_kwh.max()),
        "max_balance_residual_kwh":float(frame.balance_max_abs_kwh.max()),
        "simultaneous_charge_discharge_periods":int(frame.simultaneous_charge_discharge_periods.sum()),
        "cross_day_soc_continuous":bool(continuous),"solve_seconds":float(frame.solve_seconds.sum())}


def typical_day_payload(records: list[dict], frame: pd.DataFrame) -> dict:
    by_date={r["date"]:r for r in records}; indexed=frame.set_index("date")
    payload={}
    for date in SPECIFIED:
        r=by_date[date]; m=indexed.loc[date]
        payload[date]={"metrics":{k:(int(v) if isinstance(v,(np.integer,)) else float(v) if isinstance(v,(np.floating,float)) else v) for k,v in m.items()},
            "plan_purchase_kwh":r["plan"]["purchase"].tolist(),"final_purchase_kwh":r["final_purchase"].tolist(),
            "charge_kwh":r["actual"]["charge"].tolist(),"discharge_kwh":r["actual"]["discharge"].tolist(),
            "soc_kwh":r["actual"]["soc"].tolist(),"emergency_kwh":r["actual"]["emergency"].tolist(),
            "waste_kwh":r["actual"]["waste"].tolist()}
    return payload


def plot_typical(records: list[dict], load: np.ndarray, pv: np.ndarray,
                 dates: pd.DatetimeIndex, prefix: str) -> list[str]:
    FIG.mkdir(parents=True,exist_ok=True); index={d.strftime("%Y-%m-%d"):i for i,d in enumerate(dates)}
    recs={r["date"]:r for r in records}; outputs=[]; x=np.arange(144)/6
    for date in SPECIFIED:
        r=recs[date]; i=index[date]; a=r["actual"]
        fig,axes=plt.subplots(2,1,figsize=(11,6.8),sharex=True,constrained_layout=True)
        axes[0].plot(x,load[i]*DT,label="实际负载",lw=1.1)
        axes[0].plot(x,pv[i]*DT,label="实际光伏",lw=1.1)
        axes[0].plot(x,r["plan"]["purchase"],label="0时计划购电",lw=1.0)
        axes[0].plot(x,r["final_purchase"],label="最终购电",lw=1.0,ls="--")
        axes[0].bar(x,a["emergency"],width=1/6,color="#d62728",alpha=.45,label="紧急购电")
        axes[0].bar(x,-a["waste"],width=1/6,color="#7f7f7f",alpha=.35,label="弃电")
        axes[0].set_ylabel("区间电量 (kWh)"); axes[0].legend(ncol=3,fontsize=8)
        axes[1].plot(np.arange(145)/6,a["soc"],color="#2ca02c",label="SOC")
        axes[1].fill_between(x,0,a["charge"],step="post",alpha=.35,label="充电")
        axes[1].fill_between(x,0,-a["discharge"],step="post",alpha=.35,label="放电")
        axes[1].axhline(SOC_LOWER,color="gray",ls=":"); axes[1].axhline(SOC_UPPER,color="gray",ls=":")
        axes[1].set(xlabel="时刻 (h)",ylabel="SOC / 充放电 (kWh)",xlim=(0,24)); axes[1].legend(ncol=3,fontsize=8)
        path=FIG/f"{prefix}_{date}.png"; fig.savefig(path,dpi=220); plt.close(fig); outputs.append(str(path.relative_to(ROOT)))
    return outputs
