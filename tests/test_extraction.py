import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking.extraction import contour_area, crop_space, order_contour


def test_ordering_is_invariant_to_permutation():
    """Same quadrilateral, corners in any order, must give the same result."""
    base = np.array([[10, 10], [30, 10], [30, 50], [10, 50]], dtype=np.float32)
    expected = order_contour(base)

    for k in range(4):
        np.testing.assert_allclose(order_contour(np.roll(base, k, axis=0)), expected)
    np.testing.assert_allclose(order_contour(base[::-1]), expected)


def test_first_edge_is_the_short_one():
    """A space lying on its side must still come out portrait."""
    ordered = order_contour(np.array([[0, 0], [60, 0], [60, 20], [0, 20]], dtype=np.float32))
    assert np.linalg.norm(ordered[0] - ordered[1]) <= np.linalg.norm(ordered[1] - ordered[2])


def test_ordering_rejects_wrong_point_count():
    with pytest.raises(ValueError):
        order_contour(np.array([[0, 0], [1, 1], [2, 2]], dtype=np.float32))


def test_crop_of_axis_aligned_region_keeps_content():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[20:60, 30:50] = (0, 0, 255)

    contour = np.array([[30, 20], [50, 20], [50, 60], [30, 60]], dtype=np.float32)
    patch = crop_space(image, contour, size=(20, 40))

    assert patch.shape == (40, 20, 3)
    assert (patch[5:-5, 5:-5, 2] > 200).all()
    assert (patch[5:-5, 5:-5, 0] < 50).all()


def test_crop_removes_perspective():
    """A filled trapezoid must come back as a filled rectangle."""
    image = np.zeros((200, 200), dtype=np.uint8)
    trapezoid = np.array([[80, 40], [120, 40], [150, 160], [50, 160]], dtype=np.float32)
    cv2.fillPoly(image, [trapezoid.astype(np.int32)], 255)

    patch = crop_space(image, trapezoid, size=(40, 60))

    assert patch.shape == (60, 40)
    assert patch.mean() > 240


def test_crop_honours_requested_size():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    contour = np.array([[10, 10], [40, 12], [38, 70], [8, 66]], dtype=np.float32)

    for size in [(16, 24), (48, 64), (64, 64)]:
        assert crop_space(image, contour, size).shape[:2] == (size[1], size[0])


def test_crop_rejects_invalid_size():
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    contour = np.array([[0, 0], [10, 0], [10, 20], [0, 20]], dtype=np.float32)

    with pytest.raises(ValueError):
        crop_space(image, contour, size=(0, 10))


def test_area_of_known_rectangle():
    contour = np.array([[0, 0], [20, 0], [20, 40], [0, 40]], dtype=np.float32)
    assert contour_area(contour) == pytest.approx(800.0, rel=1e-3)
