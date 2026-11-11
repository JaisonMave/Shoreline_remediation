from __future__ import annotations

from typing import Dict, List

from .data_model import Scenario, TREATMENT_LIBRARY


class FASTRuleEngine:
    """Rule-based feasibility screening inspired by FAST decision logic."""

    def evaluate_feasibility(self, scenario: Scenario) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for treatment in TREATMENT_LIBRARY:
            results[treatment] = self._classify_treatment(treatment, scenario)
        return results

    def _classify_treatment(self, treatment: str, scenario: Scenario) -> str:
        shoreline = scenario.shoreline_type.lower()
        oil = scenario.oil_category.lower()
        coverage = scenario.oil_coverage
        penetration = scenario.penetration_depth_cm
        exposure = scenario.wave_exposure.lower()
        sensitivity = scenario.shoreline_sensitivity.lower()

        if shoreline in {"marsh", "mudflat", "peat", "tundra"}:
            if treatment in {"manual_removal", "passive_sorbents"}:
                return "eligible"
            # Heated flushing is included because hot-water methods should avoid sensitive habitats
            # (docs/NOAA_ASSUMPTION_AUDIT.md). It previously fell through to a generic rule and came out eligible.
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
            # High-pressure washing is decided by the dedicated rule further down (eligible on hard substrate
            # with more than 40% cover and less than 5 cm penetration). An early "conditional" return here
            # used to make that rule unreachable for bedrock, boulder and cobble.

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
                shoreline == "mixed_sediment" and scenario.substrate_permeability == "high"
            )
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
