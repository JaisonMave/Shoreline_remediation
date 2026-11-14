from __future__ import annotations

from typing import Dict, List

from . import knowledge
from .data_model import Scenario, TREATMENT_LIBRARY


class FASTRuleEngine:
    """Rule-based feasibility screening inspired by FAST decision logic.

    The rules themselves live in data/knowledge/tables/screening_rule.csv (D16, V4 F2) and are read through
    src/shoreline_remediation/knowledge.py. They were moved from this class unchanged in behaviour; an
    equivalence test (tests/test_f2_f3.py) proves the verdicts are identical before and after the move.
    """

    def evaluate_feasibility(self, scenario: Scenario) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for treatment in TREATMENT_LIBRARY:
            results[treatment] = self._classify_treatment(treatment, scenario)
        return results

    def _classify_treatment(self, treatment: str, scenario: Scenario) -> str:
        return knowledge.classify(treatment, scenario)

    def filter_feasible(self, scenario: Scenario, include_conditional: bool = True) -> List[str]:
        feasibility = self.evaluate_feasibility(scenario)
        feasible = [
            treatment for treatment, status in feasibility.items() if status == "eligible"
        ]
        if include_conditional:
            feasible.extend(
                treatment for treatment, status in feasibility.items() if status == "conditional"
            )
        return feasible
