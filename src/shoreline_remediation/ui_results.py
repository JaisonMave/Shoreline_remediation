"""Assessment results view (V5.4 plot-first). Presentation only.

Reading order of ONE DecisionReport: scenario line (with the report download), finding (one sentence and its main limitation),
primary visual (treatment-effect plot, historical visible-oil curve, or the screening table), response options, and, in the
collapsed Methods and sources area drawn by site_view, citations, flags, reference values, the ranking method and the links to
Evidence and Models.

Everything about screening, categories, flags, abstentions and recommendations is read from the report that
decision_pipeline.run_decision() returned (through ui_pipeline) and from ui_decision_board.board_model(). Treatment contrasts come
from comparison.py, which reads the report and cannot change it. One cell's observed rate and leave-one-basin-out prediction
come from the site-table row that site_view passes in. Streamlit-free helpers (`top_card`, `this_site`, `breadcrumb_items`,
`finding_for`, `option_rows`) are testable without a browser. This module never calls the decision engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from src.shoreline_remediation import comparison as K, model_validation_data as MV, ui_components as C, ui_decision_board as B
from src.shoreline_remediation import ui_evidence as E, ui_plots, ui_theme as T
from src.shoreline_remediation.decision_pipeline import CATEGORY_LABELS

EDGE_MODEL = "edge_loss_v1"
PAH_MODEL = "pah_decline_v1"
ABSTENTION_OUTCOMES = ("insufficient_evidence", "out_of_scope", "unsupported_habitat")
# outcome key (DecisionReport.decision_outcome) -> (visual tone, status pill). The wording of the outcome itself is the report's
# decision_outcome_label; the pill only says what kind of outcome it is. Abstention is a valid outcome, so it gets the same weight.
OUTCOME_PILL = {
    "intervention_recommended": ("recommended", ""),
    "conditional_only": ("conditional", ""),
    "natural_recovery_monitoring": ("reference", ""),
    "insufficient_evidence": ("abstain", "Abstention: evidence is insufficient (a valid outcome, not an error)"),
    "out_of_scope": ("abstain", "Abstention: outside the scope of this tool (a valid outcome, not an error)"),
    "unsupported_habitat": ("abstain", "Abstention: unsupported habitat (a valid outcome, not an error)"),
}
FLAG_SOURCE = {"abstentions": "Abstention", "advisories": "Advisory", "site scope": "Site scope"}
DEPLOYED_LABEL = "Deployed estimate (edge_loss_v1, fitted on all cells)"
OBSERVED_LABEL = "Historical observation, 2010 to 2015 (aerial images)"
LOBO_LABEL = "Held-out test prediction (basin of this cell left out of the fit)"
ONE_CELL_NOTE = ("The deployed estimate and the held-out prediction come from different fits and are not expected to match. One "
                 "cell's difference from its observation is not the model's accuracy")
NOT_ASSESSED_TEXT = "No options are listed because the pipeline made no assessment for this input."
PAH_STATUS = ("Soil PAH-sum decline ({model}): registry state {state}, whole-station hold-out summary on the Models page. No per-station "
              "hold-out predictions are stored in this repository, so no predicted-against-observed chart is shown for it.")
SAND_LIMIT = ("Historical response: visible oil under the cleanup as it was carried out in 2010 to 2013. It is not natural recovery "
              "and not a comparison of treatments.")
REFERENCE_REASON = "Reference option: every method is compared with it."
GROUP_LABELS = C.GROUP_LABELS


# ---------------------------------------------------------------------------------------------------------------
# Streamlit-free helpers

def top_card(model: B.BoardModel):
    """The first board card (in decision_pipeline.CATEGORY_ORDER) that lists at least one option."""
    return next((c for c in model.cards if c.options), None)


def breadcrumb_items(rec: dict) -> list:
    """Place | shoreline type and ESI | oil category | oiling class with its source. Read from the run record's `crumb`; a record
    without one (older session) falls back to the single `where` string."""
    crumb = rec.get("crumb") or {}
    items = [crumb.get(k) for k in ("place", "shoreline", "oil", "oiling")]
    items = [str(i) for i in items if i]
    return items or [str(rec.get("where") or "run record not available")]


@dataclass
class ThisSite:
    cell: str
    deployed: float
    deployed_quantity: str
    observed: float
    lobo: float
    abs_diff: float
    pct: float | None        # only where the observation is not 0


def deployed_reference(report) -> dict | None:
    """The report's natural-recovery reference row that comes from the deployed edge-loss model, or None."""
    for r in E.reference_rows(report):
        if str(E.field(r, "model_id", "")) == EDGE_MODEL and str(E.field(r, "quantity", "")).startswith("edge-loss rate") \
                and E.finite(E.field(r, "value")):
            return r
    return None


