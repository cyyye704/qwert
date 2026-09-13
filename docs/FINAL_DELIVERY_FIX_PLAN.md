# 最终交付链收口：阶段 A 只读审计与最小修复方案

> 历史实施方案，已执行完毕。2026-09-12 后续决定已取消其中的“源码哈希冻结”约束；文内基线哈希仅保留作当时审计记录，不再是活动门禁，也不得用于阻止后续模型修改。当前规则以 `src/build_final_manifest.py` 为准。

生成时间：2026-09-12（Asia/Shanghai）  
唯一候选模型版本：`c-spec-v1-2026-09-12`  
阶段状态：**A 阶段完成，B 阶段未开始**  
执行闸门：只有收到用户明确回复 **“继续执行”** 后，才允许修改源码、运行模型、覆盖工作簿、移动历史文件或建立 `FINAL/`。

## 0. 本阶段实际操作边界

本阶段只进行了文件读取、调用链分析、工作簿结构读取、哈希计算和方案编制：

- 未修改任何既有文件；
- 未运行 Q1–Q4 模型；
- 未运行全年计算；
- 未清理缓存；
- 未覆盖五个根目录工作簿；
- 未移动或删除历史文件；
- 本文件 `FINAL_DELIVERY_FIX_PLAN.md` 是本阶段唯一新增文件。

## 1. 冻结边界与源码基准

### 1.1 阶段 B 禁止修改的模型事实源

下列文件定义当前冻结模型。阶段 B 必须保持其内容哈希不变；若任何一项发生变化，立即停止，不得继续封包。

| 文件 | 当前 SHA-256 | 冻结内容 |
|---|---|---|
| `src/config.py` | `BCB083165EBDBFA985055934C61C6DE36A8E8ABAA130FFD5FE190E77079CEDB0` | 模型版本、参数、发布时刻、SOC/效率/费用常量 |
| `src/dispatch_core.py` | `924B714A96545AC249B4F92395E76463DBD3F1C7710D041D2FB4ADD05D30994C` | 数据读取、预测、随机 LP、实时执行、Q2/Q3/Q4 调度与结算 |
| `src/scenario_cache.py` | `6AECC945F1FB5FEEAB082280A832EC3E69F6764AE9DEC62668500F117F6AF2E1` | 当前数值缓存格式、物理断言和缓存键 |
| `src/problem1.py` | `33E740340C88B8A5292E184D6B059D7165FD52D03D6214EF461564DAF976A428` | Q1 LP、汇总、图和当前输出数据结构 |
| `src/problem2.py` | `2D96B67106A633A5DE9E06965A6F5F2CAD28073CBC5A09D6A1441C8F6694C868` | Q2 当前方案与输出 |
| `src/problem3.py` | `1A8535A13EDA529EDA93CD09088759885A41DB47A06FEF7A7EDF732AAFAA4B65` | Q3 6/12/18 滚动方案、消融与输出 |
| `src/problem4.py` | `F76C9BAEA363D05FC5ABEDE7EA3DC82CB76E5875420B509F16373367FE443780` | Q4 因果/固定价/oracle 场景与输出 |

说明：`src/problem1.py` 当前因缺少工作簿接口而不能完整执行，但这不需要修改其中的 LP、参数或求解过程；修复应发生在导出器与总入口。

### 1.2 允许改变、但必须证明不改变数值的工程文件

| 文件 | 当前 SHA-256 | 可修改范围 |
|---|---|---|
| `src/time_axis.py` | `EED68B66CA556D24604FB392B2AB4A56DCD711D1ADB854AFD5DB021C543FEBEF` | 只改最终显示标签 `24:00` 为 `0:00+1`，禁止改内部索引与数值坐标 |
| `src/result_workbooks.py` | `688A1A6DF433E8043CFEA9A02CB379882543D5738BB70F2962160A053753A4E7` | Q1 接口、模板内写入、样式保留、输出路径；禁止重排数组 |
| `src/build_summary.py` | `25C5ACAE04B8C001F0705753400F109D6946532858BAD69F4C54C0A4D86AC744` | 纳入 Q1、五工作簿、最新测试/图/哈希 |
| `run_all.py` | `562B3E764FA118BD27B5C65196F3F55B045BF8F5376F33B5B37BF8AACD7EF013` | 完整入口、执行顺序、验收与 manifest 调用 |
| `src/test_c_spec.py` | 当前活动测试 | 更新标签断言，不改模型断言 |
| `src/test_timestamp_alignment.py` | 当前活动时间轴测试 | 删除已经失效的“跨日搬移”验收逻辑，改为标签修正与 j→j 断言 |
| `src/audit_timestamp_alignment.py` | 当前活动时间轴审计 | 重新审计最终标签，保留并解释旧结论为何失效 |

## 2. A1：当前真实生成链

### 2.1 当前总入口的真实行为

当前命令入口为：

```text
python run_all.py [--fresh]
```

真实调用顺序如下：

