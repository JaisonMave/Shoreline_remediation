from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Scenario:
    shoreline_type: str
    shoreline_sensitivity: str = "moderate"
    oil_category: str = "medium"
    oil_coverage: float = 40.0
    oil_thickness: float = 5.0
    penetration_depth_cm: float = 8.0
    wave_exposure: str = "moderate"
    tidal_range: str = "moderate"
    temperature_c: float = 15.0
    season: str = "summer"
    substrate_permeability: str = "moderate"
    surface_oil: bool = True
    subsurface_oil: bool = False
    accessibility: str = "good"
    habitat_type: str = "mixed_sediment"
    recovery_potential: str = "moderate"
    waste_handling: str = "manageable"


@dataclass
class TreatmentScore:
    treatment: str
    feasibility: str
    suitability: float
    ecological_suitability: float
    utility: float
    confidence: float
    reason: str
    # "synthetic_rules": suitability comes from a model trained on rule-generated labels (not field data).
    # "none": no suitability labels exist for this treatment, so it is listed after the scored treatments.
    evidence: str = "synthetic_rules"


TREATMENT_LIBRARY: List[str] = [
    "natural_attenuation",
    "manual_removal",
    "passive_sorbents",
    "vacuum_removal",
    "low_pressure_flushing",
    "low_pressure_heated_flushing",
    "high_pressure_washing",
    "high_pressure_heated_washing",
    "surface_washing_agents",
    "solidifiers",
    "mechanical_removal",
    "sediment_relocation",
    "sediment_mixing",
    "bioremediation",
    "vegetation_cutting",
]
