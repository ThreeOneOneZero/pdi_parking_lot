"""Frozen experimental split: which frames calibrate the threshold and which evaluate it.

Frames are grouped by date, not by weather folder, because one date often appears
under two weathers. Splitting by folder would put the morning of a day in calibration
and its afternoon in test, two nearly identical views of the same lot.
"""

from __future__ import annotations

import csv
from pathlib import Path

from . import annotations as ann

WEATHERS = ("Sunny", "Cloudy", "Rainy")
LOTS = ("UFPR04", "UFPR05", "PUCPR")

CALIBRATION = "calibration"
TEST = "test"

FIELDS = ["lot", "weather", "date", "frame", "partition"]


def frame_date(frame: Path) -> str:
    """Date of a frame, taken from its folder: <lot>/<weather>/<date>/<frame>.jpg."""
    return frame.parent.name


def assign_dates(dates: list[str]) -> dict[str, str]:
    """Alternate sorted dates between calibration and test, so both cover the whole period."""
    return {
        date: CALIBRATION if index % 2 == 0 else TEST
        for index, date in enumerate(sorted(set(dates)))
    }


def sample_evenly(frames: list[Path], count: int) -> list[Path]:
    """Take `count` frames spread over the sorted list, so they span many dates and hours."""
    if count <= 0 or not frames:
        return []
    step = max(1, len(frames) // count)
    return frames[::step][:count]


def build_split(data: Path, calibrate_on: str, frames_per_cell: int) -> list[dict]:
    """Choose the frames of every lot, weather and partition.

    Only `calibrate_on` gets a calibration partition; the other lots are test only,
    which is the different-lot scenario of the proposal.
    """
    rows = []
    for lot in LOTS:
        frames = ann.list_frames(data, lot)
        if not frames:
            continue

        if lot == calibrate_on:
            partition_of = assign_dates([frame_date(f) for f in frames])
        else:
            partition_of = {frame_date(f): TEST for f in frames}

        for weather in WEATHERS:
            in_weather = [f for f in frames if f.parent.parent.name == weather]
            for partition in sorted(set(partition_of.values())):
                cell = [f for f in in_weather if partition_of[frame_date(f)] == partition]
                for frame in sample_evenly(cell, frames_per_cell):
                    rows.append(
                        {
                            "lot": lot,
                            "weather": weather,
                            "date": frame_date(frame),
                            "frame": frame.relative_to(data).as_posix(),
                            "partition": partition,
                        }
                    )
    return rows


def check_split(rows: list[dict], calibrate_on: str) -> None:
    """Refuse a split where a date crosses partitions or a weather lacks calibration frames."""
    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["lot"], row["date"])
        if seen.setdefault(key, row["partition"]) != row["partition"]:
            raise ValueError(f"date {row['date']} of {row['lot']} is in both partitions")

    for weather in WEATHERS:
        for partition in (CALIBRATION, TEST):
            if not any(
                r["lot"] == calibrate_on and r["weather"] == weather and r["partition"] == partition
                for r in rows
            ):
                raise ValueError(f"{calibrate_on} {weather} has no {partition} frames")


def write_split(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_split(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
