"""Figures of E3: what a normalization does to the patch and to the measure.

One figure shows real spaces before and after the normalization with their edge
maps, picking spaces the normalization recovered and spaces it broke. The other
plots the paired difference against the baseline, with its interval, for every lot
and weather.

    python -m scripts.e3_figures --data ../PKLot/PKLot
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
from parking import normalization as norm  # noqa: E402
from parking import split  # noqa: E402

NORMALIZERS = {"clahe": norm.clahe, "stretch": norm.stretch}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e3_figures", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--normalization", default="clahe", choices=list(NORMALIZERS))
    p.add_argument("--baseline", default="none+edge_density")
    p.add_argument("--examples", type=int, default=3, help="spaces per case")
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--evaluation", type=Path, default=ROOT / "results" / "evaluation.csv")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    return p


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def thresholds(evaluation: list[dict]) -> dict[str, float]:
    return {r["pipeline"]: float(r["threshold"]) for r in evaluation}


def pick(rows, lot, weather, occupied, base, new, t_base, t_new, recovered, count):
    """Test spaces where the new pipeline changes the decision.

    With `recovered`, spaces the baseline got wrong and the new pipeline got right;
    otherwise the reverse. Spread over the sorted list so they come from many frames.
    """
    def correct(value, threshold):
        return (value > threshold) == bool(occupied)

    chosen = [
        r for r in rows
        if r["partition"] == split.TEST and r["lot"] == lot and r["weather"] == weather
        and int(r["occupied"]) == occupied
        and correct(float(r[new]), t_new) == recovered
        and correct(float(r[base]), t_base) != recovered
    ]
    chosen.sort(key=lambda r: (r["frame"], int(r["space_id"])))
    step = max(1, len(chosen) // count)
    return chosen[::step][:count], len(chosen)


def load_patch(data: Path, row: dict) -> np.ndarray:
    """Grayscale patch of one space, cropped exactly as the measurement does."""
    frame = data / row["frame"]
    image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
    space = next(s for s in ann.read_annotation(ann.annotation_for(frame)).labeled
                 if s.id == row["space_id"])
    return feat.to_gray(ext.crop_space(image, space.contour))


def edge_map(gray: np.ndarray) -> np.ndarray:
    return feat.gradient_magnitude(gray) > 60


def examples_figure(data, cases, name, normalize, t_base, t_new, destination: Path):
    rows = [(title, r) for title, picked in cases for r in picked]
    figure, axes = plt.subplots(len(rows), 4, figsize=(7.2, 2.1 * len(rows)))
    axes = np.atleast_2d(axes)
    headers = ["recorte", "bordas (>60)", f"recorte, {name}", f"bordas, {name}"]

    for i, (title, row) in enumerate(rows):
        gray = load_patch(data, row)
        normalized = normalize(gray)
        raw_d, new_d = feat.edge_density(gray), feat.edge_density(normalized)
        panels = [
            (gray, f"{raw_d:.3f} vs lim {t_base:.3f}"),
            (edge_map(gray), ""),
            (normalized, f"{new_d:.3f} vs lim {t_new:.3f}"),
            (edge_map(normalized), ""),
        ]
        for j, (img, caption) in enumerate(panels):
            ax = axes[i, j]
            ax.imshow(img, cmap="gray", vmin=0, vmax=255 if img.dtype != bool else 1)
            ax.set_xticks([]), ax.set_yticks([])
            if i == 0:
                ax.set_title(headers[j], fontsize=8)
            if caption:
                ax.set_xlabel(caption, fontsize=7)
        axes[i, 0].set_ylabel(title, fontsize=7)

    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def difference_figure(evaluation, pipelines, destination: Path):
    labels = [f"{lot}\n{w}" for lot in split.LOTS for w in ("all",) + split.WEATHERS]
    figure, ax = plt.subplots(figsize=(11, 3.6))
    width = 0.8 / max(1, len(pipelines))

    for k, name in enumerate(pipelines):
        by_key = {(r["lot"], r["weather"]): r for r in evaluation if r["pipeline"] == name}
        x, y, low, high = [], [], [], []
        for i, (lot, weather) in enumerate(
            (lot, w) for lot in split.LOTS for w in ("all",) + split.WEATHERS
        ):
            r = by_key.get((lot, weather))
            if r is None or not r["bacc_delta"]:
                continue
            d = 100 * float(r["bacc_delta"])
            x.append(i + (k - (len(pipelines) - 1) / 2) * width)
            y.append(d)
            low.append(d - 100 * float(r["delta_low"]))
            high.append(100 * float(r["delta_high"]) - d)
        ax.bar(x, y, width=width, label=name, yerr=[low, high], capsize=2)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("diferença de acurácia\nbalanceada (pontos)")
    ax.set_title("Diferença pareada contra o baseline, com intervalo de 95% (bootstrap por data)",
                 fontsize=10)
    ax.legend(fontsize=8)
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
    evaluation = read_csv(args.evaluation)
    limits = thresholds(evaluation)
    new = f"{args.normalization}+edge_density"
    if new not in limits or args.baseline not in limits:
        print(f"error: {new} or {args.baseline} not in {args.evaluation}", file=sys.stderr)
        return 1

    t_base, t_new = limits[args.baseline], limits[new]
    recovered, n_rec = pick(rows, "UFPR05", "Rainy", 1, args.baseline, new,
                            t_base, t_new, True, args.examples)
    broken, n_brk = pick(rows, "UFPR05", "Sunny", 0, args.baseline, new,
                         t_base, t_new, False, args.examples)
    print(f"UFPR05 Rainy, occupied, recovered by {args.normalization}: {n_rec} spaces")
    print(f"UFPR05 Sunny, free, broken by {args.normalization}:     {n_brk} spaces")

    examples = args.output / f"e3_{args.normalization}_examples.png"
    examples_figure(
        args.data,
        [("UFPR05 chuva\nocupada, recuperada", recovered),
         ("UFPR05 sol\nlivre, virou FP", broken)],
        args.normalization, NORMALIZERS[args.normalization], t_base, t_new, examples,
    )

    pipelines = [p for p in dict.fromkeys(r["pipeline"] for r in evaluation)
                 if p != args.baseline]
    differences = args.output / "e3_paired_difference.png"
    difference_figure(evaluation, pipelines, differences)

    print(f"\nexamples:    {examples}")
    print(f"differences: {differences}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
