"""Assessment results view (V5.4 Stage 3). Presentation only.

One coherent view of ONE DecisionReport, in this order: title row (breadcrumb and report download), primary outcome card beside the
key-flags card, alternatives grouped by category, expected outcome beside the validation card, supporting evidence.

Everything shown is read from the report that decision_pipeline.run_decision() returned (through ui_pipeline) and from
ui_decision_board.board_model(): no class, category, order, state or number is computed here. The only values that come from
elsewhere are (a) the hold-out scatter, read from model_validation_data.edge_loss_scatter() (the same reader as the Models page),
and (b) one cell's own observed rate and leave-one-basin-out prediction, read from a site-table row that site_view passes in.
Streamlit-free helpers (`top_card`, `this_site`, `breadcrumb_items`) are testable without a browser. This module never calls the
decision engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

import streamlit as st

from src.shoreline_remediation import model_validation_data as MV, ui_components as C, ui_decision_board as B, ui_evidence as E
from src.shoreline_remediation import ui_models, ui_theme as T
from src.shoreline_remediation.decision_pipeline import CAT_NATURAL, CATEGORY_LABELS, CATEGORY_ORDER

FLAG_CAP = 3
EDGE_MODEL = "edge_loss_v1"
PAH_MODEL = "pah_decline_v1"
ABSTENTION_OUTCOMES = ("insufficient_evidence", "out_of_scope", "unsupported_habitat")
# outcome key (DecisionReport.decision_outcome) -> (visual tone, status pill). The wording of the outcome itself is the report's
# decision_outcome_label; the pill only says what kind of outcome it is. Abstention is a valid outcome, so it gets the same weight.
OUTCOME_PILL = {
    "intervention_recommended": ("recommended", ""),
    "conditional_only": ("conditional", "Conditional: no outright recommendation"),
    "natural_recovery_monitoring": ("reference", "Natural recovery stays the reference"),
    "insufficient_evidence": ("abstain", "Abstention: evidence is insufficient (a valid outcome, not an error)"),
    "out_of_scope": ("abstain", "Abstention: outside the scope of this tool (a valid outcome, not an error)"),
    "unsupported_habitat": ("abstain", "Abstention: unsupported habitat (a valid outcome, not an error)"),
}
GROUP_NOTE = {
    "conditional": "Allowed. Field evidence of benefit exists, but conditions apply or the transfer to this input is untested.",
    "natural_recovery_monitoring": "The reference every option is compared with. It is a reference, not a recommendation.",
    "no_demonstrated_benefit": "Evidence exists and shows no clear difference from natural recovery. This is not a finding of harm.",
    "insufficient_evidence": "No eligible evidence compares these options with natural recovery. This is not a finding of no benefit.",
    "excluded": "Removed by a hard constraint (screening rule or habitat rating) or by evidence of harm.",
    "recommended": "Evidence of benefit over natural recovery, inside the scope where that evidence was gathered.",
}
FLAGS_EMPTY = "The report lists no abstentions, advisories or site-scope flags for this run."
FLAG_SOURCE = {"abstentions": "Abstention", "advisories": "Advisory", "site scope": "Site scope"}
DEPLOYED_LABEL = "Deployed model reference (edge_loss_v1, fitted on all cells; value from the report)"
OBSERVED_LABEL = "Observed at this cell, 2010 to 2015 (aerial images; site table)"
LOBO_LABEL = "Leave-one-basin-out prediction for this cell (its basin held out; site table)"
DIFF_LABEL = "Absolute difference: observed minus leave-one-basin-out prediction"
ONE_CELL_NOTE = ("This is one cell's individual error. It is not the model's accuracy: the overall validation metric is the mean "
                 "absolute error over all cells (shown beside this card) and does not change with this cell.")
EXPECTED_TITLE = "Expected outcome: natural-recovery reference"
NOT_ASSESSED_TEXT = "No expected outcome is shown because the pipeline made no assessment for this input."
PAH_STATUS = ("Soil PAH-sum decline ({model}): registry state {state}, whole-station hold-out summary on the Models page. No per-station "
              "hold-out predictions are stored in this repository, so no predicted-against-observed chart is shown for it.")


# ---------------------------------------------------------------------------------------------------------------
# Streamlit-free helpers

def top_card(model: B.BoardModel):
    """The first board card (in decision_pipeline.CATEGORY_ORDER) that lists at least one option. The natural-recovery card counts
    as a group like any other: when nothing outranks it, it is the top applicable category and is called the reference."""
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
    """The 'this site' block for ONE in-scope salt-marsh cell, or None. Needs the cell's own row of the site table (observed_rate and
    lobo_pred both present) and the deployed-model reference value in the report. A typed site, a habitat-level run and every
    non-marsh habitat have no such row, so no block is made for them."""
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


# ---------------------------------------------------------------------------------------------------------------
# Drawing

def _title_row(report, rec: dict, key: str) -> None:
    left, right = st.columns([4, 1.4], vertical_alignment="center")
    crumbs = "".join(f"<span>{escape(i)}</span>" for i in breadcrumb_items(rec))
    left.markdown(f'<div class="sr-rtitle">Remediation assessment</div><div class="sr-crumbs">{crumbs}</div>', unsafe_allow_html=True)
    if report is not None:
        from src.shoreline_remediation import ui_report
        view = E.report_view(report)
        right.download_button("Download this report (HTML)", data=ui_report.build_html(view, title=str(rec.get("where", "")), habitat=key),
                              file_name=f"shoreline_report_{key}.html", mime="text/html", key=f"dl_{key}", icon=":material/download:",
                              width="stretch")


def _option_chips(name: str, row: dict | None) -> str:
    if row is None:
        return f'<span class="sr-alt-name">{escape(E.plain_name(name))}</span> <span class="sr-muted">(no row in the report)</span>'
    v = E.option_view(row)
    return f'<span class="sr-alt-name">{escape(v.name)}</span> {T.class_html(v.cls, with_name=False)} {T.grade_html(v.grade)}'


def _outcome_card(m: B.BoardModel) -> None:
    tone, pill = OUTCOME_PILL.get(m.outcome, ("reference", ""))
    card = None if m.refused else top_card(m)
    with st.container(key=f"sr_outcome_{tone}"):
        st.markdown(f'<div class="sr-oc-kicker">Decision outcome</div><div class="sr-oc-title">{escape(m.outcome_label)}</div>'
                    + (f'<div class="sr-oc-pill">{escape(pill)}</div>' if pill else ""), unsafe_allow_html=True)
        if m.refused:
            st.markdown(f"Scope of the tool for this input: {T.grade_html(T.TIER_TO_GRADE.get(m.scope_tier, 'out_of_scope'), T.TIER_TEXT.get(m.scope_tier, m.scope_tier))}",
                        unsafe_allow_html=True)
            st.write(m.scope_message)
            st.caption(B.NO_ASSESSMENT_TEXT)
            return
        if card is not None:
            st.markdown(C.status_label(card.category, card.label), unsafe_allow_html=True)
            if card.is_natural:
                st.caption("No intervention outranks natural recovery in this report, so the reference option is the top category. "
                           "It is the reference every intervention is compared with, not a recommendation.")
            for name in card.options:
                st.markdown(f'<div class="sr-oc-opt">{_option_chips(name, card.rows.get(name))}</div>', unsafe_allow_html=True)
                if not card.is_natural and card.rows.get(name):
                    for line in B.benefit_lines(card.rows[name]):
                        st.markdown(f"- {line}")
            convention = [card.rows[x] for x in card.options if (card.rows.get(x) or {}).get("rank_basis") == "display_convention"]
            if len(card.options) > 1 and convention:
                st.caption("The order within this group is a display convention, not a ranking. Order: "
                           + str(convention[0].get("rank_basis_text") or ""))
        st.markdown("Scope of the tool for this input: "
                    + T.grade_html(T.TIER_TO_GRADE.get(m.scope_tier, "rules_literature"), T.TIER_TEXT.get(m.scope_tier, m.scope_tier)),
                    unsafe_allow_html=True)
        if m.scope_message:
            st.caption(m.scope_message)


def _flags_card(m: B.BoardModel) -> None:
    with st.container(key="sr_flags"):
        st.markdown('<div class="sr-fl-title"><span aria-hidden="true">&#9888;</span> Key flags</div>', unsafe_allow_html=True)
        if not m.flags:
            st.caption(FLAGS_EMPTY)
            return

        def line(f: B.Flag) -> str:
            src = FLAG_SOURCE.get(f.source, f.source)
            prefix = "" if f.text.lower().startswith(src.lower()) else f"**{src}:** "
            return f"- {prefix}{f.text}" + (f" (`{f.kind}`)" if f.kind else "")

        for f in m.flags[:FLAG_CAP]:
            st.markdown(line(f))
        rest = m.flags[FLAG_CAP:]
        if rest:
            with st.expander(f"Show all {len(m.flags)} flags"):
                for f in rest:
                    st.markdown(line(f))


def _option_line(name: str, row: dict | None, category: str) -> None:
    st.markdown(f'<div class="sr-alt-opt">{_option_chips(name, row)}</div>', unsafe_allow_html=True)
    if row is None:
        return
    view = E.option_view(row)
    if category == "excluded":
        for x in row.get("exclusion_reasons") or []:
            st.caption("Excluded: " + C.humanise(str(x.get("detail", x)) if isinstance(x, dict) else str(x), [view]))
    elif row.get("recommendation_category_reason") and category in ("conditional", "no_demonstrated_benefit", "insufficient_evidence"):
        st.caption(C.humanise(str(row["recommendation_category_reason"]), [view]))


def _group(card: B.BoardCard, ctx: dict | None) -> None:
    n = len(card.options)
    st.markdown(C.status_label(card.category, card.label) + f" &nbsp;<span class='sr-muted'>{n} option{'s' if n != 1 else ''}</span>",
                unsafe_allow_html=True)
    st.caption(GROUP_NOTE.get(card.category, ""))
    convention = n > 1 and any((card.rows.get(x) or {}).get("rank_basis") == "display_convention" for x in card.options)
    if convention:
        st.caption("The order within this group is a display convention, not a ranking.")
    for name in card.options:
        _option_line(name, card.rows.get(name), card.category)
    if card.is_natural and card.monitoring:
        st.caption(f"Monitoring: {card.monitoring}")
    if ctx and card.options and not card.is_natural:
        st.button("Why? Open the evidence", key=f"why_{ctx['key']}_{card.category}", icon=":material/menu_book:", type="tertiary",
                  on_click=B.open_evidence, args=(ctx["habitat"], ctx.get("esi"), tuple(card.options)))


def _alternatives(m: B.BoardModel, top, ctx: dict | None) -> None:
    rest = [c for c in m.cards if c is not top and (c.options or c.is_natural)]
    if not rest:
        return
    st.markdown('<div class="sr-sec">Alternatives</div>', unsafe_allow_html=True)
    shown = [c for c in rest if c.category != "excluded"]
    for i in range(0, len(shown), 2):
        for col, card in zip(st.columns(2), shown[i:i + 2]):
            with col, st.container(border=True, key=f"sr_alt_{card.category}"):
                _group(card, ctx)
    for card in (c for c in rest if c.category == "excluded"):
        with st.expander(f"Excluded ({len(card.options)} options): reasons available", expanded=False):
            _group(card, ctx)


def _reference_table(rows: list) -> None:
    body = []
    for r in rows:
        q = escape(str(E.field(r, "quantity", "reference quantity")))
        v = E.field(r, "value")
        if E.finite(v):
            lo, hi, unit = E.field(r, "lo90"), E.field(r, "hi90"), str(E.field(r, "unit", ""))
            est = E.fmt_interval(v, lo, hi, 2, unit) if E.finite(lo) and E.finite(hi) else f"{v:.2f} {unit}"
            est = escape(est) + ("<br><span class='sr-muted'>90% interval</span>" if E.finite(lo) and E.finite(hi) else "")
        else:
            est = escape(f"not available ({E.field(r, 'status', 'no value')}). {E.field(r, 'reason', '')}")
        mid, state = escape(str(E.field(r, "model_id", "") or "not stated")), escape(str(E.field(r, "state", "") or "not stated"))
        scope = escape(str(E.field(r, "scope", "") or "not stated"))
        body.append(f"<tr><td>{q}</td><td>{est}</td><td><code>{mid}</code><br>{T.grade_html(E.reference_grade(r), state)}<br><span class='sr-muted'>scope: {scope}</span></td></tr>")
    st.markdown('<table class="sr-reftable"><thead><tr><th>Quantity</th><th>Estimate</th><th>Model, registry state, scope</th></tr>'
                f"</thead><tbody>{''.join(body)}</tbody></table>", unsafe_allow_html=True)


def _this_site_block(ts: ThisSite) -> None:
    def row(label: str, value: str) -> str:
        return f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"

    pct = "" if ts.pct is None else f" ({ts.pct:.0f}% of the observed rate)"
    body = (row(DEPLOYED_LABEL, f"{ts.deployed:.2f} m/yr") + row(OBSERVED_LABEL, f"{ts.observed:.2f} m/yr")
            + row(LOBO_LABEL, f"{ts.lobo:.2f} m/yr") + row(DIFF_LABEL, f"{ts.abs_diff:.2f} m/yr{pct}"))
    st.markdown(f'<div class="sr-thissite"><div class="sr-ts-title">This site: cell {escape(ts.cell)}, three separate numbers</div>'
                f"<dl>{body}</dl></div>", unsafe_allow_html=True)
    res = MV.edge_loss_scatter()
    overall = (f" Overall metric for comparison: mean absolute error {res['MAE']:.3f} m/yr over n = {res['n']:,} cells, leave-one-basin-out."
               if res.get("available") else "")
    st.caption(ONE_CELL_NOTE + overall + " Positive = land lost. The deployed model is an all-cell refit; the leave-one-basin-out "
               "prediction is a different, held-out estimate, so the two are not expected to match.")


def _expected_card(report, m: B.BoardModel, ts: ThisSite | None) -> None:
    with st.container(key="sr_expected"):
        st.markdown(f'<div class="sr-card-title">{escape(EXPECTED_TITLE)}</div>', unsafe_allow_html=True)
        if m.refused:
            st.caption(NOT_ASSESSED_TEXT)
            return
        all_rows = E.reference_rows(report)
        rows = [r for r in all_rows if E.finite(E.field(r, "value"))]
        missing = [str(E.field(r, "quantity", "")) for r in all_rows if not E.finite(E.field(r, "value"))]
        if missing:
            st.caption("No value is available for this input (no registered model covers it): " + "; ".join(missing) + ".")
        if rows:
            _reference_table(rows)
            st.caption("Intervals are 90% ranges from each model's own uncertainty method; the chip is the model's registry state, not a "
                       "coverage guarantee. Sign convention: positive edge loss = land lost.")
        if ts is not None:
            _this_site_block(ts)
        if B.referenced_model(report) is None:
            st.caption(B.NO_FORECAST_TEXT)


def _validation_card(report, ctx: dict | None, ts: ThisSite | None) -> None:
    used = models_used(report)
    with st.container(key="sr_validation"):
        st.markdown('<div class="sr-card-title">Prediction and validation status</div>', unsafe_allow_html=True)
        if EDGE_MODEL in used:
            res = MV.edge_loss_scatter()
            if not res.get("available"):
                st.warning(f"Hold-out scatter: unavailable. {res.get('reason', '')} (expected in {res.get('source', 'the repository')}).")
            else:
                st.markdown(f"**{EDGE_MODEL}**: held-out predicted against observed marsh-edge loss")
                st.altair_chart(ui_models.scatter_chart(res, height=360, highlight=None if ts is None else (ts.observed, ts.lobo)),
                                theme="streamlit", width="stretch")
                st.markdown(f'<div class="sr-stats"><span><b>MAE</b> {res["MAE"]:.3f} m/yr</span><span><b>n</b> {res["n"]:,}</span>'
                            "<span><b>Method</b> leave-one-basin-out</span><span><b>Unit</b> m/yr (positive = land lost)</span></div>",
                            unsafe_allow_html=True)
                st.caption("Dashed line: 1:1 (perfect agreement). One spill, northern Gulf salt marsh; the deployed model is an all-cells "
                           "refit and is not what is plotted. " + ("The ringed point is this cell. " if ts else "")
                           + ui_models.INDIVIDUAL_ERROR_NOTE)
        if PAH_MODEL in used:
            state = next((str(E.field(r, "state", "not stated")) for r in E.reference_rows(report)
                          if str(E.field(r, "model_id", "")) == PAH_MODEL), "not stated")
            st.caption(PAH_STATUS.format(model=PAH_MODEL, state=state))
        if ctx and B.referenced_model(report):
            st.button("How good is the number?", key=f"how_{ctx['key']}", icon=":material/query_stats:", on_click=B.open_model,
                      args=(B.referenced_model(report),),
                      help=f"Opens Model validation on {B.referenced_model(report)}, the model behind the reference numbers.")
        if not used & {EDGE_MODEL, PAH_MODEL}:
            st.caption("No validated model supplies a number for this input, so there is no hold-out chart to show.")


def _supporting(ctx: dict | None) -> None:
    st.markdown('<div class="sr-sec">Supporting evidence</div>', unsafe_allow_html=True)
    a, b = st.columns([3, 2], vertical_alignment="center")
    a.caption("Categories come from the decision pipeline's transparent rules. Evidence grade chips are not probabilities. Screening is "
              "not demonstrated effectiveness.")
    if ctx:
        b.button("Why? Evidence for this habitat", key=f"whyboard_{ctx['key']}", icon=":material/menu_book:", on_click=B.open_evidence,
                 args=(ctx["habitat"], ctx.get("esi"), ()), help="Opens the Evidence explorer filtered to this habitat class and ESI code.")


def render_results(report, rec: dict, ctx: dict, site_row: dict | None = None) -> None:
    """Draw the results view for `report` (a DecisionReport) of the run record `rec`. `ctx` = {"key", "habitat", "esi"}.
    `site_row` is the run's site-table row for a known marsh cell (None for typed, habitat-level and non-marsh runs)."""
    _title_row(report, rec, ctx["key"])
    if report is None:
        st.warning("The decision pipeline did not return a report, so there are no results to show.")
        return
    m = B.board_model(report, rec.get("flags"))
    top = None if m.refused else top_card(m)
    left, right = st.columns([5, 3], gap="medium")
    with left:
        _outcome_card(m)
    with right:
        _flags_card(m)
    if not m.refused:
        _alternatives(m, top, ctx)
    ts = this_site(report, site_row, ctx["key"])
    if m.refused:
        _expected_card(report, m, ts)
    else:
        show_valid = bool(models_used(report) & {EDGE_MODEL, PAH_MODEL})
        if show_valid:
            c1, c2 = st.columns([11, 9], gap="medium")
            with c1:
                _expected_card(report, m, ts)
            with c2:
                _validation_card(report, ctx, ts)
        else:
            _expected_card(report, m, ts)
    _supporting(ctx)
