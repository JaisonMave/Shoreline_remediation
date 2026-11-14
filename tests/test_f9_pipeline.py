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
    assert summer["recommendation_class"] == "D" and any("Growing season" in f["detail"] for f in summer["harm_flags"])
    assert winter["recommendation_class"] == "B" and not winter["harm_flags"]


def test_moderate_marsh_cell_is_experimental_and_has_no_field_benefit(sites):
    cell = sites[(sites.status == "in_scope") & (sites.max_oiling == "Moderate")].iloc[0].to_dict()
    report = dp.run_decision(cell)
    assert report.scope_tier == "experimental"
    assert report.classes()["A"] == []
    assert report.headline.startswith("No option is shown by evidence to beat natural recovery; monitor")


def test_hot_water_washing_on_rocky_shore_is_removed_by_do_no_harm(rocky):
    assert rocky.scope_tier == "rules_and_literature"
    row = rocky.option("high_pressure_heated_washing")
    assert row["rule_verdict"] == "eligible"  # the rule alone would allow it on hard substrate
    assert row["do_no_harm"] == "removed" and row["recommendation_class"] == "E"
    assert any(r["source"] == "evidence_verdicts.csv" and "Houghton" in r["detail"] for r in row["exclusion_reasons"])
    assert dp.NATURAL not in rocky.classes()["E"]
    assert rocky.plots["cumulative_edge_loss"]["series"] == []
    assert rocky.natural_recovery["reference"][0]["status"] == "no model"


def test_sand_beach_is_rules_and_literature_only(sand):
    assert sand.scope_tier == "rules_and_literature"
    assert sand.option("high_pressure_heated_washing")["recommendation_class"] == "E"
    sources = {r["source"] for r in sand.option("high_pressure_heated_washing")["exclusion_reasons"]}
    assert sources == {"rule", "evidence_verdicts.csv"}  # rule and do-no-harm both cited
    assert sand.option(dp.PLANTING)["recommendation_class"] == "E"
    assert sand.version["models_used"] == []
    assert sand.headline.startswith("No option is shown by evidence to beat natural recovery; monitor")


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
    assert sampled.option("high_pressure_heated_washing")["recommendation_class"] == "E"
    unsourced = dp.decide_case({"Case_ID": "PRE-NS", "Shoreline_Type": ""})
    assert unsourced.scope_tier == "out_of_scope" and "NOT_SOURCED" in unsourced.headline
