import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking.annotations import annotation_for, read_annotation

VALID = """<?xml version="1.0"?>
<parking id="ufpr04">
  <space id="1" occupied="1">
    <contour>
      <point x="720" y="549" /><point x="805" y="665" />
      <point x="715" y="698" /><point x="644" y="582" />
    </contour>
  </space>
  <space id="2" occupied="0">
    <contour>
      <point x="100" y="100" /><point x="150" y="100" />
      <point x="150" y="200" /><point x="100" y="200" />
    </contour>
  </space>
  <space id="3">
    <contour>
      <point x="10" y="10" /><point x="20" y="10" />
      <point x="20" y="30" /><point x="10" y="30" />
    </contour>
  </space>
</parking>
"""

BROKEN_CONTOURS = """<?xml version="1.0"?>
<parking id="ufpr05">
  <space id="1" occupied="1">
    <contour><point x="0" y="0" /><point x="10" y="0" /></contour>
  </space>
  <space id="2" occupied="0"><rotatedRect /></space>
  <space id="3" occupied="1">
    <contour>
      <point x="0" y="0" /><point x="10" y="0" />
      <point x="10" y="20" /><point x="0" y="20" />
    </contour>
  </space>
</parking>
"""

UPPERCASE_POINT = """<?xml version="1.0"?>
<parking id="ufpr04">
  <space id="1" occupied="0">
    <contour>
      <Point x="700" y="598" /><Point x="758" y="673" />
      <Point x="688" y="704" /><Point x="640" y="625" />
    </contour>
  </space>
</parking>
"""


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_reads_spaces_and_labels(tmp_path):
    annotation = read_annotation(write(tmp_path, "f.xml", VALID))

    assert annotation.parking_id == "ufpr04"
    assert len(annotation.spaces) == 3
    assert annotation.spaces[0].occupied is True
    assert annotation.spaces[1].occupied is False
    assert annotation.spaces[2].occupied is None


def test_contour_shape_and_values(tmp_path):
    contour = read_annotation(write(tmp_path, "f.xml", VALID)).spaces[0].contour

    assert contour.shape == (4, 2)
    assert contour.dtype.kind == "f"
    assert tuple(contour[0]) == (720.0, 549.0)


def test_labeled_skips_unlabeled_space(tmp_path):
    assert len(read_annotation(write(tmp_path, "f.xml", VALID)).labeled) == 2


def test_unusable_contours_are_counted_not_guessed(tmp_path):
    annotation = read_annotation(write(tmp_path, "f.xml", BROKEN_CONTOURS))

    assert len(annotation.spaces) == 1
    assert annotation.skipped == 2


def test_accepts_uppercase_point_tag(tmp_path):
    """53 of the 2553 XML files use <Point>; a case-sensitive read loses those frames."""
    annotation = read_annotation(write(tmp_path, "f.xml", UPPERCASE_POINT))

    assert len(annotation.spaces) == 1
    assert annotation.skipped == 0
    assert tuple(annotation.spaces[0].contour[0]) == (700.0, 598.0)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_annotation(tmp_path / "missing.xml")


def test_malformed_xml(tmp_path):
    with pytest.raises(ValueError):
        read_annotation(write(tmp_path, "bad.xml", "<parking><space</parking>"))


def test_unexpected_root(tmp_path):
    with pytest.raises(ValueError, match="unexpected root"):
        read_annotation(write(tmp_path, "other.xml", "<something />"))


def test_annotation_path_from_frame():
    assert annotation_for(Path("a/b/2012-12-07_16_57_25.jpg")).name == "2012-12-07_16_57_25.xml"
