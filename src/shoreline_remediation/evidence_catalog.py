"""Data layer for the Evidence explorer (V5.2). No Streamlit, no scientific calculation, no decision logic.

It reads the repository's evidence and screening tables without changing them and returns ONE tidy table in which every row
keeps the file and identifier it came from. Material of different standing is never merged: the `kind` column says whether a row is
a published study record, a literature summary, a field-plot effect used by the experimental composer, screening metadata written
or transcribed by an AI, or an evidence verdict the pipeline reads. Missing information is shown as such: a row with no DOI or URL
says "Source not available in repository" and nothing is invented to fill a column.

Authority for decisions stays with decision_pipeline.run_decision(); `pipeline_context()` only calls it and re-shapes its report.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import habitat as hab

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "data" / "knowledge"
TABLES = KNOWLEDGE / "tables"

NOT_IN_REPO = "Source not available in repository"
NOT_RECORDED = "not recorded in the repository table"

KIND_STUDY = "AI-extracted study record (Proposed)"
KIND_LITERATURE = "Literature summary (not used in numbers)"
KIND_COMPOSER = "Field-plot effect (experimental composer input)"
KIND_SCREENING = "Screening metadata (AI-proposed or AI-transcribed)"
KIND_VERDICT = "Evidence verdict read by the pipeline"
KINDS = (KIND_STUDY, KIND_LITERATURE, KIND_COMPOSER, KIND_SCREENING, KIND_VERDICT)

KIND_NOTES = {
    KIND_STUDY: ("A result extracted from a published study by an AI agent. Its status is Proposed (or abstract-only). The table's checked-by "
                 "field is one blanket owner attestation, not an independent expert review. Not a prediction."),
    KIND_LITERATURE: "A qualitative summary of a study. It is shown for context and does not enter any number the platform computes.",
    KIND_COMPOSER: "A paired field-plot difference that the experimental scenario composer uses (heavily oiled salt marsh). Experimental.",
    KIND_SCREENING: "Written or transcribed by an AI and marked Proposed. Not evidence of remediation effectiveness and not human-verified.",
    KIND_VERDICT: ("The verdict the decision pipeline reads for a technology and habitat class. In this table it comes from one or two single studies, or from no eligible rows (see the basis in the result); no row is a meta-analytic pool. 'No clear difference' is the rule's label for that situation, not a measured null effect."),
}

# Evidence chip (ui_theme.GRADES key) shown beside a row, so the explorer uses the same visual language as the site page.
KIND_CHIP = {KIND_STUDY: "rules_literature", KIND_LITERATURE: "rules_literature", KIND_COMPOSER: "experimental",
             KIND_SCREENING: "ai_proposed", KIND_VERDICT: "rules_literature"}

HABITAT_CLASSES = ("marsh", "mangrove", "rocky/hard", "sand/gravel beach", "other")

COLUMNS = ["record_id", "kind", "source_file", "source_id", "habitat_label", "habitat_class", "esi_codes", "option", "option_code",
           "outcome", "comparator", "location", "oil", "design", "result", "grade", "status", "applicability", "limitations",
           "citation", "link", "source_location", "provenance", "pipeline_use"]

# Explicit, exact name matches only. Anything else keeps the table's own wording.
_UNTESTED_TO_CODE = {"in-situ burning": "in_situ_burning", "vegetation cutting": "vegetation_cutting",
                     "natural attenuation (reference)": "natural_attenuation", "low-pressure ambient flushing": "low_pressure_flushing",
                     "passive sorbents": "passive_sorbents", "replanting after cleanup": "planting",
                     "surface washing agents / shoreline cleaners (e.g. Corexit 9580)": "surface_washing_agents"}
_EXTRA_NAMES = {"in_situ_burning": "In-situ burning", "planting": "Planting (after mechanical cleanup)",
                "oiling_effect": "Oiling effect (no treatment)"}
_PIPELINE_USE = {
    KIND_STUDY: "Pooled into the pipeline's evidence verdicts only if it meets the pooling rules (grades A to C, with a control; see docs/F8_LITERATURE_POOLING_PLAN.md)",
    KIND_LITERATURE: "Not used in any platform number",
    KIND_COMPOSER: "Input to the experimental scenario composer (heavily oiled salt marsh)",
    KIND_VERDICT: "Read by run_decision() as the evidence state of the option",
}


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


@lru_cache(maxsize=1)
def _option_names() -> dict:
    names = dict(_EXTRA_NAMES)
    try:
        tech = _read(TABLES / "technology.csv")
        names.update({r.code: r.name for r in tech.itertuples()})
    except (OSError, pd.errors.ParserError):
        pass
    return names


def option_name(code: str) -> str:
    return _option_names().get(code, code.replace("_", " ").capitalize()) if code else ""


def habitat_class_of(text: str) -> str:
    """Habitat class of a free-text habitat label. Reuses decision_pipeline._literature_habitat, the function the pipeline itself applies to
    the same table, so the explorer and the decision engine cannot disagree; tests/test_v52_evidence_catalog.py also compares it with
    validation.literature_pooling._habitat_class, which assigned the classes in evidence_verdicts.csv."""
    from .decision_pipeline import _literature_habitat
    return _literature_habitat(_clean(text))


def _link(doi: str, url: str = "") -> str:
    doi, url = _clean(doi), _clean(url)
    if url.startswith("http"):
        return url
    if doi.startswith("http"):
        return doi
    if doi:
        return "https://doi.org/" + doi
    return NOT_IN_REPO


def _row(kind: str, source_file: str, source_id: str, **kw) -> dict:
    row = {c: "" for c in COLUMNS}
    row.update(kind=kind, source_file=source_file, source_id=source_id, pipeline_use=_PIPELINE_USE.get(kind, ""))
    row.update({k: _clean(v) for k, v in kw.items()})
    row["record_id"] = f"{source_file.split('/')[-1]}:{source_id}"
    row["option"] = row["option"] or option_name(row["option_code"])
    row["link"] = row["link"] or NOT_IN_REPO
    row["citation"] = row["citation"] or NOT_IN_REPO
    return row


def _study_records() -> list:
    df = _read(KNOWLEDGE / "literature_effects.csv")
    rows = []
    for r in df.itertuples():
        control = _clean(r.untreated_oiled_control)
        comparator = ("Untreated oiled control" if control == "yes" else
                      f"No untreated oiled control ({control})" if control else f"Comparator {NOT_RECORDED}")
        unit = f" ({_clean(r.unit)})" if _clean(r.unit) else ""
        treated, ctrl = _clean(r.treated_mean), _clean(r.control_mean)
        means = f"; treated mean {treated} vs control mean {ctrl}{unit}" if treated and ctrl else ""
        who = (f"Extracted by {_clean(r.extracted_by) or NOT_RECORDED}; checked by {_clean(r.checked_by) or NOT_RECORDED}"
               f"; value origin: {_clean(r.value_origin) or NOT_RECORDED}")
        if _clean(r.status) == "abstract_only":
            who += ("; status abstract_only: the study was read at abstract level, so the checked-by text above (a blanket attestation "
                    "on every row) should not be read as a full-text check")
        rows.append(_row(KIND_STUDY, "data/knowledge/literature_effects.csv", r.effect_id, habitat_label=r.habitat,
                         habitat_class=habitat_class_of(r.habitat), esi_codes=r.esi_code, option_code=r.technology,
                         outcome=" - ".join(x for x in (_clean(r.outcome), _clean(r.metric)) if x), comparator=comparator,
                         location=", ".join(x for x in (_clean(r.location), _clean(r.year)) if x),
                         oil=" ".join(x for x in (_clean(r.oil_type), _clean(r.oil_weathering)) if x), design=r.design,
                         result=(_clean(r.reported_effect).rstrip(". ") + means).strip("; "), grade=r.grade, status=r.status,
                         applicability="; ".join(x for x in (f"treatment: {_clean(r.treatment_detail)}" if _clean(r.treatment_detail) else "",
                                                             f"season: {_clean(r.season)}" if _clean(r.season) else "",
                                                             f"wave energy: {_clean(r.wave_energy)}" if _clean(r.wave_energy) else "") if x),
                         limitations="; ".join(x for x in (f"harm reported: {_clean(r.harm_reported)}" if _clean(r.harm_reported) else "",
                                                           _clean(r.notes)) if x),
                         citation=r.citation, link=_link(r.doi), source_location=r.source_location, provenance=who))
    return rows


def _literature_summaries() -> list:
    df = _read(KNOWLEDGE / "treatment_evidence_untested.csv")
    rows = []
    for i, r in enumerate(df.itertuples(), 1):
        code = _UNTESTED_TO_CODE.get(r.treatment, "")
        rows.append(_row(KIND_LITERATURE, "data/knowledge/treatment_evidence_untested.csv", f"row {i}", habitat_label=r.habitat,
                         habitat_class=habitat_class_of(r.habitat), option=option_name(code) if code else r.treatment, option_code=code,
                         outcome=r.outcome, comparator="see result and conditions", location=r.study_location, oil=r.conditions,
                         design=r.evidence_type, result=f"direction: {r.direction}. {_clean(r.magnitude)}",
                         applicability=r.conditions, limitations=r.notes_limits, citation=r.citation, link=_link(r.doi_or_url),
                         provenance=f"Access level recorded: {_clean(r.access_level) or NOT_RECORDED}"))
    return rows


def _composer_inputs() -> list:
    df = _read(TABLES / "evidence_effect.csv")
    rows = []
    for r in df.itertuples():
        rows.append(_row(KIND_COMPOSER, "data/knowledge/tables/evidence_effect.csv", r.effect_id, habitat_label=r.habitat,
                         habitat_class=habitat_class_of(r.habitat), option_code=r.technology, outcome=f"{r.outcome} ({r.unit})",
                         comparator="natural recovery plots", location="see citation (location not a column of this table)",
                         oil=f"oiling: {r.oiling}", design=r.design,
                         result=f"effect {r.effect} (90% range {r.lo90} to {r.hi90}); {r.years_since_spill} year(s) after the spill ({r.period}); "
                                f"n = {r.n} vs {r.n_baseline}",
                         grade="", status=r.status, applicability=f"heavily oiled salt marsh; evidence type: {r.evidence_type}",
                         limitations="Experimental composer input: one site's field plots; classes were not randomly assigned unless the design says so.",
                         citation=r.source, link=_link("", re.search(r"doi:(\S+)", r.source).group(1) if re.search(r"doi:(\S+)", r.source) else ""),
                         provenance=f"Status recorded: {_clean(r.status)}"))
    return rows


def _screening_metadata() -> list:
    rows = []
    ms = _read(KNOWLEDGE / "mangrove_screening.csv")
    for r in ms.itertuples():
        rows.append(_row(KIND_SCREENING, "data/knowledge/mangrove_screening.csv", r.tool_code or r.treatment, habitat_label="mangrove",
                         habitat_class="mangrove", option=r.treatment, option_code=r.tool_code, outcome="screening verdict",
                         comparator="natural recovery (reference)", location="not stated", design=r.evidence_class,
                         result=f"verdict: {r.verdict}. {r.reason}", status=r.provenance, applicability=r.conditions,
                         limitations="Screening metadata only; says nothing quantitative about remediation effectiveness.",
                         citation=r.source, provenance=r.provenance,
                         pipeline_use="Rule metadata for mangrove screening (AI-proposed)"))
    nr = _read(TABLES / "noaa_response_rating.csv")
    for r in nr.itertuples():
        code = r.pipeline_option.split("|")[0]
        h = hab.get(r.esi_code)
        rows.append(_row(KIND_SCREENING, "data/knowledge/tables/noaa_response_rating.csv", r.rating_id, habitat_label=r.habitat,
                         habitat_class=(h.habitat_class if h else habitat_class_of(r.habitat)), esi_codes=r.esi_code,
                         option=" / ".join(option_name(c) for c in r.pipeline_option.split("|")), option_code=code,
                         outcome="NOAA habitat-impact letter rating (not effectiveness)", comparator="not applicable",
                         location="not applicable", design=f"NOAA table: {r.noaa_table}",
                         result=f"ratings by oil category: I={r.cat_I}, II={r.cat_II}, III={r.cat_III}, IV={r.cat_IV}, V={r.cat_V}",
                         status=r.status, applicability=_clean(r.note), limitations="Letters rate adverse habitat impact, not how well oil is removed.",
                         citation=r.source, source_location=f"page {r.page}", provenance=r.status,
                         pipeline_use="Habitat-impact rating used by the pipeline's eligibility rules (Proposed, not human-verified)"))
    bn = _read(TABLES / "beach_literature_notes.csv")
    for r in bn.itertuples():
        codes = [c for c in r.esi_codes.split("|") if c]
        classes = {hab.get(c).habitat_class for c in codes if hab.get(c)}
        rows.append(_row(KIND_SCREENING, "data/knowledge/tables/beach_literature_notes.csv", r.note_id,
                         habitat_label="beach (ESI " + ", ".join(codes) + ")", habitat_class=(next(iter(classes)) if len(classes) == 1 else "other"),
                         esi_codes="|".join(codes), outcome=r.topic, comparator="see statement", design=r.evidence_class, result=r.statement,
                         status=r.status, limitations=r.display_label, citation=r.source, provenance=f"{r.status}; source check: {_clean(r.source_checked)}",
                         pipeline_use="Shown beside ESI 5 and 6A decisions as 'literature, not a prediction'"))
    return rows


def _evidence_verdicts() -> list:
    df = _read(KNOWLEDGE / "evidence_verdicts.csv")
    rows = []
    for r in df.itertuples():
        rows.append(_row(KIND_VERDICT, "data/knowledge/evidence_verdicts.csv", f"{r.technology}|{r.habitat}|{r.outcome_family}",
                         habitat_label=r.habitat, habitat_class=r.habitat, esi_codes=r.esi_codes, option_code=r.technology,
                         outcome=r.outcome_family, comparator="natural recovery / untreated oiled control",
                         location="across the studies named in the basis", design="evidence verdict (rule label)", result=f"verdict: {r.verdict} ({r.basis})",
                         grade=f"grade mix: {r.grade_mix}" if _clean(r.grade_mix) else "", status="derived", limitations=r.notes,
                         citation="see the individual study records of this technology and habitat class (basis column)",
                         provenance=f"n studies: {_clean(r.n_studies) or '0'}"))
    return rows


@lru_cache(maxsize=1)
def load_catalog() -> pd.DataFrame:
    """The whole catalogue. Raises nothing for a missing optional column; a missing file raises FileNotFoundError (the page reports it)."""
    rows = (_study_records() + _literature_summaries() + _composer_inputs() + _screening_metadata() + _evidence_verdicts())
    return pd.DataFrame(rows, columns=COLUMNS)


def _tokens(esi_text: str) -> set:
    return {t.strip().upper() for t in re.split(r"[/|,]", esi_text or "") if t.strip()}


def filter_catalog(df: pd.DataFrame, *, habitat_classes=(), esi=(), options=(), kinds=(), grades=(), statuses=(), locations=(),
                   text: str = "") -> pd.DataFrame:
    """Plain filtering. An empty selection means no restriction. Text search covers the fields a reader would look for."""
    out = df
    if habitat_classes:
        out = out[out.habitat_class.isin(habitat_classes)]
    if esi:
        want = {e.upper() for e in esi}
        out = out[out.esi_codes.map(lambda v: bool(_tokens(v) & want or "ALL" in _tokens(v)))]
    if options:
        out = out[out.option.isin(options)]
    if kinds:
        out = out[out.kind.isin(kinds)]
    if grades:
        out = out[out.grade.isin(grades)]
    if statuses:
        out = out[out.status.isin(statuses)]
    if locations:
        out = out[out.location.isin(locations)]
    if text and text.strip():
        needle = text.strip().lower()
        hay = (out.citation + " " + out.outcome + " " + out.option + " " + out.habitat_label + " " + out.location + " " + out.result
               + " " + out.source_id).str.lower()
        out = out[hay.str.contains(re.escape(needle), regex=True)]
    return out


# ---------------------------------------------------------------------------------------------------------------
# Gaps and the link to pipeline decisions

STUDY_OPTIONS_EXCLUDED = ("oiling_effect",)   # an oiling effect is not a remediation option


def gap_matrix(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Option x habitat class: number of published study records and the pipeline's verdict(s). A cell with zero study records is a gap.
    The verdict column text is read from evidence_verdicts.csv unchanged; nothing is computed from it."""
    df = load_catalog() if df is None else df
    studies = df[df.kind == KIND_STUDY]
    verdicts = df[df.kind == KIND_VERDICT]
    codes = sorted({c for c in list(studies.option_code) + list(verdicts.option_code) if c and c not in STUDY_OPTIONS_EXCLUDED})
    out = []
    for code in codes:
        for cls in HABITAT_CLASSES[:-1]:
            n = int(((studies.option_code == code) & (studies.habitat_class == cls)).sum())
            v = verdicts[(verdicts.option_code == code) & (verdicts.habitat_class == cls)]
            kinds = sorted(set(re.match(r"verdict: ([^()]+)", x).group(1).strip() for x in v.result)) if len(v) else []
            out.append({"option_code": code, "option": option_name(code), "habitat_class": cls, "study_records": n,
                        "pipeline_verdicts": ", ".join(kinds) if kinds else "no pipeline verdict row", "gap": n == 0})
    return pd.DataFrame(out)


