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

from . import habitat as hab
from . import knowledge, registry
from . import scenario_composer as sc
from . import site_evidence as se
from .data_model import Scenario, TREATMENT_LIBRARY
from .model_interface import ScenarioRequest, SiteRecord

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "data" / "knowledge"
PIPELINE_VERSION = "f9-v3"   # V5.1: additive fields (recommendation_category, decision_outcome, abstentions, rank_basis)
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
# Evidence states (D35). Class letters A-E are unchanged; the state is an explicit extra field and part of the headline.
STATE_INSUFFICIENT = "insufficient_evidence"
STATE_NO_DIFFERENCE = "no_clear_difference"
EVIDENCE_STATE_LABELS = {
    STATE_INSUFFICIENT: "Insufficient evidence to compare with natural recovery",
    STATE_NO_DIFFERENCE: "No clear difference from natural recovery (evidence exists)",
    "benefit": "Evidence of benefit over natural recovery",
    "harm": "Evidence of harm compared with natural recovery",
    "mixed": "Mixed evidence compared with natural recovery",
    "baseline": "Natural recovery (the baseline)",
}
# Stakeholder recommendation categories (V5.1, decision D41, Proposed). A transparent, rule-based reading of the class
# letter, the option's evidence state and the scope tier. Class letters A-E are unchanged; nothing here is a new model.
CAT_RECOMMENDED = "recommended"
CAT_CONDITIONAL = "conditional"
CAT_NATURAL = "natural_recovery_monitoring"
CAT_NO_BENEFIT = "no_demonstrated_benefit"
CAT_INSUFFICIENT = "insufficient_evidence"
CAT_EXCLUDED = "excluded"
CATEGORY_ORDER = (CAT_RECOMMENDED, CAT_CONDITIONAL, CAT_NATURAL, CAT_NO_BENEFIT, CAT_INSUFFICIENT, CAT_EXCLUDED)
CATEGORY_LABELS = {
    CAT_RECOMMENDED: "Recommended",
    CAT_CONDITIONAL: "Conditional",
    CAT_NATURAL: "Natural recovery with monitoring (reference option)",
    CAT_NO_BENEFIT: "Allowed, no demonstrated benefit over natural recovery",
    CAT_INSUFFICIENT: "Insufficient evidence",
    CAT_EXCLUDED: "Excluded",
}
CATEGORY_RULES = {
    CAT_RECOMMENDED: "class A (evidence of benefit, no harm flag) AND the input is inside the scope where that evidence was "
                     "gathered (scope tier 'validated')",
    CAT_CONDITIONAL: "class D (allowed, harm flagged under some conditions or mixed evidence), OR class A when the input is "
                     "outside the scope where the benefit evidence was gathered (transfer untested), OR class A when the option "
                     "presupposes a method that is itself excluded",
    CAT_NATURAL: "class C: natural recovery, the reference every option is compared with",
    CAT_NO_BENEFIT: "class B with evidence rows that show no clear difference from natural recovery",
    CAT_INSUFFICIENT: "class B with no eligible evidence rows: no comparison with natural recovery is possible",
    CAT_EXCLUDED: "class E: removed by a hard constraint (screening rule or habitat rating) or by evidence of harm",
}
# Decision outcome of a whole report (one of these; 'out_of_scope' is a refusal).
OUTCOME_LABELS = {
    "intervention_recommended": "At least one intervention is recommended over natural recovery",
    "conditional_only": "No intervention is recommended outright; at least one is conditional. Natural recovery stays the reference",
    "natural_recovery_monitoring": "No intervention is shown to beat natural recovery: natural recovery with monitoring",
    "insufficient_evidence": "Insufficient evidence to compare any intervention with natural recovery: natural recovery with "
                             "monitoring is the default, and further assessment is needed",
    "out_of_scope": "Outside the scope of this tool: no assessment was made",
    "unsupported_habitat": "Unsupported habitat: no screening, comparison or recommendation was made",
}
RANK_BASIS_EVIDENCE = "evidence"
RANK_BASIS_CONVENTION = "display_convention"
RANK_BASIS_TEXT = {
    RANK_BASIS_EVIDENCE: "ordered by the lower bound of a benefit interval (evidence)",
    RANK_BASIS_CONVENTION: "display convention only: no benefit interval separates this option from its neighbours; the order "
                           "uses the ASSUMED ecological score and then the name, and is not a scientific ranking",
}
TIER_MESSAGES = {
    "validated": ("Heavily oiled salt marsh in the northern Gulf of Mexico: the marsh-edge loss model and the soil PAH-sum "
                  "decline are validated (held-out, one spill). Treatment differences (composer) and the vegetation curve "
                  "are experimental and carry that badge."),
    "experimental": ("Experimental: numbers are shown with an experimental badge and the reason; they are not validated "
                     "forecasts for this input."),
    "rules_and_literature": ("Rules and literature only: screening verdicts and literature evidence verdicts; there is no "
                             "site-specific forecast for this shoreline type."),
}
TIER_SAND_NOTE = (" Sand beaches: the sand-beach data model is not integrated yet (D36), so no persistence forecast is shown; "
                  "the tier becomes experimental when it is.")
