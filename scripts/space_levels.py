"""Turn each measure into a per-space value, using that space's unlabelled history.

Two variants, so their effect can be separated:

    offset   measure minus the free level of the space
    rescale  measure placed between the free and taken levels of the space

The percentiles that define the levels are chosen on the calibration partition only.
The output has the same layout as measurements.csv, so scripts.evaluate scores it.
The levels and threshold of the rescale variant, the final solution, go to
final_config.json, which scripts.infer reads.

    python -m scripts.space_levels
    python -m scripts.evaluate --measurements results/measurements_e6.csv --output results/evaluation_e6.csv
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import decision, history, split  # noqa: E402

BASE_FIELDS = ["lot", "weather", "date", "frame", "partition",
               "space_id", "area_px", "cx", "cy", "occupied"]
LOW = (5, 10, 20)
HIGH = (80, 90, 95)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="space_levels", description=__doc__)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--history", type=Path, default=ROOT / "results" / "history.csv")
    p.add_argument("--pipeline", default="none+edge_density")
    p.add_argument("--min-spread", type=float, default=0.1)
    p.add_argument("--output", type=Path, default=ROOT / "results" / "measurements_e6.csv")
    p.add_argument("--sweep", type=Path, default=ROOT / "results" / "e6_sweep.csv")
    p.add_argument("--config", type=Path, default=ROOT / "results" / "final_config.json")
    return p


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def transform(rows, past: history.SpaceHistory, name, low, high, min_spread) -> tuple[list, list]:
    """Offset and rescaled value of every row, from the levels of its own space."""
    offsets, rescaled = [], []
    for row in rows:
        values = past.values_for(row["lot"], row["space_id"], row["date"], row["partition"])
        free, taken = history.levels(values, low, high)
        value = float(row[name])
        offsets.append(history.offset(value, free))
        rescaled.append(history.rescale(value, free, taken, min_spread))
    return offsets, rescaled


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.measurements, args.history):
        if not path.is_file():
            print(f"error: not found: {path}", file=sys.stderr)
            return 1

    rows, past_rows = read(args.measurements), read(args.history)
    name = args.pipeline
    if name not in rows[0] or name not in past_rows[0]:
        print(f"error: '{name}' missing from the measurements or the history", file=sys.stderr)
        return 1

    past = history.SpaceHistory(past_rows, name)
    missing = {(r["lot"], r["space_id"]) for r in rows
               if past.values_for(r["lot"], r["space_id"], r["date"], r["partition"]).size == 0}
    if missing:
        print(f"error: {len(missing)} spaces without history, e.g. {sorted(missing)[0]}",
              file=sys.stderr)
        return 1

    calibration = [r for r in rows if r["partition"] == split.CALIBRATION]
    labels = [r["occupied"] == "1" for r in calibration]

    sweep = []
    print(f"{len(calibration)} calibration spaces, {len(past_rows)} history spaces\n")
    for low, high in itertools.product(LOW, HIGH):
        offsets, rescaled = transform(calibration, past, name, low, high, args.min_spread)
        _, offset_score = decision.calibrate(offsets, labels)
        _, rescale_score = decision.calibrate(rescaled, labels)
        sweep.append({"low": low, "high": high, "offset_bacc": round(offset_score, 4),
                      "rescale_bacc": round(rescale_score, 4)})
        print(f"  p{low:<2} p{high}   offset {100 * offset_score:5.1f}   "
              f"rescale {100 * rescale_score:5.1f}")

    best = max(sweep, key=lambda s: (s["rescale_bacc"], -s["low"], s["high"]))
    best_offset = max((s for s in sweep if s["high"] == best["high"]),
                      key=lambda s: (s["offset_bacc"], -s["low"]))
    print(f"\nchosen on calibration: rescale p{best['low']}-p{best['high']}, "
          f"offset p{best_offset['low']}")

    offsets, _ = transform(rows, past, name, best_offset["low"], best["high"], args.min_spread)
    _, rescaled = transform(rows, past, name, best["low"], best["high"], args.min_spread)

    out_names = [name, f"{name}@offset", f"{name}@rescale"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BASE_FIELDS + out_names)
        writer.writeheader()
        for row, off, res in zip(rows, offsets, rescaled):
            writer.writerow({**{k: row[k] for k in BASE_FIELDS}, name: row[name],
                             out_names[1]: round(off, 6), out_names[2]: round(res, 6)})

    with args.sweep.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sweep[0]))
        writer.writeheader()
        writer.writerows(sweep)
    calibration_rescaled = [v for r, v in zip(rows, rescaled)
                            if r["partition"] == split.CALIBRATION]
    threshold, _ = decision.calibrate(calibration_rescaled, labels)
    config = {"pipeline": name, "low": best["low"], "high": best["high"],
              "min_spread": args.min_spread, "threshold": round(threshold, 6)}
    args.config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    print(f"\nmeasurements: {args.output}\nsweep:        {args.sweep}\n"
          f"config:       {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
