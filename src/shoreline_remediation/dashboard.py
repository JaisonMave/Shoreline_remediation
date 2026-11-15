"""Shoreline Remediation Decision Support: Streamlit entry point (decision D40).

Run: streamlit run src/shoreline_remediation/dashboard.py
The page opens with the platform hero and the featured-location cards (ui_components, V5.1 Session 2 Stage 2).
Only the selected top-level view runs on each click. Views: "Site evidence" (real data, habitat switcher, decision pipeline) and
"Scenario screening" (legacy rule screening and illustrative process model, re-based on the decision pipeline).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Shoreline Remediation Decision Support", page_icon=":material/water:", layout="wide",
                   initial_sidebar_state="expanded")

from src.shoreline_remediation import ui_components as C  # noqa: E402
from src.shoreline_remediation.site_view import featured_sites, render_site_evidence, select_site  # noqa: E402
from src.shoreline_remediation.ui_scenario import render_scenario_view  # noqa: E402

VIEW_SITE = "Site evidence"
VIEW_SCENARIO = "Scenario screening (legacy)"


def open_site(site_id: str) -> None:
    """Card and hero buttons: switch to the site view and hand the choice to the existing site selection."""
    st.session_state["top_view"] = VIEW_SITE
    select_site(site_id)


def main() -> None:
    C.inject_css()
    pressed = C.hero(chips=[("Numerical demonstration: Louisiana salt marsh", "gray"), ("Other habitats: screening or limited evidence", "gray"),
                            ("One spill per dataset", "gray"), ("Associations, not causes", "gray")],
                     primary=C.HeroAction("Open the Bay Jimmy worked example", "open_example", open_site, ("marsh",)),
                     secondary=C.HeroAction("How evidence is graded", "evidence"))
    if pressed == "evidence":
        C.evidence_dialog()
    with st.sidebar:
        C.evidence_legend()
    cards = featured_sites()
    C.section_header("Featured locations", kicker="Explore", anchor="featured-locations",
                     description="Entries you can open now. Each card shows only what the repository holds for that entry, and says "
                                 "how each value was obtained.",
                     meta="Sources: site table, mangrove study results, model registry")
    C.card_row(cards, lambda card: C.site_card(card, on_select=open_site), key="featured",
               empty_text="No site data could be read from the repository.")
    C.section_header("Assessment", kicker="Decision support", anchor="assessment")
    view = st.segmented_control("View", [VIEW_SITE, VIEW_SCENARIO], default=VIEW_SITE, required=True, key="top_view",
                                label_visibility="collapsed")
    if view == VIEW_SCENARIO:
        render_scenario_view()
    else:
        render_site_evidence()


main()
