#!/usr/bin/env python3
"""Run the c-spec implementation in its required validation/order sequence."""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))


def cleanup():
    exact=[ROOT/name for name in ["result1.xlsx","result2.xlsx","result3.xlsx","result4-2.xlsx","result4-3.xlsx",
        "summary.json","FINAL_RUN_MANIFEST.md","SHA256SUMS.txt","result1.xlsx.inspect.ndjson",
        "result2.xlsx.inspect.ndjson","result3.xlsx.inspect.ndjson","result4-2.xlsx.inspect.ndjson","result4-3.xlsx.inspect.ndjson"]]
    result_patterns=["problem1*","problem2*","problem3*","problem4*","summary.md","final_audit.json",
                     "c_spec_unit_tests.json","c_spec_typical_day_validation.json",
                     "timestamp_alignment_*.json","q3_forecast_alignment_audit.json"]
    figure_patterns=["problem1*","P2_*","P3_*","P4*","problem2*","problem3*","problem4*",
                     "forecast_pv_mae.png","_figure_lint.json"]
    targets=exact[:]
    for pattern in result_patterns: targets.extend((ROOT/"results").glob(pattern))
    for pattern in figure_patterns: targets.extend((ROOT/"figures").glob(pattern))
    for path in sorted(set(targets),key=lambda p:str(p)):
        resolved=path.resolve()
        if ROOT.resolve() not in resolved.parents:
            raise RuntimeError(f"refuse cleanup outside project: {resolved}")
        if path.is_file() or path.is_symlink(): path.unlink()
    for folder in [ROOT/"build/scheme_b_cache",ROOT/"build/c_spec_cache"]:
        if folder.exists():
            resolved=folder.resolve()
            if ROOT.resolve() not in resolved.parents: raise RuntimeError(resolved)
            shutil.rmtree(folder)


def checked(script):
    subprocess.run([sys.executable,str(ROOT/"src"/script)],cwd=ROOT,check=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fresh",action="store_true")
    args=parser.parse_args()
    if args.fresh: cleanup()
    os.environ["FINAL_RUN_ID"]=dt.datetime.now().astimezone().strftime("c-spec-%Y%m%dT%H%M%S%z")
    os.environ["FINAL_RUN_FRESH"]="true" if args.fresh else "false"
    print("阶段A：底层单元与因果性测试",flush=True); checked("test_c_spec.py")
    print("阶段B：四个典型日隔离验证",flush=True); checked("validate_typical_days.py")
    print("阶段C0：Q1单日模型、图与正式工作簿",flush=True); checked("problem1.py")
    import dispatch_core as core
    from problem2 import run_problem2
    from problem3 import run_problem3
    from problem4 import run_problem4
    from problem4_sensitivity import run_problem4_sensitivity
    data=core.load_data(); fixed,variable,load,pv,dates,forecasts=data
    bundle=core.build_causal_forecasts(load,pv,variable,dates,forecasts,fixed)
    print("阶段C1：Q2全年",flush=True)
    q2_all,_,_,_,_,_=run_problem2(use_cache=True,data=data,bundle=bundle)
    print("阶段C2：Q3完整方案、全部消融与固定价完美信息下界",flush=True)
    q3_all,_,_,_,_,_=run_problem3(use_cache=True,q2_records_all=q2_all,bundle=bundle,data=data,include_ablations=True)
    print("阶段C3：Q4主方案、价格oracle与完美信息下界",flush=True)
    run_problem4(use_cache=True,data=data,bundle=bundle,q2_fixed_all=q2_all,q3_fixed_all=q3_all,include_oracles=True)
    print("阶段C4：Q4电价日内波动灵敏度",flush=True)
    run_problem4_sensitivity(use_cache=True,data=data)
    print("阶段D1：Q3发布边界审计",flush=True); checked("audit_q3_forecast_alignment.py")
    print("阶段D2：五工作簿时间轴测试",flush=True); checked("test_timestamp_alignment.py")
    print("阶段D3：时间轴审计",flush=True); checked("audit_timestamp_alignment.py")
    print("阶段D4：统一summary与最终一致性审计",flush=True); checked("build_summary.py")
    print("阶段D5：最终运行manifest",flush=True); checked("build_final_manifest.py")
    print("全部完成",flush=True)


if __name__=="__main__": main()
