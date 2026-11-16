"""Decision board (V5.1 Stage 2): presents one DecisionReport. Presentation only.

Everything shown is read from the report that decision_pipeline.run_decision() returned (via ui_pipeline). The board never
recomputes a class, category, order or evidence state, adds no numeric confidence and no legacy heuristic confidence score, and
invents no flag names: flags are the report's abstentions and advisories and the site-scope flags, copied verbatim.
`board_model` is the Streamlit-free part (testable); `render_decision_board` draws it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

import streamlit as st

from src.shoreline_remediation import evidence_catalog as EC, ui_components as C, ui_evidence as E, ui_nav, ui_theme as T
from src.shoreline_remediation.decision_pipeline import CAT_NATURAL, CATEGORY_LABELS, CATEGORY_ORDER

NO_ASSESSMENT_TEXT = "No technology cards are shown because the pipeline made no assessment for this input."
NOT_SOURCED = "not sourced"
NO_FORECAST_TEXT = ("No validated numerical forecast exists for this habitat or scenario, so there is no model accuracy to inspect. "
                    "The categories above are rule-based screening from the evidence record.")
# Models whose numbers the decision pipeline can show as natural-recovery references, and whose validation can be opened.
LINKABLE_MODELS = ("edge_loss_v1", "pah_decline_v1")


@dataclass
class BoardCard:
    category: str                       # a key of decision_pipeline.CATEGORY_ORDER
    label: str                          # decision_pipeline.CATEGORY_LABELS[category]
    options: list = field(default_factory=list)   # names exactly as in report.recommendation_summary[category]
    rows: dict = field(default_factory=dict)      # option name -> report.options row (absent when the report has no row)
    is_natural: bool = False
    reference: list = field(default_factory=list)  # natural_recovery["reference"] rows (natural-recovery card only)
    monitoring: str = ""


@dataclass
class Flag:
    source: str                         # "abstentions", "advisories" or "site scope"
    kind: str                           # the abstention's own `kind`; empty for the other sources
    text: str


@dataclass
class BoardModel:
    outcome: str
    outcome_label: str
    scope_tier: str
    scope_message: str
    refused: bool                       # unsupported habitat or out of scope: message only, no technology cards
    cards: list = field(default_factory=list)
    flags: list = field(default_factory=list)


def _site_flag_texts(site_flags) -> list:
    """Texts of a site_evidence.Flags object (or None), in the order the object lists them."""
    if site_flags is None:
        return []
    out = []
    for name in ("out_of_scope", "extrapolation", "evidence_scope"):
        out += [str(x) for x in (getattr(site_flags, name, None) or [])]
    return out


def board_model(report, site_flags=None) -> BoardModel:
    summary = dict(E.field(report, "recommendation_summary", {}) or {})
    tier = str(E.field(report, "scope_tier", ""))
    flags = [Flag("abstentions", str(a.get("kind", "")) if isinstance(a, dict) else "",
                  str(a.get("text", "")) if isinstance(a, dict) else str(a))
             for a in E.field(report, "abstentions", []) or []]
    refused = tier in E.NO_ASSESSMENT_TIERS
    model = BoardModel(outcome=str(E.field(report, "decision_outcome", "")),
                       outcome_label=str(E.field(report, "decision_outcome_label", "")), scope_tier=tier,
                       scope_message=str(E.field(report, "scope_message", "")), refused=refused)
    if refused:
        model.flags = flags
        return model
    flags += [Flag("advisories", "", str(x)) for x in E.field(report, "advisories", []) or []]
    flags += [Flag("site scope", "", t) for t in _site_flag_texts(site_flags)]
    model.flags = flags
    by_name = {r["option"]: r for r in E.field(report, "options", []) or []}
    nat = E.field(report, "natural_recovery", {}) or {}
    if not any(summary.get(c) for c in CATEGORY_ORDER):
        return model
    for cat in CATEGORY_ORDER:
        names = list(summary.get(cat) or [])
        if cat == CAT_NATURAL:      # the reference option is always shown, even if the summary lists nothing under it
            model.cards.append(BoardCard(cat, CATEGORY_LABELS[cat], names, {n: by_name[n] for n in names if n in by_name},
                                         True, list(nat.get("reference") or []), str(nat.get("monitoring") or "")))
        elif names:
            model.cards.append(BoardCard(cat, CATEGORY_LABELS[cat], names, {n: by_name[n] for n in names if n in by_name}))
    return model


# ---------------------------------------------------------------------------------------------------------------
# Deep links (Streamlit-free state builders, then on_click callbacks)

def referenced_model(report) -> str | None:
    """The first of LINKABLE_MODELS used by the report's natural-recovery reference numbers, else None."""
    nat = E.field(report, "natural_recovery", {}) or {}
    used = {str(E.field(r, "model_id", "") or "") for r in nat.get("reference") or []}
    return next((m for m in LINKABLE_MODELS if m in used), None)


