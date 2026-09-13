"""Canonical mapping between source right endpoints and internal 10-minute slots."""
from __future__ import annotations

import datetime as dt
from typing import Iterable

import numpy as np

from config import DT, N, STEPS_PER_HOUR, TIME_STEP_MINUTES


def boundary_label(minutes: int) -> str:
    """Format an internal-day boundary, spelling 24:00 as next-day 0:00."""
    if minutes < 0 or minutes > 24 * 60:
        raise ValueError(f"boundary outside one day: {minutes} min")
    if minutes == 24 * 60:
        return "0:00+1"
    hour, minute = divmod(minutes, 60)
    return f"{hour}:{minute:02d}"


def slot_label(index: int) -> str:
    """Return the interval represented by internal slot index ``index``."""
    if not 0 <= index < N:
        raise IndexError(index)
    start = index * TIME_STEP_MINUTES
    return f"{boundary_label(start)}-{boundary_label(start + TIME_STEP_MINUTES)}"


def interval_label(start: int, end: int) -> str:
    """Return the half-open interval covering slots ``start:end``."""
    if not 0 <= start < end <= N:
        raise ValueError((start, end))
    return f"{boundary_label(start * TIME_STEP_MINUTES)}-{boundary_label(end * TIME_STEP_MINUTES)}"


def all_slot_labels() -> list[str]:
    return [slot_label(i) for i in range(N)]


def interval_start_index(hour: int) -> int:
    """Map HH:00-HH:10 to the first slot beginning at HH:00."""
    index = hour * STEPS_PER_HOUR
    if not 0 <= index < N:
        raise ValueError(hour)
    return index


def right_endpoint_hours() -> np.ndarray:
    """Coordinates of source observations labelled by each slot's right endpoint."""
    return (np.arange(N, dtype=float) + 1.0) * DT


def interval_start_hours() -> np.ndarray:
    return np.arange(N, dtype=float) * DT


def _endpoint_minutes(value) -> int:
    if isinstance(value, dt.datetime):
        value = value.time()
    if isinstance(value, dt.time):
        return value.hour * 60 + value.minute
    if isinstance(value, dt.timedelta):
        return round(value.total_seconds() / 60)
    if isinstance(value, (float, np.floating)) and 0 <= float(value) <= 1:
        return round(float(value) * 24 * 60)
    text = str(value).strip()
    if text.endswith("+1"):
        text = text[:-2]
        day = 1
    else:
        day = 0
    parts = text.split(":")
    if len(parts) < 2:
        raise ValueError(f"unrecognized timestamp {value!r}")
    return day * 24 * 60 + int(parts[0]) * 60 + int(parts[1])


def validate_right_endpoint_axis(values: Iterable, source: str) -> None:
    """Require 00:10,...,24:00, treating a final 00:00 header as 24:00."""
    minutes = [_endpoint_minutes(value) for value in values]
    if len(minutes) == N and minutes[-1] == 0:
        minutes[-1] = 24 * 60
    expected = list(range(TIME_STEP_MINUTES, 24 * 60 + 1, TIME_STEP_MINUTES))
    if minutes != expected:
        mismatch = next((i for i, pair in enumerate(zip(minutes, expected)) if pair[0] != pair[1]), None)
        detail = f"first mismatch at slot {mismatch}: got {minutes[mismatch]}, expected {expected[mismatch]}" if mismatch is not None else f"length {len(minutes)}, expected {N}"
        raise ValueError(f"{source} is not the required 10-minute right-endpoint axis ({detail})")
