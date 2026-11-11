from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .data_model import Scenario, TreatmentScore, TREATMENT_LIBRARY
from .fast_engine import FASTRuleEngine
from .ml_models import GaussianProcessSuitabilityModel, make_synthetic_dataset


class HybridDecisionModel:
    """Hybrid decision-support framework combining FAST feasibility and ML suitability."""

    def __init__(self):
        self.fast_engine = FASTRuleEngine()
        self.treatment_models = {}
        self._trained = False

    def _build_training_data(self, treatment: str) -> tuple[pd.DataFrame, pd.Series]:
        df = make_synthetic_dataset(n_rows=220)
        features = df[[
            "shoreline_type",
            "oil_category",
            "oil_coverage",
            "oil_thickness",
            "penetration_depth_cm",
            "wave_exposure",
            "shoreline_sensitivity",
            "surface_oil",
        ]]
        target = df[treatment]
        return features, target

    def train_treatment_models(self):
        labelled = set(make_synthetic_dataset(n_rows=1).columns)
        for treatment in TREATMENT_LIBRARY:
            if treatment not in labelled:
                continue  # no labels exist; score_treatment marks these as evidence="none"
            X, y = self._build_training_data(treatment)
            model = GaussianProcessSuitabilityModel()
            model.fit(X, y)
            self.treatment_models[treatment] = model
        self._trained = True

    def score_treatment(self, scenario: Scenario, treatment: str) -> TreatmentScore:
        feasibility = self.fast_engine._classify_treatment(treatment, scenario)

        if not self._trained:
            self.train_treatment_models()

        model = self.treatment_models.get(treatment)
        if model is None:
            # No labels, so no suitability score. A fixed placeholder of 5.0 used to be returned here; because
            # it was higher than most modelled scores, passive sorbents topped the ranking for every scenario.
            ecological_suitability = self._ecological_score(treatment, scenario)
            return TreatmentScore(
                treatment=treatment, feasibility=feasibility, suitability=float("nan"),
                ecological_suitability=ecological_suitability,
                utility=round(0.4 * ecological_suitability if feasibility != "ineligible" else 0.0, 2),
                confidence=0.2,
                reason=f"{treatment}: no suitability evidence yet, so it is listed after the scored treatments; "
                       + self._reason_for_treatment(treatment, scenario, feasibility).split(": ", 1)[1],
                evidence="none",
            )
        else:
            input_df = pd.DataFrame([
                {
                    "shoreline_type": scenario.shoreline_type,
                    "oil_category": scenario.oil_category,
                    "oil_coverage": scenario.oil_coverage,
                    "oil_thickness": scenario.oil_thickness,
                    "penetration_depth_cm": scenario.penetration_depth_cm,
                    "wave_exposure": scenario.wave_exposure,
                    "shoreline_sensitivity": scenario.shoreline_sensitivity,
                    "surface_oil": int(scenario.surface_oil),
                }
            ])
            suitability = float(model.predict(input_df)[0])

        ecological_suitability = self._ecological_score(treatment, scenario)
        utility = self._decision_utility(
            feasibility, suitability, ecological_suitability
        )

        confidence = self._confidence(feasibility, suitability, ecological_suitability)
        reason = self._reason_for_treatment(treatment, scenario, feasibility)

        return TreatmentScore(
            treatment=treatment,
            feasibility=feasibility,
            suitability=suitability,
            ecological_suitability=ecological_suitability,
            utility=utility,
            confidence=confidence,
            reason=reason,
        )

    def rank_treatments(self, scenario: Scenario) -> List[TreatmentScore]:
        scores = []
        for treatment in TREATMENT_LIBRARY:
            try:
                scores.append(self.score_treatment(scenario, treatment))
            except Exception:
                continue
        # Scored treatments first, by utility; treatments without suitability evidence follow.
        scores.sort(key=lambda x: (x.evidence != "none", x.utility), reverse=True)
        return scores

    def _ecological_score(self, treatment: str, scenario: Scenario) -> float:
        shoreline = scenario.shoreline_type.lower()
        sensitivity = scenario.shoreline_sensitivity.lower()
        base = 5.0

        if treatment == "natural_attenuation":
            if shoreline in {"marsh", "mudflat"} and sensitivity in {"high", "very_high"}:
                return 8.5
            return 7.0

        if treatment == "bioremediation":
            return 6.0

        if treatment in {"manual_removal", "vacuum_removal", "mechanical_removal"}:
            if shoreline in {"marsh", "mudflat", "tundra"}:
                return 3.0
            return 6.0

        if treatment in {"high_pressure_washing", "high_pressure_heated_washing", "sediment_mixing"}:
            # On hard substrates pressure washing is an accepted method, so it is not scored as the most
            # damaging option there. Heated washing stays lower: hot-water-washed Exxon Valdez sites initially
            # declined more than unwashed ones (NOAA OR&R). The values 4.5 and 3.0 are ASSUMED.
            if shoreline in {"bedrock", "boulder", "cobble"} and treatment != "sediment_mixing":
                return 4.5 if treatment == "high_pressure_washing" else 3.0
            return 2.0

        if treatment in {"low_pressure_flushing", "surface_washing_agents", "low_pressure_heated_flushing"}:
            return 4.5

        if treatment in {"vegetation_cutting", "sediment_relocation"}:
            if shoreline in {"marsh", "tundra"}:
                return 2.5
            return 4.0

        if treatment == "passive_sorbents":
            return 6.5

        return base

    def ecological_score_explanation(self, treatment: str, scenario: Scenario) -> dict:
        """Return the rule rationale used for the ecological suitability score."""
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

    def _decision_utility(self, feasibility: str, suitability: float, ecological_suitability: float) -> float:
        feasibility_weight = {"eligible": 1.0, "conditional": 0.6, "ineligible": 0.0}[feasibility]
        return round((0.6 * feasibility_weight * suitability) + (0.4 * ecological_suitability), 2)

    def _confidence(self, feasibility: str, suitability: float, ecological_suitability: float) -> float:
        base = {"eligible": 0.8, "conditional": 0.6, "ineligible": 0.2}[feasibility]
        spread = 1.0 - min(abs(suitability - ecological_suitability) / 10.0, 1.0)
        return round(min(1.0, max(0.0, base * 0.7 + spread * 0.3)), 2)

    def _reason_for_treatment(self, treatment: str, scenario: Scenario, feasibility: str) -> str:
        core = [
            f"shoreline={scenario.shoreline_type}",
            f"oil={scenario.oil_category}",
            f"coverage={scenario.oil_coverage}%",
            f"penetration={scenario.penetration_depth_cm} cm",
        ]
        if feasibility == "eligible":
            return f"{treatment}: operationally feasible; " + "; ".join(core)
        if feasibility == "conditional":
            return f"{treatment}: conditionally feasible; needs expert review; " + "; ".join(core)
        return f"{treatment}: likely infeasible for this scenario; " + "; ".join(core)
