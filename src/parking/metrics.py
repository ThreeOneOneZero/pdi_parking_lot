"""Scores for the occupied/free decision. Occupied is the positive class.

A false positive says occupied where the space was free; a false negative says free
where it was occupied, the costly error in the application, since it sends a driver
to a space that is taken.
"""

from __future__ import annotations

import math

import numpy as np


def confusion(labels, predicted) -> dict:
    """True and false positives and negatives."""
    labels = np.asarray(labels, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)
    return {
        "tp": int((predicted & labels).sum()),
        "tn": int((~predicted & ~labels).sum()),
        "fp": int((predicted & ~labels).sum()),
        "fn": int((~predicted & labels).sum()),
    }


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else math.nan


def scores(labels, predicted) -> dict:
    """Accuracy, balanced accuracy, precision, recall and F1 of one decision.

    Balanced accuracy averages the recall of each class present, so a lot where
    most spaces are free cannot look good by calling everything free.
    """
    c = confusion(labels, predicted)
    n = c["tp"] + c["tn"] + c["fp"] + c["fn"]

    recall = _ratio(c["tp"], c["tp"] + c["fn"])
    specificity = _ratio(c["tn"], c["tn"] + c["fp"])
    precision = _ratio(c["tp"], c["tp"] + c["fp"])
    present = [v for v in (recall, specificity) if not math.isnan(v)]

    return {
        "n": n,
        "accuracy": _ratio(c["tp"] + c["tn"], n),
        "balanced_accuracy": sum(present) / len(present) if present else math.nan,
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * c["tp"], 2 * c["tp"] + c["fp"] + c["fn"]),
        "fp": c["fp"],
        "fn": c["fn"],
    }


def balanced_accuracy(labels, predicted) -> float:
    return scores(labels, predicted)["balanced_accuracy"]


def count_error(labels, predicted, frames) -> dict:
    """Error in the number of free spaces per frame, the figure a parking panel shows.

    Returns the mean absolute error and the mean signed error; a positive bias means
    the method announces more free spaces than there are.
    """
    labels = np.asarray(labels, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)
    frames = np.asarray(frames)

    errors = []
    for frame in np.unique(frames):
        here = frames == frame
        errors.append(int((~predicted[here]).sum()) - int((~labels[here]).sum()))

    errors = np.array(errors, dtype=float)
    return {
        "frames": len(errors),
        "count_mae": float(np.abs(errors).mean()) if errors.size else math.nan,
        "count_bias": float(errors.mean()) if errors.size else math.nan,
    }


def bootstrap_ci(
    labels,
    predicted,
    clusters,
    metric=balanced_accuracy,
    resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Confidence interval of `metric`, resampling whole clusters with replacement.

    Spaces of one frame, and frames of one day, are not independent, so resampling
    single spaces would give an interval narrower than the data support.
    """
    labels = np.asarray(labels, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)
    clusters = np.asarray(clusters)

    groups = [np.flatnonzero(clusters == c) for c in np.unique(clusters)]
    if len(groups) < 2:
        return math.nan, math.nan

    rng = np.random.default_rng(seed)
    values = []
    for _ in range(resamples):
        chosen = rng.integers(0, len(groups), size=len(groups))
        index = np.concatenate([groups[g] for g in chosen])
        value = metric(labels[index], predicted[index])
        if not math.isnan(value):
            values.append(value)

    if not values:
        return math.nan, math.nan
    tail = (1 - confidence) / 2 * 100
    low, high = np.percentile(values, [tail, 100 - tail])
    return float(low), float(high)


def paired_difference(
    labels,
    predicted_base,
    predicted_new,
    clusters,
    metric=balanced_accuracy,
    resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float, float]:
    """How much `metric` changes from the base decision to the new one, with an interval.

    Both decisions are scored on the same resampled clusters, so the interval answers
    whether the new one is better on these spaces, which two separate intervals that
    overlap cannot answer. Returns (difference, low, high).
    """
    labels = np.asarray(labels, dtype=bool)
    base = np.asarray(predicted_base, dtype=bool)
    new = np.asarray(predicted_new, dtype=bool)
    clusters = np.asarray(clusters)

    observed = metric(labels, new) - metric(labels, base)
    groups = [np.flatnonzero(clusters == c) for c in np.unique(clusters)]
    if len(groups) < 2:
        return observed, math.nan, math.nan

    rng = np.random.default_rng(seed)
    values = []
    for _ in range(resamples):
        chosen = rng.integers(0, len(groups), size=len(groups))
        index = np.concatenate([groups[g] for g in chosen])
        value = metric(labels[index], new[index]) - metric(labels[index], base[index])
        if not math.isnan(value):
            values.append(value)

    if not values:
        return observed, math.nan, math.nan
    tail = (1 - confidence) / 2 * 100
    low, high = np.percentile(values, [tail, 100 - tail])
    return observed, float(low), float(high)
