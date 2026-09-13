# 最终交付物全量盘点（只读冻结审计）

> **后续收口状态更新（2026-09-12 21:xx，优先于下方历史盘点结论）：** 下方正文记录的是修复前的只读现场，保留作为冲突溯源证据；其中“尚不存在完整交付集合”等结论已被 run_id `c-spec-20260912T200729+0800` 的干净运行和最终验收取代。项目现已取消源码哈希冻结：模型源码可以修改，manifest 不再与硬编码基线比较；修改模型后仍需重新运行并生成新的结果清单。当前交付目录为 `FINAL/`，详见 `FINAL_DELIVERY_AUDIT.md`、`FINAL_RUN_MANIFEST.md` 与 `SHA256SUMS.txt`。
>
> 新增 Q4 电价日内波动灵敏度已归入**当前最终版**：`src/problem4_sensitivity.py`、`results/problem4_price_volatility_sensitivity.csv/json`、`figures/P4_price_volatility_sensitivity.png` 及 `build/c_spec_cache/q4_sensitivity_*.npz`；对应副本位于 `FINAL/reproducibility/`。它是独立反事实检验，不修改本次主 Q4 结果或五个提交工作簿。`archive/pre_q4_sensitivity_20260912/` 归为**旧版/实施前快照**；运行环境探针目录 `.final_runtime_*`、`.final_wheels*` 仍为**中间产物**且未进入 `FINAL/`。

审计时间：2026-09-12（Asia/Shanghai）  
审计根目录：`C:\Users\hw\Documents\xwechat_files\wxid_7y63n1g0nafn22_c993\msg\file\2026-09\重构2\重构2`  
审计范围：递归遍历当前项目 435 个文件，共 274,683,597 字节。  
操作边界：本轮未删除、未移动、未覆盖任何既有文件；未修改模型、源代码、结果工作簿、论文或图片。本文件是唯一新增文件。

## 1. 结论先行

**当前项目中不存在一套可以认定为“同一次最终运行、可直接交付”的完整文件集合。**

主要断点如下：

1. 当前活动代码的模型版本为 `c-spec-v1-2026-09-12`，但 `run_all.py` 没有执行问题1；`src/problem1.py` 又调用当前 `src/result_workbooks.py` 中不存在的 `export_problem1`。因此当前代码不能从零复现 `result1.xlsx`。
2. 根目录 `result2.xlsx`、`result3.xlsx`、`result4-2.xlsx`、`result4-3.xlsx` 的核心数值总体对应 15:08–15:10 的 c-spec 全量运行；其中 Q3、Q4-3 与当前活动代码所命中的源哈希缓存一致。
3. `results/problem3.*`、`results/problem4*.csv/json` 及对应 P3/P4 图在 16:51–16:54 被另一条不完整运行覆盖。Q3、Q4-3 的总费用分别变成 13,256,700.05 元和 13,945,791.78 元，与根工作簿/15:10 summary 的 13,266,622.73 元和 13,953,460.93 元冲突。
4. `summary.json`、`results/summary.md`、`results/final_audit.json` 同属 15:10 的全量运行候选，但 `final_audit.json` 记录的 CSV、图及 `result2.xlsx` 哈希已经过时；其“所有工作簿与当前 CSV 一致”结论在现状下不再成立。
5. `report.md`、`chapters/*.md`、`build/thesis*.docx` 是 09:17–09:20 的 Scheme B 论文链，核心费用仍为 Q2 19,257,140.05 元、Q3 19,123,232.50 元、Q4-2 20,381,775.13 元、Q4-3 20,169,378.52 元，与当前 c-spec 结果完全不是同一模型/运行。
6. 17:36 的时间轴审计明确给出 `final_workbooks_ready=false`：根工作簿当前并未通过官方模板时间轴的最终交付判定；`build/official_template_alignment_staging/...` 也被明确标记为非最终候选。

因此，四类状态的总体判定为：

| 分类 | 当前内容 |
|---|---|
| 当前最终版 | 仅指当前活动的 c-spec 源码基线、与其源哈希一致的 15:08–15:10 数值候选、以及最新只读审计；“当前最终版”不等于“已满足交付条件” |
| 旧版 | Scheme B 论文、Scheme B 结果/工具、`build/before_*` 与 `build/revision_backup_*` 中的历史快照 |
| 中间产物 | 后续不完整运行的 CSV/JSON/图、staging 工作簿、检查 NDJSON、缓存、预览、日志、`__pycache__`、临时审计脚本 |
| 无法判断 | 缺少可靠运行清单或生成链的独立素材/辅助文件，以及数值虽相符但不能由当前入口完整复现的 `result1.xlsx` |

## 2. 判定口径

“与当前最终代码一致”以根目录当前活动实现为准：

- 模型标识：`src/config.py` 中的 `c-spec-v1-2026-09-12`；
- 核心实现：`src/config.py`、`src/time_axis.py`、`src/dispatch_core.py`、`src/scenario_cache.py`、`src/problem1.py` 至 `src/problem4.py`、`src/reporting.py`、`src/result_workbooks.py`、`src/build_summary.py`；
- 一致：数值或缓存键与当前活动源码哈希相符；
- 部分一致：核心总额相符，但生成入口、时间轴、文件哈希或依赖链不闭合；
- 不一致：核心数值、模型口径、缓存键或生成逻辑不同；
- 无法判断：没有足够证据把文件绑定到某次完整运行。

文件修改时间只用于建立先后关系，不单独作为“最终版”证明。SHA-256 在表中取前 12 位，完整哈希可在后续正式封包时生成。

## 3. 当前活动代码及其冲突副本

