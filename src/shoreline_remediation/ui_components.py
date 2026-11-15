"""Streamlit building blocks for the dashboard (decision D40): chips, legend, scope panel, answer card, option cards,
interval chart, reference numbers, "Sources and decisions", beach placeholder.

Everything reads display objects from ui_evidence (built from the decision pipeline's report) and wording from ui_theme.
Colours never carry meaning alone: every chip has words, and the classes also carry a letter and a symbol.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Callable, Sequence

import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from . import ui_evidence as E
from . import ui_theme as T
from .decision_pipeline import CATEGORY_LABELS


# ---------------------------------------------------------------------------------------------------------------
# Theme helpers

def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:  # not in a browser session (tests), or an older Streamlit
        return False


def inject_css() -> None:
    st.markdown(T.CSS, unsafe_allow_html=True)


def text_colour() -> str:
    return T.PALETTE["text"] if is_dark() else "#1B2A30"


def themed_fig(figsize=(9, 4.2)):
    """Matplotlib figure with a transparent background and theme-aware text, readable in light and dark mode."""
    fig, ax = plt.subplots(figsize=figsize)
    style_axes(fig, ax)
    return fig, ax


def style_axes(fig, *axes) -> None:
    colour = text_colour()
    fig.patch.set_alpha(0)
    for ax in axes or fig.axes:
        ax.set_facecolor("none")
        ax.tick_params(colors=colour, labelsize=9)
        ax.xaxis.label.set_color(colour)
        ax.yaxis.label.set_color(colour)
        ax.title.set_color(colour)
        for spine in ax.spines.values():
            spine.set_color(T.NEUTRAL)
        leg = ax.get_legend()
        if leg:
            for t in leg.get_texts():
                t.set_color(colour)
            leg.get_frame().set_alpha(0)


def show_fig(fig, **kwargs) -> None:
    """Render a matplotlib figure and close it (figures are not kept in memory between reruns)."""
    style_axes(fig)
    st.pyplot(fig, width="stretch", transparent=True, **kwargs)
    plt.close(fig)


def ai_style_dataframe(df: pd.DataFrame):
    """Desaturated look for tables of AI-proposed numbers (grid cells accept only colour, not hatching)."""
    return df.style.set_properties(**{"color": "#8A7F99", "font-style": "italic"})


# ---------------------------------------------------------------------------------------------------------------
# Header, legend, scope

# Reusable components (V5.1 Session 2 Stage 2). Each has a pure *_html builder (testable without a browser) and a thin
# Streamlit renderer. They show what they are given: no component computes a recommendation or fills in a missing value.

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_") or "item"


def section_header_html(title: str, kicker: str | None = None, description: str | None = None, meta: str | None = None,
                        anchor: str | None = None) -> str:
    """Kicker, heading, optional description and optional right-hand metadata (for example a count or a data source)."""
    kick = f'<div class="sr-kicker">{escape(kicker)}</div>' if kicker else ""
    side = f'<div class="sr-section-meta">{escape(meta)}</div>' if meta else ""
    desc = f'<p class="sr-section-desc">{escape(description)}</p>' if description else ""
    ident = f' id="{escape(anchor, quote=True)}"' if anchor else ""
    return (f'<div class="sr-section"{ident}>{kick}<div class="sr-section-head"><h2>{escape(title)}</h2>{side}</div>'
            f'{desc}</div>')


def section_header(title: str, kicker: str | None = None, description: str | None = None, meta: str | None = None,
                   anchor: str | None = None) -> None:
    st.markdown(section_header_html(title, kicker, description, meta, anchor), unsafe_allow_html=True)


def status_label(category: str | None, label: str | None = None) -> str:
    """HTML label for a recommendation category assigned by decision_pipeline.run_decision() (decision D41).

    `category` is a key of decision_pipeline.CATEGORY_ORDER; the wording is the pipeline's own CATEGORY_LABELS unless the
    report's label is passed in. A missing or unrecognised category is shown as exactly that, in a neutral dotted style:
    it is never mapped to a real category. This function does not decide anything.
    """
    key = str(category or "").strip()
    style = T.CATEGORY_STYLE.get(key)
    if style is None:
        text = f"{T.STATUS_UNRECOGNISED_TEXT}: {key}" if key else T.STATUS_MISSING_TEXT
        return (f'<span class="sr-status sr-status-unknown" style="--c:{T.CATEGORY_UNKNOWN["colour"]}">'
                f'<b aria-hidden="true">{T.CATEGORY_UNKNOWN["symbol"]}</b><span>{escape(text)}</span></span>')
    text = label or CATEGORY_LABELS[key]
    return (f'<span class="sr-status sr-status-{key.replace("_", "-")}" style="--c:{style["colour"]}">'
            f'<b aria-hidden="true">{style["symbol"]}</b><span>{escape(text)}</span></span>')


@dataclass(frozen=True)
class SiteFact:
    """One value on a site card. `kind` is a key of ui_theme.VALUE_KINDS and says how the value was obtained.
    `value=None` means the repository has no such value: the card says "not available" instead of leaving it out."""
    label: str
    value: str | None
    kind: str = "record"


@dataclass(frozen=True)
class SiteCard:
    """Display record for one site or habitat entry. Built by the data layer (site_view.featured_sites) from repository
    files; the card adds nothing. `site_id` is passed unchanged to the navigation callback."""
    site_id: str
    name: str
    kicker: str = ""
    location: str = ""
    habitat: str = ""
    description: str = ""
    facts: tuple[SiteFact, ...] = ()
    evidence: tuple[tuple[str, str], ...] = ()      # (evidence grade key from ui_theme.GRADES, chip text)
    action_label: str = "Open site assessment"


def site_card_html(card: SiteCard) -> str:
    where = " | ".join(x for x in (card.location, card.habitat) if x)
    parts = ['<div class="sr-site">']
    if card.kicker:
        parts.append(f'<div class="sr-kicker">{escape(card.kicker)}</div>')
    parts.append(f"<h3>{escape(card.name)}</h3>")
    if where:
        parts.append(f'<div class="sr-site-where">{escape(where)}</div>')
    if card.description:
        parts.append(f'<p class="sr-site-desc">{escape(card.description)}</p>')
    if card.facts:
        rows = []
        for f in card.facts:
            if f.value is None or f.kind == "unavailable":
                rows.append(f'<div><dt>{escape(f.label)}</dt><dd class="sr-unavailable">{T.VALUE_KINDS["unavailable"].lower()}</dd></div>')
            else:
                kind = T.VALUE_KINDS.get(f.kind, T.VALUE_KINDS["record"])
                rows.append(f"<div><dt>{escape(f.label)}</dt><dd>{escape(str(f.value))}<small>{escape(kind)}</small></dd></div>")
        parts.append("<dl>" + "".join(rows) + "</dl>")
    if card.evidence:
        parts.append('<div class="sr-site-evidence">' + " ".join(T.grade_html(g, t) for g, t in card.evidence) + "</div>")
    parts.append("</div>")
    return "".join(parts)


def site_card(card: SiteCard, on_select: Callable[[str], None] | None = None, key: str | None = None,
              button_key: str | None = None) -> None:
    """One site card. With `on_select` the card gets a button that calls on_select(card.site_id) before the rerun; without
    it no button is drawn (a button that does nothing is never shown). `key` replaces the id slug in the container and button
    keys (sr_site_<key>, sr_open_site_<key>), so one entry can appear in two rows; `button_key` overrides the button suffix."""
    slug = _slug(key if key is not None else card.site_id)
    with st.container(key=f"sr_site_{slug}"):
        st.markdown(site_card_html(card), unsafe_allow_html=True)
        if on_select is not None:
            st.button(card.action_label, key=f"sr_open_site_{_slug(button_key) if button_key else slug}", on_click=on_select, args=(card.site_id,),
                      width="stretch")


def card_row(items: Sequence, render: Callable, key: str, empty_text: str = "Nothing to show here yet.") -> int:
    """A row of cards: calls render(item) for each item inside one wrapping flex container.

    The row wraps instead of scrolling sideways: three cards sit side by side on a desktop, and stack on a phone, with no
    horizontal page overflow and no JavaScript. Streamlit buttons cannot live inside a raw-HTML scroll strip (.sr-row), so
    cards with a working button use this. Returns the number of cards drawn; an empty list shows `empty_text`.
    """
    items = list(items)
    if not items:
        st.caption(empty_text)
        return 0
    with st.container(horizontal=True, wrap=True, gap="medium", key=f"sr_row_{_slug(key)}"):
        for item in items:
            render(item)
    return len(items)


@dataclass(frozen=True)
class HeroAction:
    """A hero button. `key` is returned by hero_feature() when the button is pressed; `on_click` (optional) runs first."""
    label: str
    key: str
    on_click: Callable | None = None
    args: tuple = ()


def hero_feature_html(title: str, description: str, kicker: str | None = None, points: Sequence[str] = (),
                      meta: Sequence[str] = ()) -> str:
    kick = f'<div class="sr-kicker">{escape(kicker)}</div>' if kicker else ""
    pts = ('<ul class="sr-hero-points">' + "".join(f"<li>{escape(p)}</li>" for p in points) + "</ul>") if points else ""
    tags = ('<div class="sr-meta">' + "".join(f"<span>{escape(m)}</span>" for m in meta) + "</div>") if meta else ""
    return f'<div class="sr-hero">{kick}<h1>{escape(title)}</h1><p>{escape(description)}</p>{pts}{tags}</div>'


def hero_feature(title: str, description: str, kicker: str | None = None, points: Sequence[str] = (), meta: Sequence[str] = (),
                 primary: HeroAction | None = None, secondary: HeroAction | None = None, key: str = "main") -> str | None:
    """Featured banner for a platform overview, a site or a habitat: kicker, title, description, optional capability
    points, optional metadata tags, and up to two real buttons. Returns the `key` of the action pressed in this run, or
    None. Gradients only: no image, no figure that the caller did not pass in."""
    pressed = None
    with st.container(key=f"sr_hero_{_slug(key)}"):
        st.markdown(hero_feature_html(title, description, kicker, points, meta), unsafe_allow_html=True)
        actions = [a for a in (primary, secondary) if a is not None]
        if actions:
            with st.container(horizontal=True, wrap=True, gap="small"):
                for a in actions:
                    if st.button(a.label, key=f"sr_act_hero_{_slug(key)}_{_slug(a.key)}", on_click=a.on_click, args=a.args,
                                 type="primary" if a is primary else "secondary"):
                        pressed = a.key
    return pressed


HERO_TITLE = "Shoreline Remediation Intelligence"
HERO_KICKER = "Coastal and marine decision support"
HERO_DESCRIPTION = ("A scientifically governed decision-support platform for assessing coastal and marine shoreline conditions, "
                    "evaluating remediation options and understanding ecological recovery evidence.")
HERO_POINTS = ("Explore shoreline environments and assessment sites.",
               "Compare remediation pathways with natural recovery.",
               "Understand the evidence, uncertainty and limitations behind decisions.")


def hero(subtitle: str | None = None, chips: list[tuple[str, str]] | None = None, primary: HeroAction | None = None,
         secondary: HeroAction | None = None) -> str | None:
    """Platform banner, built on hero_feature(). `subtitle` replaces the standard description; `chips` are (text, colour)
    pairs as before, now shown as neutral scope tags (the colour is ignored, so a tag cannot read as a validation
    status). Returns the key of the action pressed, or None."""
    return hero_feature(HERO_TITLE, subtitle or HERO_DESCRIPTION, kicker=HERO_KICKER, points=HERO_POINTS,
                        meta=[text for text, _ in (chips or [])], primary=primary, secondary=secondary, key="platform")


def evidence_legend_body() -> None:
    """The five evidence grades and the class letters, in words."""
    for key in T.GRADE_ORDER:
        info = T.GRADES[key]
        st.markdown(f'<div class="sr-legend-row">{T.grade_html(key)} {escape(info["legend"])}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sr-legend-row sr-muted">Recommendation classes: '
                + " ".join(T.class_html(c, with_name=False) for c in T.CLASS_ORDER)
                + " (A benefit, B unclear, C natural recovery, D harm under conditions, E excluded)</div>", unsafe_allow_html=True)


def evidence_legend() -> None:
    """Permanent legend of the five evidence grades (used by every chip in the dashboard)."""
    with st.expander("Evidence grades: what the chips mean", expanded=False):
        evidence_legend_body()


@st.dialog("How evidence is graded", width="large")
def evidence_dialog() -> None:
    """The same legend, opened from the hero."""
    st.markdown("Every number and verdict carries one of five evidence grades. Only the first means a model passed a test on "
                "data it never saw, and that holds for a limited scope, not for every habitat.")
    evidence_legend_body()


def scope_panel(habitat: str, extra: list[str] | None = None) -> None:
    """One-line scope bar plus ONE 'Scope and limits' panel (replaces many same-weight caveat boxes)."""
    line = T.SCOPE_ONE_LINE.get(habitat, T.SCOPE_ONE_LINE["marsh"])
    c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
    c1.markdown(f'<div class="sr-scope">{escape(line)}</div>', unsafe_allow_html=True)
    with c2.popover("Scope and limits", icon=":material/rule:", width="stretch"):
        st.markdown("**What this tool can and cannot tell you**")
        for x in T.SCOPE_LIMITS.get(habitat, []) + list(extra or []):
            st.markdown(f"- {x}")
        st.caption(T.LABELS["interval_note"])


# ---------------------------------------------------------------------------------------------------------------
# Answer card

def humanise(text: str, options: list) -> str:
    """Replace option codes such as manual_removal by plain names in the pipeline's headline."""
    for o in sorted(options, key=lambda o: -len(o.option)):
        text = re.sub(rf"(?<![A-Za-z_]){re.escape(o.option)}(?![A-Za-z_])", o.name[:1].lower() + o.name[1:], text)
    return text


