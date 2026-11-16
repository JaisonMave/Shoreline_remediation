"""Gulf map (Stage 1 of the map-first dashboard): data layer, session-key mapping and the Home page widget.

Run from the repository root:  python -m pytest tests/test_map_sites.py
Dashboard and data-access checks only; not scientific validation.
"""
import sys
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import map_sites as M, site_view as SV, ui_map  # noqa: E402


@pytest.fixture(scope="module")
def cells():
    return M.load_cells()


def test_constants_match_site_view():
    assert M.EXAMPLE_CELL == SV.EXAMPLE_CELL
    assert M.SITE_MODE_WORKED == SV.SITE_MODE_WORKED
    assert M.PICKER_BASINS == tuple(SV.BASINS)


def test_pins_contain_bay_jimmy_only(cells):
    pins = M.demonstration_pins(cells)
    assert list(pins.cell) == [M.EXAMPLE_CELL]
    assert abs(pins.lat.iloc[0] - 29.4) < 1 and pins.lon.iloc[0] < -88


def test_habitat_demos_are_not_plotted_points():
    keys = {k for k, _, _ in M.HABITAT_DEMOS}
    assert {"beach_fine", "esi_1A", "esi_8A", "mangrove"} == keys
    assert all(k in SV.HABITAT_BY_KEY for k in keys)
    assert "Panama" in dict((k, l) for k, l, _ in M.HABITAT_DEMOS)["mangrove"]


@pytest.mark.parametrize("basin", M.LAYER_BASINS)
def test_layer_is_bounded_and_in_scope_10a(cells, basin):
    d = M.cell_layer(basin, cells=cells)
    assert 0 < len(d) <= M.LAYER_CAP < len(cells)
    assert set(d.status) == {"in_scope"} and set(d.esi_main) == {"10A"} and set(d.basin) == {basin}
    assert len(M.cell_layer(basin, cap=10**9, cells=cells)) <= M.LAYER_CAP


def test_layer_unknown_basin_is_empty(cells):
    assert M.cell_layer(None, cells=cells).empty and M.cell_layer("mars", cells=cells).empty


def test_lookup_known_and_unknown(cells):
    r = cells[cells.cell == M.EXAMPLE_CELL].iloc[0]
    assert M.lookup_cell(r.lat, r.lon, cells=cells)["cell"] == M.EXAMPLE_CELL
    assert M.lookup_cell(25.0, -90.0, cells=cells) is None            # open Gulf water
    assert M.lookup_cell(r.lat + 0.5, r.lon, cells=cells) is None
    assert M.lookup_cell("x", None, cells=cells) is None and M.lookup_cell(float("nan"), 1, cells=cells) is None


def test_lookup_never_invents_status(cells):
    for _, r in cells.sample(200, random_state=1).iterrows():
        hit = M.lookup_cell(r.lat, r.lon, cells=cells)
        assert hit is not None and hit["status"] == r.status
    assert M.lookup_cell(0.0, 0.0, cells=cells) is None


def test_example_selection_equals_select_site_marsh(monkeypatch):
    monkeypatch.setattr(st, "session_state", {})
    SV.select_site("marsh")
    expected = dict(st.session_state)
    monkeypatch.setattr(st, "session_state", {})
    assert ui_map.apply_cell_selection(M.cell_by_id(M.EXAMPLE_CELL))
    assert dict(st.session_state) == expected


def test_other_cell_fills_picker_keys(cells, monkeypatch):
    row = M.cell_layer("barataria", cells=cells).iloc[5].to_dict()
    monkeypatch.setattr(st, "session_state", {})
    assert ui_map.apply_cell_selection(row)
    s = st.session_state
    assert s["site_habitat"] == "marsh" and s["site_mode"] == "Pick a Louisiana edge cell"
    assert (s["pick_basin"], s["pick_seg"], s["pick_cell"], s["pick_oil"], s["pick_scope"]) == (
        row["basin"], row["segment"], row["cell"], "any", True)


def test_unselectable_rows_change_nothing(monkeypatch):
    monkeypatch.setattr(st, "session_state", {})
    assert not ui_map.apply_cell_selection(None)
    assert not ui_map.apply_cell_selection({"cell": "x", "esi_main": "1A", "basin": "barataria", "segment": "s"})
    assert dict(st.session_state) == {}


def test_home_renders_map_and_existing_cards():
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    assert at.get("deck_gl_json_chart"), "map widget missing on Home"
    assert at.selectbox(key="map_basin").value == "barataria"
    assert any("Open the Bay Jimmy assessment" in b.label for b in at.button)
    assert any(b.key == "home_run" and b.label == "Run assessment" for b in at.button)   # V5.4: the scenario panel replaced the hero


def test_coordinate_check_open_water_creates_no_site():
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.number_input(key="map_lat").set_value(25.0)
    at.number_input(key="map_lon").set_value(-90.0).run()
    assert not at.exception, at.exception
    assert any("No known site at this coordinate" in i.value for i in at.info)
    assert not any(b.key == "map_open_coord" for b in at.button)
    assert at.session_state["page"] == "landing"


def test_coordinate_check_known_cell_opens_site_page():
    cell = M.cell_layer("barataria").iloc[3]
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.number_input(key="map_lat").set_value(float(cell.lat))
    at.number_input(key="map_lon").set_value(float(cell.lon)).run()
    at.button(key="map_open_coord").click().run()          # V5.4: selects the cell in the panel; Run then opens the Assessment page
    assert not at.exception, at.exception
    assert at.session_state["page"] == "landing" and at.session_state["home_cell"] == cell.cell
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.session_state["page"] == "site"
    assert at.selectbox(key="pick_cell").value == cell.cell


def test_other_pages_still_load():
    for p in ("evidence", "models", "legacy"):
        at = AppTest.from_file(APP, default_timeout=300)
        at.run()
        at.segmented_control(key="page").set_value(p).run()
        assert not at.exception, (p, at.exception)
        if p == "legacy":
            assert any("illustrative process model" in w.value for w in at.warning)
