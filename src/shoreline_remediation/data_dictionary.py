from __future__ import annotations

import random
from typing import Dict, List

import pandas as pd

FAST_SCAT_VARIABLES: List[Dict[str, str]] = [
    {"field": "scenario_id", "group": "metadata", "dtype": "string", "units": "-", "description": "Unique scenario identifier"},
    {"field": "shoreline_type", "group": "shoreline", "dtype": "categorical", "units": "-", "description": "Shoreline class such as marsh, sand beach, mixed-sediment, bedrock"},
    {"field": "grain_size_mm", "group": "shoreline", "dtype": "numeric", "units": "mm", "description": "Representative grain size"},
    {"field": "substrate_permeability", "group": "shoreline", "dtype": "categorical", "units": "-", "description": "Low, moderate, or high permeability"},
    {"field": "slope_deg", "group": "shoreline", "dtype": "numeric", "units": "deg", "description": "Shoreline slope angle"},
    {"field": "oil_category", "group": "oil", "dtype": "categorical", "units": "-", "description": "Light, medium, heavy, or solid oil"},
    {"field": "api_gravity", "group": "oil", "dtype": "numeric", "units": "API", "description": "API gravity of the oil"},
    {"field": "viscosity_cP", "group": "oil", "dtype": "numeric", "units": "cP", "description": "Dynamic viscosity"},
    {"field": "pour_point_C", "group": "oil", "dtype": "numeric", "units": "C", "description": "Pour point temperature"},
    {"field": "weathering_pct", "group": "oil", "dtype": "numeric", "units": "%", "description": "Oil weathering percent"},
    {"field": "stabilized_oil_fraction", "group": "oil", "dtype": "numeric", "units": "%", "description": "Emulsion stabilization fraction"},
    {"field": "oil_coverage_pct", "group": "oiling", "dtype": "numeric", "units": "%", "description": "Percent shoreline oil coverage"},
    {"field": "oil_thickness_cm", "group": "oiling", "dtype": "numeric", "units": "cm", "description": "Observed oil thickness"},
    {"field": "oil_distribution", "group": "oiling", "dtype": "categorical", "units": "-", "description": "Patchy, continuous, linear, or isolated distribution"},
    {"field": "penetration_depth_cm", "group": "oiling", "dtype": "numeric", "units": "cm", "description": "Depth of oil penetration"},
    {"field": "subsurface_oil", "group": "oiling", "dtype": "boolean", "units": "-", "description": "Whether subsurface oil is present"},
    {"field": "wave_exposure", "group": "environment", "dtype": "categorical", "units": "-", "description": "Low, moderate, or high wave exposure"},
    {"field": "tidal_range_m", "group": "environment", "dtype": "numeric", "units": "m", "description": "Tidal range"},
    {"field": "current_m_s", "group": "environment", "dtype": "numeric", "units": "m/s", "description": "Current speed"},
    {"field": "temperature_C", "group": "environment", "dtype": "numeric", "units": "C", "description": "Ambient temperature"},
    {"field": "season", "group": "environment", "dtype": "categorical", "units": "-", "description": "Seasonal category"},
    {"field": "habitat_type", "group": "ecology", "dtype": "categorical", "units": "-", "description": "Habitat type present in shoreline zone"},
    {"field": "shoreline_sensitivity", "group": "ecology", "dtype": "categorical", "units": "-", "description": "Low to very high sensitivity"},
    {"field": "vegetation", "group": "ecology", "dtype": "categorical", "units": "-", "description": "Vegetation status or presence"},
    {"field": "recovery_potential", "group": "ecology", "dtype": "categorical", "units": "-", "description": "Recovery potential of the shoreline"},
    {"field": "accessibility", "group": "operations", "dtype": "categorical", "units": "-", "description": "Site access quality"},
    {"field": "equipment_access", "group": "operations", "dtype": "categorical", "units": "-", "description": "Equipment access status"},
    {"field": "waste_handling", "group": "operations", "dtype": "categorical", "units": "-", "description": "Waste handling complexity"},
    {"field": "safety_constraint", "group": "operations", "dtype": "categorical", "units": "-", "description": "Safety or operational limitation"},
    {"field": "natural_attenuation", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for natural attenuation"},
    {"field": "manual_removal", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for manual removal"},
    {"field": "passive_sorbents", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for passive sorbents"},
    {"field": "vacuum_removal", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for vacuum removal"},
    {"field": "low_pressure_flushing", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for low-pressure flushing"},
    {"field": "mechanical_removal", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for mechanical removal"},
    {"field": "high_pressure_washing", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for high-pressure washing"},
    {"field": "surface_washing_agents", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for surface washing agents"},
    {"field": "bioremediation", "group": "target", "dtype": "numeric", "units": "0-10", "description": "Suitability score for bioremediation"},
]


def generate_training_dataset(n_rows: int = 500) -> pd.DataFrame:
    """Generate a realistic synthetic training dataset using FAST/SCAT-style feature fields."""
    rng = random.Random(42)
    shoreline_types = ["sand_beach", "mixed_sediment", "marsh", "bedrock", "mudflat", "cobble", "boulder", "tundra"]
    oil_categories = ["light", "medium", "heavy", "solid"]
    oil_distributions = ["patchy", "continuous", "linear", "isolated"]
    wave_exposure = ["low", "moderate", "high"]
    season = ["spring", "summer", "autumn", "winter"]
    sensitivity = ["low", "moderate", "high", "very_high"]
    permeability = ["low", "moderate", "high"]
    access = ["good", "restricted", "poor"]
    waste_handling = ["manageable", "moderate", "difficult"]
    safety = ["low", "moderate", "high"]
    habitat = ["salt_marsh", "mudflat", "sandy_beach", "mixed_sediment", "gravel_beach", "peat", "tundra"]

    rows = []
    for i in range(n_rows):
        shoreline = rng.choice(shoreline_types)
        oil = rng.choice(oil_categories)
        coverage = int(rng.uniform(5, 90))
        thickness = round(rng.uniform(0.2, 18.0), 2)
        penetration = round(rng.uniform(0, 25.0), 2)
        exposure = rng.choice(wave_exposure)
        sens = rng.choice(sensitivity)
        perm = rng.choice(permeability)

        api_gravity = {"light": rng.uniform(25, 45), "medium": rng.uniform(15, 25), "heavy": rng.uniform(5, 15), "solid": rng.uniform(0, 10)}[oil]
        viscosity = {"light": rng.uniform(5, 100), "medium": rng.uniform(100, 5000), "heavy": rng.uniform(5000, 200000), "solid": rng.uniform(80000, 800000)}[oil]
        weathering = round(rng.uniform(0, 80), 1)

        row = {
            "scenario_id": f"SCENE_{i:04d}",
            "shoreline_type": shoreline,
            "grain_size_mm": round(rng.uniform(0.1, 30.0), 2),
            "substrate_permeability": perm,
            "slope_deg": round(rng.uniform(1, 25), 2),
            "oil_category": oil,
            "api_gravity": round(api_gravity, 2),
            "viscosity_cP": round(viscosity, 2),
            "pour_point_C": round(rng.uniform(-5, 30), 2),
            "weathering_pct": weathering,
            "stabilized_oil_fraction": round(rng.uniform(0, 65), 2),
            "oil_coverage_pct": coverage,
            "oil_thickness_cm": thickness,
            "oil_distribution": rng.choice(oil_distributions),
            "penetration_depth_cm": penetration,
            "subsurface_oil": rng.choice([True, False]),
            "wave_exposure": exposure,
            "tidal_range_m": round(rng.uniform(0.5, 5.0), 2),
            "current_m_s": round(rng.uniform(0.1, 2.5), 2),
            "temperature_C": round(rng.uniform(2, 28), 2),
            "season": rng.choice(season),
            "habitat_type": rng.choice(habitat),
            "shoreline_sensitivity": sens,
            "vegetation": rng.choice(["sparse", "moderate", "dense"]),
            "recovery_potential": rng.choice(["low", "moderate", "high"]),
            "accessibility": rng.choice(access),
            "equipment_access": rng.choice(["easy", "moderate", "difficult"]),
            "waste_handling": rng.choice(waste_handling),
            "safety_constraint": rng.choice(safety),
        }

        base_scores = {
            "natural_attenuation": 6.5,
            "manual_removal": 6.0,
            "passive_sorbents": 5.5,
            "vacuum_removal": 5.0,
            "low_pressure_flushing": 5.5,
            "mechanical_removal": 5.8,
            "high_pressure_washing": 4.2,
            "surface_washing_agents": 5.0,
            "bioremediation": 6.2,
        }

        score_map = {}
        for treatment, base in base_scores.items():
            score = float(base)

            if shoreline in {"marsh", "mudflat", "peat", "tundra"}:
                if treatment in {"manual_removal", "mechanical_removal", "high_pressure_washing"}:
                    score -= 2.5
                if treatment in {"natural_attenuation", "bioremediation"}:
                    score += 1.5
            if shoreline in {"sand_beach", "mixed_sediment", "gravel_beach"}:
                if treatment in {"manual_removal", "vacuum_removal", "low_pressure_flushing"}:
                    score += 1.0
                if treatment in {"high_pressure_washing", "mechanical_removal"}:
                    score += 0.5
            if oil == "heavy":
                if treatment in {"high_pressure_washing", "mechanical_removal"}:
                    score -= 1.0
                if treatment in {"natural_attenuation", "bioremediation"}:
                    score += 0.5
            if oil == "solid":
                if treatment in {"natural_attenuation", "bioremediation", "passive_sorbents"}:
                    score -= 1.0
            if coverage > 60:
                if treatment in {"manual_removal", "vacuum_removal", "low_pressure_flushing"}:
                    score += 0.8
            if penetration > 10:
                if treatment in {"manual_removal", "vacuum_removal", "low_pressure_flushing"}:
                    score += 0.7
                if treatment in {"high_pressure_washing", "surface_washing_agents"}:
                    score -= 1.0
            if exposure == "high":
                if treatment in {"natural_attenuation", "manual_removal"}:
                    score -= 0.8
            if sens == "very_high":
                if treatment in {"high_pressure_washing", "mechanical_removal", "surface_washing_agents"}:
                    score -= 2.0
                if treatment in {"natural_attenuation", "bioremediation"}:
                    score += 1.0

            score += rng.uniform(-1.8, 1.8)
            score = max(0.0, min(10.0, round(score, 2)))
            score_map[treatment] = score

        row.update(score_map)
        rows.append(row)

    return pd.DataFrame(rows)
