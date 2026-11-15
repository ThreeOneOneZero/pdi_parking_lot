"""Measure the spaces of unlabelled frames outside the split, the history of each space.

These frames are never scored and their occupancy labels are not copied: only the
space polygons are read from the XML. The table feeds the per-space levels of M3.

    python -m scripts.measure_history --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import extraction as ext  # noqa: E402
from parking import history, pipelines, split  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="measure_history", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--split", type=Path, default=ROOT / "results" / "split.csv")
    p.add_argument("--calibrate-on", default="UFPR04")
    p.add_argument("--per-weather", type=int, default=100,
                   help="history frames per lot and weather")
    p.add_argument("--pipelines", default="none+edge_density")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "history.csv")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.data.is_dir():
        print(f"error: data directory not found: {args.data}", file=sys.stderr)
        return 1
    if not args.split.is_file():
        print(f"error: split not found: {args.split}", file=sys.stderr)
        return 1
    try:
        chosen = pipelines.select(args.pipelines)
    except KeyError as err:
        print(f"error: {err.args[0]}", file=sys.stderr)
        return 1

    entries = history.history_frames(args.data, split.read_split(args.split),
                                     args.calibrate_on, args.per_weather)
    rows = []
    for number, entry in enumerate(entries, start=1):
        frame = args.data / entry["frame"]
        image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
        if image is None:
            print(f"error: could not read {frame}", file=sys.stderr)
            return 1
        for space in ann.read_annotation(ann.annotation_for(frame)).spaces:
            patch = ext.crop_space(image, space.contour)
            rows.append({**entry, "space_id": space.id,
                         **{name: round(run(patch), 6) for name, run in chosen.items()}})
        if number % 100 == 0 or number == len(entries):
            print(f"{number}/{len(entries)} frames, {len(rows)} spaces")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=history.FIELDS + list(chosen))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nhistory: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