### 3.1 当前活动 c-spec 代码

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源/作用 | 核心结果或状态 | 与当前最终代码一致 |
|---|---|---:|---|---|---|---|
| 当前最终版 | `run_all.py` | 2026-09-12 14:30:12 | `562B3E764FA1` | 当前总入口 | 执行 Q2/Q3/Q4、测试与 summary；不执行 Q1 | 是，但入口不完整 |
| 当前最终版 | `src/config.py` | 2026-09-12 14:10:25 | `BCB083165EBD` | c-spec 配置 | `MODEL_VERSION=c-spec-v1-2026-09-12` | 是 |
| 当前最终版 | `src/time_axis.py` | 2026-09-12 17:24:03 | `EED68B66CA55` | 当前内部时间轴 | 144 个十分钟片；与官方输出模板仍存在跨日映射争议 | 是，但交付映射未冻结 |
| 当前最终版 | `src/dispatch_core.py` | 2026-09-12 17:20:21 | `924B714A9654` | 当前调度与结算核心 | c-spec 随机/滚动 LP | 是 |
| 当前最终版 | `src/scenario_cache.py` | 2026-09-12 17:20:33 | `6AECC945F1FB` | 缓存键与结果装载 | 当前源码哈希映射到 14:47–14:59 缓存链 | 是 |
| 当前最终版 | `src/problem1.py` | 2026-09-12 17:24:02 | `33E740340C88` | Q1 当前实现 | 35,101.57 元；但工作簿导出调用缺失函数 | 是，但不可完整运行 |
| 当前最终版 | `src/problem2.py` | 2026-09-12 14:30:58 | `2D96B67106A6` | Q2 当前实现 | 13,701,658.50 元 | 是 |
| 当前最终版 | `src/problem3.py` | 2026-09-12 15:02:24 | `1A8535A13EDA` | Q3 当前实现 | 完整滚动应为 13,266,622.73 元 | 是 |
| 当前最终版 | `src/problem4.py` | 2026-09-12 17:24:00 | `F76C9BAEA363` | Q4 当前实现 | 因果 Q4-2 14,401,772.58 元；因果 Q4-3 13,953,460.93 元 | 是 |
| 当前最终版 | `src/reporting.py` | 2026-09-12 17:23:59 | `D49E4D468109` | JSON/CSV/绘图支持 | 当前输出口径 | 是 |
| 当前最终版 | `src/result_workbooks.py` | 2026-09-12 17:27:32 | `688A1A6DF433` | Q2–Q4 工作簿导出 | 仅有 `export_records`，没有 Q1 的 `export_problem1` | 是，但接口断裂 |
| 当前最终版 | `src/build_summary.py` | 2026-09-12 17:28:17 | `25C5ACAE04B8` | summary 与一致性审计 | 当前文件比 15:10 summary 更新，现有 summary 不是由这一版重新生成 | 是 |
| 当前最终版 | `src/test_c_spec.py` | 2026-09-12 17:24:45 | `0CD31B1B8AE8` | 当前单元审计 | 对应 17:36 测试记录 | 是 |
| 当前最终版 | `src/audit_timestamp_alignment.py` | 2026-09-12 17:33:38 | `950A777A9080` | 官方模板时间轴审计 | 判定最终工作簿未就绪 | 是 |
| 当前最终版 | `src/test_timestamp_alignment.py` | 2026-09-12 17:35:41 | `E15F99B71447` | 时间轴测试 | `final_workbooks_ready=false` | 是 |
| 当前最终版 | `src/audit_q3_forecast_alignment.py` | 2026-09-12 17:37:04 | `3B91F962BADA` | Q3 预报对齐审计 | 晚于现有 Q3 结果文件 | 是 |

当前活动代码的两个可复现性断点：

- `run_all.py` 第 43–61 行只有 Q2、Q3、Q4，没有调用 Q1。
- `src/problem1.py` 第 169–171 行导入并调用 `export_problem1`，而当前 `src/result_workbooks.py` 中不存在该函数。

### 3.2 代码重复/冲突文件

