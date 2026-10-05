"""Проверки справочника показателей и редактирования норм."""

from copy import deepcopy

import pytest

from models.metrics import default_metrics, get_metric


def test_update_metric_limits():
    metric = get_metric(default_metrics(), "temperature")
    metric.update_limits(16, 22)
    assert (metric.minimum, metric.maximum) == (16, 22)
    assert default_metrics()[0].minimum == 18


@pytest.mark.parametrize("minimum,maximum", [
    (30, 20), (float("nan"), 20), (0, float("inf")), (True, 20),
])
def test_invalid_limits_leave_metric_unchanged(minimum, maximum):
    metric = default_metrics()[0]
    before = deepcopy(metric)
    with pytest.raises(ValueError):
        metric.update_limits(minimum, maximum)
    assert metric == before


def test_leak_normal_cannot_include_leak():
    metric = get_metric(default_metrics(), "leak")
    with pytest.raises(ValueError):
        metric.update_limits(0, 1)


def test_unknown_metric():
    with pytest.raises(ValueError, match="не найден"):
        get_metric(default_metrics(), "unknown")
