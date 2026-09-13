"""问题1：基于连续线性规划的单日微网计划购电策略。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from config import (
    SEED,
    DT,
    N,
    CAPACITY_KWH,
    POWER_LIMIT_KW,
    ETA,
    SOC_INITIAL,
    SOC_LOWER,
    SOC_UPPER,
    ENERGY_LIMIT,
    LP_METHOD,
)
from plot_style import PALETTE, apply, combo_axes, response_surface, save_publication, series_style  # noqa: E402
from time_axis import all_slot_labels, interval_start_index, right_endpoint_hours, validate_right_endpoint_axis

DATA_FILE = ROOT / "data" / "附件" / "附件1.xlsx"
TEMPLATE_FILE = ROOT / "data" / "附件" / "附件5" / "result1.xlsx"
FIG = ROOT / "figures"
RES = ROOT / "results"


def time_labels() -> list[str]:
    return all_slot_labels()


def load_inputs() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    data = pd.read_excel(DATA_FILE, sheet_name="Sheet1")
    expected = ["时间", "电价", "小区负载", "光伏发电预测功率"]
    if list(data.columns) != expected or len(data) != N:
        raise ValueError(f"附件1字段或行数不符：{list(data.columns)}，{len(data)} 行")
    validate_right_endpoint_axis(data["时间"], "附件1 时间列")
    price = data["电价"].to_numpy(dtype=float)
    load = data["小区负载"].to_numpy(dtype=float) * DT
    pv = data["光伏发电预测功率"].to_numpy(dtype=float) * DT
    if not np.isfinite(np.r_[price, load, pv]).all() or (price < 0).any():
        raise ValueError("附件1含非有限数或负电价")
    return data, price, load, pv


def solve_lp(price: np.ndarray, load: np.ndarray, pv: np.ndarray, *,
             soc_lower: float = SOC_LOWER, soc_upper: float = SOC_UPPER,
             energy_limit: float = ENERGY_LIMIT) -> dict:
    """用HiGHS精确求解购电、充电、放电和SOC组成的连续线性规划。"""
    # 变量顺序为 p[0:N]、c[0:N]、d[0:N]、soc[0:N+1]。
    offset_c, offset_d, offset_soc = N, 2 * N, 3 * N
    nvar = 4 * N + 1
    objective = np.zeros(nvar)
    objective[:N] = price

    equality = []
    rhs = []
    for t in range(N):
        row = np.zeros(nvar)
        row[t] = 1.0
        row[offset_c + t] = -1 / ETA
        row[offset_d + t] = ETA
        equality.append(row)
        rhs.append(load[t] - pv[t])

        row = np.zeros(nvar)
        row[offset_soc + t + 1] = 1.0
        row[offset_soc + t] = -1.0
        row[offset_c + t] = -1.0
        row[offset_d + t] = 1.0
        equality.append(row)
        rhs.append(0.0)

    row = np.zeros(nvar)
    row[offset_soc] = 1.0
    equality.append(row)
    rhs.append(SOC_INITIAL)
    row = np.zeros(nvar)
    row[offset_soc + N] = 1.0
    equality.append(row)
    rhs.append(SOC_INITIAL)

    bounds = ([(0.0, None)] * N + [(0.0, energy_limit)] * N
              + [(0.0, energy_limit)] * N
              + [(soc_lower, soc_upper)] * (N + 1))
    start = time.perf_counter()
    result = linprog(objective, A_eq=np.asarray(equality), b_eq=np.asarray(rhs),
                     bounds=bounds, method=LP_METHOD)
    elapsed = time.perf_counter() - start
    if not result.success:
        raise RuntimeError(f"LP未求得最优解：{result.status} {result.message}")
    x = result.x
    return {
        "purchase": x[:N], "charge": x[offset_c:offset_d],
        "discharge": x[offset_d:offset_soc], "soc": x[offset_soc:],
        "cost": float(result.fun), "status": result.message,
        "solver_status_code": int(result.status), "solve_seconds": elapsed,
    }


def intervals_from_mask(mask: np.ndarray) -> str:
    starts = np.flatnonzero(mask & ~np.r_[False, mask[:-1]])
    ends = np.flatnonzero(mask & ~np.r_[mask[1:], False]) + 1
    def hhmm(index: int) -> str:
        mins = index * 10
        return f"{mins // 60:02d}:{mins % 60:02d}"
    return "、".join(f"{hhmm(s)}-{hhmm(e)}" for s, e in zip(starts, ends)) or "无"


def summarise(solution: dict, price: np.ndarray, load: np.ndarray, pv: np.ndarray) -> dict:
    purchase, charge, discharge, soc = (solution[k] for k in ("purchase", "charge", "discharge", "soc"))
    residual = purchase + pv + ETA * discharge - load - charge / ETA
    selected = {time_labels()[i]: float(purchase[i])
                for i in [interval_start_index(hour) for hour in (10, 12, 14, 16, 18, 20)]}
    windows = {}
    for i, start in enumerate(range(0, N, 24)):
        name = f"{i * 4}:00-{(i + 1) * 4}:00"
        windows[name] = {"charge_kwh": float(charge[start:start + 24].sum()),
                         "discharge_kwh": float(discharge[start:start + 24].sum())}
    charge_mask = charge > 1e-5
    discharge_mask = discharge > 1e-5
    charge_mean = float(price[charge_mask].mean()) if charge_mask.any() else 0.0
    discharge_mean = float(price[discharge_mask].mean()) if discharge_mask.any() else 0.0
    simultaneous = int(np.count_nonzero(charge_mask & discharge_mask))
    return {
        "method": "连续线性规划（scipy.optimize.linprog，HiGHS）",
        "data_source": "附件1.xlsx Sheet1真实预测数据",
        "time_step_hours": DT,
        "efficiency": ETA,
        "soc_bounds_kwh": [SOC_LOWER, SOC_UPPER],
        "charge_discharge_limit_kwh": ENERGY_LIMIT,
        "solver_status": "optimal" if solution["solver_status_code"] == 0 else solution["status"],
        "solver_message": solution["status"],
        "global_optimum_basis": "线性规划可行域为凸多面体，HiGHS最优状态给出全局最优解",
        "optimality_gap": 0.0,
        "solve_seconds": solution["solve_seconds"],
        "daily_purchase_kwh": float(purchase.sum()),
        "daily_purchase_cost_yuan": solution["cost"],
        "specified_purchase_kwh": selected,
        "storage_windows_kwh": windows,
        "soc_0000_kwh": float(soc[0]),
        "soc_2400_kwh": float(soc[-1]),
        "soc_terminal_difference_kwh": float(abs(soc[-1] - soc[0])),
        "power_balance_max_abs_residual_kwh": float(np.abs(residual).max()),
        "power_balance_rmse_kwh": float(np.sqrt(np.mean(residual ** 2))),
        "soc_min_kwh": float(soc.min()), "soc_max_kwh": float(soc.max()),
        "charge_total_kwh": float(charge.sum()), "discharge_total_kwh": float(discharge.sum()),
        "charge_period_count": int(charge_mask.sum()), "discharge_period_count": int(discharge_mask.sum()),
        "simultaneous_charge_discharge_periods": simultaneous,
        "charge_period_mean_price_yuan_per_kwh": charge_mean,
        "discharge_period_mean_price_yuan_per_kwh": discharge_mean,
        "price_gap_discharge_minus_charge_yuan_per_kwh": discharge_mean - charge_mean,
        "charge_intervals": intervals_from_mask(charge_mask),
        "discharge_intervals": intervals_from_mask(discharge_mask),
    }


def save_workbook(solution: dict) -> None:
    from result_workbooks import export_problem1
    export_problem1(solution)


def draw_main(raw: pd.DataFrame, price: np.ndarray, solution: dict) -> None:
    apply()
    hour = right_endpoint_hours()
    soc_hour = np.arange(N + 1) * DT
    fig, axes = combo_axes(2)
    ax, ax_soc = axes
    load_kw = raw["小区负载"].to_numpy(float)
    pv_kw = raw["光伏发电预测功率"].to_numpy(float)
    ax.plot(hour, load_kw, label="小区负载", **series_style("小区负载", marker=False))
    ax.plot(hour, pv_kw, label="光伏发电预测功率", **series_style("光伏发电预测功率", marker=False))
    price_style = series_style("电价（按5000 kW缩放）", marker=False)
    price_style.update(linestyle="--", linewidth=1.2)
    ax.plot(hour, price * POWER_LIMIT_KW, label=f"电价（按{POWER_LIMIT_KW:g} kW缩放）", **price_style)
    charge = solution["charge"] > 1e-5
    discharge = solution["discharge"] > 1e-5
    ax.fill_between(hour, 0, 1, where=charge, transform=ax.get_xaxis_transform(), color=PALETTE[2], alpha=0.16, label="充电时段")
    ax.fill_between(hour, 0, 1, where=discharge, transform=ax.get_xaxis_transform(), color=PALETTE[1], alpha=0.12, label="放电时段")
    ax.set(xlim=(0, 24), xlabel="时间（h）", ylabel="功率（kW）")
    ax.set_xticks(np.arange(0, 25, 4))
    ax.legend(loc="upper left", fontsize=8)
    ax.annotate(f"低价充电均价 {price[charge].mean():.3f} 元/kWh", xy=(2, load_kw.max() * 0.88), fontsize=8)

    ax_soc.plot(soc_hour, solution["soc"], label="储能SOC", **series_style("储能SOC", marker=False))
    lower_style = series_style("SOC下界", marker=False)
    lower_style.update(linestyle="--", linewidth=1.0)
    upper_style = series_style("SOC上界", marker=False)
    upper_style.update(linestyle=":", linewidth=1.0)
    ax_soc.axhline(SOC_LOWER, label="SOC下界", **lower_style)
    ax_soc.axhline(SOC_UPPER, label="SOC上界", **upper_style)
    ax_soc.fill_between(soc_hour, SOC_LOWER, solution["soc"], color=PALETTE[2], alpha=0.12)
    ax_soc.set(xlim=(0, 24), ylim=(0, CAPACITY_KWH), xlabel="时间（h）", ylabel="储电量SOC（kWh）")
    ax_soc.set_xticks(np.arange(0, 25, 4))
    ax_soc.legend(loc="upper left", fontsize=8)
    peak = int(np.argmax(solution["soc"]))
    ax_soc.annotate(f"峰值 {solution['soc'][peak]:.0f} kWh", xy=(soc_hour[peak], solution["soc"][peak]), xytext=(soc_hour[peak] - 5, solution["soc"][peak] - 1800), arrowprops={"arrowstyle": "->", "color": "#333333"}, fontsize=8)
    save_publication(fig, FIG / "problem1", dpi=300)
    plt.close(fig)


def draw_diagnostic(price: np.ndarray, load: np.ndarray, pv: np.ndarray, solution: dict, summary: dict) -> None:
    apply()
    hour = right_endpoint_hours()
    residual = solution["purchase"] + pv + ETA * solution["discharge"] - load - solution["charge"] / ETA
    fig, axes = combo_axes(2)
    ax, heat = axes
    ax.plot(hour, residual * 1e9, color=PALETTE[0], lw=1.1, label="平衡残差")
    ax.axhline(0, color="#444444", lw=0.9)
    ax.axhspan(-0.01 * 1e9, 0.01 * 1e9, color=PALETTE[2], alpha=0.15, label="±0.01 kWh阈值")
    ax.set(xlim=(0, 24), xlabel="时间（h）", ylabel="功率平衡残差（10^-9 kWh）")
    ax.set_xticks(np.arange(0, 25, 4))
    ax.legend(loc="upper left", fontsize=8)
    ax.text(0.03, 0.05, f"最大绝对残差={summary['power_balance_max_abs_residual_kwh']:.2e} kWh\nRMSE={summary['power_balance_rmse_kwh']:.2e} kWh", transform=ax.transAxes, fontsize=8, va="bottom")

    values = np.vstack([solution["purchase"], solution["charge"], solution["discharge"], solution["soc"][:-1]])
    normalized = values / np.maximum(values.max(axis=1, keepdims=True), 1.0)
    im = heat.imshow(normalized, aspect="auto", cmap="viridis", interpolation="nearest",
                     extent=(0, 24, 3.5, -0.5))
    heat.set(yticks=np.arange(4), yticklabels=["购电量", "充电量", "放电量", "SOC"], xlabel="时间片（每片10 min）")
    heat.set_xticks([0, 6, 12, 18, 24], ["0", "6", "12", "18", "24"])
    fig.colorbar(im, ax=heat, fraction=0.046, pad=0.04, label="各变量归一化值")
    save_publication(fig, FIG / "problem1_diagnostic", dpi=300)
    plt.close(fig)


def run_sensitivity(price: np.ndarray, load: np.ndarray, pv: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    capacity_scale = np.linspace(0.5, 1.0, 11)
    power_scale = np.array([0.4, 0.48, 0.56, 0.64, 0.72, 0.8, 0.88, 0.96, 1.0, 1.1, 1.2])
    costs = np.empty((len(power_scale), len(capacity_scale)))
    for i, power in enumerate(power_scale):
        for j, capacity in enumerate(capacity_scale):
            upper = SOC_INITIAL + (SOC_UPPER - SOC_INITIAL) * capacity
            lower = SOC_INITIAL - (SOC_INITIAL - SOC_LOWER) * capacity
            sol = solve_lp(price, load, pv, soc_lower=lower, soc_upper=upper, energy_limit=ENERGY_LIMIT * power)
            costs[i, j] = sol["cost"]
    return capacity_scale, power_scale, costs


def draw_sensitivity(capacity: np.ndarray, power: np.ndarray, costs: np.ndarray) -> dict:
    apply()
    cap_grid, power_grid = np.meshgrid(capacity, power)
    fig, axes = combo_axes(2, projections=("3d", None))
    min_idx = np.unravel_index(np.argmin(costs), costs.shape)
    mark = (cap_grid[min_idx], power_grid[min_idx], costs[min_idx])
    response_surface(cap_grid, power_grid, costs, ax=axes[0], xlabel="SOC可用容量系数", ylabel="功率上限系数", zlabel="购电费用（元）", mark=mark, colorbar=False)
    contour = axes[1].contourf(cap_grid, power_grid, costs, levels=14, cmap="coolwarm")
    axes[1].contour(cap_grid, power_grid, costs, colors="#555555", levels=7, linewidths=0.5)
    axes[1].scatter(mark[0], mark[1], color=PALETTE[1], s=28, label="名义最优配置")
    axes[1].set(xlabel="SOC可用容量系数", ylabel="功率上限系数")
    axes[1].legend(loc="upper right", fontsize=8)
    fig.colorbar(contour, ax=axes[1], label="全天购电费用（元）")
    fig.set_constrained_layout(False)
    fig.subplots_adjust(left=0.05, right=0.94, bottom=0.18, top=0.90, wspace=0.48)
    save_publication(fig, FIG / "problem1_sensitivity", dpi=300, formats=("png",))
    plt.close(fig)
    return {"capacity_scale_levels": capacity.tolist(), "power_scale_levels": power.tolist(),
            "cost_min_yuan": float(costs.min()), "cost_max_yuan": float(costs.max()),
            "nominal_cost_yuan": float(costs[power.tolist().index(1.0) if 1.0 in power else 0, capacity.tolist().index(1.0) if 1.0 in capacity else -1]),
            "surface_csv": "problem1_sensitivity.csv"}


def main() -> None:
    np.random.seed(SEED)
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    raw, price, load, pv = load_inputs()
    solution = solve_lp(price, load, pv)
    summary = summarise(solution, price, load, pv)
    save_workbook(solution)
    draw_main(raw, price, solution)
    draw_diagnostic(price, load, pv, solution, summary)
    cap, power, costs = run_sensitivity(price, load, pv)
    pd.DataFrame(costs, index=[f"功率系数_{v:.2f}" for v in power], columns=[f"容量系数_{v:.2f}" for v in cap]).to_csv(RES / "problem1_sensitivity.csv", encoding="utf-8-sig")
    summary["sensitivity"] = draw_sensitivity(cap, power, costs)
    with (RES / "problem1.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: summary[k] for k in ["solver_status", "daily_purchase_kwh", "daily_purchase_cost_yuan", "power_balance_max_abs_residual_kwh", "price_gap_discharge_minus_charge_yuan_per_kwh"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
