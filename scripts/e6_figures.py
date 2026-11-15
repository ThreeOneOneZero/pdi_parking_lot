"""Figures of E6: the per-space levels against the single threshold of the baseline.

One figure compares the balanced accuracy of the baseline, the offset and the rescale
variants on every lot. One repeats the E4 histograms with the rescaled measure. The
last shows the final output on two frames, with the wrong spaces marked.

    python -m scripts.e6_figures --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
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
from parking import history, inference, split  # noqa: E402

BASE = "none+edge_density"
VARIANTS = [(BASE, "baseline (M2)", "tab:gray"),
            (f"{BASE}@offset", "nível livre da vaga", "tab:blue"),
            (f"{BASE}@rescale", "livre e ocupado da vaga (final)", "tab:green")]
EXAMPLES = [("UFPR05/Sunny/2013-04-10/2013-04-10_08_25_02.jpg", "erro mediano do UFPR05"),
            ("PUCPR/Sunny/2012-09-19/2012-09-19_16_08_43.jpg", "um dos piores quadros do PUCPR")]
WEATHER = {"Sunny": "sol", "Cloudy": "nublado", "Rainy": "chuva"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e6_figures", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements_e6.csv")
    p.add_argument("--evaluation", type=Path, default=ROOT / "results" / "evaluation_e6.csv")
    p.add_argument("--history", type=Path, default=ROOT / "results" / "history.csv")
    p.add_argument("--config", type=Path, default=ROOT / "results" / "final_config.json")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    return p


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def comparison_figure(evaluation, destination: Path):
    rows = {(r["pipeline"], r["lot"]): r for r in evaluation if r["weather"] == "all"}
    lots = [lot for lot in split.LOTS if (BASE, lot) in rows]
    figure, ax = plt.subplots(figsize=(8, 3.6))
    width = 0.27
    for i, (name, label, colour) in enumerate(VARIANTS):
        x = np.arange(len(lots)) + (i - 1) * width
        y = [100 * float(rows[(name, lot)]["balanced_accuracy"]) for lot in lots]
        low = [100 * float(rows[(name, lot)]["bacc_low"]) for lot in lots]
        high = [100 * float(rows[(name, lot)]["bacc_high"]) for lot in lots]
        ax.bar(x, y, width, color=colour, label=label,
               yerr=[np.subtract(y, low), np.subtract(high, y)], capsize=3)
    ax.set_xticks(np.arange(len(lots)), [f"{lot} (teste)" for lot in lots])
    ax.set_ylim(70, 100)
    ax.set_ylabel("acurácia balanceada (%)")
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title("Mesmo quadro de teste, mesma medida; muda só a referência do limiar",
                 fontsize=10)
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def histogram_figure(rows, limits, destination: Path):
    measures = [(BASE, "densidade de bordas", np.linspace(0, 1, 41)),
                (f"{BASE}@rescale", "entre livre e ocupado da vaga", np.linspace(-1, 2.5, 41))]
    groups = [("UFPR04", split.CALIBRATION, "UFPR04, calibração"),
              ("UFPR05", split.TEST, "UFPR05, teste")]
    figure, axes = plt.subplots(len(measures), len(groups), figsize=(9, 5.4), sharex="row")
    for i, (name, label, bins) in enumerate(measures):
        for j, (lot, partition, title) in enumerate(groups):
            subset = [r for r in rows if r["lot"] == lot and r["partition"] == partition]
            free = [float(r[name]) for r in subset if r["occupied"] == "0"]
            occupied = [float(r[name]) for r in subset if r["occupied"] == "1"]
            ax = axes[i, j]
            ax.hist(np.clip(free, bins[0], bins[-1]), bins=bins, alpha=0.6,
                    color="tab:green", label="livre")
            ax.hist(np.clip(occupied, bins[0], bins[-1]), bins=bins, alpha=0.6,
                    color="tab:red", label="ocupada")
            ax.axvline(limits[name], color="black", linestyle="--", linewidth=1)
            ax.set_title(f"{title}: {label}", fontsize=9)
            ax.text(0.98, 0.95, f"mediana ocupada {np.median(occupied):.2f}",
                    transform=ax.transAxes, ha="right", va="top", fontsize=7)
        axes[i, 0].set_ylabel("vagas")
    axes[0, 0].legend(fontsize=7)
    figure.suptitle("Linha tracejada: limiar calibrado no UFPR04", fontsize=10)
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def output_figure(data: Path, past, config, destination: Path):
    """Final output on example frames; wrong spaces get a thick yellow outline."""
    figure, axes = plt.subplots(len(EXAMPLES), 1, figsize=(9, 5.2 * len(EXAMPLES)))
    for ax, (relative, why) in zip(np.atleast_1d(axes), EXAMPLES):
        frame = data / relative
        image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
        spaces = ann.read_annotation(ann.annotation_for(frame)).labeled
        lot, date = frame.parents[2].name, frame.parent.name
        decided = inference.classify(image, spaces, lot, date, past, config)

        predicted = [dataclasses.replace(s, occupied=d["occupied"])
                     for s, d in zip(spaces, decided)]
        overlay = ext.draw_spaces(image, predicted)
        for space, d in zip(spaces, decided):
            if d["occupied"] != space.occupied:
                pts = np.asarray(space.contour, dtype=np.int32).reshape(-1, 1, 2)
                cv2.polylines(overlay, [pts], True, (0, 255, 255), 5)

        free = sum(not d["occupied"] for d in decided)
        reference = sum(not s.occupied for s in spaces)
        wrong = sum(d["occupied"] != s.occupied for s, d in zip(spaces, decided))
        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax.set_axis_off()
        ax.set_title(f"{lot} {WEATHER[frame.parents[1].name]} ({why}): {free} livres previstas, "
                     f"{reference} na referência, {wrong} vagas erradas", fontsize=9)
    figure.suptitle("Verde livre, vermelho ocupada (previsto); amarelo: decisão errada",
                    fontsize=10)
    figure.tight_layout()
    figure.savefig(destination, dpi=130, bbox_inches="tight")
    plt.close(figure)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.measurements, args.evaluation, args.history, args.config):
        if not path.is_file():
            print(f"error: {path} not found", file=sys.stderr)
            return 1

    evaluation = read_csv(args.evaluation)
    limits = {r["pipeline"]: float(r["threshold"]) for r in evaluation}
    config = json.loads(args.config.read_text(encoding="utf-8"))
    past = history.SpaceHistory(read_csv(args.history), config["pipeline"])

    args.output.mkdir(parents=True, exist_ok=True)
    comparison_figure(evaluation, args.output / "e6_comparison.png")
    histogram_figure(read_csv(args.measurements), limits, args.output / "e6_histograms.png")
    output_figure(args.data, past, config, args.output / "e6_output_examples.png")
    print(f"figures: {args.output}/e6_*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
