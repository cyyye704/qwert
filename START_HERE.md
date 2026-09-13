# 项目迁移包使用说明

本目录用于把项目迁移到另一台电脑继续开发，不是只供提交的 `FINAL/` 快照。

## 当前状态

- 当前结果运行 ID：`c-spec-20260912T200729+0800`
- 当前模型版本：`c-spec-v1-2026-09-12`
- 唯一全链入口：`python run_all.py`
- 源码哈希冻结已经取消；模型源码可以继续修改。
- `SHA256SUMS.txt`、`SOURCE_HASHES.md` 和迁移清单中的哈希仅用于传输完整性与结果溯源，不会阻止修改。
- 五个根目录 `result*.xlsx`、`summary.json`、`results/`、`figures/` 与 `build/c_spec_cache/` 是当前同一结果链。

## 建议放置位置

解压到较短的本地路径，例如：

```text
D:\c_project
```

不要继续放在很深的微信接收目录中，以免 Windows 长路径影响安装依赖、压缩或读取文件。

## 新电脑首次配置

需要 64 位 Python 3.12。进入本目录后执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-final.txt
```

快速验证现有代码与输入：

```powershell
.\.venv\Scripts\python.exe src\test_c_spec.py
```

使用已携带的年度缓存运行完整生成链：

```powershell
.\.venv\Scripts\python.exe run_all.py
```

需要从空缓存重新计算全部模型时才使用：

```powershell
.\.venv\Scripts\python.exe run_all.py --fresh
```

注意：`--fresh` 会删除本迁移副本中的当前工作簿、结果、图和活动缓存后重新生成。建议先保留原 ZIP，再执行该命令。

## 目录说明

- `data/附件/`：四个原始数据工作簿及附件5官方输出模板，重跑必需。
- `question/C题.pdf`：原题 PDF。
- `src/`：当前模型、输出、审计、测试和少量数据检查工具。
- `build/c_spec_cache/`：当前可验证的年度计算缓存；可以删除，但删除后重算时间较长。
- `results/`：当前 JSON、CSV、summary 和审计结果。
- `figures/`：当前正式图集，共26个文件。
- 根目录 `result1.xlsx` 至 `result4-3.xlsx`：五个当前正式工作簿。
- `paper_draft_legacy/`：旧 Scheme B 论文草稿，只作文字结构参考，数值和模型口径不能直接引用。
- `docs/`：历史修复方案和输入说明。

## 当前核心结果

| 结果 | 费用（元） |
|---|---:|
| Q1 | 35,101.567554 |
| Q2 | 13,701,658.500733 |
| Q3 | 13,266,622.729589 |
| Q4-2 causal | 14,401,772.581567 |
| Q4-3 causal | 13,953,460.931182 |

## 有意排除的内容

迁移包未复制以下内容：

- `.final_runtime_*`、`.final_wheels*` 和任何本机 Python 运行环境；
- `__pycache__`、`.pyc`、临时 PDF 图片、检查预览和会话状态；
- `archive/`、`build/before_*`、`build/revision_backup_*` 等历史快照；
- 旧 Scheme B 结果链和旧发布脚本；
- `FINAL/` 重复副本。

这些排除项不会影响在新电脑继续修改或重新运行当前模型。
