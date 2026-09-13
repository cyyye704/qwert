"""汇总附件的字段、规模、时间覆盖与数值范围，仅用于方案阶段数据核查。"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ATT = ROOT / "data" / "附件"


def matrix_summary(name: str, sheet: str | int = 0) -> None:
    df = pd.read_excel(ATT / name, sheet_name=sheet)
    dates = pd.to_datetime(df.iloc[:, 0])
    values = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    print(
        f"{name}/{sheet}: shape={df.shape}, dates={dates.min().date()}..{dates.max().date()}, "
        f"values={values.size}, missing={np.isnan(values).sum()}, min={np.nanmin(values):.4f}, "
        f"max={np.nanmax(values):.4f}, mean={np.nanmean(values):.4f}, std={np.nanstd(values):.4f}"
    )


a1 = pd.read_excel(ATT / "附件1.xlsx")
print("附件1:", a1.shape, list(a1.columns))
for col in ["电价", "小区负载", "光伏发电预测功率"]:
    x = pd.to_numeric(a1[col], errors="coerce")
    print(f"  {col}: missing={x.isna().sum()}, min={x.min():.4f}, max={x.max():.4f}, mean={x.mean():.4f}, std={x.std():.4f}")

matrix_summary("附件2.xlsx", "小区负载")
matrix_summary("附件2.xlsx", "光伏发电实际功率")

f = pd.read_excel(ATT / "附件3.xlsx")
forecast_cols = [c for c in f.columns if str(c).startswith("预报") and str(c) != "预报时刻"]
forecast = f[forecast_cols].apply(pd.to_numeric, errors="coerce").to_numpy(float)
print(
    f"附件3: shape={f.shape}, dates={f['日期'].iloc[0]}..{f['日期'].iloc[-1]}, "
    f"发布时刻={sorted(f['预报时刻'].astype(str).unique().tolist())}, forecast_cols={len(forecast_cols)}, "
    f"missing={np.isnan(forecast).sum()}, min={np.nanmin(forecast):.4f}, max={np.nanmax(forecast):.4f}, mean={np.nanmean(forecast):.4f}"
)

matrix_summary("附件4.xlsx", "Sheet1")
