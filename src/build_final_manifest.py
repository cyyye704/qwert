"""Generate a provenance and integrity manifest for one completed run."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODEL_SOURCE_FILES = (
    "src/config.py",
    "src/dispatch_core.py",
    "src/scenario_cache.py",
    "src/problem1.py",
    "src/problem2.py",
    "src/problem3.py",
    "src/problem4.py",
)

ENGINEERING_FILES = (
    "run_all.py",
    "src/time_axis.py",
    "src/result_workbooks.py",
    "src/reporting.py",
    "src/build_summary.py",
    "src/test_c_spec.py",
    "src/test_timestamp_alignment.py",
    "src/audit_timestamp_alignment.py",
    "src/audit_q3_forecast_alignment.py",
    "src/validate_typical_days.py",
    "src/build_final_manifest.py",
    "src/problem4_sensitivity.py",
    "plot_style.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "NOT INSTALLED"


def main() -> None:
    summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "results/final_audit.json").read_text(encoding="utf-8"))
    timestamp = json.loads((ROOT / "results/timestamp_alignment_audit.json").read_text(encoding="utf-8"))
    run_id = summary["run_id"]

    inputs = [f"data/附件/附件{i}.xlsx" for i in range(1, 5)]
    workbooks = ["result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx"]
    results = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for pattern in (
            "problem1*", "problem2*", "problem3*", "problem4*",
            "summary.md", "final_audit.json", "c_spec_unit_tests.json",
            "c_spec_typical_day_validation.json", "timestamp_alignment_*.json",
            "q3_forecast_alignment_audit.json",
        )
        for path in (ROOT / "results").glob(pattern)
        if path.is_file()
    )
    figures = sorted(audit["figures"]["sha256"])
    caches = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "build/c_spec_cache").glob("*.npz")
    )
    tracked = sorted(set([
        *inputs,
        *MODEL_SOURCE_FILES,
        *ENGINEERING_FILES,
        *workbooks,
        "summary.json",
        *results,
        *figures,
        *caches,
        "c建模说明与结果.txt",
        "requirements-final.txt",
        "SOURCE_HASHES.md",
        "FINAL_DELIVERY_AUDIT.md",
    ]))
    file_hashes = {name: sha256(ROOT / name) for name in tracked}

    q4_rows = {row["scenario"]: row for row in summary["q4"]["scenarios"]}
    core = {
        "Q1_cost_yuan": summary["q1"]["daily_purchase_cost_yuan"],
        "Q1_purchase_kwh": summary["q1"]["daily_purchase_kwh"],
        "Q2_cost_yuan": summary["q2"]["annual"]["total_cost_yuan"],
        "Q3_cost_yuan": summary["q3"]["full_scheme"]["total_cost_yuan"],
        "Q4_2_cost_yuan": q4_rows["causal Q4-2"]["total_cost_yuan"],
        "Q4_3_cost_yuan": q4_rows["causal Q4-3"]["total_cost_yuan"],
    }
    dependencies = {
        name: version(name)
        for name in ("numpy", "pandas", "scipy", "openpyxl", "matplotlib", "tabulate")
    }
    unresolved = []
    if not audit.get("final_delivery_chain_pass"):
        unresolved.append("results/final_audit.json did not pass the complete delivery chain")
    if timestamp.get("verdict") != "PASS":
        unresolved.append("timestamp alignment did not pass")
    verdict = "PASS" if not unresolved else "FAIL"

    lines = [
        "# FINAL RUN MANIFEST", "",
        f"- Verdict: **{verdict}**",
        f"- Run ID: `{run_id}`",
        f"- MODEL_VERSION: `{summary['model_version']}`",
        f"- Manifest generated: `{datetime.now().astimezone().isoformat()}`",
        f"- Fresh numerical run: `{os.environ.get('FINAL_RUN_FRESH', 'unknown')}`", "",
        "## Python environment", "",
        f"- Executable: `{sys.executable}`",
        f"- Python: `{platform.python_version()}`",
        f"- Platform: `{platform.platform()}`", "",
        "| Dependency | Version |", "|---|---|",
        *[f"| {name} | `{value}` |" for name, value in dependencies.items()], "",
        "## Model source policy", "",
        "- Model source files are versioned by the run manifest but are not compared against a hard-coded baseline.",
        "- Changing model source no longer blocks manifest generation; rerun the numerical chain after substantive changes.", "",
        "## Core results", "",
        "| Metric | Value |", "|---|---:|",
        *[f"| {name} | {value:.12f} |" for name, value in core.items()], "",
        "## Time-axis acceptance", "",
        f"- Verdict: `{timestamp.get('verdict')}`",
        f"- Mapping: `{timestamp.get('confirmed_interpretation', {}).get('mapping')}`",
        f"- Array shift/roll used: `{timestamp.get('confirmed_interpretation', {}).get('array_shift_or_roll_used')}`",
        f"- Release boundaries: `{json.dumps(timestamp.get('release_boundaries'), ensure_ascii=False)}`", "",
        "## Tests", "",
        f"- Unit/physical audit: `{audit.get('energy_balance_pass')}`",
        f"- Five workbooks match sources: `{audit.get('all_five_workbooks_match_sources')}`",
        f"- Timestamp tests: `{audit.get('timestamp_tests_pass')}`",
        f"- Final delivery chain: `{audit.get('final_delivery_chain_pass')}`", "",
        "## Unresolved issues", "",
        *( ["- None."] if not unresolved else [f"- {item}" for item in unresolved] ), "",
        "## File hashes", "",
        "| Path | SHA-256 |", "|---|---|",
        *[f"| `{name}` | `{digest}` |" for name, digest in file_hashes.items()], "",
    ]
    manifest = ROOT / "FINAL_RUN_MANIFEST.md"
    manifest.write_text("\n".join(lines), encoding="utf-8")
    checksum_lines = [f"{digest}  {name}" for name, digest in file_hashes.items()]
    checksum_lines.append(f"{sha256(manifest)}  FINAL_RUN_MANIFEST.md")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "run_id": run_id,
        "tracked_files": len(file_hashes),
        "manifest": "FINAL_RUN_MANIFEST.md",
        "checksums": "SHA256SUMS.txt",
    }, ensure_ascii=False, indent=2))
    if verdict != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
