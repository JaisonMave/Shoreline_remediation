from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .data_model import Scenario, TreatmentScore, TREATMENT_LIBRARY
from .fast_engine import FASTRuleEngine
from . import knowledge
from .ml_models import GaussianProcessSuitabilityModel, make_synthetic_dataset


class HybridDecisionModel:
    """Rule screening plus ecological ordering; the rule-trained ML suitability layer is opt-in only.

    Default (decision path, D26): feasibility from the FAST-like rules, then an ASSUMED ecological (do-no-harm)
    score orders options within a feasibility tier. No suitability score is used, because the only labels
    available are generated from hand-written rules. `use_synthetic_suitability=True` restores the GPR layer
    for the "Method test (synthetic data)" view only. Literature effect coefficients enter here later (V4 R2, F2).
    """

    def __init__(self, use_synthetic_suitability: bool = False):
        self.fast_engine = FASTRuleEngine()
        self.use_synthetic_suitability = use_synthetic_suitability
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

        if not self.use_synthetic_suitability:
            ecological_suitability = self._ecological_score(treatment, scenario)
            return TreatmentScore(
                treatment=treatment, feasibility=feasibility, suitability=float("nan"),
                ecological_suitability=ecological_suitability,
                utility=0.0 if feasibility == "ineligible" else round(ecological_suitability, 2),
                confidence={"eligible": 0.6, "conditional": 0.4, "ineligible": 0.2}[feasibility],
                reason=f"{treatment}: rule screening; ordered within its tier by an ASSUMED ecological score "
                       "(no outcome-based suitability yet); "
                       + self._reason_for_treatment(treatment, scenario, feasibility).split(": ", 1)[1],
                evidence="screening_only",
            )

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
        # Feasibility tier first (rules are hard constraints), then scored before unscored, then utility (D25).
        tier = {"eligible": 0, "conditional": 1, "ineligible": 2}
        scores.sort(key=lambda x: (tier[x.feasibility], x.evidence == "none", -x.utility))
        return scores

    def _ecological_score(self, treatment: str, scenario: Scenario) -> float:
        # ASSUMED ecological (do-no-harm) scores moved to data/knowledge/tables/ecological_score.csv (D16, F2).
        return knowledge.ecological_score(treatment, scenario)

    def ecological_score_explanation(self, treatment: str, scenario: Scenario) -> dict:
        """Return the rule rationale used for the ecological suitability score (read from ecological_score.csv)."""
        return knowledge.ecological_score_explanation(treatment, scenario)

    def _decision_utility(self, feasibility: str, suitability: float, ecological_suitability: float) -> float:
        if feasibility == "ineligible":
            return 0.0  # a rule exclusion is final; ecology cannot lift an excluded option (V4 R1, D25)
        feasibility_weight = {"eligible": 1.0, "conditional": 0.6}[feasibility]
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
