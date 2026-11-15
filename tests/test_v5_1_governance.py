"""V5.1 Session 1: architecture and scientific-governance checks.

These are software tests of the governance rules (categories, abstention, promotion, provenance, pathway isolation).
Passing them is not scientific validation of any model.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import registry, site_evidence as se  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.model_interface import ScenarioRequest, SiteRecord  # noqa: E402

SRC = ROOT / "src" / "shoreline_remediation"
DRAWS = 400


@pytest.fixture(scope="module")
def heavy_site() -> dict:
    sites = se.load_sites()
    return sites[(sites.max_oiling == "Heavy") & (sites.status == "in_scope")].iloc[0].to_dict()


@pytest.fixture(scope="module")
def marsh_report(heavy_site):
    return dp.run_decision(heavy_site, n_draws=DRAWS)


def _scenario_report(habitat: str):
    return dp.run_decision(Scenario(shoreline_type=habitat), habitat=habitat, n_draws=DRAWS)


# ---------------------------------------------------------------------------------------------------------------
# Recommendation categories (D41)

def test_every_option_has_one_known_category_and_summary_partitions_options(marsh_report):
    names = [o["option"] for o in marsh_report.options]
    for o in marsh_report.options:
        assert o["recommendation_category"] in dp.CATEGORY_ORDER
        assert o["recommendation_category_label"] == dp.CATEGORY_LABELS[o["recommendation_category"]]
        assert o["recommendation_category_rule"] and o["recommendation_category_reason"]
    listed = [x for c in dp.CATEGORY_ORDER for x in marsh_report.recommendation_summary[c]]
    assert sorted(listed) == sorted(names)


def test_category_rules_are_a_pure_function_of_class_state_and_scope():
    assert dp._category("C", "baseline", "validated", [])[0] == dp.CAT_NATURAL
    assert dp._category("E", "harm", "validated", [])[0] == dp.CAT_EXCLUDED
    assert dp._category("A", "benefit", "validated", [])[0] == dp.CAT_RECOMMENDED
    # benefit evidence outside the scope it was gathered in is never an outright recommendation
    assert dp._category("A", "benefit", "experimental", ["generic marsh"])[0] == dp.CAT_CONDITIONAL
    assert dp._category("A", "benefit", "rules_and_literature", [])[0] == dp.CAT_CONDITIONAL
    assert dp._category("A", "benefit", "validated", [], prerequisite_excluded="mechanical_removal")[0] == dp.CAT_CONDITIONAL
    assert dp._category("D", "mixed", "validated", [])[0] == dp.CAT_CONDITIONAL
    assert dp._category("B", dp.STATE_INSUFFICIENT, "validated", [])[0] == dp.CAT_INSUFFICIENT
    assert dp._category("B", dp.STATE_NO_DIFFERENCE, "validated", [])[0] == dp.CAT_NO_BENEFIT


def test_class_letters_are_unchanged_by_the_category_layer(marsh_report):
    for o in marsh_report.options:
        cls, cat = o["recommendation_class"], o["recommendation_category"]
        assert (cls == "E") == (cat == dp.CAT_EXCLUDED)
        assert (cls == "C") == (cat == dp.CAT_NATURAL)
        if cat == dp.CAT_RECOMMENDED:
            assert cls == "A"
        if cls == "B":
            assert cat in (dp.CAT_INSUFFICIENT, dp.CAT_NO_BENEFIT)


def test_planting_is_not_recommended_outright_while_its_prerequisite_is_excluded(marsh_report):
    assert marsh_report.option("mechanical_removal")["recommendation_class"] == "E"
    planting = marsh_report.option(dp.PLANTING)
    assert planting["recommendation_class"] == "A"
    assert planting["recommendation_category"] == dp.CAT_CONDITIONAL
    assert "mechanical_removal" in planting["recommendation_category_reason"]


def test_recommended_option_states_the_design_of_its_evidence(marsh_report):
    assert marsh_report.scope_tier == "validated" and marsh_report.decision_outcome == "intervention_recommended"
    for name in marsh_report.recommendation_summary[dp.CAT_RECOMMENDED]:
        row = marsh_report.option(name)
        assert "one site" in row["recommendation_category_reason"]
        assert row["model_state"] == "experimental"     # the benefit numbers stay labelled experimental


def test_rank_basis_never_presents_an_assumed_order_as_evidence(marsh_report):
    for o in marsh_report.options:
        assert o["rank_basis"] in (dp.RANK_BASIS_EVIDENCE, dp.RANK_BASIS_CONVENTION)
        if o["benefit_lower_bound"] is None:
            assert o["rank_basis"] == dp.RANK_BASIS_CONVENTION
            assert "not a scientific ranking" in o["rank_basis_text"]
    tied = [o for o in marsh_report.options if o["recommendation_class"] == "B"]
    assert len(tied) > 1 and all(o["rank_tied_with"] for o in tied)


# ---------------------------------------------------------------------------------------------------------------
# Abstention: unsupported habitat, limited evidence, missing data, out of scope

@pytest.mark.parametrize("habitat", ["coral_reef", "seagrass_meadow", "not a shoreline"])
def test_unsupported_habitat_abstains_instead_of_screening(habitat):
    r = _scenario_report(habitat)
    assert r.scope_tier == "unsupported_habitat" and r.decision_outcome == "unsupported_habitat"
    assert r.options == [] and r.natural_recovery == {} and r.plots == {}
    assert all(not v for v in r.recommendation_summary.values())
    assert r.abstentions and r.abstentions[0]["kind"] == "unsupported_habitat"
    assert "Unsupported habitat" in r.headline and "salt- to brackish-water marsh" in r.headline
    assert len(r.trace) == 8 and r.trace[1]["outputs"] == {"skipped": "unsupported habitat"}
    json.loads(r.to_json())


def test_mangrove_demonstration_abstains_from_recommending_and_from_marsh_numbers():
    r = _scenario_report("mangrove")
    assert r.scope_tier == "experimental"
    assert r.decision_outcome == "insufficient_evidence"
    assert r.recommendation_summary[dp.CAT_RECOMMENDED] == [] and r.recommendation_summary[dp.CAT_CONDITIONAL] == []
    kinds = {a["kind"] for a in r.abstentions}
    assert {"outside_validated_scope", "no_model", "insufficient_evidence", "no_recommendation"} <= kinds
    assert any("one spill" in a["text"] for a in r.abstentions)
    # no marsh model output is passed off as a mangrove number
    for ref in r.natural_recovery["reference"]:
        if ref.get("model_id") in ("pah_decline_v1", "veg_recovery_v1", "edge_loss_v1", "composer_natural_recovery_v1"):
            pytest.fail(f"marsh model {ref['model_id']} used for mangrove")
        if ref.get("value") is not None:
            assert ref.get("state") == "experimental"


def test_rocky_shore_demonstration_is_screening_only_with_no_numerical_forecast():
    r = _scenario_report("rocky_shore")
    assert r.scope_tier == "rules_and_literature"
    assert r.recommendation_summary[dp.CAT_RECOMMENDED] == []
    assert r.decision_outcome in ("conditional_only", "natural_recovery_monitoring", "insufficient_evidence")
    assert all(ref.get("value") is None for ref in r.natural_recovery["reference"])
    assert all(not o["benefit_outcomes"] and o["model_id"] is None for o in r.options)
    assert "no_site_forecast" in {a["kind"] for a in r.abstentions}
    assert r.version["models_used"] == []


def test_missing_site_input_gives_no_edge_loss_number_and_says_why(heavy_site):
    site = dict(heavy_site)
    site["fetch_mean_m"] = float("nan")
    r = dp.run_decision(site, n_draws=DRAWS)
    assert r.scope_tier == "experimental"
    assert any("missing input" in x for x in r.characterisation["scope_reasons"])
    edge = [x for x in r.natural_recovery["reference"] if "edge loss" in x["quantity"]]
    assert edge and all(x["value"] is None and "missing input" in x["reason"] for x in edge)
    assert r.recommendation_summary[dp.CAT_RECOMMENDED] == []        # nothing is recommended outright on incomplete inputs
    assert any(a["kind"] == "outside_validated_scope" and "missing input" in a["text"] for a in r.abstentions)


def test_site_outside_treatment_evidence_scope_gets_no_recommendation(heavy_site):
    site = dict(heavy_site)
    site["max_oiling"] = "Light"
    r = dp.run_decision(site, n_draws=DRAWS)
    assert r.scope_tier == "experimental"
    assert r.recommendation_summary[dp.CAT_RECOMMENDED] == []
    assert any("heavily oiled marsh only" in a["text"] for a in r.abstentions)


def test_borrowed_salt_marsh_evidence_is_declared_for_other_wetland_types():
    r = _scenario_report("mudflat")
    assert "borrowed_evidence" in {a["kind"] for a in r.abstentions}
    assert "borrowed_evidence" not in {a["kind"] for a in _scenario_report("salt_marsh").abstentions}


def test_out_of_scope_request_is_refused_with_an_outcome():
    r = dp.run_decision(Scenario(shoreline_type="marsh"), contaminant="mercury")
    assert r.scope_tier == "out_of_scope" and r.decision_outcome == "out_of_scope" and r.options == []
    assert r.abstentions[0]["kind"] == "out_of_scope"


def test_trace_records_the_category_rules(marsh_report):
    step7 = marsh_report.trace[6]["outputs"]
    assert step7["decision_outcome"] == marsh_report.decision_outcome
    assert set(step7["category_rules"]) == set(dp.CATEGORY_ORDER)


# ---------------------------------------------------------------------------------------------------------------
# Registry and promotion

def _entries() -> dict:
    spec = json.loads((ROOT / "models" / "registry.json").read_text())
    return {e["model_id"]: e for e in spec["models"] + spec["cards_without_adapter"]}


def test_every_registry_entry_has_a_complete_governance_record():
    for model_id, entry in _entries().items():
        assert registry.governance_gaps(entry.get("governance")) == [], model_id


def test_validated_set_is_unchanged_and_only_models_without_blocking_failures():
    assert {m.model_id for m in registry.validated_only()} == {"edge_loss_v1", "pah_decline_v1"}
    for m in registry.validated_only():
        assert registry.failed_gates(m.governance, blocking_only=True) == []


def test_failed_gates_stay_visible_in_the_governance_table():
    table = {r["model_id"]: r for r in registry.governance_table()}
    assert set(table) == set(_entries())
    expected = {"composer_natural_recovery_v1": {"R3-heavy-bias", "D32-heavy-bias", "V5-0.1"},
                "beach_sand_persistence_v1": {"B-1", "B-2"}, "process_model_v2": {"F5"},
                "oil_excess_oos_v1": {"V5-0.1"}, "edge_loss_v2": {"V5-0.2"}, "veg_recovery_v1": {"A1-validated"},
                "mangrove_damage_v1": {"independent-spill"}}
    for model_id, gates in expected.items():
        row = table[model_id]
        assert row["state"] == "experimental", model_id
        assert gates <= set(row["failed_gates"]), model_id
        assert row["reasons_not_validated"], model_id
    # a validated model still shows the failed interval gate that concerns it
    assert "V5-0.2" in table["edge_loss_v1"]["failed_gates"]
    assert "NOT independently validated" in table["edge_loss_v1"]["interval_status"]


def test_blocking_failed_gate_or_incomplete_record_prevents_promotion():
    entry = _entries()["pah_decline_v1"]
    card = json.loads((ROOT / entry["card"]).read_text())
    gov = entry["governance"]
    assert registry.resolve_state("validated", card, None, gov) == "validated"
    failed = copy.deepcopy(gov)
    failed["gates"].append({"gate_id": "X", "description": "test gate", "passed": False, "blocks_promotion": True, "source": "test"})
    report = registry.promotion_report("validated", card, None, failed)
    assert report["state"] == "experimental" and report["blocking_failed_gates"] == ["X"]
    incomplete = {k: v for k, v in gov.items() if k != "validation_data"}
    assert registry.resolve_state("validated", card, None, incomplete) == "experimental"
    assert registry.resolve_state("validated", card, None, None) == "experimental"       # no governance record at all
    assert registry.resolve_state("experimental", card, None, gov) == "experimental"     # never promoted above its declaration


def test_declaring_a_failed_model_validated_does_not_promote_it():
    for model_id in ("composer_natural_recovery_v1", "veg_recovery_v1", "beach_sand_persistence_v1", "mangrove_damage_v1"):
        entry = _entries()[model_id]
        card = json.loads((ROOT / entry["card"]).read_text())
        assert registry.promotion_report("validated", card, None, entry["governance"])["state"] == "experimental", model_id


def test_process_model_is_registered_as_card_only_and_outside_the_decision_path(marsh_report):
    card = registry.card_only("process_model_v2")
    assert card.state == "experimental" and card.card["decision_path"] is False
    assert "process_model_v2" not in registry.model_ids()
    assert "process_model_v2" not in marsh_report.version["models_used"]


def test_predictions_carry_interval_method_level_status_and_scope(heavy_site):
    site = SiteRecord(site_id="t", habitat="10A", oiling="Heavy", lat=heavy_site["lat"], lon=heavy_site["lon"],
                      fields={**{f: heavy_site[f] for f in se.FEATURES}, "status": "in_scope"})
    for model_id in ("edge_loss_v1", "pah_decline_v1", "veg_recovery_v1", "composer_natural_recovery_v1"):
        pred = registry.get(model_id).predict(site, ScenarioRequest(horizon_years=5))
        assert pred.interval_method and pred.interval_level and pred.scope
        assert pred.interval_status and pred.interval_status != "not recorded", model_id
        assert pred.state == registry.get(model_id).state
        assert "interval_status" in dataclasses.asdict(pred)


# ---------------------------------------------------------------------------------------------------------------
# One authoritative pathway: production modules must not import the legacy decision models

LEGACY_MODULES = {"decision_framework", "fast_engine", "ml_models", "process_model", "scenario_runner", "shoreline_transport",
                  "training_pipeline", "train_models", "run_benchmark", "expert_scoring", "validation_panel"}
PRODUCTION_MODULES = ("site_view", "ui_pipeline", "ui_compare", "ui_components", "ui_evidence", "ui_report", "ui_theme",
                      "decision_pipeline", "registry", "model_interface", "scenario_composer", "site_evidence", "habitat",
                      "knowledge", "beach_model", "treatment_effects")


def _imported_modules(path: Path) -> set:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
        if isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[-1])
            names.update(a.name.split(".")[-1] for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name.split(".")[-1] for a in node.names)
    return names


@pytest.mark.parametrize("module", PRODUCTION_MODULES)
def test_production_modules_do_not_import_legacy_decision_code(module):
    assert not (_imported_modules(SRC / f"{module}.py") & LEGACY_MODULES), module


def test_site_view_reads_recommendations_only_through_ui_pipeline():
    text = (SRC / "site_view.py").read_text()
    assert "HybridDecisionModel" not in text and "rank_treatments" not in text
    assert "P.decision_for_site(" in text and "P.decision_for_scenario(" in text
    bridge = (SRC / "ui_pipeline.py").read_text()
    assert bridge.count("run_decision(") >= 2 and "HybridDecisionModel" not in bridge


def test_legacy_view_is_reached_only_from_the_labelled_legacy_entry():
    importers = [p.stem for p in SRC.glob("*.py") if "ui_scenario" in _imported_modules(p)]
    assert importers == ["dashboard"]
    assert 'VIEW_SCENARIO = "Scenario screening (legacy)"' in (SRC / "dashboard.py").read_text()


# ---------------------------------------------------------------------------------------------------------------
# NOAA provenance

def test_noaa_tables_keep_their_proposed_status_and_the_pipeline_shows_it():
    import pandas as pd
    tables = ROOT / "data" / "knowledge" / "tables"
    for name in ("noaa_response_rating.csv", "noaa_rating_mapping.csv"):
        status = pd.read_csv(tables / name, dtype=str).status
        assert status.str.startswith("Proposed").all(), name
    r = _scenario_report("rocky_shore")
    rated = [o for o in r.options if o["habitat_rating"]]
    assert rated and all("Proposed" in o["habitat_rating"]["source"] for o in rated)


def test_noaa_transcription_matches_the_source_pdf_text():
    from validation import noaa_rating_source_check as check
    if not check.available():
        pytest.skip("NOAA PDF or pdftotext not available")
    res = check.check()
    assert len(res) == 126
    assert (res.result == "match").all(), res[res.result != "match"].to_dict("records")
    assert res.table_title_matches.all()


# ---------------------------------------------------------------------------------------------------------------
# View model and report carry the governance fields

def test_report_view_and_html_report_show_outcome_category_and_abstentions():
    from src.shoreline_remediation import ui_evidence as E, ui_report
    r = _scenario_report("mangrove")
    view = E.report_view(r)
    assert view.decision_outcome == "insufficient_evidence" and view.abstentions
    assert all(o.category_label for o in view.options)
    html = ui_report.build_html(view, title="Mangrove", habitat="mangrove")
    assert "Decision outcome:" in html and "What this report does not state" in html and "<th>Category</th>" in html
    unsupported = E.report_view(_scenario_report("coral_reef"))
    assert unsupported.out_of_scope and unsupported.headline_grade_text == "Unsupported habitat"