| 分类 | 路径（逐个列出） | 修改时间 | 来源 | 核心结果/用途 | 与当前最终代码一致 |
|---|---|---:|---|---|---|
| 旧版 | `build/revision_backup_20260911/src/config.py` | 2026-09-10 21:53:57 | 9月11日修订前备份 | 早期参数 | 否 |
| 旧版 | `build/before_scheme_b/src/config.py` | 2026-09-11 20:14:14 | Scheme B 前快照 | 旧预测/调度参数 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/dispatch_core.py` | 2026-09-11 20:49:16 | 时间轴修正前快照 | Scheme B/旧调度核心 | 否 |
| 旧版 | `build/revision_backup_20260911/src/problem1.py` | 2026-09-11 07:32:24 | 9月11日修订备份 | 旧 Q1 | 否 |
| 旧版 | `build/before_scheme_b/src/problem1.py` | 2026-09-11 20:20:39 | Scheme B 前快照 | 旧 Q1 导出链 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/problem1.py` | 2026-09-11 20:49:17 | 时间轴修正前快照 | 旧时间标签 Q1 | 否 |
| 旧版 | `build/revision_backup_20260911/src/problem2.py` | 2026-09-11 08:15:43 | 9月11日修订备份 | 旧 Q2 | 否 |
| 旧版 | `build/before_scheme_b/src/problem2.py` | 2026-09-11 20:20:01 | Scheme B 前快照 | Q2 旧预测规则 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/problem2.py` | 2026-09-11 20:51:36 | 时间轴修正前快照 | Scheme B Q2，约 19.257 百万元 | 否 |
| 旧版 | `build/revision_backup_20260911/src/problem3.py` | 2026-09-11 10:06:36 | 9月11日修订备份 | 旧 Q3 | 否 |
| 旧版 | `build/before_scheme_b/src/problem3.py` | 2026-09-11 20:20:05 | Scheme B 前快照 | 旧 Q3 | 否 |
| 旧版 | `build/revision_backup_20260911/src/problem4.py` | 2026-09-11 11:05:28 | 9月11日修订备份 | 旧 Q4 | 否 |
| 旧版 | `build/before_scheme_b/src/problem4.py` | 2026-09-11 20:20:07 | Scheme B 前快照 | 旧 Q4 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/problem4.py` | 2026-09-11 21:07:55 | 时间轴修正前快照 | Scheme B Q4 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result_workbooks.py` | 2026-09-11 20:51:31 | 旧工作簿导出器 | 可导出旧 Scheme B 表 | 否 |
| 旧版 | `src/publish_scheme_b.py` | 2026-09-12 09:14:45 | Scheme B 发布脚本 | 发布 19–20 百万元结果链 | 否 |
| 旧版 | `src/record_scheme_b_delivery.py` | 2026-09-12 09:15:08 | Scheme B 清单脚本 | 记录旧论文/工作簿哈希 | 否 |
| 旧版 | `src/verify_scheme_b.py` | 2026-09-12 09:15:21 | Scheme B 验证脚本 | 校验旧交付 | 否 |
| 旧版 | `src/build_scheme_b_docx.py` | 2026-09-11 21:09:49 | Scheme B 文档构建 | 生成旧论文 DOCX | 否 |
| 旧版 | `src/connect_workbook_export.py`、`src/finalize_scheme_b.py`、`src/implement_scheme_b.py` | 2026-09-12 07:50:41 | Scheme B 小型包装入口 | 均为 182 字节的旧包装脚本 | 否 |
| 旧版 | `src/reexport_timestamp_corrected_workbooks.py` | 2026-09-12 09:10:51 | 旧重导出入口 | 导入当前已不存在的 `reexport_existing_annual` | 否/已失效 |
| 中间产物 | `src/diagnostic_plot.py`、`src/scenario_figures.py`、`src/validate_typical_days.py`、各 `audit_*`/`test_*` | 2026-09-11 至 2026-09-12 | 诊断、绘图、测试 | 支持运行与核验，不是独立交付模型 | 与各自生成时点有关 |
| 无法判断 | `check_figures.py`、`merge_parts.py`、`plot_style.py`、`src/inspect_*.py`、`src/profile_attachments.py`、`src/validate_plan.py` | 2026-09-10 至 2026-09-11 | 通用辅助工具 | 不直接定义最终数值；可复用但无运行清单绑定 | 不适用 |

## 4. 结果工作簿：全部 39 个 XLSX 的分类

### 4.1 根目录结果工作簿

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源 | 核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|---|---|
| 无法判断 | `result1.xlsx` | 2026-09-12 09:10:11 | `887AC45843A4` | Scheme B/时间轴修正阶段导出；当前入口无法重建 | 总购电 59,482.70 kWh、费用 35,101.57 元；表内 `12:00-12:10=578.9955`，与当前时间轴取值 `573.0050` 冲突 | 数值总额部分一致，生成链与时轴不一致 |
| 当前最终版 | `result2.xlsx` | 2026-09-12 15:57:22 | `E85573DA5867` | c-spec Q2 后续重导出 | 13,701,658.50 元 | 数值一致；哈希晚于 15:10 审计，审计记录已过期 |
| 当前最终版 | `result3.xlsx` | 2026-09-12 15:08:13 | `2952376C83F2` | c-spec 全量 Q3 缓存 `...39c8...` 导出 | 13,266,622.73 元 | 数值一致；但官方模板时间轴未通过 |
| 当前最终版 | `result4-2.xlsx` | 2026-09-12 15:08:37 | `089C68F9CCCC` | c-spec 全量因果 Q4-2 缓存 `...ea8d...` 导出 | 14,401,772.58 元 | 数值一致；但官方模板时间轴未通过 |
| 当前最终版 | `result4-3.xlsx` | 2026-09-12 15:08:39 | `E592A2B7720A` | c-spec 全量因果 Q4-3 缓存 `...1b3f...` 导出 | 13,953,460.93 元 | 数值一致；但官方模板时间轴未通过 |

注意：这里将 Q2–Q4 根工作簿列为“当前最终版”只表示它们是当前 c-spec 数值基线的候选权威文件，不表示可以直接提交。17:36 的最新审计明确否定了最终工作簿就绪状态。

### 4.2 官方空白模板的两套相同副本

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源/核心内容 | 与当前最终代码一致 |
|---|---|---:|---|---|---|
| 当前最终版 | `data/附件/附件5/result1.xlsx` | 2026-08-24 18:13:18 | `28360E0974E7` | 官方 Q1 空白模板 | 输入模板，不作数值一致性判断 |
| 当前最终版 | `question/附件/附件5/result1.xlsx` | 2026-08-24 18:13:18 | `28360E0974E7` | 与上一文件逐字节相同的官方副本 | 同上 |
| 当前最终版 | `data/附件/附件5/result2.xlsx` | 2026-08-24 17:37:48 | `1C26494CFC6D` | 官方 Q2 空白模板 | 同上 |
| 当前最终版 | `question/附件/附件5/result2.xlsx` | 2026-08-24 17:37:48 | `1C26494CFC6D` | 相同官方副本 | 同上 |
| 当前最终版 | `data/附件/附件5/result3.xlsx` | 2026-08-24 17:40:44 | `C59DA470CABD` | 官方 Q3 空白模板 | 同上 |
| 当前最终版 | `question/附件/附件5/result3.xlsx` | 2026-08-24 17:40:44 | `C59DA470CABD` | 相同官方副本 | 同上 |
| 当前最终版 | `data/附件/附件5/result4-2.xlsx` | 2026-08-24 17:37:48 | `1C26494CFC6D` | 官方 Q4-2 空白模板 | 同上 |
| 当前最终版 | `question/附件/附件5/result4-2.xlsx` | 2026-08-24 17:37:48 | `1C26494CFC6D` | 相同官方副本 | 同上 |
| 当前最终版 | `data/附件/附件5/result4-3.xlsx` | 2026-08-24 17:40:44 | `C59DA470CABD` | 官方 Q4-3 空白模板 | 同上 |
| 当前最终版 | `question/附件/附件5/result4-3.xlsx` | 2026-08-24 17:40:44 | `C59DA470CABD` | 相同官方副本 | 同上 |

官方模板与根结果工作簿的结构冲突：

- 官方明细轴首列从 `0:10-0:20` 开始并跨到次日 `0:00(+1)-0:10(+1)`；当前内部模型日轴从 `0:00-0:10` 开始。
- Q3/Q4-3 官方“调整购电量”表为单日一行、144 个值及汇总列；根工作簿已改造成每个日期三行的 6/12/18 时调整表示，并增加了 `每日汇总`、`最终购电量` 等表。
- 最新审计认为严格物理映射需要下一日首片数据，最后一个输出日期无法闭合，因此不能把 staging 版本认定为最终提交文件。

### 4.3 历史与 staging 工作簿副本

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源 | 核心结果/用途 | 与当前最终代码一致 |
|---|---|---:|---|---|---|---|
| 旧版 | `build/before_scheme_b/result1.xlsx` | 2026-09-11 07:41:55 | `112B38CE9710` | Scheme B 前快照 | Q1 35,101.57 元族 | 否：旧导出/时轴 |
| 旧版 | `build/before_scheme_b/result2.xlsx` | 2026-09-11 13:28:14 | `0F009873B9BF` | Scheme B 前快照 | 与旧 Q2 19,257,140.05 元结果族关联 | 否 |
| 旧版 | `build/before_scheme_b/result3.xlsx` | 2026-09-11 09:54:26 | `D9D9C8FDF124` | Scheme B 前快照 | 旧 Q3 候选；同期 JSON 含 15.614/18.060/16.532/19.603 百万元多方案 | 否 |
| 旧版 | `build/before_scheme_b/result4-2.xlsx` | 2026-09-11 11:14:07 | `AEF443940BF9` | Scheme B 前快照 | 旧 Q4 结果族 | 否 |
| 旧版 | `build/before_scheme_b/result4-3.xlsx` | 2026-09-11 11:14:09 | `BFC12577B16A` | Scheme B 前快照 | 旧 Q4 结果族 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result1.xlsx` | 2026-09-11 07:41:55 | `112B38CE9710` | 时间轴修正前，和 before_scheme_b 的 Q1 完全相同 | Q1 旧模板映射 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result2.xlsx` | 2026-09-11 20:54:33 | `7835DBC41103` | Scheme B 时间轴修正前 | Q2 19,257,140.05 元族 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result3.xlsx` | 2026-09-11 21:04:44 | `0D6184707DA7` | Scheme B 时间轴修正前 | Q3 19,123,232.50 元族 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result4-2.xlsx` | 2026-09-11 21:07:53 | `303263110B79` | Scheme B 时间轴修正前 | Q4-2 20,381,775.13 元族 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/result4-3.xlsx` | 2026-09-11 21:08:06 | `21F916DC279D` | Scheme B 时间轴修正前 | Q4-3 20,169,378.52 元族 | 否 |
| 中间产物 | `build/official_template_alignment_staging/template_position_candidate/result1.xlsx` | 2026-09-12 16:47:34 | `C83A72B0C54F` | 官方模板位置映射试验 | Q1 template-position 候选 | 否：审计明确标为 nonfinal |
| 中间产物 | `build/official_template_alignment_staging/template_position_candidate/result2.xlsx` | 2026-09-12 17:09:29 | `CBF4C75364AB` | 同上 | Q2 位置映射候选 | 否：nonfinal |
| 中间产物 | `build/official_template_alignment_staging/template_position_candidate/result3.xlsx` | 2026-09-12 17:09:44 | `F7D6BAE1DCE0` | 同上 | Q3 位置映射候选 | 否：nonfinal/跨日未闭合 |
| 中间产物 | `build/official_template_alignment_staging/template_position_candidate/result4-2.xlsx` | 2026-09-12 17:09:51 | `EB1E3F43DF80` | 同上 | Q4-2 位置映射候选 | 否：nonfinal |
| 中间产物 | `build/official_template_alignment_staging/template_position_candidate/result4-3.xlsx` | 2026-09-12 17:10:06 | `068BBBBFD29D` | 同上 | Q4-3 位置映射候选 | 否：nonfinal/跨日未闭合 |
| 中间产物 | `build/style_probe.xlsx` | 2026-09-12 17:07:38 | `0AEC8EC055D2` | Excel 样式探针 | 无模型结果 | 不适用 |

