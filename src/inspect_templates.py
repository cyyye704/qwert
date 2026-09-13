"""探查附件5结果模板的工作表与表头结构(只读)。"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "data" / "附件" / "附件5"

for name in ["result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx"]:
    xl = pd.ExcelFile(TPL / name)
    print("=" * 60)
    print(name, xl.sheet_names)
    for sh in xl.sheet_names:
        df = xl.parse(sh, header=None, nrows=5)
        print(f"  [{sh}] head:")
        print(df.to_string(max_cols=10))
