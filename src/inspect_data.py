"""探查附件结构:工作表名、形状、列名、前几行、缺失。仅做只读检查。"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ATT = ROOT / "data" / "附件"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def probe(path: Path, nrows: int = 4) -> None:
    print("=" * 70)
    print("FILE:", path.name)
    xl = pd.ExcelFile(path)
    print("sheets:", xl.sheet_names)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        print("-" * 60)
        print(f"[{sh}] shape={df.shape}")
        print("columns(前12):", list(df.columns)[:12])
        print("dtypes(前6):", dict(list(df.dtypes.astype(str).items())[:6]))
        print(df.head(nrows).to_string())
        print("tail:")
        print(df.tail(2).to_string())
        print("na_total:", int(df.isna().sum().sum()))


for name in ["附件1.xlsx", "附件2.xlsx", "附件3.xlsx", "附件4.xlsx"]:
    probe(ATT / name)

print("=" * 70)
for name in ["result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx"]:
    p = ATT / "附件5" / name
    xl = pd.ExcelFile(p)
    print("TEMPLATE:", name, "sheets:", xl.sheet_names)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        print(f"  [{sh}] shape={df.shape} cols(前10)={list(df.columns)[:10]}")
        print(df.head(3).to_string())
