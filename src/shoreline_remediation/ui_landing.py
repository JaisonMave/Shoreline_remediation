"""Landing page and placeholder pages (V5.1 Session 2 Stage 3). Presentation only: data comes from site_view, nothing is
computed here, and no value on this page is a recommendation or a prediction."""
from __future__ import annotations

from typing import Callable

from html import escape

import streamlit as st

from src.shoreline_remediation import ui_components as C, ui_theme as T
from src.shoreline_remediation.site_view import featured_sites, habitat_cards

SCOPE_CHIPS = [("Numerical demonstration: Louisiana salt marsh", "gray"), ("Other habitats: screening or limited evidence", "gray"),
               ("One spill per dataset", "gray"), ("Associations, not causes", "gray")]
STEPS = ("Explore the shoreline and the available environmental evidence.",
         "Evaluate intervention options against natural recovery.",
         "Review recommendations, evidence grades, uncertainty and limitations.")
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


def render_landing(on_open_site: Callable, on_navigate: Callable) -> None:
    pressed = C.hero(chips=SCOPE_CHIPS,
                     primary=C.HeroAction("Explore shoreline sites", "explore", on_navigate, ("site",)),
                     secondary=C.HeroAction("How evidence is graded", "evidence"))
    if pressed == "evidence":
        C.evidence_dialog()

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
    tier_of = {v["label"]: k for k, v in T.COVERAGE_TIERS.items()}

    def render_habitat(card) -> None:
        tier = tier_of.get(card.kicker, "screening")
        openable = bool(card.action_label)
        C.site_card(card, on_select=on_open_site if openable else None, key=f"hab_{tier}_{card.site_id}", button_key=f"hab_{card.site_id}")

    C.card_row(_safe(habitat_cards), render_habitat, key="habitats", empty_text=NO_DATA)

    C.section_header("How the platform works", kicker="Method", anchor="how-it-works")
    st.markdown('<div class="sr-steps">' + "".join(f'<div class="sr-step"><b>{i}</b><p>{escape(t)}</p></div>'
                                                     for i, t in enumerate(STEPS, 1)) + "</div>", unsafe_allow_html=True)
