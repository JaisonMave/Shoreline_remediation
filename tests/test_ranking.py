"""Tests for the treatment ranking. Each one guards a defect found by the validation scripts.

Run from the repository root:  python -m pytest tests
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.data_model import TREATMENT_LIBRARY, Scenario  # noqa: E402
from src.shoreline_remediation.decision_framework import HybridDecisionModel  # noqa: E402
from src.shoreline_remediation.fast_engine import FASTRuleEngine  # noqa: E402


@pytest.fixture(scope="module")
def model() -> HybridDecisionModel:
    trained = HybridDecisionModel()
    trained.train_treatment_models()
    return trained


TIER = {"eligible": 0, "conditional": 1, "ineligible": 2}


def rank_of(model, scenario, treatment) -> int:
    return [score.treatment for score in model.rank_treatments(scenario)].index(treatment) + 1


def test_every_treatment_is_listed_and_unscored_ones_come_last_within_a_tier(model):
    ranked = model.rank_treatments(Scenario("sand_beach", oil_category="heavy"))
    assert sorted(score.treatment for score in ranked) == sorted(TREATMENT_LIBRARY)
    keys = [(TIER[score.feasibility], score.evidence == "none") for score in ranked]
    assert keys == sorted(keys)  # within a feasibility tier, scored treatments first
    for score in ranked:
        assert math.isnan(score.suitability) == (score.evidence == "none")  # no placeholder scores




def test_no_ineligible_treatment_ranks_above_an_allowed_one(model):
    """V4 R1: scored-but-ineligible options used to keep 0.4*E and sort above unscored eligible options."""
    from src.shoreline_remediation.expert_scoring import build_scoring_sheet

    scenarios = [Scenario("sand_beach", oil_category="heavy", oil_coverage=80, oil_thickness=20),
                 Scenario("marsh", shoreline_sensitivity="very_high", oil_category="heavy", oil_coverage=80,
                          oil_thickness=20, substrate_permeability="low")]
    fields = set(Scenario.__dataclass_fields__)
    for _, row in build_scoring_sheet().iterrows():
        scenarios.append(Scenario(**{k: v for k, v in row.items() if k in fields}))
    for scenario in scenarios:
        ranked = model.rank_treatments(scenario)
        tiers = [TIER[score.feasibility] for score in ranked]
        assert tiers == sorted(tiers)
        assert all(score.utility == 0.0 for score in ranked if score.feasibility == "ineligible")


def test_top_choice_depends_on_the_scenario(model):
    """The ranking used to return passive sorbents first for every scenario."""
    scenarios = [
        Scenario("sand_beach", oil_category="heavy", oil_coverage=40, oil_thickness=10),
        Scenario("marsh", shoreline_sensitivity="very_high", oil_category="medium", oil_coverage=15, oil_thickness=2),
        Scenario("marsh", shoreline_sensitivity="very_high", oil_category="heavy", oil_coverage=80, oil_thickness=25),
    ]
    assert len({model.rank_treatments(scenario)[0].treatment for scenario in scenarios}) >= 2


def test_thick_oil_moves_the_ranking_away_from_natural_attenuation(model):
    """Check E3: the Deepwater Horizon marsh endpoints required no thick (> 1 cm) oil."""
    rng = np.random.default_rng(3)
    thin, thick = [], []
    for _ in range(20):
        common = dict(oil_category="heavy", oil_coverage=float(rng.uniform(20, 90)), wave_exposure="low",
                      shoreline_sensitivity=str(rng.choice(["moderate", "high"])))
        thin.append(rank_of(model, Scenario("marsh", oil_thickness=2.0, **common), "natural_attenuation"))
        thick.append(rank_of(model, Scenario("marsh", oil_thickness=25.0, **common), "natural_attenuation"))
    assert np.mean(thick) > np.mean(thin) + 0.25


def test_high_pressure_washing_ranks_better_on_bedrock_than_on_sand(model):
    """Check E5: pressure washing is a method for hard surfaces."""
    common = dict(oil_category="heavy", oil_coverage=70, oil_thickness=10, penetration_depth_cm=0.0)
    on_rock = rank_of(model, Scenario("bedrock", **common), "high_pressure_washing")
    on_sand = rank_of(model, Scenario("sand_beach", **common), "high_pressure_washing")
    assert on_rock < on_sand


def test_feasibility_rules_for_pressure_and_heat():
    engine = FASTRuleEngine()
    marsh = Scenario("marsh", shoreline_sensitivity="very_high", oil_category="heavy", oil_coverage=80)
    assert engine._classify_treatment("low_pressure_heated_flushing", marsh) == "ineligible"
    rock = Scenario("bedrock", oil_category="heavy", oil_coverage=70, penetration_depth_cm=1)
    assert engine._classify_treatment("high_pressure_washing", rock) == "eligible"
    lightly_oiled_rock = Scenario("bedrock", oil_category="heavy", oil_coverage=20, penetration_depth_cm=1)
    assert engine._classify_treatment("high_pressure_washing", lightly_oiled_rock) == "conditional"


def test_expert_agreement_statistics():
    from src.shoreline_remediation.expert_scoring import build_scoring_sheet, combine_expert_scores, icc_absolute_agreement

    # Worked example from Shrout and Fleiss (1979), Table 2: six targets, four judges, ICC(2,1) = 0.29.
    table = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])
    assert icc_absolute_agreement(table) == pytest.approx(0.29, abs=0.005)

    sheet = build_scoring_sheet()
    assert len(sheet) == 30 and sheet["shoreline_type"].nunique() == 8
    assert all(treatment in sheet.columns for treatment in TREATMENT_LIBRARY)

    # Three simulated experts who share a view and differ by small random amounts should agree well.
    rng = np.random.default_rng(0)
    truth = rng.uniform(1, 9, size=(len(sheet), len(TREATMENT_LIBRARY)))
    sheets = {}
    for name in ["a", "b", "c"]:
        filled = sheet.copy()
        filled[TREATMENT_LIBRARY] = np.clip(truth + rng.normal(0, 0.5, truth.shape), 0, 10)
        sheets[name] = filled
    labels, agreement, disputed = combine_expert_scores(sheets)
    assert len(labels) == 30 and agreement["usable_as_labels"].all() and (agreement["icc_2_1"] > 0.8).all()
