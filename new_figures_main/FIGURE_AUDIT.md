# 正文图表审计（Q1–Q4）

- 审计对象：`new_figures_main/` 中 14 张正文主图（14 个 PNG、13 个 PDF）。
- 最终运行：`c-spec-20260912T200729+0800`；模型版本：`c-spec-v1-2026-09-12`。
- 冻结链校验：`SHA256SUMS.txt` 所列 111 个既有文件全部匹配。
- 中文字体：`Microsoft YaHei`，解析路径 `C:\Windows\Fonts\msyh.ttc`。
- 模型状态：未调用优化器、未修改模型/参数/预测/SOC/结算逻辑；仅重建确定性预测与情景数组用于作图。
- Q1 保护：只对用户加入 `new_figures_main/` 的5个Q1成品文件进行语义化重命名；未修改图像内容、结果数据或 `src/problem1.py`。

## 自动检查结果

| 图 | PNG DPI | PDF 头 | 数据一致性 | 结果 |
|---|---:|---|---|---|
| `Q1_F1_optimal_dispatch` | 500.0 | PASS | 图示口径与 `results/problem1.json` 中SOC边界、充放电均价和最优解汇总一致；重命名前后SHA256一致。 | PASS |
| `Q1_F2_solution_diagnostics` | 500.0 | PASS | 最大平衡残差2.27×10⁻¹³ kWh、RMSE 3.68×10⁻¹⁴ kWh与 `results/problem1.json` 一致；重命名前后SHA256一致。 | PASS |
| `Q1_F3_storage_sensitivity` | 500.0 | 不适用 | 参数范围及费用范围与 `results/problem1_sensitivity.csv`、`results/problem1.json` 一致；原始成品仅有PNG，未擅自补绘PDF；重命名前后SHA256一致。 | PASS |
| `Q2_F1_typical_dispatch` | 360.0 | PASS | 缓存余额残差与 SOC 边界通过最终运行审计；计划与最终计划逐点一致。 | PASS |
| `Q2_F2_uncertainty_scenarios` | 360.0 | PASS | 情景数=10；代表日 P10–P90 覆盖率=79.2%。 | PASS |
| `Q2_F3_annual_risk_profile` | 360.0 | PASS | 月度汇总之和与 problem2.json 年度紧急购电量及费用一致。 | PASS |
| `Q3_F1_rolling_timeline` | 360.0 | PASS | 更新时间 6/12/18 h 与内部索引 36/72/108 逐项断言一致。 | PASS |
| `Q3_F2_forecast_improvement` | 360.0 | PASS | 16 个 MAE 数值与 problem3.json 的 forecast_accuracy 逐项一致。 | PASS |
| `Q3_F3_strategy_pareto` | 360.0 | PASS | 成本与紧急购电量逐项匹配 problem3.json；非支配前沿=12+18、主方案、6+12+18（无追索）。 | PASS |
| `Q3_F4_plan_evolution` | 360.0 | PASS | 缓存内三次更新时刻为 6/12/18 h；各计划在发布前均为 NaN，未向过去延伸。 | PASS |
| `Q4_F1_information_value` | 360.0 | PASS | 七个年度费用值与 problem4.json 的 scenarios 逐项一致。 | PASS |
| `Q4_F2_price_forecast_update` | 360.0 | PASS | 四个全年 MAE 由冻结预测重新只读计算，并与正式 CSV 在 1e-12 内一致。 | PASS |
| `Q4_F3_price_dispatch_coupling` | 360.0 | PASS | 更新时刻完整；低/高价阈值分别为 0.4406/1.0080 元/kWh。 | PASS |
| `Q4_F4_rolling_gain_sensitivity` | 360.0 | PASS | 五个 λ 点均来自最终灵敏度 CSV/JSON；ΔC=18.04–64.34 万元，R=1.174%–4.757%；仅 causal 序列可用。 | PASS |

## 统一性与版式检查

