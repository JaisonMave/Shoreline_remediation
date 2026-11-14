"""F9 decision pipeline (D17, D31): fixed steps, constraints, do-no-harm, classes, scope tiers, determinism.

Run from the repository root:  python -m pytest tests/test_f9_pipeline.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import site_evidence as se  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402

CELL = "8018_32612"
HEAVY_COVERAGE = 80.0


@pytest.fixture(scope="module")
def sites():
    return se.load_sites()


@pytest.fixture(scope="module")
def worked_cell(sites):
    return sites[sites.cell == CELL].iloc[0].to_dict()


@pytest.fixture(scope="module")
def timed_marsh(worked_cell):
    start = time.perf_counter()
    report = dp.run_decision(worked_cell)
    return report, time.perf_counter() - start


@pytest.fixture(scope="module")
def marsh(timed_marsh):
    return timed_marsh[0]


@pytest.fixture(scope="module")
def rocky():
    return dp.run_decision(Scenario(shoreline_type="bedrock", oil_category="heavy", oil_coverage=HEAVY_COVERAGE,
                                    penetration_depth_cm=2.0))


@pytest.fixture(scope="module")
def sand():
    return dp.run_decision(Scenario(shoreline_type="sand_beach", oil_category="medium", oil_coverage=60.0))


@pytest.fixture(scope="module")
def mangrove():
    return dp.run_decision(Scenario(shoreline_type="mangrove", oil_category="medium", oil_coverage=60.0), habitat="mangrove")


def test_trace_has_the_eight_steps_in_order(marsh, rocky, sand, mangrove):
    for report in (marsh, rocky, sand, mangrove):
        assert [t["step"] for t in report.trace] == list(range(1, 9))
        assert [t["name"] for t in report.trace] == list(dp.STEP_NAMES)
        for t in report.trace:
            assert {"inputs", "outputs", "sources"} <= set(t)


def test_excluded_options_never_appear_in_classes_a_to_d(marsh, rocky, sand, mangrove):
    for report in (marsh, rocky, sand, mangrove):
        for row in report.options:
            excluded = row["rule_verdict"] == "ineligible" or row["do_no_harm"] == "removed"
            if row["option"] == dp.NATURAL:
                continue
            assert (row["recommendation_class"] == "E") == excluded, row["option"]
            if excluded:
                assert row["exclusion_reasons"], row["option"]


def test_natural_recovery_is_always_present_as_class_c(marsh, rocky, sand, mangrove):
    for report in (marsh, rocky, sand, mangrove):
        assert report.classes()["C"] == [dp.NATURAL]
        assert report.natural_recovery["option"] == dp.NATURAL


def test_class_order_and_ranks(marsh):
    order = [r["recommendation_class"] for r in marsh.options]
    assert order == sorted(order)
    a = [r for r in marsh.options if r["recommendation_class"] == "A"]
    assert [r["rank_in_class"] for r in a] == list(range(1, len(a) + 1))
    edge = [r["benefit_lower_bound"] for r in a if r["benefit_lower_bound_unit"].startswith("edge loss")]
    assert edge == sorted(edge, reverse=True)


def test_heavy_marsh_worked_cell_puts_planting_in_class_a_with_an_interval(marsh):
    assert marsh.scope_tier == "validated"
    planting = marsh.option(dp.PLANTING)
    assert planting["recommendation_class"] == "A"
    point = next(o for o in planting["benefit_outcomes"] if o["decision_point"] and o["outcome"] == "edge_loss_avoided_m")
    assert point["direction"] == "benefit" and point["year"] == 8
    assert 0 < point["lo90"] <= point["median"] <= point["hi90"]
    assert planting["model_id"] == "composer_natural_recovery_v1" and planting["model_state"] == "experimental"
    assert marsh.option("manual_removal")["recommendation_class"] == "A"
    assert marsh.option("mechanical_removal")["recommendation_class"] == "E"
    assert "planting" in marsh.headline


def test_marsh_cell_reference_numbers_come_from_registered_models(marsh):
    ref = {r["quantity"]: r for r in marsh.natural_recovery["reference"]}
    pah = ref["PAH-sum half-life (heavy)"]
    assert pah["model_id"] == "pah_decline_v1" and pah["state"] == "validated"
    assert (pah["lo90"], pah["value"], pah["hi90"]) == (1.25, 1.61, 2.38)
    veg = ref["vegetation time to 80% of reference cover"]
    assert veg["state"] == "experimental" and "worse than" in veg["note"]
    edge = ref["natural recovery cumulative edge loss to year 8"]
    assert edge["lo90"] < edge["value"] < edge["hi90"] and edge["model_id"] == "composer_natural_recovery_v1"
    assert marsh.plots["cumulative_edge_loss"]["series"]


def test_season_decides_the_vegetation_cutting_condition(worked_cell):
    summer = dp.run_decision(worked_cell, season="summer").option("vegetation_cutting")
    winter = dp.run_decision(worked_cell, season="winter").option("vegetation_cutting")
    # AI-proposed condition rows are advisory notes, never a class D flag (14 Nov 2026)
    assert summer["recommendation_class"] == "B" and not summer["harm_flags"]
    assert any("Growing season" in n and "AI-proposed, not reviewed by an expert" in n for n in summer["advisory_notes"])
    assert winter["recommendation_class"] == "B" and not winter["harm_flags"]


def test_moderate_marsh_cell_is_experimental_and_has_no_field_benefit(sites):
    cell = sites[(sites.status == "in_scope") & (sites.max_oiling == "Moderate")].iloc[0].to_dict()
    report = dp.run_decision(cell)
    assert report.scope_tier == "experimental"
    assert report.classes()["A"] == []
    assert report.headline.startswith(("No clear difference from natural recovery (evidence exists)",
                                       "Insufficient evidence to compare with natural recovery"))
    assert report.evidence_state in {"no_clear_difference", "insufficient_evidence"}


def test_hot_water_washing_on_rocky_shore_is_a_sourced_noaa_rule_not_a_pooled_verdict(rocky):
    assert rocky.scope_tier == "rules_and_literature"
    row = rocky.option("high_pressure_heated_washing")
    # exposed rocky shore (ESI 1A), heavy oil = NOAA IV: rated C -> conditional, flag shown, option stays (D36, Proposed)
    assert row["habitat_rating"]["rating"] == "C" and row["rule_verdict"] == "conditional"
    assert row["do_no_harm"] == "flagged" and row["recommendation_class"] == "D"
    assert any("NOAA" in f["source"] and "p.14" in f["detail"] for f in row["harm_flags"])
    assert dp.NATURAL not in rocky.classes()["E"]
    assert rocky.plots["cumulative_edge_loss"]["series"] == []
    assert rocky.natural_recovery["reference"][0]["status"] == "no model"


def test_sheltered_rocky_shore_excludes_hot_water_with_the_noaa_source_cited():
    r = dp.run_decision(Scenario(shoreline_type="bedrock", oil_category="heavy", oil_coverage=80.0, penetration_depth_cm=2.0,
                                 wave_exposure="low"))
    row = r.option("high_pressure_heated_washing")
    assert r.characterisation["esi_code"] == "8A" and row["recommendation_class"] == "E"
    assert any("NOAA" in e["source"] and "p.42" in e["detail"] and "D" in e["detail"] for e in row["exclusion_reasons"])


def test_sand_beach_is_rules_and_literature_only(sand):
    assert sand.scope_tier == "rules_and_literature" and "not integrated" in sand.scope_message
    row = sand.option("high_pressure_heated_washing")
    assert row["recommendation_class"] == "E"
    sources = [r["source"] for r in row["exclusion_reasons"]]
    assert "rule" in sources and any("NOAA" in x for x in sources)   # rule and NOAA table (not applicable on sand, p.23) both cited
    assert sand.option(dp.PLANTING)["recommendation_class"] == "E"
    assert sand.version["models_used"] == []
    assert sand.headline.startswith(("No clear difference from natural recovery (evidence exists)",
                                     "Insufficient evidence to compare with natural recovery"))


def test_beach_persistence_hook_returns_none_until_the_data_model_is_integrated():
    assert dp._beach_persistence_reference({"esi": "3A"}) is None


@pytest.mark.parametrize("shoreline,esi", [("sand_beach", "3A"), ("mixed_sediment", "5"), ("gravel_beach", "6A"), ("cobble", "6A")])
def test_beach_screening_and_scope_by_esi(shoreline, esi):
    r = dp.run_decision(Scenario(shoreline_type=shoreline, oil_category="heavy", oil_coverage=60.0, penetration_depth_cm=3.0))
    assert r.characterisation["esi_code"] == esi and r.scope_tier == "rules_and_literature"
    assert r.characterisation["noaa_oil_category"] == "IV"
    hot = r.option("high_pressure_heated_washing")
    assert hot["habitat_rating"]["rating"] == {"3A": "-", "5": "D", "6A": "C"}[esi]
    assert (hot["recommendation_class"] == "E") == (esi in {"3A", "5"})
    assert r.option("manual_removal")["habitat_rating"]["rating"] == {"3A": "A", "5": "B", "6A": "B"}[esi]
    assert bool(r.literature_notes) == (esi in {"5", "6A"})
    assert all(n["label"] == "literature, not a prediction" for n in r.literature_notes)


def test_mixed_sediment_with_high_permeability_no_longer_allows_high_pressure_washing():
    r = dp.run_decision(Scenario(shoreline_type="mixed_sediment", oil_category="medium", oil_coverage=80.0, penetration_depth_cm=2.0,
                                 substrate_permeability="high"))
    assert r.option("high_pressure_washing")["rule_id"] != "hpw_gravel_elig"
    assert r.option("high_pressure_washing")["rule_verdict"] != "eligible"


def test_hot_water_evidence_from_mixed_gravel_is_not_applied_to_fine_sand():
    mixed = dp.run_decision(Scenario(shoreline_type="mixed_sediment", oil_category="heavy", oil_coverage=60.0))
    sand = dp.run_decision(Scenario(shoreline_type="sand_beach", oil_category="heavy", oil_coverage=60.0))
    assert mixed.option("high_pressure_heated_washing")["evidence_state"] == "no_clear_difference"
    assert sand.option("high_pressure_heated_washing")["evidence_state"] == "insufficient_evidence"


def test_evidence_state_separates_insufficient_evidence_from_no_clear_difference(rocky):
    mixed = dp.run_decision(Scenario(shoreline_type="mixed_sediment", oil_category="heavy", oil_coverage=60.0))
    assert mixed.evidence_state == "insufficient_evidence"
    assert mixed.headline.startswith("Insufficient evidence to compare with natural recovery")
    assert all(r["evidence_state"] == "insufficient_evidence" for r in mixed.options if r["recommendation_class"] in {"B", "D"})
    assert rocky.evidence_state == "no_clear_difference"
    assert rocky.headline.startswith("No clear difference from natural recovery (evidence exists)")
    assert set(mixed.classes()) == {"A", "B", "C", "D", "E"}   # class letters are unchanged


def test_planting_label_is_observational_one_site_and_not_randomised(marsh):
    row = marsh.option(dp.PLANTING)
    assert row["recommendation_class"] == "A" and "observational, one site" in row["evidence_design"]
    text = " ".join(row["caveats"])
    assert "not a randomised comparison" in text and "randomised, Zengel" not in text and "presupposes mechanical removal" in text
    assert "observational, one site" in marsh.headline


def test_mangrove_input_never_uses_marsh_models(mangrove, worked_cell):
    assert mangrove.scope_tier == "experimental"
    assert mangrove.version["models_used"] == ["mangrove_damage_v1"]
    assert all(o["model_id"] is None for o in mangrove.options)
    assert mangrove.plots["paired_differences"] == [] and mangrove.plots["cumulative_edge_loss"]["series"] == []
    assert mangrove.option("manual_removal")["recommendation_class"] == "E"
    assert mangrove.option(dp.PLANTING)["recommendation_class"] in {"B", "D"}
    as_site = dp.run_decision(worked_cell, habitat="mangrove")
    assert as_site.version["models_used"] == ["mangrove_damage_v1"]
    assert as_site.classes()["A"] == []


@pytest.mark.parametrize("kwargs", [{"contaminant": "chemical spill"}, {"objective": "cost_optimal"}, {"response_zone": "offshore"}])
def test_out_of_scope_input_returns_the_refusal(kwargs):
    report = dp.run_decision(Scenario(shoreline_type="sand_beach"), **kwargs)
    assert report.scope_tier == "out_of_scope" and report.options == []
    assert report.headline.startswith("Out of scope:") and "outside its scope" in report.headline
    assert [t["step"] for t in report.trace] == list(range(1, 9))


def test_same_seed_gives_identical_reports_and_json_round_trips(worked_cell, marsh):
    again = dp.run_decision(worked_cell)
    a, b = marsh.to_dict(), again.to_dict()
    a.pop("version"), b.pop("version")
    assert a == b
    assert json.loads(marsh.to_json()) == marsh.to_dict()
    assert set(marsh.version) >= {"pipeline_version", "git_commit", "models_used", "seed"}


def test_single_cell_run_is_fast(timed_marsh):
    assert timed_marsh[1] < 5.0


def test_decide_case_uses_the_generic_path_and_refuses_unsourced_cases():
    case = {"Case_ID": "DWH-04", "Shoreline_Type": "Salt marsh, northern Barataria Bay (Spartina, Juncus)",
            "Oiling_Intensity": "Heavily oiled; emulsified oil layer", "Documented_Response": "manual and mechanical raking"}
    report = dp.decide_case(case)
    assert report.characterisation["input_kind"] == "scenario" and report.characterisation["label"] == "DWH-04"
    assert report.scope_tier == "experimental" and report.characterisation["oiling_class"] == "Heavy"
    assert report.characterisation["assumptions"]
    sampled = dp.decide_case({"Case_ID": "EVOS-01", "scenario": Scenario(shoreline_type="bedrock", oil_category="heavy",
                                                                           oil_coverage=60.0, penetration_depth_cm=2.0)})
    assert sampled.option("high_pressure_heated_washing")["recommendation_class"] == "D"   # NOAA 1A rating C: flag, option stays
    unsourced = dp.decide_case({"Case_ID": "PRE-NS", "Shoreline_Type": ""})
    assert unsourced.scope_tier == "out_of_scope" and "NOT_SOURCED" in unsourced.headline
