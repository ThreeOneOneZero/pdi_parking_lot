"""E1 - crop parking spaces with perspective correction.

Produces the visual evidence for the M1 feasibility study: an overlay of one frame
with its annotated spaces, and a grid of cropped patches grouped by weather and class.

    python -m scripts.e1_extract_patches --data ../PKLot/PKLot --lot UFPR04
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import extraction as ext  # noqa: E402

WEATHERS = ("Sunny", "Cloudy", "Rainy")


def patch_size(text: str) -> tuple[int, int]:
    try:
        width, height = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"bad size '{text}', use WxH such as 48x64")
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError(f"size must be positive: '{text}'")
    return width, height


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e1_extract_patches", description=__doc__)
    p.add_argument("--data", required=True, type=Path,
                   help="PKLot directory holding the parking lots")
    p.add_argument("--lot", default="UFPR04", help="PUCPR, UFPR04 or UFPR05")
    p.add_argument("--weather", default="all", help="Sunny, Cloudy, Rainy or all")
    p.add_argument("--frames-per-weather", type=int, default=2)
    p.add_argument("--samples-per-cell", type=int, default=8,
                   help="patches shown per weather/class cell in the grid")
    p.add_argument("--patch-size", type=patch_size, default=ext.DEFAULT_SIZE, metavar="WxH")
    p.add_argument("--output", type=Path, default=ROOT / "images" / "results")
    p.add_argument("--results", type=Path, default=ROOT / "results")
    p.add_argument("--seed", type=int, default=42)
    return p


def load_frame(path: Path, size: tuple[int, int]):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"could not open image: {path}")

    annotation = ann.read_annotation(ann.annotation_for(path))
    patches = [
        (space, ext.crop_space(image, space.contour, size), ext.contour_area(space.contour))
        for space in annotation.spaces
    ]
    return image, annotation, patches


def save_grid(samples, destination: Path, lot: str, size: tuple[int, int]):
    weathers = [w for w in WEATHERS if any(k[0] == w for k in samples)]
    if not weathers:
        return None

    columns = max(len(samples.get((w, c), [])) for w in weathers for c in (True, False))
    if columns == 0:
        return None

    rows = len(weathers) * 2
    figure, axes = plt.subplots(rows, columns, figsize=(columns * 1.1, rows * 1.5), squeeze=False)

    for i, weather in enumerate(weathers):
        for j, occupied in enumerate((True, False)):
            row = i * 2 + j
            patches = samples.get((weather, occupied), [])
            for column in range(columns):
                ax = axes[row][column]
                ax.axis("off")
                if column < len(patches):
                    ax.imshow(cv2.cvtColor(patches[column], cv2.COLOR_BGR2RGB))
                if column == 0:
                    ax.set_ylabel(f"{weather}\n{'occupied' if occupied else 'free'}", fontsize=7)
                    ax.axis("on")
                    ax.set_xticks([])
                    ax.set_yticks([])

    figure.suptitle(f"{lot} - {size[0]}x{size[1]} patches after perspective correction", fontsize=10)
    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return destination


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    random.seed(args.seed)

    if not args.data.is_dir():
        print(f"error: data directory not found: {args.data}", file=sys.stderr)
        return 1

    weathers = WEATHERS if args.weather.lower() == "all" else (args.weather,)
    args.output.mkdir(parents=True, exist_ok=True)
    args.results.mkdir(parents=True, exist_ok=True)

    samples = defaultdict(list)
    rows = []
    frame_count = 0

    for weather in weathers:
        frames = ann.list_frames(args.data, args.lot, weather)
        if not frames:
            print(f"warning: no annotated frames in {args.lot}/{weather}", file=sys.stderr)
            continue

        # Spread the picks across the list so we don't sample the same minute twice.
        step = max(1, len(frames) // args.frames_per_weather)
        for frame in frames[::step][: args.frames_per_weather]:
            try:
                image, annotation, patches = load_frame(frame, args.patch_size)
            except (ValueError, FileNotFoundError) as err:
                print(f"warning: {err}", file=sys.stderr)
                continue

            frame_count += 1
            occupied = sum(1 for s, _, _ in patches if s.occupied)
            print(f"{args.lot}/{weather}/{frame.name}: {len(patches)} spaces "
                  f"({occupied} occupied, {len(patches) - occupied} free, "
                  f"{annotation.skipped} skipped)")

            cv2.imwrite(
                str(args.output / f"overlay_{args.lot}_{weather}_{frame.stem}.png"),
                ext.draw_spaces(image, annotation.spaces),
            )

            for space, patch, area in patches:
                if space.occupied is not None:
                    samples[(weather, space.occupied)].append(patch)
                rows.append({
                    "lot": args.lot,
                    "weather": weather,
                    "frame": frame.stem,
                    "space_id": space.id,
                    "occupied": "" if space.occupied is None else int(space.occupied),
                    "area_px": round(area, 1),
                })

    if frame_count == 0:
        print("error: no frames processed", file=sys.stderr)
        return 1

    for key in samples:
        random.shuffle(samples[key])
        samples[key] = samples[key][: args.samples_per_cell]

    grid = save_grid(samples, args.output / f"grid_{args.lot}.png", args.lot, args.patch_size)

    inventory = args.results / "e1_inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["lot", "weather", "frame", "space_id", "occupied", "area_px"],
        )
        writer.writeheader()
        writer.writerows(rows)

    areas = [row["area_px"] for row in rows]
    print(f"\nframes processed: {frame_count}")
    print(f"spaces extracted: {len(rows)}")
    print(f"space area (px):  min={min(areas):.0f} max={max(areas):.0f} "
          f"ratio={max(areas) / max(min(areas), 1):.1f}x")
    print(f"inventory:        {inventory}")
    if grid:
        print(f"grid:             {grid}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
