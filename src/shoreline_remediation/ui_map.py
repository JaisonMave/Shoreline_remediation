"""Gulf map for the Home page (map-first dashboard). Presentation only.

The map draws only rows of data/demo/p5_sites.csv: the Bay Jimmy pin and a bounded sample (at most map_sites.LAYER_CAP per
basin) of in-scope ESI 10A salt-marsh edge cells in three Louisiana basins, coloured by SCAT maximum oiling. Nothing else is drawn:
no shoreline outside these basins, no imagery layers. Basemap: Carto dark tiles through pydeck (no token needed).

Selection: st.pydeck_chart with on_select="rerun" (single object). render_map() returns the id of a cell picked on the map; the
caller (ui_site_panel) decides what a selection means. Clicking open water selects nothing. The coordinate check is the keyboard
alternative; it only matches existing rows (about 50 m) and never creates a site or an in_scope status.
"""
from __future__ import annotations

from html import escape
from typing import Callable

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.shoreline_remediation import map_sites as M, ui_theme as T

STATE_KEYS = ("map_basin", "map_lat", "map_lon")   # not the chart key "map_gulf": Streamlit forbids assigning a selection state
OFF = "Off"
MAP_HEIGHT = 520
NO_DATA = "The site table could not be read, so the map is not available. Use the shoreline type control and the habitat cards below."
SCREENING_ONLY = ("No known site at this coordinate, so no site is created. You can still run habitat screening: choose a "
                  "shoreline type in the scenario panel.")
LEGEND_WHAT = "In-scope salt-marsh edge cells (ESI 10A), Louisiana, Deepwater Horizon 2010"
LEGEND_COVERAGE = ("Coverage outside these Louisiana basins is not in the repository. Other shoreline types are not plotted: "
                   "choose them with the shoreline type control.")


def apply_cell_selection(row: dict | None) -> bool:
    """Write the session keys of the existing site picker for a known cell. Returns False (and changes nothing) when the cell
    cannot be selected there."""
    updates = M.session_updates_for_cell(row or {})
    if not updates:
        return False
    for k, v in updates.items():
        st.session_state[k] = v
    return True


def legend_html() -> str:
    """Plain-language legend of what is drawn. Swatches use the dark-theme oiling colours; each also has its name."""
    items = "".join(f'<span class="sr-leg-item"><i style="background:{T.oiling_colour(o, True)}"></i>{escape(T.OILING_LABELS[o])}</span>'
                    for o in T.OILING_ORDER)
    return ('<div class="sr-map-legend">'
            f'<div class="sr-leg-row"><span class="sr-leg-label">SCAT maximum oiling</span>{items}</div>'
            '<div class="sr-leg-row"><span class="sr-leg-item"><i class="sr-leg-ring"></i>Selected cell</span>'
            '<span class="sr-leg-item"><i class="sr-leg-pin"></i>Bay Jimmy worked example</span></div></div>')


def _layers(basin: str, selected: dict | None) -> list:
    layers = []
    cells = M.cell_layer(basin) if basin != OFF else pd.DataFrame()
    if not cells.empty:
        d = cells.assign(color=cells.max_oiling.map(lambda o: list(T.hex_to_rgb(T.oiling_colour(o, True))) + [215]),
                         oiling=cells.max_oiling.map(lambda o: T.OILING_LABELS.get(o, str(o))))
        layers.append(pdk.Layer("ScatterplotLayer", d[["cell", "lat", "lon", "segment", "oiling", "color"]], id="cells",
                                get_position="[lon, lat]", get_fill_color="color", get_radius=90, radius_min_pixels=3,
                                radius_max_pixels=9, pickable=True, auto_highlight=True))
    pins = M.demonstration_pins()
    if not pins.empty:
        pins = pins.assign(oiling=pins.max_oiling.map(lambda o: T.OILING_LABELS.get(o, str(o))), label="Bay Jimmy, Louisiana")
        layers.append(pdk.Layer("ScatterplotLayer", pins[["cell", "lat", "lon", "segment", "oiling", "name", "label"]], id="pins",
                                get_position="[lon, lat]", get_fill_color=list(T.hex_to_rgb(T.BRAND["dark"])) + [255],
                                get_line_color=[255, 255, 255, 255], stroked=True, line_width_min_pixels=2, get_radius=300,
                                radius_min_pixels=9, pickable=True))
        layers.append(pdk.Layer("TextLayer", pins[["lat", "lon", "label"]], id="pin_label", get_position="[lon, lat]", get_text="label",
                                get_size=14, get_color=[244, 247, 250, 255], get_pixel_offset=[0, -22], get_text_anchor="'middle'",
                                get_alignment_baseline="'bottom'", background=True, get_background_color=[8, 13, 23, 215],
                                background_padding=[6, 3], font_family="'sans-serif'", font_weight=600, pickable=False))
    if selected:
        sel = pd.DataFrame([{"lat": float(selected["lat"]), "lon": float(selected["lon"])}])
        layers.append(pdk.Layer("ScatterplotLayer", sel, id="selected", get_position="[lon, lat]", filled=False, stroked=True,
                                get_line_color=[255, 255, 255, 255], line_width_min_pixels=3, get_radius=200, radius_min_pixels=14,
                                radius_max_pixels=14, pickable=False))
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


def render_map(selected: dict | None, height: int = MAP_HEIGHT) -> str | None:
    """Draw the layer control, the map and its legend. `selected` is the selected cell's row (ringed; the view moves to it).
    Returns the id of the cell picked on the map, or None."""
    try:
        M.load_cells()
    except Exception:
        st.warning(NO_DATA)
        return None
    st.session_state.setdefault("map_basin", M.LAYER_BASINS[0])   # default through state only: keep_alive re-assigns this key
    st.selectbox("Cell layer", [OFF, *M.LAYER_BASINS], key="map_basin",
                 format_func=lambda b: "Off (Bay Jimmy pin only)" if b == OFF else f"Basin: {b.title()} (in-scope salt-marsh cells, sampled)",
                 label_visibility="collapsed")
    deck = pdk.Deck(layers=_layers(st.session_state.get("map_basin", M.LAYER_BASINS[0]), selected),
                    initial_view_state=pdk.ViewState(**M.view_for(selected)), map_style="dark",
                    tooltip={"text": "Cell {cell}\n{segment}\nSCAT oiling: {oiling}"})
    event = st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key="map_gulf", height=height,
                            alt="Dark map of the Louisiana coast showing the Bay Jimmy worked example and sampled salt-marsh edge cells")
    st.markdown(legend_html(), unsafe_allow_html=True)
    return _picked_cell(event)


def coordinate_check(on_select: Callable[[str], None]) -> None:
    """Keyboard alternative to clicking. A known cell (about 50 m) can be selected; an unknown coordinate creates nothing."""
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
        elif M.session_updates_for_cell(row):
            st.caption(f"Known cell {row['cell']} ({str(row['basin']).title()}, segment {row['segment']}).")
            st.button("Select this cell", key="map_open_coord", icon=":material/pin_drop:", on_click=on_select, args=(str(row["cell"]),))
        else:
            st.info("A cell exists here but it is not a Louisiana ESI 10A edge cell, so it cannot be assessed from the site picker. "
                    "Use the shoreline type control for habitat screening.")
