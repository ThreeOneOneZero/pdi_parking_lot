"""Named combinations of photometric normalization and pixel measure.

Every experiment compares entries of PIPELINES over the same frozen sample, so adding
a normalization or a measure is one line here and no change to the scripts.
"""

from __future__ import annotations

from functools import partial
from typing import Callable

import numpy as np

from . import features, normalization, regions


def no_normalization(gray: np.ndarray) -> np.ndarray:
    """Leave the patch as it is; the M1 baseline."""
    return gray


def compose(normalize: Callable, measure: Callable) -> Callable:
    """Build `patch -> number`: grayscale, then normalize, then measure."""

    def run(patch: np.ndarray) -> float:
        return float(measure(normalize(features.to_gray(patch))))

    return run


PIPELINES: dict[str, Callable] = {
    "none+edge_density": compose(no_normalization, features.edge_density),
    "clahe+edge_density": compose(normalization.clahe, features.edge_density),
    "stretch+edge_density": compose(normalization.stretch, features.edge_density),
    # Morphology sizes from the calibration-only sweep in results/e4_sweep.csv.
    "none+region_fraction": compose(
        no_normalization, partial(regions.region_fraction, close_size=5, open_size=3)
    ),
    "clahe+region_fraction": compose(
        normalization.clahe, partial(regions.region_fraction, close_size=3, open_size=3)
    ),
}


def select(names: str | None) -> dict[str, Callable]:
    """Pipelines named in a comma separated list, or all of them when `names` is empty."""
    if not names:
        return dict(PIPELINES)
    chosen = {}
    for name in (n.strip() for n in names.split(",") if n.strip()):
        if name not in PIPELINES:
            raise KeyError(f"unknown pipeline '{name}', available: {', '.join(PIPELINES)}")
        chosen[name] = PIPELINES[name]
    return chosen
