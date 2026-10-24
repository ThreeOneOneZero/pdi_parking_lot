"""E5 - do the errors concentrate by size, position or individual space?

Uses the measurements already taken, so no frame is read except one per lot for the
error map. Groups are quartiles inside each lot, because every camera has its own
scale of space size and position. Only test spaces are analysed.

    python -m scripts.e5_errors --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import analysis, metrics, split  # noqa: E402
from parking import annotations as ann  # noqa: E402

GROUPINGS = {"area": "area_px", "position": "cy"}
GROUP_FIELDS = ["lot", "grouping", "bin", "low", "high", "n", "occupied", "fn", "fn_rate",
                "fn_low", "fn_high", "free", "fp", "fp_rate", "balanced_accuracy"]
SPACE_FIELDS = ["lot", "space_id", "appearances", "occupied", "fn", "free", "fp",
                "errors", "error_rate"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e5_errors", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--pipeline", default="none+edge_density")
    p.add_argument("--bins", type=int, default=4)
    p.add_argument("--resamples", type=int, default=1000)
    p.add_argument("--measurements", type=Path, default=ROOT / "results" / "measurements.csv")
    p.add_argument("--evaluation", type=Path, default=ROOT / "results" / "evaluation.csv")
    p.add_argument("--results", type=Path, default=ROOT / "results")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    return p


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def by_quartile(rows, key, bins, resamples) -> list[dict]:
    """Error rates of each quartile of `key`, with an interval on the false negative rate."""
    values = [float(r[key]) for r in rows]
    groups = analysis.quantile_bins(values, bins)
    result = []
    for b in range(bins):
        members = [r for r, g in zip(rows, groups) if g == b]
        labels = [r["occupied"] == "1" for r in members]
        predicted = [r["predicted"] for r in members]
        low, high = metrics.bootstrap_ci(labels, predicted, [r["date"] for r in members],
                                         metric=analysis.fn_rate, resamples=resamples)
        span = [float(r[key]) for r in members]
        result.append({"bin": b + 1, "low": round(min(span), 1), "high": round(max(span), 1),
                       "n": len(members), **analysis.rates(labels, predicted),
                       "fn_low": low, "fn_high": high})
    return result


def by_space(rows) -> list[dict]:
    """Errors of every individual space over the test frames where it appears."""
    tally = defaultdict(lambda: {"appearances": 0, "occupied": 0, "fn": 0, "free": 0, "fp": 0})
    for r in rows:
        t = tally[r["space_id"]]
        t["appearances"] += 1
        if r["occupied"] == "1":
            t["occupied"] += 1
            t["fn"] += not r["predicted"]
        else:
            t["free"] += 1
            t["fp"] += r["predicted"]
    result = []
    for space_id, t in sorted(tally.items(), key=lambda item: int(item[0])):
        errors = t["fn"] + t["fp"]
        result.append({"space_id": space_id, **t, "errors": errors,
                       "error_rate": round(errors / t["appearances"], 4)})
    return result


def error_map(data, frame_path, spaces, lot, destination: Path) -> None:
    """Each space of one frame filled with its error rate over all test frames."""
    frame = data / frame_path
    image = cv2.cvtColor(cv2.imread(str(frame), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    rate = {s["space_id"]: s["error_rate"] for s in spaces}
    colormap = plt.get_cmap("RdYlGn_r")

    figure, ax = plt.subplots(figsize=(9, 5.4))
    ax.imshow(image)
    for space in ann.read_annotation(ann.annotation_for(frame)).labeled:
        if space.id not in rate:
            continue
        colour = colormap(min(rate[space.id] / 0.5, 1.0))
        ax.add_patch(Polygon(space.contour, closed=True, facecolor=colour, alpha=0.55,
                             edgecolor=colour, linewidth=1))
    ax.set_axis_off()
    mappable = plt.cm.ScalarMappable(cmap=colormap, norm=plt.Normalize(0, 0.5))
    bar = figure.colorbar(mappable, ax=ax, fraction=0.03, pad=0.01)
    bar.set_label("taxa de erro da vaga nos quadros de teste (0,5 ou mais em vermelho)",
                  fontsize=8)
    ax.set_title(f"{lot}: erro por vaga (baseline, partição de teste)", fontsize=10)
    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=130, bbox_inches="tight")
    plt.close(figure)


def rates_figure(table, destination: Path) -> None:
    lots = list(dict.fromkeys(r["lot"] for r in table))
    figure, axes = plt.subplots(1, len(lots), figsize=(4 * len(lots), 3.2), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, lot in zip(axes, lots):
        rows = [r for r in table if r["lot"] == lot and r["grouping"] == "area"]
        y = [100 * r["fn_rate"] for r in rows]
        err = [[100 * (r["fn_rate"] - r["fn_low"]) for r in rows],
               [100 * (r["fn_high"] - r["fn_rate"]) for r in rows]]
        ax.bar([f"Q{r['bin']}" for r in rows], y, yerr=err, capsize=3, color="tab:red")
        ax.set_title(lot, fontsize=10)
        ax.set_xlabel("quartil de área (Q1 menores, mais distantes)", fontsize=8)
    axes[0].set_ylabel("falsos negativos entre\nas ocupadas (%)")
    figure.suptitle("Taxa de falso negativo por tamanho da vaga, com intervalo de 95%",
                    fontsize=10)
    figure.tight_layout()
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)


def show(value: float) -> str:
    return "  -  " if math.isnan(value) else f"{100 * value:5.1f}"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.measurements, args.evaluation):
        if not path.is_file():
            print(f"error: {path} not found", file=sys.stderr)
            return 1

    limits = {r["pipeline"]: float(r["threshold"]) for r in read_csv(args.evaluation)}
    if args.pipeline not in limits:
        print(f"error: {args.pipeline} not in {args.evaluation}", file=sys.stderr)
        return 1
    threshold = limits[args.pipeline]

    test = [r for r in read_csv(args.measurements) if r["partition"] == split.TEST]
    for r in test:
        r["predicted"] = float(r[args.pipeline]) > threshold

    table, spaces_table = [], []
    for lot in split.LOTS:
        rows = [r for r in test if r["lot"] == lot]
        if not rows:
            continue
        corr = analysis.correlation([float(r["area_px"]) for r in rows],
                                    [float(r["cy"]) for r in rows])
        print(f"\n=== {lot} === (correlation between area and vertical position: {corr:+.2f})")
        for grouping, key in GROUPINGS.items():
            print(f"  by {grouping} ({key})        n   FN rate      95% CI    FP rate   bacc")
            for g in by_quartile(rows, key, args.bins, args.resamples):
                print(f"    Q{g['bin']} {g['low']:>7.1f}-{g['high']:<7.1f} {g['n']:>5}  "
                      f"{show(g['fn_rate'])}  [{show(g['fn_low'])},{show(g['fn_high'])}]  "
                      f"{show(g['fp_rate'])}  {show(g['balanced_accuracy'])}")
                table.append({"lot": lot, "grouping": grouping, **g})

        spaces = by_space(rows)
        spaces_table.extend({"lot": lot, **s} for s in spaces)
        worst = sorted(spaces, key=lambda s: -s["error_rate"])[:5]
        print("  worst spaces: " + ", ".join(
            f"#{s['space_id']} {100 * s['error_rate']:.0f}%" for s in worst))

        frame_path = sorted(r["frame"] for r in rows if r["weather"] == "Sunny")[0]
        error_map(args.data, frame_path, spaces, lot, args.output / f"e5_error_map_{lot}.png")

    write_csv(args.results / "e5_by_group.csv", GROUP_FIELDS,
              [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
               for r in table])
    write_csv(args.results / "e5_by_space.csv", SPACE_FIELDS, spaces_table)
    rates_figure(table, args.output / "e5_fn_by_area.png")

    print(f"\ngroups: {args.results / 'e5_by_group.csv'}")
    print(f"spaces: {args.results / 'e5_by_space.csv'}")
    print(f"figures: {args.output}/e5_*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
