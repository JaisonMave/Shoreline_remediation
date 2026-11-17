"""Landing page and placeholder pages (V5.1 Session 2 Stage 3). Presentation only: data comes from site_view, nothing is
computed here, and no value on this page is a recommendation or a prediction."""
from __future__ import annotations

from typing import Callable

from html import escape

import streamlit as st

from src.shoreline_remediation import ui_components as C, ui_map, ui_site_panel, ui_theme as T
from src.shoreline_remediation.site_view import habitat_coverage

COVERAGE_LINE = "Mapped sites are historical Louisiana salt-marsh cells (Deepwater Horizon, 2010)."
COVERAGE_TITLE = "Geographic and habitat coverage"
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


def coverage_rows() -> list:
    """(habitat, ESI, coverage, what exists) for the collapsed coverage section, from site_view.habitat_coverage()."""
    return [{"Shoreline type": c.label, "ESI": c.esi or "-", "Coverage": T.COVERAGE_TIERS[c.tier]["label"], "What exists": c.summary}
            for c in _safe(habitat_coverage)]


def render_landing(on_open_site: Callable, on_navigate: Callable) -> None:
    """Map page: the map, the place and scenario panel with the one Run button, one coverage line and one collapsed coverage
    section. `on_open_site` and `on_navigate` are kept for the caller's signature; the panel's Run button is the only way in."""
    line, legend_btn = st.columns([6, 1.4], vertical_alignment="center")
    line.markdown(f'<p class="sr-coverline">{escape(COVERAGE_LINE)}</p>', unsafe_allow_html=True)
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

    with st.expander(COVERAGE_TITLE, icon=":material/public:"):
        st.markdown(f"{ui_map.LEGEND_WHAT}: a sample of at most {ui_map.M.LAYER_CAP:,} cells per basin (Terrebonne, Barataria, Breton). "
                    f"{ui_map.LEGEND_COVERAGE}")
        rows = coverage_rows()
        if rows:
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.caption(NO_DATA)
        st.caption("One spill per dataset. Field comparisons are associations, not proven causes.")
