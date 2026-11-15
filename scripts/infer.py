"""Final output for one frame: occupied or free for every space, and the free count.

Reads the frame and the space polygons of the XML next to it, measures each space,
places the measure between the free and taken levels of that space's history and
applies the calibrated threshold from final_config.json. Labels in the XML are read
only after the decision, to print the reference count beside the predicted one.

    python -m scripts.infer --frame examples/PKLot/UFPR05/Sunny/2013-04-10/2013-04-10_08_25_02.jpg
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from parking import annotations as ann  # noqa: E402
from parking import extraction as ext  # noqa: E402
from parking import history, inference, split  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="infer", description=__doc__)
    p.add_argument("--frame", required=True, type=Path,
                   help="<lot>/<weather>/<date>/<frame>.jpg, with its .xml beside it")
    p.add_argument("--config", type=Path, default=ROOT / "results" / "final_config.json")
    p.add_argument("--history", type=Path, default=ROOT / "results" / "history.csv")
    p.add_argument("--output", type=Path, default=ROOT / "results" / "infer")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    frame = args.frame
    if not frame.is_file():
        print(f"error: frame not found: {frame}", file=sys.stderr)
        return 1
    if not ann.annotation_for(frame).is_file():
        print(f"error: no XML with the space polygons beside {frame}", file=sys.stderr)
        return 1
    for path in (args.config, args.history):
        if not path.is_file():
            print(f"error: not found: {path}; run scripts.space_levels first", file=sys.stderr)
            return 1

    image = cv2.imread(str(frame), cv2.IMREAD_COLOR)
    if image is None:
        print(f"error: could not read {frame}", file=sys.stderr)
        return 1

    config = json.loads(args.config.read_text(encoding="utf-8"))
    lot, date = frame.parents[2].name, frame.parent.name
    with args.history.open(newline="", encoding="utf-8") as handle:
        past = history.SpaceHistory(list(csv.DictReader(handle)), config["pipeline"])

    spaces = ann.read_annotation(ann.annotation_for(frame)).spaces
    if not spaces:
        print(f"error: no spaces in the XML of {frame}", file=sys.stderr)
        return 1
    if any(past.values_for(lot, s.id, date, split.TEST).size == 0 for s in spaces):
        print(f"error: lot '{lot}' or some of its spaces have no history", file=sys.stderr)
        return 1

    decided = inference.classify(image, spaces, lot, date, past, config)
    free = sum(not d["occupied"] for d in decided)
    labelled = [s for s in spaces if s.occupied is not None]
    reference = sum(not s.occupied for s in labelled) if len(labelled) == len(spaces) else None

    args.output.mkdir(parents=True, exist_ok=True)
    report = {"frame": frame.as_posix(), "lot": lot, "date": date, "config": config,
              "spaces": len(decided), "free": free, "occupied": len(decided) - free,
              "reference_free": reference, "decisions": decided}
    json_path = args.output / f"{frame.stem}.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    predicted = [dataclasses.replace(s, occupied=d["occupied"]) for s, d in zip(spaces, decided)]
    overlay = ext.draw_spaces(image, predicted)
    cv2.putText(overlay, f"livres: {free}/{len(decided)}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    image_path = args.output / f"{frame.stem}.png"
    cv2.imwrite(str(image_path), overlay)

    print(f"{lot} {date}: {free} vagas livres de {len(decided)}")
    if reference is not None:
        wrong = sum(d["occupied"] != s.occupied for s, d in zip(spaces, decided))
        print(f"referência do XML: {reference} livres, {wrong} vagas classificadas errado")
    print(f"\nsaída:  {json_path}\nimagem: {image_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
