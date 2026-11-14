from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.stats import qmc


MODEL_VERSION = "dhi_informed_shoreline_v1"

# Representative DHI Oil Spill Model parameterization values from the supplied
# manual's parameter table. These are screening defaults, not site calibration.
DHI_OIL_PARAMETERS = {
    "light": {"volatile_fraction": 0.729, "heavy_fraction": 0.2609, "wax_fraction": 0.01, "asphaltene_fraction": 0.0001, "evap_a": 2.52, "evap_b": 0.045, "bio_volatile": 0.005, "bio_heavy": 0.0, "dissolve_volatile": 0.4, "dissolve_heavy": 0.4},
    "medium": {"volatile_fraction": 0.30, "heavy_fraction": 0.683, "wax_fraction": 0.007, "asphaltene_fraction": 0.01, "evap_a": 1.89, "evap_b": 0.045, "bio_volatile": 0.005, "bio_heavy": 0.0, "dissolve_volatile": 0.4, "dissolve_heavy": 0.4},
    "heavy": {"volatile_fraction": 0.075, "heavy_fraction": 0.775, "wax_fraction": 0.07, "asphaltene_fraction": 0.08, "evap_a": 1.31, "evap_b": 0.045, "bio_volatile": 0.005, "bio_heavy": 0.0, "dissolve_volatile": 0.4, "dissolve_heavy": 0.4},
    "solid": {"volatile_fraction": 0.075, "heavy_fraction": 0.775, "wax_fraction": 0.07, "asphaltene_fraction": 0.08, "evap_a": 0.80, "evap_b": 0.035, "bio_volatile": 0.003, "bio_heavy": 0.0, "dissolve_volatile": 0.2, "dissolve_heavy": 0.1},
}

TREATMENT_PARAMETERS = {
    "no_cleanup": {"surface_removal": 0.0, "subsurface_removal": 0.0, "disturbance": 0.0},
    "manual_removal": {"surface_removal": 0.045, "subsurface_removal": 0.006, "disturbance": 0.08},
    "passive_sorbents": {"surface_removal": 0.032, "subsurface_removal": 0.002, "disturbance": 0.04},
    "vacuum_removal": {"surface_removal": 0.050, "subsurface_removal": 0.012, "disturbance": 0.10},
    "low_pressure_flushing": {"surface_removal": 0.060, "subsurface_removal": 0.010, "disturbance": 0.16},
    "low_pressure_heated_flushing": {"surface_removal": 0.075, "subsurface_removal": 0.014, "disturbance": 0.20},
    "mechanical_removal": {"surface_removal": 0.070, "subsurface_removal": 0.030, "disturbance": 0.25},
    "sediment_relocation": {"surface_removal": 0.035, "subsurface_removal": 0.020, "disturbance": 0.22},
    "sediment_mixing": {"surface_removal": 0.025, "subsurface_removal": 0.018, "disturbance": 0.24},
    "natural_attenuation": {"surface_removal": 0.010, "subsurface_removal": 0.004, "disturbance": 0.01},
    "bioremediation": {"surface_removal": 0.016, "subsurface_removal": 0.009, "disturbance": 0.03},
    "vegetation_cutting": {"surface_removal": 0.030, "subsurface_removal": 0.002, "disturbance": 0.30},
}


def _lhs_values(n_samples: int, seed: int) -> np.ndarray:
    sampler = qmc.LatinHypercube(d=8, seed=seed)
    return sampler.random(n=n_samples)


def _category(value: float, levels: list[str]) -> str:
    return levels[min(int(value * len(levels)), len(levels) - 1)]


def _scenario_from_lhs(row: np.ndarray, index: int) -> dict:
    shorelines = ["sand_beach", "mixed_sediment", "marsh", "mudflat", "cobble", "bedrock"]
    oils = ["light", "medium", "heavy", "solid"]
    treatments = ["manual_removal", "passive_sorbents", "vacuum_removal", "low_pressure_flushing", "mechanical_removal", "natural_attenuation", "bioremediation"]
    shoreline = _category(row[0], shorelines)
    oil = _category(row[1], oils)
    treatment = _category(row[7], treatments)
    start = date(2024, 1, 1) + timedelta(days=index * 3)
    return {
        "survey_date": start,
        "segment_id": f"LHS-{index + 1:04d}",
        "latitude": round(29.0 + row[2] * 4.0, 6),
        "longitude": round(-91.5 + row[3] * 3.0, 6),
        "shoreline_type": shoreline,
        "surface_oil_distribution_pct": round(10 + row[4] * 80, 1),
        "oil_thickness_cm": round(0.05 + row[5] * 2.0, 2),
        "oil_character": ["ST", "CT", "CV", "TO"][min(int(row[5] * 4), 3)],
        "oil_category": oil,
        "subsurface_oil_interval_cm": round(row[6] * 40, 1),
        "treatment_applied": treatment,
        "treatment_start_date": start + timedelta(days=1),
        "treatment_end_date": start + timedelta(days=2),
        "weather_class": _category(row[2], ["calm", "moderate", "rough"]),
        "tide_class": _category(row[3], ["low", "moderate", "high"]),
        "wave_class": _category(row[4], ["low", "moderate", "high"]),
        "temperature_c": round(5 + row[5] * 25, 1),
        "initial_oil_mass_kg": round(30 + row[4] * 470, 2),
    }