```text
run_all.main
├─ 可选 cleanup()
├─ subprocess: src/test_c_spec.py
├─ subprocess: src/validate_typical_days.py
├─ dispatch_core.load_data()
├─ dispatch_core.build_causal_forecasts(...)
├─ problem2.run_problem2(...)
├─ problem3.run_problem3(include_ablations=False)
├─ problem4.run_problem4(include_oracles=False)
├─ problem3.run_problem3(include_ablations=True)
├─ problem4.run_problem4(include_oracles=True)
└─ subprocess: src/build_summary.py
```

已确认的入口缺陷：

1. 总入口没有调用 Q1。
2. 总入口不调用 `test_timestamp_alignment.py`、`audit_timestamp_alignment.py` 或 `audit_q3_forecast_alignment.py`。
3. Q3 会先写出一次仅含主方案的 CSV/JSON/图/工作簿，再由全消融调用覆盖。
4. Q4 会先写出一次仅含 4 场景的 CSV/JSON/图/工作簿，再由 oracle 全量调用覆盖。
5. 如果进程在两次调用之间中断，就会留下当前项目中已经出现过的“不完整结果伪装成最新结果”状态。

### 2.2 Q1 入口

直接入口：`python src/problem1.py`

```text
problem1.main
├─ np.random.seed(SEED)
├─ load_inputs()
│  ├─ 读取 data/附件/附件1.xlsx / Sheet1
│  └─ validate_right_endpoint_axis(...)
├─ solve_lp(price, load, pv)
├─ summarise(solution, ...)
├─ save_workbook(solution)
│  └─ from result_workbooks import export_problem1   ← 当前不存在，执行在此中断
├─ draw_main(...)             → figures/problem1.png、problem1.pdf
├─ draw_diagnostic(...)       → figures/problem1_diagnostic.png/pdf
├─ run_sensitivity(...)
├─ 写 results/problem1_sensitivity.csv
├─ draw_sensitivity(...)      → figures/problem1_sensitivity.png
└─ 写 results/problem1.json
```

当前事实：Q1 的优化与汇总均已定义；断点是纯导出接口缺失。由于工作簿写出发生在图和 JSON 之前，当前 `problem1.main()` 会在产生完整 Q1 产物前失败。

### 2.3 Q2 入口

直接入口：`python src/problem2.py`  
总入口：`run_all.main → run_problem2(use_cache=True, data=data, bundle=bundle)`

```text
problem2.run_problem2
├─ dispatch_core.load_data() / 使用注入 data
├─ build_causal_forecasts() / 使用注入 bundle
├─ scenario_cache.run_continuous(
│     label="q2_fixed",
│     options={model, price="attachment1"},
│     runner=dispatch_core.run_q2_day)
├─ dispatch_core.q2_metrics(...)
├─ reporting.annual_summary(...)
├─ 写 results/problem2_daily.csv
├─ reporting.plot_typical(..., prefix="P2") → 4 张 P2 图
├─ reporting.write_json(...) → results/problem2.json
└─ result_workbooks.export_records(..., "result2.xlsx", rolling=False)
```

### 2.4 Q3 入口

直接入口：`python src/problem3.py`，默认 `include_ablations=True`。  
总入口当前调用两次：先 `False`，后 `True`。

```text
problem3.run_problem3
├─ 对 ordered 中每个方案调用 _run_scheme(...)
│  └─ scenario_cache.run_continuous(...)
│     └─ dispatch_core.run_q3_day(...)
│        ├─ 0:00 随机计划
│        ├─ release 6  → boundary 36
│        ├─ release 12 → boundary 72
│        └─ release 18 → boundary 108
├─ 可选 Q2 对照与 perfect_fixed 下界
├─ 写 results/problem3_ablation.csv
├─ 写 results/problem3_daily.csv
├─ 写 results/problem3_forecast_accuracy.csv
├─ _plot_ablation(...)              → figures/P3_compare.png
├─ _forecast_stats(...)             → figures/forecast_pv_mae.png
├─ reporting.plot_typical(...,"P3") → 4 张 P3 图
├─ 写 results/problem3.json
└─ export_records(...,"result3.xlsx",rolling=True)
```

当前 `run_q3_day` 的数据事实：

- `plan["purchase"]` 是 0:00 原计划；
- `updates` 保存 6/12/18 三次从边界开始的计划快照，边界前为 NaN；
- `final_purchase` 是当天实际采用的最终分段购电序列；
- 发布边界已经是 36/72/108，不需要也不允许修改。

### 2.5 Q4 入口

直接入口：`python src/problem4.py`，默认 `include_oracles=True`。  
总入口当前调用两次：先 `False`，后 `True`。

```text
problem4.run_problem4
├─ build/复用 causal、fixed、oracle 价格预报
├─ run_continuous("q4_causal_q2", ...) → run_q2_day
├─ run_continuous("q4_causal_q3", ...) → run_q3_day(boundary 36/72/108)
├─ 可选 q4_oracle_q2 / q4_oracle_q3 / perfect_variable
├─ 复用/生成 fixed Q2 与 fixed Q3
├─ 写 4 或 7 个 daily CSV
├─ export_records(...,"result4-2.xlsx",rolling=False)
├─ export_records(...,"result4-3.xlsx",rolling=True)
├─ 写 problem4_price_forecast_accuracy.csv
├─ 写 problem4_comparison.csv
├─ _plot_comparison(...)             → P4_compare、P4_price_forecast
├─ reporting.plot_typical(...,"P4-2"/"P4-3") → 8 张图
└─ 写 results/problem4.json
```

