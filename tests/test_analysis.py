import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from parking import analysis


def test_quartiles_have_equal_size_even_with_ties():
    groups = analysis.quantile_bins([5, 5, 5, 5, 1, 2, 9, 9], bins=4)
    assert sorted(groups.tolist()) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_quartiles_follow_the_order_of_the_values():
    groups = analysis.quantile_bins([40, 10, 30, 20], bins=4)
    assert groups.tolist() == [3, 0, 2, 1]


def test_quartiles_of_nothing():
    assert analysis.quantile_bins([], bins=4).size == 0


def test_rates_split_errors_by_class():
    labels = [1, 1, 1, 1, 0, 0]
    predicted = [1, 0, 0, 1, 1, 0]
    r = analysis.rates(labels, predicted)
    assert (r["occupied"], r["fn"], r["free"], r["fp"]) == (4, 2, 2, 1)
    assert r["fn_rate"] == pytest.approx(0.5)
    assert r["fp_rate"] == pytest.approx(0.5)


def test_fn_rate_without_occupied_spaces_is_undefined():
    assert math.isnan(analysis.fn_rate([0, 0], [0, 1]))


def test_correlation_of_perspective():
    """Spaces lower in the frame are closer, so larger: the two groupings align."""
    cy = [100, 200, 300, 400]
    area = [1000, 2100, 2900, 4100]
    assert analysis.correlation(area, cy) > 0.95
    assert math.isnan(analysis.correlation([1, 1, 1], [1, 2, 3]))
