"""Site evidence for the P5 demo: edge-loss prediction, flags and treatment evidence (plan: docs/P5_DEMO_PLAN.md).

Everything here reads committed files only and needs numpy and pandas, so the dashboard runs from a clean
install of requirements.txt. The model artefact and the site table are built by scripts/build_p5_demo.py.

Inputs:
    models/p5_edge_loss_v1.json   deployed edge-loss model (P2's M1 refitted on all valid cells)
    data/demo/p5_sites.csv        Louisiana SCAT edge cells with inputs, scope status and observed rates
Outputs (functions): predict_edge_loss, site_flags, treatment_evidence, site_scenario.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "p5_edge_loss_v1.json"
SITES_PATH = ROOT / "data" / "demo" / "p5_sites.csv"
FEATURES = ["water_1km_2010", "water_250m_2010", "fetch_mean_m", "pre_rate"]
FEATURE_LABELS = {
    "water_1km_2010": "Open water within 1 km (share, 2010)",
    "water_250m_2010": "Open water within 250 m (share, 2010)",
    "fetch_mean_m": "Mean fetch (m, 16 directions, capped at 10 km)",
    "pre_rate": "Pre-spill edge-loss trend 1999-2008 (m/yr, Landsat)",
}

# Why a cell has no prediction. Keys are the `status` values written by scripts/build_p5_demo.py.
STATUS_TEXT = {
    "in_scope": "In scope: salt-marsh edge cell used to fit the model.",
    "not_salt_marsh": "Out of scope: shoreline is not ESI 10A salt marsh; the model and the treatment evidence cover salt marsh only.",
    "river_delta": "Out of scope: active Mississippi River delta (birdfoot). Land/water mapping fails in the river plume, so no model was fitted or tested here (P2).",
    "classification_unreliable": "Out of scope: area excluded because land/water mapping is unreliable on water-dominated or plume imagery (P2).",
    "not_edge_2010": "Out of scope: not a marsh edge in 2010 (almost all land or all water in the cell).",
    "image_quality": "Out of scope: imagery failed the quality checks for this cell.",
    "no_pre_spill_trend": "Out of scope: too few clear Landsat scenes for the pre-spill trend.",
    "measurement_disagreement": "Out of scope: 2010 aerial and 2007-2009 Landsat land maps disagree by more than 0.4 here.",
}

# Tool treatment -> evidence group (D13, proposed; awaiting Jaison). natural_attenuation is the baseline.
TREATMENT_EVIDENCE = {
    "natural_attenuation": "none",
    "manual_removal": "manual",
    "mechanical_removal": "mechanical",
}
RESTORATION_ADDONS = {"planting (after mechanical cleanup)": "mechanical+planting"}

# Scenario inputs implied by a salt-marsh edge cell. ASSUMED values are labelled in the dashboard.
OIL_COVERAGE_BY_CLASS = {"Heavy": 80.0, "Moderate": 50.0, "Light": 25.0, "Very_Light": 10.0, "NOO": 0.0}  # ASSUMED
FETCH_EXPOSURE_BREAKS = [(500, "low"), (2000, "moderate"), (5000, "high")]  # ASSUMED; above 5 km = very_high


@lru_cache(maxsize=1)
def load_model(path: str = str(MODEL_PATH)) -> dict:
    with open(path) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_sites(path: str = str(SITES_PATH)) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"cell": str, "segment": str, "cell_2km": str})


def _design(values: dict, model: dict) -> np.ndarray:
    x = [1.0]
    for name in model["terms"][1:]:
        if name == "log_fetch":
            x.append(float(np.log(values["fetch_mean_m"] + model["fetch_offset_m"])))
        else:
            x.append(float(values[name]))
    return np.array(x)


def predict_edge_loss(values: dict, model: dict | None = None) -> dict:
    """Expected NAIP edge-loss rate 2010-2015 (m/yr) with a 90% interval, for one set of inputs.

    values needs the four FEATURES. Raises ValueError if any is missing; callers check scope first.
    """
    model = model or load_model()
    missing = [f for f in FEATURES if values.get(f) is None or pd.isna(values.get(f))]
    if missing:
        raise ValueError(f"missing inputs: {missing}")
    point = float(_design(values, model) @ np.array(model["coefficients"]))
    lo, hi = model["interval_offsets"]
    return {"rate": point, "lo": point + lo, "hi": point + hi, "level": model["interval_level"]}


@dataclass
class Flags:
    in_scope: bool
    out_of_scope: list[str] = field(default_factory=list)
    extrapolation: list[str] = field(default_factory=list)
    evidence_scope: list[str] = field(default_factory=list)


def site_flags(values: dict, status: str = "in_scope", habitat: str = "10A", oiling: str | None = None,
               lat: float | None = None, lon: float | None = None, model: dict | None = None) -> Flags:
    """Scope and extrapolation flags for a site (plan section 4)."""
    model = model or load_model()
    out, extra, ev = [], [], []
    if status != "in_scope":
        out.append(STATUS_TEXT.get(status, f"Out of scope: {status}."))
    elif habitat != "10A":
        out.append(STATUS_TEXT["not_salt_marsh"])
    missing = [FEATURE_LABELS[f] for f in FEATURES if values.get(f) is None or pd.isna(values.get(f))]
    if missing and not out:
        out.append("Out of scope: missing input(s): " + "; ".join(missing) + ".")
    if not out:
        for f in FEATURES:
            lo, hi = model["training_range"][f]["p01"], model["training_range"][f]["p99"]
            v = float(values[f])
            if v < lo or v > hi:
                extra.append(f"{FEATURE_LABELS[f]} = {v:.3g} is outside the central 98% of training cells "
                             f"({lo:.3g} to {hi:.3g}); the prediction is an extrapolation.")
        if lat is not None and lon is not None:
            box = model["training_box"]
            if not (box["lat_min"] <= lat <= box["lat_max"] and box["lon_min"] <= lon <= box["lon_max"]):
                extra.append("Site lies outside the area of the training cells (coastal Louisiana, Terrebonne to "
                             "Breton Sound); the model has not been tested there.")
    if oiling != "Heavy":
        ev.append("Treatment evidence (Zengel et al. 2015, 2022) covers heavily oiled salt marsh only; "
                  f"this site is {'not classed' if oiling is None else oiling.replace('_', ' ')}, so treatment "
                  "effects are shown for reference only.")
    return Flags(in_scope=not out, out_of_scope=out, extrapolation=extra, evidence_scope=ev)


def _fmt(effect: float, lo: float, hi: float, unit: str = "") -> str:
    return f"{effect:+.2f}{unit} ({lo:+.2f} to {hi:+.2f})"


def treatment_evidence(treatments: list[str], oiling: str | None = "Heavy") -> pd.DataFrame:
    """Evidence per tool treatment against natural recovery, with 90% intervals (D11).

    Columns: treatment, evidence_group, erosion_0_2, erosion_2_8, veg_cover_yr2, note.
    Erosion is extra marsh-edge erosion in m/yr (positive = more erosion than natural recovery).
    """
    from src.shoreline_remediation.treatment_effects import erosion_prior, treatment_prior

    oil = "heavy" if oiling == "Heavy" else "other"
    rows = []
    items = [(t, TREATMENT_EVIDENCE.get(t)) for t in treatments] + list(RESTORATION_ADDONS.items())
    for name, group in items:
        row = {"treatment": name, "evidence_group": group or "none found"}
        if group is None:
            row.update(erosion_0_2="no outcome evidence", erosion_2_8="no outcome evidence",
                       veg_cover_yr2="no outcome evidence", note="No field outcome data found for this method in marsh.")
        elif group == "none":
            row.update(erosion_0_2="baseline (0)", erosion_2_8="baseline (0)", veg_cover_yr2="baseline (0)",
                       note="Natural recovery is the comparison group in both studies.")
        else:
            a = erosion_prior(group, "2010-2012", oiling=oil)
            b = erosion_prior(group, "2012-2018", oiling=oil)
            row["erosion_0_2"] = _fmt(a["effect"], a["lo"], a["hi"], " m/yr")
            row["erosion_2_8"] = _fmt(b["effect"], b["lo"], b["hi"], " m/yr")
            if group in ("manual", "mechanical"):
                v = treatment_prior(group, 2, oiling=oil)
                row["veg_cover_yr2"] = _fmt(v.veg_cover_effect, v.veg_cover_lo, v.veg_cover_hi, " pts")
            else:
                row["veg_cover_yr2"] = "see Zengel 2015 planting contrast (Spartina cover)"
            note = a["note"]
            if group == "mechanical":
                note += " Mechanical plots were the most heavily oiled, so oiling and method are confounded."
            if group == "mechanical+planting":
                note += " Planting was randomized against mechanical-only plots."
            row["note"] = note
        rows.append(row)
    return pd.DataFrame(rows)


def site_scenario_inputs(site: dict, oil_category: str = "light") -> list[tuple[str, str, str]]:
    """(input, value, basis) for the rule screening of a salt-marsh edge cell."""
    fetch = site.get("fetch_mean_m")
    exposure = "very_high"
    if fetch is not None and not pd.isna(fetch):
        for limit, label in FETCH_EXPOSURE_BREAKS:
            if fetch < limit:
                exposure = label
                break
    else:
        exposure = "moderate"
    oiling = site.get("max_oiling") or "NOO"
    return [
        ("shoreline_type", "marsh", "ESI 10A salt marsh (SCAT)"),
        ("shoreline_sensitivity", "very_high", "ESI 10 is the most sensitive shoreline class"),
        ("habitat_type", "salt_marsh", "ESI 10A"),
        ("oil_category", oil_category, "chosen in this view (DWH oil was a light crude, weathered on arrival)"),
        ("oil_coverage", f"{OIL_COVERAGE_BY_CLASS.get(oiling, 0.0):.0f}", f"ASSUMED from SCAT class {oiling}"),
        ("wave_exposure", exposure, "ASSUMED from mean fetch (<0.5 km low, <2 km moderate, <5 km high)"),
        ("tidal_range", "low", "northern Gulf of Mexico is microtidal"),
        ("season", "summer", "DWH oil reached Louisiana marsh in summer 2010"),
        ("substrate_permeability", "low", "ASSUMED: fine-grained marsh soils"),
        ("oil_thickness_mm", "5", "ASSUMED"),
        ("penetration_depth_cm", "2", "ASSUMED"),
        ("subsurface_oil", "False", "ASSUMED"),
        ("accessibility", "restricted", "ASSUMED: boat access, soft soils"),
        ("recovery_potential", "moderate", "ASSUMED"),
        ("waste_handling", "moderate", "ASSUMED"),
    ]


def site_scenario(site: dict, oil_category: str = "light"):
    """Scenario object for the existing rule screening, built from site_scenario_inputs."""
    from src.shoreline_remediation.data_model import Scenario

    v = {k: val for k, val, _ in site_scenario_inputs(site, oil_category)}
    return Scenario(
        shoreline_type=v["shoreline_type"], shoreline_sensitivity=v["shoreline_sensitivity"],
        oil_category=v["oil_category"], oil_coverage=float(v["oil_coverage"]), oil_thickness=float(v["oil_thickness_mm"]),
        penetration_depth_cm=float(v["penetration_depth_cm"]), wave_exposure=v["wave_exposure"],
        tidal_range=v["tidal_range"], season=v["season"], substrate_permeability=v["substrate_permeability"],
        surface_oil=v["oil_coverage"] != "0", subsurface_oil=False, accessibility=v["accessibility"],
        habitat_type=v["habitat_type"], recovery_potential=v["recovery_potential"], waste_handling=v["waste_handling"],
    )