### 2.6 Summary 入口

直接入口：`python src/build_summary.py`  
总入口：Q2–Q4 完成后由 `run_all.checked("build_summary.py")` 调用。

当前真实输入：

- `results/problem2.json`
- `results/problem3.json`
- `results/problem4.json`
- Q2/Q3/Q4 的 8 个 daily CSV
- `result2.xlsx`、`result3.xlsx`、`result4-2.xlsx`、`result4-3.xlsx`
- `results/c_spec_unit_tests.json`
- Q2/Q3/Q4 JSON 中登记的图路径

当前真实输出：

- `summary.json`
- `results/summary.md`
- `results/final_audit.json`

当前缺口：Q1 JSON、Q1 图和 `result1.xlsx` 均没有进入 summary/audit；时间轴测试/审计也没有成为最终审计的硬闸门。

### 2.7 Figures 入口

| 问题 | 生成函数 | 输出 |
|---|---|---|
| Q1 | `problem1.draw_main`、`draw_diagnostic`、`draw_sensitivity` | `problem1.png/pdf`、`problem1_diagnostic.png/pdf`、`problem1_sensitivity.png` |
| Q2 | `reporting.plot_typical(...,"P2")` | 4 个指定日期的 P2 PNG |
| Q3 | `_plot_ablation`、`_forecast_stats`、`plot_typical(...,"P3")` | P3 比较图、PV MAE 图、4 个典型日图 |
| Q4 | `_plot_comparison`、`plot_typical(...,"P4-2/P4-3")` | 2 个比较/价格图、8 个典型日图 |

图使用的数组均直接来自当前记录；本轮时间标签修正只涉及文本标签，不应改图的数值数组。Q1 主图使用原始数据的右端点数值坐标，Q2–Q4 典型日图使用内部区间起点坐标；两者的物理语义已经明确，不需要移动数组。

### 2.8 五个工作簿导出入口

| 工作簿 | 当前调用 | 当前状态 |
|---|---|---|
| `result1.xlsx` | `problem1.save_workbook → export_problem1` | 接口缺失，断链 |
| `result2.xlsx` | `problem2.run_problem2 → export_records(..., rolling=False)` | 可生成，但当前导出器重建/扩展表结构和表头样式 |
| `result3.xlsx` | `problem3.run_problem3 → export_records(..., rolling=True)` | 可生成；“调整购电量”被改成每日期三行并增加“调整时刻”列，偏离官方一日一行模板 |
| `result4-2.xlsx` | `problem4.run_problem4 → export_records(..., rolling=False)` | 同 Q2 |
| `result4-3.xlsx` | `problem4.run_problem4 → export_records(..., rolling=True)` | 同 Q3 |

当前 `export_records` 虽然从官方模板加载，但随即执行删除行、删除/插入列、统一蓝色表头、增加 `每日汇总`/`最终购电量` 工作表等操作，不能称为“尽量保留官方模板格式”。正式提交导出器应改为以模板原有工作表为骨架，只填值、修正 144 个标签，并在确需扩行时复制模板样式。

### 2.9 时间标签的唯一生成位置

当前唯一基础实现位于 `src/time_axis.py`：

```text
boundary_label(minutes)
└─ slot_label(index)
   └─ all_slot_labels()
```

使用点：

- Q1 `time_labels()` 直接返回 `all_slot_labels()`；
- Q2–Q4 `export_records` 使用 `all_slot_labels()` 写详细表头；
- Q3/Q4 调整/最终详细表也使用同一列表；
- `interval_label(start,end)` 用于储能汇总和紧急购电连续区间；
- `test_c_spec.py`、时间轴测试/审计和 `build_summary.py` 均依赖该事实源。

当前唯一标签差异：`boundary_label(1440)` 返回 `24:00`，所以 `slot_label(143)` 为 `23:50-24:00`；冻结要求为 `23:50-0:00+1`。内部索引、`interval_start_index`、`right_endpoint_hours`、`interval_start_hours` 均已正确，不得修改。

### 2.10 当前测试入口

| 入口 | 当前覆盖 | 当前缺口 |
|---|---|---|
| `src/test_c_spec.py` | 参数、输入形状、因果预测、SOC、平衡、36/72/108、结算 | 仍断言最后标签为 `23:50-24:00` |
| `src/validate_typical_days.py` | 四个指定日期的 Q2/Q3/Q4 独立求解 | 不含 Q1，不检查工作簿 |
| `src/test_timestamp_alignment.py` | 验证旧模板标签导致的跨日偏移，并故意输出 `final_workbooks_ready=false` | 整套验收前提已被本轮确认的新口径推翻 |
| `src/audit_timestamp_alignment.py` | 记录旧标签位置 j 对应 internal j+1 的冲突 | 必须改为“模板只改标签、数据位置 j 对应 internal j” |
| `src/audit_q3_forecast_alignment.py` | Q3 预报发布边界/未来数据隔离 | 当前未纳入 `run_all.py` |
| `src/build_summary.py` | Q2–Q4 数值、CSV/工作簿、图、物理断言 | 不含 Q1、五工作簿统一标签和新时间轴审计 |