def evidence_link_state(habitat_label: str, esi: str | None, option_codes=()) -> dict:
    """Widget values for the Evidence explorer: habitat class of the label, the ESI code and the option display names, each kept
    only if the catalogue actually offers it (an invalid multiselect value would raise)."""
    df = EC.load_catalog()
    cls = EC.habitat_class_of(habitat_label or "")
    classes = [cls] if cls in EC.HABITAT_CLASSES else []
    codes = {t for v in df.esi_codes for t in EC._tokens(v)}
    names = set(df.option)
    opts = []
    for c in option_codes:
        for cand in (str(c), EC.option_name(str(c))):
            if cand in names and cand not in opts:
                opts.append(cand)
                break
    return {"ev_classes": classes, "ev_esi": [esi] if esi in codes else [], "ev_options": opts}


def open_evidence(habitat_label: str, esi: str | None, option_codes=()) -> None:
    """on_click callback: set the explorer filters, then go to the Evidence explorer."""
    for k, v in evidence_link_state(habitat_label, esi, option_codes).items():
        st.session_state[k] = v
    ui_nav.go("evidence")


def open_model(model_id: str) -> None:
    """on_click callback: select the model on the Model validation page, then go there."""
    st.session_state["mv_model"] = model_id
    ui_nav.go("models")


# ---------------------------------------------------------------------------------------------------------------
# Drawing

def _benefit_lines(row: dict) -> list:
    """Decision-point benefit outcomes of an option row, formatted only (value, 90% range, unit). Method, level, model and its
    registry state are named so the interval is never shown without them."""
    view = E.option_view(row)
    lines = [f"{o.label}, year {o.year}: {E.fmt_interval(o.median, o.lo, o.hi, 2)}; {o.unit}" for o in view.decision_outcomes()
             if o.year is not None]
    if lines and row.get("model_id"):
        lines.append(f"Interval: 90% interval from {row['model_id']} (registry state: {row.get('model_state', 'not stated')}); "
                     "one site's field evidence, not a validated forecast.")
    return lines


def _rating_text(row: dict) -> str | None:
    r = row.get("habitat_rating")
    if not isinstance(r, dict) or not r.get("rating"):
        return None
    cat = f", oil category {r['noaa_oil_category']}" if r.get("noaa_oil_category") else ""
    return f"Habitat rating {r['rating']}{cat} (rates adverse habitat impact, not effectiveness; Proposed, not human-verified)"


def _option_block(name: str, row: dict | None, show_rank_basis: bool, category: str, ctx: dict | None = None) -> None:
    with st.container(border=True):
        if row is None:
            st.markdown(f'<div class="sr-opt-title">{escape(E.plain_name(name))}</div>', unsafe_allow_html=True)
            st.caption("The report has no row for this option.")
            return
        view = E.option_view(row)
        st.markdown(f'<div class="sr-opt-title">{escape(view.name)}</div>{T.class_html(view.cls, with_name=False)} '
                    f'{T.grade_html(view.grade)}', unsafe_allow_html=True)
        if view.evidence_state_label:
            st.caption(f"Evidence state: {view.evidence_state_label}.")
        rating = _rating_text(row)
        if rating:
            st.caption(rating, help=str(row["habitat_rating"].get("text") or "") or None)
        if category == "excluded":
            for x in row.get("exclusion_reasons") or []:
                st.markdown(f"- Excluded: {C.humanise(str(x.get('detail', x)) if isinstance(x, dict) else str(x), [view])}")
        elif category in ("recommended", "conditional", "no_demonstrated_benefit"):
            st.write(C.humanise(str(row.get("evidence_verdict", "")), [view]))
            for line in _benefit_lines(row):
                st.markdown(f"- {line}")
        reason = row.get("recommendation_category_reason")
        if reason and category in ("conditional", "no_demonstrated_benefit"):
            st.caption(f"Why this category: {reason}")
        harm = [str(h.get("detail", h)) if isinstance(h, dict) else str(h) for h in row.get("harm_flags") or []]
        trade = str(row.get("secondary_impacts") or NOT_SOURCED)
        st.caption("Trade-offs: " + (trade if trade != NOT_SOURCED else "not sourced") + (" | Harm flags: " + "; ".join(harm) if harm else ""))
        if show_rank_basis and row.get("rank_basis_text"):
            st.caption("Order: " + str(row["rank_basis_text"]))
        if ctx:
            st.button("Why? Open the evidence", key=f"why_{ctx['key']}_{category}_{name}", icon=":material/menu_book:",
                      on_click=open_evidence, args=(ctx["habitat"], ctx.get("esi"), (name,)))


