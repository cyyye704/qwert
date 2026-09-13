"""Q3: combined PV forecasts and causal 06/12/18 stochastic adjustments."""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
import dispatch_core as core  # noqa: E402
from config import MODEL_VERSION, RELEASES  # noqa: E402
from reporting import annual_summary, plot_typical, typical_day_payload, write_json  # noqa: E402
from result_workbooks import export_records  # noqa: E402
from scenario_cache import run_continuous  # noqa: E402


SCHEMES=[
    ("仅0:00，不调整",(),False),
    ("仅6:00",(6,),False),
    ("仅12:00",(12,),False),
    ("仅18:00",(18,),False),
    ("6:00+12:00",(6,12),False),
    ("12:00+18:00",(12,18),False),
    ("6:00+12:00+18:00（计划不含追索）",(6,12,18),False),
    ("完整追索式计划",(6,12,18),True),
]
FULL_SCHEME=("完整追索式计划",(6,12,18),True)


def _run_scheme(name,hours,recourse,fixed,load,pv,dates,bundle,price_releases,use_cache):
    label="q3_"+("none" if not hours else "_".join(map(str,hours)))+("_rec" if recourse else "")
    all_records=run_continuous(label,{"model":MODEL_VERSION,"updates":hours,"recourse_plan":recourse},len(dates)-1,
        lambda i,soc: core.run_q3_day(i,dates,load,pv,price_releases,bundle,soc,hours,recourse),use_cache=use_cache)
    ids=core.decision_indices(dates); records=[all_records[i] for i in ids]
    frame=pd.DataFrame([core.q3_metrics(r,fixed) for r in records])
    return all_records,records,frame,annual_summary(frame,records)


def _plot_ablation(table):
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),constrained_layout=True)
    x=np.arange(len(table)); labels=[s.replace("（计划不含追索）","\n无追索计划") for s in table.scheme]
    axes[0].bar(x,table.total_cost_yuan/1e4,color="#4472C4")
    axes[0].set(ylabel="全年费用（万元）",xticks=x,xticklabels=labels); axes[0].tick_params(axis="x",rotation=35,labelsize=8)
    axes[1].bar(x,table.emergency_kwh/1e4,color="#ED7D31")
    axes[1].set(ylabel="紧急购电量（万kWh）",xticks=x,xticklabels=labels); axes[1].tick_params(axis="x",rotation=35,labelsize=8)
    path=ROOT/"figures/P3_compare.png"; path.parent.mkdir(exist_ok=True); fig.savefig(path,dpi=220); plt.close(fig)
    return str(path.relative_to(ROOT))


def _forecast_stats(bundle,pv,ids):
    rows=[]
    for release in RELEASES:
        start=release*6
        actual=pv[np.ix_(ids,range(start,144))]
        for kind,array in [("附件3",bundle.pv_attachment[release]),("历史",bundle.pv_history),
                           ("组合",bundle.pv_combined[release]),
                           ("组合+日内晴空指数修正",bundle.pv_realtime[release])]:
            error=array[np.ix_(ids,range(start,144))]-actual
            rows.append({"release_hour":release,"forecast":kind,"mae_kw":float(np.mean(np.abs(error))),
                         "rmse_kw":float(np.sqrt(np.mean(error**2)))})
    frame=pd.DataFrame(rows)
    fig,ax=plt.subplots(figsize=(8,4.8),constrained_layout=True)
    for kind,g in frame.groupby("forecast"):
        ax.plot(g.release_hour,g.mae_kw,marker="o",label=kind)
    ax.set(xlabel="预报发布时间",ylabel="剩余时段MAE（kW）",xticks=list(RELEASES)); ax.legend()
    path=ROOT/"figures/forecast_pv_mae.png"; fig.savefig(path,dpi=220); plt.close(fig)
    return frame,str(path.relative_to(ROOT))


def run_problem3(use_cache: bool=True, q2_records_all=None, bundle=None, data=None,
                 include_ablations: bool=True):
    if data is None:
        fixed,variable,load,pv,dates,forecasts=core.load_data()
        data=(fixed,variable,load,pv,dates,forecasts)
    else:
        fixed,variable,load,pv,dates,forecasts=data
    if bundle is None:
        bundle=core.build_causal_forecasts(load,pv,variable,dates,forecasts,fixed)
    price_releases=core.fixed_release_forecasts(fixed,len(dates))
    outputs={}; rows=[]
    ordered=[FULL_SCHEME]
    if include_ablations:
        ordered += [scheme for scheme in SCHEMES if scheme != FULL_SCHEME]
    for name,hours,recourse in ordered:
        print(f"Q3消融：{name}",flush=True)
        outputs[name]=_run_scheme(name,hours,recourse,fixed,load,pv,dates,bundle,price_releases,use_cache)
        rows.append({"scheme":name,**outputs[name][3]})
    if q2_records_all is None:
        q2_records_all=run_continuous("q2_fixed",{"model":MODEL_VERSION,"price":"attachment1"},len(dates)-1,
            lambda i,soc: core.run_q2_day(i,dates,load,pv,fixed,bundle,soc),use_cache=use_cache)
    ids=core.decision_indices(dates); q2_records=[q2_records_all[i] for i in ids]
    q2_frame=pd.DataFrame([core.q2_metrics(r,fixed) for r in q2_records]); q2_summary=annual_summary(q2_frame,q2_records)
    perfect_all=None
    if include_ablations:
        rows.append({"scheme":"问题2方案",**q2_summary})
        perfect_all=run_continuous("perfect_fixed",{"model":MODEL_VERSION,"information":"load_pv_perfect","price":"attachment1"},len(dates)-1,
            lambda i,soc: core.run_perfect_information_day(i,dates,load,pv,fixed,soc),use_cache=use_cache)
        perfect=[perfect_all[i] for i in ids]
        perfect_frame=pd.DataFrame([core.q2_metrics(r,fixed) for r in perfect]); perfect_summary=annual_summary(perfect_frame,perfect)
        rows.append({"scheme":"完美信息下界",**perfect_summary})
    ablation=pd.DataFrame(rows); ablation.to_csv(ROOT/"results/problem3_ablation.csv",index=False,encoding="utf-8-sig")
    full_all,full,full_frame,full_summary=outputs["完整追索式计划"]
    full_frame.to_csv(ROOT/"results/problem3_daily.csv",index=False,encoding="utf-8-sig")
    forecast_frame,forecast_fig=_forecast_stats(bundle,pv,ids)
    forecast_frame.to_csv(ROOT/"results/problem3_forecast_accuracy.csv",index=False,encoding="utf-8-sig")
    summary={"model_version":MODEL_VERSION,
        "method":"附件3与历史PV的30日因果权重组合 + 发布时间残差场景 + AR(1)/晴空指数日内修正 + 随机LP滚动调整",
        "full_scheme":full_summary,"ablation":ablation.to_dict("records"),
        "forecast_accuracy":forecast_frame.to_dict("records"),"typical_days":typical_day_payload(full,full_frame)}
    summary["figures"]=[_plot_ablation(ablation),forecast_fig,*plot_typical(full,load,pv,dates,"P3")]
    write_json(ROOT/"results/problem3.json",summary)
    export_records(full,full_frame,"result3.xlsx",rolling=True)
    return full_all,full,full_frame,summary,outputs,perfect_all


def main():
    _,_,_,summary,_,_=run_problem3(); print(summary["full_scheme"])


if __name__=="__main__": main()