TIER_MIXED_GRAVEL_NOTE = (" Mixed sand and gravel and gravel beaches are rules and literature only by owner decision (14 Nov 2026): "
                          "the literature notes below are not a prediction for this site.")

# Habitat strings are resolved by habitat.normalise() (data/knowledge/tables/habitat.csv, keyed to the ESI code, D36).
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

# Design of the evidence behind each option's composer numbers, shown beside the class (honest label, 14 Nov 2026).
_OPTION_DESIGN = {
    "manual_removal": "observational, one site (Zengel et al. 2022, Bay Jimmy)",
    "mechanical_removal": "observational, one site (Zengel et al. 2022, Bay Jimmy)",
    PLANTING: ("observational, one site: mechanically cleaned and planted plots versus untreated plots, 5 versus 9 plots "
               "(not a randomised comparison)"),
}
_PREREQUISITE = {PLANTING: "mechanical_removal"}   # the planting evidence is from mechanically cleaned plots (Zengel et al. 2022)
ADVISORY_PREFIX = "advisory (AI-proposed, not reviewed by an expert)"
_COMPOSER_CAVEAT = ("Paired difference from one site's field evidence (Bay Jimmy, Zengel et al.), the same at any heavily "
                    "oiled marsh site; the composer is experimental (R3 bias gate failed, FINDINGS_V4 26).")