def this_site(report, row: dict | None, habitat: str) -> ThisSite | None:
    """The site-model strip for ONE in-scope salt-marsh cell, or None. Needs the cell's own row of the site table (observed_rate and
    lobo_pred both present) and the deployed-model reference value in the report. A typed site, a habitat-level run and every
    non-marsh habitat have no such row, so no strip is made for them."""
    if habitat != "marsh" or not row or row.get("status") != "in_scope":
        return None
    obs, lobo = row.get("observed_rate"), row.get("lobo_pred")
    ref = deployed_reference(report)
    if ref is None or not (E.finite(obs) and E.finite(lobo)):
        return None
    diff = abs(float(lobo) - float(obs))
    return ThisSite(str(row.get("cell", "")), float(ref["value"]), str(ref["quantity"]), float(obs), float(lobo), diff,
                    None if float(obs) == 0.0 else diff / abs(float(obs)) * 100.0)


def models_used(report) -> set:
    return {str(E.field(r, "model_id", "") or "") for r in E.reference_rows(report)}


def run_oiling(rec: dict) -> str | None:
    """SCAT oiling class of the run, read from the run record's spec (site spec: the site item; scenario spec: its oiling)."""
    spec = rec.get("spec") or ()
    if spec and spec[0] == "site":
        return dict(spec[1]).get("max_oiling")
    return spec[2] if len(spec) > 2 else None


def comparisons_for(report, rec: dict) -> dict:
    """{target key: comparison.Comparison} for a salt-marsh run (empty otherwise). The applicability note says whose plots these
    are when the run is not the Bay Jimmy record itself."""
    if rec.get("habitat") != "marsh" or report is None or str(E.field(report, "scope_tier", "")) in E.NO_ASSESSMENT_TIERS:
        return {}
    return K.assessment_comparisons(report, "salt_marsh", run_oiling(rec))


def beach_reference(report) -> dict | None:
    """The report's visible-oil persistence reference (sand beach, ESI 3A), or None."""
    return next((r for r in E.reference_rows(report) if E.field(r, "curves_by_group")), None)


def condition_phrase(line: str) -> str:
    """'Crews walk on the marsh ... -> harms [unknown (ask user)]' -> 'Harm reported if: crews walk ... (not established here)'."""
    body, _, status = str(line).rpartition("[")
    text, _, effect = body.rpartition("->")
    if not text:
        return str(line)
    status = status.rstrip("] ").lower()
    known = "not established here" if status.startswith("unknown") else status.replace("by input", "by the entered")
    lead = {"harms": "Harm reported if", "no benefit": "No benefit if", "helps": "Helps if", "may help": "May help if",
            "less harm": "Less harm if"}.get(effect.strip().lower(), effect.strip().capitalize() + " if")
    text = text.strip()
    return f"{lead}: {text[:1].lower() + text[1:]} ({known})"


def _basis_text(row: dict, view) -> str:
    source = str(row.get("evidence_source") or "")
    if source == "scenario_composer":
        text = "Field plots at Bay Jimmy, through the experimental scenario composer"
    elif source == "evidence_verdicts":
        text = f"Literature verdict: {row.get('evidence_verdict') or 'not stated'}"
    else:
        text = "Screening rule only"
    rating = row.get("habitat_rating")
    if isinstance(rating, dict) and str(rating.get("rating") or "-").strip() not in ("-", ""):
        text += f"; NOAA habitat rating {rating['rating']} (unverified transcription)"
    if view.grade == "ai_proposed":
        text += "; AI-proposed, not reviewed by a person"
    return text


