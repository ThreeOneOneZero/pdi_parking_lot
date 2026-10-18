"""The explicit decision rule, `measure > threshold`, and how the threshold is chosen."""

from __future__ import annotations

import numpy as np

from . import metrics


def calibrate(values, labels) -> tuple[float, float]:
    """Threshold with the best balanced accuracy on the calibration spaces.

    Candidates are the midpoints between consecutive distinct values. Returns the
    threshold and the balanced accuracy it reaches on those same spaces.
    """
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels, dtype=bool)

    candidates = np.unique(values)
    if candidates.size < 2:
        return float(candidates[0]) if candidates.size else 0.0, float("nan")

    midpoints = (candidates[:-1] + candidates[1:]) / 2
    best_threshold, best_score = float(midpoints[0]), -1.0
    for threshold in midpoints:
        score = metrics.balanced_accuracy(labels, values > threshold)
        if score > best_score:
            best_threshold, best_score = float(threshold), score
    return best_threshold, best_score


def predict(values, threshold: float) -> np.ndarray:
    """Occupied where the measure exceeds the threshold."""
    return np.asarray(values, dtype=float) > threshold