## 3. 官方模板结构只读审计

官方模板位于 `data/附件/附件5/`，阶段 A 只读打开，未修改。

| 文件 | 官方工作表 | 详细表布局 |
|---|---|---|
| `result1.xlsx` | `计划购电量`、`充放电量` | Q1 计划表为 A2:A145 标签、B2:B145 数值 |
| `result2.xlsx` | `计划购电量`、`充放电量`、`紧急购电量` | 计划表为每日期一行，B:EO 共 144 个详细位置 |
| `result3.xlsx` | `计划购电量`、`调整购电量`、`充放电量`、`紧急购电量` | 计划和调整表均为每日期一行、144 个详细位置、全天量/费用两列 |
| `result4-2.xlsx` | 与 result2 相同 | 同 Q2 |
| `result4-3.xlsx` | 与 result3 相同 | 同 Q3 |

旧模板的 144 个标签从 `0:10-0:20` 开始，以次日 `0:00-0:10(+1)` 结束。阶段 B 只能把每个位置的显示文本改为 `all_slot_labels()[j]`，不得移动该位置的数据。

Q3/Q4-3 的正式“调整购电量”表应恢复官方的一日一行结构：

- 144 个详细位置写当前记录的 `final_purchase[j]`；
- “全天计划购电量”写 `final_purchase.sum()`；
- “全天计划购电费”写 `plan_cost_yuan + adjustment_cost_yuan`；
- 三次发布快照继续保留在 JSON/缓存/审计证据中，不在正式模板中增设“调整时刻”列或三行结构；
- 这只是把当前活动记录映射到官方输出格式，不改变 0:00 计划、三次更新、最终执行数组或结算公式。

该映射将在阶段 B 开始前由用户通过“继续执行”一并确认；若用户不认可，应停在输出格式决策，不得触碰模型。

## 4. A2：最小修复方案

### 4.1 必须修改/新增的文件

| 文件 | 具体修改 | 工程修复而非模型修改的理由 | 是否改变模型数值 |
|---|---|---|---|
| `src/time_axis.py` | 使日终边界显示为 `0:00+1`；令 `slot_label(143)` 精确为 `23:50-0:00+1`。保持 N=144、索引、起点/右端点数值坐标不变 | 只改变字符串格式 | 否 |
| `src/result_workbooks.py` | 新增与当前 Q1 `solution` 字典兼容的 `export_problem1`；为两类导出器增加可选输出路径；从官方模板 fresh load 后原位填值；统一用 `all_slot_labels()` 覆写 144 个标签；复制模板样式扩展行；正式工作簿仅保留官方 sheet 集合；不得调用 shift/roll/offset | 纯 Excel 映射与接口恢复 | 否；工作簿二进制和标签会变，数值数组不得变 |
| `run_all.py` | 在 Q2 前执行 Q1；把 Q3 改为一次 `include_ablations=True`，Q4 改为一次 `include_oracles=True`；生成五工作簿后运行新时间轴测试/审计；最后运行 summary 和 manifest；扩充显式 `--fresh` 清单但先归档再清理 | 调整生成顺序、避免阶段性文件泄漏，不改任何求解函数 | 否 |
| `src/build_summary.py` | 读取 `problem1.json`；将 Q1 纳入 `summary.json`/`summary.md`；审计 `result1.xlsx`；五工作簿统一检查官方 sheet 名、144 标签、日期、数值；读取新时间轴审计；图哈希覆盖 Q1–Q4；不再把过期审计当 PASS | 聚合与验收修复 | 否 |
| `src/test_c_spec.py` | 断言 0/35/36/60/72/108/143 的精确标签；把末标签期望改为 `23:50-0:00+1`；保留 36/72/108 与全部模型断言 | 标签测试更新 | 否 |
| `src/test_timestamp_alignment.py` | 移除 `j→j+1`/跨日取值的旧验收；新增五工作簿各详细 sheet 的标签断言和 `template position j == internal j` 数值断言；检查 Q3/Q4 更新边界仍为 36/72/108；实际检查后产生 `final_workbooks_ready` | 根据用户确认的输出口径更新测试 | 否 |
| `src/audit_timestamp_alignment.py` | 审计生成后的五个正式工作簿；记录旧结论摘要、原审计文件哈希/时间及“旧结论失效原因=官方模板标签应修正而非映射到下一片”；输出真实 PASS/FAIL，禁止硬编码 true | 更新审计证据，不删除历史 | 否 |
| `src/build_final_manifest.py`（新增） | 生成 `FINAL_RUN_MANIFEST.md`：环境、依赖、输入/源码/结果/图/工作簿哈希、Q1–Q4 核心数值、测试、时间轴验收、缓存是否复用、未解决项 | 交付可追溯性工具 | 否 |
| `FINAL_RUN_MANIFEST.md`（生成） | 由上述脚本写出，不手工填写结果 | 最终运行事实记录 | 否 |
| `FINAL/`（最终验收后生成） | 只复制同一最终 run_id 的论文前置数据、五工作簿、summary、图、审计、代码和 manifest | 唯一交付目录 | 否 |

