"""Create the frozen split once, before any comparison.

Dates of the calibration lot alternate between calibration and test; the other lots
are test only. The file is meant to be committed and never regenerated, so the
script refuses to overwrite it without --force.

    python -m scripts.make_split --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import split  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="make_split", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--calibrate-on", default="UFPR04")
    p.add_argument("--frames-per-cell", type=int, default=20,
                   help="frames per lot, weather and partition")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "split.csv")
    p.add_argument("--force", action="store_true", help="overwrite an existing split")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.data.is_dir():
        print(f"error: data directory not found: {args.data}", file=sys.stderr)
        return 1
    if args.output.exists() and not args.force:
        print(f"error: {args.output} already exists; the split is frozen. "
              "Use --force only if you mean to discard it.", file=sys.stderr)
        return 1

    rows = split.build_split(args.data, args.calibrate_on, args.frames_per_cell)
    try:
        split.check_split(rows, args.calibrate_on)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    split.write_split(args.output, rows)

    frames = Counter((r["lot"], r["weather"], r["partition"]) for r in rows)
    dates = {}
    for r in rows:
        dates.setdefault((r["lot"], r["partition"]), set()).add(r["date"])

    for lot in split.LOTS:
        for partition in (split.CALIBRATION, split.TEST):
            if (lot, partition) not in dates:
                continue
            cells = "  ".join(
                f"{w} {frames[(lot, w, partition)]:>3}" for w in split.WEATHERS
            )
            print(f"{lot:<7} {partition:<11} {len(dates[(lot, partition)]):>2} dates   {cells}")
    print(f"\nsplit: {args.output} ({len(rows)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
