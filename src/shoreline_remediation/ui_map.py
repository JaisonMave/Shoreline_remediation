"""Gulf of Mexico map for the Home page (Stage 1 of the map-first dashboard). Presentation only.

Selection mechanism: st.pydeck_chart with on_select="rerun" (single-object). A pick fills a details panel and an explicit
"Open this site" button; the button writes the same session keys as site_view.select_site("marsh") and the existing
'Pick a Louisiana edge cell' picker, then navigates to the Site assessment page. The select boxes and habitat cards stay
available as keyboard-accessible alternatives and remain the source of truth for the cell id.
Clicking open water selects nothing (deck.gl only reports picked objects), so a coordinate check is offered; it matches
existing p5 rows only and never creates a site or an in_scope status.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.shoreline_remediation import map_sites as M, ui_components as C, ui_theme as T

STATE_KEYS = ("map_basin", "map_lat", "map_lon")   # not the chart key "map_gulf": Streamlit forbids assigning a selection state
OFF = "Off"
NO_DATA = "The site table could not be read, so the map is not available. Use the habitat cards below."
SCREENING_ONLY = ("No known site at this coordinate. The map only shows cells that exist in the Louisiana site table, so no site "
                  "is created here. For this kind of shoreline you can run habitat screening only: pick an ESI habitat in "
                  "the habitat cards below.")


def apply_cell_selection(row: dict | None) -> bool:
    """Write the session keys for a known cell. Returns False (and changes nothing) when the cell cannot be selected."""
    updates = M.session_updates_for_cell(row or {})
    if not updates:
        return False
    for k, v in updates.items():
        st.session_state[k] = v
    return True


def open_cell(cell_id: str, on_navigate: Callable) -> None:
    """Button callback: select the cell, then go to the Site assessment page. Unknown ids change nothing."""
    if apply_cell_selection(M.cell_by_id(cell_id)):
        on_navigate("site")


def _layers(basin: str, dark: bool) -> list:
    layers = []
    cells = M.cell_layer(basin) if basin != OFF else pd.DataFrame()
    if not cells.empty:
        d = cells.assign(color=cells.max_oiling.map(lambda o: list(T.hex_to_rgb(T.oiling_colour(o, dark))) + [190]),
                         oiling=cells.max_oiling.map(lambda o: T.OILING_LABELS.get(o, str(o))))
        layers.append(pdk.Layer("ScatterplotLayer", d[["cell", "lat", "lon", "segment", "oiling", "color"]], id="cells",
                                get_position="[lon, lat]", get_fill_color="color", get_radius=120, radius_min_pixels=3,
                                pickable=True, auto_highlight=True))
    pins = M.demonstration_pins()
    if not pins.empty:
        pins = pins.assign(oiling=pins.max_oiling.map(lambda o: T.OILING_LABELS.get(o, str(o))))
        layers.append(pdk.Layer("ScatterplotLayer", pins[["cell", "lat", "lon", "segment", "oiling", "name"]], id="pins",
                                get_position="[lon, lat]", get_fill_color=list(T.hex_to_rgb(T.BRAND["dark"])) + [255],
                                get_line_color=[255, 255, 255, 255], stroked=True, line_width_min_pixels=2, get_radius=300,
                                radius_min_pixels=9, pickable=True))
    return layers


def _picked_cell(event) -> str | None:
    try:
        objs = event.selection.objects
    except Exception:
        return None
    for layer in ("pins", "cells"):
        for o in (objs.get(layer) or []):
            if isinstance(o, dict) and o.get("cell"):
                return str(o["cell"])
    return None


def _details(row: dict, key: str, on_navigate: Callable) -> None:
    where = f"Cell {row['cell']} | {str(row['basin']).title()} | segment {row['segment']}"
    oiling = T.OILING_LABELS.get(row.get("max_oiling"), "not recorded")
    status = "in scope for the edge-loss model" if row.get("status") == "in_scope" else f"not in scope ({row.get('status')})"
    with st.container(border=True):
        st.markdown(f"**{where}**")
        st.caption(f"ESI {row['esi_main']} | SCAT maximum oiling: {oiling} | Model scope status from the site table: {status}")
        if M.session_updates_for_cell(row):
            st.button("Open this site", key=f"map_open_{key}", icon=":material/arrow_forward:", on_click=open_cell,
                      args=(str(row["cell"]), on_navigate))
        else:
            st.caption("This cell cannot be opened in the site picker (not a Louisiana ESI 10A edge cell). Use the habitat cards below.")


def _coordinate_check(on_navigate: Callable) -> None:
    with st.expander("Check a coordinate (keyboard alternative to clicking the map)"):
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", -90.0, 90.0, value=None, step=0.0001, format="%.5f", key="map_lat")
        lon = c2.number_input("Longitude", -180.0, 180.0, value=None, step=0.0001, format="%.5f", key="map_lon")
        if lat is None or lon is None:
            st.caption("Enter both values. Only coordinates that match a cell in the site table (about 50 m) are accepted.")
            return
        row = M.lookup_cell(lat, lon)
        if row is None:
            st.info(SCREENING_ONLY)
        else:
            _details(row, "coord", on_navigate)


def render_gulf_map(on_navigate: Callable) -> None:
    C.section_header("Gulf of Mexico site map", kicker="Map", anchor="site-map",
                     description="Select a known demonstration site. Pins are real records of the Louisiana site table; "
                                 "the habitat cards below remain a full alternative.",
                     meta="Source: data/demo/p5_sites.csv (SCAT edge cells, Deepwater Horizon 2010)")
    try:
        M.load_cells()
    except Exception:
        st.warning(NO_DATA)
        return
    dark = C.is_dark()
    st.selectbox("Cell layer", [OFF, *M.LAYER_BASINS], index=1, key="map_basin",
                 format_func=lambda b: "Off (pins only)" if b == OFF else f"In-scope salt-marsh cells: {b.title()} (sampled, at most {M.LAYER_CAP})")
    deck = pdk.Deck(layers=_layers(st.session_state.get("map_basin", M.LAYER_BASINS[0]), dark),
                    initial_view_state=pdk.ViewState(**M.GULF_VIEW), map_style="dark" if dark else "light",
                    tooltip={"text": "Cell {cell}\n{segment}\nSCAT oiling: {oiling}"})
    event = st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key="map_gulf", height=460,
                            alt="Map of the Gulf of Mexico with the Bay Jimmy worked example and sampled Louisiana salt-marsh edge cells")
    st.caption("Large teal pin: Bay Jimmy worked example. Small dots: sampled in-scope salt-marsh edge cells, coloured by SCAT maximum oiling.")
    picked = _picked_cell(event)
    if picked:
        row = M.cell_by_id(picked)
        if row:
            _details(row, "pick", on_navigate)
    else:
        st.caption("Click a pin or dot to see the cell. Clicking open water selects nothing and creates no site.")
    _coordinate_check(on_navigate)
    with st.expander("Habitat demonstrations without a Gulf location"):
        for _, label, note in M.HABITAT_DEMOS:
            st.markdown(f"**{label}.** {note}")
        st.caption("Open these with the habitat cards below.")