### 4.2 明确不修改的活动文件

以下文件不需要改动：

- `src/config.py`
- `src/dispatch_core.py`
- `src/scenario_cache.py`
- `src/problem1.py`
- `src/problem2.py`
- `src/problem3.py`
- `src/problem4.py`
- `src/reporting.py`
- `src/validate_typical_days.py`
- `src/audit_q3_forecast_alignment.py`
- `plot_style.py`

如果实施过程中发现必须修改上述冻结模型文件才能通过，立即停止并报告；不得自行扩展范围。`src/problem1.py` 最多允许在未来单独讨论“添加非数值元数据”这类输出改动，但本最小方案不需要它。

### 4.3 Q1 导出器的精确拟议行为

`export_problem1(solution, output_path=None)`：

1. 只从 `data/附件/附件5/result1.xlsx` 加载新副本；不读取旧 Scheme B 工作簿。
2. 不改变工作表名称、行列、样式、行高、列宽、数字格式。
3. `计划购电量!A(2+j)` 写 `all_slot_labels()[j]`，`B(2+j)` 写 `solution["purchase"][j]`，j=0…143。
4. `充放电量` 六个 4 小时区间写当前 `charge`/`discharge` 聚合；SOC 只写当前 `soc[0]` 与 `soc[-1]` 对应的 0:00/24:00 单元格。
5. 输出前断言所有数组长度、有限性、标签数量和关键位置。
6. 默认输出仍为根 `result1.xlsx`；测试时通过 `output_path` 写入隔离 staging，避免提前覆盖正式文件。

### 4.4 Q2–Q4 正式模板导出的精确拟议行为

`export_records(..., output_path=None)`：

1. 每次从官方对应模板加载，绝不以当前根工作簿或 staging 工作簿为输入。
2. 对所有详细 sheet 写入同一 `labels=all_slot_labels()`；标签位置 j 与数组位置 j 一一对应。
3. `计划购电量`：144 值来自 `record["plan"]["purchase"]`。
4. Q3/Q4-3 `调整购电量`：144 值来自 `record["final_purchase"]`，不写三行 release snapshot，不新增“调整时刻”列。
5. `充放电量`/`紧急购电量` 需要扩行时，从官方示例行复制样式、格式、行高；不替换表头样式。
6. 正式提交工作簿只保留官方 sheet 集合；`每日汇总` 等审计信息继续留在 CSV/JSON，不混入 submission workbook。
7. 所有写入都只按原数组顺序；代码和测试中禁止出现 `np.roll`、`shift`、`[1:] + next_day` 等映射。

### 4.5 数值不变性策略

阶段 B 修改前先建立只读基准：

- Q1：当前 `solve_lp` 的 purchase/charge/discharge/SOC 数组及费用；
- Q2–Q4：当前源码哈希匹配缓存中的 plan/final/charge/discharge/SOC/emergency/waste/residual 数组；
- 核心目标值：Q1 35,101.567554 元；Q2 13,701,658.500733 元；Q3 13,266,622.729589 元；Q4-2 14,401,772.581567 元；Q4-3 13,953,460.931182 元。

修复后逐数组使用 `rtol=0`、适当浮点绝对容差（建议 `1e-9`；物理残差继续使用现有 `1e-7` 闸门）比较。标签修正允许文件 SHA 改变，不允许数值单元格、CSV、JSON 核心值或数组摘要改变。任何超限变化立即停止。

## 5. 缓存策略与是否重跑

### 5.1 可直接用于阶段 B 导出预检的当前匹配缓存

以下缓存已按当前 `scenario_cache.cache_path` 规则匹配当前 `config.py`、`dispatch_core.py`、`scenario_cache.py` 与四个原始附件哈希：

- `q2_fixed_a3de9cbf6b675e252f96.npz`
- `q3_6_12_18_rec_39c8fa1a4dd9cd8ca668.npz`
- `q4_causal_q2_ea8d6fef4c7c10188c34.npz`
- `q4_causal_q3_1b3f5149e97b5cda8e76.npz`
- `q3_none_29862a174c96d492597b.npz`
- `q3_6_3a067d4eebb2038e66a1.npz`
- `q3_12_f35a5afae6d28c6a6894.npz`
- `q3_18_20dc119bf1e9e477ff54.npz`
- `q3_6_12_e952a232510846ee5f99.npz`
- `q3_12_18_d24003d6a2ce0bb7a12e.npz`
- `q3_6_12_18_8a116a581929dd41771f.npz`
- `perfect_fixed_707929fa5b9cd670c7d6.npz`
- `q4_oracle_q2_93ee086cf647b4eb2ca6.npz`
- `q4_oracle_q3_7542a1fc12e4829e1ae2.npz`
- `perfect_variable_eb605db3aa7ca8fa8e3d.npz`

