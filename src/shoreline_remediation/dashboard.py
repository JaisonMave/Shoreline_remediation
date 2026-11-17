"""Shoreline Remediation Decision Support: Streamlit entry point (decision D40).

Run: streamlit run src/shoreline_remediation/dashboard.py
Pages (ui_nav.PAGES; short labels Map, Assessment, Evidence, Models, Research): Home (landing: map, site and spill scenario panel, one collapsed coverage section), Site assessment (real data, habitat switcher,
decision pipeline), Evidence explorer and Model validation (V5.2: ui_evidence_explorer, ui_models), Legacy and research (legacy rule
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

from src.shoreline_remediation import ui_components as C, ui_evidence_explorer, ui_landing, ui_map, ui_models, ui_nav, ui_site_panel  # noqa: E402
from src.shoreline_remediation.site_view import HABITAT_BY_KEY, render_site_evidence, scenario_state_keys, select_site  # noqa: E402
from src.shoreline_remediation.ui_scenario import render_scenario_view  # noqa: E402

LEGACY_WARNING = ("This is the legacy scenario screening and illustrative process model. It is kept for comparison and research "
                  "and does not drive production recommendations.")


SITE_PICKER_KEYS = ("pick_basin", "pick_oil", "pick_scope", "pick_seg", "pick_cell", "new_oil")  # site_view's cell picker; kept across pages


def open_site(site_id: str) -> None:
    """Card buttons: switch to the site page and hand the choice to the existing site selection. Unknown ids change nothing."""
    if site_id not in HABITAT_BY_KEY:
        return
    ui_nav.go("site")
    select_site(site_id)


def _back_home() -> None:
    st.button("Back to home", key="sr_nav_home", on_click=ui_nav.go, args=("landing",), icon=":material/arrow_back:", type="tertiary")


def main() -> None:
    C.inject_css()
    ui_nav.keep_alive(("site_habitat", "site_mode") + SITE_PICKER_KEYS + ui_map.STATE_KEYS + ui_site_panel.STATE_KEYS + scenario_state_keys() + ui_evidence_explorer.STATE_KEYS
                      + ui_models.STATE_KEYS)
    page = ui_nav.render_nav()
    if page == "landing":
        ui_landing.render_landing(on_open_site=open_site, on_navigate=ui_nav.go)
    elif page == "site":
        st.markdown('<div id="assessment"></div>', unsafe_allow_html=True)
        with st.sidebar:
            C.evidence_legend()
        render_site_evidence(lead=_back_home)
    elif page == "legacy":
        C.section_header("Legacy and research", kicker="Comparison", anchor="legacy",
                         description="Historical scenario screening, kept for comparison and research.")
        _back_home()
        st.warning(LEGACY_WARNING)
        with st.sidebar:
            C.evidence_legend()
        render_scenario_view()
    elif page == "evidence":
        _back_home()
        with st.sidebar:
            C.evidence_legend()
        ui_evidence_explorer.render_evidence()
    elif page == "models":
        _back_home()
        with st.sidebar:
            C.evidence_legend()
        ui_models.render_models()
    else:
        ui_landing.render_placeholder(page, ui_nav.go)


main()
