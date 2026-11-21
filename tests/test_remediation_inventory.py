"""Technique-by-endpoint inventory (docs/CLAUDE_REMEDIATION_SCENARIOS_PLAN.md section 1).

The committed Bay Jimmy report is the worked fixture; the live run_decision() report is the source of eligibility and is reconciled
against it. Scientific content is tested here without Streamlit.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.shoreline_remediation import comparison as K
from src.shoreline_remediation.projections import catalogue as C, inventory as I

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "projection_baseline"
ENDPOINTS = ("total_vegetation_cover", "soil_tpah", "cumulative_shoreline_retreat")
PLANTING = "planting (after mechanical cleanup)"
FIXTURE_CATEGORIES = {   # the plan's table for the saved Bay Jimmy case
    "natural_recovery_monitoring": {"natural_attenuation"},
    "recommended": {"manual_removal"},
    "conditional": {PLANTING},
    "no_demonstrated_benefit": {"low_pressure_flushing", "surface_washing_agents", "vegetation_cutting"},
    "insufficient_evidence": {"passive_sorbents", "bioremediation", "vacuum_removal"},
    "excluded": {"solidifiers", "low_pressure_heated_flushing", "mechanical_removal", "sediment_relocation",
                 "high_pressure_heated_washing", "high_pressure_washing", "sediment_mixing"},
}


def _load(name: str) -> dict:
    return json.loads((BASE / f"{name}.report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixture_report():
    return _load("bay_jimmy_mapped")


@pytest.fixture(scope="module")
def inv(fixture_report):
    return I.build_inventory(fixture_report)


@pytest.fixture(scope="module")
def live_report():
    from src.shoreline_remediation.decision_pipeline import run_decision
    from src.shoreline_remediation.site_evidence import load_sites
    s = load_sites()
    row = s[s.cell == "8018_32612"].iloc[0].to_dict()
    return run_decision({k: v for k, v in row.items() if v == v}, habitat="salt_marsh", oil="light", season=None, n_draws=500)


# ---- coverage ------------------------------------------------------------------------------------------------------

def test_fixture_enumerates_16_options_by_3_endpoints(inv, fixture_report):
    assert inv.in_scope and inv.site_id == "bay_jimmy_zengel_plots"
    assert len(inv.rows) == 48 and len({(r.option, r.endpoint) for r in inv.rows}) == 48
    assert inv.options == [o["option"] for o in fixture_report["options"]]
    assert all(tuple(r.endpoint for r in inv.rows if r.option == o) == ENDPOINTS for o in inv.options)
    for e in ENDPOINTS:
        assert inv.reference(e).option == "natural_attenuation"
        assert inv.reference(e).comparator == I.REFERENCE_COMPARATOR and not inv.reference(e).what_if_allowed


def test_fixture_categories_match_the_plan_table(inv):
    got = {}
    for c in inv.coverage():
        got.setdefault(c["category"], set()).add(c["option"])
    assert got == FIXTURE_CATEGORIES


def test_coverage_table_of_the_fixture(inv):
    cov = {c["option"]: (c["total_vegetation_cover"], c["soil_tpah"], c["cumulative_shoreline_retreat"]) for c in inv.coverage()}
    assert cov["natural_attenuation"] == ("observed", "observed", "observed")
    assert cov["manual_removal"] == ("observed_and_contrast", "observed", "observed")
    assert cov["mechanical_removal"] == ("observed_and_contrast", "observed", "context_only")
    assert cov[PLANTING] == ("context_only", "evidence_gap", "context_only")
    others = set(cov) - {"natural_attenuation", "manual_removal", "mechanical_removal", PLANTING}
    assert len(others) == 12 and all(cov[o] == ("evidence_gap",) * 3 for o in others)


def test_report_fields_are_copied_verbatim_and_report_is_unchanged(fixture_report):
    before = copy.deepcopy(fixture_report)
    inv = I.build_inventory(fixture_report)
    assert fixture_report == before
    for o in fixture_report["options"]:
        for e in ENDPOINTS:
            r = inv.cell(o["option"], e)
            assert r.category == o["recommendation_category"] and r.rule_verdict == o["rule_verdict"]
            assert r.rule_id == o["rule_id"] and r.do_no_harm == o["do_no_harm"]
            assert r.conditions == tuple(o["conditions"]) and r.harm_flags == tuple(o["harm_flags"])
            assert r.report_source_ids == tuple(o["source_ids"]) and r.category_reason == o["recommendation_category_reason"]
            assert r.exclusion_reasons == tuple(x["detail"] for x in o["exclusion_reasons"])
            assert (r.conditions_state, r.conditions_detail) == K.conditions_state(o)


# ---- worked rows -----------------------------------------------------------------------------------------------------

def test_manual_removal_cells(inv):
    veg = inv.cell("manual_removal", "total_vegetation_cover")
    assert veg.admissible_outputs == ("observed_group_mean", "experimental_fit", "field_contrast")
    assert veg.comparator == "untreated oiled plots" and veg.comparison_status == ""
    contrast = next(s for s in veg.support if s.record_type == "field_contrast")
    est = next(e for e in K.vegetation_year2_estimates() if e.option == "manual_removal")
    assert est.estimate == pytest.approx(34.0) and "+34.0 percentage points" in contrast.description
    assert "+19.0 to +49.0" in contrast.description and contrast.n_plots == (5, 9) and "not randomly assigned" in contrast.note
    obs = next(s for s in veg.support if s.record_type == "observed_group_mean")
    assert obs.dates == ("2011-09", "2012-09") and obs.n_plots == (5, 5)
    assert veg.unavailable_reason.startswith(C.VEG_FUTURE_GAP[:40])

    pah = inv.cell("manual_removal", "soil_tpah")
    assert pah.admissible_outputs == ("observed_group_mean",) and pah.availability == "observed"
    assert pah.support[0].dates == ("2011-07/08", "2012-09") and pah.support[0].n_plots == (5, 5)
    assert C.PAH_TREATMENT_GAP in pah.unavailable_reason and "no matched contrast" in pah.comparator

    ret = inv.cell("manual_removal", "cumulative_shoreline_retreat")
    assert ret.admissible_outputs == ("observed_group_mean",)
    assert [s.on_endpoint for s in ret.support] == [True, False, False]       # erosion-rate contrasts are context (m/yr)
    assert all("different endpoint" in s.note for s in ret.support[1:])
    assert ret.what_if_allowed and "trampling" in ret.what_if_reason and len(ret.unresolved_conditions) == 1


def test_reference_rows_admit_their_existing_outputs(inv):
    assert inv.reference("total_vegetation_cover").admissible_outputs == ("observed_group_mean", "experimental_fit")
    assert inv.reference("soil_tpah").admissible_outputs == ("observed_group_mean", "model_reference_index")
    assert inv.reference("soil_tpah").support[0].n_plots == (9, 9)
    assert inv.reference("cumulative_shoreline_retreat").admissible_outputs == ("observed_group_mean", "conditional_projection")


def test_planting_shows_its_excluded_prerequisite(inv):
    for e in ENDPOINTS:
        r = inv.cell(PLANTING, e)
        assert r.prerequisites == ("mechanical_removal",) and r.prerequisite_state == "excluded"
        assert not r.what_if_allowed and "independently documented" in r.what_if_reason
        assert "field_contrast" not in r.admissible_outputs
    veg = inv.cell(PLANTING, "total_vegetation_cover")
    assert veg.availability == "context_only" and "Spartina" in veg.support[0].description
    assert "Different outcome" in veg.support[0].note


def test_prerequisites_agree_with_the_decision_pipeline():
    from src.shoreline_remediation import decision_pipeline as dp
    assert {k: v[0] for k, v in I.prerequisites().items()} == dp._PREREQUISITE


def test_excluded_options_are_never_prospective_controls(inv):
    for o in FIXTURE_CATEGORIES["excluded"]:
        for e in ENDPOINTS:
            r = inv.cell(o, e)
            assert not r.what_if_allowed and r.what_if_reason.startswith("Excluded by screening: ")
            assert r.exclusion_reasons and r.exclusion_reasons[0] in r.unavailable_reason
    mech = inv.cell("mechanical_removal", "total_vegetation_cover")
    assert mech.historical_context_only and mech.comparison_status.startswith("Excluded by screening")
    ret = inv.cell("mechanical_removal", "cumulative_shoreline_retreat")
    assert "4 December 2010 origin" in ret.unavailable_reason and ret.admissible_outputs == ()
    assert ret.comparator.startswith("no matched comparator on this endpoint")
    assert not inv.cell("solidifiers", "soil_tpah").historical_context_only


def test_no_benefit_and_insufficient_evidence_give_specific_gaps(inv):
    for o in FIXTURE_CATEGORIES["no_demonstrated_benefit"]:
        for e in ENDPOINTS:
            r = inv.cell(o, e)
            assert r.admissible_outputs == () and I.NO_EFFECT_SIZE in r.unavailable_reason
            assert "Screening rationale" in r.unavailable_reason and I.NEEDED[e] in r.unavailable_reason
    for o in FIXTURE_CATEGORIES["insufficient_evidence"]:
        for e in ENDPOINTS:
            r = inv.cell(o, e)
            assert r.admissible_outputs == () and r.unavailable_reason.startswith("Insufficient evidence")
            assert I.NEEDED[e] in r.unavailable_reason and r.comparator == "none available"


def test_unknown_or_unmet_conditions_are_never_executable(inv):
    for o in ("bioremediation", "low_pressure_flushing", "surface_washing_agents", "vacuum_removal"):
        r = inv.cell(o, "soil_tpah")
        assert r.conditions_state == "unknown" and not r.what_if_allowed and r.conditions
        assert r.what_if_reason.startswith("Conditions not established")
    cut = inv.cell("vegetation_cutting", "soil_tpah")
    assert cut.conditions_state == "unmet" and not cut.what_if_allowed
    sorb = inv.cell("passive_sorbents", "soil_tpah")      # rule-eligible, no conditions, but no evidence: assumptions only
    assert sorb.what_if_allowed and sorb.admissible_outputs == ()


# ---- changed reports -------------------------------------------------------------------------------------------------

def test_a_new_report_option_becomes_an_explicit_evidence_gap(fixture_report):
    rep = copy.deepcopy(fixture_report)
    new = copy.deepcopy(next(o for o in rep["options"] if o["option"] == "passive_sorbents"))
    new.update(option="hypothetical_new_method", source_ids=["screening_rule.csv:new"])
    rep["options"].append(new)
    inv = I.build_inventory(rep)
    assert len(inv.rows) == 51
    for e in ENDPOINTS:
        r = inv.cell("hypothetical_new_method", e)
        assert r.availability == "evidence_gap" and r.admissible_outputs == () and I.NEEDED[e] in r.unavailable_reason


def test_duplicate_options_are_rejected(fixture_report):
    rep = copy.deepcopy(fixture_report)
    rep["options"].append(copy.deepcopy(rep["options"][0]))
    with pytest.raises(ValueError, match="more than once"):
        I.build_inventory(rep)


def test_missing_reference_option_uses_the_natural_recovery_block(fixture_report):
    rep = copy.deepcopy(fixture_report)
    rep["options"] = [o for o in rep["options"] if o["option"] != "natural_attenuation"]
    inv = I.build_inventory(rep)
    assert len(inv.rows) == 48 and inv.notes
    assert inv.reference("soil_tpah").admissible_outputs == ("observed_group_mean", "model_reference_index")


@pytest.mark.parametrize("case,habitat_key", [("rocky_esi_1A", "rocky_shore"), ("mangrove", "mangrove")])
def test_unsupported_habitats_return_their_own_reason(case, habitat_key):
    inv = I.build_inventory(_load(case))
    assert not inv.in_scope and inv.scope_reason == C.UNSUPPORTED_HABITATS[habitat_key]
    assert len(inv.rows) == 48 and all(r.availability == "out_of_scope" and r.admissible_outputs == () for r in inv.rows)
    assert not any(r.what_if_allowed for r in inv.rows)
    assert inv.cell("natural_attenuation", "soil_tpah").role == "reference"


def test_marsh_without_a_linked_field_site_shows_no_site_evidence():
    inv = I.build_inventory(_load("typed_marsh"))
    assert inv.site_id is None and not inv.in_scope and "worked example only" in inv.scope_reason
    assert all(r.support == () for r in inv.rows)


def test_wrong_oiling_class_is_out_of_scope(fixture_report):
    rep = copy.deepcopy(fixture_report)
    rep["characterisation"]["oiling_class"] = "Light"
    inv = I.build_inventory(rep)
    assert not inv.in_scope and "Light" in inv.scope_reason


# ---- live report reconciliation -------------------------------------------------------------------------------------

def test_live_report_reconciles_with_the_fixture(live_report, inv):
    live = I.build_inventory(live_report)       # DecisionReport object, not a dict
    assert live.site_id == "bay_jimmy_zengel_plots"
    assert live.coverage() == inv.coverage()
    for a, b in zip(live.rows, inv.rows):
        assert (a.option, a.endpoint, a.category, a.rule_verdict, a.conditions, a.exclusion_reasons, a.prerequisite_state,
                a.admissible_outputs, a.what_if_allowed, a.unavailable_reason) == \
               (b.option, b.endpoint, b.category, b.rule_verdict, b.conditions, b.exclusion_reasons, b.prerequisite_state,
                b.admissible_outputs, b.what_if_allowed, b.unavailable_reason)


def test_records_are_json_serialisable(inv):
    recs = inv.to_records()
    assert len(recs) == 48 and json.loads(json.dumps(recs)) == recs


def test_inventory_imports_no_ui_or_decision_engine():
    code = ("import sys; import src.shoreline_remediation; before = set(sys.modules); "
            "import src.shoreline_remediation.projections.inventory; added = set(sys.modules) - before; "
            "print(sorted(m for m in added if m.split('.')[-1] in ('scenario_runner', 'decision_framework', 'decision_pipeline', "
            "'dashboard', 'site_view') or m.startswith('streamlit') or m.split('.')[-1].startswith('ui_')))")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]"
