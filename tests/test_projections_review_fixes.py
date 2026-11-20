"""Regression tests for the four pre-commit review findings (written before the fixes; each failed on the reviewed code).

1. A segment oiled before the request window must not get a first-arrival window inside it.
2. A window containing only partial_clear visits is inconclusive, not 'no oil observed'.
3. Figures for an as_of before the final survey must not present later surveys as available observations.
4. Plot IDs are exported only where the source establishes membership for that survey and endpoint.
    python -m pytest -q tests/test_projections_review_fixes.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import run  # noqa: E402
from src.shoreline_remediation.projections.runner import compare  # noqa: E402

EX = ROOT / "examples" / "projections"


def ex(name: str, **changes) -> dict:
    d = json.loads((EX / name).read_text(encoding="utf-8"))
    d.update(changes)
    return d


# ---- 1. previously oiled segments ----------------------------------------------------------------------------------

def test_segment_oiled_before_the_window_has_no_first_arrival_window(tmp_path):
    res = run(ex("dwh_mobile_exposure_hindcast.json", as_of="2010-07-01"), tmp_path / "jul")
    d = pd.read_csv(res.output_dir / "survey_contact.csv").set_index("segment")
    a = d.loc["ALBA1-001"]
    assert a.survey_class == "oiled_before_window"
    assert a.prior_oiled_observation == "2010-06-04"                 # the documented 4 June observation is retained
    assert pd.isna(a.window_start) and pd.isna(a.window_end) and pd.isna(a.window_days)
    assert a.n_visits == 5 and a.first_visit == "2010-07-06"          # July/August surveys still reported as in-window
    s = res.manifest["exposure"]["survey_summary"]["survey_class_counts"]
    assert s["oiled_before_window"] == int((d.survey_class == "oiled_before_window").sum()) > 0
    # no segment with oil before the window may carry an arrival window
    assert d[d.survey_class == "oiled_before_window"].window_start.isna().all()


def test_arrival_windows_with_a_later_start_use_the_full_survey_record(tmp_path):
    """Adjacent to finding 1: with a start after the release, a first-arrival window must begin at the last clear visit in the
    whole record (which may precede as_of), or at the release start if the segment was never surveyed clear before its first oil."""
    res = run(ex("dwh_mobile_exposure_hindcast.json", as_of="2010-07-01"), tmp_path / "jul")
    d = pd.read_csv(res.output_dir / "survey_contact.csv")
    v = pd.read_csv(ROOT / "data" / "external" / "scat_dwh_mobile" / "beach_visits.csv", parse_dates=["date"])
    arrivals = d[d.survey_class.isin(["clear_then_oiled", "oiled_at_first_visit"])]
    assert len(arrivals) > 0
    for r in arrivals.itertuples():
        before = v[(v.segment == r.segment) & (v.date < pd.Timestamp(r.window_end)) & (v.status == "clear")]
        if r.survey_class == "clear_then_oiled":
            assert r.window_start == before.date.max().date().isoformat()
        else:
            assert before.empty and r.window_start == "2010-04-20"
    assert (d[d.survey_class == "clear_then_oiled"].window_start < "2010-07-01").any()   # windows can straddle as_of


# ---- 2. partial-clear visits -----------------------------------------------------------------------------------------

def test_window_with_only_partial_clear_visits_is_inconclusive(tmp_path):
    res = run(ex("dwh_mobile_exposure_hindcast.json", as_of="2010-08-12"), tmp_path / "aug")
    d = pd.read_csv(res.output_dir / "survey_contact.csv").set_index("segment")
    f = d.loc["FLGU1-135"]
    assert f.survey_class == "inconclusive_partial_clear" and f.n_visits == 1 and f.n_clear_visits == 0
    s = res.manifest["exposure"]["survey_summary"]
    noo = d[d.survey_class == "no_oil_observed"]
    assert "FLGU1-135" not in noo.index and (noo.n_clear_visits >= 1).all()
    assert s["survey_class_counts"]["inconclusive_partial_clear"] == int((d.survey_class == "inconclusive_partial_clear").sum())
    assert s["survey_class_counts"]["no_oil_observed"] == len(noo)


# ---- 3. historical cutoff figures ------------------------------------------------------------------------------------

def test_figures_with_an_earlier_as_of_separate_later_observations(tmp_path):
    early = run(ex("bay_jimmy_retreat_2030.json", as_of="2013-09-08"), tmp_path / "early")
    svg = (early.output_dir / "projection.svg").read_text(encoding="utf-8")
    assert "4 survey dates available at as_of" in svg
    assert "Retrospective observations after as_of" in svg and "3 survey dates" in svg
    assert "7 survey dates" not in svg
    other = run(ex("bay_jimmy_retreat_2030.json", as_of="2013-09-08", scenario_id="early_zero",
                   assumptions=[{"assumption_id": "retreat_rate", "value": 0.0, "unit": "m/yr", "origin": "user_assumption",
                                 "source": "test"}]), tmp_path / "early0")
    paths = compare([early.output_dir, other.output_dir], tmp_path / "fig" / "cmp")
    cmp_svg = paths[1].read_text(encoding="utf-8")
    assert "Retrospective observations after as_of" in cmp_svg and "4 survey dates available at as_of" in cmp_svg


# ---- 4b. every source a contrast run reads is in its manifest ---------------------------------------------------------

def test_contrast_manifest_lists_all_three_sources_read(tmp_path):
    import hashlib
    from src.shoreline_remediation.projections import catalogue as C
    res = run(EX / "bay_jimmy_veg_contrast_year2.json", tmp_path / "c")     # existing file, unchanged: still replayable
    assert res.status == "completed" and res.manifest["run_id"] == "1c3e23fab97e18f4"
    src = {s["evidence_id"]: s for s in res.manifest["sources"]}
    assert set(src) == {"zengel2015_s1_group_means", "zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"}
    for eid, s in src.items():
        assert s["present"] and s["sha256"] == hashlib.sha256((ROOT / C.EVIDENCE[eid].path).read_bytes()).hexdigest(), eid
    assert src["zengel2015_s1_group_means"]["cited_in_spec"] is True
    assert src["zengel2022_griidc_vegetation"]["cited_in_spec"] is False and src["zengel2022_griidc_vegetation"]["read_for"]
    assert src["zengel2022_griidc_field_positions"]["cited_in_spec"] is False
    k = pd.read_csv(res.output_dir / "contrast.csv").set_index("record_type").loc["field_contrast"]
    assert k.value == 34.0 and k.interval_lo == pytest.approx(18.962854, abs=1e-6) and k.interval_hi == pytest.approx(49.037146, abs=1e-6)


# ---- 4. mechanical-treatment plot provenance -------------------------------------------------------------------------

def test_tpah_mechanical_rows_do_not_claim_unestablished_plot_ids(tmp_path):
    res = run(ex("bay_jimmy_tpah_observed.json", plot_group_id="mechanical_removal_heavy", arm="intervention"), tmp_path / "t")
    o = pd.read_csv(res.output_dir / "observed.csv").iloc[0]
    assert o.n_plots == 5 and o.value == 178.0
    assert pd.isna(o.plots) and "not established" in o.plot_membership


def test_vegetation_contrast_rows_list_only_surveyed_plots(tmp_path):
    from src.shoreline_remediation import comparison as CMP
    res = run(ex("bay_jimmy_veg_contrast_year2.json", plot_group_id="mechanical_removal_heavy"), tmp_path / "c")
    c = pd.read_csv(res.output_dir / "contrast.csv")
    mean_row = c[(c.record_type == "observed_group_mean") & (c.plot_group_id == "mechanical_removal_heavy")].iloc[0]
    k = c[c.record_type == "field_contrast"].iloc[0]
    expected = "16-17, 17-18, 19-20, 20-21, 22-23"                    # plot-level 2012 records in the GRIIDC dataset
    assert mean_row.plots == expected and mean_row.n_plots == 5 and mean_row.value == 23.0
    assert k.plots == expected and k.n_plots == 5
    for row in (mean_row, k):
        assert "GRIIDC" in row.plot_membership
    est = next(e for e in CMP.vegetation_year2_estimates() if e.option == "mechanical_removal")
    assert (k.value, k.interval_lo, k.interval_hi) == pytest.approx((est.estimate, est.lo, est.hi))   # published values kept
    assert k.n_comparator == 9 and len(k.comparator_plots.split(", ")) == 9