def _main_reason(row: dict, category: str, views: list) -> str:
    if category == "excluded":
        text = (K._exclusion_text(row) or "Excluded by screening").replace(" (pipeline applicability rule, not a table row)", "")
        text = text[:1].upper() + text[1:]
        harm = [str(h.get("detail", h)) if isinstance(h, dict) else str(h) for h in row.get("harm_flags") or []]
        return C.humanise(text + (" Harm flag: " + harm[0] if harm else ""), views)
    if category == "natural_recovery_monitoring":
        return REFERENCE_REASON
    if category == "recommended":
        cond = [condition_phrase(c) for c in row.get("conditions") or []]
        return cond[0] if cond else "No condition listed by the pipeline."
    reason = str(row.get("recommendation_category_reason") or "")
    harm = [str(h.get("detail", h)) if isinstance(h, dict) else str(h) for h in row.get("harm_flags") or []]
    if "(see harm_flags)" in reason:            # name the flag instead of pointing at an internal field
        reason = reason.replace(" (see harm_flags)", "") + (". Harm flag: " + harm[0] if harm else "")
    return C.humanise(reason[:1].upper() + reason[1:], views) if reason else "Not stated."


def option_rows(report, comp: K.Comparison | None = None) -> list:
    """One record per option in the report, in the pipeline's category order: method, screening status (the report's category),
    evidence basis, the main condition or exclusion reason and, when a comparison is given, its value or 'No comparative data'.
    Nothing is reclassified here."""
    m = B.board_model(report)
    views = [E.option_view(r) for r in E.field(report, "options", []) or []]
    out = []
    for card in m.cards:
        for name in card.options:
            row = card.rows.get(name)
            rec = {"option": name, "method": E.plain_name(name), "category": card.category, "status": card.label,
                   "basis": "No row in the report", "reason": "", "comparison": None, "rank": None}
            if row is not None:
                rec["basis"] = "Reference" if card.is_natural else _basis_text(row, E.option_view(row))
                rec["reason"] = _main_reason(row, card.category, views)
            if comp is not None:
                rec["comparison"] = K.cell_text(comp, name)
                r = comp.row_for(name)
                rec["rank"] = r.rank if r else None
            out.append(rec)
    return out


def _site_limit(rec: dict) -> str:
    flags = rec.get("flags")
    for name in ("out_of_scope", "extrapolation"):
        items = [str(x) for x in (getattr(flags, name, None) or [])]
        if items:
            return ("Extrapolation: " if name == "extrapolation" else "") + items[0]
    return ""


def sand_point(ref: dict, group: str | None = None, day: int = 365) -> dict | None:
    """One time point of the packaged visible-oil curve for a first-oiling group (the report's default group unless given)."""
    curves = ref.get("curves_by_group") or {}
    group = group if group in curves else ref.get("group") if ref.get("group") in curves else next(iter(curves), None)
    horizons = list(ref.get("horizons_days") or [90, 180, 365, 730])
    if group is None or day not in horizons:
        return None
    c, i = curves[group], horizons.index(day)
    return {"group": group, "day": day, "median": float(c["median"][i]), "lo": float(c["lo90"][i]), "hi": float(c["hi90"][i]),
            "n": c.get("n_segments")}