### 4.4 其余 8 个 XLSX 输入副本

`data/附件/附件1.xlsx` 至 `附件4.xlsx` 与 `question/附件/附件1.xlsx` 至 `附件4.xlsx` 是两套逐字节相同的官方输入数据，不是生成结果。修改时间均为 2026-08-24；对应哈希前12位依次为 `66B87134F5EC`、`2E95FD446BFA`、`8A61B06C52BD`、`20E9C93AEAB5`。分类为“当前最终版（官方输入）”，但只应在复现包中保留一个权威副本，另一个仅作为来源镜像记录。

## 5. Summary、逐题结果与审计文件

### 5.1 当前 summary 链

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源 | 核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|---|---|
| 当前最终版 | `summary.json` | 2026-09-12 15:10:38 | `DE0A42D558AA` | 15:08–15:10 c-spec 全量运行 | Q2 13,701,658.50；Q3 13,266,622.73；Q4-2 14,401,772.58；Q4-3 13,953,460.93；含完整消融/oracle/perfect-info | 核心数值一致；不含 Q1；早于最后代码修改 |
| 当前最终版 | `results/summary.md` | 2026-09-12 15:10:38 | `55D44274666D` | 上述 JSON 的可读摘要 | 同一组核心数值 | 同上 |
| 无法判断 | `results/final_audit.json` | 2026-09-12 15:10:38 | `68106CBF1A76` | 15:10 自动审计快照 | 当时宣称所有工作簿、CSV、20 张图一致 | 审计结论已被后续覆盖操作破坏，不能继续作为最终证明 |

`results/final_audit.json` 的具体过期证据：

- 它记录 `result2.xlsx` 的完整哈希以 `65266f8f...` 开头，而当前根文件哈希以 `e85573da...` 开头。
- 它记录的 P2/P3/P4 图哈希与当前 16:50–16:54 图文件哈希不同。
- 它声称 Q3/Q4-3 工作簿与 CSV 一致；当前只读复核发现 Q3 每日费用最大差约 822.76 元、年度差 9,922.68 元，Q4-3 每日费用最大差约 799.65 元、年度差 7,669.15 元。

### 5.2 当前逐题 CSV/JSON 的分叉

