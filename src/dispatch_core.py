"""Shared Q2--Q4 implementation specified by c建模说明与结果.txt.

All forecasts are causal. Charge/discharge are grid-side interval energy, so
SOC evolves as ``S[t+1] = S[t] + eta*c[t] - d[t]/eta``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from config import (  # noqa: E402
    COMBINATION_LOOKBACK_DAYS, COMBINATION_WEIGHT_GRID, DECISION_START,
    DECREASE_FEE_MULTIPLIER, DT, EMERGENCY_PRICE_MULTIPLIER, ENERGY_LIMIT,
    ETA, INCREASE_PRICE_MULTIPLIER, LOAD_AR_RHO,
    LOAD_HISTORY_SAME_TYPE_DAYS, LP_METHOD, N,
    PRICE_HISTORY_SAME_TYPE_DAYS, PV_HISTORY_DAYS, PV_PERSISTENCE_PHI,
    RELEASES, RESIDUAL_SCENARIOS, SOC_LOWER, SOC_SAFETY_MARGIN_KWH,
    SOC_UPPER, TERMINAL_VALUE_YUAN_PER_KWH,
    THROUGHPUT_REGULARIZATION_YUAN_PER_KWH, YEAR_DAYS,
)
from time_axis import right_endpoint_hours, validate_right_endpoint_axis  # noqa: E402

DATA = ROOT / "data" / "附件"


@dataclass
class ForecastBundle:
    load_day_ahead: np.ndarray
    pv_history: np.ndarray
    price_day_ahead: np.ndarray
    pv_attachment: dict[int, np.ndarray]
    pv_combined: dict[int, np.ndarray]
    combination_weights: dict[int, np.ndarray]
    load_realtime: dict[int, np.ndarray]
    pv_realtime: dict[int, np.ndarray]


def load_data():
    fixed_df = pd.read_excel(DATA / "附件1.xlsx")
    load_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="小区负载")
    pv_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="光伏发电实际功率")
    variable_df = pd.read_excel(DATA / "附件4.xlsx")
    validate_right_endpoint_axis(fixed_df.iloc[:, 0], "附件1 时间列")
    validate_right_endpoint_axis(load_df.columns[1:], "附件2 负载表头")
    validate_right_endpoint_axis(pv_df.columns[1:], "附件2 光伏表头")
    validate_right_endpoint_axis(variable_df.columns[1:], "附件4 电价表头")
    fixed = fixed_df.iloc[:, 1].to_numpy(float)
    load = load_df.iloc[:, 1:].to_numpy(float)
    pv = pv_df.iloc[:, 1:].to_numpy(float)
    variable = variable_df.iloc[:, 1:].to_numpy(float)
    dates = pd.DatetimeIndex(pd.to_datetime(load_df.iloc[:, 0]).dt.normalize())
    pv_dates = pd.DatetimeIndex(pd.to_datetime(pv_df.iloc[:, 0]).dt.normalize())
    price_dates = pd.DatetimeIndex(pd.to_datetime(variable_df.iloc[:, 0]).dt.normalize())
    if fixed.shape != (N,) or load.shape != (YEAR_DAYS, N) or pv.shape != (YEAR_DAYS, N) or variable.shape != (YEAR_DAYS, N):
        raise ValueError(f"输入形状异常 fixed={fixed.shape}, load={load.shape}, pv={pv.shape}, price={variable.shape}")
    if not dates.equals(pv_dates) or not dates.equals(price_dates):
        raise ValueError("附件2和附件4日期未严格对齐")
    values = np.r_[fixed, load.ravel(), pv.ravel(), variable.ravel()]
    if not np.isfinite(values).all() or np.any(fixed <= 0) or np.any(variable <= 0):
        raise ValueError("附件含缺失、无穷值或非正电价")

    fdf = pd.read_excel(DATA / "附件3.xlsx")
    forecast_dates = pd.to_datetime(fdf.iloc[:, 0], errors="coerce").ffill().dt.normalize()
    releases = fdf.iloc[:, 1].astype(str).str.extract(r"(\d+)")[0].astype(int).to_numpy()
    values24 = fdf.iloc[:, 2:26].to_numpy(float)
    forecasts = {}
    for forecast_date, release, values_ in zip(forecast_dates, releases, values24):
        forecasts[(pd.Timestamp(forecast_date).strftime("%Y-%m-%d"), int(release))] = np.maximum(values_, 0.0)
    expected = {(d.strftime("%Y-%m-%d"), r) for d in dates for r in RELEASES}
    missing = expected.difference(forecasts)
    if missing:
        raise ValueError(f"附件3缺少{len(missing)}个日期-发布时间记录")
    return fixed, variable, load, pv, dates, forecasts


def load_initial_profiles() -> tuple[np.ndarray, np.ndarray]:
    frame = pd.read_excel(DATA / "附件1.xlsx")
    return frame.iloc[:, 2].to_numpy(float), frame.iloc[:, 3].to_numpy(float)


def day_type(date: pd.Timestamp) -> int:
    """Specification/data day types: low-load Friday/Saturday versus normal days."""
    # Attachment 2 confirms the two classes numerically: Friday and Saturday
    # are about 63% of ordinary-day energy, while Sunday is ordinary load.
    return int(pd.Timestamp(date).dayofweek in (4, 5))


def previous_same_type(dates: pd.DatetimeIndex, i: int, count: int) -> list[int]:
    wanted = day_type(dates[i])
    found = [j for j in range(i - 1, -1, -1) if day_type(dates[j]) == wanted]
    return list(reversed(found[:count]))


def _history_mean(values: np.ndarray, indices: list[int], fallback: np.ndarray) -> np.ndarray:
    return np.asarray(values[indices], float).mean(axis=0) if indices else np.asarray(fallback, float).copy()


def attachment_forecast_to_grid(values: np.ndarray, release_hour: int,
                                observed_at_release: float = 0.0) -> np.ndarray:
    x = np.r_[float(release_hour), release_hour + np.arange(1, 25, dtype=float)]
    y = np.r_[max(float(observed_at_release), 0.0), np.maximum(np.asarray(values, float), 0.0)]
    return np.interp(right_endpoint_hours(), x, y, left=y[0], right=y[-1])


def _intraday_load_forecast(base: np.ndarray, actual: np.ndarray, start: int) -> np.ndarray:
    out = np.asarray(base, float).copy()
    if start <= 0:
        return np.maximum(out, 0.0)
    residual = np.asarray(actual[:start], float) - out[:start]
    bias = float(residual.mean())
    latest = float(residual[-1])
    leads = np.arange(1, N - start + 1, dtype=float)
    out[start:] += bias + np.power(LOAD_AR_RHO, leads) * (latest - bias)
    return np.maximum(out, 0.0)


def _intraday_pv_forecast(base: np.ndarray, day_ahead: np.ndarray,
                          actual: np.ndarray, start: int) -> np.ndarray:
    out = np.asarray(base, float).copy()
    if start <= 0:
        return np.maximum(out, 0.0)
    eligible = np.flatnonzero(np.asarray(day_ahead[:start]) > 1.0)
    if eligible.size:
        anchor = int(eligible[-1])
        kappa = float(actual[anchor] / day_ahead[anchor])
    else:
        kappa = 1.0
    leads = np.arange(1, N - start + 1, dtype=float)
    out[start:] *= 1.0 + (kappa - 1.0) * np.power(PV_PERSISTENCE_PHI, leads)
    return np.maximum(out, 0.0)


def build_causal_forecasts(load: np.ndarray, pv: np.ndarray, prices: np.ndarray,
                           dates: pd.DatetimeIndex, forecasts: dict,
                           fixed_price_fallback: np.ndarray | None = None) -> ForecastBundle:
    fallback_load, fallback_pv = load_initial_profiles()
    fallback_price = prices[0] if fixed_price_fallback is None else np.asarray(fixed_price_fallback, float)
    load_day = np.empty_like(load, dtype=float)
    pv_hist = np.empty_like(pv, dtype=float)
    price_day = np.empty_like(prices, dtype=float)
    for i in range(len(dates)):
        load_day[i] = _history_mean(load, previous_same_type(dates, i, LOAD_HISTORY_SAME_TYPE_DAYS), fallback_load)
        pv_hist[i] = _history_mean(pv, list(range(max(0, i-PV_HISTORY_DAYS), i)), fallback_pv)
        price_day[i] = _history_mean(prices, previous_same_type(dates, i, PRICE_HISTORY_SAME_TYPE_DAYS), fallback_price)

    attachment = {r: np.empty_like(pv, dtype=float) for r in RELEASES}
    for i, date in enumerate(dates):
        key = date.strftime("%Y-%m-%d")
        for release in RELEASES:
            start = release * 6
            observed = 0.0 if start == 0 else float(pv[i, start-1])
            attachment[release][i] = attachment_forecast_to_grid(forecasts[(key, release)], release, observed)

    combined = {r: np.empty_like(pv, dtype=float) for r in RELEASES}
    weights = {r: np.zeros(len(dates), dtype=float) for r in RELEASES}
    grid = np.asarray(COMBINATION_WEIGHT_GRID, float)
    for release in RELEASES:
        start = release * 6
        for i in range(len(dates)):
            hist = list(range(max(0, i-COMBINATION_LOOKBACK_DAYS), i))
            if hist:
                scores = []
                for weight in grid:
                    pred = weight*attachment[release][hist, start:] + (1-weight)*pv_hist[hist, start:]
                    scores.append(float(np.mean(np.abs(pred-pv[hist, start:]))))
                weight = float(grid[int(np.argmin(scores))])
            else:
                weight = 0.0
            weights[release][i] = weight
            combined[release][i] = weight*attachment[release][i] + (1-weight)*pv_hist[i]

    load_rt = {r: np.empty_like(load, dtype=float) for r in RELEASES}
    pv_rt = {r: np.empty_like(pv, dtype=float) for r in RELEASES}
    for release in RELEASES:
        start = release * 6
        for i in range(len(dates)):
            load_rt[release][i] = _intraday_load_forecast(load_day[i], load[i], start)
            pv_rt[release][i] = _intraday_pv_forecast(combined[release][i], combined[0][i], pv[i], start)
    return ForecastBundle(load_day, pv_hist, price_day, attachment, combined, weights, load_rt, pv_rt)


def price_release_forecasts(actual_prices: np.ndarray, day_ahead: np.ndarray) -> dict[int, np.ndarray]:
    """Apply the observed-prefix actual/predicted ratio to the remaining day."""
    result = {0: np.asarray(day_ahead, float).copy()}
    for release in RELEASES[1:]:
        start = release * 6
        updated = np.asarray(day_ahead, float).copy()
        ratios = actual_prices[:, :start].sum(axis=1) / day_ahead[:, :start].sum(axis=1)
        updated[:, start:] *= ratios[:, None]
        result[release] = updated
    return result


def fixed_release_forecasts(fixed: np.ndarray, days: int) -> dict[int, np.ndarray]:
    matrix = np.tile(np.asarray(fixed, float), (days, 1))
    return {r: matrix.copy() for r in RELEASES}


def oracle_release_forecasts(actual_prices: np.ndarray) -> dict[int, np.ndarray]:
    return {r: np.asarray(actual_prices, float).copy() for r in RELEASES}


def residual_scenarios(point: np.ndarray, actual_history: np.ndarray,
                       forecast_history: np.ndarray, i: int,
                       count: int = RESIDUAL_SCENARIOS) -> np.ndarray:
    indices = list(range(max(0, i-count), i))
    if not indices:
        return np.asarray(point, float)[None, :]
    residuals = actual_history[indices] - forecast_history[indices]
    return np.maximum(np.asarray(point, float)[None, :] + residuals, 0.0)


def scenario_pair(bundle: ForecastBundle, load: np.ndarray, pv: np.ndarray,
                  i: int, release: int, use_attachment: bool) -> tuple[np.ndarray, np.ndarray]:
    if use_attachment:
        load_forecasts = bundle.load_realtime[release]
        pv_forecasts = bundle.pv_realtime[release]
    else:
        load_forecasts = bundle.load_day_ahead
        pv_forecasts = bundle.pv_history
    return (residual_scenarios(load_forecasts[i], load, load_forecasts, i),
            residual_scenarios(pv_forecasts[i], pv, pv_forecasts, i))


def solve_stochastic_plan(price: np.ndarray, load_scenarios_kw: np.ndarray,
                          pv_scenarios_kw: np.ndarray, soc0: float, *, start: int = 0,
                          safety_margin: float = SOC_SAFETY_MARGIN_KWH,
                          terminal_value: float = TERMINAL_VALUE_YUAN_PER_KWH,
                          recourse_start: int | None = None) -> dict:
    """Shared-purchase stochastic LP; optional Q3 scenario adjustment recourse."""
    h = N-start
    price = np.asarray(price, float)[start:]
    load_s = np.asarray(load_scenarios_kw, float)[:, start:]*DT
    pv_s = np.asarray(pv_scenarios_kw, float)[:, start:]*DT
    if load_s.shape != pv_s.shape or load_s.shape[1] != h:
        raise ValueError("scenario shapes do not match horizon")
    k_count = load_s.shape[0]
    q0 = None if recourse_start is None else max(0, int(recourse_start)-start)
    qlen = 0 if q0 is None else h-q0
    shared = h; block = 5*h+1+2*qlen; nvar = shared+k_count*block
    objective = np.zeros(nvar); objective[:h] = price
    aeq = lil_matrix((k_count*(2*h+1), nvar)); beq = np.zeros(k_count*(2*h+1))
    aub = lil_matrix((k_count*qlen, nvar)) if qlen else None
    bub = np.zeros(k_count*qlen) if qlen else None
    bounds = [(0.0, None)]*h; row = 0; urow = 0; adjust_offsets = []
    for k in range(k_count):
        base = shared+k*block
        oc,od,oe,ow,os = base,base+h,base+2*h,base+3*h,base+4*h
        or_,ox = os+h+1,os+h+1+qlen
        objective[oc:od] = THROUGHPUT_REGULARIZATION_YUAN_PER_KWH/k_count
        objective[od:oe] = THROUGHPUT_REGULARIZATION_YUAN_PER_KWH/k_count
        objective[oe:ow] = EMERGENCY_PRICE_MULTIPLIER*price/k_count
        objective[os+h] = -terminal_value/k_count
        if qlen:
            objective[or_:ox] = -DECREASE_FEE_MULTIPLIER*price[q0:]/k_count
            objective[ox:ox+qlen] = INCREASE_PRICE_MULTIPLIER*price[q0:]/k_count
        for j in range(h):
            aeq[row,j]=1
            if qlen and j>=q0:
                q=j-q0; aeq[row,or_+q]=-1; aeq[row,ox+q]=1
            aeq[row,oc+j]=-1; aeq[row,od+j]=1; aeq[row,oe+j]=1; aeq[row,ow+j]=-1
            beq[row]=load_s[k,j]-pv_s[k,j]; row+=1
            aeq[row,os+j+1]=1; aeq[row,os+j]=-1; aeq[row,oc+j]=-ETA; aeq[row,od+j]=1/ETA
            row+=1
        aeq[row,os]=1; beq[row]=soc0; row+=1
        if qlen:
            for q in range(qlen):
                aub[urow,or_+q]=1; aub[urow,q0+q]=-1; urow+=1
        bounds += ([(0.0,ENERGY_LIMIT)]*h+[(0.0,ENERGY_LIMIT)]*h
                   +[(0.0,None)]*h+[(0.0,None)]*h
                   +[(SOC_LOWER,SOC_UPPER)]
                   +[(SOC_LOWER+safety_margin,SOC_UPPER-safety_margin)]*h
                   +[(0.0,None)]*(2*qlen))
        adjust_offsets.append((or_,ox))
    tic=time.perf_counter()
    out=linprog(objective,A_ub=None if aub is None else aub.tocsr(),b_ub=bub,
                A_eq=aeq.tocsr(),b_eq=beq,bounds=bounds,method=LP_METHOD)
    if not out.success:
        raise RuntimeError(f"随机LP失败 start={start}: {out.status} {out.message}")
    scenario_purchase=[]
    for or_,ox in adjust_offsets:
        schedule=out.x[:h].copy()
        if qlen:
            schedule[q0:] += -out.x[or_:ox]+out.x[ox:ox+qlen]
        scenario_purchase.append(schedule)
    return {"purchase":out.x[:h],"scenario_purchase":np.asarray(scenario_purchase),
            "objective_with_regularization":float(out.fun),"seconds":time.perf_counter()-tic,
            "status":"optimal","scenario_count":int(k_count),"start":int(start),
            "recourse_start":recourse_start}


def solve_stochastic_adjustment(price: np.ndarray, original_plan: np.ndarray,
                                load_scenarios_kw: np.ndarray, pv_scenarios_kw: np.ndarray,
                                soc0: float, start: int, *,
                                safety_margin: float = SOC_SAFETY_MARGIN_KWH,
                                terminal_value: float = TERMINAL_VALUE_YUAN_PER_KWH) -> dict:
    """Optimize a shared remaining schedule, settled against the 00:00 plan."""
    h=N-start; price_h=np.asarray(price,float)[start:]; base_plan=np.asarray(original_plan,float)[start:]
    load_s=np.asarray(load_scenarios_kw,float)[:,start:]*DT
    pv_s=np.asarray(pv_scenarios_kw,float)[:,start:]*DT
    k_count=load_s.shape[0]
    oy,or_,ox=0,h,2*h; shared=3*h; block=5*h+1; nvar=shared+k_count*block
    objective=np.zeros(nvar)
    objective[or_:ox]=-DECREASE_FEE_MULTIPLIER*price_h
    objective[ox:shared]=INCREASE_PRICE_MULTIPLIER*price_h
    aeq=lil_matrix((h+k_count*(2*h+1),nvar)); beq=np.zeros(h+k_count*(2*h+1))
    bounds=[(0.0,None)]*h+[(0.0,float(v)) for v in base_plan]+[(0.0,None)]*h
    row=0
    for j in range(h):
        aeq[row,oy+j]=1; aeq[row,or_+j]=1; aeq[row,ox+j]=-1; beq[row]=base_plan[j]; row+=1
    for k in range(k_count):
        base=shared+k*block; oc,od,oe,ow,os=base,base+h,base+2*h,base+3*h,base+4*h
        objective[oc:od]=THROUGHPUT_REGULARIZATION_YUAN_PER_KWH/k_count
        objective[od:oe]=THROUGHPUT_REGULARIZATION_YUAN_PER_KWH/k_count
        objective[oe:ow]=EMERGENCY_PRICE_MULTIPLIER*price_h/k_count
        objective[os+h]=-terminal_value/k_count
        for j in range(h):
            aeq[row,oy+j]=1; aeq[row,oc+j]=-1; aeq[row,od+j]=1; aeq[row,oe+j]=1; aeq[row,ow+j]=-1
            beq[row]=load_s[k,j]-pv_s[k,j]; row+=1
            aeq[row,os+j+1]=1; aeq[row,os+j]=-1; aeq[row,oc+j]=-ETA; aeq[row,od+j]=1/ETA; row+=1
        aeq[row,os]=1; beq[row]=soc0; row+=1
        bounds += ([(0.0,ENERGY_LIMIT)]*h+[(0.0,ENERGY_LIMIT)]*h
                   +[(0.0,None)]*h+[(0.0,None)]*h
                   +[(SOC_LOWER,SOC_UPPER)]
                   +[(SOC_LOWER+safety_margin,SOC_UPPER-safety_margin)]*h)
    tic=time.perf_counter()
    out=linprog(objective,A_eq=aeq.tocsr(),b_eq=beq,bounds=bounds,method=LP_METHOD)
    if not out.success:
        raise RuntimeError(f"调整随机LP失败 start={start}: {out.status} {out.message}")
    return {"purchase":out.x[:h],"decrease":out.x[or_:ox],"increase":out.x[ox:shared],
            "seconds":time.perf_counter()-tic,"status":"optimal","scenario_count":int(k_count),
            "start":int(start),"objective_with_regularization":float(out.fun)}


def execute_causal_rule(purchase: np.ndarray, load_kw: np.ndarray, pv_kw: np.ndarray,
                        soc0: float, start: int = 0, end: int = N) -> dict:
    purchase=np.asarray(purchase,float); load_e=np.asarray(load_kw,float)*DT; pv_e=np.asarray(pv_kw,float)*DT
    h=end-start
    charge=np.zeros(h); discharge=np.zeros(h); emergency=np.zeros(h); waste=np.zeros(h)
    soc=np.empty(h+1); soc[0]=float(soc0)
    for j,t in enumerate(range(start,end)):
        surplus=purchase[t]+pv_e[t]-load_e[t]
        if surplus>=0:
            charge[j]=min(surplus,ENERGY_LIMIT,max(0.0,(SOC_UPPER-soc[j])/ETA))
            waste[j]=surplus-charge[j]
        else:
            deficit=-surplus
            discharge[j]=min(deficit,ENERGY_LIMIT,max(0.0,(soc[j]-SOC_LOWER)*ETA))
            emergency[j]=deficit-discharge[j]
        soc[j+1]=soc[j]+ETA*charge[j]-discharge[j]/ETA
    residual=purchase[start:end]+pv_e[start:end]+discharge+emergency-load_e[start:end]-charge-waste
    return {"charge":charge,"discharge":discharge,"emergency":emergency,"waste":waste,
            "soc":soc,"residual":residual}


def run_q2_day(i: int, dates: pd.DatetimeIndex, load: np.ndarray, pv: np.ndarray,
               decision_price: np.ndarray, bundle: ForecastBundle, soc0: float) -> dict:
    load_s,pv_s=scenario_pair(bundle,load,pv,i,0,False)
    plan=solve_stochastic_plan(decision_price,load_s,pv_s,soc0)
    actual=execute_causal_rule(plan["purchase"],load[i],pv[i],soc0)
    return {"date":dates[i].strftime("%Y-%m-%d"),"plan":plan,
            "final_purchase":plan["purchase"].copy(),"actual":actual,"updates":[]}


def run_q3_day(i: int, dates: pd.DatetimeIndex, load: np.ndarray, pv: np.ndarray,
               release_prices: dict[int,np.ndarray], bundle: ForecastBundle, soc0: float,
               update_hours: tuple[int,...]=(6,12,18), recourse_plan: bool=False) -> dict:
    load_s,pv_s=scenario_pair(bundle,load,pv,i,0,True)
    plan=solve_stochastic_plan(release_prices[0][i],load_s,pv_s,soc0,
                               recourse_start=36 if recourse_plan else None)
    original=plan["purchase"].copy(); schedule=original.copy()
    actual={name:np.zeros(N) for name in ("charge","discharge","emergency","waste","residual")}
    actual["soc"]=np.empty(N+1); actual["soc"][0]=soc0
    updates=[]; cursor=0; seconds=plan["seconds"]
    for release in tuple(update_hours)+(24,):
        boundary=release*6
        seg=execute_causal_rule(schedule,load[i],pv[i],actual["soc"][cursor],cursor,boundary)
        for name in ("charge","discharge","emergency","waste","residual"):
            actual[name][cursor:boundary]=seg[name]
        actual["soc"][cursor:boundary+1]=seg["soc"]
        cursor=boundary
        if release==24: break
        load_s,pv_s=scenario_pair(bundle,load,pv,i,release,True)
        adjustment=solve_stochastic_adjustment(release_prices[release][i],original,load_s,pv_s,
                                               actual["soc"][cursor],cursor)
        schedule[cursor:]=adjustment["purchase"]; seconds+=adjustment["seconds"]
        snapshot=np.full(N,np.nan); snapshot[cursor:]=schedule[cursor:]
        updates.append({"release_hour":release,"purchase":snapshot,"seconds":adjustment["seconds"],
                        "observed_prefix_end":cursor})
    return {"date":dates[i].strftime("%Y-%m-%d"),"plan":plan,"final_purchase":schedule,
            "actual":actual,"updates":updates,"seconds":seconds,
            "update_hours":tuple(update_hours),"recourse_plan":bool(recourse_plan)}


def run_perfect_information_day(i: int, dates: pd.DatetimeIndex, load: np.ndarray,
                                pv: np.ndarray, price: np.ndarray, soc0: float) -> dict:
    plan=solve_stochastic_plan(price,load[i][None,:],pv[i][None,:],soc0,safety_margin=0.0)
    actual=execute_causal_rule(plan["purchase"],load[i],pv[i],soc0)
    return {"date":dates[i].strftime("%Y-%m-%d"),"plan":plan,
            "final_purchase":plan["purchase"].copy(),"actual":actual,"updates":[]}


def _common_metrics(record: dict, plan_cost: float, adjustment_cost: float,
                    emergency_cost: float) -> dict:
    a=record["actual"]
    return {"date":record["date"],"plan_cost_yuan":plan_cost,
            "adjustment_cost_yuan":adjustment_cost,"emergency_cost_yuan":emergency_cost,
            "total_cost_yuan":plan_cost+adjustment_cost+emergency_cost,
            "plan_kwh":float(record["plan"]["purchase"].sum()),
            "final_purchase_kwh":float(record["final_purchase"].sum()),
            "emergency_kwh":float(a["emergency"].sum()),"waste_kwh":float(a["waste"].sum()),
            "charge_kwh":float(a["charge"].sum()),"discharge_kwh":float(a["discharge"].sum()),
            "emergency_periods":int(np.count_nonzero(a["emergency"]>1e-8)),
            "simultaneous_charge_discharge_periods":int(np.count_nonzero((a["charge"]>1e-8)&(a["discharge"]>1e-8))),
            "soc_start_kwh":float(a["soc"][0]),"soc_end_kwh":float(a["soc"][-1]),
            "soc_min_kwh":float(a["soc"].min()),"soc_max_kwh":float(a["soc"].max()),
            "max_charge_kwh":float(a["charge"].max()),"max_discharge_kwh":float(a["discharge"].max()),
            "balance_max_abs_kwh":float(np.abs(a["residual"]).max()),
            "solve_seconds":float(record.get("seconds",record["plan"]["seconds"]))}


def q2_metrics(record: dict, settlement_price: np.ndarray) -> dict:
    p=record["plan"]["purchase"]; a=record["actual"]
    plan_cost=float(np.dot(settlement_price,p))
    emergency_cost=float(np.dot(EMERGENCY_PRICE_MULTIPLIER*settlement_price,a["emergency"]))
    return _common_metrics(record,plan_cost,0.0,emergency_cost)


def q3_metrics(record: dict, settlement_price: np.ndarray) -> dict:
    base=record["plan"]["purchase"]; final=record["final_purchase"]; a=record["actual"]
    decrease=np.maximum(base-final,0.0); increase=np.maximum(final-base,0.0)
    plan_cost=float(np.dot(settlement_price,base))
    adjustment_cost=float(np.dot(settlement_price,-DECREASE_FEE_MULTIPLIER*decrease+INCREASE_PRICE_MULTIPLIER*increase))
    emergency_cost=float(np.dot(EMERGENCY_PRICE_MULTIPLIER*settlement_price,a["emergency"]))
    return _common_metrics(record,plan_cost,adjustment_cost,emergency_cost)


def decision_indices(dates: pd.DatetimeIndex) -> list[int]:
    return list(np.flatnonzero(dates>=DECISION_START))