def finding_for(report, m: B.BoardModel, comps: dict, rec: dict, sand_group: str | None = None) -> tuple:
    """(sentence, limitation) of the Finding block. The sentence states one quantity with its comparator and time where a
    comparable estimate exists, otherwise what the screening returned. The limitation is the single most important applicability
    or harm qualification; the other flags are listed once, in Methods and sources."""
    if m.refused:
        return m.outcome_label + ".", m.scope_message
    site_limit = _site_limit(rec)
    abst = [f.text for f in m.flags if f.source == "abstentions"]
    veg = comps.get(K.VEG_YEAR2.key)
    if veg is not None and K.finding(veg):
        return K.finding(veg), site_limit or K.design_limit(veg)
    if veg is not None and not veg.applicable:
        return (f"{K.NO_DATA} for this scenario: the treatment plots at Bay Jimmy were all heavily oiled salt marsh.",
                site_limit or veg.applicability)
    ref = beach_reference(report)
    pt = sand_point(ref, sand_group) if ref else None
    if pt:
        n = f"; {pt['n']} Deepwater Horizon segments" if pt.get("n") else ""
        return (f"Visible oil was still recorded on {pt['median']:.0%} of fine-to-medium sand beach segments {pt['day']} days after the "
                f"first oiled survey, for segments first seen with {GROUP_LABELS.get(pt['group'], pt['group']).lower()} "
                f"(90% interval {pt['lo']:.0%} to {pt['hi']:.0%}{n}).", SAND_LIMIT)
    counts = {c.category: len(c.options) for c in m.cards}
    allowed = sum(counts.get(k, 0) for k in ("recommended", "conditional", "no_demonstrated_benefit", "insufficient_evidence"))
    sentence = (f"No treatment has a comparable effect estimate for this shoreline type: screening allows {allowed} of "
                f"{allowed + counts.get('excluded', 0)} methods, {counts.get('conditional', 0)} of them conditionally, and excludes "
                f"{counts.get('excluded', 0)}.")
    return sentence, site_limit or (abst[0] if abst else m.scope_message)


# ---------------------------------------------------------------------------------------------------------------
# Drawing

def _scenario_row(report, rec: dict, key: str, comps: dict) -> None:
    left, right = st.columns([4, 1.4], vertical_alignment="center")
    crumbs = "".join(f"<span>{escape(i)}</span>" for i in breadcrumb_items(rec))
    left.markdown(f'<div class="sr-rtitle">Remediation assessment</div><div class="sr-crumbs">{crumbs}</div>', unsafe_allow_html=True)
    if report is not None:
        from src.shoreline_remediation import ui_report
        view = E.report_view(report)
        right.download_button("Download report (HTML)", key=f"dl_{key}", icon=":material/download:", width="stretch", mime="text/html",
                              data=ui_report.build_html(view, title=str(rec.get("where", "")), habitat=key, comparisons=list(comps.values())),
                              file_name=f"shoreline_report_{key}.html")


def _finding_block(report, m: B.BoardModel, comps: dict, rec: dict, key: str) -> None:
    tone, pill = OUTCOME_PILL.get(m.outcome, ("reference", ""))
    sentence, limit = finding_for(report, m, comps, rec, st.session_state.get(f"sand_group_{key}"))
    with st.container(key=f"sr_outcome_{tone}"):
        st.markdown(f'<div class="sr-oc-kicker">Finding</div><div class="sr-find">{escape(sentence)}</div>'
                    + (f'<div class="sr-limit"><b>Main limitation.</b> {escape(limit)}</div>' if limit else ""), unsafe_allow_html=True)
        st.markdown(f'<div class="sr-oc-title"><span class="sr-oc-lead">Screening outcome:</span> {escape(m.outcome_label)}</div>'
                    + (f'<div class="sr-oc-pill">{escape(pill)}</div>' if pill else ""), unsafe_allow_html=True)
        if m.refused:
            st.caption(NOT_ASSESSED_TEXT)


