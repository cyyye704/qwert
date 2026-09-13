"""Q4: causal, fixed-price-decision and price-oracle comparisons."""
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


def _formal(records_all,ids,prices,rolling):
    records=[records_all[i] for i in ids]
    metric=core.q3_metrics if rolling else core.q2_metrics
    frame=pd.DataFrame([metric(r,prices[i]) for r,i in zip(records,ids)])
    return records,frame,annual_summary(frame,records)


def _price_accuracy(actual,releases,ids):
    rows=[]
    for release in RELEASES:
        start=release*6; error=releases[release][np.ix_(ids,range(start,144))]-actual[np.ix_(ids,range(start,144))]
        rows.append({"release_hour":release,"mae_yuan_per_kwh":float(np.mean(np.abs(error))),
                     "rmse_yuan_per_kwh":float(np.sqrt(np.mean(error**2)))})
    return pd.DataFrame(rows)


def _plot_comparison(rows,price_accuracy,actual,day_ahead,dates):
    fig,ax=plt.subplots(figsize=(10,5),constrained_layout=True)
    x=np.arange(len(rows)); ax.bar(x,[r["total_cost_yuan"]/1e4 for r in rows],color="#4472C4")
    ax.set(ylabel="全年费用（万元）",xticks=x,xticklabels=[r["scenario"].replace(" ","\n") for r in rows]); ax.tick_params(axis="x",labelsize=8)
    p1=ROOT/"figures/P4_compare.png"; p1.parent.mkdir(exist_ok=True); fig.savefig(p1,dpi=220); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    sample=int(np.flatnonzero(dates==pd.Timestamp("2025-09-23"))[0]); t=np.arange(144)/6
    axes[0].plot(t,actual[sample],label="实际价格"); axes[0].plot(t,day_ahead[sample],label="0时预测")
    axes[0].set(xlabel="时刻 (h)",ylabel="元/kWh"); axes[0].legend()
    axes[1].plot(price_accuracy.release_hour,price_accuracy.mae_yuan_per_kwh,marker="o")
    axes[1].set(xlabel="发布时间",ylabel="剩余时段价格MAE",xticks=list(RELEASES))
    p2=ROOT/"figures/P4_price_forecast.png"; fig.savefig(p2,dpi=220); plt.close(fig)
    return [str(p1.relative_to(ROOT)),str(p2.relative_to(ROOT))]


