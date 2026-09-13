# 微网与外部电网电力调控策略

2026 CUMCM C题建模项目。项目围绕单日最优购电、全年随机调度、日内滚动优化和动态电价信息价值展开，包含完整模型代码、原始附件、年度计算缓存、结果表、正文图及一致性审计材料。

## 当前版本

- 结果运行ID：`c-spec-20260912T200729+0800`
- 模型版本：`c-spec-v1-2026-09-12`
- Python版本：3.12
- 最终运行审计：PASS
- 正文图集：Q1–Q4共14张主图（14个PNG、13个PDF）

## 问题结构

| 问题 | 主要内容 |
|---|---|
| Q1 | 基于连续线性规划的单日最优购电与储能调度 |
| Q2 | 考虑负荷和光伏预测误差的全年随机日前调度 |
| Q3 | 6:00、12:00和18:00信息更新下的滚动优化 |
| Q4 | 动态电价预测、信息价值及电价波动灵敏度分析 |

## 快速开始

推荐使用64位Python 3.12。在项目根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-final.txt
```

先运行核心测试：

```powershell
.\.venv\Scripts\python.exe src\test_c_spec.py
```

使用仓库中已有年度缓存执行完整结果链：

```powershell
.\.venv\Scripts\python.exe run_all.py
```

仅在确需从零重新计算时使用：

```powershell
.\.venv\Scripts\python.exe run_all.py --fresh
```

> `--fresh` 会删除当前生成结果和活动缓存后重新计算。执行前建议保留Git提交或独立备份。

## 目录结构

```text
.
├─ data/附件/               原始数据及官方结果模板
├─ question/                赛题PDF
├─ src/                     模型、绘图、审计与测试代码
├─ build/c_spec_cache/      最终年度实验缓存
├─ results/                 JSON、CSV和一致性审计结果
├─ new_figures_main/        Q1–Q4论文正文主图
├─ old_figures/             历史图件，仅供追溯
├─ 论文构建/                 论文事实基线、结构与写作材料
├─ paper_draft_legacy/      旧版论文草稿，仅供结构参考
├─ result1.xlsx             Q1正式结果工作簿
├─ result2.xlsx             Q2正式结果工作簿
├─ result3.xlsx             Q3正式结果工作簿
├─ result4-2.xlsx           Q4-2正式结果工作簿
├─ result4-3.xlsx           Q4-3正式结果工作簿
└─ run_all.py               全链复现入口
```

`build/c_spec_cache/` 虽属于计算缓存，但正文图和现有结果链会直接读取其中的最终实验结果，因此纳入版本控制。虚拟环境、Python缓存和 `tmp/` 检查文件由 `.gitignore` 排除。

## 主要结果

| 方案 | 费用（元） |
|---|---:|
| Q1 | 35,101.567554 |
| Q2 | 13,701,658.500733 |
| Q3 | 13,266,622.729589 |
| Q4-2 causal | 14,401,772.581567 |
| Q4-3 causal | 13,953,460.931182 |

以上数值来自当前最终运行；引用前可通过 [`FINAL_RUN_MANIFEST.md`](FINAL_RUN_MANIFEST.md) 和 [`results/final_audit.json`](results/final_audit.json) 复核。

## 正文图表

正文主图位于 [`new_figures_main/`](new_figures_main/)，采用 `Qx_Fy_语义名` 命名：

- Q1：3张
- Q2：3张
- Q3：4张
- Q4：4张

完整图题、数据来源、panel含义和推荐caption见：

- [`FIGURE_MANIFEST.md`](new_figures_main/FIGURE_MANIFEST.md)
- [`FIGURE_AUDIT.md`](new_figures_main/FIGURE_AUDIT.md)

Q1图仅进行了文件名体系整理，图像内容、模型数据和绘图代码均未修改。Q1-F3的既有最终成品只有PNG，因此未补造PDF。

## 结果与审计入口

- [`START_HERE.md`](START_HERE.md)：迁移、环境与重跑说明
- [`FINAL_RUN_MANIFEST.md`](FINAL_RUN_MANIFEST.md)：运行环境、核心结果和文件哈希
- [`FINAL_DELIVERY_AUDIT.md`](FINAL_DELIVERY_AUDIT.md)：最终交付一致性审计
- [`DELIVERABLE_INVENTORY.md`](DELIVERABLE_INVENTORY.md)：交付文件清单
- [`论文构建/00_事实基线.md`](论文构建/00_事实基线.md)：论文写作的事实口径
- [`论文构建/06_关键结果与数字核验.md`](论文构建/06_关键结果与数字核验.md)：关键数字核验

## 使用约定

- 修改模型、预测规则、参数或结算逻辑后，应重新运行对应测试和结果链。
- `paper_draft_legacy/` 中的旧稿不得直接作为当前结果口径引用。
- 正式论文优先使用 `new_figures_main/` 中的主图，不使用 `old_figures/` 中的历史图件。
- 不手工修改结果表中的模型输出；应通过源码和复现入口生成。
