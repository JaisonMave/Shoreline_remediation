"""User-defined soil tPAH what-if (tpah_whatif/1). Expected values are worked by hand: 1 January dates are whole calendar decimal
years, so a two-year half-life halves the concentration exactly every two 1 January dates. The 100 mg/kg anchor is a test fixture
only; the dashboard anchors on the measured Bay Jimmy cores."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from src.shoreline_remediation.projections import evidence as E, pah as PH
from src.shoreline_remediation.recovery_trajectories import decimal_year

D = dt.date
FIXTURE = PH.Anchor("fixture", "fixture", "day", D(2028, 1, 1), 100.0, 9, "0-10 cm cores", "tPAH (fixture)")


def effect(r, date=D(2030, 1, 1), option="manual_removal", basis=PH.DEFAULT_BASIS):
    return PH.PahEffect(option, date, r, basis)


def run(eff, half_life=2.0, end=D(2033, 1, 1), cadence="annual", anchor=FIXTURE):
    return PH.two_arms(anchor, end, cadence, half_life, eff)


def at(w, date, col, sample=None):
    return float(w.row(date, sample)[col])


# ---- the owner's hand check ---------------------------------------------------------------------------------------------

def test_half_life_and_twenty_percent_reduction_match_the_hand_check():
    w = run(effect(20.0))
    assert w.has_treatment
    assert at(w, D(2030, 1, 1), "natural_mgkg", "intervention_before") == pytest.approx(50.0, abs=1e-12)
    assert at(w, D(2030, 1, 1), "treatment_mgkg", "intervention_before") == pytest.approx(50.0, abs=1e-12)
    assert at(w, D(2030, 1, 1), "treatment_mgkg", "intervention_after") == pytest.approx(40.0, abs=1e-12)
    assert at(w, D(2032, 1, 1), "natural_mgkg") == pytest.approx(25.0, abs=1e-12)
    assert at(w, D(2032, 1, 1), "treatment_mgkg") == pytest.approx(20.0, abs=1e-12)
    before = w.frame[w.frame.date < "2030-01-01"]
    assert (before.treatment_mgkg == before.natural_mgkg).all() and (before.difference_mgkg == 0.0).all()
    assert list(w.frame[w.frame.date == "2030-01-01"]["sample"]) == ["intervention_before", "intervention_after"]
    assert PH.summary_text(w, D(2033, 1, 1)).startswith("At the intervention (01 Jan 2030): 50.0 mg/kg before, 40.0 mg/kg after")


def test_held_baseline_is_flat_and_the_treated_arm_steps_once():
    w = run(effect(20.0), half_life=None)
    assert (w.frame.natural_mgkg == 100.0).all()
    after = w.frame[(w.frame.date >= "2030-01-01") & (w.frame["sample"] != "intervention_before")]
    assert after.treatment_mgkg.tolist() == pytest.approx([80.0] * len(after))
    assert after.difference_mgkg.tolist() == pytest.approx([-20.0] * len(after))
    assert PH.baseline_label(None) == "Natural recovery scenario: concentration held at the last observation"
    assert "zero long-term background" in PH.baseline_label(2.0)


def test_blank_draws_the_baseline_alone_and_zero_draws_two_identical_arms():
    blank = run(effect(None))
    assert not blank.has_treatment and "treatment_mgkg" not in blank.frame and "enter an assumed reduction" in blank.message
    assert not (blank.frame["sample"] == "intervention_before").any()
    assert set(PH.export_rows(_obs().iloc[0:0], blank, "Manual removal").arm) == {PH.NATURAL_ARM}
    zero = run(effect(0.0))
    assert zero.has_treatment and (zero.frame.treatment_mgkg == zero.frame.natural_mgkg).all()
    assert (zero.frame.difference_mgkg == 0.0).all() and not (zero.frame.difference_mgkg.astype(str) == "-0.0").any()
    assert "identical" in PH.summary_text(zero, D(2033, 1, 1))


def test_full_reduction_removes_the_concentration():
    w = run(effect(100.0))
    assert at(w, D(2030, 1, 1), "treatment_mgkg", "intervention_after") == 0.0
    assert (w.frame[w.frame.date > "2030-01-01"].treatment_mgkg == 0.0).all()


@pytest.mark.parametrize("r", [-0.1, 100.1, float("nan"), float("inf")])
def test_reductions_outside_0_to_100_are_refused(r):
    w = run(effect(r))
    assert not w.has_treatment and "between 0% and 100%" in w.message


@pytest.mark.parametrize("hl", [0.0, -1.0, float("inf"), float("nan")])
def test_invalid_half_lives_are_refused(hl):
    assert PH.baseline_problem(hl)
    with pytest.raises(ValueError, match="positive, finite"):
        run(effect(20.0), half_life=hl)


@pytest.mark.parametrize("eff,text", [
    (effect(20.0, date=D(2027, 6, 1)), "after the last measurement"),
    (effect(20.0, date=D(2034, 1, 1)), "after the scenario end date"),
    (effect(20.0, basis="  "), "Record the basis"),
])
def test_invalid_dates_and_missing_basis_explain_themselves(eff, text):
    w = run(eff)
    assert not w.has_treatment and text in w.message


def test_intervention_between_annual_samples_is_exact():
    d = D(2030, 7, 15)
    w = run(effect(20.0, date=d))
    t, t0 = decimal_year(d), decimal_year(D(2028, 1, 1))
    expected = 100.0 * 2 ** (-(t - t0) / 2.0)
    assert at(w, d, "treatment_mgkg", "intervention_before") == pytest.approx(expected, abs=1e-12)
    assert at(w, d, "treatment_mgkg", "intervention_after") == pytest.approx(0.8 * expected, abs=1e-12)
    assert at(w, D(2031, 1, 1), "treatment_mgkg") == pytest.approx(0.8 * at(w, D(2031, 1, 1), "natural_mgkg"), abs=1e-12)
    assert at(w, D(2030, 1, 1), "difference_mgkg") == 0.0


def test_monthly_and_annual_agree_at_shared_dates():
    e = effect(20.0, date=D(2030, 7, 15))
    yearly, monthly = run(e).frame, run(e, cadence="monthly").frame
    key = ["date", "sample"]
    merged = yearly.merge(monthly, on=key, suffixes=("_y", "_m"))
    assert len(merged) == len(yearly)
    for col in ("natural_mgkg", "treatment_mgkg", "difference_mgkg"):
        assert (merged[f"{col}_y"] - merged[f"{col}_m"]).abs().max() == 0.0


def test_blocked_technique_draws_no_treatment_curve():
    sp = SimpleNamespace(end=D(2033, 1, 1), cadence="annual", technique="planting (after mechanical cleanup)", as_of=PH.AS_OF)
    blocked = SimpleNamespace(what_if_allowed=False, endpoint=PH.ENDPOINT, what_if_reason="Presupposes mechanical_removal")
    c = PH.compute(sp, _obs(), None, effect(20.0, option=sp.technique), blocked)
    assert not c.applied and set(c.rows.arm) == {"observed", PH.NATURAL_ARM} and "Presupposes" in c.screening_reason
    wrong = SimpleNamespace(what_if_allowed=True, endpoint="total_vegetation_cover", what_if_reason="")
    assert not PH.compute(sp, _obs(), None, effect(20.0), wrong).applied


# ---- the measured Bay Jimmy anchor and exports ----------------------------------------------------------------------------

def _obs(as_of=PH.AS_OF, group="untreated_heavy"):
    return E.tpah_observed(PH.observation_spec(group, as_of))


def test_bay_jimmy_anchor_is_september_2012_112_mg_per_kg_nine_plots():
    a = PH.anchor_from(_obs())
    assert (a.survey, a.survey_period, a.date_precision, a.value, a.n_plots, a.starts) == \
        ("2012-09", "September 2012", "month", 112.0, 9, D(2012, 9, 30))
    assert a.depth == "0-10 cm cores, surface oil scraped aside" and "dry or wet basis not recorded" in a.analyte
    early = PH.anchor_from(_obs("2012-01-01"))
    assert (early.survey_period, early.value) == ("July-August 2011", 260.0)
    manual = _obs(group="manual_removal_heavy")
    assert manual["value"].tolist() == [220.0, 101.0] and manual.survey_period.tolist() == ["July-August 2011", "September 2012"]


def test_no_measurement_at_the_cutoff_draws_no_future_curve():
    obs = _obs("2011-06-30")
    assert PH.anchor_from(obs) is None
    sp = SimpleNamespace(end=D(2030, 1, 1), cadence="annual", technique="manual_removal", as_of="2011-06-30")
    with pytest.raises(ValueError, match="no future curve is drawn"):
        PH.compute(sp, obs, None, None, None)


def test_exports_keep_measurement_dates_and_both_intervention_rows_in_order():
    obs = _obs()
    w = PH.two_arms(PH.anchor_from(obs), D(2030, 1, 1), "annual", 4.0, effect(25.0, date=D(2020, 1, 1)))
    rows = PH.export_rows(obs, w, "Manual removal")
    observed = rows[rows.arm == "observed"]
    assert observed.date.tolist() == ["2011-07/08", "2012-09"] and observed.survey_period.tolist() == \
        ["July-August 2011", "September 2012"]
    assert (rows.sampling_depth == "0-10 cm cores, surface oil scraped aside").all() and (rows.unit == "mg/kg").all()
    trt = rows[(rows.arm == PH.TREATMENT_ARM) & (rows.date == "2020-01-01")]
    assert trt["sample"].tolist() == ["intervention_before", "intervention_after"] and trt["order"].is_monotonic_increasing
    assert trt.soil_tpah.iloc[1] == pytest.approx(0.75 * trt.soil_tpah.iloc[0])
    nat = rows[(rows.arm == PH.NATURAL_ARM) & (rows.date == "2020-01-01")]
    assert len(nat) == 1                                                    # one natural value per date
    assert rows["order"].is_monotonic_increasing                            # shared step numbers across arms, rising
    assert all(g["order"].is_unique and g["order"].is_monotonic_increasing for _, g in rows.groupby("arm"))
    assert (rows[(rows.arm == PH.TREATMENT_ARM) & (rows.record_type == "conditional_projection")].origin == "user_assumption").all()
    d = effect(25.0).as_dict()
    assert d["unit"] == "percent of soil tPAH concentration" and d["basis"] == PH.DEFAULT_BASIS and d["measured"] is False
