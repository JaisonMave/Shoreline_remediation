"""Shoreline Remediation Decision Support: Streamlit entry point (decision D40).

Run: streamlit run src/shoreline_remediation/dashboard.py
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
from src.shoreline_remediation.site_view import render_site_evidence  # noqa: E402
from src.shoreline_remediation.ui_scenario import render_scenario_view  # noqa: E402

VIEW_SITE = "Site evidence"
VIEW_SCENARIO = "Scenario screening (legacy)"


def main() -> None:
    C.inject_css()
    C.hero("What happens to the shoreline after an oil spill, and what do cleanup options change? Every number comes with its "
           "range and a label saying how well it is supported.",
           [("Louisiana salt marsh worked example", "green"), ("One spill", "gray"), ("Associations, not causes", "orange")])
    with st.sidebar:
        C.evidence_legend()
    view = st.segmented_control("View", [VIEW_SITE, VIEW_SCENARIO], default=VIEW_SITE, required=True, key="top_view",
                                label_visibility="collapsed")
    if view == VIEW_SCENARIO:
        render_scenario_view()
    else:
        render_site_evidence()


main()
