"""Evidence explorer page (V5.2). Presentation only: rows come from evidence_catalog (repository tables, unchanged) and the decision
context from decision_pipeline.run_decision() through evidence_catalog.pipeline_context(). Nothing here classifies an option or
rates evidence; a column the repository does not hold reads "Source not available in repository" or "not recorded".

Entry point: render_evidence(). Widget keys are listed in STATE_KEYS so the dashboard can keep them when the page changes.
"""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from . import evidence_catalog as EC
from . import habitat as hab
from . import ui_components as C
from . import ui_theme as T

STATE_KEYS = ("ev_text", "ev_kinds", "ev_classes", "ev_esi", "ev_options", "ev_grades", "ev_status", "ev_locations", "ev_pick",
              "ev_ctx_esi", "ev_gap_class")

INTRO = ("Every row below comes from a table in this repository and keeps the file and identifier it came from. Rows of different "
         "standing are never merged: study records extracted by an AI, literature summaries, experimental composer inputs, "
         "AI-proposed screening metadata and the evidence verdicts the pipeline reads each carry their own label.")
CAVEAT = ("The explorer shows what the repository holds. It is not a verification of the evidence: the study records are AI-extracted "
          "and marked Proposed, the NOAA habitat-impact ratings are AI-transcribed and not human-verified, and no expert review exists. "
          "A habitat or option with no record is an evidence gap, not a finding that the option does not work.")

_TABLE_COLUMNS = {"kind": "Kind", "habitat_class": "Habitat class", "esi_codes": "ESI", "option": "Option", "outcome": "Outcome",
                  "result": "Result as recorded", "grade": "Grade as recorded", "status": "Status", "record_id": "Record"}


def _unique(series: pd.Series) -> list:
    return sorted(v for v in series.unique() if v)


def _default_esi() -> str:
    """The ESI code of the habitat chosen on the Site assessment page, if any (site selection persists across pages)."""
    try:
        from .site_view import HABITAT_BY_KEY
        view = HABITAT_BY_KEY.get(st.session_state.get("site_habitat", ""))
        return str(getattr(view, "esi", "") or "")
    except Exception:   # noqa: BLE001 - the explorer must open even if the site view cannot be imported
        return ""


def _chip(kind: str) -> str:
    return T.grade_html(EC.KIND_CHIP.get(kind, "rules_literature"), kind)


def _filters(df: pd.DataFrame) -> pd.DataFrame:
    st.text_input("Search", key="ev_text", placeholder="Citation, outcome, option, habitat, location or record id")
    c1, c2, c3 = st.columns(3)
    kinds = c1.multiselect("Kind of evidence", list(EC.KINDS), key="ev_kinds")
    classes = c2.multiselect("Habitat class", list(EC.HABITAT_CLASSES), key="ev_classes")
    esi_options = sorted({t for v in df.esi_codes for t in EC._tokens(v)})
    esi = c3.multiselect("ESI code", esi_options, key="ev_esi",
                         help="Study records may name several ESI codes (for example 1A/2A) or none; blank means the table gives no code.")
    options = st.multiselect("Remediation option", _unique(df.option), key="ev_options")
    with st.expander("More filters: recorded grade, status, study location"):
        d1, d2, d3 = st.columns(3)
        grades = d1.multiselect("Grade as recorded", _unique(df.grade), key="ev_grades",
                                help="Grades are as recorded by the extraction protocol (design, control, risk of bias); see docs/R2_LITERATURE_EVIDENCE_GUIDE.md.")
        statuses = d2.multiselect("Status as recorded", _unique(df.status), key="ev_status")
        locations = d3.multiselect("Study location", _unique(df.location), key="ev_locations")
    return EC.filter_catalog(df, habitat_classes=classes, esi=esi, options=options, kinds=kinds, grades=grades, statuses=statuses,
                             locations=locations, text=st.session_state.get("ev_text", ""))


def _field(label: str, value: str) -> None:
    st.markdown(f"**{label}**  \n{escape(value) if value else EC.NOT_RECORDED}")


