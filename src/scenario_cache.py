"""Versioned, validated cache for the c-spec annual simulations."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import time

import numpy as np

from config import ENERGY_LIMIT, MODEL_VERSION, N, SOC_INITIAL, SOC_LOWER, SOC_UPPER

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "build" / "c_spec_cache"


def _hash_file(hasher, path: Path) -> None:
    hasher.update(str(path.relative_to(ROOT)).encode("utf-8"))
    hasher.update(path.read_bytes())


def cache_path(label: str, options: dict) -> Path:
    hasher = hashlib.sha256(MODEL_VERSION.encode("utf-8"))
    hasher.update(label.encode("utf-8"))
    hasher.update(json.dumps(options, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for path in [ROOT/"src/config.py", ROOT/"src/dispatch_core.py", ROOT/"src/scenario_cache.py",
                 ROOT/"data/附件/附件1.xlsx", ROOT/"data/附件/附件2.xlsx",
                 ROOT/"data/附件/附件3.xlsx", ROOT/"data/附件/附件4.xlsx"]:
        _hash_file(hasher, path)
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / f"{label}_{hasher.hexdigest()[:20]}.npz"


def audit_record(record: dict) -> None:
    a = record["actual"]
    if a["soc"].min() < SOC_LOWER-1e-7 or a["soc"].max() > SOC_UPPER+1e-7:
        raise AssertionError("SOC bound violated")
    if a["charge"].min() < -1e-9 or a["discharge"].min() < -1e-9:
        raise AssertionError("negative charge/discharge")
    if a["charge"].max() > ENERGY_LIMIT+1e-7 or a["discharge"].max() > ENERGY_LIMIT+1e-7:
        raise AssertionError("charge/discharge limit violated")
    np.testing.assert_allclose(np.diff(a["soc"]), 0.9*a["charge"]-a["discharge"]/0.9,
                               rtol=0, atol=1e-7)
    if np.max(np.abs(a["residual"])) > 1e-7:
        raise AssertionError("energy balance violated")
    if np.any((a["charge"] > 1e-8) & (a["discharge"] > 1e-8)):
        raise AssertionError("simultaneous charge/discharge")


def pack(path: Path, records: list[dict]) -> None:
    days = len(records)
    update_purchase = np.full((days, 3, N), np.nan)
    update_hours = np.full((days, 3), -1, dtype=int)
    for i, record in enumerate(records):
        for j, update in enumerate(record.get("updates", [])[:3]):
            update_purchase[i,j] = update["purchase"]
            update_hours[i,j] = int(update["release_hour"])
    np.savez_compressed(
        path,
        date=np.asarray([r["date"] for r in records]),
        plan=np.asarray([r["plan"]["purchase"] for r in records]),
        final=np.asarray([r["final_purchase"] for r in records]),
        charge=np.asarray([r["actual"]["charge"] for r in records]),
        discharge=np.asarray([r["actual"]["discharge"] for r in records]),
        emergency=np.asarray([r["actual"]["emergency"] for r in records]),
        waste=np.asarray([r["actual"]["waste"] for r in records]),
        residual=np.asarray([r["actual"]["residual"] for r in records]),
        soc=np.asarray([r["actual"]["soc"] for r in records]),
        seconds=np.asarray([r.get("seconds", r["plan"]["seconds"]) for r in records]),
        scenario_count=np.asarray([r["plan"].get("scenario_count", 0) for r in records]),
        recourse_plan=np.asarray([r.get("recourse_plan", False) for r in records]),
        update_purchase=update_purchase,
        update_hours=update_hours,
    )


def unpack(path: Path) -> list[dict]:
    with np.load(path, allow_pickle=False) as data:
        records = []
        for i, date in enumerate(data["date"]):
            updates = []
            for j, hour in enumerate(data["update_hours"][i]):
                if hour >= 0:
                    updates.append({"release_hour":int(hour), "purchase":data["update_purchase"][i,j].copy(),
                                    "seconds":0.0, "observed_prefix_end":int(hour)*6})
            seconds=float(data["seconds"][i])
            records.append({"date":str(date),
                "plan":{"purchase":data["plan"][i].copy(),"seconds":seconds,
                        "scenario_count":int(data["scenario_count"][i]),"status":"optimal"},
                "final_purchase":data["final"][i].copy(),
                "actual":{name:data[name][i].copy() for name in ("charge","discharge","emergency","waste","residual","soc")},
                "updates":updates,"seconds":seconds,"recourse_plan":bool(data["recourse_plan"][i])})
        return records


def run_continuous(label: str, options: dict, last_index: int, runner,
                   use_cache: bool = True) -> list[dict]:
    """Run Jan 1 through ``last_index`` so Feb 1 inherits the Jan 31 SOC."""
    path = cache_path(label, options)
    if use_cache and path.exists():
        records = unpack(path)
        for record in records:
            audit_record(record)
        for left, right in zip(records, records[1:]):
            if abs(left["actual"]["soc"][-1]-right["actual"]["soc"][0]) > 1e-7:
                raise AssertionError("cached cross-day SOC discontinuity")
        print(f"复用当前模型版本缓存 {label}: {len(records)}天", flush=True)
        return records
    records=[]; soc=SOC_INITIAL; tic=time.perf_counter()
    for i in range(last_index+1):
        record=runner(i,soc)
        audit_record(record)
        if abs(record["actual"]["soc"][0]-soc)>1e-7:
            raise AssertionError("cross-day SOC start mismatch")
        records.append(record); soc=float(record["actual"]["soc"][-1])
        if (i+1)%25==0 or i==last_index:
            print(f"{label}: {i+1}/{last_index+1}天, {time.perf_counter()-tic:.1f}s",flush=True)
    pack(path,records)
    return records
