"""Shoreline Remediation Decision Support: Streamlit entry point (decision D40).

Run: streamlit run src/shoreline_remediation/dashboard.py
Pages (ui_nav.PAGES): Home (landing: hero, featured locations, habitat coverage), Site assessment (real data, habitat switcher,
decision pipeline), Evidence explorer and Model validation (placeholders for Session 3), Legacy and research (legacy rule
screening and illustrative process model, kept for comparison; it does not drive production recommendations).
Only the selected page runs on each click.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Shoreline Remediation Decision Support", page_icon=":material/water:", layout="wide",
                   initial_sidebar_state="auto")

from src.shoreline_remediation import ui_components as C, ui_landing, ui_nav  # noqa: E402
from src.shoreline_remediation.site_view import HABITAT_BY_KEY, render_site_evidence, select_site  # noqa: E402
from src.shoreline_remediation.ui_scenario import render_scenario_view  # noqa: E402

LEGACY_WARNING = ("This is the legacy scenario screening and illustrative process model. It is kept for comparison and research "
                  "and does not drive production recommendations.")


def open_site(site_id: str) -> None:
    """Card buttons: switch to the site page and hand the choice to the existing site selection. Unknown ids change nothing."""
    if site_id not in HABITAT_BY_KEY:
        return
    ui_nav.go("site")
    select_site(site_id)


def _back_home() -> None:
    st.button("Back to home", key="sr_nav_home", on_click=ui_nav.go, args=("landing",), icon=":material/arrow_back:")


def main() -> None:
    C.inject_css()
    ui_nav.keep_alive(("site_habitat", "site_mode"))
    page = ui_nav.render_nav()
    if page == "landing":
        ui_landing.render_landing(on_open_site=open_site, on_navigate=ui_nav.go)
    elif page == "site":
        C.section_header("Site assessment", kicker="Decision support", anchor="assessment",
                         description="Real repository data for the selected habitat, compared against natural recovery.")
        _back_home()
        with st.sidebar:
            C.evidence_legend()
        render_site_evidence()
    elif page == "legacy":
        C.section_header("Legacy and research", kicker="Comparison", anchor="legacy",
                         description="Historical scenario screening, kept for comparison and research.")
        _back_home()
        st.warning(LEGACY_WARNING)
        with st.sidebar:
            C.evidence_legend()
        render_scenario_view()
    else:
        ui_landing.render_placeholder(page, ui_nav.go)


main()