def _detail(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f"{_chip(row.kind)}", unsafe_allow_html=True)
        st.caption(EC.KIND_NOTES[row.kind])
        st.markdown(f"#### {row.option or 'Option not stated'} - {row.outcome or 'outcome not stated'}")
        a, b = st.columns(2)
        with a:
            _field("Habitat (as recorded)", f"{row.habitat_label} (class: {row.habitat_class})" if row.habitat_label else "")
            _field("ESI code(s)", row.esi_codes)
            _field("Comparator", row.comparator)
            _field("Study location", row.location)
            _field("Oil", row.oil)
            _field("Design", row.design)
        with b:
            _field("Result as recorded", row.result)
            _field("Grade as recorded", row.grade)
            _field("Status as recorded", row.status)
            _field("Applicability", row.applicability)
            _field("Limitations and notes", row.limitations)
        st.markdown("**Source and provenance**")
        st.write(row.citation)
        if row.link.startswith("http"):
            st.link_button("Open the cited source", row.link, icon=":material/open_in_new:")
        else:
            st.caption(row.link)
        st.caption(f"Repository file: {row.source_file}; record: {row.source_id}"
                   + (f"; location in the source: {row.source_location}" if row.source_location else ""))
        st.caption(f"Provenance: {row.provenance or EC.NOT_RECORDED}")
        st.caption(f"Use in the platform: {row.pipeline_use or 'not stated'}")


def _records_tab(df: pd.DataFrame) -> None:
    shown = _filters(df)
    st.caption(f"{len(shown)} of {len(df)} records match.")
    if shown.empty:
        st.info("No record matches these filters. That is a statement about this repository, not about the option or habitat.")
        return
    st.dataframe(shown[list(_TABLE_COLUMNS)].rename(columns=_TABLE_COLUMNS), hide_index=True, width="stretch", height=320)
    ids = list(shown.record_id)
    labels = {r.record_id: f"{r.record_id} | {r.option or 'option not stated'} | {r.habitat_class}" for r in shown.itertuples()}
    if st.session_state.get("ev_pick") not in ids:
        st.session_state.pop("ev_pick", None)
    pick = st.selectbox("Inspect a record", ids, format_func=labels.get, key="ev_pick", index=0)
    _detail(shown[shown.record_id == pick].iloc[0])


def _gap_style(row: pd.Series) -> list:
    flag = row["Study records"] == 0
    return ["background-color: rgba(224,168,58,.16); color: #E0A83A;" if flag else "" for _ in row]


def _gaps_tab(df: pd.DataFrame) -> None:
    st.markdown("For one habitat class at a time: the number of AI-extracted study records for each option and the verdict the pipeline "
                "reads (a missing verdict means the table has no row). **A count of 0 means the repository holds no record; it does not "
                "mean the option is ineffective or unsuitable.**")
    gm = EC.gap_matrix(df)
    classes = list(EC.HABITAT_CLASSES[:-1])
    if st.session_state.get("ev_gap_class") not in classes:
        st.session_state["ev_gap_class"] = classes[0]
    cls = st.segmented_control("Habitat class", classes, key="ev_gap_class", required=True)
    view = gm[gm.habitat_class == cls]
    table = pd.DataFrame({"Study records": view.study_records.astype(int), "Option": view.option,
                          "Pipeline verdict": view.pipeline_verdicts.replace({"no pipeline verdict row": "no verdict row"})})
    st.dataframe(table.style.apply(_gap_style, axis=1), hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3,
                 column_config={"Study records": st.column_config.NumberColumn(width="small")})
    st.caption(f"{int((view.study_records == 0).sum())} of {len(view)} options have no study record in the {cls} class (highlighted).")
    verdicts = sorted(set(df[df.kind == EC.KIND_VERDICT].result.str.extract(r"verdict: ([^()]+)")[0].str.strip()))
    other = int(((df.kind == EC.KIND_STUDY) & (df.habitat_class == "other") & (~df.option_code.isin(EC.STUDY_OPTIONS_EXCLUDED))).sum())
    st.caption("Source: data/knowledge/literature_effects.csv (records) and data/knowledge/evidence_verdicts.csv (verdicts). Counts are numbers of rows "
               "whatever their grade or design, so they do not measure the strength of evidence. Verdict values present in the table: "
               + ", ".join(verdicts) + ". 'No clear difference' is the rule's label for one or two single studies (or none that qualify), not a measured null "
               f"effect. {other} study record(s) concern habitats that are not class-specific and appear under Habitat class 'other' in the records tab, not here.")
    rocky = df[(df.kind == EC.KIND_VERDICT) & (df.habitat_class == "rocky/hard") & (~df.result.str.contains("verdict: no evidence"))]
    st.markdown("**Applications the repository cannot support yet**")
    st.markdown("- Rocky shores (ESI 1A and 8A): the verdict table has " + (f"{len(rocky)} row(s) with content for rocky/hard ("
                + "; ".join(f"{r.option}: {r.result.split(' (')[0]}" for r in rocky.itertuples()) + "), none of them a demonstrated benefit"
                if len(rocky) else "no rocky/hard row with content") + ".\n"
                "- Mangroves: oiling-damage evidence comes from one spill; cleanup options have screening metadata only.\n"
                "- Any option shown with a count of 0 above for a habitat class.")


