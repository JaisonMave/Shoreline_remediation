"""User-defined vegetation-cover what-if (cover_whatif/1). Expected values are worked by hand: 1 January dates are whole calendar
decimal years, so a 2030 -> 2032 -> 2034 effect is exactly halfway on 1 January 2031 and 2033. The 60% anchor is a test fixture
only; the dashboard anchors on the measured Bay Jimmy survey."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.shoreline_remediation.projections import cover as CV, evidence as E, spec as S
from src.shoreline_remediation.recovery_trajectories import decimal_year

ROOT = Path(__file__).resolve().parents[1]
D = dt.date
FIXTURE = CV.Anchor("fixture", "day", "test fixture only", D(2016, 9, 30), 60.0, 5)


def effect(peak, start=D(2030, 1, 1), top=D(2032, 1, 1), end=D(2034, 1, 1), option="manual_removal"):
    return CV.CoverEffect(option, start, top, end, peak)


def run(eff, end=D(2036, 1, 1), cadence="annual", anchor=FIXTURE):
    return CV.two_arms(anchor, end, cadence, eff)


def val(w, date, col):
    return float(w.at(date)[col])


# ---- the owner's worked example ---------------------------------------------------------------------------------------

def test_plus_ten_points_rises_to_the_peak_and_returns():
    w = run(effect(10.0))
    assert w.has_treatment
    for date, expected in ((D(2030, 1, 1), 60.0), (D(2031, 1, 1), 65.0), (D(2032, 1, 1), 70.0), (D(2033, 1, 1), 65.0),
                           (D(2034, 1, 1), 60.0), (D(2035, 1, 1), 60.0)):
        assert val(w, date, "treatment_pct") == pytest.approx(expected, abs=1e-12), date
        assert val(w, date, "natural_recovery_pct") == 60.0
    assert (w.frame.natural_recovery_pct == 60.0).all()                       # the baseline never moves
    before = w.frame[w.frame.date < "2030-01-01"]
    assert len(before) > 5 and (before.treatment_pct == before.natural_recovery_pct).all() and (before.difference_pp == 0.0).all()
    assert set(w.frame.set_index("date").loc[["2030-01-01", "2032-01-01", "2034-01-01"], "sample"]) == \
        {"intervention_start", "effect_peak", "effect_end"}
    assert CV.peak_text(w) == ("At the peak (01 Jan 2032): natural recovery 60.0%; treatment scenario 70.0%; difference "
                               "+10.0 percentage points. The difference returns to zero by 01 Jan 2034.")


def test_damage_lowers_cover_temporarily():
    w = run(effect(-20.0))
    assert [val(w, D(y, 1, 1), "treatment_pct") for y in (2030, 2031, 2032, 2033, 2034)] == pytest.approx([60, 50, 40, 50, 60])
    assert "difference -20.0 percentage points" in CV.peak_text(w)


def test_blank_draws_only_the_baseline_and_zero_draws_two_coincident_arms():
    blank = run(effect(None))
    assert not blank.has_treatment and "treatment_pct" not in blank.frame and "enter an assumed peak change" in blank.message
    rows = CV.export_rows(_no_obs(), blank, "Manual removal")
    assert set(rows.arm) == {CV.NATURAL_ARM}
    assert not run(None).has_treatment
    zero = run(effect(0.0))
    assert zero.has_treatment and (zero.frame.treatment_pct == zero.frame.natural_recovery_pct).all()
    assert (zero.frame.difference_pp == 0.0).all() and not (zero.frame.difference_pp.astype(str) == "-0.0").any()
    assert "coincide" in CV.peak_text(zero)


@pytest.mark.parametrize("peak,text", [
    (40.0 + 1e-9, "between -60.0 and +40.0 percentage points"),
    (-60.5, "between -60.0 and +40.0 percentage points"),
])
def test_cover_outside_0_100_is_refused_with_the_allowable_range(peak, text):
    w = run(effect(peak))
    assert not w.has_treatment and text in w.message and "within 0-100%" in w.message


def test_boundary_values_are_allowed():
    assert run(effect(40.0)).at(D(2032, 1, 1)).treatment_pct == 100.0
    assert run(effect(-60.0)).at(D(2032, 1, 1)).treatment_pct == 0.0
    assert CV.allowed_range(70.0) == (-70.0, 30.0)


@pytest.mark.parametrize("eff,text", [
    (effect(5.0, start=D(2016, 9, 1)), "after the last survey"),
    (effect(5.0, top=D(2030, 1, 1)), "start, then peak, then end"),
    (effect(5.0, top=D(2035, 1, 1)), "start, then peak, then end"),
    (effect(5.0, top=D(2037, 1, 1), end=D(2038, 1, 1)), "peak falls after the scenario end"),
    (effect(float("inf")), "finite"),
])
def test_invalid_dates_and_values_explain_themselves(eff, text):
    w = run(eff)
    assert not w.has_treatment and text in w.message


def test_off_grid_peak_is_sampled_and_reported_exactly():
    start, top, end = D(2030, 3, 15), D(2031, 8, 20), D(2033, 2, 10)
    w = run(effect(12.0, start, top, end))
    assert {"2030-03-15", "2031-08-20", "2033-02-10"} <= set(w.frame.date)
    assert val(w, top, "treatment_pct") == 72.0 and w.frame.treatment_pct.max() == 72.0
    t = decimal_year(D(2031, 1, 1))
    expected = 60 + 12 * (t - decimal_year(start)) / (decimal_year(top) - decimal_year(start))
    assert val(w, D(2031, 1, 1), "treatment_pct") == pytest.approx(expected, abs=1e-12)
    assert "At the peak (20 Aug 2031)" in CV.peak_text(w) and "72.0%" in CV.peak_text(w)


def test_monthly_and_annual_agree_at_shared_dates():
    e = effect(12.0, D(2030, 3, 15), D(2031, 8, 20), D(2033, 2, 10))
    yearly, monthly = run(e).frame.set_index("date"), run(e, cadence="monthly").frame.set_index("date")
    shared = yearly.index.intersection(monthly.index)
    assert len(shared) == len(yearly)
    for col in ("natural_recovery_pct", "treatment_pct", "difference_pp"):
        assert (yearly.loc[shared, col] - monthly.loc[shared, col]).abs().max() == 0.0


def test_blocked_technique_draws_no_curve_even_with_an_effect():
    obs = _bay_jimmy_obs()
    sp = SimpleNamespace(end=D(2036, 1, 1), cadence="annual", technique="planting (after mechanical cleanup)", as_of="2016-12-31")
    blocked = SimpleNamespace(what_if_allowed=False, endpoint=CV.ENDPOINT, what_if_reason="Presupposes mechanical_removal")
    c = CV.compute(sp, obs, effect(5.0, option=sp.technique), blocked)
    assert not c.applied and not c.screening_allows and "Presupposes" in c.screening_reason
    assert set(c.rows.arm) == {"observed", CV.NATURAL_ARM}
    wrong_endpoint = SimpleNamespace(what_if_allowed=True, endpoint="cumulative_shoreline_retreat", what_if_reason="")
    assert not CV.compute(sp, obs, effect(5.0), wrong_endpoint).applied


# ---- the measured Bay Jimmy anchor -------------------------------------------------------------------------------------

def _spec(as_of="2016-12-31"):
    raw = json.loads((ROOT / "examples/projections/bay_jimmy_veg_manual_fit.json").read_text(encoding="utf-8"))
    raw.update(plot_group_id="untreated_heavy", arm="reference", model_version="observed_record/1", as_of=as_of,
               scenario_id="anchor_probe")
    return S.from_dict(raw)


def _bay_jimmy_obs(as_of="2016-12-31"):
    return E.vegetation_observed(_spec(as_of))


def _no_obs():
    return _bay_jimmy_obs().iloc[0:0]


def test_bay_jimmy_anchor_is_the_last_untreated_survey():
    a = CV.anchor_from(_bay_jimmy_obs())
    assert (a.survey, a.date_precision, a.value, a.n_plots, a.starts) == ("2016-09", "month", 70.0, 5, D(2016, 9, 30))
    assert "assumed" in a.date_basis                                # the 2016 survey month is not recorded in the sources
    assert CV.allowed_range(a.value) == (-70.0, 30.0)
    earlier = CV.anchor_from(_bay_jimmy_obs("2014-01-01"))
    assert (earlier.survey, earlier.value) == ("2013-09", pytest.approx(48.6))


def test_no_survey_at_the_cutoff_draws_no_future_curve():
    obs = _bay_jimmy_obs("2011-06-30")
    assert CV.anchor_from(obs) is None
    sp = SimpleNamespace(end=D(2036, 1, 1), cadence="annual", technique="manual_removal", as_of="2011-06-30")
    with pytest.raises(ValueError, match="no future curve is drawn"):
        CV.compute(sp, obs, None, None)


def test_exports_keep_survey_dates_and_label_the_baseline_assumption():
    obs = _bay_jimmy_obs()
    a = CV.anchor_from(obs)
    w = CV.two_arms(a, D(2036, 1, 1), "annual", effect(-10.0))
    rows = CV.export_rows(obs, w, "Manual removal")
    observed = rows[rows.arm == "observed"]
    assert observed.date.tolist() == ["2011-09", "2012-09", "2013-09", "2014-09", "2015-09", "2016-09"]
    assert (observed.date_precision == "month").all() and observed.interval_lo.notna().all()
    nat = rows[(rows.arm == CV.NATURAL_ARM) & (rows.record_type == "conditional_projection")]
    assert (nat.status_label == CV.BASELINE_LABEL).all() and (nat.total_cover == 70.0).all()
    assert CV.BASELINE_LABEL == "Natural recovery scenario: cover held at the last observed value"
    trt = rows[(rows.arm == CV.TREATMENT_ARM) & (rows.record_type == "conditional_projection")]
    assert (trt.status_label == "User-defined what-if").all() and (trt.origin == "user_assumption").all()
    assert (rows.unit == "percent").all() and set(trt.difference_unit) == {"percentage points"}
    assert set(rows[rows.record_type == "observed_anchor"].date) == {"2016-09-30"}