它们可在不重新求解全年 LP 的前提下验证：记录解包、物理断言、CSV/JSON 重建、图生成和五工作簿导出。

### 5.2 禁止使用的中间缓存

- `q2_fixed_66803a4caf118279f23a.npz`
- `q3_6_12_18_rec_59b04cb113416e5a3780.npz`
- `q4_causal_q2_3a6c614f4bf4507930b8.npz`
- `q4_causal_q3_9ff4684b34212f2d72fe.npz`

其中 Q3/Q4-3 已知会产生 13,256,700.05 元和 13,945,791.78 元的冲突结果。即使 Q2/Q4-2 数值碰巧相同，也不得用于最终链。

### 5.3 是否需要清缓存

- 阶段 B 的语法、单元、时间轴、Q1 单次、工作簿 staging 预检：**不清缓存**。
- `time_axis.py`、导出器、总入口、summary、测试和 manifest 的修改不会改变模型数组；现有匹配缓存足够验证工程链。
- 最终正式封包前：**建议进行一次干净的 Q1→Q2→Q3→Q4 全链运行**。原因不是怀疑模型，而是当前最终文件混合了不同时点，且现有缓存键只覆盖核心三文件和输入，并不自描述所有包装/输出源码。
- 干净运行只能在所有前置闸门 PASS 后进行；运行前先把当前混合产物移入只读归档并记录哈希，再清理 `build/c_spec_cache`。不得一开始就执行 `--fresh`。

### 5.4 哪些必须执行、哪些可先重导

| 对象 | 工程预检 | 最终正式运行 |
|---|---|---|
| Q1 | 必须执行一次当前 Q1 单日 LP并导出 staging | 必须由统一入口执行 |
| Q2 | 可从匹配缓存重导 | 干净全量重算 |
| Q3 | 可从 `...39c8...` 及消融缓存重导 | 干净全量重算，禁止 `...59b0...` |
| Q4 | 可从 `...ea8d...`、`...1b3f...`、oracle/perfect 缓存重导 | 干净全量重算，禁止 `...9ff4...` |
| CSV/JSON/图 | 必须在一次验证/正式入口中重建 | 必须全部由同一最终 run_id 重建 |
| 五工作簿 | 先写 staging 检查；不覆盖根文件 | 正式运行后统一生成并验收 |
| summary/audit/manifest | 只能在所有上游文件完成后生成 | 必须最后生成 |

## 6. 阶段 B 的闸门顺序（收到“继续执行”后）

```text
B0  记录冻结源码/输入/当前产物完整哈希；建立只读 pre-final 归档
 ↓
B1  只修改工程文件：time_axis、result_workbooks、run_all、summary、测试/审计；新增 manifest 构建器
 ↓
B2  语法检查；复核第1.1节全部冻结模型哈希完全不变
 ↓
B3  运行 test_c_spec；断言标签关键点和 36/72/108
 ↓
B4  仅运行 Q1 单次求解，输出到 staging；比较全部数值基准
 ↓
B5  从当前匹配缓存生成 Q2–Q4 staging 工作簿；不做全年求解
 ↓
B6  运行新 test_timestamp_alignment 和 audit_timestamp_alignment
    - 五个工作簿全部标签 PASS
    - template j == internal j
    - 数值数组零移动
    - 官方 sheet/样式/日期/单位检查 PASS
 ↓
B7  若任何数值变化或时间轴 FAIL：立即停止，不覆盖正式结果
 ↓
B8  前置闸门全 PASS 后，运行一次干净、单入口 Q1→Q2→Q3→Q4
 ↓
B9  生成 summary → final_audit → timestamp audit → FINAL_RUN_MANIFEST
 ↓
B10 对五工作簿、CSV、JSON、图和 manifest 做最终哈希/数值交叉验收
 ↓
B11 仅当全部通过时建立唯一 FINAL/；否则不封包
```

`final_workbooks_ready` 必须由实际检查汇总计算，不能常量赋值。若任一文件不存在、标签不符、数组错位、sheet 集合不符或数值不变性失败，值必须为 false。

## 7. 新时间轴测试与工作簿验收设计

### 7.1 唯一标签期望

所有五个工作簿、所有包含 144 个详细位置的 sheet，必须断言：

| position | 显示标签 | 数值来源 |
|---:|---|---|
| 0 | `0:00-0:10` | internal[0] |
| 35 | `5:50-6:00` | internal[35] |
| 36 | `6:00-6:10` | internal[36] |
| 60 | `10:00-10:10` | internal[60] |
| 72 | `12:00-12:10` | internal[72] |
| 108 | `18:00-18:10` | internal[108] |
| 143 | `23:50-0:00+1` | internal[143] |

### 7.2 按工作簿的实际单元格位置

- `result1.xlsx / 计划购电量`：标签在 `A2:A145`，数值在 `B2:B145`。
- `result2.xlsx`、`result4-2.xlsx / 计划购电量`：标签在 `B1:EO1`，数值按日期位于相同行 `B:EO`。
- `result3.xlsx`、`result4-3.xlsx / 计划购电量`：同上。
- `result3.xlsx`、`result4-3.xlsx / 调整购电量`：同一组 `B1:EO1`，数值为对应日期的 `final_purchase[0:144]`。