def answer_card(view, where: str, metrics: list[dict] | None = None) -> None:
    """Answer first: where, headline recommendation with its evidence chip, then the key numbers."""
    with st.container(border=True):
        st.markdown(f"**{where}**")
        if view is None:
            st.warning("The decision pipeline could not produce a recommendation for these inputs.")
        else:
            st.markdown(f'<div class="sr-answer">{escape(humanise(view.headline, view.options))}</div>', unsafe_allow_html=True)
            info = T.grade_info(view.headline_grade)
            st.markdown("Evidence behind this recommendation: " + T.grade_html(view.headline_grade, view.headline_grade_text)
                        + "&nbsp; Scope of the tool for this input: " + T.grade_html(view.tier_grade, view.tier_text),
                        unsafe_allow_html=True)
            if view.evidence_state_label:
                st.markdown(f"Against natural recovery: **{view.evidence_state_label}**")
            st.caption(info["legend"])
        if metrics:
            cols = st.columns(len(metrics))
            for col, m in zip(cols, metrics):
                col.metric(m["label"], m["value"], delta=m.get("range"), delta_color="off", delta_arrow="off",
                           help=m.get("help"), border=True)
                if m.get("grade"):
                    col.markdown(T.grade_html(m["grade"], m.get("grade_text")), unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------------------------
# Option comparison: interval chart + cards

_OUTCOME_OPTIONS = {"edge_loss_avoided_m": "Marsh edge saved (m)", "veg_cover_ratio_gain": "Vegetation cover gained"}


def interval_chart(rows: list, title: str, x_title: str) -> alt.Chart:
    """Median dot and 90% range bar for each option, on a shared, visible zero line."""
    df = pd.DataFrame(rows)
    order = list(df["option"])
    opacity = {"validated": 1.0, "experimental": 0.75, "rules_literature": 0.55, "ai_proposed": 0.45, "illustrative": 0.4}
    df["opacity"] = df["grade"].map(opacity).fillna(0.5)
    df["Class"] = df["cls"]
    df["Range"] = [f"{r.median:+.2f} (90% range {r.lo:+.2f} to {r.hi:+.2f})" for r in df.itertuples()]
    df["Evidence"] = df["grade"].map(lambda g: T.grade_info(g)["label"])
    colour = alt.Color("Class:N", scale=alt.Scale(domain=T.CLASS_ORDER, range=[T.class_style(c)["colour"] for c in T.CLASS_ORDER]),
                       legend=alt.Legend(title="Class", orient="bottom"))
    y = alt.Y("option:N", sort=order, title=None, axis=alt.Axis(labelLimit=260))
    tip = ["option", "Range", "Evidence", "Class"]
    base = alt.Chart(df)
    bars = base.mark_rule(size=5).encode(x=alt.X("lo:Q", title=x_title), x2="hi:Q", y=y, color=colour,
                                         opacity=alt.Opacity("opacity:Q", legend=None), tooltip=tip)
    dots = base.mark_point(filled=True, size=110, stroke="white", strokeWidth=1).encode(
        x="median:Q", y=y, color=colour, opacity=alt.Opacity("opacity:Q", legend=None), tooltip=tip)
    zero = alt.Chart(pd.DataFrame({"x": [0.0], "t": ["0 = same as natural recovery"]}))
    zero_rule = zero.mark_rule(strokeDash=[5, 4], strokeWidth=2, color=T.NEUTRAL).encode(x="x:Q")
    zero_text = zero.mark_text(align="left", dx=4, dy=-4, baseline="bottom", fontSize=11, color=T.NEUTRAL).encode(
        x="x:Q", y=alt.value(0), text="t:N")
    return (zero_rule + bars + dots + zero_text).properties(height=max(90, 34 * len(df) + 70), title=title)


def render_interval_comparison(view, key: str) -> None:
    """Interval bars for the options that have numbers, for one chosen outcome and year."""
    outcomes = E.available_outcomes(view.options)
    if not outcomes:
        st.caption("No option has a numerical forecast for this input, so there is nothing to put on an interval chart. "
                   "The cards below give the screening verdict and the source for each option.")
        return
    keys = list(outcomes)
    sig = "_".join(f"{k}{''.join(map(str, v))}" for k, v in outcomes.items())
    c1, c2 = st.columns([2, 1])
    outcome = c1.segmented_control("Outcome", keys, default=keys[0], required=True, key=f"{key}_outcome_{sig}",
                                   format_func=lambda k: _OUTCOME_OPTIONS.get(k, E.plain_name(k)))
    years = outcomes[outcome]
    year = c2.segmented_control("Year after cleanup", years, default=years[-1], required=True, key=f"{key}_year_{sig}_{outcome}",
                                format_func=lambda y: f"year {y}")
    rows = E.interval_rows(view.options, outcome, year)
    if not rows:
        st.caption("No option has numbers for that outcome and year.")
        return
    label, unit = E.OUTCOME_LABELS.get(outcome, (E.plain_name(outcome), ""))
    x_title = (T.LABELS["edge_saved"] if outcome == "edge_loss_avoided_m" else T.LABELS["veg_gain"]) + ": right of zero is better"
    st.altair_chart(interval_chart(rows, f"{label}, year {year}", x_title), theme="streamlit", width="stretch")
    crossing = [r["option"] for r in rows if r["crosses_zero"]]
    notes = []
    if crossing:
        notes.append("Range crosses zero (cannot be told apart from natural recovery): " + ", ".join(crossing) + ".")
    if E.any_overlap(rows):
        notes.append(T.LABELS["overlap_note"])
    notes.append("Fainter marks mean weaker evidence than a validated model. All of these come from one site's field plots.")
    st.caption(" ".join(notes))


def _option_card(o) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="sr-opt-title">{escape(o.name)}</div>'
                    f'{status_label(o.category, o.category_label or None)} {T.class_html(o.cls, with_name=False)} '
                    f'{T.grade_html(o.grade)}', unsafe_allow_html=True)
        st.write(o.verdict_text)
        if o.evidence_state_label:
            st.caption(f"Evidence state: {o.evidence_state_label}.")
        if o.evidence_design:
            st.caption(f"Design of the evidence: {o.evidence_design}")
        st.caption(f"Source: {o.source_text}.", help="; ".join(o.source_ids) or None)
        with st.expander("Details and caveats"):
            st.markdown(f"**Evidence grade:** {T.grade_info(o.grade)['label']}. {o.grade_note}.")
            if o.rule_verdict:
                st.markdown(f"**Screening rule:** {o.rule_verdict}. {o.rule_reason}")
            for x in o.outcomes:
                if x.decision_point or x.year is None:
                    continue
                st.markdown(f"- {x.label}, year {x.year}: {E.fmt_interval(x.median, x.lo, x.hi, 2)}")
            if o.advisory_notes:
                st.markdown("**Advisory notes** (AI-proposed, not used to set the class):")
                for c in o.advisory_notes:
                    st.markdown(f"- {c}")
            if o.conditions:
                st.markdown("**Conditions to check** (AI-proposed, not human-reviewed):")
                for c in o.conditions:
                    st.markdown(f"- {c}")
            if o.caveats:
                st.markdown("**Caveats:**")
                for c in o.caveats:
                    st.markdown(f"- {c}")
            if o.ecological_score is not None:
                st.caption(f"Assumed ecological score {o.ecological_score:.1f} of 10 (higher means less disturbance). "
                           "It orders options inside a class; it is not evidence.")