def _rates(record: dict) -> tuple[float, float, float, float]:
    treatment = TREATMENT_PARAMETERS.get(record["treatment_applied"], TREATMENT_PARAMETERS["natural_attenuation"])
    weathering = {"light": 0.020, "medium": 0.014, "heavy": 0.009, "solid": 0.005}[record["oil_category"]]
    wave_factor = {"low": 0.75, "moderate": 1.0, "high": 1.30}[record["wave_class"]]
    temperature_factor = 0.65 + max(record["temperature_c"], 0.0) / 25.0
    return (
        weathering * wave_factor * temperature_factor,
        treatment["surface_removal"],
        treatment["subsurface_removal"],
        treatment["disturbance"],
    )


def _dhi_weathering_rates(record: dict, age_days: float) -> tuple[float, float, float, float]:
    """Return effective DHI-inspired evaporation, dissolution, and bio rates."""
    parameters = DHI_OIL_PARAMETERS[record["oil_category"]]
    temperature = max(record["temperature_c"], 15.0)
    wave_factor = {"low": 0.75, "moderate": 1.0, "high": 1.30}[record["wave_class"]]
    # Fingas/DHI logarithmic evaporation form: A + B*T*ln(t), converted to a
    # local first-order rate for the ODE. Surface oil only is evaporative.
    minutes = max(age_days * 1440.0, 10.0)
    evap_rate = parameters["evap_b"] * temperature / minutes
    dissolution_rate = 0.0008 * wave_factor
    bio_volatile = parameters["bio_volatile"] / 30.0
    bio_heavy = parameters["bio_heavy"] / 365.0
    return evap_rate, dissolution_rate, bio_volatile, bio_heavy


def simulate_segment(record: dict, survey_days: list[int] | None = None) -> pd.DataFrame:
    survey_days = survey_days or [0, 7, 14, 30, 60, 90, 180, 365]
    _, treatment_surface, treatment_subsurface, disturbance = _rates(record)
    parameters = DHI_OIL_PARAMETERS[record["oil_category"]]
    surface_initial = record["initial_oil_mass_kg"] * (0.72 + 0.2 * record["surface_oil_distribution_pct"] / 100)
    subsurface_initial = record["initial_oil_mass_kg"] - surface_initial
    surface_fractions = np.array([parameters["volatile_fraction"], parameters["heavy_fraction"], parameters["wax_fraction"], parameters["asphaltene_fraction"]], dtype=float)
    surface_fractions /= surface_fractions.sum()
    subsurface_fractions = surface_fractions.copy()
    initial_state = np.array([
        surface_initial * surface_fractions[0], surface_initial * surface_fractions[1],
        subsurface_initial * subsurface_fractions[0], subsurface_initial * subsurface_fractions[1],
        record["initial_oil_mass_kg"] * parameters["wax_fraction"],
        record["initial_oil_mass_kg"] * parameters["asphaltene_fraction"],
    ])
    transfer = 0.004 + record["subsurface_oil_interval_cm"] / 10000

    def derivative(_time: float, state: np.ndarray) -> list[float]:
        surface_volatile, surface_heavy, subsurface_volatile, subsurface_heavy, wax, asphaltene = state
        age_days = max(float(_time), 0.01)
        evaporation, dissolution, bio_volatile, bio_heavy = _dhi_weathering_rates(record, age_days)
        surface_total = surface_volatile + surface_heavy
        subsurface_total = subsurface_volatile + subsurface_heavy
        treatment_surface_loss = treatment_surface * surface_total
        treatment_subsurface_loss = treatment_subsurface * subsurface_total
        d_surface_volatile = -(evaporation + dissolution + bio_volatile) * surface_volatile - treatment_surface_loss * surface_volatile / max(surface_total, 1e-9) + transfer * subsurface_volatile
        d_surface_heavy = -(dissolution * 0.25 + bio_heavy) * surface_heavy - treatment_surface_loss * surface_heavy / max(surface_total, 1e-9) + transfer * subsurface_heavy
        d_subsurface_volatile = -(dissolution * 0.10 + bio_volatile * 0.35) * subsurface_volatile - treatment_subsurface_loss * subsurface_volatile / max(subsurface_total, 1e-9) - transfer * subsurface_volatile
        d_subsurface_heavy = -(bio_heavy * 0.35) * subsurface_heavy - treatment_subsurface_loss * subsurface_heavy / max(subsurface_total, 1e-9) - transfer * subsurface_heavy
        return [d_surface_volatile, d_surface_heavy, d_subsurface_volatile, d_subsurface_heavy, 0.0, 0.0]

    horizon = max(survey_days)
    solution = solve_ivp(derivative, (0, horizon), initial_state, t_eval=survey_days, max_step=3.0)
    records = []
    initial_total = float(initial_state.sum())
    for day, surface, subsurface in zip(solution.t, solution.y[0], solution.y[1]):
        state = solution.y[:, len(records)]
        surface_volatile, surface_heavy, subsurface_volatile, subsurface_heavy, wax, asphaltene = state
        surface_mass = max(0.0, float(surface_volatile + surface_heavy))
        subsurface_mass = max(0.0, float(subsurface_volatile + subsurface_heavy))
        residual = max(0.0, float(state.sum()))
        oil_reduction = max(0.0, 1.0 - residual / initial_total)
        disturbance_penalty = disturbance * np.exp(-day / 90.0)
        habitat_recovery = float(np.clip(oil_reduction * 0.85 + (1.0 - disturbance_penalty) * 0.15, 0.0, 1.0))
        meets_endpoint = residual <= initial_total * 0.20 and habitat_recovery >= 0.80
        endpoint = "Meets cleanup endpoints" if meets_endpoint else "Continued monitoring required"
        if meets_endpoint and day > 0:
            endpoint = "No further treatment recommended"
        records.append({
            **record,
            "survey_date": record["survey_date"] + timedelta(days=int(day)),
            "survey_day": int(day),
            "surface_oil_mass_kg": round(surface_mass, 3),
            "subsurface_oil_mass_kg": round(subsurface_mass, 3),
            "volatile_oil_mass_kg": round(max(0.0, float(surface_volatile + subsurface_volatile)), 3),
            "heavy_oil_mass_kg": round(max(0.0, float(surface_heavy + subsurface_heavy)), 3),
            "wax_mass_kg": round(max(0.0, float(wax)), 3),
            "asphaltene_mass_kg": round(max(0.0, float(asphaltene)), 3),
            "residual_oil_kg": round(residual, 3),
            "residual_oil_pct_of_initial": round(100 * residual / initial_total, 2),
            "habitat_recovery_index": round(habitat_recovery, 3),
            "endpoint_decision": endpoint,
            "continued_monitoring": not meets_endpoint,
            "model_version": MODEL_VERSION,
        })
    return pd.DataFrame(records)