def _context_tab(df: pd.DataFrame) -> None:
    choices = EC.esi_choices()
    codes = [c for c, _ in choices]
    names = dict(choices)
    default = _default_esi()
    if "ev_ctx_esi" not in st.session_state or st.session_state["ev_ctx_esi"] not in codes:
        st.session_state["ev_ctx_esi"] = default if default in codes else codes[0]
    esi = st.selectbox("Shoreline type (ESI)", codes, key="ev_ctx_esi", format_func=lambda c: f"{c} - {names[c]}")
    ctx = EC.pipeline_context(esi)
    if "error" in ctx:
        st.warning(f"The decision pipeline could not run for this shoreline type ({ctx['error']}).")
        return
    st.caption(f"Pipeline report for default inputs: {ctx['inputs']}. This is a screening view, not a site assessment.")
    st.markdown(f"**Decision outcome:** {ctx['decision_outcome_label']}")
    h = hab.get(esi)
    hclass = h.habitat_class if h else "other"
    gm = EC.gap_matrix(df)
    rows = []
    for o in ctx["options"]:
        n = gm[(gm.option_code == o["option_code"]) & (gm.habitat_class == hclass)]
        rows.append({"Option": o["option"], "Pipeline category": o["category_label"],
                     "NOAA rating": (f"{o['rating']} (Proposed)" if o["rating"] and o["rating_status"] else o["rating"] or "none in the repository table"),
                     f"Study records ({hclass})": (int(n.study_records.iloc[0]) if len(n) else 0) if hclass != "other" else "n/a (no habitat class)", "Evidence state": o["evidence_state"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=35 * (len(rows) + 1) + 3)
    st.caption("Categories and evidence states are copied from run_decision(). Eligibility reflects habitat-impact screening, not "
               "demonstrated remediation effectiveness. The NOAA ratings are AI-transcribed and Proposed. The record count is the number of "
               "AI-extracted study records for the option in this habitat class (0 = none in the repository; it measures neither strength nor effect).")
    for text in ctx["abstentions"]:
        st.caption(f"Pipeline abstention: {text}")


def render_evidence() -> None:
    C.section_header("Evidence explorer", kicker="Traceable evidence", anchor="evidence", description=INTRO,
                     meta="Sources: data/knowledge tables")
    try:
        df = EC.load_catalog()
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        st.error(f"The evidence tables could not be read ({type(exc).__name__}: {exc}). Nothing is shown rather than a partial catalogue.")
        return
    st.warning(CAVEAT)
    counts = df.kind.value_counts()
    st.markdown("  \n".join(f"- **{int(counts.get(k, 0))}** {k}" for k in EC.KINDS))
    t1, t2, t3 = st.tabs(["Evidence records", "Gaps and unsupported applications", "Relation to pipeline decisions"])
    with t1:
        _records_tab(df)
    with t2:
        _gaps_tab(df)
    with t3:
        _context_tab(df)
