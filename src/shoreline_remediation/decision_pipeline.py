"""Fixed, logged decision pipeline (V4 F9; D17, D30, D31). Plan: docs/F9_PIPELINE_PLAN.md.

Eight steps in a fixed order, each logged (inputs, outputs, source ids) in `DecisionReport.trace`:
    1 characterise  2 hard constraints  3 do no harm  4 benefit vs natural recovery
    5 endpoint and time  6 trade-offs  7 recommendation classes  8 report
There is no weighted score: outcomes stay separate (D13, D17) and no language model is involved.

Entry points:
    run_decision(inputs, ...)  inputs = Scenario (generic shoreline) or a site dict from data/demo/p5_sites.csv
    decide_case(case_row, ...) a historical case (validation/historical_validation.CASES style) -> DecisionReport
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import knowledge, registry
from . import scenario_composer as sc
from . import site_evidence as se
from .data_model import Scenario, TREATMENT_LIBRARY
from .model_interface import ScenarioRequest, SiteRecord

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "data" / "knowledge"
PIPELINE_VERSION = "f9-v1"
PLANTING = sc.PLANTING
DEFAULT_OPTIONS = list(TREATMENT_LIBRARY) + [PLANTING]
NATURAL = sc.NATURAL
DEFAULT_SEED = 20261112
STEP_NAMES = ("characterise", "hard_constraints", "do_no_harm", "benefit_vs_natural_recovery",
              "endpoint_and_time", "trade_offs", "recommendation", "report")

CLASS_LABELS = {"A": "allowed, field evidence of benefit",
                "B": "allowed, no clear evidence either way",
                "C": "natural recovery with monitoring",
                "D": "allowed but harm reported under some conditions",
                "E": "excluded"}
ORDER_BASIS = ("within a class: lower bound of the 90% benefit interval where it exists (edge loss avoided by year 8 in m, "
               "then vegetation cover ratio at year 2, then literature lnRR lower bound; units are never mixed), then the "
               "ASSUMED ecological score (higher = lower disturbance first), then name")
OUT_OF_SCOPE_TEXT = ("this tool covers oil on shorelines; other contaminants, cost optimisation and offshore response are "
                     "outside its scope (D30)")
TIER_MESSAGES = {
    "validated": ("Heavily oiled salt marsh in the northern Gulf of Mexico: the marsh-edge loss model and the soil PAH-sum "
                  "decline are validated (held-out, one spill). Treatment differences (composer) and the vegetation curve "
                  "are experimental and carry that badge."),
    "experimental": ("Experimental: numbers are shown with an experimental badge and the reason; they are not validated "
                     "forecasts for this input."),
    "rules_and_literature": ("Rules and literature only: screening verdicts and literature evidence verdicts; there is no "
                             "site-specific forecast for this shoreline type."),
}

# Mapping of Scenario.shoreline_type / habitat to the habitat classes of evidence_verdicts.csv.
_MARSH_TYPES = {"salt_marsh", "marsh", "mudflat", "peat", "tundra"}
_ROCKY_TYPES = {"bedrock", "boulder", "cobble"}
_BEACH_TYPES = {"sand_beach", "mixed_sediment"}
# ASSUMED breaks reading site_evidence.OIL_COVERAGE_BY_CLASS backwards, used only for a Scenario without an oiling class.
_COVERAGE_BREAKS = ((70.0, "Heavy"), (40.0, "Moderate"), (20.0, "Light"))
_PAH_KEY = {"Heavy": "heavy", "Moderate": "moderate", "Light": "light", "Very_Light": "very_light", "NOO": "none"}

# ASSUMED aliases: condition / mangrove rows without a tool code mapped to library options.
_CONDITION_ALIAS = {"vegetation cutting": ["vegetation_cutting"], "sediment removal / excavation": ["mechanical_removal"],
                    "in-situ burning": []}
_MANGROVE_NAME_ALIAS = {"vegetation_cutting": "vegetation cutting or removal of oiled trees",
                        "mechanical_removal": "sediment removal or excavation",
                        PLANTING: "replanting after an oil spill"}
_MANGROVE_CODE_ALIAS = {"high_pressure_heated_washing": "high_pressure_washing"}
_MANGROVE_VERDICT = {"acceptable": "eligible", "conditional": "conditional", "not_recommended": "ineligible"}
# Conditions the input season can decide (condition text prefix -> test on the season).
_SEASON_CONDITIONS = {"growing season": lambda s: s in {"spring", "summer"},
                      "autumn or winter": lambda s: s in {"autumn", "fall", "winter"}}

_COMPOSER_CAVEAT = ("Paired difference from one site's field evidence (Bay Jimmy, Zengel et al.), the same at any heavily "
                    "oiled marsh site; the composer is experimental (R3 bias gate failed, FINDINGS_V4 26).")
_OPTION_CAVEAT = {
    "manual_removal": "Observational: treatment classes were not randomly assigned.",
    "mechanical_removal": "Observational; mechanical plots were the most heavily oiled, so oiling and method are confounded.",
    PLANTING: ("Evidence is planted vs oil-untreated plots inside mechanically treated areas (planting randomised, Zengel 2022); "
               "mechanical removal itself is excluded on marsh by rule, so the two rules are in tension."),
}


# ---------------------------------------------------------------------------------------------------------------
# Report

@dataclass
class DecisionReport:
    headline: str
    scope_tier: str
    scope_message: str
    options: list
    natural_recovery: dict
    plots: dict
    trace: list
    version: dict
    characterisation: dict = field(default_factory=dict)

    def classes(self) -> dict:
        out = {c: [] for c in CLASS_LABELS}
        for row in self.options:
            out[row["recommendation_class"]].append(row["option"])
        return out

    def option(self, name: str) -> dict:
        for row in self.options:
            if row["option"] == name:
                return row
        raise KeyError(name)

    def to_dict(self) -> dict:
        return _jsonable(dataclasses.asdict(self))

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, allow_nan=False)


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in (sorted(x, key=str) if isinstance(x, (set, frozenset)) else x)]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, (Path, pd.Timestamp)):
        return str(x)
    return x


def _num(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) or (not isinstance(x, str) and pd.isna(x)) else float(x)


# ---------------------------------------------------------------------------------------------------------------
# Cached loads

@lru_cache(maxsize=1)
def _rule_text() -> dict:
    df = pd.read_csv(knowledge.SCREENING_RULE_CSV)
    return {r.rule_id: (r.reason, r.source) for r in df.itertuples()}


@lru_cache(maxsize=1)
def _verdicts() -> pd.DataFrame:
    return pd.read_csv(KNOW / "evidence_verdicts.csv")


@lru_cache(maxsize=1)
def _conditions() -> pd.DataFrame:
    return pd.read_csv(KNOW / "treatment_conditions.csv").fillna("")


@lru_cache(maxsize=1)
def _mangrove_screening() -> pd.DataFrame:
    return pd.read_csv(KNOW / "mangrove_screening.csv").fillna("")


@lru_cache(maxsize=1)
def _literature() -> pd.DataFrame:
    return pd.read_csv(KNOW / "literature_effects.csv", dtype=str).fillna("")


@lru_cache(maxsize=1)
def _technology() -> dict:
    return {r.code: r.secondary_impacts for r in knowledge.load_technology().itertuples()}


@lru_cache(maxsize=1)
def _git_commit() -> dict:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5)
        commit = out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {"git_commit": commit or None}


@lru_cache(maxsize=1)
def _table_checksums() -> dict:
    files = [KNOW / "evidence_verdicts.csv", KNOW / "treatment_conditions.csv", KNOW / "mangrove_screening.csv",
             KNOW / "literature_effects.csv", *knowledge.all_table_paths()]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in files}


@lru_cache(maxsize=32)
def _compose_cached(features: tuple, oiling: str, pred_rate: float | None, options: tuple, n_draws: int, seed: int):
    site = {"max_oiling": oiling}
    if pred_rate is not None:
        site["pred_rate"] = pred_rate
    else:
        site.update(dict(zip(se.FEATURES, features)))
    return sc.compose(site, list(options), horizon_years=8, n_draws=n_draws, seed=seed)


def habitat_class(habitat: str) -> str:
    """Habitat class used by evidence_verdicts.csv."""
    h = habitat.lower()
    if h == "mangrove":
        return "mangrove"
    if h in _MARSH_TYPES:
        return "marsh"
    if h in _ROCKY_TYPES:
        return "rocky/hard"
    if h in _BEACH_TYPES:
        return "sand/gravel beach"
    return "other"


def _literature_habitat(text: str) -> str:
    # same keywords as validation/literature_pooling._habitat_class
    value = text.lower()
    if "mangrove" in value or "rhizophora" in value:
        return "mangrove"
    if any(w in value for w in ("marsh", "spartina", "salicornia", "wetland")):
        return "marsh"
    if any(w in value for w in ("rock", "bedrock", "hard substrate", "riprap", "seawall")):
        return "rocky/hard"
    if any(w in value for w in ("sand", "gravel", "pebble", "cobble", "beach", "sediment")):
        return "sand/gravel beach"
    return "other"


def _code(option: str) -> str:
    return "planting" if option == PLANTING else option


# ---------------------------------------------------------------------------------------------------------------
# Trace

def _log(trace: list, step: int, inputs: dict, outputs: dict, sources: list) -> None:
    trace.append({"step": step, "name": STEP_NAMES[step - 1], "inputs": _jsonable(inputs),
                  "outputs": _jsonable(outputs), "sources": list(sources)})


# ---------------------------------------------------------------------------------------------------------------
# Step 1

def _oiling_from_coverage(coverage: float) -> str:
    for limit, name in _COVERAGE_BREAKS:
        if coverage >= limit:
            return name
    return "Very_Light" if coverage > 0 else "NOO"


def _resolve_oil(oil, default: str, temperature_c: float) -> tuple[str, str]:
    if oil is None:
        return default, "input"
    text = str(oil).strip()
    if text.lower() in {"light", "medium", "heavy", "solid"}:
        return text.lower(), "chosen category"
    from . import oil_library
    info = oil_library.scenario_oil_inputs(text, temperature_c)
    return info["oil_category"], f"ADIOS {info['oil_id']} ({info['name']}, API {info['api_gravity']:.1f})"


def _refusal(contaminant: str, objective: str, response_zone: str) -> str | None:
    reasons = []
    if str(contaminant).lower() not in {"oil", "crude oil", "petroleum"}:
        reasons.append(f"contaminant '{contaminant}' is not oil")
    if "cost" in str(objective).lower():
        reasons.append("cost optimisation is requested and no sourced cost data exist")
    if str(response_zone).lower() not in {"shoreline", "shore"}:
        reasons.append(f"response zone '{response_zone}' is not the shoreline")
    if not reasons:
        return None
    return "Out of scope: " + "; ".join(reasons) + ". " + OUT_OF_SCOPE_TEXT[0].upper() + OUT_OF_SCOPE_TEXT[1:] + "."


def _characterise(inputs, habitat, oiling_class, oil, season, assumptions) -> dict:
    site = None
    if isinstance(inputs, Scenario):
        scenario = inputs
        habitat = habitat or scenario.shoreline_type
        oil_default = scenario.oil_category
        oiling = oiling_class or _oiling_from_coverage(float(scenario.oil_coverage))
        oiling_basis = ("input" if oiling_class else
                        "derived from oil_coverage with ASSUMED breaks (>=70 Heavy, >=40 Moderate, >=20 Light, >0 Very_Light)")
    elif isinstance(inputs, dict):
        site = dict(inputs)
        habitat = habitat or "salt_marsh"
        if oiling_class:
            site["max_oiling"] = oiling_class
        oiling = site.get("max_oiling") or "NOO"
        oiling_basis = "input" if oiling_class else "site max_oiling (SCAT)"
        oil_default = "light"
        scenario = se.site_scenario(site, oil_category=oil_default)
    else:
        raise TypeError("inputs must be a Scenario or a site dict")
    hclass = habitat_class(habitat)
    category, oil_source = _resolve_oil(oil, oil_default, scenario.temperature_c)
    over = {"oil_category": category}
    if season:
        over["season"] = str(season).lower()
    if habitat.lower() == "salt_marsh" and scenario.shoreline_type.lower() not in _MARSH_TYPES:
        over["shoreline_type"] = "marsh"
    elif habitat.lower() == "mangrove":
        over["shoreline_type"] = "mangrove"
    scenario = dataclasses.replace(scenario, **over)
    salt_marsh = habitat.lower() in {"salt_marsh", "marsh"}
    flags = None
    if site is not None and salt_marsh:
        values = {f: site.get(f) for f in se.FEATURES}
        flags = se.site_flags(values, status=site.get("status", "in_scope"), habitat=str(site.get("esi_main") or "10A"),
                              oiling=oiling, lat=_num(site.get("lat")), lon=_num(site.get("lon")))
    return {"scenario": scenario, "site": site, "habitat": habitat.lower(), "habitat_class": hclass, "salt_marsh": salt_marsh,
            "oiling": oiling, "oiling_basis": oiling_basis, "oil_category": category, "oil_source": oil_source,
            "flags": flags, "assumptions": list(assumptions or [])}


def _scope_tier(ctx: dict) -> tuple[str, str, list]:
    flags = ctx["flags"]
    if ctx["salt_marsh"]:
        reasons = []
        if ctx["site"] is None:
            reasons.append("no edge cell given: generic marsh scenario, transfer of the Bay Jimmy evidence is untested")
        elif flags is not None and (flags.out_of_scope or flags.extrapolation):
            reasons += flags.out_of_scope + flags.extrapolation
        if ctx["oiling"] != "Heavy":
            reasons.append(f"oiling class {ctx['oiling']}: treatment evidence covers heavily oiled marsh only")
        if not reasons:
            return "validated", TIER_MESSAGES["validated"], []
        return "experimental", TIER_MESSAGES["experimental"] + " Reasons: " + " | ".join(reasons), reasons
    if ctx["habitat_class"] == "mangrove":
        reasons = ["mangrove damage model: one spill (Bahia Las Minas, Panama), oiling effect only, no treatment effects"]
        return "experimental", TIER_MESSAGES["experimental"] + " Reasons: " + reasons[0], reasons
    return "rules_and_literature", TIER_MESSAGES["rules_and_literature"], []


# ---------------------------------------------------------------------------------------------------------------
# Step 2

def _screen_option(option: str, ctx: dict) -> dict:
    hc = ctx["habitat_class"]
    if option == PLANTING and hc not in {"marsh", "mangrove"}:
        return {"verdict": "ineligible", "rule_id": "f9:planting_applicability",
                "reason": "planting add-on applies to vegetated wetlands only (pipeline applicability rule, not a table row)",
                "source": "docs/F9_PIPELINE_PLAN.md"}
    if hc == "mangrove":
        return _screen_mangrove(option)
    scenario = ctx["scenario"]
    for rule in knowledge.load_screening_rules():
        if rule.matches_treatment(option) and rule.condition_holds(scenario):
            reason, source = _rule_text()[rule.rule_id]
            return {"verdict": rule.verdict, "rule_id": rule.rule_id, "reason": reason, "source": source}
    return {"verdict": "conditional", "rule_id": "none", "reason": "no rule matched", "source": "screening_rule.csv"}


def _screen_mangrove(option: str) -> dict:
    df = _mangrove_screening()
    code = _MANGROVE_CODE_ALIAS.get(option, option)
    row = df[df.tool_code == code] if code != PLANTING else df[df.treatment == _MANGROVE_NAME_ALIAS[PLANTING]]
    if row.empty and option in _MANGROVE_NAME_ALIAS:
        row = df[df.treatment == _MANGROVE_NAME_ALIAS[option]]
    if row.empty:
        return {"verdict": "ineligible", "rule_id": "mangrove_screening:unscreened",
                "reason": "no mangrove screening row for this option; excluded until screened", "source": "mangrove_screening.csv"}
    r = row.iloc[0]
    slug = re.sub(r"[^a-z0-9]+", "_", r.treatment.lower()).strip("_")
    return {"verdict": _MANGROVE_VERDICT[r.verdict], "rule_id": f"mangrove_screening:{slug}",
            "reason": r.reason if r.reason and r.reason != "-" else f"mangrove screening verdict: {r.verdict}",
            "source": f"mangrove_screening.csv ({r.source}); {r.provenance}", "conditions": r.conditions}


# ---------------------------------------------------------------------------------------------------------------
# Step 3 and the evidence verdicts

def _verdict_rows(option: str, hclass: str) -> pd.DataFrame:
    v = _verdicts()
    return v[(v.technology == _code(option)) & (v.habitat == hclass)]


def _aggregate_verdicts(rows: pd.DataFrame) -> tuple[str, str, float | None]:
    if rows.empty:
        return "no evidence", "no evidence_verdicts row for this technology and habitat class", None
    kinds = set(rows.verdict)
    benefit, harm = "evidence of benefit" in kinds, "evidence of harm" in kinds
    if benefit and harm:
        verdict = "mixed"
    elif benefit:
        verdict = "evidence of benefit"
    elif harm:
        verdict = "evidence of harm"
    elif "no clear difference" in kinds:
        verdict = "no clear difference"
    else:
        verdict = "no evidence"
    basis = "; ".join(f"{r.outcome_family}: {r.verdict} ({r.basis})" for r in rows.itertuples())
    bounds = [b for r in rows[rows.verdict == "evidence of benefit"].itertuples()
              for b in [_num(r.pi_lo) if _num(r.pi_lo) is not None else _num(r.ci_lo)] if b is not None]
    return verdict, basis, (min(bounds) if bounds else None)


def _condition_rows(option: str, ctx: dict) -> list:
    if ctx["habitat_class"] != "marsh":
        return []
    out = []
    for r in _conditions().itertuples():
        targets = [r.tool_code] if r.tool_code else _CONDITION_ALIAS.get(r.treatment, [])
        if _code(option) not in targets:
            continue
        status = "unknown (ask user)"
        season = ctx["scenario"].season.lower()
        for prefix, test in _SEASON_CONDITIONS.items():
            if r.condition.lower().startswith(prefix):
                status = "met by input season" if test(season) else "not met by input season"
        out.append({"condition": r.condition, "effect_when_met": r.effect_when_met, "status": status,
                    "source": r.source, "provenance": r.provenance})
    return out


# ---------------------------------------------------------------------------------------------------------------
# Step 4

def _direction(lo: float, hi: float) -> str:
    return "benefit" if lo > 0 else ("harm" if hi < 0 else "no clear difference")


def _composer_outcomes(row, anchor: int) -> list:
    outs = []
    for y in (2, 5, 8):
        if f"paired_diff_cum_edge_loss_y{y}_median" not in row.index:
            continue
        med, lo, hi = (row[f"paired_diff_cum_edge_loss_y{y}_{k}"] for k in ("median", "lo90", "hi90"))
        b_lo, b_med, b_hi = -hi, -med, -lo
        outs.append({"outcome": "edge_loss_avoided_m", "year": y, "median": float(b_med), "lo90": float(b_lo), "hi90": float(b_hi),
                     "unit": "m of cumulative marsh-edge loss avoided vs natural recovery (positive = less loss)",
                     "direction": _direction(b_lo, b_hi), "decision_point": y == anchor})
        vm = row.get(f"paired_diff_veg_ratio_y{y}_median")
        if vm is not None and pd.notna(vm):
            v_lo, v_hi = row[f"paired_diff_veg_ratio_y{y}_lo90"], row[f"paired_diff_veg_ratio_y{y}_hi90"]
            outs.append({"outcome": "veg_cover_ratio_gain", "year": y, "median": float(vm), "lo90": float(v_lo), "hi90": float(v_hi),
                         "unit": "vegetation cover ratio to reference, option minus natural recovery (positive = more cover)",
                         "direction": _direction(v_lo, v_hi), "decision_point": y == 2})
    return outs


# ---------------------------------------------------------------------------------------------------------------
# Step 5

def _no_model(quantity: str, reason: str) -> dict:
    return {"quantity": quantity, "status": "no model", "value": None, "lo90": None, "hi90": None, "reason": reason}


def _reference_rows(ctx: dict, natural_tidy, anchor: int) -> list:
    rows = []
    hc, oiling = ctx["habitat_class"], ctx["oiling"]
    flags, site = ctx["flags"], ctx["site"]
    if ctx["habitat_class"] == "mangrove":
        model = registry.get("mangrove_damage_v1")
        for ys in range(1, 6):
            p = model.predict(SiteRecord(site_id="mangrove", habitat="mangrove", oiling="oiled",
                                         fields={"year_since_spill": ys}), ScenarioRequest(horizon_years=ys))
            rows.append({"quantity": f"oiling effect on share of prop roots recorded dead, year {ys} after the spill",
                         "value": p.value, "lo90": p.interval_lo, "hi90": p.interval_hi, "unit": p.unit,
                         "model_id": model.model_id, "state": p.state, "scope": p.scope, "scope_reasons": p.scope_reasons,
                         "note": "oiled minus unoiled; damage was still rising in year 4-5, so no recovery time can be given"})
        rows.append(_no_model("PAH-sum half-life", "marsh soil model; not used for mangrove"))
        rows.append(_no_model("vegetation time to 80% of reference", "marsh curve; not used for mangrove"))
        rows.append(_no_model("natural edge loss to year 5 and 8", "marsh-edge model; not used for mangrove"))
        return rows
    if not ctx["salt_marsh"]:
        reason = f"no registered model covers {ctx['habitat']} shorelines"
        return [_no_model(q, reason) for q in ("PAH-sum half-life", "vegetation time to 80% of reference",
                                               "natural edge loss to year 5 and 8")]
    pah = registry.get("pah_decline_v1")
    key = _PAH_KEY.get(oiling, "pooled")
    pred = pah.predict(SiteRecord(site_id="pah", habitat=ctx["habitat"], oiling=key), ScenarioRequest())
    cls = pah.card["half_life_years_by_class"][key]
    if cls["half_life"] is None:
        rows.append({"quantity": f"PAH-sum half-life ({key})", "value": None, "lo90": cls["lo90"], "hi90": None, "unit": "years",
                     "status": "no decline detected", "model_id": pah.model_id, "state": pred.state, "scope": pred.scope,
                     "scope_reasons": pred.scope_reasons, "note": "lower 90% bound only; PAH sum did not decline"})
    else:
        rows.append({"quantity": f"PAH-sum half-life ({key})", "value": cls["half_life"], "lo90": cls["lo90"], "hi90": cls["hi90"],
                     "unit": "years", "model_id": pah.model_id, "state": pred.state, "scope": pred.scope,
                     "scope_reasons": pred.scope_reasons,
                     "note": "sum of PAH in soil (physical loss plus degradation); validated within Deepwater Horizon only"})
    veg = registry.get("veg_recovery_v1")
    t80, (t80_lo, t80_hi) = veg.card["years_to_80_of_reference"], veg.card["intervals_90"]["years_to_80"]
    note = veg.card["limits"]
    if oiling == "Heavy":
        note += "; " + sc.VEG_CURVE_SCOPE_HEAVY
    rows.append({"quantity": "vegetation time to 80% of reference cover", "value": t80, "lo90": t80_lo, "hi90": t80_hi, "unit": "years",
                 "model_id": veg.model_id, "state": veg.state, "scope": "in range", "scope_reasons": [],
                 "evidence_grade": veg.card.get("verdict"), "note": note})
    cell_ok = site is not None and flags is not None and flags.in_scope
    if not cell_ok:
        rows.append(_no_model("natural edge loss to year 5 and 8",
                              "needs a marsh edge cell in scope of the edge-loss model" if site is None else "; ".join(flags.out_of_scope)))
        return rows
    el = registry.get("edge_loss_v1")
    p = el.predict(SiteRecord(site_id=str(site.get("cell", "site")), habitat=str(site.get("esi_main") or "10A"),
                              lat=_num(site.get("lat")), lon=_num(site.get("lon")), oiling=oiling,
                              fields={**{f: float(site[f]) for f in se.FEATURES}, "status": site.get("status", "in_scope")}),
                   ScenarioRequest())
    rows.append({"quantity": "edge-loss rate 2010-2015 (deployed model, all-cell fit)", "value": p.value, "lo90": p.interval_lo,
                 "hi90": p.interval_hi, "unit": p.unit, "model_id": el.model_id, "state": p.state, "scope": p.scope,
                 "scope_reasons": p.scope_reasons, "note": "held out by basin; the interval is for one cell"})
    comp = registry.get("composer_natural_recovery_v1")
    for y in sorted({5, anchor}):
        t = natural_tidy[(natural_tidy.outcome == "cumulative_edge_loss_m") & (natural_tidy.year == y)].iloc[0]
        rows.append({"quantity": f"natural recovery cumulative edge loss to year {y}", "value": float(t["median"]),
                     "lo90": float(t.lo90), "hi90": float(t.hi90), "unit": "m", "model_id": comp.model_id, "state": comp.state,
                     "scope": "in range", "scope_reasons": [],
                     "note": (sc.NATURAL_RECOVERY_BIAS_NOTE if oiling == "Heavy" else "clean-edge baseline, no oil excess applied")})
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Step 6

def _tradeoffs(option: str, hclass: str) -> dict:
    lit = _literature()
    rows = lit[(lit.technology == _code(option)) & (lit.habitat.map(_literature_habitat) == hclass)]
    prod = rows[rows.production_rate_m2_per_person_day != ""]
    waste = rows[rows.waste_per_m2 != ""]
    secondary = _technology().get(option)
    return {
        "production_rate": "; ".join(f"{r.production_rate_m2_per_person_day} m2/person-day ({r.effect_id})" for r in prod.itertuples()) or "not sourced",
        "waste": "; ".join(f"{r.waste_per_m2} ({r.effect_id})" for r in waste.itertuples()) or "not sourced",
        "cost_class": "not sourced",
        "secondary_impacts": secondary if secondary else "not sourced",
        "tradeoff_sources": sorted(set(prod.effect_id) | set(waste.effect_id)),
    }


# ---------------------------------------------------------------------------------------------------------------
# Pipeline

def run_decision(inputs, habitat: str | None = None, oiling_class: str | None = None, oil: str | None = None,
                 season: str | None = None, options: list | None = None, *, seed: int = DEFAULT_SEED, n_draws: int = 5000,
                 horizon_years: int = 8, contaminant: str = "oil", objective: str = "environmental_benefit",
                 response_zone: str = "shoreline", assumptions: list | None = None, label: str | None = None) -> DecisionReport:
    """Run the fixed eight-step pipeline (docs/F9_PIPELINE_PLAN.md). Deterministic for a given seed."""
    if not 2 <= int(horizon_years) <= 8:
        raise ValueError("horizon_years must be between 2 and 8 (no outcome data beyond 8 years; scenario_composer refuses more)")
    anchor = max(y for y in (2, 5, 8) if y <= horizon_years)
    options = list(dict.fromkeys(list(options) if options else list(DEFAULT_OPTIONS)))
    unknown = [o for o in options if o not in DEFAULT_OPTIONS]
    if unknown:
        raise ValueError(f"unknown options {unknown}; known: {DEFAULT_OPTIONS}")
    if NATURAL not in options:
        options.insert(0, NATURAL)
    trace: list = []

    refusal = _refusal(contaminant, objective, response_zone)
    if refusal:
        return _refuse(trace, refusal, {"contaminant": contaminant, "objective": objective, "response_zone": response_zone}, label)

    ctx = _characterise(inputs, habitat, oiling_class, oil, season, assumptions)
    ctx["label"] = label
    tier, tier_message, tier_reasons = _scope_tier(ctx)
    scenario = ctx["scenario"]
    characterisation = {
        "label": label, "habitat": ctx["habitat"], "habitat_class": ctx["habitat_class"], "oil_category": ctx["oil_category"],
        "oil_source": ctx["oil_source"], "oiling_class": ctx["oiling"], "oiling_basis": ctx["oiling_basis"],
        "exposure": scenario.wave_exposure, "access": scenario.accessibility, "season": scenario.season,
        "sensitivity": scenario.shoreline_sensitivity, "shoreline_type_for_rules": scenario.shoreline_type,
        "input_kind": "site_dict" if ctx["site"] is not None else "scenario", "cell": (ctx["site"] or {}).get("cell"),
        "assumptions": ctx["assumptions"],
        "site_scope_flags": (dataclasses.asdict(ctx["flags"]) if ctx["flags"] is not None else None),
        "scope_tier": tier, "scope_reasons": tier_reasons,
    }
    _log(trace, 1, {"habitat": habitat, "oiling_class": oiling_class, "oil": oil, "season": season,
                    "input_kind": characterisation["input_kind"], "cell": characterisation["cell"]},
         characterisation, ["inputs", "oil_library (ADIOS)", "site_evidence.site_flags", "docs/F0_F1_SCOPE_AND_DECISIONS.md D30"])

    # Step 2
    screen = {o: _screen_option(o, ctx) for o in options}
    _log(trace, 2, {"options": options, "rule_source": "mangrove_screening.csv" if ctx["habitat_class"] == "mangrove" else "screening_rule.csv"},
         {o: {k: s[k] for k in ("verdict", "rule_id", "reason")} for o, s in screen.items()},
         ["data/knowledge/tables/screening_rule.csv" if ctx["habitat_class"] != "mangrove" else "data/knowledge/mangrove_screening.csv"])

    # Step 3
    hclass = ctx["habitat_class"]
    removed, flagged, verdict_info, cond_info = {}, {}, {}, {}
    for o in options:
        rows = _verdict_rows(o, hclass)
        verdict_info[o] = _aggregate_verdicts(rows)
        conds = _condition_rows(o, ctx)
        cond_info[o] = conds
        if o == NATURAL:
            continue
        harmful = rows[rows.verdict == "evidence of harm"]
        if not harmful.empty:
            removed[o] = [{"source": "evidence_verdicts.csv", "outcome_family": r.outcome_family,
                           "detail": f"evidence of harm in {hclass}: {r.basis}"} for r in harmful.itertuples()]
        harms = [c for c in conds if c["effect_when_met"] == "harms" and c["status"] != "not met by input season"]
        if harms:
            flagged[o] = [{"source": "treatment_conditions.csv",
                           "detail": f"harm reported under condition: {c['condition']} [{c['status']}] ({c['source']})"} for c in harms]
    _log(trace, 3, {"habitat_class": hclass, "sources": ["evidence_verdicts.csv", "treatment_conditions.csv (marsh)", "mangrove_screening.csv (mangrove)"]},
         {"removed": removed, "flagged": flagged}, ["data/knowledge/evidence_verdicts.csv", "data/knowledge/treatment_conditions.csv"])

    def excluded(o):
        return o != NATURAL and (screen[o]["verdict"] == "ineligible" or o in removed)

    # Step 4
    heavy_marsh = ctx["salt_marsh"] and ctx["oiling"] == "Heavy"
    cell_ok = ctx["site"] is not None and ctx["flags"] is not None and ctx["flags"].in_scope
    composer_opts = [o for o in options if o in sc.GROUPS and o != NATURAL and not excluded(o)] if heavy_marsh else []
    composer = {}
    tidy = summ = None
    if heavy_marsh or cell_ok:
        features = tuple(float(ctx["site"][f]) for f in se.FEATURES) if cell_ok else ()
        tidy, summ = _compose_cached(features, ctx["oiling"], None if cell_ok else 0.0, tuple(composer_opts), n_draws, seed)
        for o in composer_opts:
            row = summ[summ.option == o].iloc[0]
            composer[o] = {"outcomes": _composer_outcomes(row, anchor), "evidence_label": row["evidence"]}
    comp_model = registry.get("composer_natural_recovery_v1")
    step4 = {o: {"source": "scenario_composer.compose" if o in composer else "evidence_verdicts.csv",
                 "verdict": verdict_info[o][0]} for o in options}
    for o, c in composer.items():
        step4[o]["decision_outcomes"] = [x for x in c["outcomes"] if x["decision_point"]]
    _log(trace, 4, {"composer_used": bool(composer_opts), "options_composed": composer_opts, "seed": seed, "n_draws": n_draws,
                    "decision_points": f"edge loss avoided at year {anchor}; vegetation cover ratio at year 2",
                    "model": {"id": comp_model.model_id, "state": comp_model.state}}, step4,
         ["src/shoreline_remediation/scenario_composer.py", "data/knowledge/evidence_verdicts.csv", "models/registry.json"])

    # Step 5
    natural_tidy = tidy[tidy.option == NATURAL] if tidy is not None else None
    reference = _reference_rows(ctx, natural_tidy, anchor)
    _log(trace, 5, {"oiling_class": ctx["oiling"], "habitat_class": hclass},
         {"reference": reference}, ["models/registry.json", "results/pah_decline/by_oiling_class.csv", "models/veg_recovery_v1.json",
                                    "models/p5_edge_loss_v1.json", "models/mangrove_damage_v1.json"])

    # Step 6
    trade = {o: _tradeoffs(o, hclass) for o in options}
    _log(trace, 6, {"habitat_class": hclass}, {o: {k: v for k, v in t.items() if k != "tradeoff_sources"} for o, t in trade.items()},
         ["data/knowledge/literature_effects.csv", "data/knowledge/tables/technology.csv"])

    # Step 7
    rows = [_option_row(o, ctx, screen[o], removed.get(o), flagged.get(o), verdict_info[o], cond_info[o], composer.get(o),
                        trade[o], comp_model, excluded(o), anchor) for o in options]
    _assign_order(rows)
    headline = _headline(rows, tier, anchor)
    classes = {c: [r["option"] for r in rows if r["recommendation_class"] == c] for c in CLASS_LABELS}
    _log(trace, 7, {"class_rules": "E excluded > A benefit > D harm under conditions > B no clear evidence; C natural recovery",
                    "ordering": ORDER_BASIS}, {"classes": classes, "headline": headline}, ["steps 2-6"])

    # Step 8
    plots = _plots(rows, composer, tidy, summ, cell_ok, hclass, options, verdict_info)
    natural = {"option": NATURAL, "recommendation_class": "C", "label": CLASS_LABELS["C"], "reference": reference,
               "rule_verdict": screen[NATURAL]["verdict"], "evidence_verdict": verdict_info[NATURAL][0],
               "evidence_basis": verdict_info[NATURAL][1], "monitoring": "monitor canopy, recruitment and soil oil for at least 5 years"
               if ctx["habitat_class"] == "mangrove" else "monitor and compare with the reference numbers above"}
    models_used = sorted({r["model_id"] for r in reference if r.get("model_id")} | ({comp_model.model_id} if composer else set()))
    version = {"pipeline_version": PIPELINE_VERSION, **_git_commit(), "python": sys.version.split()[0], "numpy": np.__version__,
               "pandas": pd.__version__, "seed": seed, "n_draws": n_draws, "models_used": models_used,
               "models": {m: {"state": registry.get(m).state, "version": registry.get(m).model_version} for m in models_used},
               "knowledge_checksums": _table_checksums()}
    report = DecisionReport(headline=headline, scope_tier=tier, scope_message=tier_message, options=rows, natural_recovery=natural,
                            plots=plots, trace=trace, version=version, characterisation=characterisation)
    _log(trace, 8, {"n_options": len(rows)}, {"headline": headline, "scope_tier": tier, "models_used": models_used,
                                              "plot_keys": sorted(plots)}, ["steps 1-7"])
    report.trace = _jsonable(trace)
    return report


def _refuse(trace: list, message: str, inputs: dict, label) -> DecisionReport:
    _log(trace, 1, inputs, {"scope_tier": "out_of_scope", "refusal": message}, ["docs/F0_F1_SCOPE_AND_DECISIONS.md D30"])
    for step in range(2, 9):
        _log(trace, step, {}, {"skipped": "out of scope"}, [])
    return DecisionReport(headline=message, scope_tier="out_of_scope", scope_message=message, options=[],
                          natural_recovery={}, plots={}, trace=_jsonable(trace),
                          version={"pipeline_version": PIPELINE_VERSION, **_git_commit(), "models_used": []},
                          characterisation={"label": label, "scope_tier": "out_of_scope", "refusal": message})


def _option_row(o, ctx, screen, removed, flagged, verdict, conds, composer, trade, comp_model, excluded, anchor) -> dict:
    verdict_name, basis, lit_lb = verdict
    outcomes = composer["outcomes"] if composer else []
    decisions = [x for x in outcomes if x["decision_point"]]
    favourable = any(x["direction"] == "benefit" for x in decisions)
    unfavourable = any(x["direction"] == "harm" for x in decisions)
    flags = list(flagged or [])
    if unfavourable:
        flags.append({"source": "scenario_composer", "detail": "pre-specified outcome interval excludes zero in the unfavourable direction"})
    if o == NATURAL:
        cls = "C"
    elif excluded:
        cls = "E"
    elif (favourable or verdict_name == "evidence of benefit") and not unfavourable:
        cls = "A"
    elif flags or verdict_name == "mixed":
        cls = "D"
    else:
        cls = "B"
    reasons = []
    if cls == "E":
        if screen["verdict"] == "ineligible":
            reasons.append({"source": "rule", "rule_id": screen["rule_id"], "detail": screen["reason"]})
        reasons += removed or []
    edge = next((x for x in decisions if x["outcome"] == "edge_loss_avoided_m"), None)
    veg = next((x for x in decisions if x["outcome"] == "veg_cover_ratio_gain"), None)
    if edge is not None and (edge["direction"] != "no clear difference" or veg is None):
        group, lb, lb_unit = 0, edge["lo90"], f"edge loss avoided by year {anchor} (m)"
    elif veg is not None:
        group, lb, lb_unit = 1, veg["lo90"], "vegetation cover ratio gain at year 2"
    elif lit_lb is not None:
        group, lb, lb_unit = 2, lit_lb, "literature lnRR (benefit-oriented)"
    else:
        group, lb, lb_unit = 3, None, None
    eco = knowledge.ecological_score_explanation(o, ctx["scenario"])
    caveats = []
    if composer:
        caveats += [_OPTION_CAVEAT.get(o, ""), _COMPOSER_CAVEAT]
    cond_text = [f"{c['condition']} -> {c['effect_when_met']} [{c['status']}]" for c in conds]
    if screen.get("conditions"):
        cond_text.append(f"mangrove screening: {screen['conditions']}")
    return {
        "option": o, "recommendation_class": cls, "class_label": CLASS_LABELS[cls], "rank_in_class": None,
        "order_basis": ORDER_BASIS,
        "rule_verdict": screen["verdict"], "rule_id": screen["rule_id"], "rule_reason": screen["reason"], "rule_source": screen["source"],
        "do_no_harm": "removed" if removed else ("flagged" if flags else "passed"),
        "harm_flags": flags, "exclusion_reasons": reasons,
        "evidence_source": "scenario_composer" if composer else ("evidence_verdicts" if verdict_name != "no evidence" else "none"),
        "evidence_verdict": _composer_verdict(favourable, unfavourable) if composer else verdict_name,
        "evidence_basis": basis, "evidence_label": composer["evidence_label"] if composer else None,
        "benefit_outcomes": outcomes,
        "benefit_lower_bound": lb, "benefit_lower_bound_unit": lb_unit,
        "model_id": comp_model.model_id if composer else None, "model_state": comp_model.state if composer else None,
        "ecological_score_assumed": eco["score"], "ecological_basis": eco["basis"],
        "conditions": cond_text,
        "production_rate": trade["production_rate"], "waste": trade["waste"], "cost_class": trade["cost_class"],
        "secondary_impacts": trade["secondary_impacts"], "caveats": [c for c in caveats if c],
        "source_ids": sorted({"screening_rule.csv:" + screen["rule_id"], "ecological_score.csv", *trade["tradeoff_sources"]}),
        "_group": group,
    }


def _composer_verdict(favourable: bool, unfavourable: bool) -> str:
    if favourable and unfavourable:
        return "mixed (field, composer)"
    if favourable:
        return "evidence of benefit (field, composer)"
    if unfavourable:
        return "evidence of harm (field, composer)"
    return "no clear difference (field, composer: 90% interval includes zero)"


def _assign_order(rows: list) -> None:
    for cls in CLASS_LABELS:
        members = [r for r in rows if r["recommendation_class"] == cls]
        members.sort(key=lambda r: (r["_group"], -(r["benefit_lower_bound"] if r["benefit_lower_bound"] is not None else 0.0),
                                    -r["ecological_score_assumed"], r["option"]))
        for i, r in enumerate(members, 1):
            r["rank_in_class"] = i
    for r in rows:
        del r["_group"]
    rows.sort(key=lambda r: (list(CLASS_LABELS).index(r["recommendation_class"]), r["rank_in_class"]))


def _benefit_text(r: dict, anchor: int) -> str:
    edge = next((x for x in r["benefit_outcomes"] if x["decision_point"] and x["outcome"] == "edge_loss_avoided_m"), None)
    veg = next((x for x in r["benefit_outcomes"] if x["decision_point"] and x["outcome"] == "veg_cover_ratio_gain"), None)
    parts = []
    if edge and edge["direction"] == "benefit":
        parts.append(f"edge loss avoided by year {anchor} {edge['median']:.1f} m (90% {edge['lo90']:.1f} to {edge['hi90']:.1f})")
    if veg and veg["direction"] == "benefit":
        parts.append(f"vegetation cover ratio gain at year 2 {veg['median']:.2f} (90% {veg['lo90']:.2f} to {veg['hi90']:.2f})")
    return "; ".join(parts) if parts else r["evidence_verdict"]


def _headline(rows: list, tier: str, anchor: int) -> str:
    a = [r for r in rows if r["recommendation_class"] == "A"]
    if a:
        text = "Field evidence of benefit over natural recovery: " + "; ".join(f"{r['option']} ({_benefit_text(r, anchor)})" for r in a)
        if any(r["model_id"] for r in a):
            text += ". Differences are experimental composer output from one site's field evidence"
        return text + "."
    b = [r["option"] for r in rows if r["recommendation_class"] == "B"][:3]
    text = "No option is shown by evidence to beat natural recovery; monitor."
    if b:
        text += " Best allowed options with no clear evidence either way (class B): " + ", ".join(b) + "."
    else:
        text += " No allowed alternative has been identified."
    return text


def _plots(rows, composer, tidy, summ, cell_ok, hclass, options, verdict_info) -> dict:
    paired = [{"option": o, "outcome": x["outcome"], "year": x["year"], "median": x["median"], "lo90": x["lo90"], "hi90": x["hi90"],
               "unit": x["unit"], "direction": x["direction"], "decision_point": x["decision_point"]}
              for o, c in composer.items() for x in c["outcomes"]]
    traj = []
    if cell_ok and tidy is not None:
        top = [r["option"] for r in rows if r["recommendation_class"] in ("A", "B", "D") and r["option"] in composer][:3]
        t = tidy[(tidy.outcome == "cumulative_edge_loss_m") & tidy.option.isin([NATURAL] + top)]
        traj = [{"option": r.option, "year": int(r.year), "median": float(r.median), "lo90": float(r.lo90), "hi90": float(r.hi90)}
                for r in t.itertuples()]
    matrix = []
    for o in options:
        rs = _verdict_rows(o, hclass)
        if rs.empty:
            matrix.append({"option": o, "outcome_family": "any", "verdict": "no evidence", "source": "evidence_verdicts.csv",
                           "basis": "no row for this technology and habitat class"})
        for r in rs.itertuples():
            matrix.append({"option": o, "outcome_family": r.outcome_family, "verdict": r.verdict, "source": "evidence_verdicts.csv",
                           "basis": r.basis})
        for x in (composer[o]["outcomes"] if o in composer else []):
            if x["decision_point"]:
                matrix.append({"option": o, "outcome_family": x["outcome"], "verdict": "evidence of " + x["direction"]
                               if x["direction"] != "no clear difference" else x["direction"], "source": "scenario_composer",
                               "basis": f"paired difference at year {x['year']}: {x['median']:.2f} ({x['lo90']:.2f} to {x['hi90']:.2f})"})
    return {"paired_differences": paired,
            "cumulative_edge_loss": {"series": traj, "unit": "m", "note": "natural recovery vs top options; empty without an in-scope marsh edge cell"},
            "evidence_matrix": matrix}


# ---------------------------------------------------------------------------------------------------------------
# Historical cases

_NOT_SOURCED = "NOT_SOURCED"


def _scenario_from_case(case_row: dict) -> tuple[Scenario | None, list]:
    given = case_row.get("scenario")
    if isinstance(given, Scenario):
        return given, []
    if isinstance(given, dict):
        return Scenario(**given), []
    text = f"{case_row.get('Shoreline_Type', '')} {case_row.get('Substrate', '')}".lower()
    if not text.strip():
        return None, []
    for words, shore in ((("mangrove",), "mangrove"), (("marsh",), "marsh"), (("sand",), "sand_beach"), (("cobble",), "cobble"),
                         (("boulder",), "boulder"), (("rock", "bedrock", "seawall", "hard"), "bedrock"), (("gravel", "mixed"), "mixed_sediment")):
        if any(w in text for w in words):
            break
    else:
        return None, []
    intensity = str(case_row.get("Oiling_Intensity", "")).lower()
    assumed = ["fields not stated by the case keep Scenario defaults (ASSUMED): coverage, thickness, penetration, exposure, access, season"]
    values = {"shoreline_type": shore}
    if "heav" in intensity:
        values.update(oil_coverage=80.0, oil_category="heavy")
    return Scenario(**values), assumed


def decide_case(case_row: dict, *, options: list | None = None, seed: int = DEFAULT_SEED, **kwargs) -> DecisionReport:
    """Decision report for a historical case (validation/historical_validation.CASES style) on the generic Scenario path.

    case_row may carry a `scenario` (Scenario or dict of its fields, e.g. one Latin-hypercube draw) or the text fields
    Shoreline_Type / Substrate / Oiling_Intensity, mapped with documented keywords. A case with no sourced shoreline gets an
    out-of-scope report (no decision is invented). The documented response is never an input.
    """
    case_id = case_row.get("Case_ID")
    scenario, assumed = _scenario_from_case(case_row)
    if scenario is None:
        msg = (f"Out of scope: case {case_id} has no sourced shoreline description ({_NOT_SOURCED}); no decision is made.")
        return _refuse([], msg, {"case_id": case_id}, case_id)
    return run_decision(scenario, options=options, seed=seed, assumptions=assumed, label=case_id, **kwargs)
