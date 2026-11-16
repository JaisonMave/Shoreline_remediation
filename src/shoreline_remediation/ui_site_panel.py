"""The "Site and spill scenario" panel beside the Home map (map-first dashboard). Presentation and session wiring only.

What it does: shows the place selected on the map (or none), the record values of that cell, and the scenario inputs the decision
pipeline really reads (shoreline type, oil category, oiling class, optional season, named oil and wave exposure). The single
primary button stores the same run record the Site page's Run button stores (site_view.store_run, built by the
site_view.*_run_request functions) and opens the Assessment page, where ui_pipeline runs. This module never calls the pipeline.

A place is only ever a row of the site table. With no selected cell the panel does habitat screening only: it creates no site and
assigns no model scope status. Controls shown here reuse the Site page's widget keys, so the two pages stay in step.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from src.shoreline_remediation import map_sites as M, site_view as SV, ui_map, ui_nav, ui_theme as T

HOME_CELL = "home_cell"
HOME_HABITAT = "home_habitat"
HOME_MAP_SEEN = "home_map_seen"
STATE_KEYS = (HOME_CELL, HOME_HABITAT, HOME_MAP_SEEN)
NEW_SITE_MODE = "New site (enter values)"        # site_view._pick_site's third mode: the generic, record-less place
NOT_PLOTTED = "Not plotted on the map: habitat-level screening entry, no site record."
RUN_HELP = ("Runs the same decision pipeline as the Assessment page and opens it. The answer can be that evidence is insufficient "
            "or that natural recovery stays the reference.")
MANGROVE_NOTE = ("Bahía Las Minas, Panama (limited evidence: one field study of one 1986 spill, oiling damage only). Not plotted on "
                 "the map. The platform may abstain from a cleanup forecast.")


def select_cell(cell_id: str) -> None:
    """Callback: make a known cell the selected place. Unknown or unselectable cells change nothing."""
    row = M.cell_by_id(cell_id)
    if row and M.session_updates_for_cell(row):
        st.session_state[HOME_CELL] = str(cell_id)
        st.session_state[HOME_HABITAT] = "marsh"


def clear_selection() -> None:
    st.session_state.pop(HOME_CELL, None)


def selected_row() -> dict | None:
    """Row of the selected cell, or None (nothing selected, or the cell is no longer in the table)."""
    cell = st.session_state.get(HOME_CELL)
    return M.cell_by_id(cell) if cell else None


def handle_map_pick(picked: str | None) -> bool:
    """Apply a map click once. Returns True when the selection changed (the caller reruns to move the ring and the view)."""
    if not picked or picked == st.session_state.get(HOME_MAP_SEEN):
        return False
    st.session_state[HOME_MAP_SEEN] = picked
    before = st.session_state.get(HOME_CELL)
    select_cell(picked)
    return st.session_state.get(HOME_CELL) != before


def run_and_open(req: dict, updates: dict) -> None:
    """Callback of the primary button: point the Site page at this place, store the run record, go to the Assessment page."""
    for k, v in updates.items():
        st.session_state[k] = v
    st.session_state["site_habitat"] = req["habitat"]
    SV.store_run(req)
    ui_nav.go("site")


def _place_block(row: dict | None) -> None:
    if row is None:
        st.caption("No place selected. Click a cell or the Bay Jimmy pin on the map, or start from the worked example.")
        st.button("Use Bay Jimmy (worked example)", key="home_use_bay_jimmy", icon=":material/pin_drop:", on_click=select_cell,
                  args=(M.EXAMPLE_CELL,), width="stretch")
        return
    is_example = row["cell"] == M.EXAMPLE_CELL
    status = "in scope for the edge-loss model" if row.get("status") == "in_scope" else f"not in scope ({row.get('status')})"
    facts = [("Cell", row["cell"]), ("Basin", str(row["basin"]).title()), ("SCAT segment", row["segment"]),
             ("Shoreline (ESI)", row["esi_main"]), ("SCAT maximum oiling", T.OILING_LABELS.get(row.get("max_oiling"), "not recorded")),
             ("Model scope status", status)]
    dl = "".join(f"<div><dt>{escape(k)}</dt><dd>{escape(str(v))}</dd></div>" for k, v in facts)
    title = "Bay Jimmy, Louisiana" if is_example else f"Cell {row['cell']}"
    st.markdown(f'<div class="sr-place"><div class="sr-place-name">{escape(title)}</div>'
                f'<div class="sr-place-src">Record values from the site table (not predictions)</div><dl>{dl}</dl></div>',
                unsafe_allow_html=True)
    st.button("Clear selection", key="home_clear", icon=":material/close:", on_click=clear_selection, type="tertiary")


def _habitat_label(key: str) -> str:
    h = SV.HABITAT_BY_KEY[key]
    if key == "marsh":
        return "Salt marsh (ESI 10A)"
    if key == "mangrove":
        return "Mangrove (Panama, not plotted)"
    return f"{h.label} (not plotted)"


def render_panel() -> None:
    row = selected_row()
    with st.container(key="sr_panel", border=True):
        st.markdown('<div class="sr-panel-title">Site and spill scenario</div>', unsafe_allow_html=True)
        _place_block(row)
        if row is not None:
            st.session_state[HOME_HABITAT] = "marsh"      # a Louisiana cell is a salt-marsh cell
        habitat = st.selectbox("Shoreline type", list(SV.HABITAT_BY_KEY), index=None, key=HOME_HABITAT, disabled=row is not None,
                               placeholder="Choose a shoreline type", format_func=_habitat_label,
                               help="Habitat screening works for every type. Only the Louisiana salt marsh has site records and a model.")
        req, updates, note = None, {}, ""
        if habitat is None:
            st.caption("Select a place on the map, or choose a shoreline type, to set the scenario.")
        elif habitat == "marsh":
            oiling = row.get("max_oiling") if row else None
            from_record = oiling if oiling in SV.CLASSES else None
            sv = SV.scenario_form("marsh", oiling_from_record=from_record, ask_oiling=from_record is None,
                                  default_oiling=oiling if oiling in SV.CLASSES else "Moderate", stacked=True)
            if row is not None:
                site = SV.site_for_cell(row["cell"])
                if site is not None:
                    req = SV.marsh_run_request(site, sv)
                    updates = M.session_updates_for_cell(row)
                else:
                    note = "This cell is not in the site table used by the Assessment page, so it cannot be run."
            else:
                site = {"esi_main": "10A", "max_oiling": sv.oiling, "source": "new site", "cell": "new site", "segment": "-",
                        "basin": "no site", "place_label": "no site record (habitat screening)"}
                req = SV.marsh_run_request(site, sv)
                updates = {"site_mode": NEW_SITE_MODE, "new_oil": sv.oiling}
                note = "No site record: habitat screening only. No model scope status is assigned to an unknown location."
        elif habitat == "mangrove":
            req = SV.mangrove_run_request()
            note = MANGROVE_NOTE
        else:
            h = SV.HABITAT_BY_KEY[habitat]
            sv = SV.scenario_form(habitat, ask_exposure=True, default_oil="medium", stacked=True)
            req = SV.screening_run_request(h, sv)
            note = f"{NOT_PLOTTED} Rules and literature only; there is no numerical forecast for this shoreline type."
        if note:
            st.caption(note)
        st.button("Run assessment", key="home_run", type="primary", icon=":material/play_arrow:", width="stretch",
                  disabled=req is None, on_click=run_and_open, args=(req or {}, updates))
        st.caption(RUN_HELP if req else "Run is available once a place or a shoreline type is chosen.")
