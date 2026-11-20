"""Session 3 of docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md: rate_continuation/1 arithmetic, outputs and figures.

Expected values are written out by hand from the protocol's time convention (calendar decimal years). 2016 is a leap year and
5 October 2016 is day 279, so its decimal year is 2016 + 278/366. Software checks only; not scientific validation.
    python -m pytest -q tests/test_projections_rate.py
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import (  # noqa: E402
    OutputExistsError, SpecError, check_scope, from_dict, normalized, run)
from src.shoreline_remediation.projections import projection as P  # noqa: E402
from src.shoreline_remediation.projections import runner as R  # noqa: E402
from src.shoreline_remediation.projections.__main__ import main  # noqa: E402

EX = ROOT / "examples" / "projections"
A = 2016 + 278 / 366                      # 5 Oct 2016
ANCHOR = dt.date(2016, 10, 5)
OBSERVED_FINAL = 12.125645               # protocol table, 6 decimals


def spec_dict(rate=1.43, end="2030-01-01", cadence="annual", change=None, second=None, **kw) -> dict:
    d = json.loads((EX / "bay_jimmy_retreat_2030.json").read_text(encoding="utf-8"))
    d.update(end_date=end, cadence=cadence, **kw)
    d["assumptions"] = [{"assumption_id": "retreat_rate", "value": rate, "unit": "m/yr", "origin": "user_assumption",
                         "source": "test"}]
    if change:
        d["assumptions"] += [
            {"assumption_id": "rate_change_date", "value": change, "unit": "date", "origin": "user_assumption", "source": "test"},
            {"assumption_id": "changed_retreat_rate", "value": second, "unit": "m/yr", "origin": "user_assumption", "source": "test"}]
    return d


def table(anchor_value=OBSERVED_FINAL, **kw) -> pd.DataFrame:
    return P.project(from_dict(spec_dict(**kw)), ANCHOR, anchor_value, 9)[0]


def at(t: pd.DataFrame, date: str) -> float:
    return float(t.loc[t.date == date, "additional_retreat_since_anchor_m"].iloc[0])


# ---- arithmetic against hand calculations -------------------------------------------------------------------------

def test_anchor_is_exactly_zero_additional_and_the_observed_value():
    t = table(anchor_value=12.12564494664146)
    assert t.date.iloc[0] == "2016-10-05" and t.record_type.iloc[0] == "observed_anchor"
    assert t.additional_retreat_since_anchor_m.iloc[0] == 0.0
    assert t.cumulative_retreat_since_origin_m.iloc[0] == 12.12564494664146     # exact, not approximate


def test_zero_rate_is_flat():
    t = table(rate=0.0)
    assert (t.additional_retreat_since_anchor_m == 0.0).all()
    assert (t.cumulative_retreat_since_origin_m == OBSERVED_FINAL).all()


def test_fixed_rate_matches_hand_calculation():
    t = table(rate=2.0)
    assert at(t, "2017-01-01") == pytest.approx(2.0 * (88 / 366), abs=1e-12)
    assert at(t, "2030-01-01") == pytest.approx(2.0 * (13 + 88 / 366), abs=1e-12)
    assert t.cumulative_retreat_since_origin_m.iloc[-1] == pytest.approx(OBSERVED_FINAL + 2.0 * (13 + 88 / 366), abs=1e-12)


def test_two_equal_rates_equal_one_fixed_rate():
    fixed = table(rate=1.7, end="2040-01-01")
    split = table(rate=1.7, end="2040-01-01", change="2025-07-01", second=1.7)
    merged = split[split.date.isin(fixed.date)]
    assert list(merged.date) == list(fixed.date)
    assert merged.additional_retreat_since_anchor_m.values == pytest.approx(fixed.additional_retreat_since_anchor_m.values, abs=1e-12)


def test_change_date_between_samples_integrates_each_rate_for_its_duration():
    t = table(rate=1.0, end="2030-01-01", change="2025-07-01", second=3.0)
    c = 2025 + 181 / 365                                      # 1 July 2025 (2025 is not a leap year)
    assert "2025-07-01" in set(t.date) and t.loc[t.date == "2025-07-01", "sample"].iloc[0] == "rate_change"
    assert at(t, "2025-01-01") == pytest.approx(1.0 * (2025 - A), abs=1e-12)
    assert at(t, "2025-07-01") == pytest.approx(1.0 * (c - A), abs=1e-12)               # continuous join
    assert at(t, "2026-01-01") == pytest.approx(1.0 * (c - A) + 3.0 * (2026 - c), abs=1e-12)
    assert at(t, "2030-01-01") == pytest.approx(1.0 * (c - A) + 3.0 * (2030 - c), abs=1e-12)
    rates = t.set_index("date").rate_in_effect_m_per_yr
    assert rates["2025-07-01"] == 1.0 and rates["2026-01-01"] == 3.0


def test_requested_end_date_between_samples_is_included_exactly():
    t = table(rate=2.0, end="2030-06-15")
    e = 2030 + 165 / 365
    assert t.date.iloc[-1] == "2030-06-15" and t["sample"].iloc[-1] == "end_date"
    assert at(t, "2030-06-15") == pytest.approx(2.0 * (e - A), abs=1e-12)
    assert "2030-01-01" in set(t.date)


@pytest.mark.parametrize("kw", [dict(rate=1.43), dict(rate=1.0, change="2027-08-20", second=2.5, end="2050-03-17")])
def test_cadence_cannot_change_any_shared_value(kw):
    tabs = {c: table(cadence=c, **kw).set_index("date") for c in ("annual", "quarterly", "monthly")}
    shared = set(tabs["annual"].index)
    assert shared <= set(tabs["quarterly"].index) <= set(tabs["monthly"].index)
    for c in ("quarterly", "monthly"):
        for col in ("additional_retreat_since_anchor_m", "cumulative_retreat_since_origin_m"):
            assert tabs[c].loc[sorted(shared), col].values == pytest.approx(tabs["annual"].loc[sorted(shared), col].values, abs=1e-12)
    assert len(tabs["monthly"]) > len(tabs["quarterly"]) > len(tabs["annual"])


def test_sample_dates_are_first_of_period_plus_anchor_change_and_end():
    d = P.sample_dates(ANCHOR, dt.date(2018, 3, 10), "quarterly", (dt.date(2017, 5, 20),))
    assert [x.isoformat() for x in d] == ["2016-10-05", "2017-01-01", "2017-04-01", "2017-05-20", "2017-07-01", "2017-10-01",
                                          "2018-01-01", "2018-03-10"]


# ---- input checks for the model -----------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, words", [
    (lambda: {**spec_dict(), "assumptions": []}, "needs 'retreat_rate'"),
    (lambda: {**spec_dict(), "assumptions": spec_dict(change="2025-01-01", second=2.0)["assumptions"][:2]}, "together"),
    (lambda: spec_dict(change="2015-01-01", second=2.0), "must lie after as_of"),
    (lambda: spec_dict(change="2031-01-01", second=2.0), "before end_date"),
    (lambda: {**spec_dict(), "model_version": "observed_record/1"}, "not used by observed_record/1"),
])
def test_model_input_errors_are_actionable(raw, words):
    with pytest.raises(SpecError) as e:
        check_scope(from_dict(raw()))
    assert any(words in m for _, m in e.value.problems), e.value.problems


def test_missing_rate_is_an_explicit_abstention_not_a_zero():
    d = spec_dict()
    d["assumptions"][0].update(value=None, missing_reason="owner has not chosen a rate")
    u = check_scope(from_dict(d))
    assert u.code == "rate_not_available" and "owner has not chosen a rate" in u.reason


@pytest.mark.parametrize("habitat", ["rocky_shore", "mangrove"])
def test_rocky_and_mangrove_projections_remain_unsupported(habitat, tmp_path):
    res = run(spec_dict(habitat=habitat), tmp_path / habitat)
    assert res.status == "unsupported" and res.unsupported.code == "habitat_unsupported"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["input.json", "manifest.json"]


def test_no_observation_before_as_of_abstains(tmp_path):
    res = run(spec_dict(as_of="2010-06-01"), tmp_path / "early")
    assert res.status == "unsupported" and res.unsupported.code == "no_anchor_observation"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["input.json", "manifest.json"]


# ---- runner outputs -----------------------------------------------------------------------------------------------

def test_example_2030_run_outputs_and_hand_checked_endpoint(tmp_path):
    res = run(EX / "bay_jimmy_retreat_2030.json", tmp_path / "r")
    assert res.status == "completed"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["input.json", "manifest.json", "observed.csv", "projection.csv",
                                                               "projection.png", "projection.svg"]
    m = res.manifest["projection"]
    obs = R.observed_record(from_dict(res.manifest["spec"]))
    assert m["anchor"]["date"] == "2016-10-05" and m["anchor"]["cumulative_retreat_m"] == float(obs.value.iloc[-1])
    assert m["rates"] == [{"assumption_id": "retreat_rate", "rate": 1.43, "unit": "m/yr", "origin": "fitted_parameter",
                           "source": json.loads((EX / "bay_jimmy_retreat_2030.json").read_text())["assumptions"][0]["source"],
                           "applies_from": "2016-10-05", "applies_to": "2030-01-01"}]
    expected_add = 1.43 * (13 + 88 / 366)
    assert m["end"]["additional_retreat_since_anchor_m"] == pytest.approx(expected_add, abs=1e-9)
    assert m["end"]["cumulative_retreat_since_origin_m"] == pytest.approx(m["anchor"]["cumulative_retreat_m"] + expected_add, abs=1e-9)
    assert "18.933825" in m["arithmetic"] and "31.059470" in m["arithmetic"]
    t = pd.read_csv(res.output_dir / "projection.csv")
    assert t.additional_retreat_since_anchor_m.iloc[0] == 0.0
    assert t.cumulative_retreat_since_origin_m.iloc[0] == pytest.approx(OBSERVED_FINAL, abs=5e-7)
    assert (t.record_type.iloc[1:] == "conditional_projection").all() and (t.unit == "m").all()


def test_example_2050_changed_rate_endpoint(tmp_path):
    res = run(EX / "bay_jimmy_retreat_2050_changed_rate.json", tmp_path / "r")
    end = res.manifest["projection"]["end"]
    add = 1.43 * (13 + 88 / 366) + 2.19 * 20
    assert end["date"] == "2050-01-01" and end["additional_retreat_since_anchor_m"] == pytest.approx(add, abs=1e-9)
    assert [r["assumption_id"] for r in res.manifest["projection"]["rates"]] == ["retreat_rate", "changed_retreat_rate"]
    assert "43.800000" in res.manifest["projection"]["arithmetic"] and "74.859470" in res.manifest["projection"]["arithmetic"]


def test_earlier_as_of_anchors_on_the_last_available_survey(tmp_path):
    res = run(spec_dict(as_of="2013-09-08"), tmp_path / "r")
    a = res.manifest["projection"]["anchor"]
    assert a["date"] == "2013-09-08" and a["cumulative_retreat_m"] == pytest.approx(7.223314, abs=5e-7)


def test_projection_runs_are_reproducible_including_figures(tmp_path):
    a = run(EX / "bay_jimmy_retreat_2050_changed_rate.json", tmp_path / "a")
    b = run(EX / "bay_jimmy_retreat_2050_changed_rate.json", tmp_path / "b")
    assert normalized(a.manifest) == normalized(b.manifest)
    for name in ("projection.csv", "projection.png", "projection.svg"):
        assert (a.output_dir / name).read_bytes() == (b.output_dir / name).read_bytes(), name


def test_figure_identifies_site_group_unit_and_conditional_status(tmp_path):
    res = run(EX / "bay_jimmy_retreat_2050_changed_rate.json", tmp_path / "r")
    svg = (res.output_dir / "projection.svg").read_text(encoding="utf-8")
    for words in ("Bay Jimmy field plots", "untreated, heavily oiled plots, n = 9", "Cumulative shoreline retreat (m)",
                  "Conditional projection", "Not a forecast", "5 Oct 2016: last survey", "extrapolation starts",
                  "1.43 m/yr (fitted parameter) to 2030-01-01, then 2.19 m/yr", "rate changes", "74.86 m on 1 Jan 2050",
                  "7 survey dates"):
        assert words in svg, words


def test_no_recommendation_is_assigned_anywhere(tmp_path):
    res = run(EX / "bay_jimmy_retreat_2030.json", tmp_path / "r")

    def keys(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from keys(v)
        elif isinstance(x, list):
            for v in x:
                yield from keys(v)
    assert not [k for k in keys(res.manifest) if "recommend" in k.lower() or "rank" in k.lower()]
    cols = pd.read_csv(res.output_dir / "projection.csv").columns
    assert not [c for c in cols if "recommend" in c.lower() or "rank" in c.lower()]


def test_compare_overlays_two_runs_and_refuses_to_overwrite(tmp_path):
    a = run(EX / "bay_jimmy_retreat_2030.json", tmp_path / "a").output_dir
    b = run(EX / "bay_jimmy_retreat_2050_changed_rate.json", tmp_path / "b").output_dir
    assert main(["compare", "--runs", str(a), str(b), "--output", str(tmp_path / "fig" / "sens")]) == 0
    svg = (tmp_path / "fig" / "sens.svg").read_text(encoding="utf-8")
    assert "not a probability band" in svg and (tmp_path / "fig" / "sens.png").exists()
    with pytest.raises(OutputExistsError):
        R.compare([a, b], tmp_path / "fig" / "sens")
    early = run(spec_dict(as_of="2013-09-08"), tmp_path / "early").output_dir
    with pytest.raises(ValueError, match="anchor"):
        R.compare([a, early], tmp_path / "fig2" / "x")
    obs_only = run(EX / "bay_jimmy_observed.json", tmp_path / "obs").output_dir
    with pytest.raises(ValueError, match="not a completed projection"):
        R.compare([a, obs_only], tmp_path / "fig3" / "x")
