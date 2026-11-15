"""Turns a decision-pipeline report into plain display objects (decision D40). No Streamlit in here.

The pipeline (decision_pipeline.run_decision) returns a DecisionReport whose option rows are dicts. Another part of the
project is still adding fields to it (an `evidence_state` per option, an "insufficient evidence" headline, habitat
normalisation). So everything here reads fields with `field()` (works on dicts and objects) and a default, and loops over
whatever options, classes and outcomes exist. Nothing assumes a fixed list of options or classes.

Evidence grade of an option, in order of preference:
    1. the pipeline's own `evidence_state`, if it is present and recognisable;
    2. otherwise derived: composer evidence -> the composer model's state (experimental); mangrove screening rows and
       harm flags from the AI-proposed conditions table -> AI-proposed; literature verdicts or no evidence -> rules and
       literature only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field

from . import ui_theme as T

AI_TABLES = ("treatment_conditions.csv", "mangrove_screening.csv", "elicited_priors.csv")
OUTCOME_LABELS = {
    "edge_loss_avoided_m": ("Marsh edge saved vs natural recovery", "m"),
    "veg_cover_ratio_gain": ("Extra vegetation cover vs natural recovery", "fraction of reference cover"),
}


def field(obj, key: str, default=None):
    """Read a field from a dict or an object, with a default (new fields may not exist yet)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        value = obj.get(key, default)
    else:
        value = getattr(obj, key, default)
    return default if value is None else value


def plain_name(option: str) -> str:
    text = str(option).replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def grade_from_text(value) -> str | None:
    """Map free text such as 'experimental', 'AI-proposed', 'rules and literature' to a grade key, or None."""
    if isinstance(value, dict):
        for k in ("grade", "state", "label", "evidence_state", "name"):
            if k in value:
                return grade_from_text(value[k])
        return None
    if value is None:
        return None
    t = str(value).lower().replace("_", " ").replace("-", " ").strip()
    if not t:
        return None
    if "ai proposed" in t or t.startswith("ai ") or "elicited" in t:
        return "ai_proposed"
    if "illustrative" in t:
        return "illustrative"
    if "experimental" in t or "suggestive" in t:
        return "experimental"
    if t.startswith("validated") or t == "validated" or "validated" in t.split():
        return "validated"
    if any(w in t for w in ("rule", "literature", "insufficient", "no evidence", "none", "screening")):
        return "rules_literature"
    return None


@dataclass
class Outcome:
    outcome: str
    year: int | None
    median: float
    lo: float
    hi: float
    unit: str
    direction: str
    decision_point: bool
    label: str

    @property
    def crosses_zero(self) -> bool:
        return self.lo <= 0.0 <= self.hi


@dataclass
class OptionView:
    option: str
    name: str
    cls: str
    class_name: str
    grade: str
    grade_note: str
    source_text: str
    source_ids: list
    verdict_text: str
    rule_verdict: str
    rule_reason: str
    evidence_verdict: str
    outcomes: list = dc_field(default_factory=list)
    caveats: list = dc_field(default_factory=list)
    conditions: list = dc_field(default_factory=list)
    harm_flags: list = dc_field(default_factory=list)
    exclusion_reasons: list = dc_field(default_factory=list)
    rank_in_class: int | None = None
    evidence_state_label: str = ""
    evidence_design: str = ""
    advisory_notes: list = dc_field(default_factory=list)
    ecological_score: float | None = None
    model_id: str | None = None
    raw: dict = dc_field(default_factory=dict)
    category: str = ""               # V5.1 (D41): stakeholder category from the pipeline, never recomputed in the UI
    category_label: str = ""
    category_reason: str = ""
    rank_basis: str = ""             # "evidence" or "display_convention"
    rank_basis_text: str = ""

    def decision_outcomes(self) -> list:
        return [o for o in self.outcomes if o.decision_point]


def _outcomes(row) -> list:
    out = []
    for o in field(row, "benefit_outcomes", []) or []:
        lo, hi, med = field(o, "lo90"), field(o, "hi90"), field(o, "median")
        if not (finite(lo) and finite(hi) and finite(med)):
            continue
        kind = str(field(o, "outcome", "outcome"))
        label, _ = OUTCOME_LABELS.get(kind, (plain_name(kind), ""))
        year = field(o, "year")
        out.append(Outcome(kind, int(year) if finite(year) else None, float(med), float(lo), float(hi),
                           str(field(o, "unit", "")), str(field(o, "direction", "")), bool(field(o, "decision_point", False)), label))
    return out