def _site_strip(ts: ThisSite, key: str, report) -> None:
    def cell(label: str, value: float) -> str:
        return f"<div><dt>{escape(label)}</dt><dd>{value:.2f} m/yr</dd></div>"

    st.markdown(f'<div class="sr-strip"><div class="sr-strip-title">Marsh-edge loss at cell {escape(ts.cell)} (natural recovery, '
                f'positive = land lost)</div><dl>{cell(DEPLOYED_LABEL, ts.deployed)}{cell(OBSERVED_LABEL, ts.observed)}'
                f"{cell(LOBO_LABEL, ts.lobo)}</dl></div>", unsafe_allow_html=True)
    res = MV.edge_loss_scatter()
    overall = (f": over all cells the held-out mean absolute error is {res['MAE']:.3f} m/yr (n = {res['n']:,}, leave-one-basin-out)."
               if res.get("available") else ".")
    a, b = st.columns([4, 1.6], vertical_alignment="center")
    a.caption(ONE_CELL_NOTE + overall)
    if B.referenced_model(report):
        b.button("Held-out test on Models", key=f"how_{key}", icon=":material/query_stats:", on_click=B.open_model,
                 args=(B.referenced_model(report),), width="stretch",
                 help="Opens Models on the full predicted-against-observed scatter of the edge-loss model.")


def _effect_visual(comps: dict, key: str) -> K.Comparison | None:
    """Treatment-effect plot for the chosen target. Returns the comparison shown (the options table quotes the same one)."""
    drawable = [k for k, c in comps.items() if K.plot_records(c)]
    if not drawable:
        return comps.get(K.VEG_YEAR2.key)
    choice = drawable[0]
    if len(drawable) > 1:
        choice = st.segmented_control("Outcome", drawable, default=drawable[0], required=True, key=f"cmp_target_{key}",
                                      format_func=lambda k: K.TARGET_LABELS[k], label_visibility="collapsed")
    comp = comps[choice]
    st.markdown(f'<div class="sr-card-title">{escape(comp.title)}</div><div class="sr-muted">Bay Jimmy field plots, heavily oiled salt '
                f'marsh; difference from {escape(comp.target.comparator)} ({escape(comp.target.unit)})</div>', unsafe_allow_html=True)
    chart = ui_plots.effect_chart(comp, C.text_colour(), T.BRAND["dark" if C.is_dark() else "light"])
    rec = K.plot_records(comp)
    st.altair_chart(chart, theme="streamlit", width="stretch")
    st.caption(" ".join(f"{r['label']}: {r['value_text']} {comp.target.unit_short}." for r in rec) + " " + K.source_caption(comp)
               + (" " + comp.order_note if comp.order_note else ""))
    return comp


def _sand_visual(ref: dict, key: str) -> None:
    groups = list(ref["curves_by_group"])
    default = ref.get("group") if ref.get("group") in groups else groups[0]
    st.markdown('<div class="sr-card-title">Historical response: visible oil on fine-to-medium sand beaches</div>'
                '<div class="sr-muted">Share of ever-oiled Deepwater Horizon survey segments (ESI 3A) still recorded with visible oil, '
                'by days after the first oiled survey</div>', unsafe_allow_html=True)
    group = st.segmented_control("First oiling category seen at the segment", groups, default=default, required=True, key=f"sand_group_{key}",
                                 format_func=lambda g: GROUP_LABELS.get(g, g),
                                 help="The pipeline does not know which category was seen first, so you choose it.")
    c = ref["curves_by_group"][group]
    horizons = ref.get("horizons_days") or [90, 180, 365, 730]
    st.altair_chart(ui_plots.persistence_chart(horizons, c["median"], c["lo90"], c["hi90"], C.text_colour(),
                                               T.BRAND["dark" if C.is_dark() else "light"]), theme="streamlit", width="stretch")
    pts = "; ".join(f"day {d}: {m_:.0%} ({a:.0%} to {b:.0%})" for d, m_, a, b in zip(horizons, c["median"], c["lo90"], c["hi90"]))
    st.caption(f"{pts}. Dot: share still oiled. Bar: 90% interval from 200 refits resampling whole segments. n = {c.get('n_segments', '?')} "
               "segments in this group; a segment counts as cleared at its first survey with no oil observed. Model "
               "beach_sand_persistence_v1 (experimental: it did not beat this baseline curve on held-out states, so only the baseline "
               "is shown).")


