"""Figures of E4: every stage of the region measure, and how both measures shift by lot.

The stages figure follows real spaces through edges, closing, opening and the largest
region, in cases the measure gets right and cases it gets wrong. The histogram figure
puts the calibration lot next to UFPR05 for edge density and region fraction, with
the calibrated threshold.

    python -m scripts.e4_figures --data ../PKLot/PKLot
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
from parking import features, normalization, regions, split  # noqa: E402

# Normalization and morphology sizes of each region pipeline, as in pipelines.py.
REGION_SETUP = {
    "none+region_fraction": (lambda g: g, 5, 3),
    "clahe+region_fraction": (normalization.clahe, 3, 3),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e4_figures", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--evaluation", type=Path, default=ROOT / "results" / "evaluation.csv")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    return p


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def first_match(rows, lot, weather, occupied, pipeline, threshold, correct):
    """First test space, in sorted order, where `pipeline` is right or wrong as asked."""
    candidates = sorted(
        (r for r in rows
         if r["partition"] == split.TEST and r["lot"] == lot
         and (weather is None or r["weather"] == weather)
         and int(r["occupied"]) == occupied
         and ((float(r[pipeline]) > threshold) == bool(occupied)) == correct),
        key=lambda r: (r["frame"], int(r["space_id"])),
    )
    return candidates[len(candidates) // 2] if candidates else None


def load_gray(data: Path, row: dict) -> np.ndarray:
    frame = data / row["frame"]
    image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
    space = next(s for s in ann.read_annotation(ann.annotation_for(frame)).labeled
                 if s.id == row["space_id"])
    return features.to_gray(ext.crop_space(image, space.contour))


def stages_figure(data, cases, limits, destination: Path):
    headers = ["recorte", "bordas (>60)", "fechamento", "abertura", "maior região"]
    figure, axes = plt.subplots(len(cases), 5, figsize=(8.4, 2.2 * len(cases)))
    axes = np.atleast_2d(axes)

    for i, (title, pipeline, row) in enumerate(cases):
        normalize, close, opening = REGION_SETUP[pipeline]
        gray = normalize(load_gray(data, row))
        steps = regions.stages(gray, close, opening)
        d = regions.describe(steps["region"])
        panels = [gray, steps["edges"], steps["closed"], steps["opened"], steps["region"]]
        for j, img in enumerate(panels):
            ax = axes[i, j]
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)
            ax.set_xticks([]), ax.set_yticks([])
            if i == 0:
                ax.set_title(headers[j], fontsize=8)
        axes[i, 0].set_ylabel(title, fontsize=7)
        axes[i, 4].set_xlabel(
            f"área {d['area_fraction']:.2f} (lim {limits[pipeline]:.2f})\n"
            f"extensão {d['extent']:.2f}  solidez {d['solidity']:.2f}", fontsize=6.5)

    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def histogram_figure(rows, limits, destination: Path):
    measures = [("none+edge_density", "densidade de bordas"),
                ("none+region_fraction", "fração da maior região")]
    groups = [("UFPR04", split.CALIBRATION, "UFPR04, calibração"),
              ("UFPR05", split.TEST, "UFPR05, teste")]
    figure, axes = plt.subplots(len(measures), len(groups), figsize=(9, 5.4), sharex="row")

    for i, (pipeline, label) in enumerate(measures):
        bins = np.linspace(0, 1, 41)
        for j, (lot, partition, title) in enumerate(groups):
            subset = [r for r in rows if r["lot"] == lot and r["partition"] == partition]
            free = [float(r[pipeline]) for r in subset if r["occupied"] == "0"]
            occupied = [float(r[pipeline]) for r in subset if r["occupied"] == "1"]
            ax = axes[i, j]
            ax.hist(free, bins=bins, alpha=0.6, color="tab:green", label="livre")
            ax.hist(occupied, bins=bins, alpha=0.6, color="tab:red", label="ocupada")
            ax.axvline(limits[pipeline], color="black", linestyle="--", linewidth=1)
            ax.set_title(f"{title}: {label}", fontsize=9)
            ax.text(0.98, 0.95, f"mediana ocupada {np.median(occupied):.2f}",
                    transform=ax.transAxes, ha="right", va="top", fontsize=7)
        axes[i, 0].set_ylabel("vagas")
    axes[0, 0].legend(fontsize=7)
    figure.suptitle("Linha tracejada: limiar calibrado no UFPR04", fontsize=10)
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.measurements, args.evaluation):
        if not path.is_file():
            print(f"error: {path} not found; run scripts.measure and scripts.evaluate",
                  file=sys.stderr)
            return 1

    rows = read_csv(args.measurements)
    limits = {r["pipeline"]: float(r["threshold"]) for r in read_csv(args.evaluation)}
    needed = ["none+edge_density", *REGION_SETUP]
    missing = [p for p in needed if p not in limits]
    if missing:
        print(f"error: missing in evaluation: {', '.join(missing)}", file=sys.stderr)
        return 1

    plain, clahe = "none+region_fraction", "clahe+region_fraction"
    wanted = [
        ("acerto\nocupada, UFPR04", plain, ("UFPR04", None, 1, plain, True)),
        ("acerto\nlivre, UFPR04", plain, ("UFPR04", None, 0, plain, True)),
        ("erro: FN\nocupada, UFPR05 chuva", plain, ("UFPR05", "Rainy", 1, plain, False)),
        ("erro: FP com CLAHE\nlivre, UFPR05 sol", clahe, ("UFPR05", "Sunny", 0, clahe, False)),
    ]
    cases = []
    for title, pipeline, (lot, weather, occupied, measure, correct) in wanted:
        row = first_match(rows, lot, weather, occupied, measure, limits[measure], correct)
        if row is not None:
            cases.append((title, pipeline, row))

    stages = args.output / "e4_region_stages.png"
    stages_figure(args.data, cases, limits, stages)
    histograms = args.output / "e4_histograms.png"
    histogram_figure(rows, limits, histograms)

    print(f"stages:     {stages}")
    print(f"histograms: {histograms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
