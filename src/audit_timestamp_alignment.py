"""Audit the confirmed label-only j-to-j Attachment 5 mapping."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from test_timestamp_alignment import audit_workbooks  # noqa: E402

OLD_AUDIT = ROOT / "archive" / "pre_final_20260912" / "results" / "timestamp_alignment_audit.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "timestamp_alignment_audit.json")
    args = parser.parse_args()

    checks = audit_workbooks(args.workbook_root.resolve())
    old_payload = json.loads(OLD_AUDIT.read_text(encoding="utf-8")) if OLD_AUDIT.exists() else {}
    report = {
        "verdict": "PASS" if checks["final_workbooks_ready"] else "FAIL",
        "confirmed_interpretation": {
            "internal_axis": "144 natural-day ten-minute intervals from 0:00-0:10 through 23:50-0:00+1",
            "source_timestamps": "right endpoints of the represented internal intervals",
            "template_action": "replace the 144 display labels only",
            "mapping": "template position j <- internal j",
            "array_shift_or_roll_used": False,
        },
        "release_boundaries": checks["release_boundaries"],
        "key_labels": checks["key_labels"],
        "workbooks": checks["workbooks"],
        "supersedes": {
            "path": str(OLD_AUDIT.relative_to(ROOT)) if OLD_AUDIT.exists() else None,
            "sha256": _sha256(OLD_AUDIT) if OLD_AUDIT.exists() else None,
            "prior_verdict": old_payload.get("verdict"),
            "why_prior_conclusion_is_no_longer_applicable": (
                "The prior audit treated Attachment 5's original labels as an immutable physical axis and "
                "therefore derived a j-to-j+1 cross-day mapping. The confirmed delivery rule instead corrects "
                "those display labels ten minutes earlier while retaining every result value at position j."
            ),
        },
        "model_or_internal_index_changed": False,
        "final_workbooks_ready": bool(checks["final_workbooks_ready"]),
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
