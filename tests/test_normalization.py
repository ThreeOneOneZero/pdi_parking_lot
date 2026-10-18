import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import normalization
from parking.features import edge_density


def low_contrast_car():
    """Dark patch with a faint rectangle: the edges exist but stay under the threshold.

    Sobel answers a step with four times its height, so a step of 12 gives 48 < 60.
    """
    patch = np.full((64, 48), 40, dtype=np.uint8)
    patch[16:48, 10:38] = 52
    return patch


def test_outputs_keep_shape_and_type():
    patch = low_contrast_car()
    for normalize in (normalization.clahe, normalization.stretch):
        out = normalize(patch)
        assert out.shape == patch.shape
        assert out.dtype == np.uint8


def test_stretch_maps_the_percentiles_to_the_full_range():
    patch = np.tile(np.arange(0, 64, dtype=np.uint8).reshape(64, 1), (1, 48)) + 100
    out = normalization.stretch(patch)
    assert out.min() == 0
    assert out.max() == 255


def test_stretch_leaves_a_uniform_patch_uniform():
    patch = np.full((64, 48), 90, dtype=np.uint8)
    assert np.array_equal(normalization.stretch(patch), patch)


def test_normalization_lifts_faint_edges_over_the_threshold():
    """E3 in miniature: a low-contrast car is missed raw and found after normalizing."""
    patch = low_contrast_car()
    assert edge_density(patch) == 0.0
    assert edge_density(normalization.stretch(patch)) > 0.0
    assert edge_density(normalization.clahe(patch)) > 0.0


def test_stretch_also_amplifies_noise_on_empty_asphalt():
    """The risk E3 measures: slight noise on a free space becomes edges."""
    rng = np.random.default_rng(0)
    asphalt = (100 + rng.integers(-3, 4, size=(64, 48))).astype(np.uint8)
    assert edge_density(asphalt) == 0.0
    assert edge_density(normalization.stretch(asphalt)) > 0.0