def render_option_cards(view, key: str) -> None:
    """Cards for classes A to D and a compact table for the excluded options (class E)."""
    groups = view.by_class()
    st.caption("Within a class the options are listed in the pipeline's order. That order is not a ranking of how well they work.")
    for cls in ("A", "B", "C", "D"):
        members = groups.get(cls, [])
        if not members:
            continue
        s = T.class_style(cls)
        st.markdown(f'{T.class_html(cls)} <span class="sr-muted">{escape(s["plain"])}</span>', unsafe_allow_html=True)
        for i in range(0, len(members), 2):
            cols = st.columns(2)
            for col, o in zip(cols, members[i:i + 2]):
                with col:
                    _option_card(o)
    for cls in sorted(c for c in groups if c not in ("A", "B", "C", "D", "E")):  # classes the pipeline may add later
        for o in groups[cls]:
            _option_card(o)
    excluded = groups.get("E", [])
    if excluded:
        s = T.class_style("E")
        st.markdown(f'{T.class_html("E")} <span class="sr-muted">{escape(s["plain"])}</span>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Option": o.name, "Why it is excluded": o.verdict_text.removeprefix("Excluded: "),
                                    "Evidence": T.grade_info(o.grade)["label"], "Source": o.source_text} for o in excluded]),
                     hide_index=True, width="stretch")