def _reference_rows(rows: list) -> None:
    for r in rows:
        quantity = str(E.field(r, "quantity", "reference quantity"))
        value = E.field(r, "value")
        if E.finite(value):
            lo, hi = E.field(r, "lo90"), E.field(r, "hi90")
            rng = E.fmt_interval(value, lo, hi, 2, str(E.field(r, "unit", ""))) if E.finite(lo) and E.finite(hi) else \
                f"{value:.2f} {E.field(r, 'unit', '')}"
            st.markdown(f"**{escape(quantity)}**: {rng}", unsafe_allow_html=True)
            mid, state = E.field(r, "model_id"), E.field(r, "state")
            st.markdown(f"Model {mid or 'not stated'}, registry state {state or 'not stated'}: "
                        + T.grade_html(E.reference_grade(r)), unsafe_allow_html=True)
            if E.field(r, "scope"):
                st.caption(f"Scope: {r['scope']}. " + " ".join(map(str, E.field(r, "scope_reasons", []) or [])))
        else:
            st.markdown(f"**{escape(quantity)}**: not available ({E.field(r, 'status', 'no value')}). "
                        f"{E.field(r, 'reason', '')}", unsafe_allow_html=True)


def _natural_card(card: BoardCard, n_other: int) -> None:
    with st.container(border=True):
        st.markdown(C.status_label(card.category, card.label), unsafe_allow_html=True)
        st.caption("The reference every intervention is compared with. It is always shown, including when no intervention is "
                   "recommended.")
        for name in card.options:
            st.markdown(f"**{E.plain_name(name)}**")
        if card.reference:
            st.markdown("**Reference numbers**")
            _reference_rows(card.reference)
        if card.monitoring:
            st.caption(f"Monitoring: {card.monitoring}")


def _links(report, ctx: dict) -> None:
    model_id = referenced_model(report)
    a, b = st.columns(2)
    with a:
        if model_id:
            st.button("How good is the number?", key=f"how_{ctx['key']}", icon=":material/query_stats:", on_click=open_model,
                      args=(model_id,), help=f"Opens Model validation on {model_id}, the model behind the reference numbers.")
        else:
            st.caption(NO_FORECAST_TEXT)
    with b:
        st.button("Why? Evidence for this habitat", key=f"whyboard_{ctx['key']}", icon=":material/menu_book:", on_click=open_evidence,
                  args=(ctx["habitat"], ctx.get("esi"), ()), help="Opens the Evidence explorer filtered to this habitat class and ESI code.")


def render_decision_board(report, site_flags=None, ctx: dict | None = None) -> None:
    """Draw the decision board for a DecisionReport. `site_flags` is an optional site_evidence.Flags (marsh cell). `ctx` (optional)
    is {"key", "habitat", "esi"} and enables the "How good is the number?" and "Why?" links."""
    if report is None:
        st.warning("The decision pipeline did not return a report, so there is no decision board.")
        return
    m = board_model(report, site_flags)
    with st.container(border=True):
        st.markdown(f'<div class="sr-answer">{escape(m.outcome_label)}</div>', unsafe_allow_html=True)
        st.markdown("Scope of the tool for this input: " + T.grade_html(T.TIER_TO_GRADE.get(m.scope_tier, "rules_literature"),
                                                                        T.TIER_TEXT.get(m.scope_tier, m.scope_tier)), unsafe_allow_html=True)
        st.write(m.scope_message)
    if m.refused:
        for f in m.flags:
            st.warning(f.text, icon=":material/block:")
        st.caption(NO_ASSESSMENT_TEXT)
        return
    st.caption("Categories come from the decision pipeline's transparent rules. Evidence grade chips are not probabilities. "
               "Screening is not demonstrated effectiveness.")
    for card in m.cards:
        n = len(card.options)
        if card.is_natural:
            _natural_card(card, n)
            continue
        st.markdown(C.status_label(card.category, card.label) + f" &nbsp;<span class='sr-muted'>{n} option{'s' if n != 1 else ''}</span>",
                    unsafe_allow_html=True)
        convention = n > 1 and any((card.rows.get(x) or {}).get("rank_basis") == "display_convention" for x in card.options)
        if convention:
            st.caption("The order within this group is a display convention, not a ranking.")
        for i in range(0, n, 2):
            cols = st.columns(2)
            for col, name in zip(cols, card.options[i:i + 2]):
                with col:
                    _option_block(name, card.rows.get(name), convention, card.category, ctx)
    if ctx:
        _links(report, ctx)
    if m.flags:
        with st.container(border=True):
            st.markdown("**Flags**")
            for f in m.flags:
                st.markdown(f"- {f.text}" + (f" (`{f.kind}`)" if f.kind else ""))


# Public names for the Assessment results view (ui_results), which reuses these pieces instead of copying them.
benefit_lines = _benefit_lines
reference_rows = _reference_rows