| 分类 | 路径 | 修改时间 | 来源 | 核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|---|
| 中间产物 | `results/problem1.json` | 2026-09-12 16:47:40 | 后续时间轴试验运行 | 35,101.57 元；指定时点 12:00=578.9955、16:00=394.9315、18:00=636.9826 | 总额一致，时点标签与当前代码/论文不一致 |
| 中间产物 | `results/problem1_sensitivity.csv` | 2026-09-12 16:47:39 | 同次 Q1 后续运行 | 121 个容量/功率组合；最低约 35,056.72 元 | 与该次 Q1 JSON 同源，但不构成当前完整运行 |
| 当前最终版 | `results/problem2_daily.csv` | 2026-09-12 16:50:17 | 后续 Q2 运行，命中不同缓存名但数值未变 | 年度 13,701,658.50 元 | 数值一致 |
| 当前最终版 | `results/problem2.json` | 2026-09-12 16:50:18 | 同上 | 年度 13,701,658.50 元 | 数值一致，但不与 15:10 图哈希同源 |
| 中间产物 | `results/problem3_daily.csv` | 2026-09-12 16:51:37 | 后续 Q3 中间源码缓存 `...59b0...` | 年度 13,256,700.05 元 | 否；当前代码应为 13,266,622.73 元 |
| 中间产物 | `results/problem3.json` | 2026-09-12 16:51:38 | 同上，且只运行主方案 | 年度 13,256,700.05 元；仅 1 条消融记录 | 否；全量运行应有完整消融集合 |
| 中间产物 | `results/problem3_ablation.csv` | 2026-09-12 16:51:37 | `include_ablations=False` 阶段性输出 | 仅 1 行完整方案 | 否/不完整 |
| 中间产物 | `results/problem3_forecast_accuracy.csv` | 2026-09-12 16:51:37 | 同次 Q3 运行 | Q3 预测精度 | 与中间 Q3 同源，不与当前 Q3 工作簿同源 |
| 当前最终版 | `results/problem4_causal_q2_daily.csv` | 2026-09-12 16:53:42 | 后续 Q4 运行 | 14,401,772.58 元 | 数值一致 |
| 中间产物 | `results/problem4_causal_q3_daily.csv` | 2026-09-12 16:53:42 | 后续 Q4 中间源码缓存 `...9ff4...` | 13,945,791.78 元 | 否；当前代码/工作簿为 13,953,460.93 元 |
| 中间产物 | `results/problem4.json` | 2026-09-12 16:53:57 | `include_oracles=False` 阶段性输出 | 只含 4 个因果/固定价场景；Q4-3 为 13,945,791.78 元 | 否/不完整；全量 summary 含 7 个场景 |
| 中间产物 | `results/problem4_comparison.csv`、`results/problem4_price_forecast_accuracy.csv` | 2026-09-12 16:53:54 | 同次不完整 Q4 运行 | 4 场景比较及价格预测指标 | 不与 15:10 全量 summary 同源 |
| 中间产物 | `results/problem4_fixed_q2_daily.csv` | 2026-09-12 16:53:42 | 后续 Q4 中间运行 | 固定价 Q4-2 14,448,789.36 元 | 数值与 15:10 summary 一致 |
| 中间产物 | `results/problem4_fixed_q3_daily.csv` | 2026-09-12 16:53:42 | 后续 Q4 中间运行 | 固定价 Q4-3 13,982,047.84 元 | 否；15:10 summary 为 13,991,559.82 元 |
| 当前最终版 | `results/problem4_oracle_q2_daily.csv` | 2026-09-12 15:08:36 | 15:08 全量 Q4 | price-oracle Q4-2 结果 | 与当前全量缓存/summary 一致 |
| 当前最终版 | `results/problem4_oracle_q3_daily.csv` | 2026-09-12 15:08:36 | 15:08 全量 Q4 | price-oracle Q4-3 结果 | 与当前全量缓存/summary 一致 |
| 当前最终版 | `results/problem4_perfect_information_daily.csv` | 2026-09-12 15:08:36 | 15:08 全量 Q4 | 完美信息下界 12,809,266.07 元 | 与当前全量缓存/summary 一致 |

### 5.3 审计文件

| 分类 | 路径 | 修改时间 | 来源 | 核心结论 | 与当前最终代码一致 |
|---|---|---:|---|---|---|
| 当前最终版 | `results/c_spec_unit_tests.json` | 2026-09-12 17:36:01 | 当前单元测试 | 已记录核心物理/因果性测试 | 是，但不能替代端到端复现 |
| 当前最终版 | `results/timestamp_alignment_audit.json` | 2026-09-12 17:36:00 | 最新时间轴审计 | `BLOCKED`；`final_workbooks_ready=false` | 是 |
| 当前最终版 | `results/timestamp_alignment_tests.json` | 2026-09-12 17:35:59 | 最新时间轴测试 | 最终工作簿未就绪 | 是 |
| 当前最终版 | `results/q3_forecast_alignment_audit.json` | 2026-09-12 16:59:49 | Q3 预报切片审计 | 检查 0/6/12/18 时更新边界 | 与审计时代码接近；晚于中间 Q3 结果 |
| 中间产物 | `results/c_spec_typical_day_validation.json` | 2026-09-12 16:49:41 | 16:49 典型日验证 | 由后续中间运行生成 | 不能证明当前全量 Q3/Q4 |
| 旧版 | `results/scheme_b_tests.json`、`scheme_b_validation.json`、`scheme_b_docx_validation.json`、`scheme_b_publication.json`、`scheme_b_manifest.json`、`timestamp_docx_validation.json` | 2026-09-12 09:17–13:18 | Scheme B 发布/文档审计 | 验证旧论文和旧哈希 | 否 |
| 旧版 | `results/_ledger.json`、`_digest.md`、`_data_card.*`、`_provenance/*.json`、`revision_notes.md` | 2026-09-11 至 09:21 | 旧流水线/旧结果账本 | 多处仍记录 Scheme B 或更早结果 | 否 |
| 旧版 | `results/model_derivation.*`、`paper_quality.*`、`score_points.*`、`baseline_review/*`、`parameter_refactor_validation.json` | 2026-09-11 | 旧推导、论文质量和基线比较 | 为旧模型选择/写作服务 | 否 |
| 无法判断 | `results/AI工具使用详情.md`、`markup_check.*`、`manuscript_revision.json` | 2026-09-11 | 写作/合规辅助 | 可能作为说明材料，但与当前 c-spec 数值无直接绑定 | 不适用 |

## 6. 图文件

### 6.1 当前根 `figures/` 的分类

| 分类 | 路径/文件族 | 修改时间 | 来源 | 核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|---|
| 中间产物 | `figures/problem1.png`、`problem1.pdf`、`problem1_diagnostic.png/pdf`、`problem1_sensitivity.png` | 2026-09-12 16:47:35–16:47:40 | 与后续 Q1 JSON 同次运行 | Q1 调度、诊断和敏感性 | 总额口径相近，但时间标签与当前代码/工作簿冲突 |
| 当前最终版 | `figures/P2_2025-03-20.png`、`P2_2025-06-21.png`、`P2_2025-09-23.png`、`P2_2025-12-21.png` | 2026-09-12 16:50:17–16:50:18 | 后续 Q2 运行 | Q2 四个典型日；年度总额未变 | 数值一致，但不是 15:10 audit 记录的同一二进制图 |
| 中间产物 | `figures/P3_*.png`、`forecast_pv_mae.png`、`P3_compare.png` | 2026-09-12 16:51:37–16:51:38 | Q3 中间缓存 `...59b0...` 且仅 1 行消融 | Q3 13,256,700.05 元族；比较图不完整 | 否 |
| 中间产物 | `figures/P4-2_*.png`、`P4-3_*.png`、`P4_compare.png`、`P4_price_forecast.png` | 2026-09-12 16:53:54–16:53:57 | 不完整 Q4 运行 | 仅 4 场景；Q4-3 13,945,791.78 元族 | Q4-2 数值相符；Q4-3 及比较图不一致/不完整 |
| 中间产物 | `figures/_figure_lint.json` | 2026-09-12 16:47:40 | 图检查元数据 | 只覆盖当时图状态 | 不能证明后续 P2–P4 图 |
| 旧版 | `figures/flowchart.png`、`problem1_mechanism.png` 及其 `.meta.json`/`.prompt.txt` | 2026-09-11 11:39–11:41 | Scheme B 写作素材 | 静态机制图，不含当前数值 | 未绑定当前代码；需重新核文案 |
| 旧版 | `figures/_palette_map.json`、`_vlm_review.json`、`.polish_*.json`、`figure_assets.json` | 2026-09-11 | 旧图像润色/资产记录 | 图形流水线元数据 | 否/过期 |

