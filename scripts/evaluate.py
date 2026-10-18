"""Calibrate each pipeline on the calibration partition and score it on the test one.

The threshold is chosen only from calibration spaces and then applied unchanged to
the test days of the same lot and to the other lots. Results are broken down by lot
and weather, with balanced accuracy, precision, recall, F1, false positives and
negatives, the error in the free-space count per frame, and a confidence interval
obtained by resampling whole dates. Every pipeline is also compared with a baseline
on the same resampled dates.

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
                 "precision", "recall", "f1", "fp", "fn", "count_mae", "count_bias",
                 "bacc_delta", "delta_low", "delta_high"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evaluate", description=__doc__)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--pipelines", default="", help="comma separated names, default all")
    p.add_argument("--baseline", default="none+edge_density",
                   help="pipeline the others are compared with")
    p.add_argument("--resamples", type=int, default=1000)
    p.add_argument("--output", type=Path, default=ROOT / "results" / "evaluation.csv")
    return p


def read_measurements(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        names = [f for f in reader.fieldnames if f not in BASE_FIELDS]
    return rows, names


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


def score_group(rows, name, threshold, baseline_prediction, resamples) -> tuple[dict, list]:
    """Every reported figure for one pipeline on one group, and its predictions."""
    labels = [r["occupied"] == "1" for r in rows]
    dates = [r["date"] for r in rows]
    predicted = decision.predict([float(r[name]) for r in rows], threshold)

    result = metrics.scores(labels, predicted)
    result.update(metrics.count_error(labels, predicted, [r["frame"] for r in rows]))
    result["bacc_low"], result["bacc_high"] = metrics.bootstrap_ci(
        labels, predicted, dates, resamples=resamples
    )
    if baseline_prediction is not None:
        result["bacc_delta"], result["delta_low"], result["delta_high"] = (
            metrics.paired_difference(labels, baseline_prediction, predicted, dates,
                                      resamples=resamples)
        )
    return result, predicted


def percent(value: float) -> str:
    return "  -  " if value is None or math.isnan(value) else f"{100 * value:5.1f}"


def signed(value: float) -> str:
    return "   -  " if value is None or math.isnan(value) else f"{100 * value:+5.1f}"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.measurements.is_file():
        print(f"error: measurements not found: {args.measurements}; "
              "run scripts.measure first", file=sys.stderr)
        return 1

    rows, available = read_measurements(args.measurements)
    names = [n.strip() for n in args.pipelines.split(",") if n.strip()] or available
    unknown = [n for n in names + [args.baseline] if n not in available]
    if unknown:
        print(f"error: not in the measurements: {', '.join(unknown)}", file=sys.stderr)
        return 1
    names = [args.baseline] + [n for n in names if n != args.baseline]

    calibration = [r for r in rows if r["partition"] == split.CALIBRATION]
    if not calibration:
        print("error: no calibration spaces in the measurements", file=sys.stderr)
        return 1

    thresholds = {}
    for name in names:
        thresholds[name] = decision.calibrate(
            [float(r[name]) for r in calibration],
            [r["occupied"] == "1" for r in calibration],
        )

    baseline_predictions = {}
    table = []
    for name in names:
        threshold, fitted = thresholds[name]
        is_baseline = name == args.baseline
        print(f"\n=== {name}{'  (baseline)' if is_baseline else ''} ===")
        print(f"threshold {threshold:.5f}, balanced accuracy on its own calibration "
              f"spaces {percent(fitted)}% (n={len(calibration)}, not a test result)")
        print(f"{'lot':<7} {'weather':<7} {'n':>5}  {'bacc':>5} {'95% CI':>13}  "
              f"{'acc':>5} {'prec':>5} {'rec':>5} {'f1':>5}  {'FP':>4} {'FN':>4}  "
              f"{'cnt MAE':>7}  {'vs base':>7} {'95% CI':>15}")

        for lot, weather, subset in groups(rows):
            key = (lot, weather)
            base = None if is_baseline else baseline_predictions[key]
            result, predicted = score_group(subset, name, threshold, base, args.resamples)
            if is_baseline:
                baseline_predictions[key] = predicted

            interval = f"[{percent(result['bacc_low'])},{percent(result['bacc_high'])}]"
            delta = result.get("bacc_delta")
            delta_ci = ("" if is_baseline else
                        f"[{signed(result['delta_low'])},{signed(result['delta_high'])}]")
            print(f"{lot:<7} {weather:<7} {result['n']:>5}  "
                  f"{percent(result['balanced_accuracy'])} {interval:>13}  "
                  f"{percent(result['accuracy'])} {percent(result['precision'])} "
                  f"{percent(result['recall'])} {percent(result['f1'])}  "
                  f"{result['fp']:>4} {result['fn']:>4}  {result['count_mae']:>7.2f}  "
                  f"{signed(delta) if not is_baseline else '':>7} {delta_ci:>15}")
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