def run_problem4(use_cache: bool=True, data=None, bundle=None,
                 q2_fixed_all=None, q3_fixed_all=None, include_oracles: bool=True):
    if data is None:
        data=core.load_data()
    fixed,variable,load,pv,dates,forecasts=data
    if bundle is None:
        bundle=core.build_causal_forecasts(load,pv,variable,dates,forecasts,fixed)
    ids=core.decision_indices(dates)
    causal_releases=core.price_release_forecasts(variable,bundle.price_day_ahead)
    fixed_releases=core.fixed_release_forecasts(fixed,len(dates))
    oracle_releases=core.oracle_release_forecasts(variable)

    causal_q2_all=run_continuous("q4_causal_q2",{"model":MODEL_VERSION,"price":"causal"},len(dates)-1,
        lambda i,soc: core.run_q2_day(i,dates,load,pv,causal_releases[0][i],bundle,soc),use_cache=use_cache)
    causal_q3_all=run_continuous("q4_causal_q3",{"model":MODEL_VERSION,"price":"causal","updates":[6,12,18],"recourse":True},len(dates)-1,
        lambda i,soc: core.run_q3_day(i,dates,load,pv,causal_releases,bundle,soc,(6,12,18),True),use_cache=use_cache)
    oracle_q2_all=oracle_q3_all=perfect_all=None
    if include_oracles:
        oracle_q2_all=run_continuous("q4_oracle_q2",{"model":MODEL_VERSION,"price":"oracle_only"},len(dates)-1,
            lambda i,soc: core.run_q2_day(i,dates,load,pv,variable[i],bundle,soc),use_cache=use_cache)
        oracle_q3_all=run_continuous("q4_oracle_q3",{"model":MODEL_VERSION,"price":"oracle_only","updates":[6,12,18],"recourse":True},len(dates)-1,
            lambda i,soc: core.run_q3_day(i,dates,load,pv,oracle_releases,bundle,soc,(6,12,18),True),use_cache=use_cache)
        perfect_all=run_continuous("perfect_variable",{"model":MODEL_VERSION,"information":"load_pv_price_perfect"},len(dates)-1,
            lambda i,soc: core.run_perfect_information_day(i,dates,load,pv,variable[i],soc),use_cache=use_cache)
    if q2_fixed_all is None:
        q2_fixed_all=run_continuous("q2_fixed",{"model":MODEL_VERSION,"price":"attachment1"},len(dates)-1,
            lambda i,soc: core.run_q2_day(i,dates,load,pv,fixed,bundle,soc),use_cache=use_cache)
    if q3_fixed_all is None:
        q3_fixed_all=run_continuous("q3_6_12_18_rec",{"model":MODEL_VERSION,"updates":[6,12,18],"recourse_plan":True},len(dates)-1,
            lambda i,soc: core.run_q3_day(i,dates,load,pv,fixed_releases,bundle,soc,(6,12,18),True),use_cache=use_cache)

    cq2,cq2f,cq2s=_formal(causal_q2_all,ids,variable,False)
    cq3,cq3f,cq3s=_formal(causal_q3_all,ids,variable,True)
    fq2,fq2f,fq2s=_formal(q2_fixed_all,ids,variable,False)
    fq3,fq3f,fq3s=_formal(q3_fixed_all,ids,variable,True)
    extra_frames=[]; extra_scenarios=[]
    if include_oracles:
        oq2,oq2f,oq2s=_formal(oracle_q2_all,ids,variable,False)
        oq3,oq3f,oq3s=_formal(oracle_q3_all,ids,variable,True)
        perfect,perfectf,perfects=_formal(perfect_all,ids,variable,False)
        extra_frames=[("problem4_oracle_q2_daily",oq2f),("problem4_oracle_q3_daily",oq3f),
                      ("problem4_perfect_information_daily",perfectf)]
        extra_scenarios=[("price-oracle Q4-2",oq2s),("price-oracle Q4-3",oq3s),
                         ("perfect-information lower bound",perfects)]
    for name,frame in [("problem4_causal_q2_daily",cq2f),("problem4_causal_q3_daily",cq3f),
                       ("problem4_fixed_q2_daily",fq2f),("problem4_fixed_q3_daily",fq3f),*extra_frames]:
        frame.to_csv(ROOT/f"results/{name}.csv",index=False,encoding="utf-8-sig")
    export_records(cq2,cq2f,"result4-2.xlsx",rolling=False)
    export_records(cq3,cq3f,"result4-3.xlsx",rolling=True)
    price_accuracy=_price_accuracy(variable,causal_releases,ids)
    price_accuracy.to_csv(ROOT/"results/problem4_price_forecast_accuracy.csv",index=False,encoding="utf-8-sig")
    scenarios=[("causal Q4-2",cq2s),("causal Q4-3",cq3s),("fixed-price Q4-2",fq2s),
               ("fixed-price Q4-3",fq3s),*extra_scenarios]
    rows=[{"scenario":name,**value} for name,value in scenarios]
    comparison=pd.DataFrame(rows); comparison.to_csv(ROOT/"results/problem4_comparison.csv",index=False,encoding="utf-8-sig")
    summary={"model_version":MODEL_VERSION,
        "method":"最近3个同类型日电价均值；6/12/18以已观测前缀实际/预测比修正；全部按附件4实际价结算",
        "information_policies":{"causal":"历史价格及当日已观测价格前缀","fixed_price":"附件1决策、附件4结算",
                                "price_oracle":"仅开放未来真实价格，负载和PV仍为因果预测/场景",
                                "perfect_information":"仅作为负载、PV、价格全部已知的理论下界"},
        "scenarios":rows,"price_forecast_accuracy":price_accuracy.to_dict("records"),
        "typical_days":{"q4_2":typical_day_payload(cq2,cq2f),"q4_3":typical_day_payload(cq3,cq3f)}}
    summary["figures"]=[*_plot_comparison(rows,price_accuracy,variable,bundle.price_day_ahead,dates),
                        *plot_typical(cq2,load,pv,dates,"P4-2"),*plot_typical(cq3,load,pv,dates,"P4-3")]
    write_json(ROOT/"results/problem4.json",summary)
    return summary


def main():
    summary=run_problem4(); print({r["scenario"]:r["total_cost_yuan"] for r in summary["scenarios"]})


if __name__=="__main__": main()
