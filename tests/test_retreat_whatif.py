"""User-defined retreat what-if (remediation scenarios plan, section 3). Expected values are computed by hand here, not with
the module's formula: 1 January dates are whole decimal years, so a rate change over [2030, 2040) adds rate x 10 years."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

from src.shoreline_remediation.projections import projection as P, runner, spec as S, whatif as W
from src.shoreline_remediation.recovery_trajectories import decimal_year

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/projections/bay_jimmy_retreat_2030.json"
D = dt.date


def make_spec(end="2050-01-01", rate=1.43, change=None, second=None, cadence="annual"):
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    a = [dict(assumption_id="retreat_rate", value=rate, unit="m/yr", origin="user_assumption", source="test")]
    if change:
        a += [dict(assumption_id="rate_change_date", value=change, unit="date", origin="user_assumption", source="test"),
              dict(assumption_id="changed_retreat_rate", value=second, unit="m/yr", origin="user_assumption", source="test")]
    raw.update(scenario_id="test_whatif", end_date=end, assumptions=a, cadence=cadence)
    return S.from_dict(raw)


@pytest.fixture(scope="module")
def anchor():
    obs = runner.observed_record(S.load(EXAMPLE))
    last = obs.sort_values("date").iloc[-1]
    assert last.date == "2016-10-05" and int(last.n_plots) == 9
    return D(2016, 10, 5), float(last.value)


def at(w, date):
    return w.frame.set_index("date").loc[date]


def effect(delta, start=D(2030, 1, 1), end=D(2040, 1, 1)):
    return W.RetreatEffect("manual_removal", start, end, delta)


# ---- the owner's worked example ---------------------------------------------------------------------------------------

def test_slower_retreat_example_matches_hand_arithmetic(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(), a, v, effect(-0.50))
    assert w.has_treatment
    years_to_2030 = 2030 - decimal_year(a)
    for date in ("2017-01-01", "2025-01-01", "2030-01-01"):          # identical through the intervention start
        r = at(w, date)
        assert r.treatment_m == r.natural_recovery_m and r.difference_m == 0.0
    assert at(w, "2030-01-01").natural_recovery_m == pytest.approx(v + 1.43 * years_to_2030, abs=1e-9)
    r40, r50 = at(w, "2040-01-01"), at(w, "2050-01-01")
    assert r40.natural_recovery_m == pytest.approx(v + 1.43 * (years_to_2030 + 10), abs=1e-9)
    assert r40.treatment_m == pytest.approx(v + 1.43 * (years_to_2030 + 10) - 5.0, abs=1e-9)
    assert r40.difference_m == pytest.approx(-5.0, abs=1e-12) and r50.difference_m == pytest.approx(-5.0, abs=1e-12)
    assert r50.treatment_m - r40.treatment_m == pytest.approx(14.3, abs=1e-9)      # baseline rate resumes after 2040
    assert at(w, "2035-01-01").treatment_rate_m_per_yr == pytest.approx(0.93) and at(w, "2045-01-01").treatment_rate_m_per_yr == 1.43
    assert W.summary_text(w, D(2050, 1, 1)).endswith("5.00 m less cumulative retreat under your assumption.")


def test_natural_arm_equals_the_existing_projection(anchor):
    a, v = anchor
    sp = make_spec(change="2035-06-30", second=2.19)
    base, _ = P.project(sp, a, v, 9)
    w = W.two_arms(sp, a, v, effect(-0.5))
    merged = base.merge(w.frame, on="date")
    assert len(merged) == len(base)
    assert (merged.cumulative_retreat_since_origin_m - merged.natural_recovery_m).abs().max() == 0.0


# ---- blank, zero, faster ----------------------------------------------------------------------------------------------

def test_blank_change_draws_no_treatment_curve(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(), a, v, effect(None))
    assert not w.has_treatment and "treatment_m" not in w.frame and "enter an assumed rate change" in w.message
    assert "treatment scenario" not in W.summary_text(w, D(2050, 1, 1))
    rows = W.export_rows(pd.DataFrame(), w, 9, "Manual removal")
    assert set(rows.arm) == {W.NATURAL_ARM}
    assert not W.two_arms(make_spec(), a, v, None).has_treatment


def test_zero_change_reproduces_the_baseline_exactly(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(), a, v, effect(0.0))
    assert w.has_treatment and (w.frame.treatment_m == w.frame.natural_recovery_m).all()
    assert "coincide" in W.summary_text(w, D(2050, 1, 1))


def test_faster_retreat_keeps_its_sign(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(), a, v, effect(+0.30, D(2030, 1, 1), D(2035, 1, 1)))
    assert at(w, "2050-01-01").difference_m == pytest.approx(1.5, abs=1e-12)
    assert W.summary_text(w, D(2050, 1, 1)).endswith("1.50 m more cumulative retreat under your assumption.")


# ---- schedule and date handling ----------------------------------------------------------------------------------------

def test_baseline_rate_change_during_treatment_is_carried_by_both_arms(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(change="2035-01-01", second=2.19), a, v, effect(-0.5))
    pre = 2030 - decimal_year(a)
    expected_nat_2040 = v + 1.43 * (pre + 5) + 2.19 * 5
    r = at(w, "2040-01-01")
    assert r.natural_recovery_m == pytest.approx(expected_nat_2040, abs=1e-9)
    assert r.treatment_m == pytest.approx(expected_nat_2040 - 5.0, abs=1e-9)
    assert at(w, "2035-01-01").difference_m == pytest.approx(-2.5, abs=1e-12)
    assert at(w, "2037-01-01").treatment_rate_m_per_yr == pytest.approx(1.69)
    assert at(w, "2050-01-01").difference_m == pytest.approx(-5.0, abs=1e-12)


def test_off_grid_intervention_dates_are_integrated_exactly(anchor):
    a, v = anchor
    start, end = D(2030, 7, 15), D(2033, 3, 20)
    w = W.two_arms(make_spec(), a, v, effect(-0.4, start, end))
    span = decimal_year(end) - decimal_year(start)
    assert {"2030-07-15", "2033-03-20"} <= set(w.frame.date)              # both dates are sampled exactly
    assert set(w.frame.set_index("date").loc[["2030-07-15", "2033-03-20"], "sample"]) == {"intervention_start", "effect_end"}
    assert at(w, "2031-01-01").difference_m == pytest.approx(-0.4 * (2031 - decimal_year(start)), abs=1e-12)
    assert at(w, "2033-03-20").difference_m == pytest.approx(-0.4 * span, abs=1e-12)
    assert at(w, "2040-01-01").difference_m == pytest.approx(-0.4 * span, abs=1e-12)
    assert at(w, "2030-07-15").difference_m == 0.0


def test_monthly_and_annual_agree_at_shared_dates(anchor):
    a, v = anchor
    e = effect(-0.4, D(2030, 7, 15), D(2033, 3, 20))
    yearly = W.two_arms(make_spec(cadence="annual"), a, v, e).frame.set_index("date")
    monthly = W.two_arms(make_spec(cadence="monthly"), a, v, e).frame.set_index("date")
    shared = yearly.index.intersection(monthly.index)
    assert len(shared) == len(yearly)
    for col in ("natural_recovery_m", "treatment_m", "difference_m"):
        assert (yearly.loc[shared, col] - monthly.loc[shared, col]).abs().max() == 0.0


def test_effect_ending_after_the_scenario_end_is_truncated(anchor):
    a, v = anchor
    w = W.two_arms(make_spec(end="2035-01-01"), a, v, effect(-0.5, D(2030, 1, 1), D(2040, 1, 1)))
    assert w.frame.date.iloc[-1] == "2035-01-01" and at(w, "2035-01-01").difference_m == pytest.approx(-2.5, abs=1e-12)


@pytest.mark.parametrize("eff,text", [
    (W.RetreatEffect("m", D(2016, 1, 1), D(2030, 1, 1), -0.5), "after the last survey"),
    (W.RetreatEffect("m", D(2030, 1, 1), D(2030, 1, 1), -0.5), "after the intervention start"),
    (W.RetreatEffect("m", D(2051, 1, 1), D(2060, 1, 1), -0.5), "on or after the scenario end date"),
    (W.RetreatEffect("m", D(2030, 1, 1), D(2040, 1, 1), -2.0), "advances seaward"),
    (W.RetreatEffect("m", D(2030, 1, 1), D(2040, 1, 1), float("nan")), "finite"),
])
def test_invalid_assumptions_explain_themselves_and_draw_nothing(anchor, eff, text):
    a, v = anchor
    w = W.two_arms(make_spec(), a, v, eff)
    assert not w.has_treatment and text in w.message and "treatment_m" not in w.frame


# ---- exports ----------------------------------------------------------------------------------------------------------

def test_exports_keep_survey_dates_and_label_the_user_assumption(anchor):
    a, v = anchor
    obs = runner.observed_record(S.load(EXAMPLE))
    w = W.two_arms(make_spec(), a, v, effect(-0.5))
    rows = W.export_rows(obs, w, 9, "Manual removal")
    observed = rows[rows.arm == "observed"]
    assert observed.date.tolist() == obs.date.tolist() and observed.date.iloc[-1] == "2016-10-05"
    assert (observed.record_type == "observed_group_mean").all()
    treat = rows[(rows.arm == W.TREATMENT_ARM) & (rows.record_type == "conditional_projection")]
    assert (treat.status_label == W.WHATIF_LABEL).all() and (treat.origin == "user_assumption").all()
    assert treat.series.iloc[0] == "User-defined what-if: Manual removal"
    end = rows[(rows.date == "2050-01-01")].set_index("arm")
    assert end.loc[W.TREATMENT_ARM, "difference_from_natural_m"] == pytest.approx(-5.0)
    anchors = rows[rows.record_type == "observed_anchor"]
    assert set(anchors.date) == {"2016-10-05"} and anchors.cumulative_retreat_m.nunique() == 1
    d = effect(-0.5).as_dict()
    assert d["origin"] == "user_assumption" and d["label"] == W.WHATIF_LABEL and d["measured"] is False
