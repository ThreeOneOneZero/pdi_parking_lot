"""Error analysis: how errors spread over groups of spaces, such as size or position."""

from __future__ import annotations

import math

import numpy as np

from . import metrics


def quantile_bins(values, bins: int = 4) -> np.ndarray:
    """Group index 0..bins-1 by rank, so every group holds the same number of spaces.

    Ranking instead of cutting at value edges keeps the groups equal even when many
    spaces share the same value.
    """
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return np.array([], dtype=int)
    rank = np.empty(values.size, dtype=int)
    rank[np.argsort(values, kind="stable")] = np.arange(values.size)
    return rank * bins // values.size


def rates(labels, predicted) -> dict:
    """False negative rate among occupied spaces and false positive rate among free ones."""
    c = metrics.confusion(labels, predicted)
    occupied, free = c["tp"] + c["fn"], c["tn"] + c["fp"]
    return {
        "occupied": occupied,
        "fn": c["fn"],
        "fn_rate": c["fn"] / occupied if occupied else math.nan,
        "free": free,
        "fp": c["fp"],
        "fp_rate": c["fp"] / free if free else math.nan,
        "balanced_accuracy": metrics.balanced_accuracy(labels, predicted),
    }


def fn_rate(labels, predicted) -> float:
    return rates(labels, predicted)["fn_rate"]


def correlation(x, y) -> float:
    """Pearson correlation, to tell whether two groupings measure the same thing."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.size < 2 or x.std() == 0 or y.std() == 0:
        return math.nan
    return float(np.corrcoef(x, y)[0, 1])