### 6.2 图的旧副本与预览

- `build/before_scheme_b/figures/*`：共 34 个旧 Scheme B 图与元数据，修改时间 2026-09-11，包含 `problem2.png`、`problem3.png`、`problem4.png` 等旧论文实际引用的文件名。分类：**旧版**，与当前 c-spec 数值不一致。
- `build/revision_backup_20260911/figures/problem2_diagnostic.png`：修订备份。分类：**旧版**。
- `build/timestamp_workbook_previews/result*.xlsx.png`：5 张 17:00 的工作簿预览。分类：**中间产物**，用于观察排版，不是结果图。
- `tmp/pdfs/*.png`：5 张题面 PDF 渲染页。分类：**中间产物**，属于资料检查缓存。

论文图链另有一个明确断点：当前 `report.md` 引用的是旧命名 `problem2.png`、`problem3.png`、`problem4*.png`，这些文件只存在于 `build/before_scheme_b/figures/`，不在当前根 `figures/`。因此当前论文与当前根图目录不是一个可闭合的发布包。

## 7. 论文正文及重复副本

| 分类 | 路径 | 修改时间 | SHA-256 前12位 | 来源 | 核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|---|---|
| 旧版 | `report.md` | 2026-09-12 09:17:06 | `791AF8844987` | Scheme B 最后发布稿 | Q1 35,101.57；Q2 19,257,140.05；Q3 19,123,232.50；Q4-2 20,381,775.13；Q4-3 20,169,378.52 | 否 |
| 旧版 | `chapters/problem1.md` | 2026-09-12 09:17:06 | `669EF729BCD8` | Scheme B Q1 章节 | Q1 总额相同，但时点值/时间轴与当前输出冲突 | 部分数值相同，模型链不闭合 |
| 旧版 | `chapters/problem2.md` | 2026-09-12 09:17:06 | `3ABC91B36011` | Scheme B Q2 章节 | 同星期中位数、近7日光伏；19,257,140.05 元 | 否 |
| 旧版 | `chapters/problem3.md` | 2026-09-12 09:17:06 | `E4C38BDCB9F7` | Scheme B Q3 章节 | 19,123,232.50 元 | 否 |
| 旧版 | `chapters/problem4.md` | 2026-09-12 09:17:06 | `B08DDBCF8747` | Scheme B Q4 章节 | 把当日电价曲线视作 0 时已知；20.382/20.169 百万元 | 否 |
| 旧版 | `build/_cumcm.md` | 2026-09-12 09:17:06 | `BC10C4C0C27F` | Scheme B 合并排版中间稿 | 与 `report.md` 同组旧结果 | 否 |
| 旧版 | `build/thesis.docx` | 2026-09-12 09:20:26 | `510FAD3ACDC2` | Scheme B DOCX 构建 | 旧结果论文 | 否 |
| 旧版 | `build/thesis_revised.docx` | 2026-09-12 09:20:26 | `F3077B6A0748` | Scheme B DOCX 修订版 | 旧结果论文 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/report.md` | 2026-09-11 21:11:05 | `F091A54C2D5F` | 时间轴修正前论文 | Scheme B 旧结果 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/thesis.docx` | 2026-09-11 21:13:40 | `B713C20173A9` | 时间轴修正前 DOCX | Scheme B 旧结果 | 否 |
| 旧版 | `build/before_timestamp_fix_20260912/thesis_revised.docx` | 2026-09-11 21:13:41 | `B713C20173A9` | 与上一 DOCX 完全相同 | Scheme B 旧结果 | 否 |
| 旧版 | `build/before_scheme_b/report.md` | 2026-09-11 20:27:16 | `3D5CC9D6CD78` | Scheme B 前论文快照 | 更早结果/文字 | 否 |
| 旧版 | `build/before_scheme_b/build/_cumcm.md` | 2026-09-11 20:27:16 | `ACB335A77935` | Scheme B 前合并稿 | 更早结果/文字 | 否 |
| 旧版 | `build/before_scheme_b/build/thesis.docx`、`thesis_revised.docx` | 2026-09-11 20:27:17 | `863703553BE0` | 两个文件完全相同的旧 DOCX | 更早论文 | 否 |
| 旧版 | `build/before_scheme_b/chapters/problem1.md` 至 `problem4.md` | 2026-09-11 20:27:16 | 各异 | Scheme B 前章节快照 | 更早章节 | 否 |
| 旧版 | `build/revision_backup_20260911/report.md` | 2026-09-11 13:18:25 | `55325BB53799` | 9月11日修订备份 | 更早结果/文字 | 否 |
| 旧版 | `build/revision_backup_20260911/build/_cumcm.md` | 2026-09-11 17:19:42 | `7F4AF205D2EB` | 9月11日合并稿备份 | 更早论文 | 否 |
| 旧版 | `build/revision_backup_20260911/build/thesis.docx` | 2026-09-11 17:19:45 | `D80D5BC4133F` | 9月11日 DOCX 备份 | 更早论文 | 否 |
| 旧版 | `build/revision_backup_20260911/chapters/problem1.md` 至 `problem4.md` | 2026-09-11 12:17–13:08 | 各异 | 9月11日章节备份 | 更早章节 | 否 |
| 旧版 | `journal/problem1.md` 及 `build/before_scheme_b/journal/problem1.md` 至 `problem4.md` | 2026-09-11 | 旧运行记录 | 逐题工作日志，不是论文正文 | 否/不适用 |

论文与当前代码还存在方法口径冲突：论文写的是“同星期中位数 + 近7日光伏均值、每日 SOC 回到 6000、Q4 当日电价全知”；当前 c-spec summary 写的是“最近3个同类型日均值 + 最近5日光伏均值、残差场景、安全裕度、终端价值、因果价格”。这不是简单的数值更新问题，而是来源版本不同。

## 8. 缓存与运行中间产物

### 8.1 c-spec 数值缓存