def render_reference_numbers(view) -> None:
    """Reference numbers that belong to no single option (decline rates, recovery times), each with its grade."""
    rows = []
    for r in view.reference:
        quantity = str(E.field(r, "quantity", ""))
        value, lo, hi = E.field(r, "value"), E.field(r, "lo90"), E.field(r, "hi90")
        unit = str(E.field(r, "unit", ""))
        if E.field(r, "status") == "no model" or not E.finite(value):
            rng = E.field(r, "reason", "") or ("no decline detected" if E.field(r, "status") else "no value")
            rows.append({"Quantity": quantity, "Value": "no model" if E.field(r, "status") == "no model" else "none", "90% range": rng,
                         "Evidence": "-", "Note": ""})
            continue
        grade = E.reference_grade(r)
        rows.append({"Quantity": quantity, "Value": f"{value:.2f} {unit}".strip(),
                     "90% range": f"{lo:.2f} to {hi:.2f}" if E.finite(lo) and E.finite(hi) else "not available",
                     "Evidence": T.grade_info(grade)["label"], "Note": str(E.field(r, "note", ""))})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.caption("No reference numbers for this input.")


def render_sources_and_decisions(view, extra_text: str | None = None) -> None:
    """Internal references live here, not in the main text."""
    with st.expander("Sources and decisions"):
        version = E.field(view.extra, "version", {}) or {}
        st.markdown("**How this report was made.** A fixed eight-step pipeline: characterise the site, apply hard constraints, "
                    "check for harm, compare with natural recovery, estimate time to endpoint, list trade-offs, assign a "
                    "recommendation class, and write the report. There is no weighted score and no language model.")
        if version:
            models = E.field(version, "models", {}) or {}
            st.markdown("**Version block:** pipeline " + str(E.field(version, "pipeline_version", "?"))
                        + (f", code commit {str(version['git_commit'])[:9]}" if E.field(version, "git_commit") else "")
                        + (f", random seed {version['seed']}, {version['n_draws']} Monte Carlo draws" if "seed" in version else "") + ".")
            if models:
                st.dataframe(pd.DataFrame([{"Model": k, "State": E.field(v, "state", ""), "Version": E.field(v, "version", "")}
                                           for k, v in models.items()]), hide_index=True, width="stretch")
        trace = E.field(view.extra, "trace", []) or []
        if trace:
            st.dataframe(pd.DataFrame([{"Step": E.field(t, "step"), "Name": str(E.field(t, "name", "")).replace("_", " "),
                                        "Sources": "; ".join(map(str, E.field(t, "sources", []) or []))} for t in trace]),
                         hide_index=True, width="stretch")
        st.caption("Decision references: D13 (treatment mapping), D17 and D31 (outcomes stay separate, no weighted score), "
                   "D26 (rule-trained suitability model out of the decision path), D30 (scope tiers), D32 (oil excess), "
                   "D40 (dashboard re-based on the decision pipeline; evidence grades). " + (extra_text or ""))


