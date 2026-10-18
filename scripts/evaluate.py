"""Calibrate each pipeline on the calibration partition and score it on the test one.

The threshold is chosen only from calibration spaces and then applied unchanged to
the test days of the same lot and to the other lots. Results are broken down by lot
and weather, with balanced accuracy, precision, recall, F1, false positives and
negatives, the error in the free-space count per frame, and a confidence interval
obtained by resampling whole dates.

    python -m scripts.evaluate
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import decision, metrics, split  # noqa: E402

BASE_FIELDS = {"lot", "weather", "date", "frame", "partition",
               "space_id", "area_px", "cx", "cy", "occupied"}

OUTPUT_FIELDS = ["pipeline", "threshold", "lot", "weather", "n", "frames",
                 "accuracy", "balanced_accuracy", "bacc_low", "bacc_high",
                 "precision", "recall", "f1", "fp", "fn", "count_mae", "count_bias"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evaluate", description=__doc__)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--pipelines", default="", help="comma separated names, default all")
    p.add_argument("--resamples", type=int, default=1000)
    p.add_argument("--output", type=Path, default=ROOT / "results" / "evaluation.csv")
    return p


def read_measurements(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        names = [f for f in reader.fieldnames if f not in BASE_FIELDS]
    return rows, names


def score_group(rows: list[dict], name: str, threshold: float, resamples: int) -> dict:
    """Every reported figure for one pipeline on one group of spaces."""
    labels = [r["occupied"] == "1" for r in rows]
    predicted = decision.predict([float(r[name]) for r in rows], threshold)

    result = metrics.scores(labels, predicted)
    result.update(metrics.count_error(labels, predicted, [r["frame"] for r in rows]))
    result["bacc_low"], result["bacc_high"] = metrics.bootstrap_ci(
        labels, predicted, [r["date"] for r in rows], resamples=resamples
    )
    return result


def groups(rows: list[dict]):
    """Test spaces of each lot, all weathers together and then one weather at a time."""
    test = [r for r in rows if r["partition"] == split.TEST]
    for lot in split.LOTS:
        in_lot = [r for r in test if r["lot"] == lot]
        if not in_lot:
            continue
        yield lot, "all", in_lot
        for weather in split.WEATHERS:
            subset = [r for r in in_lot if r["weather"] == weather]
            if subset:
                yield lot, weather, subset


def percent(value: float) -> str:
    return "  -  " if math.isnan(value) else f"{100 * value:5.1f}"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.measurements.is_file():
        print(f"error: measurements not found: {args.measurements}; "
              "run scripts.measure first", file=sys.stderr)
        return 1

    rows, available = read_measurements(args.measurements)
    names = [n.strip() for n in args.pipelines.split(",") if n.strip()] or available
    unknown = [n for n in names if n not in available]
    if unknown:
        print(f"error: not in the measurements: {', '.join(unknown)}", file=sys.stderr)
        return 1

    calibration = [r for r in rows if r["partition"] == split.CALIBRATION]
    if not calibration:
        print("error: no calibration spaces in the measurements", file=sys.stderr)
        return 1

    table = []
    for name in names:
        threshold, fitted = decision.calibrate(
            [float(r[name]) for r in calibration],
            [r["occupied"] == "1" for r in calibration],
        )
        print(f"\n=== {name} ===")
        print(f"threshold {threshold:.5f}, balanced accuracy on its own calibration "
              f"spaces {percent(fitted)}% (n={len(calibration)}, not a test result)")
        print(f"{'lot':<7} {'weather':<7} {'n':>5}  {'bacc':>5} {'95% CI':>13}  "
              f"{'acc':>5} {'prec':>5} {'rec':>5} {'f1':>5}  {'FP':>4} {'FN':>4}  "
              f"{'count MAE':>9}")

        for lot, weather, subset in groups(rows):
            result = score_group(subset, name, threshold, args.resamples)
            interval = f"[{percent(result['bacc_low'])},{percent(result['bacc_high'])}]"
            print(f"{lot:<7} {weather:<7} {result['n']:>5}  "
                  f"{percent(result['balanced_accuracy'])} {interval:>13}  "
                  f"{percent(result['accuracy'])} {percent(result['precision'])} "
                  f"{percent(result['recall'])} {percent(result['f1'])}  "
                  f"{result['fp']:>4} {result['fn']:>4}  {result['count_mae']:>9.2f}")
            table.append({"pipeline": name, "threshold": round(threshold, 6),
                          "lot": lot, "weather": weather,
                          **{k: (round(v, 4) if isinstance(v, float) else v)
                             for k, v in result.items()}})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(table)
    print(f"\nevaluation: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