def _options_table(rows: list, comp: K.Comparison | None) -> None:
    has_cmp = comp is not None
    head = "<th>Method</th><th>Screening status</th><th>Evidence basis</th><th>Main condition or exclusion reason</th>"
    cmp_head = f"{comp.target.title}, difference from {comp.target.comparator}" if has_cmp else ""
    if has_cmp:
        head += f"<th>{escape(cmp_head)}</th>"
    body = []
    for r in rows:
        rank = f' <span class="sr-muted">(provisional rank {r["rank"]})</span>' if r.get("rank") else ""
        cells = (f'<td data-label="Method"><b>{escape(r["method"])}</b></td>'
                 f'<td data-label="Screening status">{C.status_label(r["category"], r["status"])}</td>'
                 f'<td data-label="Evidence basis">{escape(r["basis"])}</td>'
                 f'<td data-label="Condition or reason">{escape(r["reason"])}</td>')
        if has_cmp:
            cells += f'<td data-label="{escape(comp.target.title)}">{escape(str(r["comparison"]))}{rank}</td>'
        body.append(f"<tr>{cells}</tr>")
    st.markdown(f'<table class="sr-opttable"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>', unsafe_allow_html=True)


def render_results(report, rec: dict, ctx: dict, site_row: dict | None = None) -> None:
    """Draw the results view for `report` (a DecisionReport) of the run record `rec`. `ctx` = {"key", "habitat", "esi"}.
    `site_row` is the run's site-table row for a known marsh cell (None for typed, habitat-level and non-marsh runs)."""
    key = ctx["key"]
    comps = comparisons_for(report, rec) if report is not None else {}
    _scenario_row(report, rec, key, comps)
    if report is None:
        st.warning("The decision pipeline did not return a report, so there are no results to show.")
        return
    m = B.board_model(report, rec.get("flags"))
    _finding_block(report, m, comps, rec, key)
    if m.refused:
        return
    comp, ref = None, beach_reference(report)
    ts = this_site(report, site_row, key)
    if comps or ref or ts:
        with st.container(key="sr_visual"):
            if comps:
                comp = _effect_visual(comps, key)
            elif ref:
                _sand_visual(ref, key)
            if ts is not None:
                _site_strip(ts, key, report)
    primary = comp is None and ref is None
    st.markdown(f'<div class="sr-sec">{"Screening result" if primary else "Response options"}</div>', unsafe_allow_html=True)
    _options_table(option_rows(report, comp), comp)
    st.caption("Screening status is the decision pipeline's category. It is separate from any performance order: a large estimate "
               "does not change a status."
               + (" Treatment options have no comparable effect estimate for this shoreline type." if primary or comp is None else ""))


# ---------------------------------------------------------------------------------------------------------------
# Methods and sources (drawn by site_view inside its collapsed technical area)

def _reference_frame(rows: list) -> pd.DataFrame:
    out = []
    for r in rows:
        v, lo, hi = E.field(r, "value"), E.field(r, "lo90"), E.field(r, "hi90")
        unit = str(E.field(r, "unit", ""))
        est = (f"{v:.2f} {unit}" + (f" (90% interval {lo:.2f} to {hi:.2f})" if E.finite(lo) and E.finite(hi) else "")) if E.finite(v) \
            else f"Not available: {E.field(r, 'reason', E.field(r, 'status', 'no value'))}"
        out.append({"Quantity": str(E.field(r, "quantity", "")), "Estimate": est, "Model": str(E.field(r, "model_id", "") or "none"),
                    "Registry state": str(E.field(r, "state", "") or "none"), "Scope": str(E.field(r, "scope", "") or "not stated"),
                    "Note": str(E.field(r, "note", "") or "")})
    return pd.DataFrame(out)