def render_pipeline_section(view, key: str, show_chart: bool = True) -> None:
    """The recommendation section used by the site view (all habitats) and the legacy scenario view."""
    if view is None:
        return
    if view.out_of_scope:
        st.info(view.scope_message, icon=":material/block:")
        return
    if view.decision_outcome_label:
        st.markdown(f"**Decision outcome:** {view.decision_outcome_label}.")
    if view.abstentions:
        with st.expander("What the platform does not state for this input", icon=":material/do_not_disturb_on:"):
            for item in view.abstentions:
                st.markdown(f"- {E.field(item, 'text', item)}")
    if show_chart:
        render_interval_comparison(view, key)
    render_option_cards(view, key)
    with st.expander("Reference numbers that are not tied to one option"):
        render_reference_numbers(view)
    plots = E.field(view.extra, "plots", {}) or {}
    matrix = E.field(plots, "evidence_matrix", []) or []
    if matrix:
        with st.expander("Evidence matrix (every verdict that was used)"):
            st.dataframe(pd.DataFrame([{"Option": E.plain_name(E.field(m, "option", "")), "Outcome": str(E.field(m, "outcome_family", "")).replace("_", " "),
                                        "Verdict": E.field(m, "verdict", ""), "Source": E.field(m, "source", ""),
                                        "Basis": E.field(m, "basis", "")} for m in matrix]), hide_index=True, width="stretch")