def derive_grade(row) -> tuple[str, str]:
    """Evidence grade and a one-line reason for an option row."""
    # `evidence_state` from the pipeline is a verdict state (benefit / no clear difference / insufficient evidence), not a
    # grade, so it is shown as a label (see OptionView.evidence_state_label) and does not set the grade.
    explicit = grade_from_text(field(row, "evidence_grade"))
    cls = str(field(row, "recommendation_class", ""))
    source = str(field(row, "evidence_source", ""))
    rule_id = str(field(row, "rule_id", ""))
    rule_source = str(field(row, "rule_source", ""))
    flags = field(row, "harm_flags", []) or []
    if explicit:
        return explicit, "grade set by the decision pipeline"
    if source == "scenario_composer":
        state = grade_from_text(field(row, "model_state")) or "experimental"
        return state, "differences from one site's field plots, built by the experimental scenario composer"
    if rule_id.startswith("mangrove_screening") or "AI-PROPOSED" in rule_source.upper():
        return "ai_proposed", "verdict written by an AI assistant from the literature, not reviewed by a person"
    if any(any(t in str(field(f, "source", "")) for t in AI_TABLES) for f in flags):
        return "ai_proposed", "the harm condition comes from an AI-proposed table, not reviewed by a person"
    if source == "evidence_verdicts":
        return "rules_literature", "literature verdict (AI-extracted table, not yet checked by a person)"
    if cls == "C":
        return "rules_literature", "reference option: what happens without cleanup"
    return "rules_literature", "screening rule only; no outcome evidence for this option"


def source_text(row) -> tuple[str, list]:
    source = str(field(row, "evidence_source", ""))
    ids = list(field(row, "source_ids", []) or [])
    model_id = field(row, "model_id")
    if source == "scenario_composer":
        text = "Field-plot differences through the scenario composer"
        if model_id:
            ids = [str(model_id)] + ids
    elif source == "evidence_verdicts":
        text = "Literature evidence verdict"
    else:
        text = "Screening rule only (no outcome evidence)"
    rule = str(field(row, "rule_source", "") or "")
    if rule:
        ids = ids + [f"rule source: {rule}"]
    return text, ids


def _verdict_text(row, cls: str, outcomes: list, anchor_hint: str = "") -> str:
    ev = str(field(row, "evidence_verdict", ""))
    if cls == "E":
        reasons = field(row, "exclusion_reasons", []) or []
        why = str(field(reasons[0], "detail", "")) if reasons else str(field(row, "rule_reason", ""))
        return f"Excluded: {why}" if why else "Excluded."
    if cls == "C":
        return "The reference. Every other option is compared with this."
    if cls == "A":
        bits = []
        for o in [x for x in outcomes if x.decision_point and x.direction == "benefit"]:
            unit = "m" if o.outcome == "edge_loss_avoided_m" else ""
            where = f"by year {o.year}" if o.outcome == "edge_loss_avoided_m" else f"at year {o.year}"
            what = "marsh edge saved" if o.outcome == "edge_loss_avoided_m" else "extra vegetation cover"
            fmt = "{:.1f}" if o.outcome == "edge_loss_avoided_m" else "{:.2f}"
            bits.append(f"{what} {where}: {fmt.format(o.median)}{' ' + unit if unit else ''} "
                        f"(90% range {fmt.format(o.lo)} to {fmt.format(o.hi)})")
        return "Field plots show a benefit over natural recovery: " + "; ".join(bits) if bits else f"Evidence of benefit: {ev}"
    if cls == "D":
        flags = field(row, "harm_flags", []) or []
        detail = str(field(flags[0], "detail", "")) if flags else ""
        return "Allowed, but " + (detail[:1].lower() + detail[1:] if detail else "harm is reported under some conditions")
    return f"No clear evidence either way ({ev})." if ev else "No clear evidence either way."


def option_view(row) -> OptionView:
    cls = str(field(row, "recommendation_class", "B"))
    grade, note = derive_grade(row)
    src, ids = source_text(row)
    outs = _outcomes(row)
    caveats = [str(c) for c in field(row, "caveats", []) or [] if c]
    rank = field(row, "rank_in_class")
    eco = field(row, "ecological_score_assumed")
    return OptionView(
        option=str(field(row, "option", "?")), name=plain_name(field(row, "option", "?")), cls=cls,
        class_name=T.class_style(cls)["name"], grade=grade, grade_note=note, source_text=src, source_ids=ids,
        verdict_text=_verdict_text(row, cls, outs), rule_verdict=str(field(row, "rule_verdict", "")),
        rule_reason=str(field(row, "rule_reason", "")), evidence_verdict=str(field(row, "evidence_verdict", "")),
        outcomes=outs, caveats=caveats, conditions=list(field(row, "conditions", []) or []),
        harm_flags=list(field(row, "harm_flags", []) or []), exclusion_reasons=list(field(row, "exclusion_reasons", []) or []),
        rank_in_class=int(rank) if finite(rank) else None,
        evidence_state_label=str(field(row, "evidence_state_label", "") or ""), evidence_design=str(field(row, "evidence_design", "") or ""),
        advisory_notes=[str(x) if not isinstance(x, dict) else str(x.get("text") or x.get("detail") or x) for x in field(row, "advisory_notes", []) or []], ecological_score=float(eco) if finite(eco) else None,
        model_id=field(row, "model_id"), raw=dict(row) if isinstance(row, dict) else {},
        category=str(field(row, "recommendation_category", "") or ""),
        category_label=str(field(row, "recommendation_category_label", "") or ""),
        category_reason=str(field(row, "recommendation_category_reason", "") or ""),
        rank_basis=str(field(row, "rank_basis", "") or ""), rank_basis_text=str(field(row, "rank_basis_text", "") or ""))


