import math

import pytest

from validation.literature_pooling import _outcome_family, log_response_ratio, verdict_rule


def test_log_response_ratio_known_answer():
    effect, variance = log_response_ratio(
        treated_mean=20,
        control_mean=10,
        treated_spread=4,
        control_spread=2,
        n_treated=10,
        n_control=10,
    )
    assert effect == pytest.approx(math.log(2))
    assert variance == pytest.approx(0.008)


def test_verdict_rule_uses_prediction_interval_or_grade_ab_single_ci():
    assert verdict_rule(
        n_studies=3, effect=0.4, ci_lo=0.2, ci_hi=0.6,
        pi_lo=0.05, pi_hi=0.75, pooled=True,
    ) == "evidence of benefit"
    assert verdict_rule(
        n_studies=3, effect=-0.4, ci_lo=-0.6, ci_hi=-0.2,
        pi_lo=-0.8, pi_hi=-0.05, pooled=True,
    ) == "evidence of harm"
    assert verdict_rule(
        n_studies=1, effect=0.4, ci_lo=0.1, ci_hi=0.7, grade="A",
    ) == "evidence of benefit"
    assert verdict_rule(
        n_studies=1, effect=0.4, ci_lo=0.1, ci_hi=0.7, grade="C",
    ) == "no clear difference"
    assert verdict_rule(n_studies=0, has_evidence=False) == "no evidence"



def test_k2_verdict_uses_unopposed_grade_ab_study_intervals():
    assert verdict_rule(
        n_studies=2,
        study_intervals=[
            (-0.94, -1.58, -0.30),
            (-0.66, -1.26, -0.06),
        ],
    ) == "evidence of harm"
    assert verdict_rule(
        n_studies=2,
        study_intervals=[
            (0.50, 0.10, 0.90),
            (-0.50, -0.90, -0.10),
        ],
    ) == "no clear difference"


def test_rate_mapping_precedes_erosion_and_c011_is_not_an_erosion_effect():
    assert _outcome_family(
        {
            "effect_id": "toy",
            "outcome": "oil degradation in eroding sediment",
            "metric": "first-order rate constant",
        }
    ) == "degradation rate"
    assert _outcome_family(
        {
            "effect_id": "C011",
            "outcome": "beach elevation change relative to initial sand elevation",
            "metric": "plot-averaged elevation change",
        }
    ) == ""