@lru_cache(maxsize=16)
def pipeline_context(esi: str) -> dict:
    """What run_decision() reports for one ESI shoreline type at default inputs (moderate oiling, medium oil, no site record).
    Fields are copied from the report; nothing is classified here. Returns {"error": ...} if the pipeline cannot run."""
    from .decision_pipeline import run_decision
    try:
        report = run_decision({}, habitat=esi, oiling_class="moderate", oil="medium")
    except (ValueError, KeyError, TypeError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    d = report.to_dict()
    options = [{"option_code": r["option"], "option": option_name(r["option"]), "class": r["recommendation_class"],
                "category": r["recommendation_category"], "category_label": r["recommendation_category_label"],
                "evidence_state": r.get("evidence_state_label", ""),
                "rating": (r.get("habitat_rating") or {}).get("rating", ""),
                "rating_status": "Proposed, not human-verified" if "proposed" in str((r.get("habitat_rating") or {}).get("source", "")).lower() else ""}
               for r in d["options"]]
    return {"esi": esi, "scope_tier": d["scope_tier"], "decision_outcome_label": d["decision_outcome_label"],
            "evidence_state_label": d.get("evidence_state_label", ""), "options": options,
            "abstentions": [a.get("text", "") for a in d.get("abstentions", [])],
            "inputs": "moderate oiling, medium oil, no site record (screening view; numbers appear only on the Site assessment page)"}


def esi_choices() -> list:
    """(code, name) of every shoreline type in the habitat table, for the context selector."""
    return [(code, h.name) for code, h in sorted(hab.table().items())]
