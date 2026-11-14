"""Model registry and D20 promotion gate (V4 F3). Registers thin adapters (no new science) that wrap the
existing models behind the standard interface in model_interface.py, and exposes:

    registry.get(model_id)          -> a model adapter
    registry.list(state=...)        -> adapters, optionally filtered by state
    registry.validated_only()       -> only models the orchestration layer may reach

Promotion rule (D20): meets_promotion_criteria reads the card fields (committed plan, baseline beaten on
whole held-out units, interval coverage reported, training range present) and is used to set state. A model
is 'validated' only if it passes that check AND its registry entry declares it validated; otherwise it is
'experimental' (e.g. the composer, whose R3 heavy-cell bias gate failed, FINDINGS_V4 26).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import model_interface as mi
from . import scenario_composer as sc
from . import site_evidence as se
from .model_interface import (Prediction, ScenarioRequest, SiteRecord, STATE_EXPERIMENTAL, STATE_VALIDATED,
                              SCOPE_IN_RANGE, SCOPE_NEW_REGION, SCOPE_OUTSIDE)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_JSON = ROOT / "models" / "registry.json"


def _load_card(rel_path: str) -> dict:
    with open(ROOT / rel_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------------------------------------------
# D20 promotion gate

def _promotion_summary(card: dict) -> dict:
    """Normalise the four D20 fields from a model card of any of the registered schemas."""
    plan = bool(card.get("plan") or card.get("validation"))

    baseline = card.get("baseline_beaten") is True
    if card.get("lobo_mae") is not None and card.get("lobo_mae_no_predictor") is not None:
        baseline = baseline or card["lobo_mae"] < card["lobo_mae_no_predictor"]
    for key in ("m2_minus_m0", "m1_minus_m0"):
        diff = card.get(key)
        if isinstance(diff, dict) and diff.get("hi") is not None:
            baseline = baseline or diff["hi"] < 0
    for outcome in (card.get("outcomes") or {}).values():
        diff = outcome.get("m1_minus_m0") if isinstance(outcome, dict) else None
        if isinstance(diff, dict) and diff.get("hi") is not None and outcome.get("verdict") == "validated":
            baseline = baseline or diff["hi"] < 0

    coverage = card.get("interval_coverage") is not None
    for outcome in (card.get("outcomes") or {}).values():
        if isinstance(outcome, dict) and outcome.get("interval_coverage") is not None:
            coverage = True
    if not coverage and isinstance(card.get("validation"), str) and "cover" in card["validation"].lower():
        coverage = True

    training = bool(card.get("training_range") or card.get("training_box") or card.get("scope"))
    return {"plan_committed": plan, "baseline_beaten": baseline,
            "coverage_reported": coverage, "training_range_present": training}


def meets_promotion_criteria(card: dict) -> tuple[bool, list]:
    """D20 check. Returns (passes, reasons_failed)."""
    summary = _promotion_summary(card)
    labels = {"plan_committed": "no committed plan recorded",
              "baseline_beaten": "did not beat the no-predictor baseline on held-out units",
              "coverage_reported": "interval coverage not reported",
              "training_range_present": "no training range recorded"}
    reasons = [labels[k] for k, ok in summary.items() if not ok]
    return (not reasons), reasons


def resolve_state(declared_state: str, card: dict) -> str:
    """Final state: validated only if declared validated AND the D20 check passes."""
    passes, _ = meets_promotion_criteria(card)
    return STATE_VALIDATED if (declared_state == STATE_VALIDATED and passes) else STATE_EXPERIMENTAL


# ---------------------------------------------------------------------------------------------------------------
# Scope helper for the edge-loss family

def _scope_from_flags(flags) -> tuple[str, list]:
    reasons = list(flags.out_of_scope) + list(flags.extrapolation) + list(flags.evidence_scope)
    region = (any("outside the area of the training cells" in r for r in flags.extrapolation)
              or any("new region" in r.lower() for r in flags.out_of_scope))
    if region:
        return SCOPE_NEW_REGION, reasons
    if flags.extrapolation or not flags.in_scope:
        return SCOPE_OUTSIDE, reasons
    return SCOPE_IN_RANGE, reasons


# ---------------------------------------------------------------------------------------------------------------
# Adapters (thin wrappers, no new science)

class _Adapter(mi.BaseModel):
    def __init__(self, entry: dict):
        self.model_id = entry["model_id"]
        self.title = entry.get("title", entry["model_id"])
        self.card_path = entry["card"]
        self.card = _load_card(entry["card"])
        self.declared_state = entry.get("declared_state", STATE_EXPERIMENTAL)
        self.evidence_grade = entry.get("evidence_grade", "")
        self.state = resolve_state(self.declared_state, self.card)
        self.model_version = self.card.get("name", self.model_id)


class EdgeLossV1Adapter(_Adapter):
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        values = {f: float(site.fields[f]) for f in se.FEATURES}
        pred = se.predict_edge_loss(values, model=self.card)
        flags = se.site_flags(values, status=site.fields.get("status", "in_scope"),
                              habitat=site.habitat or "10A", oiling=site.oiling,
                              lat=site.lat, lon=site.lon, model=self.card)
        scope, reasons = _scope_from_flags(flags)
        design = se._design(values, self.card)
        contributions = {term: float(design[i] * self.card["coefficients"][i])
                         for i, term in enumerate(self.card["terms"])}
        return Prediction(
            value=pred["rate"], unit="m/yr edge loss (positive = land lost)",
            interval_lo=pred["lo"], interval_hi=pred["hi"], interval_level=pred["level"],
            interval_method=self.card["interval_method"], scope=scope, scope_reasons=reasons,
            explanation={"per_term_contribution_m_per_yr": contributions,
                         "note": "arithmetic of an OLS model, not a causal claim"},
            evidence_grade=self.evidence_grade, model_id=self.model_id,
            model_version=self.model_version, state=self.state)


class ComposerNaturalRecoveryAdapter(_Adapter):
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        site_dict = {f: float(site.fields[f]) for f in se.FEATURES}
        site_dict["max_oiling"] = site.oiling
        nrs = sc.natural_recovery_summary(site_dict)
        rate = nrs["mean_rate_y1_5"]
        values = {f: float(site.fields[f]) for f in se.FEATURES}
        flags = se.site_flags(values, status=site.fields.get("status", "in_scope"),
                              habitat=site.habitat or "10A", oiling=site.oiling,
                              lat=site.lat, lon=site.lon, model=self.card)
        scope, reasons = _scope_from_flags(flags)
        reasons.append(nrs["bias_note"])
        return Prediction(
            value=rate["median"], unit="m/yr natural-recovery edge loss, mean over years 1-5",
            interval_lo=rate["lo90"], interval_hi=rate["hi90"], interval_level=0.9,
            interval_method="Monte Carlo 5th/95th percentiles of the composed rate "
                            "(clean-edge baseline + Zengel oil excess)",
            scope=scope, scope_reasons=reasons,
            explanation={"baseline": nrs["baseline"], "oil_excess": nrs["oil_excess"],
                         "heavy": nrs["heavy"], "bias_note": nrs["bias_note"]},
            evidence_grade=self.evidence_grade, model_id=self.model_id,
            model_version=self.model_version, state=self.state)


class VegRecoveryAdapter(_Adapter):
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        import math
        a, tau = self.card["parameters"]["A"], self.card["parameters"]["tau"]
        t = scenario.horizon_years + self.card["assumed"]["t_shift_years"]
        ln_rr = -a * math.exp(-t / tau)
        off_lo, off_hi = self.card["residual_offsets_90"]
        value = math.exp(ln_rr)
        reasons = [f"curve fitted to t up to {self.card['extrapolation_beyond_t']} years; {self.card['limits']}"]
        if t > self.card["extrapolation_beyond_t"]:
            scope = SCOPE_OUTSIDE
        else:
            scope = SCOPE_IN_RANGE
        if (site.oiling or "").lower() == "heavy":
            reasons.append("heavy oiling: curve is worse than a no-trend baseline there (FINDINGS 14); "
                           "shown for transparency only")
        return Prediction(
            value=value, unit="total vegetation cover ratio to reference",
            interval_lo=math.exp(ln_rr + off_lo), interval_hi=math.exp(ln_rr + off_hi), interval_level=0.9,
            interval_method="exp of lnRR +/- the 90% leave-one-study-out residual offsets",
            scope=scope, scope_reasons=reasons,
            explanation={"A": a, "tau": tau, "t_years": t, "lnRR": ln_rr,
                         "note": "M2 curve lnRR = -A exp(-t/tau)"},
            evidence_grade=self.card.get("verdict", self.evidence_grade), model_id=self.model_id,
            model_version=self.model_version, state=self.state)


class PahDeclineAdapter(_Adapter):
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        oiling = (site.oiling or "pooled").lower()
        classes = self.card["half_life_years_by_class"]
        cls = classes.get(oiling, classes["pooled"])
        half = cls["half_life"] if cls["half_life"] is not None else 50.0
        lo = cls["lo90"] if cls["lo90"] is not None else half
        hi = cls["hi90"] if cls["hi90"] is not None else max(half, lo)
        scope = SCOPE_IN_RANGE if oiling in classes else SCOPE_OUTSIDE
        reasons = ["Validated within Deepwater Horizon only (one spill); FINDINGS 22."]
        if oiling not in classes:
            reasons.append(f"no half-life fitted for oiling class '{oiling}'; pooled value used")
        return Prediction(
            value=float(half), unit="years (PAH-sum half-life)",
            interval_lo=float(lo), interval_hi=float(hi), interval_level=self.card["interval_level"],
            interval_method=self.card["interval_method"], scope=scope, scope_reasons=reasons,
            explanation={"oiling_class": oiling, "k_per_year": cls.get("k_per_year"),
                         "note": cls.get("note", "first-order decline of the soil PAH sum")},
            evidence_grade=self.evidence_grade, model_id=self.model_id,
            model_version=self.model_version, state=self.state)


class MangroveDamageAdapter(_Adapter):
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        outcome = site.fields.get("outcome", "root_documented_dead_share")
        ys = int(site.fields.get("year_since_spill", scenario.horizon_years))
        card_outcome = self.card["outcomes"][outcome]
        years = {row["year_since_spill"]: row for row in card_outcome["effect_by_year"]}
        if ys not in years:
            scope = SCOPE_OUTSIDE
            ys = min(years, key=lambda y: abs(y - ys))
        else:
            scope = SCOPE_IN_RANGE
        row = years[ys]
        reasons = ["One spill (Bahia Las Minas, Panama); Caribbean; red mangrove; years 1-5 only; "
                   "oiling effect (oiled minus unoiled), not a treatment effect."]
        return Prediction(
            value=float(row["effect"]), unit=f"oiling effect ({card_outcome['label']})",
            interval_lo=float(row["lo90"]), interval_hi=float(row["hi90"]), interval_level=0.9,
            interval_method="Wald 90% interval from the mixed-model fixed effects",
            scope=scope, scope_reasons=reasons,
            explanation={"outcome": outcome, "year_since_spill": ys,
                         "verdict": card_outcome.get("verdict"),
                         "note": "oiled minus unoiled site-year means from a mixed model"},
            evidence_grade=self.evidence_grade, model_id=self.model_id,
            model_version=self.model_version, state=self.state)


_ADAPTERS = {
    "EdgeLossV1Adapter": EdgeLossV1Adapter,
    "ComposerNaturalRecoveryAdapter": ComposerNaturalRecoveryAdapter,
    "VegRecoveryAdapter": VegRecoveryAdapter,
    "PahDeclineAdapter": PahDeclineAdapter,
    "MangroveDamageAdapter": MangroveDamageAdapter,
}


@lru_cache(maxsize=1)
def _registry() -> dict:
    with open(REGISTRY_JSON) as f:
        spec = json.load(f)
    models = {}
    for entry in spec["models"]:
        adapter_cls = _ADAPTERS[entry["adapter"]]
        models[entry["model_id"]] = adapter_cls(entry)
    return models


def get(model_id: str):
    models = _registry()
    if model_id not in models:
        raise KeyError(f"no model '{model_id}' registered; have {sorted(models)}")
    return models[model_id]


def list(state: str | None = None) -> list:
    models = _registry().values()
    if state is None:
        return [m for m in models]
    return [m for m in models if m.state == state]


def validated_only() -> list:
    return list(state=STATE_VALIDATED)


def model_ids() -> list:
    return sorted(_registry())