| 分类 | 路径 | 修改时间 | 来源/核心结果 | 与当前最终代码一致 |
|---|---|---:|---|---|
| 当前最终版 | `build/c_spec_cache/q2_fixed_a3de9cbf6b675e252f96.npz` | 2026-09-12 14:47:28 | 当前源码哈希命中的 Q2；13,701,658.50 元 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_6_12_18_rec_39c8fa1a4dd9cd8ca668.npz` | 2026-09-12 14:48:44 | 当前源码哈希命中的完整 Q3；13,266,622.73 元 | 是 |
| 当前最终版 | `build/c_spec_cache/q4_causal_q2_ea8d6fef4c7c10188c34.npz` | 2026-09-12 14:49:21 | 当前源码哈希命中的因果 Q4-2；14,401,772.58 元 | 是 |
| 当前最终版 | `build/c_spec_cache/q4_causal_q3_1b3f5149e97b5cda8e76.npz` | 2026-09-12 14:50:38 | 当前源码哈希命中的因果 Q4-3；13,953,460.93 元 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_none_29862a174c96d492597b.npz` | 2026-09-12 14:51:24 | Q3 无更新消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_6_3a067d4eebb2038e66a1.npz` | 2026-09-12 14:52:17 | Q3 仅6时更新消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_12_f35a5afae6d28c6a6894.npz` | 2026-09-12 14:53:03 | Q3 仅12时更新消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_18_20dc119bf1e9e477ff54.npz` | 2026-09-12 14:53:44 | Q3 仅18时更新消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_6_12_e952a232510846ee5f99.npz` | 2026-09-12 14:54:51 | Q3 6+12时消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_12_18_d24003d6a2ce0bb7a12e.npz` | 2026-09-12 14:55:46 | Q3 12+18时消融 | 是 |
| 当前最终版 | `build/c_spec_cache/q3_6_12_18_8a116a581929dd41771f.npz` | 2026-09-12 14:57:00 | Q3 另一完整/非追索对照 | 是 |
| 当前最终版 | `build/c_spec_cache/perfect_fixed_707929fa5b9cd670c7d6.npz` | 2026-09-12 14:57:03 | 固定价完美信息下界 | 是 |
| 当前最终版 | `build/c_spec_cache/q4_oracle_q2_93ee086cf647b4eb2ca6.npz` | 2026-09-12 14:57:51 | Q4-2 价格 oracle | 是 |
| 当前最终版 | `build/c_spec_cache/q4_oracle_q3_7542a1fc12e4829e1ae2.npz` | 2026-09-12 14:59:07 | Q4-3 价格 oracle | 是 |
| 当前最终版 | `build/c_spec_cache/perfect_variable_eb605db3aa7ca8fa8e3d.npz` | 2026-09-12 14:59:10 | 波动价完美信息下界；12,809,266.07 元 | 是 |
| 中间产物 | `build/c_spec_cache/q2_fixed_66803a4caf118279f23a.npz` | 2026-09-12 16:50:17 | 后续中间源码生成；Q2 数值碰巧未变 | 缓存键不匹配当前代码 |
| 中间产物 | `build/c_spec_cache/q3_6_12_18_rec_59b04cb113416e5a3780.npz` | 2026-09-12 16:51:37 | 后续中间 Q3；13,256,700.05 元 | 否 |
| 中间产物 | `build/c_spec_cache/q4_causal_q2_3a6c614f4bf4507930b8.npz` | 2026-09-12 16:52:22 | 后续中间 Q4-2；数值碰巧未变 | 缓存键不匹配当前代码 |
| 中间产物 | `build/c_spec_cache/q4_causal_q3_9ff4684b34212f2d72fe.npz` | 2026-09-12 16:53:42 | 后续中间 Q4-3；13,945,791.78 元 | 否 |

上述“当前最终版”缓存是复现加速资产，不应作为提交结果本身。它们只能在最终运行清单记录了代码哈希、输入哈希和缓存键时进入复现包。

### 8.2 其他缓存、检查件与流水线元数据

| 分类 | 路径/文件族 | 来源/核心内容 | 与当前最终代码一致 |
|---|---|---|---|
| 中间产物 | 根目录及 `src/__pycache__/*.pyc`（33 个 `.pyc`） | 多次 Python 运行的字节码；同时存在 Python 3.9/3.12 版本 | 不应交付，且生成时点混杂 |
| 中间产物 | `result1.xlsx.inspect.ndjson` 至 `result4-3.xlsx.inspect.ndjson` | 16:47–17:10 的工作簿结构检查转储，总计约 105 MB | 只用于审计 |
| 中间产物 | `build/agent/*.log` | 9月11日旧逐题运行日志 | 旧运行日志 |
| 中间产物 | `build/timestamp_workbook_previews/*.png` | 工作簿截图 | 只用于人工检查 |
| 中间产物 | `tmp/pdfs/*.png` | 题面 PDF 渲染缓存 | 不适用 |
| 中间产物 | `.audit_tmp_numeric.py` | 2026-09-12 18:38:02，上一轮只读数值核验脚本 | 审计工具，不是模型代码；按本轮要求保留未删除 |
| 旧版 | `build/scheme_b_tools/**` | Scheme B 文档/公式工具及其自带缓存、可执行文件 | 不属于当前 c-spec 交付 |
| 无法判断 | `.agent_memory.json`、`.agent_sessions.json`、`.cc_sessions.json`、`.qwen/**`、`.vscode/**` | 编辑器/代理会话配置 | 与科研结果无关，不应交付 |
| 旧版 | `artifact_manifest.json`、`evidence_gate.json`、`framework_tasks.json`、`modeling_plan.json`、`pipeline_events.jsonl`、`pipeline_state.json`、`pipeline_usage.json`、`meta.json`、`plan_snapshot.json`、`plan_parts/**`、`project_memory.json`、`writing_memory.json` | 旧代理/写作流水线状态 | 不能作为当前最终运行证明 |
| 无法判断 | `c建模说明与结果.txt` | 2026-09-12 13:36:19，模型规范/人工说明 | 是当前 c-spec 的规范来源，但不是可执行代码或结果；需在最终清单注明版本 |
| 无法判断 | `QWEN.md` | 旧代理说明 | 不属于交付 |

## 9. result1–4、summary、正文和图是否来自同一次最终运行

结论：**否。** 逐题矩阵如下。

| 问题 | 根工作簿 | `summary.json` | 当前 CSV/JSON | 当前图 | 论文正文 | 同一次最终运行？ |
|---|---|---|---|---|---|---|
| Q1 | 09:10 旧导出；35,101.57 元；官方标签偏移 | 不包含 Q1 | 16:47，指定时点与当前代码/论文冲突 | 16:47，同中间 Q1 | 09:17 Scheme B；总额相同但时点映射不同 | 否；且当前入口不能重建工作簿 |
| Q2 | 15:57；13,701,658.50 元 | 15:10；同总额 | 16:50；同总额 | 16:50；同总额但哈希不同 | 09:17；19,257,140.05 元 | 否；数值链部分相容，论文不相容 |
| Q3 | 15:08；13,266,622.73 元 | 15:10；13,266,622.73 元，完整消融 | 16:51；13,256,700.05 元，仅1条消融 | 16:51，同中间 Q3 | 09:17；19,123,232.50 元 | 否；工作簿/summary 与 CSV/图分叉 |
| Q4-2 | 15:08；14,401,772.58 元 | 15:10；同总额，含 oracle | 16:53；同因果总额，但只含4场景 | 16:53，4场景版 | 09:17；20,381,775.13 元 | 否；主数值相容但全量场景和论文不相容 |
| Q4-3 | 15:08；13,953,460.93 元 | 15:10；13,953,460.93 元，含 oracle | 16:53；13,945,791.78 元，只含4场景 | 16:53，同中间 Q4-3 | 09:17；20,169,378.52 元 | 否；工作簿/summary 与 CSV/图分叉 |

可以确认的局部同源关系只有：

- `result3.xlsx`、`result4-2.xlsx`、`result4-3.xlsx` 与 15:10 `summary.json` 的主结果来自同一条 c-spec 全量数值链；
- 当前活动源码哈希仍命中这条链的 `...39c8...`、`...ea8d...`、`...1b3f...` 缓存；
- Q2 后续运行数值未变，但 `result2.xlsx` 和图的二进制文件已经晚于原审计；
- 论文、Q1 工作簿、当前 Q3/Q4-3 CSV/JSON/图均不能并入该同源集合。

## 10. 唯一的 `FINAL/` 目录整理方案（仅方案，本轮不创建、不移动）

建议只采用下面这一棵目录树，不再建立 `final2`、`最终版`、`最新版` 等并行目录。`FINAL/` 在满足“单次干净运行 + 审计通过”之前保持不存在或为空；不得把当前冲突文件直接复制进去冒充最终版。

```text
FINAL/
├─ README_DELIVERY.md
├─ RUN_MANIFEST.json
├─ SHA256SUMS.txt
├─ submission/
│  ├─ 论文正文.docx
│  ├─ report.md
│  ├─ result1.xlsx
│  ├─ result2.xlsx
│  ├─ result3.xlsx
│  ├─ result4-2.xlsx
│  └─ result4-3.xlsx
└─ reproducibility/
   ├─ code/
   │  ├─ run_all.py
   │  └─ src/
   │     ├─ config.py
   │     ├─ time_axis.py
   │     ├─ dispatch_core.py
   │     ├─ scenario_cache.py
   │     ├─ problem1.py
   │     ├─ problem2.py
   │     ├─ problem3.py
   │     ├─ problem4.py
   │     ├─ reporting.py
   │     ├─ result_workbooks.py
   │     └─ build_summary.py
   ├─ environment/
   │  └─ requirements.lock
   ├─ inputs/
   │  ├─ SOURCE_HASHES.json
   │  └─ c建模说明与结果.txt
   ├─ results/
   │  ├─ summary.json
   │  ├─ summary.md
   │  ├─ problem1.json
   │  ├─ problem1_sensitivity.csv
   │  ├─ problem2.json
   │  ├─ problem2_daily.csv
   │  ├─ problem3.json
   │  ├─ problem3_daily.csv
   │  ├─ problem3_ablation.csv
   │  ├─ problem3_forecast_accuracy.csv
   │  ├─ problem4.json
   │  └─ problem4_*.csv
   ├─ figures/
   │  └─ 仅保留被最终论文实际引用且由该次运行生成的图
   ├─ audits/
   │  ├─ final_audit.json
   │  ├─ c_spec_unit_tests.json
   │  ├─ timestamp_alignment_audit.json
   │  ├─ timestamp_alignment_tests.json
   │  └─ q3_forecast_alignment_audit.json
   └─ cache/
      └─ 仅保留 RUN_MANIFEST 明确列出的源哈希匹配 `.npz`
```

唯一来源规则：

1. `submission/` 内所有文件必须由同一个 `run_id` 绑定；论文只能引用同一 `run_id` 的 summary 和 figures。
2. `RUN_MANIFEST.json` 必须记录：运行时间、Git/源码哈希、输入哈希、Python/依赖版本、随机种子、命中的缓存文件、每个输出文件完整 SHA-256、Q1–Q4 核心指标。
3. `result1.xlsx` 至 `result4-3.xlsx` 必须通过官方模板结构与时间轴审计；当前 staging 文件不得直接晋升。
4. `summary.json` 必须同时包含 Q1–Q4；当前 summary 缺 Q1，不能直接进入 `FINAL/`。
5. `final_audit.json` 必须在所有 CSV、图、论文和工作簿生成完毕后最后写出；其记录哈希必须与封包时哈希逐个相同。
6. `requirements.lock` 必须存在；当前工程没有可直接证明环境完整性的锁定依赖文件。
7. 以下内容永不进入 `FINAL/`：`build/before_*`、`build/revision_backup_*`、`build/official_template_alignment_staging`、`*.inspect.ndjson`、`__pycache__`、`*.pyc`、预览、日志、会话/代理状态、旧 Scheme B 工具、临时审计脚本。

## 11. 当前冻结状态

- **可作为下一轮唯一代码基线**：第 3.1 节列出的当前活动 c-spec 源码，但必须先解决 Q1 导出/总入口断链和官方模板时间轴问题。
- **可作为数值对照基线**：15:10 `summary.json` 中的 Q2/Q3/Q4 全量结果，以及与当前源码哈希匹配的 14:47–14:59 缓存；不得与 16:51–16:54 的中间 Q3/Q4-3 文件混用。
- **不可作为当前论文**：所有现存 `report.md`、章节和 DOCX 均为旧 Scheme B。
- **不可直接作为最终提交工作簿**：五个根结果工作簿均尚未形成通过最新时间轴审计的完整集合；Q1 还缺当前代码可复现链。
- **不可作为最终图集**：当前根图目录混合了 Q1 中间时间轴、Q2 后续同值运行、Q3/Q4-3 中间结果和旧静态机制图。

最终冻结判定：**未冻结（NO-GO）**。原因是“源码—单次运行—工作簿—summary—图—论文—最终审计”全链路尚未闭合。本结论只做盘点，不代表对模型方案进行重新设计或修改。
