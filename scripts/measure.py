"""Measure every labelled space of the frozen split with every selected pipeline.

This is the slow part, since it reads each frame from disk, so it runs once and
writes a table that the evaluation reads as many times as needed. Occupancy labels
are copied to the table but never passed to a pipeline.

    python -m scripts.measure --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import extraction as ext  # noqa: E402
from parking import pipelines, split  # noqa: E402

BASE_FIELDS = ["lot", "weather", "date", "frame", "partition",
               "space_id", "area_px", "cx", "cy", "occupied"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="measure", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--split", type=Path, default=ROOT / "results" / "split.csv")
    p.add_argument("--pipelines", default="", help="comma separated names, default all")
    p.add_argument("--patch-size", type=lambda s: tuple(int(v) for v in s.split("x")),
                   default=ext.DEFAULT_SIZE, metavar="WxH")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--timing", type=Path, default=ROOT / "results" / "timing.csv")
    return p


def measure_frame(data: Path, entry: dict, chosen: dict, size, elapsed: dict) -> list[dict]:
    """One row per labelled space of a frame, with every pipeline's value.

    `elapsed` accumulates the seconds spent inside each pipeline, the cost the
    comparison reports; reading and cropping are common to all and left out.
    """
    frame = data / entry["frame"]
    image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
    if image is None:
        raise OSError(f"could not read {frame}")

    rows = []
    for space in ann.read_annotation(ann.annotation_for(frame)).labeled:
        patch = ext.crop_space(image, space.contour, size)
        centre = space.contour.mean(axis=0)
        row = {
            **{k: entry[k] for k in ("lot", "weather", "date", "frame", "partition")},
            "space_id": space.id,
            "area_px": round(ext.contour_area(space.contour), 1),
            "cx": round(float(centre[0]), 1),
            "cy": round(float(centre[1]), 1),
            "occupied": int(space.occupied),
        }
        for name, run in chosen.items():
            start = time.perf_counter()
            row[name] = round(run(patch), 6)
            elapsed[name] = elapsed.get(name, 0.0) + time.perf_counter() - start
        rows.append(row)
    return rows


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.data.is_dir():
        print(f"error: data directory not found: {args.data}", file=sys.stderr)
        return 1
    if not args.split.is_file():
        print(f"error: split not found: {args.split}; run scripts.make_split first",
              file=sys.stderr)
        return 1
    try:
        chosen = pipelines.select(args.pipelines)
    except KeyError as err:
        print(f"error: {err.args[0]}", file=sys.stderr)
        return 1

    entries = split.read_split(args.split)
    elapsed: dict[str, float] = {}
    rows = []
    for number, entry in enumerate(entries, start=1):
        rows.extend(measure_frame(args.data, entry, chosen, args.patch_size, elapsed))
        if number % 50 == 0 or number == len(entries):
            print(f"{number}/{len(entries)} frames, {len(rows)} spaces")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BASE_FIELDS + list(chosen))
        writer.writeheader()
        writer.writerows(rows)

    with args.timing.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["pipeline", "patches", "total_s", "ms_per_patch"])
        for name in chosen:
            total = elapsed.get(name, 0.0)
            writer.writerow([name, len(rows), round(total, 3),
                             round(1000 * total / len(rows), 4) if rows else ""])

    print(f"\nmeasurements: {args.output}")
    print(f"timing:       {args.timing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
