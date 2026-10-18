"""Choose the morphology sizes of the region measure on the calibration partition only.

Every closing and opening size is scored by the balanced accuracy its best threshold
reaches on calibration spaces. Test frames are never read, so the choice cannot leak
into the evaluation.

    python -m scripts.e4_sweep --data ../PKLot/PKLot
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import decision, features, normalization, regions, split  # noqa: E402
from parking import extraction as ext  # noqa: E402

NORMALIZERS = {"none": lambda g: g, "clahe": normalization.clahe}
CLOSE_SIZES = (3, 5, 7, 9)
OPEN_SIZES = (3, 5, 7)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="e4_sweep", description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--split", type=Path, default=ROOT / "results" / "split.csv")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "e4_sweep.csv")
    return p


def calibration_patches(data: Path, entries: list[dict]) -> tuple[list, list]:
    """Grayscale patches and labels of every labelled space in the calibration frames."""
    patches, labels = [], []
    for entry in entries:
        if entry["partition"] != split.CALIBRATION:
            raise ValueError(f"test frame reached the sweep: {entry['frame']}")
        frame = data / entry["frame"]
        image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
        for space in ann.read_annotation(ann.annotation_for(frame)).labeled:
            patches.append(features.to_gray(ext.crop_space(image, space.contour)))
            labels.append(bool(space.occupied))
    return patches, labels


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.split.is_file():
        print(f"error: split not found: {args.split}", file=sys.stderr)
        return 1

    entries = [e for e in split.read_split(args.split) if e["partition"] == split.CALIBRATION]
    patches, labels = calibration_patches(args.data, entries)
    print(f"{len(entries)} calibration frames, {len(patches)} spaces\n")

    rows = []
    for norm_name, normalize in NORMALIZERS.items():
        normalized = [normalize(p) for p in patches]
        _, edge_score = decision.calibrate([features.edge_density(g) for g in normalized], labels)
        print(f"--- {norm_name} --- edge density on calibration: {100 * edge_score:.1f}%")
        for close in CLOSE_SIZES:
            line = []
            for opening in OPEN_SIZES:
                values = [regions.region_fraction(g, close, opening) for g in normalized]
                threshold, score = decision.calibrate(values, labels)
                rows.append({"normalization": norm_name, "close": close, "open": opening,
                             "threshold": round(threshold, 6),
                             "calibration_bacc": round(score, 4)})
                line.append(f"open {opening}: {100 * score:5.1f}")
            print(f"  close {close}   " + "   ".join(line))

        best = max((r for r in rows if r["normalization"] == norm_name),
                   key=lambda r: (r["calibration_bacc"], -r["close"], -r["open"]))
        print(f"  best: close {best['close']}, open {best['open']} "
              f"({100 * best['calibration_bacc']:.1f}%)\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"sweep: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
