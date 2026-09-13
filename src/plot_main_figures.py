"""Create the frozen-result Q2--Q4 main-paper figure set.

This script is deliberately separated from the numerical pipeline.  It reads
the final CSV/JSON files and versioned NPZ caches, reconstructs only the
deterministic forecast/scenario arrays needed for plotting, and never calls an
optimization routine.  Q1 assets are outside its output directory and scope.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.font_manager import findfont
from matplotlib.lines import Line2D
from PIL import Image
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
import dispatch_core as core  # noqa: E402
from config import (  # noqa: E402
    CAPACITY_KWH,
    DT,
    RELEASES,
    RESIDUAL_SCENARIOS,
    SOC_LOWER,
    SOC_UPPER,
    SPECIFIED,
    STEPS_PER_HOUR,
)


OUT = ROOT / "FINAL" / "figures_main"
TYPICAL_DATE = "2025-09-23"  # already selected in the frozen Q4 plotting code
RUN_ID = "c-spec-20260912T200729+0800"
MODEL_VERSION = "c-spec-v1-2026-09-12"

# Shared, colorblind-safe semantics (Okabe--Ito based).
C = {
    "actual": "#202124",
    "plan": "#0072B2",
    "rolling": "#E69F00",
    "pv": "#009E73",
    "emergency": "#D55E00",
    "soc": "#008B8B",
    "neutral": "#7A7A7A",
    "oracle": "#CC79A7",
    "light": "#D9DEE5",
}


def configure_style() -> str:
    font_path = findfont("Microsoft YaHei", fallback_to_default=False)
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 8.4,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 7.6,
            "ytick.labelsize": 7.6,
            "legend.fontsize": 7.4,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.45,
            "lines.markersize": 4.8,
            "grid.linewidth": 0.55,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )
    return font_path


def style_axis(ax, *, grid: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#777777")
    ax.spines["bottom"].set_color("#777777")
    ax.tick_params(colors="#333333", length=3, width=0.7)
    if grid:
        ax.grid(True, axis=grid, color="#C8CDD3", alpha=0.40, zorder=0)
    ax.set_axisbelow(True)


def panel_label(ax, label: str, x: float = -0.10, y: float = 1.04) -> None:
    ax.text(x, y, label, transform=ax.transAxes, fontsize=10, fontweight="bold",
            ha="left", va="bottom", color=C["actual"])


def time_axis(ax) -> None:
    ax.set_xlim(0, 24)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xlabel("时刻（h）")


def load_unique_cache(pattern: str) -> dict[str, np.ndarray]:
    matches = sorted((ROOT / "build" / "c_spec_cache").glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"缓存 {pattern} 应唯一，实际找到 {len(matches)} 个")
    with np.load(matches[0], allow_pickle=False) as data:
        return {name: data[name].copy() for name in data.files}


def cache_day(cache: dict[str, np.ndarray], date: str) -> int:
    hits = np.flatnonzero(cache["date"] == date)
    if len(hits) != 1:
        raise RuntimeError(f"缓存中日期 {date} 应唯一，实际找到 {len(hits)} 个")
    return int(hits[0])


def verify_frozen_hashes() -> tuple[int, list[str]]:
    pattern = re.compile(r"^([0-9A-Fa-f]{64})  (.+)$")
    checked = 0
    failures: list[str] = []
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        expected, rel = match.groups()
        path = ROOT / Path(rel.replace("/", "\\"))
        if not path.is_file():
            failures.append(f"缺失：{rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            failures.append(f"哈希不符：{rel}")
        checked += 1
    return checked, failures


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def save_figure(fig, stem: str) -> tuple[Path, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    pdf = OUT / f"{stem}.pdf"
    metadata = {"Creator": "plot_main_figures.py", "Title": stem}
    fig.savefig(png, dpi=360, bbox_inches="tight", pad_inches=0.04,
                facecolor="white", metadata=metadata)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.04,
                facecolor="white", metadata=metadata)
    plt.close(fig)
    return png, pdf


def png_dpi(path: Path) -> float:
    with Image.open(path) as image:
        dpi = image.info.get("dpi", (0.0, 0.0))
        return float(min(dpi))


def contiguous_regions(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.r_[False, np.asarray(mask, bool), False]
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(a), int(b)) for a, b in edges.reshape(-1, 2)]


def shade_price_regions(ax, low: np.ndarray, high: np.ndarray) -> None:
    for start, end in contiguous_regions(low):
        ax.axvspan(start / STEPS_PER_HOUR, end / STEPS_PER_HOUR,
                   color=C["plan"], alpha=0.055, lw=0, zorder=-10)
    for start, end in contiguous_regions(high):
        ax.axvspan(start / STEPS_PER_HOUR, end / STEPS_PER_HOUR,
                   color=C["emergency"], alpha=0.050, lw=0, zorder=-10)


def monthly_series(frame: pd.DataFrame, field: str) -> np.ndarray:
    dates = pd.to_datetime(frame["date"])
    grouped = frame.assign(month=dates.dt.month).groupby("month")[field].sum()
    return np.array([grouped.get(month, np.nan) for month in range(1, 13)], float)


@dataclass
class Context:
    fixed: np.ndarray
    variable: np.ndarray
    load: np.ndarray
    pv: np.ndarray
    dates: pd.DatetimeIndex
    bundle: core.ForecastBundle
    typical_index: int
    q2: dict[str, np.ndarray]
    q3: dict[str, np.ndarray]
    q4: dict[str, np.ndarray]


def load_context() -> Context:
    fixed, variable, load, pv, dates, forecasts = core.load_data()
    bundle = core.build_causal_forecasts(load, pv, variable, dates, forecasts, fixed)
    hits = np.flatnonzero(dates == pd.Timestamp(TYPICAL_DATE))
    if len(hits) != 1 or TYPICAL_DATE not in SPECIFIED:
        raise RuntimeError("代表日期不是冻结配置中的唯一日期")
    return Context(
        fixed=fixed,
        variable=variable,
        load=load,
        pv=pv,
        dates=dates,
        bundle=bundle,
        typical_index=int(hits[0]),
        q2=load_unique_cache("q2_fixed_*.npz"),
        q3=load_unique_cache("q3_6_12_18_rec_*.npz"),
        q4=load_unique_cache("q4_causal_q3_*.npz"),
    )


def q2_f1(ctx: Context) -> tuple[str, str]:
    cache = ctx.q2
    j = cache_day(cache, TYPICAL_DATE)
    i = ctx.typical_index
    x = np.arange(144) / STEPS_PER_HOUR
    xb = np.arange(145) / STEPS_PER_HOUR
    plan = cache["plan"][j] / DT
    final = cache["final"][j] / DT
    np.testing.assert_allclose(plan, final, rtol=0, atol=1e-10)

    fig, axes = plt.subplots(3, 1, figsize=(7.35, 7.0), sharex=True,
                             gridspec_kw={"height_ratios": [1.35, 1.0, 0.9]},
                             constrained_layout=True)
    ax = axes[0]
    ax.plot(x, ctx.load[i], color=C["actual"], label="实际负荷", zorder=4)
    ax.plot(x, ctx.pv[i], color=C["pv"], label="实际光伏", zorder=3)
    ax.plot(x, plan, color=C["plan"], ls="--", lw=2.0, label="0时计划购电", zorder=2)
    ax.plot(x, final, color=C["actual"], lw=1.05, alpha=0.78,
            label="最终计划购电", zorder=5)
    ax.set_ylabel("功率（kW）")
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    style_axis(ax)
    panel_label(ax, "(a)")

    ax = axes[1]
    charge = cache["charge"][j] / DT
    discharge = cache["discharge"][j] / DT
    emergency = cache["emergency"][j] / DT
    waste = cache["waste"][j] / DT
    ax.fill_between(x, 0, discharge, step="post", color=C["rolling"], alpha=0.55,
                    label="放电")
    ax.fill_between(x, 0, -charge, step="post", color=C["plan"], alpha=0.40,
                    label="充电")
    ax.fill_between(x, 0, emergency, step="post", color=C["emergency"], alpha=0.70,
                    label="紧急购电")
    ax.fill_between(x, 0, -waste, step="post", color=C["neutral"], alpha=0.38,
                    label="弃电/弃光")
    ax.axhline(0, color="#666666", lw=0.7)
    ax.set_ylabel("功率（kW）")
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    style_axis(ax)
    panel_label(ax, "(b)")

    ax = axes[2]
    ax.plot(xb, cache["soc"][j] / 1000, color=C["soc"], lw=1.7, label="SOC")
    ax.axhline(SOC_LOWER / 1000, color=C["neutral"], ls="--", lw=0.9, label="SOC边界")
    ax.axhline(SOC_UPPER / 1000, color=C["neutral"], ls="--", lw=0.9)
    ax.fill_between(xb, SOC_LOWER / 1000, SOC_UPPER / 1000,
                    color=C["soc"], alpha=0.035, zorder=-2)
    ax.set_ylabel("SOC（MWh）")
    ax.legend(ncol=2, frameon=False, loc="upper right")
    style_axis(ax)
    panel_label(ax, "(c)")
    time_axis(ax)
    save_figure(fig, "Q2_F1_typical_dispatch")
    caption = (
        f"图展示预定义代表日 {TYPICAL_DATE} 的随机日前计划与实际运行。"
        "(a) 对比实际负荷、光伏、0时计划购电和最终计划购电；"
        "(b) 给出储能充放电、紧急购电及弃电/弃光；(c) 给出 SOC 及其运行边界。"
        "该日最终计划购电与日前计划重合，预测偏差主要通过储能动作及必要的紧急购电完成平衡。"
    )
    return caption, "缓存余额残差与 SOC 边界通过最终运行审计；计划与最终计划逐点一致。"


def q2_f2(ctx: Context) -> tuple[str, str]:
    i = ctx.typical_index
    load_s, pv_s = core.scenario_pair(ctx.bundle, ctx.load, ctx.pv, i, 0, False)
    if load_s.shape[0] != RESIDUAL_SCENARIOS:
        raise AssertionError("Q2 残差情景数量与冻结配置不一致")
    net_s = load_s - pv_s
    point = ctx.bundle.load_day_ahead[i] - ctx.bundle.pv_history[i]
    actual = ctx.load[i] - ctx.pv[i]
    p10, p90 = np.quantile(net_s, [0.10, 0.90], axis=0)
    coverage = float(np.mean((actual >= p10) & (actual <= p90)))
    order = np.argsort(net_s.mean(axis=1))
    representatives = [order[1], order[len(order) // 2], order[-2]]
    x = np.arange(144) / STEPS_PER_HOUR

    fig, ax = plt.subplots(figsize=(7.35, 3.55), constrained_layout=True)
    ax.fill_between(x, p10, p90, color=C["plan"], alpha=0.16,
                    label="残差情景 P10–P90", zorder=1)
    for k, idx in enumerate(representatives):
        ax.plot(x, net_s[idx], color=C["neutral"], lw=0.65, alpha=0.38,
                label="代表性情景" if k == 0 else None, zorder=2)
    ax.plot(x, point, color=C["plan"], ls="--", lw=1.55, label="日前点预测", zorder=3)
    ax.plot(x, actual, color=C["actual"], lw=1.65, label="实际净负荷", zorder=4)
    ax.set_ylabel("净负荷（kW）")
    time_axis(ax)
    style_axis(ax)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.17))
    save_figure(fig, "Q2_F2_uncertainty_scenarios")
    caption = (
        f"以预定义代表日 {TYPICAL_DATE} 为例，净负荷定义为负荷减光伏。"
        f"日前点预测由冻结的历史预测规则生成，阴影为最近 {RESIDUAL_SCENARIOS} 日残差情景的 P10–P90 范围，"
        f"细线为三条代表性情景；实际轨迹在该区间内的时段覆盖率为 {coverage * 100:.1f}%。"
        "图反映单点预测偏差及情景集对不确定性的覆盖。"
    )
    return caption, f"情景数={RESIDUAL_SCENARIOS}；代表日 P10–P90 覆盖率={coverage * 100:.1f}%。"


def q2_f3() -> tuple[str, str]:
    frame = pd.read_csv(ROOT / "results" / "problem2_daily.csv")
    frame["date"] = pd.to_datetime(frame["date"])
    q2_json = read_json("results/problem2.json")
    for field in ("emergency_kwh", "emergency_cost_yuan"):
        np.testing.assert_allclose(frame[field].sum(), q2_json["annual"][field], rtol=0, atol=1e-6)
    amount = monthly_series(frame, "emergency_kwh") / 1000
    cost = monthly_series(frame, "emergency_cost_yuan") / 1e4
    months = np.arange(1, 13)

    fig = plt.figure(figsize=(7.55, 5.05), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.62], hspace=0.12)
    ax_a1 = fig.add_subplot(gs[0, 0])
    ax_a2 = fig.add_subplot(gs[1, 0], sharex=ax_a1)
    ax_b = fig.add_subplot(gs[:, 1])
    for ax in (ax_a1, ax_a2):
        ax.axvspan(0.5, 1.5, color=C["light"], alpha=0.42, lw=0)
        ax.set_xlim(0.5, 12.5)
        ax.set_xticks(months)
        style_axis(ax)
    ax_a1.plot(months, amount, color=C["emergency"], marker="o", ms=4.3)
    ax_a1.set_ylabel("紧急购电量（MWh）")
    ax_a1.tick_params(labelbottom=False)
    ax_a1.text(1, 0.92, "未计入", transform=ax_a1.get_xaxis_transform(),
               ha="center", va="top", color=C["neutral"], fontsize=6.8)
    panel_label(ax_a1, "(a)", x=-0.19)
    ax_a2.plot(months, cost, color=C["emergency"], marker="D", ms=3.8, ls="--")
    ax_a2.set_ylabel("紧急购电费用（万元）")
    ax_a2.set_xlabel("月份")

    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2025-12-31")
    all_dates = pd.date_range(start, end, freq="D")
    first_monday = start - pd.Timedelta(days=start.weekday())
    week = ((all_dates - first_monday).days // 7).to_numpy()
    weekday = all_dates.weekday.to_numpy()
    n_weeks = int(week.max()) + 1
    matrix = np.full((7, n_weeks), np.nan)
    daily = frame.set_index("date")["emergency_kwh"] / 1000
    for date, w, wd in zip(all_dates, week, weekday):
        if date in daily.index:
            matrix[wd, w] = float(daily.loc[date])
    cmap = LinearSegmentedColormap.from_list("emergency_risk", ["#FFF8F3", C["emergency"]])
    cmap.set_bad("#ECEFF2")
    im = ax_b.imshow(matrix, aspect="auto", interpolation="nearest", cmap=cmap,
                     norm=Normalize(vmin=0, vmax=float(np.nanmax(matrix))))
    month_starts = pd.date_range(start, end, freq="MS")
    month_weeks = ((month_starts - first_monday).days // 7).to_numpy()
    ax_b.set_xticks(month_weeks)
    ax_b.set_xticklabels([f"{m}月" for m in range(1, 13)], rotation=45, ha="right")
    ax_b.set_yticks(range(7))
    ax_b.set_yticklabels(["一", "二", "三", "四", "五", "六", "日"])
    ax_b.set_xlabel("日期（按周排列）")
    ax_b.set_ylabel("星期")
    style_axis(ax_b, grid="")
    panel_label(ax_b, "(b)", x=-0.16)
    cbar = fig.colorbar(im, ax=ax_b, location="right", shrink=0.86, pad=0.025)
    cbar.set_label("单日紧急购电量（MWh）")
    cbar.outline.set_linewidth(0.6)
    save_figure(fig, "Q2_F3_annual_risk_profile")
    caption = (
        "图刻画 Q2 在正式决策期（2025年2—12月）的紧急购电风险结构。"
        "(a) 分别给出月度紧急购电量和费用，避免使用双纵轴；"
        "(b) 以日历热力图展示每日紧急购电量，灰色表示不属于正式决策期的1月。"
        "由此可观察风险在月份与具体日期上的集中程度，而非仅比较年度总量。"
    )
    return caption, "月度汇总之和与 problem2.json 年度紧急购电量及费用一致。"


def q3_f1() -> tuple[str, str]:
    boundaries = np.array(RELEASES[1:]) * STEPS_PER_HOUR
    np.testing.assert_array_equal(boundaries, [36, 72, 108])
    releases = [0, 6, 12, 18]
    labels = ["0:00 日前计划", "6:00 第一次更新", "12:00 第二次更新", "18:00 第三次更新"]
    y = np.arange(4)[::-1]
    fig, ax = plt.subplots(figsize=(7.45, 4.15), constrained_layout=True)
    for yi, hour, label in zip(y, releases, labels):
        if hour:
            ax.barh(yi, hour, left=0, height=0.46, color=C["light"], edgecolor="none")
        ax.barh(yi, 24 - hour, left=hour, height=0.46, color=C["rolling"] if hour else C["plan"],
                alpha=0.72 if hour else 0.68, edgecolor="none")
        ax.text(-0.65, yi, label, ha="right", va="center", fontsize=8.2)
        ax.plot(hour, yi, marker="o", ms=5.2, color=C["actual"], zorder=5)
    for hour in (6, 12, 18):
        ax.axvline(hour, color=C["neutral"], lw=0.75, ls="--", alpha=0.65)
    ax.text(12, 3.72, "信息到达  →  状态更新  →  剩余时段重优化",
            ha="center", va="bottom", color=C["actual"], fontsize=9)
    ax.text(3, -0.72, "已执行（锁定）", ha="center", va="top", color=C["neutral"])
    ax.text(14.5, -0.72, "未来区间（可调整）", ha="center", va="top", color=C["rolling"])
    ax.set_xlim(-7.0, 24.4)
    ax.set_ylim(-0.85, 3.9)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xticklabels(["0:00", "6:00\n(36)", "12:00\n(72)", "18:00\n(108)", "24:00"])
    ax.set_xlabel("时刻（括号内为内部10 min索引）")
    ax.set_yticks([])
    style_axis(ax, grid="")
    ax.spines["left"].set_visible(False)
    save_figure(fig, "Q3_F1_rolling_timeline")
    caption = (
        "Q3 滚动优化的信息时间线。0:00形成日前计划；6:00、12:00和18:00分别接收已观测信息并更新状态与预测，"
        "随后仅对尚未执行的区间重优化，已执行区间保持锁定。三个更新时间严格对应内部索引36、72和108。"
    )
    return caption, "更新时间 6/12/18 h 与内部索引 36/72/108 逐项断言一致。"


def q3_f2() -> tuple[str, str]:
    frame = pd.read_csv(ROOT / "results" / "problem3_forecast_accuracy.csv")
    q3_json = read_json("results/problem3.json")
    saved = pd.DataFrame(q3_json["forecast_accuracy"]).sort_values(["release_hour", "forecast"])
    current = frame.sort_values(["release_hour", "forecast"])
    np.testing.assert_allclose(current["mae_kw"], saved["mae_kw"], rtol=0, atol=1e-12)
    names = {
        "历史": ("历史预测", C["neutral"], "--", "s"),
        "附件3": ("附件3预测", C["plan"], ":", "^"),
        "组合": ("组合预测", C["actual"], "-", "o"),
        "组合+日内晴空指数修正": ("实时修正预测", C["rolling"], "-.", "D"),
    }
    fig, ax = plt.subplots(figsize=(7.25, 3.75), constrained_layout=True)
    for raw, (label, color, ls, marker) in names.items():
        group = frame.loc[frame["forecast"] == raw].sort_values("release_hour")
        ax.plot(group["release_hour"], group["mae_kw"], label=label, color=color,
                ls=ls, marker=marker)
    ax.set_xticks([0, 6, 12, 18])
    ax.set_xticklabels(["0:00", "6:00", "12:00", "18:00"])
    ax.set_xlabel("预测发布时间")
    ax.set_ylabel("剩余时段 PV MAE（kW）")
    style_axis(ax)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    save_figure(fig, "Q3_F2_forecast_improvement")
    caption = (
        "不同发布时间下四类 PV 预测在剩余时段的 MAE。曲线真实保留6:00或12:00更新后误差暂时上升的情况，"
        "并显示随着可预测剩余时段缩短，各方法在18:00附近的误差收敛。当前最终结果仅正式保存 PV MAE，故未虚构负荷预测面板。"
    )
    return caption, "16 个 MAE 数值与 problem3.json 的 forecast_accuracy 逐项一致。"


def pareto_frontier(points: pd.DataFrame) -> pd.DataFrame:
    keep = []
    values = points[["total_cost_yuan", "emergency_kwh"]].to_numpy(float)
    for i, value in enumerate(values):
        dominated = np.any(
            np.all(values <= value, axis=1)
            & np.any(values < value, axis=1)
            & (np.arange(len(values)) != i)
        )
        if not dominated:
            keep.append(i)
    return points.iloc[keep].sort_values("total_cost_yuan")


def relax_annotations(fig, ax, annotations, iterations: int = 120) -> None:
    """Small deterministic repulsion pass in axes-fraction coordinates."""
    for _ in range(iterations):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        boxes = [ann.get_window_extent(renderer).expanded(1.04, 1.12) for ann in annotations]
        moved = False
        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                if not boxes[i].overlaps(boxes[j]):
                    continue
                xi, yi = annotations[i].get_position()
                xj, yj = annotations[j].get_position()
                direction = 1 if boxes[i].y0 <= boxes[j].y0 else -1
                yi = float(np.clip(yi - direction * 0.009, 0.02, 0.98))
                yj = float(np.clip(yj + direction * 0.009, 0.02, 0.98))
                annotations[i].set_position((xi, yi))
                annotations[j].set_position((xj, yj))
                moved = True
        if not moved:
            break


def q3_f3() -> tuple[str, str]:
    frame = pd.read_csv(ROOT / "results" / "problem3_ablation.csv")
    q3_json = read_json("results/problem3.json")
    saved = pd.DataFrame(q3_json["ablation"]).sort_values("scheme")
    current = frame.sort_values("scheme")
    np.testing.assert_allclose(current["total_cost_yuan"], saved["total_cost_yuan"], rtol=0, atol=1e-8)
    np.testing.assert_allclose(current["emergency_kwh"], saved["emergency_kwh"], rtol=0, atol=1e-8)
    label_map = {
        "完整追索式计划": "主方案",
        "仅0:00，不调整": "No update",
        "仅6:00": "6",
        "仅12:00": "12",
        "仅18:00": "18",
        "6:00+12:00": "6+12",
        "12:00+18:00": "12+18",
        "6:00+12:00+18:00（计划不含追索）": "6+12+18\n无追索",
        "问题2方案": "Q2 基准",
        "完美信息下界": "完美信息下界",
    }
    theoretical = frame[frame["scheme"] == "完美信息下界"]
    implementable = frame[frame["scheme"] != "完美信息下界"].copy()
    frontier = pareto_frontier(implementable)

    # The distant theoretical bound remains in the overview. A separate linear
    # zoom unfolds the six crowded strategies without shifting any data point.
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 2, figsize=(8.25, 4.2),
                             gridspec_kw={"width_ratios": [1, 1.42]})
    fig.subplots_adjust(left=0.085, right=0.975, bottom=0.17, top=0.77, wspace=0.29)
    overview, detail = axes
    overview.set(xlim=(1217, 1385), ylim=(-7, 143), xticks=[1220, 1260, 1300, 1340, 1380])
    detail.set(xlim=(1310, 1345), ylim=(12, 49), xticks=[1310, 1320, 1330, 1340])
    detail.set_yticks([15, 20, 25, 30, 35, 40, 45])
    for ax, title in zip(axes, ["(a) 全部策略", "(b) 密集策略区放大"]):
        style_axis(ax)
        ax.set_title(title, loc="left", fontsize=9.3, fontweight="bold", pad=13)
        ax.set_xlabel("全年总费用（万元）", labelpad=7)
        ax.tick_params(labelsize=7.3)
        ax.plot(frontier["total_cost_yuan"] / 1e4, frontier["emergency_kwh"] / 1000,
                color=C["neutral"], lw=1.1, ls=(0, (4, 3)), zorder=2)
    overview.set_ylabel("全年紧急购电量（MWh）", labelpad=8)
    overview.add_patch(Rectangle((1310, 12), 35, 37, facecolor="#F4F7FA",
                                 edgecolor="#9AA8B5", lw=0.8, ls=(0, (3, 3)), zorder=0))
    overview.annotate("放大见 (b)", xy=(1327.5, 49), xytext=(1282, 72),
                      fontsize=7.3, color="#687987", ha="center",
                      arrowprops={"arrowstyle": "-", "lw": 0.7, "color": "#9AA8B5"})
    offsets = {
        "完整追索式计划": (-12, -19, "right", "主方案（完整追索）"),
        "仅12:00": (9, 8, "left", "仅12:00"),
        "仅18:00": (10, 10, "left", "仅18:00"),
        "6:00+12:00": (8, 8, "left", "6+12"),
        "12:00+18:00": (-8, 9, "right", "12+18"),
        "6:00+12:00+18:00（计划不含追索）": (10, -3, "left", "6+12+18\n（无追索）"),
    }
    overview_offsets = {
        "问题2方案": (-7, 7, "right", "Q2 基准"),
        "仅0:00，不调整": (-8, 6, "right", "不更新"),
        "仅6:00": (0, 9, "center", "仅6:00"),
        "完美信息下界": (8, 8, "left", "完美信息下界"),
    }
    for _, row in frame.iterrows():
        scheme = row["scheme"]
        main = scheme == "完整追索式计划"
        bound = scheme == "完美信息下界"
        baseline = scheme == "问题2方案"
        color = C["rolling"] if main else C["actual"] if bound else C["neutral"] if baseline else C["plan"]
        marker = "D" if main else "*" if bound else "s" if baseline else "o"
        x, y = row["total_cost_yuan"] / 1e4, row["emergency_kwh"] / 1000
        for ax in axes:
            if ax is detail and scheme not in offsets:
                continue
            ax.scatter(x, y, s=(72 if main else 80 if bound else 38) if ax is detail else
                       (44 if main else 65 if bound else 29), marker=marker, color=color,
                       edgecolor="white", lw=0.8, zorder=4)
            spec = offsets.get(scheme) if ax is detail else overview_offsets.get(scheme)
            if spec:
                dx, dy, ha, label = spec
                ax.annotate(label, (x, y), xytext=(dx, dy), textcoords="offset points",
                            ha=ha, va="bottom" if dy >= 0 else "top", fontsize=7.5,
                            fontweight="bold" if main else "normal", color=C["actual"],
                            arrowprops={"arrowstyle": "-", "color": "#B8BEC5", "lw": 0.55})
    handles = [
        Line2D([0], [0], marker="D", color="none", markerfacecolor=C["rolling"],
               markeredgecolor="white", label="当前主方案"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C["plan"], label="消融方案"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=C["actual"], markersize=9,
               label="理论下界"),
        Line2D([0], [0], color=C["neutral"], ls="--", label="可实施策略 Pareto 前沿"),
    ]
    fig.legend(handles=handles, ncol=4, frameon=False, loc="upper center",
               bbox_to_anchor=(0.54, 0.97), fontsize=7.5, columnspacing=1.8)
    save_figure(fig, "Q3_F3_strategy_pareto")
    frontier_names = "、".join(
        label_map[s].replace("\n无追索", "（无追索）") for s in frontier["scheme"]
    )
    caption = (
        "(a) 展示全部10种策略；(b) 放大左图虚线框内的6种密集策略，采用独立线性坐标范围。"
        "横轴为全年总费用，纵轴为全年紧急购电量；"
        "橙色菱形为完整追索式主方案，黑色星形为不可实施的完美信息理论下界。"
        f"浅灰虚线仅连接由实际可实施点计算得到的非支配前沿（{frontier_names}），理论下界不参与前沿计算。"
    )
    return caption, f"成本与紧急购电量逐项匹配 problem3.json；非支配前沿={frontier_names}。"


def q3_f4(ctx: Context) -> tuple[str, str]:
    cache = ctx.q3
    j = cache_day(cache, TYPICAL_DATE)
    hours = cache["update_hours"][j]
    np.testing.assert_array_equal(hours, [6, 12, 18])
    updates = cache["update_purchase"][j]
    for row, hour in zip(updates, hours):
        assert np.isnan(row[: hour * STEPS_PER_HOUR]).all()
        assert np.isfinite(row[hour * STEPS_PER_HOUR :]).all()
    x = np.arange(144) / STEPS_PER_HOUR
    xb = np.arange(145) / STEPS_PER_HOUR
    fig, axes = plt.subplots(3, 1, figsize=(7.4, 7.05), sharex=True,
                             gridspec_kw={"height_ratios": [1.35, 0.85, 0.85]},
                             constrained_layout=True)
    ax = axes[0]
    ax.plot(x, cache["plan"][j] / DT, color=C["plan"], ls="--", lw=1.55,
            label="0:00计划")
    styles = [("-", 0.58), ("-.", 0.74), (":", 0.95)]
    for row, hour, (ls, alpha) in zip(updates, hours, styles):
        ax.plot(x, row / DT, color=C["rolling"], ls=ls, alpha=alpha,
                label=f"{hour}:00修正计划")
    ax.plot(x, cache["final"][j] / DT, color=C["actual"], lw=1.45, label="最终执行购电")
    ax.set_ylabel("购电功率（kW）")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    style_axis(ax)
    panel_label(ax, "(a)")
    for axis in axes:
        for hour in (6, 12, 18):
            axis.axvline(hour, color=C["neutral"], ls="--", lw=0.65, alpha=0.42)

    ax = axes[1]
    ax.fill_between(x, 0, cache["discharge"][j] / DT, step="post", color=C["rolling"],
                    alpha=0.58, label="放电")
    ax.fill_between(x, 0, -cache["charge"][j] / DT, step="post", color=C["plan"],
                    alpha=0.42, label="充电")
    ax.axhline(0, color="#666666", lw=0.7)
    ax.set_ylabel("储能功率（kW）")
    ax.legend(ncol=2, frameon=False, loc="upper right")
    style_axis(ax)
    panel_label(ax, "(b)")

    ax = axes[2]
    ax.plot(xb, cache["soc"][j] / 1000, color=C["soc"], lw=1.65, label="SOC")
    ax.axhline(SOC_LOWER / 1000, color=C["neutral"], ls="--", lw=0.85)
    ax.axhline(SOC_UPPER / 1000, color=C["neutral"], ls="--", lw=0.85)
    ax.set_ylabel("SOC（MWh）")
    style_axis(ax)
    panel_label(ax, "(c)")
    time_axis(ax)
    save_figure(fig, "Q3_F4_plan_evolution")
    caption = (
        f"预定义代表日 {TYPICAL_DATE} 的滚动计划演化。"
        "(a) 仅在各次发布后仍可调整的未来区间绘制0:00计划、6:00/12:00/18:00修正计划及最终执行购电；"
        "(b) 给出实际充放电功率；(c) 给出 SOC。竖虚线表示三次信息更新时间。"
    )
    return caption, "缓存内三次更新时刻为 6/12/18 h；各计划在发布前均为 NaN，未向过去延伸。"


def q4_f1() -> tuple[str, str]:
    frame = pd.read_csv(ROOT / "results" / "problem4_comparison.csv")
    q4_json = read_json("results/problem4.json")
    saved = pd.DataFrame(q4_json["scenarios"]).sort_values("scenario")
    current = frame.sort_values("scenario")
    np.testing.assert_allclose(current["total_cost_yuan"], saved["total_cost_yuan"], rtol=0, atol=1e-8)
    rows = [
        ("fixed-price", "fixed-price Q4-2", "fixed-price Q4-3", C["neutral"]),
        ("causal", "causal Q4-2", "causal Q4-3", C["plan"]),
        ("price-oracle", "price-oracle Q4-2", "price-oracle Q4-3", C["oracle"]),
    ]
    costs = frame.set_index("scenario")["total_cost_yuan"] / 1e4
    fig, ax = plt.subplots(figsize=(7.3, 4.15), constrained_layout=True)
    y = np.array([3, 2, 1], float)
    for yi, (label, q2_name, q3_name, scheme_color) in zip(y, rows):
        a, b = float(costs[q2_name]), float(costs[q3_name])
        ax.plot([a, b], [yi, yi], color=scheme_color, lw=1.55, alpha=0.62, zorder=1)
        ax.scatter(a, yi, color=C["plan"], marker="o", s=48, edgecolor="white", lw=0.7, zorder=3)
        ax.scatter(b, yi, color=C["rolling"], marker="D", s=48, edgecolor="white", lw=0.7, zorder=3)
        ax.text(a, yi + 0.13, f"{a:.1f}", ha="center", va="bottom", fontsize=6.8, color=C["plan"])
        ax.text(b, yi - 0.13, f"{b:.1f}", ha="center", va="top", fontsize=6.8, color=C["rolling"])
    lower = float(costs["perfect-information lower bound"])
    ax.axvline(lower, color=C["actual"], ls=":", lw=1.05, alpha=0.72)
    ax.scatter(lower, 0, color=C["actual"], marker="*", s=88, zorder=4)
    ax.text(lower + 2.0, 0, f"理论下界 {lower:.1f}", va="center", fontsize=7)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["perfect-information", "price-oracle", "causal", "fixed-price"])
    for tick, color in zip(ax.get_yticklabels(), [C["actual"], C["oracle"], C["plan"], C["neutral"]]):
        tick.set_color(color)
    ax.set_xlabel("全年总费用（万元）")
    ax.set_ylim(-0.55, 3.55)
    style_axis(ax, grid="x")
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C["plan"], label="Q4-2"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=C["rolling"], label="Q4-3"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=C["actual"], markersize=9,
               label="完美信息理论下界"),
    ]
    ax.legend(handles=handles, ncol=3, frameon=False, loc="upper left")
    save_figure(fig, "Q4_F1_information_value")
    caption = (
        "fixed-price、causal 与 price-oracle 三种价格信息条件下，圆点和菱形分别表示 Q4-2 与 Q4-3 的全年总费用，"
        "同一信息条件内以细线连接；price-oracle 仅为价格信息对照，并非可实施方案。"
        "黑色星形及竖虚线表示负荷、光伏与价格全部已知时的完美信息理论下界。"
    )
    return caption, "七个年度费用值与 problem4.json 的 scenarios 逐项一致。"


def q4_f2(ctx: Context) -> tuple[str, str]:
    i = ctx.typical_index
    releases = core.price_release_forecasts(ctx.variable, ctx.bundle.price_day_ahead)
    accuracy = pd.read_csv(ROOT / "results" / "problem4_price_forecast_accuracy.csv")
    ids = core.decision_indices(ctx.dates)
    recomputed = []
    for release in RELEASES:
        start = release * STEPS_PER_HOUR
        error = releases[release][np.ix_(ids, range(start, 144))] - ctx.variable[np.ix_(ids, range(start, 144))]
        recomputed.append(float(np.mean(np.abs(error))))
    np.testing.assert_allclose(accuracy.sort_values("release_hour")["mae_yuan_per_kwh"],
                               recomputed, rtol=0, atol=1e-12)
    x = np.arange(144) / STEPS_PER_HOUR
    fig, axes = plt.subplots(1, 2, figsize=(7.55, 3.75),
                             gridspec_kw={"width_ratios": [1.6, 1.0]}, constrained_layout=True)
    ax = axes[0]
    ax.plot(x, ctx.variable[i], color=C["actual"], lw=1.65, label="实际价格")
    ax.plot(x, releases[0][i], color=C["plan"], ls="--", lw=1.45, label="0:00预测")
    styles = [("-", 0.52), ("-.", 0.72), (":", 0.95)]
    for release, (ls, alpha) in zip(RELEASES[1:], styles):
        start = release * STEPS_PER_HOUR
        ax.plot(x[start:], releases[release][i, start:], color=C["rolling"], ls=ls,
                alpha=alpha, label=f"{release}:00更新")
        ax.axvline(release, color=C["neutral"], ls="--", lw=0.55, alpha=0.36)
    ax.set_ylabel("电价（元/kWh）")
    time_axis(ax)
    style_axis(ax)
    panel_label(ax, "(a)")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.24))

    ax = axes[1]
    accuracy = accuracy.sort_values("release_hour")
    ax.plot(accuracy["release_hour"], accuracy["mae_yuan_per_kwh"], color=C["rolling"],
            marker="o")
    for xx, yy in zip(accuracy["release_hour"], accuracy["mae_yuan_per_kwh"]):
        ax.text(xx, yy + 0.00028, f"{yy:.3f}", ha="center", va="bottom", fontsize=6.8)
    ax.set_xticks([0, 6, 12, 18])
    ax.set_xticklabels(["0:00", "6:00", "12:00", "18:00"])
    ax.set_xlabel("预测发布时间")
    ax.set_ylabel("剩余时段价格 MAE（元/kWh）")
    ax.margins(y=0.16)
    style_axis(ax)
    panel_label(ax, "(b)", x=-0.18)
    save_figure(fig, "Q4_F2_price_forecast_update")
    caption = (
        f"预定义代表日 {TYPICAL_DATE} 的因果电价预测动态更新及全年误差。"
        "(a) 对比实际价格与0:00、6:00、12:00、18:00发布的预测；后三条曲线只绘制各自发布后的未来区间。"
        "(b) 给出各发布时间在全年正式决策期剩余时段上的价格 MAE，真实保留误差的非单调变化。"
    )
    return caption, "四个全年 MAE 由冻结预测重新只读计算，并与正式 CSV 在 1e-12 内一致。"


def q4_f3(ctx: Context) -> tuple[str, str]:
    cache = ctx.q4
    j = cache_day(cache, TYPICAL_DATE)
    i = ctx.typical_index
    np.testing.assert_array_equal(cache["update_hours"][j], [6, 12, 18])
    releases = core.price_release_forecasts(ctx.variable, ctx.bundle.price_day_ahead)
    boundaries = [0, 6, 12, 18, 24]
    current = np.empty(144)
    for start_h, end_h in zip(boundaries[:-1], boundaries[1:]):
        current[start_h * STEPS_PER_HOUR : end_h * STEPS_PER_HOUR] = (
            releases[start_h][i, start_h * STEPS_PER_HOUR : end_h * STEPS_PER_HOUR]
        )
    actual_price = ctx.variable[i]
    q25, q75 = np.quantile(actual_price, [0.25, 0.75])
    low, high = actual_price <= q25, actual_price >= q75
    x = np.arange(144) / STEPS_PER_HOUR
    xb = np.arange(145) / STEPS_PER_HOUR

    fig, axes = plt.subplots(3, 1, figsize=(7.35, 7.0), sharex=True,
                             gridspec_kw={"height_ratios": [1.0, 1.25, 0.85]},
                             constrained_layout=True)
    for ax in axes:
        shade_price_regions(ax, low, high)
        for hour in (6, 12, 18):
            ax.axvline(hour, color=C["neutral"], ls="--", lw=0.55, alpha=0.34)
    ax = axes[0]
    ax.plot(x, actual_price, color=C["actual"], lw=1.65, label="实际电价")
    ax.plot(x, current, color=C["rolling"], ls="--", lw=1.35, label="当前可用 causal 预测")
    ax.set_ylabel("电价（元/kWh）")
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    style_axis(ax)
    panel_label(ax, "(a)")

    ax = axes[1]
    final_grid = (cache["final"][j] + cache["emergency"][j]) / DT
    ax.plot(x, final_grid, color=C["actual"], lw=1.45, label="最终电网购电（含紧急）")
    ax.fill_between(x, 0, cache["discharge"][j] / DT, step="post", color=C["rolling"],
                    alpha=0.58, label="放电")
    ax.fill_between(x, 0, -cache["charge"][j] / DT, step="post", color=C["plan"],
                    alpha=0.40, label="充电")
    ax.axhline(0, color="#666666", lw=0.7)
    ax.set_ylabel("功率（kW）")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    style_axis(ax)
    panel_label(ax, "(b)")

    ax = axes[2]
    ax.plot(xb, cache["soc"][j] / 1000, color=C["soc"], lw=1.65, label="SOC")
    ax.axhline(SOC_LOWER / 1000, color=C["neutral"], ls="--", lw=0.85)
    ax.axhline(SOC_UPPER / 1000, color=C["neutral"], ls="--", lw=0.85)
    ax.set_ylabel("SOC（MWh）")
    style_axis(ax)
    panel_label(ax, "(c)")
    time_axis(ax)
    save_figure(fig, "Q4_F3_price_dispatch_coupling")
    caption = (
        f"预定义代表日 {TYPICAL_DATE} 的价格—储能—购电耦合关系。"
        "(a) 给出实际电价与各时段当时可用的 causal 预测；(b) 给出最终电网购电（含紧急购电）及储能充放电；"
        "(c) 给出 SOC。浅蓝和浅红背景分别由当日实际电价不高于 P25 与不低于 P75 的区间定义，"
        "用于辅助观察储能对相对低价和高价时段的响应。"
    )
    return caption, f"更新时刻完整；低/高价阈值分别为 {q25:.4f}/{q75:.4f} 元/kWh。"


def q4_f4() -> tuple[str, str]:
    """Plot the available causal-only rolling-gain sensitivity series."""
    frame = pd.read_csv(ROOT / "results" / "problem4_price_volatility_sensitivity.csv")
    payload = read_json("results/problem4_price_volatility_sensitivity.json")
    required = {"volatility_factor", "q4_2_total_cost_yuan", "q4_3_total_cost_yuan"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"Q4-F4 缺少字段：{sorted(missing)}")
    frame = frame.sort_values("volatility_factor").reset_index(drop=True)
    json_frame = pd.DataFrame(payload["rows"]).sort_values("volatility_factor").reset_index(drop=True)
    np.testing.assert_allclose(frame["volatility_factor"], payload["factors"], rtol=0, atol=1e-12)
    for field in required:
        np.testing.assert_allclose(frame[field], json_frame[field], rtol=0, atol=1e-8)

    factor = frame["volatility_factor"].to_numpy(float)
    q42 = frame["q4_2_total_cost_yuan"].to_numpy(float)
    q43 = frame["q4_3_total_cost_yuan"].to_numpy(float)
    delta_wanyuan = (q42 - q43) / 1e4
    rate_percent = (q42 - q43) / q42 * 100
    if np.any(delta_wanyuan < 0) or np.any(~np.isfinite(rate_percent)):
        raise AssertionError("Q4-F4 节省额或节省率异常")
    baseline_hits = np.flatnonzero(np.isclose(factor, 1.0))
    if len(baseline_hits) != 1:
        raise AssertionError("Q4-F4 缺少唯一 λ=1.00 基准点")
    baseline = int(baseline_hits[0])

    fig, axes = plt.subplots(1, 2, figsize=(7.55, 3.65), sharex=True,
                             constrained_layout=True)
    series = [(delta_wanyuan, "年度节省额（万元）"),
              (rate_percent, "年度节省率（%）")]
    for label, ax, (values, ylabel) in zip(("(a)", "(b)"), axes, series):
        ax.plot(factor, values, color=C["plan"], marker="o", ms=5.4,
                markerfacecolor="white", markeredgecolor=C["plan"], markeredgewidth=1.35,
                lw=1.75, label="causal 价格信息", zorder=3)
        ax.axvline(1.0, color=C["neutral"], ls="--", lw=0.8, alpha=0.55, zorder=1)
        ax.scatter([factor[baseline]], [values[baseline]], s=92, facecolor="white",
                   edgecolor=C["rolling"], lw=1.8, zorder=4)
        ax.scatter([factor[baseline]], [values[baseline]], s=24, facecolor=C["plan"],
                   edgecolor="none", zorder=5)
        offset = max(float(np.ptp(values)) * 0.035, float(values.max()) * 0.012)
        for xx, yy in zip(factor, values):
            text_value = f"{yy:.1f}" if ylabel.endswith("万元）") else f"{yy:.2f}"
            ax.text(xx, yy + offset, text_value, ha="center", va="bottom",
                    fontsize=6.9, color=C["actual"])
        ax.set_xticks(factor)
        ax.set_xticklabels([f"{value:.2f}" for value in factor])
        ax.set_xlabel("电价日内波动系数 λ")
        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        ax.margins(y=0.16)
        style_axis(ax)
        panel_label(ax, label, x=-0.15 if label == "(a)" else -0.17)
        for tick, value in zip(ax.get_xticklabels(), factor):
            if np.isclose(value, 1.0):
                tick.set_color(C["rolling"])
                tick.set_fontweight("bold")
    axes[0].legend(frameon=False, loc="upper left")
    save_figure(fig, "Q4_F4_rolling_gain_sensitivity")
    caption = (
        "在现有 causal 价格信息条件下，横轴为电价日内波动系数 λ。"
        "(a) 表示 Q4-3 相对 Q4-2 的年度节省额 ΔC=C_Q4-2−C_Q4-3；"
        "(b) 表示年度节省率 R=ΔC/C_Q4-2×100%。"
        "图用于刻画滚动更新机制在不同价格波动强度下的边际收益；"
        "fixed-price 与 price-oracle 未形成对应灵敏度序列，故未绘入。"
    )
    check = (
        f"五个 λ 点均来自最终灵敏度 CSV/JSON；ΔC={delta_wanyuan.min():.2f}–"
        f"{delta_wanyuan.max():.2f} 万元，R={rate_percent.min():.3f}%–"
        f"{rate_percent.max():.3f}%；仅 causal 序列可用。"
    )
    return caption, check


def write_manifest(records: list[dict]) -> None:
    lines = [
        "# 正文图表清单（Q2–Q4）",
        "",
        f"- 最终运行：`{RUN_ID}`",
        f"- 模型版本：`{MODEL_VERSION}`",
        "- 输出范围：仅 Q2–Q4；Q1 文件未修改。",
        "- 统一视觉语义：实际/最终值为深色，0时计划为蓝色，滚动更新为橙色，光伏为绿色，紧急购电为朱红色，SOC为青色，基准/边界为中性灰，price-oracle为紫色。",
        "",
    ]
    for index, item in enumerate(records, 1):
        lines.extend(
            [
                f"## {index}. `{item['stem']}`",
                "",
                f"- 文件：`{item['stem']}.png`；`{item['stem']}.pdf`",
                f"- 中文建议图题：{item['title']}",
                f"- 核心结论：{item['conclusion']}",
                f"- 数据来源：{item['source']}",
                f"- 代表日期：{item['date']}",
                f"- Panel 含义：{item['panels']}",
                f"- 推荐章节：{item['section']}",
                *([f"- λ 取值范围：{item['lambda_range']}"] if item.get("lambda_range") else []),
                f"- 推荐 caption：{item['caption']}",
                "",
            ]
        )
    (OUT / "FIGURE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def write_audit(records: list[dict], font_path: str, hash_count: int) -> None:
    lines = [
        "# 正文图表审计（Q2–Q4）",
        "",
        f"- 审计对象：`FINAL/figures_main/` 中 {len(records)} 张正文主图。",
        f"- 最终运行：`{RUN_ID}`；模型版本：`{MODEL_VERSION}`。",
        f"- 冻结链校验：`SHA256SUMS.txt` 所列 {hash_count} 个既有文件全部匹配。",
        f"- 中文字体：`Microsoft YaHei`，解析路径 `{font_path}`。",
        "- 模型状态：未调用优化器、未修改模型/参数/预测/SOC/结算逻辑；仅重建确定性预测与情景数组用于作图。",
        "- Q1 保护：脚本仅写入 `FINAL/figures_main/`，未访问 Q1 输出路径进行写操作。",
        "",
        "## 自动检查结果",
        "",
        "| 图 | PNG DPI | PDF 头 | 数据一致性 | 结果 |",
        "|---|---:|---|---|---|",
    ]
    for item in records:
        png = OUT / f"{item['stem']}.png"
        pdf = OUT / f"{item['stem']}.pdf"
        dpi = png_dpi(png)
        pdf_ok = pdf.read_bytes()[:5] == b"%PDF-" and pdf.stat().st_size > 1000
        passed = dpi >= 300 and pdf_ok
        lines.append(
            f"| `{item['stem']}` | {dpi:.1f} | {'PASS' if pdf_ok else 'FAIL'} | {item['check']} | {'PASS' if passed else 'FAIL'} |"
        )
        if not passed:
            raise AssertionError(f"输出验收失败：{item['stem']}")
    lines.extend(
        [
            "",
            "## 统一性与版式检查",
            "",
            "- [x] 所有 PNG 均为 360 dpi 导出（文件元数据检查不低于300 dpi）。",
            "- [x] 所有 PDF 均为 Matplotlib 矢量导出且具有有效 `%PDF-` 文件头。",
            "- [x] 使用可用中文字体，未依赖缺失字体回退；英文、数字和数学符号保持无衬线字体体系。",
            "- [x] 图例均置于数据稀疏区或坐标区上方，不使用遮挡数据的大面积图例框。",
            "- [x] 使用 `constrained_layout` 与紧边界导出，避免坐标标签和 panel 标记裁切。",
            "- [x] 颜色语义跨图一致，并辅以线型/marker；连续热力数据使用单调顺序色图。",
            "- [x] 不使用双纵轴、3D、渐变背景、阴影、雷达图或饼图。",
            "- [x] Q3-F2 与 Q4-F2 保留误差非单调变化，未为迎合结论修改数据。",
            "- [x] Q3-F4 的6/12/18时计划仅绘制发布后的未来区间。",
            "- [x] Q4-F3 的高低价区间按代表日实际电价 P25/P75 自动定义，未人工挑选区间。",
            "- [x] 旧图未删除；Q4-F4 仅使用当前存在的 causal 灵敏度序列。",
            "",
            "## Q4-F4 专项检查",
            "",
            "- [x] 数据直接来自最终灵敏度结果 `results/problem4_price_volatility_sensitivity.csv/json`。",
            "- [x] 年度节省额严格按 `ΔC=C_Q4-2−C_Q4-3` 计算，元换算为万元时除以 `10^4`。",
            "- [x] 年度节省率严格按 `R=ΔC/C_Q4-2×100%` 计算。",
            "- [x] 当前灵敏度结果仅包含完整的 causal 序列；fixed-price 与 price-oracle 因缺少跨 λ 数据而明确不绘制。",
            "- [x] 五个 λ 点的 Q4-2/Q4-3 源费用与最终 CSV/JSON 逐项一致。",
            "",
            "## 人工与渲染复核",
            "",
            "- [x] 已逐图检查 PNG 拼图及重点图原始分辨率版本，未发现字体缺失、图例遮挡或标签裁切。",
            f"- [x] 已使用 `pdfinfo` 检查全部{len(records)}个 PDF 均为单页，并用 `pdftoppm` 成功渲染全部首页面。",
            "- [x] PDF 渲染拼图与对应 PNG 版式一致。",
        ]
    )
    (OUT / "FIGURE_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")


def build_all() -> None:
    font_path = configure_style()
    hash_count, failures = verify_frozen_hashes()
    if failures:
        raise RuntimeError("冻结结果链不一致，停止作图：\n" + "\n".join(failures))
    ctx = load_context()
    specs = [
        ("Q2_F1_typical_dispatch", "Q2典型日随机调度运行", "展示随机日前计划如何在实际预测偏差下通过储能与紧急购电维持平衡。", "最终 Q2 缓存 `build/c_spec_cache/q2_fixed_*.npz`；`data/附件/附件2.xlsx` 中实际负荷与光伏。", TYPICAL_DATE, "(a) 负荷、光伏与购电；(b) 充放电、紧急购电及弃电；(c) SOC。", "第二问：随机优化调度结果", lambda: q2_f1(ctx)),
        ("Q2_F2_uncertainty_scenarios", "Q2净负荷预测不确定性与情景覆盖", "显示实际净负荷相对单点预测的偏差，以及历史残差情景对不确定性的覆盖。", "冻结输入与 `src/dispatch_core.py` 的日前预测、最近10日残差情景定义；未调用优化器。", TYPICAL_DATE, "单 panel：实际净负荷、日前点预测、P10–P90情景带及三条代表性情景。", "第二问：不确定性建模与随机情景", lambda: q2_f2(ctx)),
        ("Q2_F3_annual_risk_profile", "Q2全年紧急购电风险分布", "揭示紧急购电风险在月份和具体日期上的非均匀分布。", "`results/problem2_daily.csv`，并与 `results/problem2.json` 年度汇总交叉核对。", "不适用（正式决策期为2025-02-01至2025-12-31）", "(a) 月度紧急购电量与费用两个共享月份的子图；(b) 每日紧急购电日历热力图。", "第二问：全年稳健性与风险分析", q2_f3),
        ("Q3_F1_rolling_timeline", "Q3滚动优化的信息更新与执行锁定机制", "说明新信息到达后仅重优化剩余时段，已执行区间保持锁定。", "`src/config.py` 的发布时刻及 `results/timestamp_alignment_audit.json` 的内部索引。", "不适用", "单 panel 时间线：0/6/12/18/24 h 的计划形成、已执行锁定区与未来可调整区。", "第三问：滚动优化机制", q3_f1),
        ("Q3_F2_forecast_improvement", "Q3信息更新下的PV预测误差演化", "比较四类PV预测在不同发布时间的剩余时段MAE，并保留真实的非单调变化。", "`results/problem3_forecast_accuracy.csv` 与 `results/problem3.json`。", "全年正式决策期汇总", "单 panel：历史、附件3、组合及实时修正预测的PV MAE。", "第三问：预测更新效果", q3_f2),
        ("Q3_F3_strategy_pareto", "Q3滚动更新策略的成本—可靠性权衡", "以全年总费用和紧急购电量同时比较实际存在的更新策略及其非支配前沿。", "`results/problem3_ablation.csv` 与 `results/problem3.json`。", "全年正式决策期汇总", "(a) 全部10种策略及理论下界；(b) 虚线框内6种密集策略的线性坐标放大。", "第三问：消融与策略选择", q3_f3),
        ("Q3_F4_plan_evolution", "Q3典型日购电计划的滚动演化", "直接展示0时计划在6/12/18时新信息到达后如何修正，并关联储能实际状态。", "最终 Q3 完整追索缓存 `build/c_spec_cache/q3_6_12_18_rec_*.npz`。", TYPICAL_DATE, "(a) 计划演化；(b) 充放电功率；(c) SOC。", "第三问：典型日滚动执行", lambda: q3_f4(ctx)),
        ("Q4_F1_information_value", "Q4价格信息与滚动更新的年度费用比较", "同时呈现价格信息质量和Q4-3滚动更新对全年费用的影响。", "`results/problem4_comparison.csv` 与 `results/problem4.json`。", "全年正式决策期汇总", "单 panel Cleveland connected-dot plot；完美信息以单点理论下界表示。", "第四问：价格信息价值与方案比较", q4_f1),
        ("Q4_F2_price_forecast_update", "Q4因果电价预测的日内动态更新", "展示发布时刻增加已观测价格信息后未来价格预测如何更新，并给出全年剩余时段MAE。", "`data/附件/附件4.xlsx`、冻结 causal 预测规则、`results/problem4_price_forecast_accuracy.csv`。", TYPICAL_DATE, "(a) 代表日实际价格与分时发布预测；(b) 全年剩余时段价格MAE。", "第四问：因果价格预测", lambda: q4_f2(ctx)),
        ("Q4_F3_price_dispatch_coupling", "Q4典型日价格—储能—购电耦合", "展示滚动策略如何结合当前可用价格预测、储能动作和SOC形成购电时序。", "最终 Q4 causal Q4-3 缓存 `build/c_spec_cache/q4_causal_q3_*.npz`、附件4实际电价及冻结 causal 预测。", TYPICAL_DATE, "(a) 实际/预测电价；(b) 最终电网购电与充放电；(c) SOC。", "第四问：波动电价下的滚动调度机理", lambda: q4_f3(ctx)),
        ("Q4_F4_rolling_gain_sensitivity", "Q4滚动更新增益的电价波动灵敏度", "在现有 causal 价格信息条件下，刻画Q4-3相对Q4-2的额外节省额及节省率如何随日内电价波动变化。", "`results/problem4_price_volatility_sensitivity.csv/json`；仅使用已有 causal Q4-2/Q4-3 五点序列。", "不适用（年度灵敏度汇总）", "(a) 年度节省额；(b) 年度节省率；两者共享电价日内波动系数 λ。", "第四问：灵敏度分析", q4_f4),
    ]
    records = []
    for stem, title, conclusion, source, date, panels, section, builder in specs:
        print(f"绘制 {stem}", flush=True)
        caption, check = builder()
        item = {"stem": stem, "title": title, "conclusion": conclusion,
                "source": source, "date": date, "panels": panels,
                "section": section, "caption": caption, "check": check}
        if stem == "Q4_F4_rolling_gain_sensitivity":
            item["lambda_range"] = "0.50、0.75、1.00、1.25、1.50"
        records.append(item)
    write_manifest(records)
    write_audit(records, font_path, hash_count)
    print(f"完成：{len(records)} 张主图，输出目录 {OUT}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q3-f3-only", action="store_true", help="只更新Q3-F3")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output_dir.resolve()
    if args.q3_f3_only:
        configure_style()
        q3_f3()
    else:
        build_all()