- [x] 所有 PNG 的文件元数据均不低于300 dpi：Q1为500 dpi，Q2–Q4为360 dpi。
- [x] 现有13个 PDF 均具有有效 `%PDF-` 文件头；Q1-F3源成品未包含PDF，清单已明确标注。
- [x] 使用可用中文字体，未依赖缺失字体回退；英文、数字和数学符号保持无衬线字体体系。
- [x] 图例均置于数据稀疏区或坐标区上方，不使用遮挡数据的大面积图例框。
- [x] 使用 `constrained_layout` 与紧边界导出，避免坐标标签和 panel 标记裁切。
- [x] 颜色语义跨图一致，并辅以线型/marker；连续热力数据使用单调顺序色图。
- [x] Q2–Q4重构图不使用双纵轴、3D、渐变背景、阴影、雷达图或饼图；Q1-F3为用户已确认的既有三维响应面，仅纳入清单，未改图。
- [x] Q3-F2 与 Q4-F2 保留误差非单调变化，未为迎合结论修改数据。
- [x] Q3-F4 的6/12/18时计划仅绘制发布后的未来区间。
- [x] Q4-F3 的高低价区间按代表日实际电价 P25/P75 自动定义，未人工挑选区间。
- [x] Q1旧文件名已按统一体系迁移为 `Q1_Fx_语义名`；Q4-F4 仅使用当前存在的 causal 灵敏度序列。

## Q1 命名与内容完整性检查

| 原文件名 | 统一文件名 | SHA256（内容） |
|---|---|---|
| `problem1.png` / `problem1.pdf` | `Q1_F1_optimal_dispatch.png` / `.pdf` | `F91A0AD8…E9F2B` / `783DF0D8…170AD` |
| `problem1_diagnostic.png` / `.pdf` | `Q1_F2_solution_diagnostics.png` / `.pdf` | `137C9819…812B7` / `83D0EE68…F86B1` |
| `problem1_sensitivity.png` | `Q1_F3_storage_sensitivity.png` | `C3FAF0AB…CBFD5` |

- [x] 文件编号按正文顺序固定为F1最优调度、F2求解诊断、F3储能灵敏度。
- [x] 文件移动前后内容哈希一致，证明本次仅更名、未重新编码或修改像素。
- [x] Q1-F1与Q1-F2同时保留PNG和矢量PDF；Q1-F3按现有资产仅保留PNG。
- [x] Q1数据来源均指向最终 `results/problem1.json`，灵敏度另与 `results/problem1_sensitivity.csv` 对应。

## Q4-F4 专项检查

- [x] 数据直接来自最终灵敏度结果 `results/problem4_price_volatility_sensitivity.csv/json`。
- [x] 年度节省额严格按 `ΔC=C_Q4-2−C_Q4-3` 计算，元换算为万元时除以 `10^4`。
- [x] 年度节省率严格按 `R=ΔC/C_Q4-2×100%` 计算。
- [x] 当前灵敏度结果仅包含完整的 causal 序列；fixed-price 与 price-oracle 因缺少跨 λ 数据而明确不绘制。
- [x] 五个 λ 点的 Q4-2/Q4-3 源费用与最终 CSV/JSON 逐项一致。

## 人工与渲染复核

- [x] 已逐图检查 PNG 拼图及重点图原始分辨率版本，未发现字体缺失、图例遮挡或标签裁切。
- [x] 已使用 `pdfinfo` 检查现有13个 PDF 均为单页，并用 `pdftoppm` 成功渲染全部首页面。
- [x] PDF 渲染拼图与对应 PNG 版式一致。

## Q3-F3 版式更新（2026-09-13）

- 输出位于当前图集目录 `new_figures_main/`；只单独重新导出 Q3-F3。
- 改为全局比较与密集区域放大双面板：左图包含全部10个点，右图重复展示框内6个点；无删点、移点、抖动、断轴或非线性缩放。
- 右图范围：1310–1345万元、12–49 MWh，与左图标出的矩形区域相同。
- 源 CSV/JSON 哈希与冻结清单一致，年度费用与紧急购电量逐项比对通过；可实施策略 Pareto 前沿未改变。
- PNG：2855×1372像素、360 dpi；PDF：单页矢量输出，已成功渲染并检查标签与图例。
- 修改前的 PNG/PDF 保留于 `tmp/Q3_F3_before_redesign/`。
- 单图复现：`.venv_figures/Scripts/python.exe src/plot_main_figures.py --q3-f3-only --output-dir new_figures_main`。