测试必须读取至少首日、四个指定日和末日的完整 144 数值，并与当前内存记录/最终缓存逐位置比较；不仅检查表头。

### 7.3 Q3/Q4 发布边界不变性

继续断言：

- 6:00 更新的 `observed_prefix_end == 36`，0…35 已锁定，36 为首个可调整位置；
- 12:00 对应 72；
- 18:00 对应 108；
- 工作簿标签变化不参与求解，也不进入 `run_q3_day` 的 boundary 计算。

### 7.4 旧时间轴审计的证据保留方式

不得删除旧 `results/timestamp_alignment_audit.json` 和 `timestamp_alignment_tests.json` 后假装从未发生。阶段 B 应：

1. 在归档中保留两文件原件和完整 SHA-256；
2. 新审计输出包含 `supersedes` 字段，记录旧审计文件哈希、旧 verdict 和生成时间；
3. 明确说明旧审计把“官方旧标签”当作不可更改的物理轴，因此推导出 j→j+1 与跨日缺数；
4. 本轮已确认官方详细标签本身应前移十分钟，所以正确动作是修改标签、数值保持 j→j；
5. 新 `final_workbooks_ready` 由五工作簿实际验收得出。

## 8. A3：保留 / 归档清单

本节只列计划，本阶段不移动。

### 8.1 保留为当前活动源码

- `run_all.py`
- `src/config.py`
- `src/time_axis.py`
- `src/dispatch_core.py`
- `src/scenario_cache.py`
- `src/problem1.py`
- `src/problem2.py`
- `src/problem3.py`
- `src/problem4.py`

### 8.2 保留为最终生成链工具

- `src/reporting.py`
- `src/result_workbooks.py`
- `src/build_summary.py`
- `src/test_c_spec.py`
- `src/test_timestamp_alignment.py`
- `src/audit_timestamp_alignment.py`
- `src/audit_q3_forecast_alignment.py`
- `src/validate_typical_days.py`
- 拟新增 `src/build_final_manifest.py`
- `plot_style.py`
- 官方输入：`data/附件/附件1.xlsx` 至 `附件4.xlsx`
- 官方模板：`data/附件/附件5/result1.xlsx` 至 `result4-3.xlsx`
- 规范来源：`c建模说明与结果.txt`

`question/附件/**` 作为官方资料镜像保留，但最终复现链只指定 `data/附件/**` 为唯一读取源，避免双源。

### 8.3 归档的 Scheme B / 历史版本

拟归入唯一 `archive/scheme_b_and_history/`，保持原相对路径和哈希：

- `src/publish_scheme_b.py`
- `src/record_scheme_b_delivery.py`
- `src/verify_scheme_b.py`
- `src/build_scheme_b_docx.py`
- `src/connect_workbook_export.py`
- `src/finalize_scheme_b.py`
- `src/implement_scheme_b.py`
- `src/update_manuscript.py`
- `src/verify_revision.py`
- `src/verify_timestamp_docx.py`
- `src/reexport_timestamp_corrected_workbooks.py`
- `build/before_scheme_b/**`
- `build/before_timestamp_fix_20260912/**`
- `build/revision_backup_20260911/**`
- `build/scheme_b_tools/**`
- 当前旧论文链：`report.md`、`chapters/**`、`build/_cumcm.md`、`build/thesis*.docx`
- `results/scheme_b_*`、`results/revision_notes.md`、旧 `_ledger/_digest/_provenance`、旧论文质量/推导/基线文件

旧论文归档后不会在本轮重写。最终 `FINAL/` 只放模型结果链与论文构建所需事实源；正式论文重建另行进行。

### 8.4 中间产物 / staging / 旧结果 / 旧图

拟归入 `archive/intermediate_pre_final/` 或明确排除于 `FINAL/`：

- `build/official_template_alignment_staging/**`
- `build/timestamp_workbook_previews/**`
- `result*.xlsx.inspect.ndjson`
- 16:47–16:54 的混合 `results/problem*.json/csv` 与 `figures/P*`、Q1 图
- `build/c_spec_cache/*66803*`、`*59b04*`、`*3a6c61*`、`*9ff468*`
- `__pycache__/**`、`src/__pycache__/**`、`*.pyc`
- `build/agent/*.log`
- `tmp/**`
- `.audit_tmp_numeric.py`
- `artifact_manifest.json`、代理会话/流水线状态文件、`.qwen/**`、`.vscode/**`
- 旧图元数据、润色标记、旧机制图及 prompt 文件

与当前源码匹配的 c-spec 缓存不归为旧结果，但最终只能放入 `FINAL/reproducibility/cache/` 中由 `FINAL_RUN_MANIFEST.md` 明确列出的那些缓存。

## 9. 最终唯一生成链（拟实施状态）

阶段 B 完成后，唯一入口应为：

```text
python run_all.py --fresh
```

唯一发布顺序应为：

