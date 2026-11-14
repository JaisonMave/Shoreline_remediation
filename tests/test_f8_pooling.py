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



def test_two_studies_give_no_clear_difference_under_the_restored_plan_rule():
    """D34: the plan's rule. Two studies are 'no clear difference' even when both intervals exclude zero."""
    both_harm = [(-0.94, -1.58, -0.30), (-0.66, -1.26, -0.06)]
    assert verdict_rule(n_studies=2, study_intervals=both_harm) == "no clear difference"
    assert verdict_rule(n_studies=2, study_intervals=both_harm, rule="original") == "no clear difference"


def test_superseded_f8b_rule_is_reachable_only_by_flag():
    both_harm = [(-0.94, -1.58, -0.30), (-0.66, -1.26, -0.06)]
    assert verdict_rule(n_studies=2, study_intervals=both_harm, rule="f8b") == "evidence of harm"
    assert verdict_rule(n_studies=2, rule="f8b", study_intervals=[(0.5, 0.1, 0.9), (-0.5, -0.9, -0.1)]) == "no clear difference"
    with pytest.raises(ValueError):
        verdict_rule(n_studies=2, rule="nonsense")


def test_single_grade_ab_study_still_uses_its_own_interval():
    assert verdict_rule(n_studies=1, effect=-0.5, ci_lo=-0.9, ci_hi=-0.1, grade="B") == "evidence of harm"


def test_b023_higher_ratio_is_harm_not_benefit():
    from validation.literature_pooling import _effect_from_row
    row = {"outcome": "intertidal community impact and repopulation amplitude",
           "metric": "ratio of stabilized post-recovery abundance to initial impacted abundance", "effect_type": "response_ratio",
           "treated_mean": "11.0", "control_mean": "3.0", "n_treated": "11", "n_control": "11"}
    fixed = _effect_from_row(row, "biological recovery")[0]
    old = _effect_from_row(row, "biological recovery", fix_direction=False)[0]
    assert fixed == pytest.approx(-math.log(11 / 3)) and old == pytest.approx(math.log(11 / 3))


def test_restored_verdict_table_has_no_hot_water_harm_verdict_and_esi_codes():
    import pandas as pd
    from validation.literature_pooling import VERDICTS
    v = pd.read_csv(VERDICTS)
    hw = v[v.technology == "high_pressure_heated_washing"]
    assert not (hw.verdict == "evidence of harm").any()
    assert "esi_codes" in v.columns
    assert hw[hw.habitat == "sand/gravel beach"].esi_codes.dropna().str.contains("5").any()


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
