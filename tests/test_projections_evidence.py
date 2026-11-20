"""Session 4 of docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md: historical evidence exports (vegetation, tPAH, DIVER index, contrasts).

Software checks of the exports' content and provenance; not scientific validation.
    python -m pytest -q tests/test_projections_evidence.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.projections import SpecError, check_scope, from_dict, run  # noqa: E402
from src.shoreline_remediation.projections import catalogue as C  # noqa: E402
from src.shoreline_remediation.projections.__main__ import main  # noqa: E402

EX = ROOT / "examples" / "projections"


def ex(name: str, **changes) -> dict:
    d = json.loads((EX / name).read_text(encoding="utf-8"))
    d.update(changes)
    return d


def csv(res, name: str) -> pd.DataFrame:
    return pd.read_csv(res.output_dir / name)


# ---- year-2 vegetation contrast: 52% (5 manual plots) vs 18% (9 untreated) -> +34 points, 90% Welch +19 to +49 ----------

def test_year2_vegetation_contrast_regression(tmp_path):
    res = run(EX / "bay_jimmy_veg_contrast_year2.json", tmp_path / "c")
    assert res.status == "completed"
    assert sorted(p.name for p in res.output_dir.iterdir()) == ["contrast.csv", "input.json", "manifest.json"]
    c = csv(res, "contrast.csv").set_index("record_type")
    means = c.loc["observed_group_mean"].set_index("plot_group_id")
    assert means.loc["manual_removal_heavy", "value"] == 52.0 and means.loc["manual_removal_heavy", "n_plots"] == 5
    assert means.loc["untreated_heavy", "value"] == 18.0 and means.loc["untreated_heavy", "n_plots"] == 9
    assert means.loc["manual_removal_heavy", "plots"] == "11, 17, 20, 21, 22"
    k = c.loc["field_contrast"]
    # independent hand calculation of the Welch interval from the S1 means, standard errors and n
    se = math.sqrt(7.0 ** 2 + 3.0 ** 2)
    df = se ** 4 / ((7.0 ** 2) ** 2 / 4 + (3.0 ** 2) ** 2 / 8)
    h = stats.t.ppf(0.95, df) * se
    assert k.value == 34.0 and k.unit == "percentage points"
    assert k.interval_lo == pytest.approx(34 - h, abs=1e-6) and k.interval_hi == pytest.approx(34 + h, abs=1e-6)
    assert round(k.interval_lo) == 19 and round(k.interval_hi) == 49 and k.interval_level == 0.9
    assert k.n_plots == 5 and k.n_comparator == 9 and k.comparator_group_id == "untreated_heavy"
    assert k.survey_period == "September 2012" and k.time.startswith("year 2")
    assert "Welch" in k.interval_method and k.design.startswith("observational")
    assert "Zengel et al. 2015" in k.source and k.evidence_id == "zengel2015_s1_group_means"
    assert "not an annual benefit" in k.applies_to and "not a projection" in k.applies_to
    m = res.manifest["contrast"]
    assert (m["treated_mean"], m["comparator_mean"], m["difference"]) == (52.0, 18.0, 34.0)
    assert m["reads"].startswith("comparison.vegetation_year2_estimates")


def test_contrast_reuses_the_dashboard_comparison_layer_values(tmp_path):
    from src.shoreline_remediation import comparison as CMP
    est = next(e for e in CMP.vegetation_year2_estimates() if e.option == "mechanical_removal")
    res = run(ex("bay_jimmy_veg_contrast_year2.json", plot_group_id="mechanical_removal_heavy"), tmp_path / "m")
    k = csv(res, "contrast.csv").set_index("record_type").loc["field_contrast"]
    assert (k.value, k.interval_lo, k.interval_hi) == pytest.approx((est.estimate, est.lo, est.hi))


def test_contrast_respects_as_of(tmp_path):
    res = run(ex("bay_jimmy_veg_contrast_year2.json", as_of="2012-09-15", end_date="2013-01-01"), tmp_path / "early")
    assert res.status == "unsupported" and res.unsupported.code == "not_available_at_as_of"
    assert not (res.output_dir / "contrast.csv").exists()


def test_contrast_input_rules():
    assert check_scope(from_dict(ex("bay_jimmy_veg_contrast_year2.json", plot_group_id="unoiled_reference", arm="reference",
                                    oiling_class="NOO"))).code == "no_field_contrast"
    with pytest.raises(SpecError, match="comparator_group_id"):
        check_scope(from_dict(ex("bay_jimmy_veg_contrast_year2.json", comparator_group_id="")))
    with pytest.raises(SpecError, match="only used by field_contrast"):
        check_scope(from_dict(ex("bay_jimmy_veg_manual_fit.json", comparator_group_id="untreated_heavy")))


# ---- vegetation observations and fits -----------------------------------------------------------------------------

def test_vegetation_observations_keep_their_survey_dates(tmp_path):
    res = run(ex("bay_jimmy_veg_manual_fit.json", model_version="observed_record/1"), tmp_path / "m")
    o = csv(res, "observed.csv")
    assert list(o.date) == ["2011-09", "2012-09"] and (o.n_plots == 5).all()      # manual observations end in 2012
    assert o.value.tolist() == pytest.approx([22.0, 52.0], abs=0.6)              # S1 Table means, same plots
    u = csv(run(ex("bay_jimmy_veg_manual_fit.json", model_version="observed_record/1", plot_group_id="untreated_heavy",
                   arm="reference"), tmp_path / "u"), "observed.csv")
    assert list(u.date) == [f"{y}-09" for y in range(2011, 2017)]
    assert u.date_basis.str.startswith("verified").tolist() == [True, True, False, False, False, False]
    assert ((u.interval_lo >= 0) & (u.interval_hi <= 100)).all() and (u.record_class == "observation").all()


def test_manual_fit_borrows_the_untreated_rate_and_says_when(tmp_path):
    res = run(EX / "bay_jimmy_veg_manual_fit.json", tmp_path / "f")
    f = csv(res, "fit.csv")
    assert (f[f.decimal_year <= 2012.70 + 1e-9].record_type == "experimental_fit").all()
    after = f[f.decimal_year > 2012.70 + 1e-9]
    assert len(after) > 0 and (after.record_type == "conditional_projection").all()
    assert (after.status_label.str.contains("IF this group followed the untreated recovery rate")).all()
    assert (f.rate_origin == "borrowed from untreated_heavy fit").all()
    assert (f.borrowing_begins == "2012-09 (last survey of this group)").all()
    assert f.decimal_year.max() == pytest.approx(2016.70)                       # nothing beyond the last untreated survey
    b = res.manifest["fit"]["borrowing"]
    assert b["parameter"] == "r" and b["from_group"] == "untreated_heavy" and b["status"] == "conditional_projection"
    assert b["begins"].startswith("2012-09")
    unt = run(ex("bay_jimmy_veg_manual_fit.json", plot_group_id="untreated_heavy", arm="reference"), tmp_path / "u")
    ru = {p["name"]: p["value"] for p in unt.manifest["fit"]["parameters"]}
    rm = {p["name"]: p["value"] for p in res.manifest["fit"]["parameters"]}
    assert rm["r"] == ru["r"] and b["value"] == ru["r"]
    # reproduces the documented full-record fits (docs/V5_4_RECOVERY_VIEW.md): r 1.20, t50 2013.8; manual t50 2012.6; K 93.6
    assert ru["r"] == pytest.approx(1.20, abs=0.01) and ru["t50"] == pytest.approx(2013.8, abs=0.05)
    assert rm["t50"] == pytest.approx(2012.6, abs=0.05) and ru["K"] == pytest.approx(93.6, abs=0.05)
    assert (csv(unt, "fit.csv").record_type == "experimental_fit").all() and unt.manifest["fit"]["borrowing"] is None


def test_fit_uses_only_surveys_available_at_as_of(tmp_path):
    res = run(ex("bay_jimmy_veg_manual_fit.json", plot_group_id="untreated_heavy", arm="reference", as_of="2014-06-01"),
              tmp_path / "a")
    assert res.manifest["fit"]["data_used"]["untreated_survey_years"] == [2011, 2012, 2013]
    assert csv(res, "fit.csv").decimal_year.max() == pytest.approx(2013.70)
    o = csv(res, "observed.csv")
    assert o.available_at_as_of.tolist() == [True, True, True, False, False, False]
    early = run(ex("bay_jimmy_veg_manual_fit.json", as_of="2013-01-01"), tmp_path / "b")
    assert early.status == "unsupported" and early.unsupported.code == "insufficient_surveys_for_fit"
    assert sorted(p.name for p in early.output_dir.iterdir()) == ["input.json", "manifest.json", "observed.csv"]


def test_reference_plots_have_no_recovery_fit():
    u = check_scope(from_dict(ex("bay_jimmy_veg_manual_fit.json", plot_group_id="unoiled_reference", arm="reference",
                                 oiling_class="NOO")))
    assert u.code == "model_not_applicable_to_group"


# ---- soil tPAH and the DIVER index --------------------------------------------------------------------------------

def test_tpah_measurements_carry_units_depth_analyte_and_dates(tmp_path):
    res = run(EX / "bay_jimmy_tpah_observed.json", tmp_path / "t")
    o = csv(res, "observed.csv")
    assert o.value.tolist() == [260.0, 112.0] and (o.n_plots == 9).all() and (o.unit == "mg/kg").all()
    assert o.survey_period.tolist() == ["July-August 2011", "September 2012"] and o.date.tolist() == ["2011-07/08", "2012-09"]
    assert (o.sampling_depth == "0-10 cm cores, surface oil scraped aside").all()
    assert o.analyte.str.contains("43 to 45 compounds").all() and o.analyte.str.contains("basis not recorded").all()
    mech = csv(run(ex("bay_jimmy_tpah_observed.json", plot_group_id="mechanical_removal_heavy", arm="intervention"),
                   tmp_path / "m"), "observed.csv")
    assert mech.date.tolist() == ["2012-09"]                                     # mechanical plots were not sampled in 2011


def test_diver_index_has_its_own_reference_class_and_support(tmp_path):
    res = run(EX / "bay_jimmy_tpah_observed.json", tmp_path / "t")
    i = csv(res, "reference_index.csv")
    assert i.value.iloc[0] == 100.0 and (i.reference_value == 100.0).all() and i.value.is_monotonic_decreasing
    assert (i.unit == "index (first campaign = 100)").all() and (i.oiling_class == "heavy (SCAT)").all()
    assert (i.record_type == "model_reference_index").all() and (i.record_class == "model_reference").all()
    assert i.decimal_year.min() == pytest.approx(2011.34, abs=0.01) and i.decimal_year.max() == pytest.approx(2013.78, abs=0.01)
    assert i.analyte.str.contains("PAH sum").all() and (i.model == "pah_decline_v1").all()
    blk = res.manifest["reference_index"]
    assert blk["exported"] and blk["k_per_year"] == pytest.approx(0.430, abs=1e-3) and blk["n_stations_2plus_campaigns"] == 36
    assert "not on the tPAH axis" in blk["not_a_plot_measurement"]


def test_diver_index_respects_as_of_and_oiling_class(tmp_path):
    res = run(ex("bay_jimmy_tpah_observed.json", as_of="2012-10-15", end_date="2013-01-01"), tmp_path / "early")
    assert not (res.output_dir / "reference_index.csv").exists()
    assert "withheld" in res.manifest["reference_index"]["reason"]
    assert csv(res, "observed.csv").available_at_as_of.tolist() == [True, True]
    ref = run(ex("bay_jimmy_tpah_observed.json", plot_group_id="unoiled_reference", oiling_class="NOO"), tmp_path / "ref")
    assert not (ref.output_dir / "reference_index.csv").exists() and "heavy class only" in ref.manifest["reference_index"]["reason"]
    assert csv(ref, "observed.csv").value.tolist() == [0.08, 1.5]


def test_treatment_specific_future_pah_is_an_evidence_gap_with_measurements_kept(tmp_path):
    out = tmp_path / "gap"
    assert main(["run", "--scenario", str(EX / "bay_jimmy_tpah_manual_future_unsupported.json"), "--output", str(out)]) == 3
    m = json.loads((out / "manifest.json").read_text())
    assert m["status"] == "unsupported" and m["outcome"]["code"] == "evidence_gap"
    assert "three or more dates" in m["outcome"]["reason"] and "no treatment variable" in m["outcome"]["reason"]
    assert m["outcome"]["historical_records_exported"] == ["observed.csv"]
    assert sorted(p.name for p in out.iterdir()) == ["input.json", "manifest.json", "observed.csv"]
    o = pd.read_csv(out / "observed.csv")
    assert o.value.tolist() == [220.0, 101.0] and (o.record_type == "observed_group_mean").all()


@pytest.mark.parametrize("changes, code", [
    (dict(endpoint="total_vegetation_cover", unit="percent", model_version="rate_continuation/1",
          evidence_ids=["zengel2022_griidc_vegetation", "zengel2022_griidc_field_positions"]), "evidence_gap"),
    (dict(endpoint="cumulative_shoreline_retreat", unit="m", model_version="field_contrast/1",
          evidence_ids=["zengel2022_griidc_field_positions"], comparator_group_id="untreated_heavy"), "evidence_gap"),
])
def test_other_evidence_gaps_still_export_observations(changes, code, tmp_path):
    res = run(ex("bay_jimmy_tpah_manual_future_unsupported.json", **changes), tmp_path / "g")
    assert res.status == "unsupported" and res.unsupported.code == code
    assert (res.output_dir / "observed.csv").exists() and not (res.output_dir / "projection.csv").exists()


# ---- one vocabulary across every export; compatibility -------------------------------------------------------------

def test_every_export_uses_the_record_vocabulary_and_cites_sources(tmp_path):
    names = ["bay_jimmy_observed.json", "bay_jimmy_retreat_2030.json", "bay_jimmy_veg_contrast_year2.json",
             "bay_jimmy_veg_manual_fit.json", "bay_jimmy_tpah_observed.json", "bay_jimmy_tpah_manual_future_unsupported.json"]
    seen = set()
    for i, n in enumerate(names):
        res = run(EX / n, tmp_path / str(i))
        for p in res.output_dir.glob("*.csv"):
            d = pd.read_csv(p)
            assert {"record_type", "record_class"} <= set(d.columns), p
            assert all(C.RECORD_TYPES[t] == c for t, c in zip(d.record_type, d.record_class)), p
            seen |= set(d.record_class)
            if "evidence_id" in d:
                assert set(d.evidence_id) <= set(C.EVIDENCE), p
            if p.name != "projection.csv" and n != "bay_jimmy_observed.json" and n != "bay_jimmy_retreat_2030.json":
                assert (d.shared_plots == C.SHARED_PLOTS_NOTE).all(), p
        for rt, cls in res.manifest.get("record_types", {}).items():
            assert C.RECORD_TYPES[rt] == cls and cls in res.manifest["record_class_meaning"]
    assert seen == {"observation", "derived_field_contrast", "experimental_fit", "conditional_projection", "model_reference"}


def test_retreat_examples_are_compatible(tmp_path):
    obs = run(EX / "bay_jimmy_observed.json", tmp_path / "o")
    assert sorted(p.name for p in obs.output_dir.iterdir()) == ["input.json", "manifest.json", "observed.csv"]
    r30 = run(EX / "bay_jimmy_retreat_2030.json", tmp_path / "r")
    assert r30.manifest["run_id"] == "8dd6de47e97a8527"        # unchanged spec, unchanged run ID (Session 3 replay)
    assert r30.manifest["projection"]["end"]["cumulative_retreat_since_origin_m"] == pytest.approx(31.059470, abs=1e-6)
    assert "comparator_group_id" not in r30.manifest["spec"]


def test_changed_rate_example_labels_2_19_as_the_fitted_constant_slope():
    a = json.loads((EX / "bay_jimmy_retreat_2050_changed_rate.json").read_text(encoding="utf-8"))
    second = next(x for x in a["assumptions"] if x["assumption_id"] == "changed_retreat_rate")
    assert second["value"] == 2.19
    assert "full-period fitted constant slope" in second["source"] and "2.08 m/yr" in second["source"]
    assert "average" not in a["description"]