_OPTION_CAVEAT = {
    "manual_removal": "Observational: treatment classes were not randomly assigned.",
    "mechanical_removal": "Observational; mechanical plots were the most heavily oiled, so oiling and method are confounded.",
    PLANTING: ("Evidence is an observational contrast, mechanically cleaned and planted plots versus untreated plots (5 versus 9 plots, "
               "one site; Zengel et al. 2022), not a randomised comparison. It presupposes mechanical removal, which the screening "
               "rules exclude on marsh, so the two rules are in tension."),
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
    evidence_state: str = ""            # D35: "benefit", "no_clear_difference" or "insufficient_evidence" (see EVIDENCE_STATE_LABELS)
    evidence_state_label: str = ""
    literature_notes: list = field(default_factory=list)   # ESI 5 and 6A: "literature, not a prediction"
    advisories: list = field(default_factory=list)         # AI-proposed condition notes, not used for classes
    decision_outcome: str = ""          # V5.1 (D41): one of OUTCOME_LABELS
    decision_outcome_label: str = ""
    recommendation_summary: dict = field(default_factory=dict)   # category -> [options], in CATEGORY_ORDER
    abstentions: list = field(default_factory=list)              # V5.1: what the platform declines to state, and why

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


def habitat_class(habitat: str, wave_exposure: str | None = None) -> str:
    """Habitat class used by evidence_verdicts.csv (resolved through the ESI-keyed habitat table, D36)."""
    return hab.habitat_class(habitat, wave_exposure)


def _esi_family(esi_codes: str) -> set:
    """Evidence families ('sand', 'mixed_gravel', 'rocky', ...) of a '|' or '/' separated list of ESI codes."""
    table = hab.table()
    out = set()
    for token in re.split(r"[|/;,\s]+", str(esi_codes)):
        if token in table:
            out.add(table[token].evidence_family)
    return out


def _applies_to_esi(esi_codes: str, esi: str | None) -> bool:
    """Do evidence rows whose source rows carry `esi_codes` apply to habitat `esi`? Hot-water harm seen on mixed sand and gravel and
    gravel beaches (ESI 5/6A) must not be applied to fine sand (D36). Rows without ESI codes are kept (unknown, shown as such)."""
    table = hab.table()
    if not esi or esi not in table or table[esi].habitat_class != "sand/gravel beach":
        return True
    families = _esi_family(esi_codes)
    return not families or table[esi].evidence_family in families


def _literature_habitat(text: str) -> str:
    # same keywords as validation/literature_pooling._habitat_class
    value = text.lower()
    if "mangrove" in value or "rhizophora" in value:
        return "mangrove"
    if any(w in value for w in ("marsh", "spartina", "salicornia", "wetland")):
        return "marsh"
    if any(w in value for w in ("rock", "bedrock", "hard substrate", "riprap", "seawall")):
        return "rocky/hard"
    # cobble: a beach (ESI 6A), in line with habitat.normalise("cobble") (D36; the old screening code treated it as hard substrate)
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
    exposure = scenario.wave_exposure
    esi = hab.normalise(habitat, exposure)
    hrow = hab.get(habitat, exposure)
    hclass = hrow.habitat_class if hrow else "other"
    category, oil_source = _resolve_oil(oil, oil_default, scenario.temperature_c)
    over = {"oil_category": category}
    if season:
        over["season"] = str(season).lower()
    # The screening rules read Scenario.shoreline_type. Resolve it through the habitat table so every alias (sandy_beach,
    # mixed, cobble, salt_marsh, rock, ...) reaches the rule that was written for it (D36).
    if hrow is not None and scenario.shoreline_type.lower() != hrow.rule_key:
        over["shoreline_type"] = hrow.rule_key
    scenario = dataclasses.replace(scenario, **over)
    salt_marsh = esi == "10A"
    noaa_cat = knowledge.load_noaa_oil_categories().get(category)
    flags = None
    if site is not None and salt_marsh:
        values = {f: site.get(f) for f in se.FEATURES}
        flags = se.site_flags(values, status=site.get("status", "in_scope"), habitat=str(site.get("esi_main") or "10A"),
                              oiling=oiling, lat=_num(site.get("lat")), lon=_num(site.get("lon")))
    return {"scenario": scenario, "site": site, "habitat": habitat.lower(), "habitat_class": hclass, "salt_marsh": salt_marsh,
            "esi": esi, "habitat_row": hrow, "noaa_oil_category": noaa_cat,
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
    esi = ctx.get("esi")
    if esi in ("3A", "4"):
        ref = _beach_persistence_reference(ctx)
        if ref is not None:   # filled by the integrating agent when the sand-beach data model exists
            reasons = ["sand-beach data model: one spill (Deepwater Horizon), outcome is a response endpoint, not chemical or ecological recovery"]
            if esi == "3A":
                return "experimental", BEACH_TIER_TEXT + " Reason: " + reasons[0], reasons
            return "experimental", TIER_MESSAGES["experimental"] + " Reasons: " + reasons[0], reasons
        return "rules_and_literature", TIER_MESSAGES["rules_and_literature"] + TIER_SAND_NOTE, []
    if esi in ("5", "6A"):
        return "rules_and_literature", TIER_MESSAGES["rules_and_literature"] + TIER_MIXED_GRAVEL_NOTE, []
    return "rules_and_literature", TIER_MESSAGES["rules_and_literature"], []


BEACH_TIER_TEXT = ("Rules and literature, plus an experimental persistence reference (did not beat its baseline; not transferable "
                   "between states).")
# ASSUMED mapping from the pipeline's SCAT maximum-oiling class to a first-oiling category group of the beach model. The
# dashboard lets the user pick the group, so this only sets the default shown.
_BEACH_GROUP_OF_OILING = {"Heavy": "surface_mod_heavy", "Moderate": "surface_mod_heavy", "Light": "surface_light",
                          "Very_Light": "tb_neg_light", "NOO": "tb_neg_light"}


def _beach_persistence_reference(ctx: dict):
    """Persistence REFERENCE for fine-to-medium sand beach (ESI 3A) only; None for ESI 4, 5 and 6A (and anything else).

    Returns the packaged baseline curve of beach_sand_persistence_v1 (Turnbull curve by first oiling category; both gates
    failed, so the model itself is not packaged). It is visible oil under the cleanup as carried out in 2010-2013, not natural
    recovery and not a treatment comparison. Same keys as a row of `_reference_rows`, plus `curve` (the chosen group) and
    `curves_by_group` (all four groups, for the dashboard)."""
    if ctx.get("esi") != "3A":
        return None
    try:
        model = registry.get("beach_sand_persistence_v1")
        card = model.card
        curves = card["baseline_curves_all_states"]
        horizons = [90, 180, 365, 730]
    except (KeyError, FileNotFoundError, ImportError):
        return None
    group = _BEACH_GROUP_OF_OILING.get(ctx.get("oiling"), "tb_neg_light")
    i365 = horizons.index(365)
    by_group = {g: {"n_segments": c["n"], "median": c["median"], "lo90": c["lo90"], "hi90": c["hi90"]} for g, c in curves.items()}
    c = by_group[group]
    return {"quantity": "visible oil still recorded 365 days after the first oiled survey (sand beach, baseline by first oiling category)",
            "value": c["median"][i365], "lo90": c["lo90"][i365], "hi90": c["hi90"][i365], "unit": "probability",
            "model_id": model.model_id, "state": "experimental", "state_label": "experimental (gate failed)",
            "evidence_state": "experimental", "scope": "in range", "scope_reasons": list(card.get("caveats_short", [])),
            "reference_only": True, "horizons_days": horizons, "group": group, "curve": c, "curves_by_group": by_group,
            "group_mapping_note": "default group ASSUMED from the SCAT oiling class; choose the group seen at the first oiled survey",
            "note": ("Persistence of visible oil under the 2010-2013 cleanup as it was carried out. Not natural recovery, not a "
                     "treatment comparison. Model did not beat its baseline (gates B-1 and B-2 failed); results differed strongly "
                     "between states. " + "; ".join(card.get("caveats_short", [])))}


# ---------------------------------------------------------------------------------------------------------------
# Step 2

_VERDICT_RANK = {"eligible": 0, "conditional": 1, "ineligible": 2}
NOAA_SHORT = "NOAA Characteristic Coastal Habitats (2017)"


def _noaa_screen(option: str, ctx: dict) -> dict | None:
    """NOAA habitat-impact rating of the option for this habitat and oil category, mapped to a pipeline verdict (D36, Proposed).

    The letters rate the adverse HABITAT IMPACT of the method (A least, D most), not how well it removes oil."""
    row = ctx.get("habitat_row")
    if row is None or not row.noaa_ratings_esi or option == PLANTING:
        return None
    r = knowledge.noaa_rating(row.noaa_ratings_esi, option, ctx["oil_category"])
    if r is None:
        return None
    mapping = knowledge.load_noaa_mapping()[r["rating"]]
    cat = r["noaa_category"]
    text = (f"{NOAA_SHORT} p.{r['page']}, {r['noaa_table']}: '{r['noaa_method']}' is rated {r['rating']} for oil category {cat} "
            f"({mapping['meaning'].split(':')[0]}); letters rate adverse habitat impact, not effectiveness")
    return {"rating": r["rating"], "verdict": mapping["verdict"], "flag": mapping["flag"], "noaa_category": cat, "page": r["page"],
            "rule_id": f"noaa:{row.noaa_ratings_esi}:{option}:{cat}", "reason": text, "rating_id": r["rating_id"],
            "source": f"{NOAA_SHORT} p.{r['page']} (data/knowledge/tables/noaa_response_rating.csv {r['rating_id']}); {r['status']}; "
                      f"mapping {mapping['status']}"}


def _screen_option(option: str, ctx: dict) -> dict:
    result = _screen_generic(option, ctx)
    noaa = _noaa_screen(option, ctx)
    result["noaa"] = noaa
    result["generic"] = {k: result[k] for k in ("verdict", "rule_id", "reason", "source")}
    if noaa is not None and option != NATURAL and _VERDICT_RANK[noaa["verdict"]] > _VERDICT_RANK[result["verdict"]]:
        result.update({k: noaa[k] for k in ("verdict", "rule_id", "reason", "source")})
    return result


def _screen_generic(option: str, ctx: dict) -> dict:
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

def _verdict_rows(option: str, hclass: str, esi: str | None = None) -> pd.DataFrame:
    v = _verdicts()
    rows = v[(v.technology == _code(option)) & (v.habitat == hclass)]
    if "esi_codes" in rows.columns and esi:
        rows = rows[rows.esi_codes.map(lambda c: _applies_to_esi("" if pd.isna(c) else c, esi)).astype(bool)].copy()
    return rows


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
        out = [_no_model(q, reason) for q in ("PAH-sum half-life", "vegetation time to 80% of reference",
                                              "natural edge loss to year 5 and 8")]
        esi = ctx.get("esi")
        if esi in ("3A", "4"):
            ref = _beach_persistence_reference(ctx)
            out.insert(0, ref if ref is not None else _no_model(
                "time to SCAT endpoint on a sand beach", "sand-beach data model not integrated yet (D36); rules and literature only"))
        elif esi in ("5", "6A"):
            out.insert(0, _no_model("persistence forecast on a mixed sand and gravel or gravel beach",
                                    "rules and literature only by owner decision (14 Nov 2026); see literature_notes, which are not a prediction"))
        return out
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

def _tradeoffs(option: str, hclass: str, esi: str | None = None) -> dict:
    lit = _literature()
    rows = lit[(lit.technology == _code(option)) & (lit.habitat.map(_literature_habitat) == hclass)]
    rows = rows[rows.esi_code.map(lambda c: _applies_to_esi(c, esi)).astype(bool)]
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
    if ctx["habitat_row"] is None:
        # V5.1 abstention: a shoreline type that is not in the habitat table has no screening rules, ratings or evidence written
        # for it. Running the generic rules would manufacture an answer, so the pipeline stops here and says so.
        supported = ", ".join(f"{h.name} (ESI {code})" for code, h in sorted(hab.table().items()))
        message = (f"Unsupported habitat: '{ctx['habitat']}' is not a shoreline type this platform has screening rules or evidence "
                   f"for, so no option is screened, compared or recommended. Supported shoreline types: {supported}. "
                   "A site-specific assessment by a qualified specialist is needed.")
        return _refuse(trace, message, {"habitat": ctx["habitat"]}, label, tier="unsupported_habitat",
                       sources=["data/knowledge/tables/habitat.csv"])
    tier, tier_message, tier_reasons = _scope_tier(ctx)
    ctx["tier"], ctx["tier_reasons"] = tier, tier_reasons
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
        "esi_code": ctx["esi"], "noaa_oil_category": ctx["noaa_oil_category"],
        "noaa_oil_category_basis": "ASSUMED mapping from the tool's oil category (data/knowledge/tables/noaa_oil_category.csv)",
        "habitat_descriptors": ({"name": ctx["habitat_row"].name, "oil_penetration_depth": ctx["habitat_row"].oil_penetration_depth,
                                 "burial_risk": ctx["habitat_row"].burial_risk, "persistence_driver": ctx["habitat_row"].persistence_driver,
                                 "asphalt_pavement_risk": ctx["habitat_row"].asphalt_pavement_risk,
                                 "source": f"NOAA Characteristic Coastal Habitats (2017) p.{ctx['habitat_row'].descriptor_pages}"}
                                if ctx["habitat_row"] else None),
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
    removed, flagged, advisory, verdict_info, cond_info = {}, {}, {}, {}, {}
    for o in options:
        rows = _verdict_rows(o, hclass, ctx["esi"])
        verdict_info[o] = _aggregate_verdicts(rows)
        conds = _condition_rows(o, ctx)
        cond_info[o] = conds
        if o == NATURAL:
            continue
        harmful = rows[rows.verdict == "evidence of harm"]
        if not harmful.empty:
            removed[o] = [{"source": "evidence_verdicts.csv", "outcome_family": r.outcome_family,
                           "detail": f"evidence of harm in {hclass}: {r.basis}"} for r in harmful.itertuples()]
        # AI-proposed condition rows are ADVISORY: shown as notes, never a class D flag (14 Nov 2026).
        harms = [c for c in conds if c["effect_when_met"] == "harms" and c["status"] != "not met by input season"]
        if harms:
            advisory[o] = [ADVISORY_PREFIX + f": harm reported under condition '{c['condition']}' [{c['status']}] ({c['source']})"
                           for c in harms]
        noaa = screen[o].get("noaa")
        if noaa is not None and noaa["flag"] and noaa["verdict"] == "conditional":
            flagged.setdefault(o, []).append({"source": noaa["source"], "detail": noaa["reason"] + " (significant or unknown habitat impact: "
                                                                                  "flag shown, option stays)"})
    _log(trace, 3, {"habitat_class": hclass, "sources": ["evidence_verdicts.csv", "treatment_conditions.csv (marsh, advisory only)",
                                                         "mangrove_screening.csv (mangrove)", "noaa_response_rating.csv (beach and rocky)"]},
         {"removed": removed, "flagged": flagged, "advisory": advisory},
         ["data/knowledge/evidence_verdicts.csv", "data/knowledge/treatment_conditions.csv", "data/knowledge/tables/noaa_response_rating.csv"])

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
    trade = {o: _tradeoffs(o, hclass, ctx["esi"]) for o in options}
    _log(trace, 6, {"habitat_class": hclass}, {o: {k: v for k, v in t.items() if k != "tradeoff_sources"} for o, t in trade.items()},
         ["data/knowledge/literature_effects.csv", "data/knowledge/tables/technology.csv"])

    # Step 7
    # An add-on option presupposes another method (planting presupposes mechanical cleanup). If that method is excluded, the
    # add-on cannot be 'recommended' outright (D41).
    ctx["prerequisite_excluded"] = {o: pre for o, pre in _PREREQUISITE.items() if pre in options and excluded(pre)}
    rows = [_option_row(o, ctx, screen[o], removed.get(o), flagged.get(o), verdict_info[o], cond_info[o], composer.get(o),
                        trade[o], comp_model, excluded(o), anchor, advisory.get(o)) for o in options]
    _assign_order(rows)
    evidence_state = _report_evidence_state(rows)
    headline = _headline(rows, tier, anchor, evidence_state)
    classes = {c: [r["option"] for r in rows if r["recommendation_class"] == c] for c in CLASS_LABELS}
    summary = {c: [r["option"] for r in rows if r["recommendation_category"] == c] for c in CATEGORY_ORDER}
    outcome = _decision_outcome(rows)
    abstentions = _abstentions(ctx, tier, tier_reasons, reference, rows)
    _log(trace, 7, {"class_rules": "E excluded > A benefit > D harm under conditions > B no clear evidence; C natural recovery",
                    "ordering": ORDER_BASIS}, {"classes": classes, "headline": headline, "evidence_state": evidence_state,
                                         "recommendation_summary": summary, "decision_outcome": outcome,
                                         "category_rules": CATEGORY_RULES},
         ["steps 2-6"])

    # Step 8
    plots = _plots(rows, composer, tidy, summ, cell_ok, hclass, options, verdict_info, ctx["esi"])
    noaa_nat = screen[NATURAL].get("noaa")
    natural = {"option": NATURAL, "recommendation_class": "C", "label": CLASS_LABELS["C"], "reference": reference,
               "habitat_rating": ({"rating": noaa_nat["rating"], "text": noaa_nat["reason"], "source": noaa_nat["source"]}
                                  if noaa_nat else None),
               "rule_verdict": screen[NATURAL]["verdict"], "evidence_verdict": verdict_info[NATURAL][0],
               "evidence_basis": verdict_info[NATURAL][1], "monitoring": "monitor canopy, recruitment and soil oil for at least 5 years"
               if ctx["habitat_class"] == "mangrove" else "monitor and compare with the reference numbers above"}
    models_used = sorted({r["model_id"] for r in reference if r.get("model_id")} | ({comp_model.model_id} if composer else set()))
    version = {"pipeline_version": PIPELINE_VERSION, **_git_commit(), "python": sys.version.split()[0], "numpy": np.__version__,
               "pandas": pd.__version__, "seed": seed, "n_draws": n_draws, "models_used": models_used,
               "models": {m: {"state": registry.get(m).state, "version": registry.get(m).model_version} for m in models_used},
               "knowledge_checksums": _table_checksums()}
    report = DecisionReport(headline=headline, scope_tier=tier, scope_message=tier_message, options=rows, natural_recovery=natural,
                            plots=plots, trace=trace, version=version, characterisation=characterisation,
                            evidence_state=evidence_state, evidence_state_label=EVIDENCE_STATE_LABELS[evidence_state],
                            literature_notes=_literature_notes(ctx), advisories=sorted({a for v in advisory.values() for a in v}),
                            decision_outcome=outcome, decision_outcome_label=OUTCOME_LABELS[outcome],
                            recommendation_summary=summary, abstentions=abstentions)
    _log(trace, 8, {"n_options": len(rows)}, {"headline": headline, "scope_tier": tier, "models_used": models_used,
                                              "plot_keys": sorted(plots), "evidence_state": evidence_state}, ["steps 1-7"])
    report.trace = _jsonable(trace)
    return report


def _refuse(trace: list, message: str, inputs: dict, label, tier: str = "out_of_scope", sources: list | None = None) -> DecisionReport:
    """A report that makes no assessment: out of scope (D30) or unsupported habitat (V5.1). No options, no numbers."""
    _log(trace, 1, inputs, {"scope_tier": tier, "refusal": message}, sources or ["docs/F0_F1_SCOPE_AND_DECISIONS.md D30"])
    for step in range(2, 9):
        _log(trace, step, {}, {"skipped": tier.replace("_", " ")}, [])
    return DecisionReport(headline=message, scope_tier=tier, scope_message=message, options=[],
                          natural_recovery={}, plots={}, trace=_jsonable(trace),
                          version={"pipeline_version": PIPELINE_VERSION, **_git_commit(), "models_used": []},
                          characterisation={"label": label, "scope_tier": tier, "refusal": message, **inputs},
                          evidence_state=STATE_INSUFFICIENT, evidence_state_label=EVIDENCE_STATE_LABELS[STATE_INSUFFICIENT],
                          decision_outcome=tier, decision_outcome_label=OUTCOME_LABELS[tier],
                          recommendation_summary={c: [] for c in CATEGORY_ORDER},
                          abstentions=[{"kind": tier, "text": message}])


def _option_row(o, ctx, screen, removed, flagged, verdict, conds, composer, trade, comp_model, excluded, anchor, advisory=None) -> dict:
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
        gen, noaa = screen.get("generic"), screen.get("noaa")
        if gen and gen["verdict"] == "ineligible":
            reasons.append({"source": "rule", "rule_id": gen["rule_id"], "detail": gen["reason"]})
        if noaa and noaa["verdict"] == "ineligible":
            reasons.append({"source": noaa["source"], "rule_id": noaa["rule_id"], "detail": noaa["reason"] + " (not advised or not applicable; D36 mapping, Proposed)"})
        if not reasons and screen["verdict"] == "ineligible":
            reasons.append({"source": "rule", "rule_id": screen["rule_id"], "detail": screen["reason"]})
        reasons += removed or []
    state = _option_state(o, composer, verdict_name, favourable, unfavourable)
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
    category, category_reason = _category(cls, state, ctx.get("tier"), ctx.get("tier_reasons") or [],
                                          prerequisite_excluded=ctx.get("prerequisite_excluded", {}).get(o),
                                          design=_OPTION_DESIGN.get(o) if composer else None)
    return {
        "option": o, "recommendation_class": cls, "class_label": CLASS_LABELS[cls], "rank_in_class": None,
        "recommendation_category": category, "recommendation_category_label": CATEGORY_LABELS[category],
        "recommendation_category_rule": CATEGORY_RULES[category], "recommendation_category_reason": category_reason,
        "evidence_state": state, "evidence_state_label": EVIDENCE_STATE_LABELS[state],
        "evidence_design": _OPTION_DESIGN.get(o) if composer else None,
        "habitat_rating": ({"rating": screen["noaa"]["rating"], "noaa_oil_category": screen["noaa"]["noaa_category"],
                            "verdict": screen["noaa"]["verdict"], "text": screen["noaa"]["reason"], "source": screen["noaa"]["source"]}
                           if screen.get("noaa") else None),
        "advisory_notes": list(advisory or []),
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


def _category(cls: str, state: str, tier: str | None, tier_reasons: list, prerequisite_excluded: str | None = None,
              design: str | None = None) -> tuple[str, str]:
    """Stakeholder category of one option (D41). Pure function of class letter, evidence state, scope tier and whether a
    method the option presupposes was itself excluded."""
    if cls == "C":
        return CAT_NATURAL, "reference option"
    if cls == "E":
        return CAT_EXCLUDED, "see exclusion_reasons"
    if cls == "A":
        if prerequisite_excluded:
            return CAT_CONDITIONAL, (f"evidence of benefit exists, but the option presupposes '{prerequisite_excluded}', which is "
                                     "excluded for this input; it applies only where that method has already been used")
        if tier == "validated":
            basis = f" Basis of the benefit evidence: {design}." if design else ""
            return CAT_RECOMMENDED, "evidence of benefit, and the input is inside the scope of that evidence." + basis
        why = "; ".join(tier_reasons) if tier_reasons else f"scope tier is '{tier}'"
        return CAT_CONDITIONAL, "evidence of benefit exists, but its transfer to this input is untested: " + why
    if cls == "D":
        return CAT_CONDITIONAL, "allowed, with harm flagged under some conditions or mixed evidence (see harm_flags)"
    if state == STATE_INSUFFICIENT:
        return CAT_INSUFFICIENT, "allowed by screening, but there are no eligible evidence rows to compare it with natural recovery"
    return CAT_NO_BENEFIT, "allowed by screening; the evidence shows no clear difference from natural recovery"


def _decision_outcome(rows: list) -> str:
    cats = {r["recommendation_category"] for r in rows}
    if CAT_RECOMMENDED in cats:
        return "intervention_recommended"
    if CAT_CONDITIONAL in cats:
        return "conditional_only"
    if CAT_NO_BENEFIT in cats:
        return "natural_recovery_monitoring"
    return "insufficient_evidence"


def _abstentions(ctx: dict, tier: str, tier_reasons: list, reference: list, rows: list) -> list:
    """Explicit list of what this report declines to state (CLAUDE.md 'scientific abstention'). Built from pipeline state only."""
    out = []
    if tier == "rules_and_literature":
        out.append({"kind": "no_site_forecast", "text": "No site-specific numerical forecast is given for this shoreline type: "
                    "the platform has no validated or experimental outcome model for it. Screening verdicts and literature only."})
    for reason in tier_reasons:
        out.append({"kind": "outside_validated_scope", "text": reason})
    if ctx["habitat_class"] == "marsh" and ctx.get("esi") != "10A":
        out.append({"kind": "borrowed_evidence", "text": "Evidence verdicts for this shoreline type are borrowed from the salt-marsh "
                    "literature (habitat table, D36). Their transfer to this shoreline type has not been demonstrated."})
    for ref in reference:
        if ref.get("value") is None and ref.get("reason"):
            out.append({"kind": "no_model", "text": f"{ref.get('quantity', 'quantity')}: {ref['reason']}"})
    n_insufficient = sum(r["recommendation_category"] == CAT_INSUFFICIENT for r in rows)
    if n_insufficient:
        out.append({"kind": "insufficient_evidence", "text": f"{n_insufficient} allowed option(s) cannot be compared with natural "
                    "recovery because no eligible evidence rows exist for this habitat. This is not a finding of no benefit."})
    if not any(r["recommendation_category"] == CAT_RECOMMENDED for r in rows):
        out.append({"kind": "no_recommendation", "text": "No intervention is recommended over natural recovery. Natural recovery "
                    "with monitoring remains the reference option."})
    return out


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
        # V5.1: say honestly what the order rests on. Only a benefit interval lower bound that differs from every other
        # member's is evidence; everything else is a display convention (ASSUMED score, then name).
        keys = [(r["_group"], r["benefit_lower_bound"]) for r in members]
        for r, key in zip(members, keys):
            by_evidence = r["_group"] < 3 and r["benefit_lower_bound"] is not None and keys.count(key) == 1 and len(members) > 1
            r["rank_basis"] = RANK_BASIS_EVIDENCE if by_evidence else RANK_BASIS_CONVENTION
            r["rank_basis_text"] = RANK_BASIS_TEXT[r["rank_basis"]]
            r["rank_tied_with"] = sorted(m["option"] for m, k in zip(members, keys) if k == key and m is not r)
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


def _option_state(o: str, composer, verdict_name: str, favourable: bool, unfavourable: bool) -> str:
    """Evidence state of one option against natural recovery (D35). 'insufficient_evidence' = no eligible evidence rows at all."""
    if o == NATURAL:
        return "baseline"
    if composer:
        return "mixed" if favourable and unfavourable else "benefit" if favourable else "harm" if unfavourable else STATE_NO_DIFFERENCE
    return {"evidence of benefit": "benefit", "evidence of harm": "harm", "mixed": "mixed",
            "no clear difference": STATE_NO_DIFFERENCE}.get(verdict_name, STATE_INSUFFICIENT)


def _report_evidence_state(rows: list) -> str:
    """'benefit' if any option is class A; 'no_clear_difference' if evidence exists for at least one allowed option;
    otherwise 'insufficient_evidence' (no allowed option has any evidence row)."""
    if any(r["recommendation_class"] == "A" for r in rows):
        return "benefit"
    allowed = [r for r in rows if r["recommendation_class"] in ("B", "D")]
    if any(r["evidence_state"] != STATE_INSUFFICIENT for r in allowed):
        return STATE_NO_DIFFERENCE
    return STATE_INSUFFICIENT


def _headline(rows: list, tier: str, anchor: int, state: str | None = None) -> str:
    a = [r for r in rows if r["recommendation_class"] == "A"]
    if a:
        text = "Field evidence of benefit over natural recovery: " + "; ".join(f"{r['option']} ({_benefit_text(r, anchor)})" for r in a)
        designs = [f"{r['option']}: {r['evidence_design']}" for r in a if r.get("evidence_design")]
        if designs:
            text += ". Design of the evidence: " + "; ".join(designs)
        if any(r["model_id"] for r in a):
            text += ". Differences are experimental composer output from one site's field evidence"
        held = [r for r in a if r.get("recommendation_category") == CAT_CONDITIONAL]
        if held:   # V5.1 (D41): evidence of benefit is not always an outright recommendation
            text += ". Conditional, not recommended outright: " + "; ".join(
                f"{r['option']} ({r['recommendation_category_reason']})" for r in held)
        return text + "."
    state = state or _report_evidence_state(rows)
    allowed = [r for r in rows if r["recommendation_class"] in ("B", "D")]
    with_evidence = [r["option"] for r in allowed if r["evidence_state"] != STATE_INSUFFICIENT]
    without = [r["option"] for r in allowed if r["evidence_state"] == STATE_INSUFFICIENT]
    b = [r["option"] for r in rows if r["recommendation_class"] == "B"][:3]
    if state == STATE_NO_DIFFERENCE:
        text = ("No clear difference from natural recovery (evidence exists): no option is shown by evidence to beat natural recovery; "
                "continue with natural recovery and monitoring. Evidence exists but shows no clear difference for: "
                + ", ".join(with_evidence) + ".")
        if without:
            text += " Insufficient evidence to compare with natural recovery for: " + ", ".join(without) + "."
    else:
        text = ("Insufficient evidence to compare with natural recovery: no allowed option has any eligible evidence rows for this "
                "habitat, so no comparison is possible. Natural recovery with monitoring is the default; this is not a finding that "
                "treatment gives no benefit.")
    if b:
        text += " Best allowed options (class B): " + ", ".join(b) + "."
    elif not allowed:
        text += " No allowed alternative has been identified."
    return text


def _literature_notes(ctx: dict) -> list:
    """ESI 5 and 6A only: literature notes shown as 'literature, not a prediction'."""
    esi = ctx.get("esi")
    if esi not in ("5", "6A"):
        return []
    df = knowledge.load_beach_notes()
    out = []
    for r in df.itertuples():
        if esi in r.esi_codes.split("|"):
            out.append({"note_id": r.note_id, "topic": r.topic, "statement": r.statement, "label": r.display_label,
                        "evidence_class": r.evidence_class, "source": r.source, "effect_ids": [x for x in r.effect_ids.split("|") if x],
                        "source_checked": r.source_checked, "status": r.status})
    return out


def _plots(rows, composer, tidy, summ, cell_ok, hclass, options, verdict_info, esi=None) -> dict:
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
        rs = _verdict_rows(o, hclass, esi)
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
