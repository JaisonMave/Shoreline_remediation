"""Cross-shore advection-dispersion-reaction (ADR) model of stranded oil on beaches and marshes.

Framework: the reactive-transport formulation used for oiled beaches (first-order / Monod kinetics with
oxygen and nutrient limitation; Geng et al. 2021, Curr. Opin. Chem. Eng. 35:100751, and the BIOB family,
Geng and Boufadel) with a linear retardation term for oil retained by marsh vegetation and soil. It replaces the
earlier DHI open-water structure, which describes slicks on the sea surface rather than oil in sediment.

Every parameter is listed in PARAMETER_TABLE as SOURCED (value taken from a document read for this project)
or ASSUMED (a screening placeholder that must be calibrated to SCAT observations).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

MODEL_VERSION = "adr_shoreline_transport_v1_1"  # v1_1: mass-conserving dispersion
N_CELLS = 40
DX_M = 1.0
SEGMENT_LENGTH_M = 100.0
OIL_DENSITY = 900.0
THICK_OIL_MM = 10.0  # Michel et al. 2013: marsh endpoint "no thick (>1 cm) oil on the marsh platform"
TREATMENT_DAYS = 60.0
MARSH_TYPES = {"marsh", "mudflat", "peat", "tundra"}
HARD_TYPES = {"bedrock", "boulder"}

PARAMETER_TABLE = [
    ("Biodegradation form", "first-order with multiplicative Monod O2 and N terms", "SOURCED", "Geng et al. 2021 (supplied): first-order, instantaneous and Monod kinetics; multiplicative Monod most common"),
    ("Oxygen limit for efficient degradation", "> 1.5 mg/L in situ (0.1 mg/L lab minimum)", "SOURCED", "Geng et al. 2021, 'Environmental conditions'"),
    ("Nitrogen half-saturation K_N", "0.1 - 1.0 mg/L (0.5 used)", "SOURCED", "Geng et al. 2021, nutrient limitation paragraph"),
    ("Marsh oil spreading distance", "10 - 15 m from the marsh edge", "SOURCED", "Michel et al. 2013, Discussion"),
    ("Marsh platform oil thickness (heavy oiling)", "2 - 3 cm", "SOURCED", "Michel et al. 2013, Discussion"),
    ("Marsh tidal range", "about 0.5 m", "SOURCED", "Michel et al. 2013, Discussion"),
    ("Marsh endpoint: no thick oil", "10 mm threshold", "SOURCED", "Michel et al. 2013, Results (no flushable oil, no sheen, no >1 cm oil)"),
    ("Surface oil definition", "oil on the surface down to 5 cm depth", "SOURCED", "NOAA Shoreline Assessment Manual (supplied), Appendix I"),
    ("Retardation factor R by zone", "1.0 - 8.0", "ASSUMED", "Linear-equilibrium retention form; magnitudes unpublished for marsh oil - calibrate"),
    ("Effective dispersion D by zone", "0.1 - 5.0 m2/day", "ASSUMED", "Order-of-magnitude tidal/swash mixing - calibrate"),
    ("Oxygen by zone", "marsh platform 0.5, beach 3-8 mg/L", "ASSUMED", "Chosen consistent with the 1.5 mg/L threshold and anoxic marsh soils - calibrate"),
    ("Oxygen half-saturation K_O", "1.0 mg/L", "ASSUMED", "Not given numerically in the supplied review"),
    ("Biodegradation base rate", "0.01 /day labile, 0.0005 /day recalcitrant at 20 C", "ASSUMED", "Screening values - calibrate"),
    ("Temperature factor Q10", "2.0", "ASSUMED", "Common biokinetic convention"),
    ("Evaporation rate by oil category", "0.01 - 0.10 /day", "ASSUMED", "Screening values - calibrate"),
    ("Labile oil fraction by category", "0.25 - 0.80", "ASSUMED", "Screening values - calibrate to oil assay"),
    ("Infiltration rate by zone", "0 - 0.02 /day", "ASSUMED", "Low in marsh (Michel: little penetration), higher in permeable sand - calibrate"),
    ("Treatment removal rates", "see TREATMENT_PARAMETERS in process_model", "ASSUMED", "Engineering placeholders; NOAA gives applicability, not rate constants"),
    ("Treatment duration", "60 days", "ASSUMED", "Operational placeholder"),
]


def _zone_arrays(scenario) -> dict[str, np.ndarray]:
    n = N_CELLS
    shore = scenario.shoreline_type
    index = np.arange(n)
    R, D, oxygen, nutrient, k_inf, v_out = (np.ones(n) for _ in range(6))
    if shore in MARSH_TYPES:
        zones = [(index < 3, 1.5, 2.0, 4.0, 0.5, 0.002, 0.05), ((index >= 3) & (index < 18), 8.0, 0.3, 0.5, 0.3, 0.0005, 0.0),
                 (index >= 18, 6.0, 0.1, 1.0, 0.3, 0.001, 0.0)]
    elif shore in HARD_TYPES:
        zones = [(index < 15, 1.0, 3.0, 8.0, 0.5, 0.0, 0.8), (index >= 15, 1.2, 1.0, 8.0, 0.5, 0.0, 0.0)]
    else:
        zones = [(index < 10, 1.2, 5.0, 6.0, 0.5, 0.02, 0.5), ((index >= 10) & (index < 25), 1.5, 1.0, 3.0, 0.4, 0.015, 0.0),
                 (index >= 25, 2.0, 0.2, 4.0, 0.3, 0.01, 0.0)]
    for mask, r, d, o, nn, ki, vo in zones:
        R[mask], D[mask], oxygen[mask], nutrient[mask], k_inf[mask], v_out[mask] = r, d, o, nn, ki, vo
    wave = {"low": 0.6, "moderate": 1.0, "high": 1.6, "very_high": 2.0}.get(scenario.wave_exposure, 1.0)
    perm = {"low": 0.5, "moderate": 1.0, "high": 1.5}.get(scenario.substrate_permeability, 1.0)
    tide = {"low": 0.7, "moderate": 1.0, "high": 1.4}.get(scenario.tidal_range, 1.0)
    return dict(R=R, D=D * wave * tide, oxygen=oxygen, nutrient=nutrient, k_inf=k_inf * perm, v_out=v_out * wave)


def _initial_state(scenario) -> tuple[np.ndarray, float, int, int]:
    labile_fraction = {"light": 0.80, "medium": 0.55, "heavy": 0.35, "solid": 0.25}[scenario.oil_category]
    band = int(round(np.clip(3 + scenario.oil_coverage / 100.0 * 12, 3, 15)))
    start = 0 if scenario.shoreline_type in MARSH_TYPES else (10 if scenario.shoreline_type not in HARD_TYPES else 0)
    stop = min(start + band, N_CELLS)
    thickness_m = max(scenario.oil_thickness, 0.1) / 1000.0
    surface = np.zeros(N_CELLS)
    surface[start:stop] = thickness_m * OIL_DENSITY * (scenario.oil_coverage / 100.0)
    state = np.concatenate([surface * labile_fraction, surface * (1 - labile_fraction), np.zeros(N_CELLS), np.zeros(N_CELLS)])
    return state, labile_fraction, start, stop


def simulate_transect(scenario, treatment: str = "no_cleanup", survey_days: list[int] | None = None, return_profiles: bool = False):
    from src.shoreline_remediation.process_model import TREATMENT_PARAMETERS

    days = sorted(set(survey_days or [0, 7, 14, 30, 60, 90, 180, 365]))
    zones = _zone_arrays(scenario)
    state0, _, start, stop = _initial_state(scenario)
    params = TREATMENT_PARAMETERS.get(treatment, TREATMENT_PARAMETERS["no_cleanup"])
    access = {"good": 1.0, "moderate": 0.7, "restricted": 0.4}.get(scenario.accessibility, 0.7)
    temperature_factor = 2.0 ** ((scenario.temperature_c - 20.0) / 10.0)
    evap = {"light": 0.10, "medium": 0.03, "heavy": 0.01, "solid": 0.005}[scenario.oil_category]
    k_o, k_n = 1.0, 0.5
    monod = (zones["oxygen"] / (k_o + zones["oxygen"])) * (zones["nutrient"] / (k_n + zones["nutrient"]))
    k_bio_labile = 0.01 * temperature_factor * monod
    k_bio_recalcitrant = 0.0005 * temperature_factor * monod
    d_eff = zones["D"] / zones["R"]
    k_inf, v_out = zones["k_inf"], zones["v_out"]
    k_up = 0.002
    surface_evap = evap * (1.0 if scenario.shoreline_type not in MARSH_TYPES else 0.6)
    n = N_CELLS

    # Dispersion is written in flux form so that it conserves mass. The earlier form, d_eff times a plain
    # Laplacian, is not conservative where d_eff changes between zones: with every sink switched off it raised
    # total oil mass by 49% in 30 days on a sand beach. Face values use the harmonic mean, the standard choice
    # for a coefficient that jumps between cells.
    d_face = 2.0 * d_eff[:-1] * d_eff[1:] / (d_eff[:-1] + d_eff[1:])

    def dispersion(field: np.ndarray) -> np.ndarray:
        flux = d_face * np.diff(field) / DX_M  # flux across each interior face; the two ends are no-flux
        return np.diff(flux, prepend=0.0, append=0.0) / DX_M

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        sl, sr, bl, br = y[:n], y[n:2 * n], y[2 * n:3 * n], y[3 * n:]
        treat = (params["surface_removal"] * access) if t <= TREATMENT_DAYS else 0.0
        treat_sub = (params["subsurface_removal"] * access) if t <= TREATMENT_DAYS else 0.0
        outflux_l = np.zeros(n)
        outflux_r = np.zeros(n)
        outflux_l[0] = v_out[0] * sl[0] / DX_M
        outflux_r[0] = v_out[0] * sr[0] / DX_M
        d_sl = dispersion(sl) - (surface_evap + k_inf + k_bio_labile + treat) * sl + k_up * bl - outflux_l
        d_sr = dispersion(sr) - (k_inf + k_bio_recalcitrant + treat) * sr + k_up * br - outflux_r
        d_bl = k_inf * sl - (k_bio_labile * 0.5 + k_up + treat_sub) * bl
        d_br = k_inf * sr - (k_bio_recalcitrant * 0.5 + k_up + treat_sub) * br
        return np.concatenate([d_sl, d_sr, d_bl, d_br])

    solution = solve_ivp(rhs, (0, max(days)), state0, t_eval=days, method="BDF", rtol=1e-6, atol=1e-9)
    initial_mass = float(state0.sum() * DX_M * SEGMENT_LENGTH_M)
    platform = slice(3, 18) if scenario.shoreline_type in MARSH_TYPES else slice(0, n)
    x_axis = (np.arange(n) + 0.5) * DX_M
    rows, profiles = [], []
    for column, day in enumerate(solution.t):
        y = np.clip(solution.y[:, column], 0.0, None)
        sl, sr, bl, br = y[:n], y[n:2 * n], y[2 * n:3 * n], y[3 * n:]
        surface = sl + sr
        surface_kg = float(surface.sum() * DX_M * SEGMENT_LENGTH_M)
        subsurface_kg = float((bl + br).sum() * DX_M * SEGMENT_LENGTH_M)
        residual = surface_kg + subsurface_kg
        thickness_mm = surface / OIL_DENSITY * 1000.0 / max(scenario.oil_coverage / 100.0, 0.05)
        max_platform_mm = float(thickness_mm[platform].max())
        centroid = float((surface * x_axis).sum() / surface.sum()) if surface.sum() > 1e-12 else np.nan
        oil_reduction = max(0.0, 1.0 - residual / initial_mass) if initial_mass > 0 else 1.0
        penalty = params["disturbance"] * (1.6 if scenario.shoreline_type in MARSH_TYPES else 1.0) * np.exp(-day / 90.0)
        habitat = float(np.clip(0.7 * oil_reduction + 0.3 * (1.0 - penalty), 0.0, 1.0))
        surface_pct = 100.0 * surface_kg / initial_mass if initial_mass > 0 else 0.0
        if scenario.shoreline_type in MARSH_TYPES:
            meets = max_platform_mm <= THICK_OIL_MM and surface_pct <= 20.0
        else:
            meets = surface_pct <= 5.0  # proxy for the "<1% visible oil" beach endpoint (Michel et al. 2013)
        endpoint = "Meets cleanup endpoints" if (meets and day > 0) else "Continued monitoring required"
        rows.append({
            "survey_date": date.today() + timedelta(days=int(day)), "survey_day": int(day),
            "surface_oil_mass_kg": round(surface_kg, 3), "subsurface_oil_mass_kg": round(subsurface_kg, 3),
            "residual_oil_kg": round(residual, 3),
            "residual_oil_pct_of_initial": round(100.0 * residual / initial_mass, 2) if initial_mass > 0 else 0.0,
            "habitat_recovery_index": round(habitat, 3), "max_platform_thickness_mm": round(max_platform_mm, 2),
            "oil_centroid_m": round(centroid, 2) if centroid == centroid else np.nan,
            "endpoint_decision": endpoint, "continued_monitoring": not (meets and day > 0),
            "treatment_applied": treatment, "model_version": MODEL_VERSION,
        })
        profiles.append(surface / OIL_DENSITY * 1000.0)
    frame = pd.DataFrame(rows)
    if return_profiles:
        return frame, x_axis, np.array(profiles)
    return frame
