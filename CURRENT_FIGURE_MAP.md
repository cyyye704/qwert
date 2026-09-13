# 当前图表盘点与正文重构映射

- 盘点对象：`figures/` 中当前最终运行图集。
- 实际文件数：26（任务说明写“25 个”，目录实盘为 26 个；其中 Q1 含 PNG/PDF 成对文件）。
- 最终运行：`c-spec-20260912T200729+0800`，模型版本 `c-spec-v1-2026-09-12`。
- 一致性校验：`SHA256SUMS.txt` 所列 111 个文件全部匹配，无缺失、无哈希冲突。
- Q1 保护：原图内容、数据与绘图代码不改；用户加入 `new_figures_main/` 的成品副本已统一为 `Q1_Fx_语义名`。
- 后续补充：按用户最新要求，Q4-F4 仅使用已有完整 causal 灵敏度序列绘制；不补算 fixed-price 或 price-oracle。

## 旧图逐项处置

| 当前文件 | 标记 | 正文目标或处置说明 |
|---|---|---|
| `figures/problem1.png` | KEEP | Q1 已确认正文图，不修改 |
| `figures/problem1.pdf` | KEEP | Q1 已确认矢量图，不修改 |
| `figures/problem1_diagnostic.png` | KEEP | Q1 已确认图，不修改 |
| `figures/problem1_diagnostic.pdf` | KEEP | Q1 已确认矢量图，不修改 |
| `figures/problem1_sensitivity.png` | KEEP | Q1 已确认图，不修改 |
| `figures/P2_2025-03-20.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P2_2025-06-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P2_2025-09-23.png` | REDRAW | 数据映射至 `Q2_F1_typical_dispatch` |
| `figures/P2_2025-12-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/forecast_pv_mae.png` | REDRAW | 数据映射至 `Q3_F2_forecast_improvement` |
| `figures/P3_compare.png` | REDRAW | 数据映射至 `Q3_F3_strategy_pareto` |
| `figures/P3_2025-03-20.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P3_2025-06-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P3_2025-09-23.png` | MERGE | 计划、执行与 SOC 数据映射至 `Q3_F4_plan_evolution` |
| `figures/P3_2025-12-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P4_compare.png` | REDRAW | 年度比较数据映射至 `Q4_F1_information_value` |
| `figures/P4_price_forecast.png` | REDRAW | 数据映射至 `Q4_F2_price_forecast_update` |
| `figures/P4_price_volatility_sensitivity.png` | REDRAW | causal 年费用灵敏度数据转换为 `Q4_F4_rolling_gain_sensitivity` 的滚动增益指标 |
| `figures/P4-2_2025-03-20.png` | APPENDIX | 重复典型日调度图，保留原文件 |
| `figures/P4-2_2025-06-21.png` | APPENDIX | 重复典型日调度图，保留原文件 |
| `figures/P4-2_2025-09-23.png` | APPENDIX | 重复典型日调度图，保留原文件 |
| `figures/P4-2_2025-12-21.png` | APPENDIX | 重复典型日调度图，保留原文件 |
| `figures/P4-3_2025-03-20.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P4-3_2025-06-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |
| `figures/P4-3_2025-09-23.png` | MERGE | 购电、充放电与 SOC 数据映射至 `Q4_F3_price_dispatch_coupling` |
| `figures/P4-3_2025-12-21.png` | APPENDIX | 历史典型日，保留原文件，不进入正文主图集 |

## 新正文图的数据映射

| 目标图 | 来源 |
|---|---|
| `Q1_F1_optimal_dispatch` | 原成品 `problem1.png/pdf`；附件1与 `results/problem1.json` |
| `Q1_F2_solution_diagnostics` | 原成品 `problem1_diagnostic.png/pdf`；`results/problem1.json` |
| `Q1_F3_storage_sensitivity` | 原成品 `problem1_sensitivity.png`；`results/problem1_sensitivity.csv` 与 `results/problem1.json` |
| `Q2_F1_typical_dispatch` | 最终 Q2 缓存 `q2_fixed_*.npz`、附件 2 实际负荷/光伏；代表日采用已预定义的 2025-09-23 |
| `Q2_F2_uncertainty_scenarios` | 最终输入、冻结预测代码生成的 Q2 日前负荷/PV 点预测与最近 10 日残差情景；不调用优化器 |
| `Q2_F3_annual_risk_profile` | `results/problem2_daily.csv` |
| `Q3_F1_rolling_timeline` | `config.py` 中发布时刻及时间轴审计结果（6/12/18 h 对应内部索引 36/72/108） |
| `Q3_F2_forecast_improvement` | `results/problem3_forecast_accuracy.csv`（当前正式结果仅保存 PV MAE） |
| `Q3_F3_strategy_pareto` | `results/problem3_ablation.csv` |
| `Q3_F4_plan_evolution` | 最终缓存 `q3_6_12_18_rec_*.npz` 中的 0/6/12/18 时刻计划快照与最终执行序列；代表日 2025-09-23 |
| `Q4_F1_information_value` | `results/problem4_comparison.csv` |
| `Q4_F2_price_forecast_update` | 附件 4 实际电价、冻结的 causal 价格发布预测、`results/problem4_price_forecast_accuracy.csv`；代表日 2025-09-23 |
| `Q4_F3_price_dispatch_coupling` | 最终缓存 `q4_causal_q3_*.npz`、附件 4 实际电价及冻结 causal 价格预测；代表日 2025-09-23 |
| `Q4_F4_rolling_gain_sensitivity` | `results/problem4_price_volatility_sensitivity.csv/json` 中已有的 causal Q4-2/Q4-3 五点灵敏度序列；不补算缺失信息方案 |

本盘点保留旧图处置记录，并补充 `new_figures_main/` 的Q1统一命名映射；Q1图像内容未修改。
