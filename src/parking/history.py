"""Per-space reference levels learned from unlabelled frames of the same camera.

The camera is fixed, so every space is seen many times. Over enough frames it is free
part of the time and taken part of the time, and the spread of its own measure says
what free and taken look like for that space. No occupancy label is read here.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from . import annotations as ann
from . import split

FIELDS = ["lot", "weather", "date", "frame", "partition", "space_id"]


def history_frames(data: Path, split_rows: list[dict], calibrate_on: str,
                   per_weather: int) -> list[dict]:
    """Frames outside the split, spread over every lot and weather.

    Each frame keeps the partition of its date, so the calibration partition can be
    restricted to history from calibration dates.
    """
    used = {r["frame"] for r in split_rows}
    rows = []
    for lot in split.LOTS:
        frames = [f for f in ann.list_frames(data, lot)
                  if f.relative_to(data).as_posix() not in used]
        if lot == calibrate_on:
            all_dates = [split.frame_date(f) for f in ann.list_frames(data, lot)]
            partition_of = split.assign_dates(all_dates)
        else:
            partition_of = {split.frame_date(f): split.TEST for f in frames}

        for weather in split.WEATHERS:
            in_weather = [f for f in frames if f.parent.parent.name == weather]
            for frame in split.sample_evenly(in_weather, per_weather):
                rows.append({"lot": lot, "weather": weather, "date": split.frame_date(frame),
                             "frame": frame.relative_to(data).as_posix(),
                             "partition": partition_of[split.frame_date(frame)]})
    return rows


def levels(values, low: float, high: float) -> tuple[float, float]:
    """Free and taken levels of one space: two percentiles of its history."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return float("nan"), float("nan")
    return float(np.percentile(values, low)), float(np.percentile(values, high))


def offset(value: float, free: float) -> float:
    """Measure above the free level of the space."""
    return value - free


def rescale(value: float, free: float, taken: float, min_spread: float) -> float:
    """Measure placed between the free (0) and taken (1) levels of the space.

    `min_spread` keeps a space that barely changed in its history, always free or
    always taken, from turning small noise into a large value.
    """
    return (value - free) / max(taken - free, min_spread)


class SpaceHistory:
    """History values of every space, looked up without the date being judged."""

    def __init__(self, rows: list[dict], name: str):
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row["lot"], row["space_id"])].append(
                (row["date"], row["partition"], float(row[name])))
        self._spaces = {
            key: (np.array([d for d, _, _ in items]), np.array([p for _, p, _ in items]),
                  np.array([v for _, _, v in items]))
            for key, items in grouped.items()
        }
        self._cache: dict = {}

    def values_for(self, lot: str, space_id: str, date: str, partition: str) -> np.ndarray:
        """History of the space, leaving out the frame's own date.

        A calibration frame only sees calibration dates, so nothing from the test
        days, not even unlabelled, shapes the calibrated threshold.
        """
        key = (lot, space_id, date, partition)
        if key not in self._cache:
            stored = self._spaces.get((lot, space_id))
            if stored is None:
                self._cache[key] = np.array([])
            else:
                dates, partitions, values = stored
                keep = dates != date
                if partition == split.CALIBRATION:
                    keep &= partitions == split.CALIBRATION
                self._cache[key] = values[keep]
        return self._cache[key]