# ---------------------------------------------------------------------------------------------------------------
# AI-proposed ranges (never shown as evidence)

def render_ai_ranges(rows: list[dict], key: str = "ai") -> None:
    """Table of AI-proposed ranges in a hatched, desaturated block. Never uses 'distinguished' or support wording."""
    if not rows:
        return
    head = "".join(f"<th>{escape(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in r.values()) + "</tr>" for r in rows)
    st.markdown(f'<div class="sr-ai-block"><div>{T.grade_html("ai_proposed", T.LABELS["ai_range"])}</div>'
                f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>', unsafe_allow_html=True)
    st.caption("These ranges were written by an AI assistant from the literature. They are not field evidence, have not been "
               "reviewed by a person, and are not used to recommend or rule out an option.")


# ---------------------------------------------------------------------------------------------------------------
# Beach persistence (sand-beach baseline curve for ESI 3A; rules and literature only elsewhere)

_BEACH_RESULTS = Path(__file__).resolve().parents[2] / "results" / "v5_beach"
GROUP_LABELS = {"surface_light": "Light surface oil", "surface_mod_heavy": "Moderate or heavy surface oil",
                "tb_neg_light": "Light tarballs (or none)", "tb_mod_heavy": "Moderate or heavy tarballs"}


@st.cache_data
def reoiling_figures() -> dict | None:
    """Re-oiling of cleared segments, read from results/v5_beach/reoiling.csv (row 'all')."""
    path = _BEACH_RESULTS / "reoiling.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    row = df[df["subset"] == "all"]
    if row.empty:
        return None
    r = row.iloc[0]
    return {"cleared": int(r["n_cleared_with_later_visit"]), "reoiled": int(r["n_reoiled"]), "share": float(r["share_reoiled"]),
            "median_days": float(r["median_days_clear_to_reoil"])}


def _beach_reference(site: dict | None):
    """The persistence reference: from the pipeline report if given, else from beach_model (imported defensively)."""
    ref = (site or {}).get("reference")
    if ref and ref.get("curves_by_group"):
        return ref
    try:
        from src.shoreline_remediation import beach_model
        card = beach_model.load_card()
        curves = card["baseline_curves_all_states"]
        by_group = {g: {"n_segments": c["n"], "median": c["median"], "lo90": c["lo90"], "hi90": c["hi90"]} for g, c in curves.items()}
        group = next(iter(by_group))
        return {"curves_by_group": by_group, "group": group, "curve": by_group[group], "horizons_days": list(beach_model.HORIZONS),
                "scope_reasons": list(card.get("caveats_short", []))}
    except Exception:  # module missing or still changing
        return None


def _persistence_chart(horizons, med, lo, hi) -> alt.Chart:
    d = pd.DataFrame({"days": horizons, "median": med, "lo": lo, "hi": hi})
    d["Range"] = [f"{m:.0%} (90% range {a:.0%} to {b:.0%})" for m, a, b in zip(d["median"], d["lo"], d["hi"])]
    x = alt.X("days:O", title="Days after the first oiled survey")
    y = alt.Y("lo:Q", title="Share of segments still recorded oiled", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"))
    blue = T.OKABE_ITO["blue"]
    bars = alt.Chart(d).mark_rule(size=5, color=blue, opacity=0.75).encode(x=x, y=y, y2="hi:Q", tooltip=["days", "Range"])
    dots = alt.Chart(d).mark_point(filled=True, size=110, color=blue, opacity=0.75).encode(x="days:O", y="median:Q", tooltip=["days", "Range"])
    line = alt.Chart(d).mark_line(color=blue, opacity=0.4).encode(x="days:O", y="median:Q")
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(strokeDash=[5, 4], strokeWidth=2, color=T.NEUTRAL).encode(y="y:Q")
    return (zero + line + bars + dots).properties(height=240)


def render_beach_persistence(site: dict | None) -> None:
    """Persistence panel for beaches. Sand beach (ESI 3A): the packaged baseline curve with a 90% range, as a REFERENCE (visible oil
    under the cleanup as carried out; not natural recovery, not a treatment comparison). ESI 4, 5 and 6A: no outcome model, rules and
    literature only, plus the literature notes the pipeline returns. Never raises if beach_model is missing or changing."""
    site = site or {}
    esi = str(site.get("esi", ""))
    with st.container(border=True):
        if esi != "3A":
            st.markdown("#### No outcome model: rules and literature only")
            st.markdown(T.grade_html("rules_literature"), unsafe_allow_html=True)
            st.caption("There is no persistence or recovery model for this beach type. The options below come from screening rules and "
                       "published findings, and the notes are not a prediction for this site.")
            notes = site.get("literature_notes") or []
            if notes:
                st.markdown("**Literature notes (literature, not a prediction)**")
                for n in notes:
                    st.markdown(f"- {E.field(n, 'statement', '')} ({E.field(n, 'source', '')}; {E.field(n, 'label', 'literature, not a prediction')})")
            return
        ref = _beach_reference(site)
        st.markdown("#### How long visible oil stayed on fine-to-medium sand beaches")
        st.markdown(T.grade_html("experimental", "Experimental: failed validation"), unsafe_allow_html=True)
        if ref is None:
            st.info("The sand-beach persistence data are not available in this installation.", icon=":material/info:")
            return
        groups = list(ref["curves_by_group"])
        default = ref.get("group") if ref.get("group") in groups else groups[0]
        group = st.segmented_control("First oiling category seen at the segment", groups, default=default, required=True,
                                     key=f"beach_group_{site.get('habitat', 'x')}", format_func=lambda g: GROUP_LABELS.get(g, g),
                                     help="The pipeline does not know which category was seen first, so you choose it.")
        c = ref["curves_by_group"][group]
        horizons = ref.get("horizons_days") or [90, 180, 365, 730]
        st.altair_chart(_persistence_chart(horizons, c["median"], c["lo90"], c["hi90"]), theme="streamlit", width="stretch")
        ro = reoiling_figures()
        text = ("This is visible oil on the beach under the cleanup as it was actually carried out in 2010 to 2013. It is not natural "
                "recovery and not a comparison of treatments. ")
        if ro:
            text += (f"About {ro['share']:.0%} of cleared segments ({ro['reoiled']} of {ro['cleared']}) were recorded oiled again, a median of "
                     f"{ro['median_days']:.0f} days later, so 'no oil observed' was often not lasting. ")
        text += ("Results differed strongly between states and depend on how often a segment was surveyed. The model did not beat a "
                 f"simple baseline on held-out states, so only the baseline curve is shown (n = {c.get('n_segments', '?')} segments in this group).")
        st.markdown(text)
        for r in ref.get("scope_reasons", [])[:1]:
            st.caption(str(r))
