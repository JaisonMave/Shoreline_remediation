"""Landing page and placeholder pages (V5.1 Session 2 Stage 3). Presentation only: data comes from site_view, nothing is
computed here, and no value on this page is a recommendation or a prediction."""
from __future__ import annotations

from typing import Callable

from html import escape

import streamlit as st

from src.shoreline_remediation import ui_components as C, ui_map, ui_site_panel, ui_theme as T
from src.shoreline_remediation.site_view import featured_sites, habitat_cards

SCOPE_CHIPS = [("Numerical demonstration: Louisiana salt marsh", "gray"), ("Other habitats: screening or limited evidence", "gray"),
               ("One spill per dataset", "gray"), ("Associations, not causes", "gray")]
INTRO = ("Choose a place on the map or a shoreline type, set the scenario, and the platform compares interventions with natural "
         "recovery, or tells you when the evidence is insufficient.")
# Orientation only (not buttons): (number, title, text)
STEP_CARDS = (("1", "Explore and select", "Click a Louisiana salt-marsh cell on the map, or choose any shoreline type."),
              ("2", "Configure scenario", "Shoreline type, oil category and oiling class: the inputs the pipeline reads."),
              ("3", "Get recommendation", "Options compared with natural recovery: recommended, conditional, excluded, or insufficient evidence."),
              ("4", "Review evidence and models", "Evidence grades, uncertainty and limitations, and what each model was validated for."))
NO_DATA = "No site data could be read from the repository."

PLACEHOLDERS = {
    "evidence": ("Evidence explorer",
                 "The evidence explorer will let you browse the evidence behind each assessment. It belongs to a later stage (Session 3).",
                 "Today: open the \"How evidence is graded\" legend (sidebar of Site assessment, or the button on Home) and the "
                 "evidence expanders inside Site assessment."),
    "models": ("Model validation",
               "The model validation page will present each model's intended use, validation status and limits. It belongs to a later stage (Session 3).",
               "Today: read docs/V5_1_VALIDATION.md and the model cards referenced in models/registry.json."),
}


def _safe(fn) -> list:
    try:
        return list(fn() or [])
    except Exception:
        return []


def render_placeholder(page_id: str, on_navigate: Callable) -> None:
    """Honest 'not built yet' page: no data, tables, metrics or numbers."""
    title, what, where = PLACEHOLDERS.get(page_id, (str(page_id), "This page will arrive in a later stage (Session 3).", ""))
    C.section_header(title, kicker="Planned")
    st.button("Back to home", key="sr_nav_home", on_click=on_navigate, args=("landing",), icon=":material/arrow_back:")
    st.info(f"This page is not yet available. {what}")
    if where:
        st.caption(where)


def step_cards_html() -> str:
    return ('<div class="sr-stepcards">' + "".join(f'<div class="sr-stepcard"><b>{n}</b><div><h3>{escape(t)}</h3><p>{escape(d)}</p></div></div>'
                                                  for n, t, d in STEP_CARDS) + "</div>")


def render_landing(on_open_site: Callable, on_navigate: Callable) -> None:
    intro, legend_btn = st.columns([6, 1], vertical_alignment="center")
    intro.markdown(f'<p class="sr-intro">{escape(INTRO)}</p>', unsafe_allow_html=True)
    if legend_btn.button("How evidence is graded", key="sr_act_hero_platform_evidence", type="tertiary", icon=":material/info:"):
        C.evidence_dialog()

    map_col, panel_col = st.columns([2, 1], gap="medium")
    with map_col:
        picked = ui_map.render_map(ui_site_panel.selected_row())
        ui_map.coordinate_check(ui_site_panel.select_cell)
    if ui_site_panel.handle_map_pick(picked):
        st.rerun()
    with panel_col:
        ui_site_panel.render_panel()

    st.markdown(step_cards_html(), unsafe_allow_html=True)
    st.markdown('<div class="sr-meta">' + "".join(f"<span>{escape(t)}</span>" for t, _ in SCOPE_CHIPS) + "</div>", unsafe_allow_html=True)

    C.section_header("Featured locations", kicker="Explore", anchor="featured-locations",
                     description="Entries you can open now. Each card shows only what the repository holds for that entry, and says "
                                 "how each value was obtained.",
                     meta="Sources: site table, mangrove study results, model registry")
    C.card_row(_safe(featured_sites), lambda card: C.site_card(card, on_select=on_open_site), key="featured", empty_text=NO_DATA)

    C.section_header("Explore habitats", kicker="Habitats", anchor="explore-habitats",
                     description="Coverage differs by habitat. The label on each card says what kind of evidence exists for it.",
                     meta="Sources: habitat table, model registry")
    st.markdown('<div class="sr-tiers">' + " ".join(T.grade_html(v["grade"], v["label"]) for v in T.COVERAGE_TIERS.values()) + "</div>",
                unsafe_allow_html=True)

    def render_habitat(card) -> None:
        tier = card.tier if card.tier in T.COVERAGE_TIERS else "screening"
        openable = bool(card.action_label)
        C.site_card(card, on_select=on_open_site if openable else None, key=f"hab_{tier}_{card.site_id}", button_key=f"hab_{card.site_id}")

    C.card_row(_safe(habitat_cards), render_habitat, key="habitats", empty_text=NO_DATA)
