import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import split

XML = '<?xml version="1.0"?><parking id="x"><space id="1" occupied="1"><contour>' \
      '<point x="0" y="0" /><point x="10" y="0" /><point x="10" y="20" />' \
      '<point x="0" y="20" /></contour></space></parking>'


def make_frames(root: Path, layout: dict) -> None:
    """layout maps (lot, weather, date) to the number of frames to create."""
    for (lot, weather, date), count in layout.items():
        folder = root / lot / weather / date
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            (folder / f"{date}_{i:02d}.jpg").write_bytes(b"")
            (folder / f"{date}_{i:02d}.xml").write_text(XML)


def test_dates_alternate_and_never_repeat():
    assigned = split.assign_dates(["d3", "d1", "d2", "d1", "d4"])
    assert assigned == {"d1": "calibration", "d2": "test", "d3": "calibration", "d4": "test"}


def test_sample_evenly_spreads_over_the_list():
    frames = [Path(f"{i:02d}.jpg") for i in range(20)]
    picked = split.sample_evenly(frames, 4)
    assert [p.stem for p in picked] == ["00", "05", "10", "15"]
    assert split.sample_evenly(frames, 0) == []


def test_a_date_under_two_weathers_stays_in_one_partition(tmp_path):
    """The reason the split is by date: the same day shows up as Sunny and Cloudy."""
    layout = {}
    for i, date in enumerate(["2012-12-01", "2012-12-02", "2012-12-03", "2012-12-04"]):
        for weather in split.WEATHERS:
            layout[("UFPR04", weather, date)] = 2
    make_frames(tmp_path, layout)

    rows = split.build_split(tmp_path, "UFPR04", frames_per_cell=10)
    split.check_split(rows, "UFPR04")

    partition_of = {}
    for row in rows:
        assert partition_of.setdefault(row["date"], row["partition"]) == row["partition"]


def test_other_lots_are_test_only(tmp_path):
    layout = {("UFPR04", w, d): 1 for w in split.WEATHERS for d in ("2012-12-01", "2012-12-02")}
    layout.update({("UFPR05", w, "2013-01-01"): 1 for w in split.WEATHERS})
    make_frames(tmp_path, layout)

    rows = split.build_split(tmp_path, "UFPR04", frames_per_cell=10)
    assert {r["partition"] for r in rows if r["lot"] == "UFPR05"} == {"test"}


def test_check_refuses_a_date_in_both_partitions():
    rows = [
        {"lot": "UFPR04", "weather": "Sunny", "date": "d1", "partition": "calibration"},
        {"lot": "UFPR04", "weather": "Cloudy", "date": "d1", "partition": "test"},
    ]
    with pytest.raises(ValueError, match="both partitions"):
        split.check_split(rows, "UFPR04")


def test_check_refuses_a_weather_without_calibration():
    rows = [{"lot": "UFPR04", "weather": w, "date": f"d{i}", "partition": "test"}
            for i, w in enumerate(split.WEATHERS)]
    with pytest.raises(ValueError, match="no calibration"):
        split.check_split(rows, "UFPR04")


def test_split_round_trips_through_csv(tmp_path):
    rows = [{"lot": "UFPR04", "weather": "Sunny", "date": "d1",
             "frame": "UFPR04/Sunny/d1/a.jpg", "partition": "calibration"}]
    path = tmp_path / "split.csv"
    split.write_split(path, rows)
    assert split.read_split(path) == rows
