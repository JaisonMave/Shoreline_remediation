import math

from validation.f11_integrated_validation import metric_row, report_class, wilson_interval


def test_wilson_interval_handles_zero_and_all_successes():
    low, high = wilson_interval(0, 6)
    assert low == 0
    assert 0 < high < 1
    low, high = wilson_interval(6, 6)
    assert 0 < low < 1
    assert math.isclose(high, 1)


def test_metric_row_returns_toy_rate_and_interval():
    row = metric_row("toy", 3, 4, "toy inputs")
    assert row["rate"] == 0.75
    assert math.isclose(row["wilson95_low"], 0.3006, rel_tol=0.01)
    assert math.isclose(row["wilson95_high"], 0.9544, rel_tol=0.01)


def test_report_class_uses_f11_active_and_monitor_definitions():
    class Report:
        def __init__(self, options, headline):
            self.options, self.headline = options, headline
    assert report_class(Report([{"recommendation_class": "A"}], "anything")) == "active"
    assert report_class(Report([{"recommendation_class": "B"}], "No option is shown; monitor.")) == "natural"
