import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import regions


def components(mask):
    return cv2.connectedComponents(mask, connectivity=8)[0] - 1


def test_edge_mask_is_binary():
    gray = np.full((64, 48), 100, dtype=np.uint8)
    gray[20:40, 10:30] = 200
    mask = regions.edge_mask(gray)
    assert set(np.unique(mask).tolist()) == {0, 255}


def test_opening_removes_specks_and_thin_lines_but_keeps_a_block():
    mask = np.zeros((64, 48), dtype=np.uint8)
    mask[20:40, 14:34] = 255     # the car
    mask[5, 5] = 255             # speck
    mask[58, 40] = 255           # speck
    mask[:, 2] = 255             # painted line, 1 px wide
    cleaned = regions.clean(mask, close_size=3, open_size=3)
    assert components(mask) == 4
    assert components(cleaned) == 1
    assert cleaned[30, 24] == 255


def test_closing_joins_a_fragmented_outline():
    """Why closing comes first: a car's edges arrive in pieces."""
    mask = np.zeros((64, 48), dtype=np.uint8)
    mask[10:14, 8:40] = 255
    mask[50:54, 8:40] = 255
    mask[16:48, 8:12] = 255      # gaps of 2 px separate the four sides
    mask[16:48, 36:40] = 255
    assert components(mask) == 4
    assert components(regions.clean(mask, close_size=5, open_size=3)) == 1


def test_largest_component_picks_the_biggest():
    mask = np.zeros((64, 48), dtype=np.uint8)
    mask[2:6, 2:6] = 255         # 16 px
    mask[30:40, 20:30] = 255     # 100 px
    region = regions.largest_component(mask)
    assert np.count_nonzero(region) == 100
    assert region[35, 25] == 255 and region[3, 3] == 0


def test_largest_component_of_an_empty_mask():
    assert not regions.largest_component(np.zeros((64, 48), dtype=np.uint8)).any()


def test_descriptors_of_a_rectangle():
    region = np.zeros((64, 48), dtype=np.uint8)
    region[10:42, 8:32] = 255    # 32 x 24 = 768 px
    d = regions.describe(region)
    assert d["area_fraction"] == pytest.approx(768 / (64 * 48))
    assert d["extent"] == pytest.approx(1.0)
    assert d["solidity"] == pytest.approx(1.0)


def test_solidity_never_exceeds_one_and_drops_for_a_hollow_shape():
    ring = np.zeros((64, 48), dtype=np.uint8)
    cv2.rectangle(ring, (8, 10), (40, 54), 255, thickness=3)
    d = regions.describe(ring)
    assert d["solidity"] < 0.5
    assert all(0 < v <= 1 for v in d.values())


def test_descriptors_of_an_empty_region():
    assert regions.describe(np.zeros((64, 48), dtype=np.uint8)) == {
        "area_fraction": 0.0, "extent": 0.0, "solidity": 0.0}


def test_flat_patch_has_no_region():
    assert regions.region_fraction(np.full((64, 48), 120, dtype=np.uint8)) == 0.0


def test_a_car_covers_more_than_scattered_texture():
    """The point of E4: a dense blob scores high, isolated specks score low."""
    rng = np.random.default_rng(0)
    car = np.full((64, 48), 90, dtype=np.uint8)
    car[12:52, 8:40] = rng.choice([30, 200], size=(40, 32)).astype(np.uint8)

    texture = np.full((64, 48), 90, dtype=np.uint8)
    texture[4::12, 4::12] = 220  # specks far from each other

    assert regions.region_fraction(car) > 0.3
    assert regions.region_fraction(texture) < 0.05


def test_stages_end_in_the_measured_region():
    rng = np.random.default_rng(1)
    gray = np.full((64, 48), 90, dtype=np.uint8)
    gray[12:52, 8:40] = rng.choice([30, 200], size=(40, 32)).astype(np.uint8)
    steps = regions.stages(gray)
    assert list(steps) == ["edges", "closed", "opened", "region"]
    assert np.count_nonzero(steps["region"]) / steps["region"].size == pytest.approx(
        regions.region_fraction(gray))
