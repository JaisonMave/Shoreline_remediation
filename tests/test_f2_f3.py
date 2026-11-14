"""F2 (D16) and F3 (D15, D20): knowledge tables equivalence, provenance, model interface and registry.

The equivalence oracles below are frozen copies of the ORIGINAL fast_engine._classify_treatment and
decision_framework._ecological_score / ecological_score_explanation, written before the move so the
table-driven engine can be proved identical to them. Run from the repository root:

    python -m pytest tests/test_f2_f3.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import knowledge  # noqa: E402
from src.shoreline_remediation import registry as reg  # noqa: E402
from src.shoreline_remediation.data_model import Scenario, TREATMENT_LIBRARY  # noqa: E402
from src.shoreline_remediation.decision_framework import HybridDecisionModel  # noqa: E402
from src.shoreline_remediation.expert_scoring import build_scoring_sheet  # noqa: E402
from src.shoreline_remediation.fast_engine import FASTRuleEngine  # noqa: E402
from src.shoreline_remediation.model_interface import (STATES, SCOPES, Prediction, ScenarioRequest,  # noqa: E402
                                                       SiteRecord, STATE_EXPERIMENTAL, STATE_VALIDATED)
from src.shoreline_remediation.site_evidence import FEATURES  # noqa: E402


# --------------------------------------------------------------------------------------------------------------
# Frozen oracles (the original code, before the move to data/knowledge/tables/)

def classify_oracle(treatment: str, scenario: Scenario) -> str:
    shoreline = scenario.shoreline_type.lower()
    oil = scenario.oil_category.lower()
    coverage = scenario.oil_coverage
    penetration = scenario.penetration_depth_cm
    exposure = scenario.wave_exposure.lower()
    sensitivity = scenario.shoreline_sensitivity.lower()
    if shoreline in {"marsh", "mudflat", "peat", "tundra"}:
        if treatment in {"manual_removal", "passive_sorbents"}:
            return "eligible"
        if treatment in {"high_pressure_washing", "high_pressure_heated_washing", "low_pressure_heated_flushing",
                         "mechanical_removal", "sediment_mixing"}:
            return "ineligible"
        if treatment in {"low_pressure_flushing", "surface_washing_agents", "vacuum_removal"}:
            return "conditional"
    if shoreline in {"sand_beach", "mixed_sediment"}:
        if treatment in {"manual_removal", "vacuum_removal", "low_pressure_flushing", "passive_sorbents"}:
            return "eligible"
        if treatment in {"mechanical_removal", "sediment_relocation", "sediment_mixing"}:
            return "conditional"
        if treatment in {"vegetation_cutting"}:
            return "conditional"
    if shoreline in {"bedrock", "boulder", "cobble"}:
        if treatment in {"manual_removal", "passive_sorbents", "surface_washing_agents", "vacuum_removal"}:
            return "eligible"
    if treatment == "natural_attenuation":
        if coverage < 30 and penetration < 8:
            return "eligible"
        if exposure in {"high", "very_high"} and oil == "light" and penetration < 8:
            return "eligible"
        return "conditional"
    if treatment in {"manual_removal", "vacuum_removal"}:
        if scenario.surface_oil and coverage < 80:
            return "eligible"
        return "conditional"
    if treatment in {"low_pressure_flushing", "low_pressure_heated_flushing"}:
        if scenario.surface_oil and penetration < 12 and exposure not in {"high", "very_high"}:
            return "eligible"
        return "conditional"
    if treatment in {"high_pressure_washing", "high_pressure_heated_washing"}:
        hard_or_gravel = shoreline in {"bedrock", "boulder", "cobble"} or (
            shoreline == "mixed_sediment" and scenario.substrate_permeability == "high")
        if hard_or_gravel and coverage > 40 and penetration < 5:
            return "eligible"
        return "ineligible" if not hard_or_gravel else "conditional"
    if treatment in {"surface_washing_agents", "solidifiers"}:
        if oil in {"heavy", "solid"} and coverage < 70:
            return "conditional"
        return "ineligible"
    if treatment == "mechanical_removal":
        if shoreline in {"sand_beach", "mixed_sediment"} and coverage > 50:
            return "conditional"
        if shoreline in {"marsh", "mudflat"}:
            return "ineligible"
        return "conditional"
    if treatment == "sediment_relocation":
        if shoreline in {"sand_beach", "mixed_sediment"} and exposure in {"moderate", "high"}:
            return "conditional"
        return "ineligible"
    if treatment == "sediment_mixing":
        if shoreline in {"sand_beach", "mixed_sediment"} and penetration > 5:
            return "conditional"
        return "ineligible"
    if treatment == "bioremediation":
        if shoreline in {"marsh", "mudflat", "mixed_sediment"} and oil in {"medium", "heavy"} and scenario.accessibility == "good":
            return "conditional"
        return "conditional"
    if treatment == "vegetation_cutting":
        if shoreline in {"marsh", "tundra"} and sensitivity in {"high", "very_high"}:
            return "conditional"
        return "ineligible"
    return "conditional"


def ecological_oracle(treatment: str, scenario: Scenario) -> dict:
    shoreline = scenario.shoreline_type.lower()
    sensitivity = scenario.shoreline_sensitivity.lower()
    if treatment == "natural_attenuation":
        if shoreline in {"marsh", "mudflat"} and sensitivity in {"high", "very_high"}:
            return {"score": 8.5, "basis": "Low-disturbance treatment aligned with sensitive wetland recovery."}
        return {"score": 7.0, "basis": "Generally low-disturbance treatment with good ecological compatibility."}
    if treatment == "bioremediation":
        return {"score": 6.0, "basis": "Potentially low physical disturbance, but effectiveness depends on nutrient, oxygen, access, and monitoring evidence; NOAA notes limited evidence for bioaugmentation."}
    if treatment in {"manual_removal", "vacuum_removal", "mechanical_removal"}:
        if shoreline in {"marsh", "mudflat", "tundra"}:
            return {"score": 3.0, "basis": "Physical removal can disturb soft sediment, vegetation, or sensitive habitat."}
        return {"score": 6.0, "basis": "Physical removal is more compatible with firm or accessible shorelines."}
    if treatment in {"high_pressure_washing", "high_pressure_heated_washing", "sediment_mixing"}:
        if shoreline in {"bedrock", "boulder", "cobble"} and treatment != "sediment_mixing":
            score = 4.5 if treatment == "high_pressure_washing" else 3.0
            return {"score": score, "basis": "Pressure washing is an accepted method on hard substrates; heated washing scores lower because hot-water-washed sites initially declined more than unwashed ones."}
        return {"score": 2.0, "basis": "High disturbance or redistribution risk for sediment and residual oil."}
    if treatment in {"low_pressure_flushing", "surface_washing_agents", "low_pressure_heated_flushing"}:
        return {"score": 4.5, "basis": "Moderate disturbance and potential residue or mobilization concerns."}
    if treatment in {"vegetation_cutting", "sediment_relocation"}:
        if shoreline in {"marsh", "tundra"}:
            return {"score": 2.5, "basis": "Vegetation or sediment disturbance is poorly suited to sensitive habitats."}
        return {"score": 4.0, "basis": "Moderate habitat and sediment disturbance risk."}
    if treatment == "passive_sorbents":
        return {"score": 6.5, "basis": "Low-contact recovery option with limited substrate disturbance."}
    return {"score": 5.0, "basis": "Neutral ecological baseline because no treatment-specific rule was triggered."}


# --------------------------------------------------------------------------------------------------------------
# Grids

SHORELINES = ["marsh", "mudflat", "peat", "tundra", "sand_beach", "mixed_sediment", "bedrock", "boulder", "cobble"]
OILS = ["light", "medium", "heavy", "solid"]
COVERAGES = [5, 20, 35, 50, 80]
PENETRATIONS = [0, 3, 6, 10, 30]
EXPOSURES = ["low", "moderate", "high", "very_high"]
SENSITIVITIES = ["low", "moderate", "high", "very_high"]
PERMEABILITIES = ["low", "moderate", "high"]
ACCESSIBILITIES = ["good", "poor"]


def dense_grid():
    for i, (sh, oil, cov, pen, exp, sen, surf) in enumerate(itertools.product(
            SHORELINES, OILS, COVERAGES, PENETRATIONS, EXPOSURES, SENSITIVITIES, [True, False])):
        yield Scenario(shoreline_type=sh, oil_category=oil, oil_coverage=cov, penetration_depth_cm=pen,
                       wave_exposure=exp, shoreline_sensitivity=sen, surface_oil=surf,
                       substrate_permeability=PERMEABILITIES[i % 3], accessibility=ACCESSIBILITIES[i % 2])


def scoring_scenarios():
    fields = set(Scenario.__dataclass_fields__)
    return [Scenario(**{k: v for k, v in row.items() if k in fields})
            for _, row in build_scoring_sheet().iterrows()]


# --------------------------------------------------------------------------------------------------------------
# F2: equivalence of the move

def test_screening_verdicts_identical_before_and_after_move():
    engine = FASTRuleEngine()
    bad = []
    for scenario in dense_grid():
        for treatment in TREATMENT_LIBRARY:
            if engine._classify_treatment(treatment, scenario) != classify_oracle(treatment, scenario):
                bad.append((treatment, scenario))
    assert not bad, f"{len(bad)} screening verdicts changed, e.g. {bad[:3]}"


def test_screening_verdicts_identical_on_blind_scoring_scenarios():
    engine = FASTRuleEngine()
    for scenario in scoring_scenarios():
        for treatment in TREATMENT_LIBRARY:
            assert engine._classify_treatment(treatment, scenario) == classify_oracle(treatment, scenario)


def test_ecological_scores_identical_before_and_after_move():
    model = HybridDecisionModel()
    scenarios = list(scoring_scenarios())
    scenarios += [Scenario(shoreline_type=sh, shoreline_sensitivity=sen)
                  for sh in SHORELINES for sen in SENSITIVITIES]
    for scenario in scenarios:
        for treatment in TREATMENT_LIBRARY:
            oracle = ecological_oracle(treatment, scenario)
            assert model._ecological_score(treatment, scenario) == oracle["score"]
            assert model.ecological_score_explanation(treatment, scenario) == oracle


def test_full_ranking_unchanged_for_the_blind_scenarios():
    """Belt and braces: the whole screening result (every treatment's tier) is identical on the 30 scenarios."""
    engine = FASTRuleEngine()
    for scenario in scoring_scenarios():
        table = engine.evaluate_feasibility(scenario)
        assert table == {t: classify_oracle(t, scenario) for t in TREATMENT_LIBRARY}


# --------------------------------------------------------------------------------------------------------------
# F2: every table row has a source and a status

@pytest.mark.parametrize("path", knowledge.all_table_paths(), ids=lambda p: p.name)
def test_every_table_row_has_source_and_status(path):
    df = pd.read_csv(path)
    for column in ("source", "status"):
        assert column in df.columns, f"{path.name} lacks a {column} column"
        blank = df[column].isna() | (df[column].astype(str).str.strip() == "")
        assert not blank.any(), f"{path.name} rows without {column}: {list(df.loc[blank].index)}"


def test_loader_rejects_a_row_without_provenance(tmp_path):
    good = pd.read_csv(knowledge.SCREENING_RULE_CSV)
    bad = good.copy()
    bad.loc[0, "status"] = ""
    bad_path = tmp_path / "screening_rule.csv"
    bad.to_csv(bad_path, index=False)
    with pytest.raises(ValueError, match="status"):
        knowledge._load_rules(bad_path, "verdict")


def test_evidence_effect_table_records_zengel_priors_with_design_n_period():
    df = knowledge.load_evidence_effects()
    for column in ("technology", "outcome", "period", "effect", "lo90", "hi90", "n", "design", "source"):
        assert column in df.columns
    manual = df[(df.technology == "manual_removal") & (df.period == "2010-2012")].iloc[0]
    assert manual.effect == pytest.approx(-0.6347, abs=1e-3) and "Zengel" in manual.source


# --------------------------------------------------------------------------------------------------------------
# F3: model interface and registry

@pytest.fixture(scope="module")
def worked_site():
    sites = pd.read_csv(ROOT / "data" / "demo" / "p5_sites.csv", dtype={"cell": str})
    row = sites[sites.cell == "8018_32612"].iloc[0]
    return SiteRecord(site_id="8018_32612", habitat="10A", region="barataria", lat=float(row.lat),
                      lon=float(row.lon), oiling="Heavy",
                      fields={**{f: float(row[f]) for f in FEATURES}, "status": "in_scope", "max_oiling": "Heavy"})


@pytest.fixture(scope="module")
def mangrove_site():
    return SiteRecord(site_id="galeta-like", habitat="mangrove", region="Caribbean", oiling="oiled",
                      fields={"outcome": "root_documented_dead_share", "oiled": 1, "year_since_spill": 2})


def test_every_registered_model_returns_a_prediction_with_interval_and_scope(worked_site, mangrove_site):
    scenario = ScenarioRequest(treatment=None, horizon_years=5)
    assert reg.model_ids()  # non-empty registry
    for model in reg.list():
        site = mangrove_site if model.model_id == "mangrove_damage_v1" else worked_site
        prediction = model.predict(site, scenario)
        assert isinstance(prediction, Prediction)
        assert prediction.interval_lo <= prediction.value <= prediction.interval_hi
        assert prediction.interval_hi > prediction.interval_lo
        assert 0 < prediction.interval_level < 1
        assert prediction.scope in SCOPES
        assert prediction.state in STATES
        assert prediction.model_id == model.model_id and prediction.model_version
        assert prediction.evidence_grade and isinstance(prediction.explanation, dict)


def test_registry_exposes_only_validated_models_to_the_orchestration_layer():
    validated = {m.model_id for m in reg.validated_only()}
    assert validated == {m.model_id for m in reg.list(state=STATE_VALIDATED)}
    assert "edge_loss_v1" in validated and "pah_decline_v1" in validated
    assert "composer_natural_recovery_v1" not in validated
    assert all(m.state == STATE_EXPERIMENTAL for m in reg.list(state=STATE_EXPERIMENTAL))
    assert set(reg.model_ids()) == {m.model_id for m in reg.list()}


def test_promotion_gate_reads_card_fields():
    edge = reg.get("edge_loss_v1")
    passes, reasons = reg.meets_promotion_criteria(edge.card)
    assert passes and not reasons
    veg = reg.get("veg_recovery_v1")
    passes, reasons = reg.meets_promotion_criteria(veg.card)
    assert not passes and any("baseline" in r for r in reasons)  # suggestive: did not beat the baseline


def test_composer_passes_generic_gate_but_declared_experimental_keeps_it_experimental():
    composer = reg.get("composer_natural_recovery_v1")
    passes, _ = reg.meets_promotion_criteria(composer.card)
    assert passes                                   # the clean-edge card meets the generic D20 criteria
    assert composer.declared_state == STATE_EXPERIMENTAL and composer.state == STATE_EXPERIMENTAL


def test_edge_loss_prediction_matches_the_underlying_model(worked_site):
    from src.shoreline_remediation import site_evidence as se
    prediction = reg.get("edge_loss_v1").predict(worked_site, ScenarioRequest(horizon_years=5))
    direct = se.predict_edge_loss({f: worked_site.fields[f] for f in FEATURES})
    assert prediction.value == pytest.approx(direct["rate"])
    assert prediction.interval_lo == pytest.approx(direct["lo"])
    assert prediction.scope == "in range"
