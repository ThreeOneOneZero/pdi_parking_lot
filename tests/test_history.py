import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import history, split

XML = '<?xml version="1.0"?><parking id="x"><space id="1" occupied="1"><contour>' \
      '<point x="0" y="0" /><point x="10" y="0" /><point x="10" y="20" />' \
      '<point x="0" y="20" /></contour></space></parking>'


def test_levels_are_percentiles_of_the_history():
    free, taken = history.levels(list(range(101)), 20, 95)
    assert (free, taken) == (pytest.approx(20), pytest.approx(95))
    assert all(math.isnan(v) for v in history.levels([], 20, 95))


def test_rescale_puts_free_at_zero_and_taken_at_one():
    assert history.rescale(0.2, 0.2, 0.6, 0.1) == pytest.approx(0.0)
    assert history.rescale(0.6, 0.2, 0.6, 0.1) == pytest.approx(1.0)
    assert history.offset(0.5, 0.2) == pytest.approx(0.3)


def test_rescale_does_not_blow_up_a_space_that_never_changed():
    assert history.rescale(0.25, 0.2, 0.21, 0.1) == pytest.approx(0.5)


def history_rows():
    rows = []
    for date, partition, value in [("d1", "calibration", 0.1), ("d2", "test", 0.5),
                                   ("d3", "calibration", 0.3)]:
        rows.append({"lot": "L", "space_id": "1", "date": date, "partition": partition,
                     "m": value})
    return rows


def test_history_leaves_out_the_judged_date():
    past = history.SpaceHistory(history_rows(), "m")
    assert sorted(past.values_for("L", "1", "d2", split.TEST)) == [0.1, 0.3]


def test_calibration_never_sees_test_dates():
    past = history.SpaceHistory(history_rows(), "m")
    assert past.values_for("L", "1", "d1", split.CALIBRATION).tolist() == [0.3]


def test_unknown_space_has_no_history():
    past = history.SpaceHistory(history_rows(), "m")
    assert past.values_for("L", "99", "d1", split.TEST).size == 0


def test_history_frames_skip_the_split(tmp_path):
    for date in ("2012-01-01", "2012-01-02"):
        folder = tmp_path / "UFPR04" / "Sunny" / date
        folder.mkdir(parents=True)
        for i in range(3):
            (folder / f"{date}_{i}.jpg").write_bytes(b"")
            (folder / f"{date}_{i}.xml").write_text(XML)
    used = [{"frame": "UFPR04/Sunny/2012-01-01/2012-01-01_0.jpg"}]

    rows = history.history_frames(tmp_path, used, "UFPR04", per_weather=10)
    frames = {r["frame"] for r in rows}
    assert len(frames) == 5 and used[0]["frame"] not in frames
    assert {r["partition"] for r in rows if r["date"] == "2012-01-01"} == {"calibration"}
    assert {r["partition"] for r in rows if r["date"] == "2012-01-02"} == {"test"}