```text
原始附件（data/附件）
  → 冻结模型与时间轴单元测试
  → Q1 当前 LP
      → problem1.json / sensitivity.csv / Q1 figures / result1.xlsx
  → Q2 当前全年模型
      → problem2.json / daily.csv / P2 figures / result2.xlsx
  → Q3 当前完整消融与正式方案（只调用一次）
      → problem3.json / CSV / P3 figures / result3.xlsx
  → Q4 当前全部场景（只调用一次）
      → problem4.json / CSV / P4 figures / result4-2.xlsx / result4-3.xlsx
  → 五工作簿时间轴测试
  → Q3 发布边界审计
  → 时间轴审计
  → build_summary
  → final_audit
  → FINAL_RUN_MANIFEST.md
  → FINAL/ 封包与最终哈希复核
```

所有输出必须登记同一个 `run_id`。任何子步骤失败，后续 summary/manifest/FINAL 封包均不得执行。

## 10. `FINAL_RUN_MANIFEST.md` 最低内容

- `MODEL_VERSION=c-spec-v1-2026-09-12`
- 唯一 `run_id`、开始/结束时间、是否使用缓存
- Python 可执行文件、Python 版本、平台
- numpy/pandas/scipy/openpyxl/matplotlib 等主要依赖版本
- `data/附件/附件1.xlsx` 至 `附件4.xlsx` 完整 SHA-256
- 第 1.1 节冻结模型源码完整 SHA-256
- 工程生成链源码完整 SHA-256
- Q1–Q4 核心费用、购电量、SOC、残差摘要
- `summary.json`、所有正式 CSV/JSON、最终图完整 SHA-256
- 五工作簿完整 SHA-256及数值区摘要哈希
- 单元测试、时间轴测试、Q3 边界审计、工作簿验收状态
- 七个关键位置在五工作簿中的实际显示
- 官方 sheet 名、日期范围、单位、样式检查结论
- 是否存在未解决问题
- 最终 verdict：PASS / PASS WITH ISSUES / FAIL

manifest 只能由脚本读取实际文件后生成，不能把预期值手工写成通过。

## 11. 唯一 `FINAL/` 方案

只有最终验收 PASS 后创建：

```text
FINAL/
├─ FINAL_RUN_MANIFEST.md
├─ SHA256SUMS.txt
├─ submission/
│  ├─ result1.xlsx
│  ├─ result2.xlsx
│  ├─ result3.xlsx
│  ├─ result4-2.xlsx
│  └─ result4-3.xlsx
└─ reproducibility/
   ├─ run_all.py
   ├─ src/                     # 仅当前活动生成链源码
   ├─ inputs/SOURCE_HASHES.md  # 引用原附件，不复制 question 镜像
   ├─ results/                 # 同一 run_id 的 JSON/CSV/summary/audit
   ├─ figures/                 # 同一 run_id 生成的图
   └─ cache/                   # 仅 manifest 登记的当前匹配缓存
```

本轮不构建论文，因此 `submission/` 暂不放旧 `report.md` 或 DOCX。待后续论文正式重写完成后，只能依据该 manifest 中的数字和图，经过另一次文档构建验收后加入同一交付包；旧 Scheme B 论文不得进入 `FINAL/`。

## 12. 预计最终验收结论规则

只有同时满足以下条件才允许 `FINAL_DELIVERY_AUDIT.md` 判定 PASS：

1. 第 1.1 节全部冻结模型源码哈希不变；
2. Q1–Q4 核心数值和所有数组未因标签修正变化；
3. 唯一入口能从 `data/附件` 完整生成全部产物；
4. Q3/Q4 边界仍为 36/72/108；
5. 五工作簿所有详细 sheet 的七个关键标签及 j→j 数值映射通过；
6. 五工作簿 sheet 名、日期、单位、样式和官方模板骨架通过；
7. CSV、JSON、summary、图、工作簿均属于同一 run_id；
8. `timestamp_alignment` 实际 PASS 且不是硬编码；
9. `FINAL_RUN_MANIFEST.md` 的全部文件哈希与封包内容一致；
10. 不存在旧 Scheme B、16:51–16:54 中间结果或 staging 工作簿混入 `FINAL/`。

如任何模型数值变化、冻结哈希变化或必须修改模型逻辑才能继续，则最终建议只能是 **C. 不能冻结**，并立即停止。

## 13. 阶段 A 结论与等待点

最小工程修复可行，且不需要改变数学模型、预测、参数、SOC、LP、调度、滚动机制或费用规则。主要工作是：

1. 补上 Q1 导出接口并接入唯一入口；
2. 把官方模板详细标签改成内部自然日标签，严格 j→j，不移动数组；
3. 恢复正式模板骨架，避免 Q3/Q4-3 三行中间表示进入正式工作簿；
4. 避免总入口先发布不完整 Q3/Q4；
5. 将 Q1、五工作簿和新时间轴验收纳入 summary/audit；
6. 先用匹配缓存做低成本预检，全部通过后再进行一次正式干净全链运行；
7. 由实际文件生成 manifest 和唯一 `FINAL/`。

**现在停止。未收到明确“继续执行”前，不进入阶段 B。**