def generate_lhs_scats(n_segments: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic longitudinal SCAT-style observations using LHS inputs."""
    rows = []
    for index, lhs_row in enumerate(_lhs_values(n_segments, seed)):
        rows.append(simulate_segment(_scenario_from_lhs(lhs_row, index)))
    return pd.concat(rows, ignore_index=True)


def export_lhs_dataset(path: str | Path, n_segments: int = 100, seed: int = 42) -> pd.DataFrame:
    data = generate_lhs_scats(n_segments=n_segments, seed=seed)
    data.to_csv(path, index=False)
    return data


def simulate_selected_scenario(scenario, treatment: str, survey_days: list[int] | None = None, engine: str = "transport",
                               oil_thickness: float | None = None, penetration_depth_cm: float | None = None,
                               season: str | None = None, parameter_overrides: dict | None = None) -> pd.DataFrame:
    if engine == "transport":
        from src.shoreline_remediation.shoreline_transport import simulate_transect

        return simulate_transect(scenario, treatment, survey_days, oil_thickness=oil_thickness,
                                 penetration_depth_cm=penetration_depth_cm, season=season,
                                 parameter_overrides=parameter_overrides)
    record = {
        "survey_date": date.today(),
        "segment_id": "SELECTED-SCENARIO",
        "latitude": np.nan,
        "longitude": np.nan,
        "shoreline_type": scenario.shoreline_type,
        "surface_oil_distribution_pct": scenario.oil_coverage,
        "oil_thickness_cm": scenario.oil_thickness / 10.0,
        "oil_character": "TO" if scenario.oil_thickness >= 10 else "CV",
        "oil_category": scenario.oil_category,
        "subsurface_oil_interval_cm": scenario.penetration_depth_cm if scenario.subsurface_oil else 0.0,
        "treatment_applied": treatment,
        "treatment_start_date": date.today() + timedelta(days=1),
        "treatment_end_date": date.today() + timedelta(days=2),
        "weather_class": scenario.wave_exposure,
        "tide_class": scenario.tidal_range,
        "wave_class": scenario.wave_exposure,
        "temperature_c": scenario.temperature_c,
        "initial_oil_mass_kg": max(50.0, scenario.oil_coverage * scenario.oil_thickness * 2.0),
    }
    return simulate_segment(record, survey_days=survey_days)
