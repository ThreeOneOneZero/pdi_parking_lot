"""E2 - can a single pixel measurement tell an occupied space from a free one?

For every sampled space we compute two numbers from the patch alone: edge density
(Sobel) and mean intensity. Occupancy labels are read only afterwards, to group the
measurements and to score a decision the labels never took part in.

A threshold is then calibrated on one lot and applied unchanged to the others, which
is the generalisation question the project asks.

    python -m scripts.e2_edge_density --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import extraction as ext  # noqa: E402
from parking import features as feat  # noqa: E402

WEATHERS = ("Sunny", "Cloudy", "Rainy")
LOTS = ("UFPR04", "UFPR05", "PUCPR")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e2_edge_density", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--calibrate-on", default="UFPR04", help="lot used to pick the threshold")
    p.add_argument("--frames-per-weather", type=int, default=6)
    p.add_argument("--patch-size", type=lambda s: tuple(int(v) for v in s.split("x")),
                   default=ext.DEFAULT_SIZE, metavar="WxH")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    p.add_argument("--results", type=Path, default=ROOT / "results")
    return p


def measure(data: Path, lot: str, frames_per_weather: int, size) -> list[dict]:
    """Measure every labelled space in a sample of frames. Labels are stored, not used."""
    rows = []
    for weather in WEATHERS:
        frames = ann.list_frames(data, lot, weather)
        if not frames:
            continue
        step = max(1, len(frames) // frames_per_weather)
        for frame in frames[::step][:frames_per_weather]:
            image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
            if image is None:
                continue
            annotation = ann.read_annotation(ann.annotation_for(frame))
            for space in annotation.labeled:
                patch = ext.crop_space(image, space.contour, size)
                rows.append({
                    "lot": lot,
                    "weather": weather,
                    "frame": frame.stem,
                    "space_id": space.id,
                    "edge_density": round(feat.edge_density(patch), 5),
                    "mean_intensity": round(feat.mean_intensity(patch), 2),
                    "occupied": int(space.occupied),
                })
    return rows


def calibrate(rows: list[dict], key: str) -> tuple[float, float]:
    """Pick the threshold that best splits the two classes. Returns (threshold, accuracy)."""
    values = np.array([r[key] for r in rows])
    labels = np.array([r["occupied"] for r in rows], dtype=bool)

    candidates = np.unique(values)
    midpoints = (candidates[:-1] + candidates[1:]) / 2
    if midpoints.size == 0:
        return float(values[0]), 0.0

    accuracies = [((values > t) == labels).mean() for t in midpoints]
    best = int(np.argmax(accuracies))
    return float(midpoints[best]), float(accuracies[best])


def score(rows: list[dict], key: str, threshold: float) -> tuple[float, int, int]:
    """Accuracy of `value > threshold`, plus false positive and false negative counts."""
    values = np.array([r[key] for r in rows])
    labels = np.array([r["occupied"] for r in rows], dtype=bool)
    predicted = values > threshold

    false_positive = int((predicted & ~labels).sum())   # said occupied, was free
    false_negative = int((~predicted & labels).sum())   # said free, was occupied
    return float((predicted == labels).mean()), false_positive, false_negative


def plot_histograms(rows, key, threshold, destination: Path, lot: str):
    figure, axes = plt.subplots(1, len(WEATHERS), figsize=(13, 3.4), sharex=True, sharey=True)

    for ax, weather in zip(axes, WEATHERS):
        subset = [r for r in rows if r["weather"] == weather]
        if not subset:
            ax.set_title(f"{weather} (no data)")
            continue
        occupied = [r[key] for r in subset if r["occupied"]]
        free = [r[key] for r in subset if not r["occupied"]]

        bins = np.linspace(0, max(r[key] for r in rows), 40)
        ax.hist(free, bins=bins, alpha=0.6, label="free", color="tab:green")
        ax.hist(occupied, bins=bins, alpha=0.6, label="occupied", color="tab:red")
        ax.axvline(threshold, color="black", linestyle="--", linewidth=1)
        ax.set_title(f"{weather}  (n={len(subset)})", fontsize=10)
        ax.set_xlabel(key)

    axes[0].set_ylabel("spaces")
    axes[0].legend(fontsize=8)
    figure.suptitle(f"{lot} - {key} by class, dashed line = calibrated threshold", fontsize=11)
    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not args.data.is_dir():
        print(f"error: data directory not found: {args.data}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)

    by_lot = {}
    for lot in LOTS:
        rows = measure(args.data, lot, args.frames_per_weather, args.patch_size)
        if rows:
            by_lot[lot] = rows
            print(f"{lot}: {len(rows)} spaces measured")

    if args.calibrate_on not in by_lot:
        print(f"error: no data for calibration lot {args.calibrate_on}", file=sys.stderr)
        return 1

    print()
    for key in ("edge_density", "mean_intensity"):
        threshold, accuracy = calibrate(by_lot[args.calibrate_on], key)
        print(f"--- {key} ---")
        print(f"threshold calibrated on {args.calibrate_on}: {threshold:.5f} "
              f"({accuracy:.1%} on the calibration lot itself)")

        for lot, rows in by_lot.items():
            marker = "  <- calibration lot" if lot == args.calibrate_on else ""
            total, fp, fn = score(rows, key, threshold)
            print(f"  {lot:<7} {total:6.1%}   false occupied={fp:<4} false free={fn:<4}{marker}")
            for weather in WEATHERS:
                subset = [r for r in rows if r["weather"] == weather]
                if subset:
                    acc, _, _ = score(subset, key, threshold)
                    print(f"      {weather:<7} {acc:6.1%}  (n={len(subset)})")
        print()

        if key == "edge_density":
            for lot, rows in by_lot.items():
                plot_histograms(rows, key, threshold,
                                args.output / f"e2_{key}_{lot}.png", lot)

    measurements = args.results / "e2_measurements.csv"
    with measurements.open("w", newline="", encoding="utf-8") as handle:
        fields = ["lot", "weather", "frame", "space_id",
                  "edge_density", "mean_intensity", "occupied"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rows in by_lot.values():
            writer.writerows(rows)

    print(f"measurements: {measurements}")
    print(f"histograms:   {args.output}/e2_edge_density_*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