@dataclass
class ReportView:
    headline: str
    tier: str
    tier_grade: str
    tier_text: str
    scope_message: str
    options: list
    reference: list
    headline_grade: str
    headline_grade_text: str
    out_of_scope: bool
    evidence_state_label: str = ""
    literature_notes: list = dc_field(default_factory=list)
    advisories: list = dc_field(default_factory=list)
    extra: dict = dc_field(default_factory=dict)
    decision_outcome: str = ""       # V5.1 (D41)
    decision_outcome_label: str = ""
    recommendation_summary: dict = dc_field(default_factory=dict)
    abstentions: list = dc_field(default_factory=list)

    def by_class(self) -> dict:
        groups = {c: [] for c in T.CLASS_ORDER}
        for o in self.options:
            groups.setdefault(o.cls, []).append(o)
        return groups


def reference_rows(report) -> list:
    nat = field(report, "natural_recovery", {}) or {}
    return list(field(nat, "reference", []) or [])


def reference_grade(row) -> str:
    return grade_from_text(field(row, "evidence_state")) or grade_from_text(field(row, "state")) or "rules_literature"


NO_ASSESSMENT_TIERS = ("out_of_scope", "unsupported_habitat")   # the pipeline made no assessment (refusal or abstention)


def report_view(report) -> ReportView:
    tier = str(field(report, "scope_tier", "rules_and_literature"))
    headline = str(field(report, "headline", ""))
    options = [option_view(r) for r in field(report, "options", []) or []]
    options.sort(key=lambda o: (T.CLASS_ORDER.index(o.cls) if o.cls in T.CLASS_ORDER else 99, o.rank_in_class or 999, o.option))
    tier_grade = T.TIER_TO_GRADE.get(tier, grade_from_text(tier) or "rules_literature")
    tier_text = T.TIER_TEXT.get(tier, tier.replace("_", " ").capitalize())
    report_level = None
    a_options = [o for o in options if o.cls == "A"]
    if tier in NO_ASSESSMENT_TIERS:
        hg, hg_text = "out_of_scope", T.TIER_TEXT.get(tier, "Out of scope")
    elif headline.lower().startswith("insufficient evidence"):
        hg, hg_text = "rules_literature", "Insufficient evidence"
    elif a_options:
        hg = T.weakest_grade([o.grade for o in a_options] + ([report_level] if report_level else []))
        hg_text = T.grade_info(hg)["label"]
    else:
        hg = T.weakest_grade([tier_grade] + ([report_level] if report_level else []))
        hg_text = T.grade_info(hg)["label"]
    return ReportView(headline=headline, tier=tier, tier_grade=tier_grade, tier_text=tier_text,
                      scope_message=str(field(report, "scope_message", "")), options=options, reference=reference_rows(report),
                      headline_grade=hg, headline_grade_text=hg_text, out_of_scope=tier in NO_ASSESSMENT_TIERS,
                      decision_outcome=str(field(report, "decision_outcome", "") or ""),
                      decision_outcome_label=str(field(report, "decision_outcome_label", "") or ""),
                      recommendation_summary=dict(field(report, "recommendation_summary", {}) or {}),
                      abstentions=list(field(report, "abstentions", []) or []),
                      evidence_state_label=str(field(report, "evidence_state_label", "") or ""),
                      literature_notes=list(field(report, "literature_notes", []) or []),
                      advisories=[str(x) for x in field(report, "advisories", []) or []],
                      extra={"version": field(report, "version", {}), "trace": field(report, "trace", []),
                             "characterisation": field(report, "characterisation", {}), "plots": field(report, "plots", {})})


# ---------------------------------------------------------------------------------------------------------------
# Interval comparison helpers

def interval_rows(options: list, outcome: str, year: int) -> list:
    """One row per option that has this outcome at this year (for the interval chart)."""
    rows = []
    for o in options:
        for x in o.outcomes:
            if x.outcome == outcome and x.year == year:
                rows.append({"option": o.name, "cls": o.cls, "grade": o.grade, "median": x.median, "lo": x.lo, "hi": x.hi,
                             "crosses_zero": x.crosses_zero, "label": x.label, "unit": x.unit})
    return rows


def available_outcomes(options: list) -> dict:
    """{outcome: sorted years} over all options."""
    found: dict = {}
    for o in options:
        for x in o.outcomes:
            if x.year is not None:
                found.setdefault(x.outcome, set()).add(x.year)
    return {k: sorted(v) for k, v in found.items()}


def any_overlap(rows: list) -> bool:
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["lo"] <= b["hi"] and b["lo"] <= a["hi"]:
                return True
    return False


def fmt_interval(median, lo, hi, digits: int = 1, unit: str = "") -> str:
    f = f"{{:.{digits}f}}"
    u = f" {unit}" if unit else ""
    return f"{f.format(median)}{u} (90% range {f.format(lo)} to {f.format(hi)})"
