"""The final command on the versioned examples, checked against the evaluation table."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import infer  # noqa: E402

EXAMPLE = ROOT / "examples" / "PKLot" / "UFPR05" / "Sunny" / "2013-04-10" / \
    "2013-04-10_08_25_02.jpg"


def test_example_gives_the_free_count(tmp_path):
    assert infer.main(["--frame", str(EXAMPLE), "--output", str(tmp_path)]) == 0
    report = json.loads((tmp_path / f"{EXAMPLE.stem}.json").read_text(encoding="utf-8"))
    assert report["spaces"] == 40
    assert report["free"] == sum(not d["occupied"] for d in report["decisions"])
    assert (tmp_path / f"{EXAMPLE.stem}.png").is_file()


def test_example_matches_the_evaluated_decisions(tmp_path):
    """Same frame, same decisions as the rows scored in results/evaluation_e6.csv."""
    infer.main(["--frame", str(EXAMPLE), "--output", str(tmp_path)])
    report = json.loads((tmp_path / f"{EXAMPLE.stem}.json").read_text(encoding="utf-8"))
    decided = {d["space_id"]: d["occupied"] for d in report["decisions"]}

    threshold = report["config"]["threshold"]
    with (ROOT / "results" / "measurements_e6.csv").open(newline="", encoding="utf-8") as h:
        rows = [r for r in csv.DictReader(h) if r["frame"].endswith(EXAMPLE.name)]
    assert rows
    for row in rows:
        assert decided[row["space_id"]] == (float(row["none+edge_density@rescale"]) > threshold)


def test_missing_frame_fails(tmp_path):
    assert infer.main(["--frame", str(tmp_path / "nothing.jpg"), "--output", str(tmp_path)]) == 1


def test_frame_without_polygons_fails(tmp_path):
    frame = tmp_path / "UFPR05" / "Sunny" / "2013-04-10" / "alone.jpg"
    frame.parent.mkdir(parents=True)
    frame.write_bytes(EXAMPLE.read_bytes())
    assert infer.main(["--frame", str(frame), "--output", str(tmp_path)]) == 1


def test_lot_without_history_fails(tmp_path):
    frame = tmp_path / "OTHER" / "Sunny" / "2013-04-10" / EXAMPLE.name
    frame.parent.mkdir(parents=True)
    frame.write_bytes(EXAMPLE.read_bytes())
    frame.with_suffix(".xml").write_bytes(EXAMPLE.with_suffix(".xml").read_bytes())
    assert infer.main(["--frame", str(frame), "--output", str(tmp_path)]) == 1
