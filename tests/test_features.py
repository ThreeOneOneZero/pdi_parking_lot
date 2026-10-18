import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking.features import edge_density, gradient_magnitude, mean_intensity


def test_flat_patch_has_no_edges():
    assert edge_density(np.full((64, 48), 120, dtype=np.uint8)) == 0.0


def test_structured_patch_scores_higher_than_flat():
    flat = np.full((64, 48), 120, dtype=np.uint8)

    striped = np.full((64, 48), 120, dtype=np.uint8)
    striped[::4] = 220

    assert edge_density(striped) > edge_density(flat)


def test_edge_density_survives_a_brightness_shift():
    """The point of the measure: an edge stays an edge when the scene gets darker.

    Halving every pixel halves the gradient too, so the raw count drops; what must
    not happen is the structured patch falling to the level of a flat one.
    """
    striped = np.full((64, 48), 200, dtype=np.uint8)
    striped[::4] = 40
    darker = (striped * 0.5).astype(np.uint8)

    assert edge_density(darker, threshold=30) > 0.0
    assert edge_density(darker, threshold=30) > edge_density(
        np.full((64, 48), 100, dtype=np.uint8), threshold=30
    )


def test_edge_density_is_a_fraction():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, size=(64, 48), dtype=np.uint8)

    assert 0.0 <= edge_density(noise) <= 1.0


def test_accepts_colour_and_grayscale():
    colour = np.zeros((64, 48, 3), dtype=np.uint8)
    gray = np.zeros((64, 48), dtype=np.uint8)

    assert edge_density(colour) == edge_density(gray)


def test_gradient_magnitude_is_the_same_on_every_call():
    """Guards the reproducibility fix: the measure must not change between runs."""
    rng = np.random.default_rng(1)
    patch = rng.integers(0, 256, size=(64, 48), dtype=np.uint8)
    first = gradient_magnitude(patch)
    assert all(np.array_equal(first, gradient_magnitude(patch)) for _ in range(30))


def test_mean_intensity_of_known_patch():
    assert mean_intensity(np.full((10, 10), 128, dtype=np.uint8)) == 128.0
