import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import decision, metrics


def test_confusion_counts():
    labels = [1, 1, 0, 0, 1]
    predicted = [1, 0, 1, 0, 1]
    assert metrics.confusion(labels, predicted) == {"tp": 2, "tn": 1, "fp": 1, "fn": 1}


def test_scores_of_a_known_case():
    result = metrics.scores([1, 1, 0, 0, 1], [1, 0, 1, 0, 1])
    assert result["accuracy"] == pytest.approx(3 / 5)
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["recall"] == pytest.approx(2 / 3)
    assert result["f1"] == pytest.approx(2 / 3)
    assert (result["fp"], result["fn"]) == (1, 1)


def test_balanced_accuracy_does_not_reward_calling_everything_free():
    """90 free and 10 occupied: saying 'free' always is 90% accurate and useless."""
    labels = [0] * 90 + [1] * 10
    result = metrics.scores(labels, [0] * 100)
    assert result["accuracy"] == pytest.approx(0.9)
    assert result["balanced_accuracy"] == pytest.approx(0.5)
    assert math.isnan(result["precision"])


def test_balanced_accuracy_with_one_class_present():
    assert metrics.scores([0, 0, 0], [0, 1, 0])["balanced_accuracy"] == pytest.approx(2 / 3)


def test_count_error_per_frame():
    labels = [1, 0, 0, 1, 1]       # frame a: 2 free; frame b: 0 free
    predicted = [1, 1, 0, 0, 1]    # frame a: 1 free; frame b: 1 free
    frames = ["a", "a", "a", "b", "b"]
    result = metrics.count_error(labels, predicted, frames)
    assert result["frames"] == 2
    assert result["count_mae"] == pytest.approx(1.0)
    assert result["count_bias"] == pytest.approx(0.0)


def test_bootstrap_interval_is_reproducible_and_ordered():
    labels = [1, 0] * 30
    predicted = [1, 0, 1, 1] * 15
    clusters = [f"d{i // 6}" for i in range(60)]
    first = metrics.bootstrap_ci(labels, predicted, clusters, resamples=200, seed=3)
    second = metrics.bootstrap_ci(labels, predicted, clusters, resamples=200, seed=3)
    assert first == second
    assert first[0] <= first[1]


def test_bootstrap_needs_more_than_one_cluster():
    low, high = metrics.bootstrap_ci([1, 0], [1, 0], ["d1", "d1"])
    assert math.isnan(low) and math.isnan(high)


def test_calibration_finds_a_separating_threshold():
    values = [0.01, 0.02, 0.03, 0.30, 0.40, 0.50]
    labels = [0, 0, 0, 1, 1, 1]
    threshold, score = decision.calibrate(values, labels)
    assert 0.03 < threshold < 0.30
    assert score == pytest.approx(1.0)
    assert list(decision.predict(values, threshold)) == [False] * 3 + [True] * 3