def render_methods(report, rec: dict, ctx: dict, site_row: dict | None = None) -> None:
    """Citations, every flag, the comparison detail (including historical contrasts of methods that are not ranked), the ranking
    method, natural-recovery reference values, and the links to Evidence and Models. Read-only."""
    key = ctx["key"]
    m = B.board_model(report, rec.get("flags"))
    a, b = st.columns(2)
    a.button("Open the evidence for this habitat", key=f"whyboard_{key}", icon=":material/menu_book:", on_click=B.open_evidence,
             args=(ctx["habitat"], ctx.get("esi"), ()), width="stretch",
             help="Opens Evidence filtered to this habitat class and ESI code.")
    model_id = B.referenced_model(report)
    if model_id and this_site(report, site_row, key) is None:
        b.button("Open the model validation", key=f"how_{key}", icon=":material/query_stats:", on_click=B.open_model, args=(model_id,),
                 width="stretch", help=f"Opens Models on {model_id}, the model behind the reference numbers.")
    elif not model_id:
        b.caption(B.NO_FORECAST_TEXT)
    st.markdown(f"**Scope of the tool for this input:** {T.grade_html(T.TIER_TO_GRADE.get(m.scope_tier, 'rules_literature'), T.TIER_TEXT.get(m.scope_tier, m.scope_tier))} "
                f"{escape(m.scope_message)}", unsafe_allow_html=True)
    st.markdown(f"**Flags ({len(m.flags)})**")
    if not m.flags:
        st.caption("The report lists no abstentions, advisories or site-scope flags for this run.")
    for f in m.flags:
        src = FLAG_SOURCE.get(f.source, f.source)
        prefix = "" if f.text.lower().startswith(src.lower()) else f"**{src}:** "
        st.markdown(f"- {prefix}{f.text}" + (f" (`{f.kind}`)" if f.kind else ""))
    comps = comparisons_for(report, rec)
    if comps:
        st.markdown("**Field comparisons in detail**")
        frame = pd.DataFrame([{"Target": K.TARGET_LABELS[k], **r} for k, c in comps.items() for r in K.table_records(c)])
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Every contrast the platform holds, including methods that are not in the order. A historical value for an excluded "
                   "or conditional method describes what happened at Bay Jimmy; it does not make the method eligible. Intervals are "
                   "90% Welch t intervals (sampling uncertainty of a difference of group means). Vegetation contrasts are derived from "
                   "published group means (Zengel et al. 2015, S1 Table); erosion contrasts are computed from plot-level rates (Zengel "
                   "et al. 2022). The two studies share plots, so they are not independent.")
        st.markdown("**How the order is made**")
        st.markdown("- Only estimates with the same outcome, unit, time and comparator are compared; no outcome is converted into "
                    "another and there is no combined score across vegetation, erosion and oil.\n"
                    "- Excluded methods are never ranked. Conditional methods are ranked only when the scenario shows their conditions "
                    "are met; unknown is not met. Planting after mechanical removal needs mechanical removal to be allowed.\n"
                    "- Eligible methods are sorted by point estimate; exact ties share a rank; one eligible method gets no rank.\n"
                    "- No probability that one method beats another is reported: no meaningful effect threshold has a scientific basis here.")
        c = K.NEAREST_CANDIDATE
        st.markdown(f"**Model estimates in the order:** none. The nearest candidate is `{c.model_id}` ({c.name}); it is not admitted.")
        st.dataframe(pd.DataFrame([{"Check": x, "Passed": "Yes" if ok else "No", "Evidence": why} for x, ok, why in c.checks]),
                     hide_index=True, width="stretch")
        st.caption("Needed for admission: " + c.missing)
    refs = E.reference_rows(report)
    if refs:
        st.markdown("**Natural-recovery reference values**")
        st.dataframe(_reference_frame(refs), hide_index=True, width="stretch")
        st.caption("Intervals are 90% ranges from each model's own uncertainty method; the registry state is not a coverage guarantee. "
                   "Positive edge loss = land lost.")
    if PAH_MODEL in models_used(report):
        state = next((str(E.field(r, "state", "not stated")) for r in refs if str(E.field(r, "model_id", "")) == PAH_MODEL), "not stated")
        st.caption(PAH_STATUS.format(model=PAH_MODEL, state=state))
    st.caption("Categories come from the decision pipeline's transparent rules. Evidence grades are not probabilities. Screening is "
               "not demonstrated effectiveness.")
