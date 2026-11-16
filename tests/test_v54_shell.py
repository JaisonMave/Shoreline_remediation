"""V5.4 Stages 1 and 2: unified shell and map-first Home. Dashboard wiring only; not scientific validation.

Run from the repository root:  python -m pytest tests/test_v54_shell.py
"""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import map_sites as M, site_view as SV, ui_nav, ui_site_panel  # noqa: E402

PAGE_IDS = ["landing", "site", "evidence", "models", "legacy"]
SHORT_LABELS = ["Map", "Assessment", "Evidence", "Models", "Research"]
FORBIDDEN_INPUTS = re.compile(r"volume|spill age|age of|weather|barrels|gallons|tonnes", re.I)


def new_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def primary_buttons(at: AppTest) -> list:
    return [b for b in at.button if b.proto.type == "primary"]


def test_nav_labels_map_to_unchanged_page_ids():
    assert list(ui_nav.PAGES) == PAGE_IDS
    assert list(ui_nav.PAGES.values()) == SHORT_LABELS
    assert ui_nav.PAGE_KEY == "page" and ui_nav.DEFAULT_PAGE == "landing"
    at = new_app()
    assert at.segmented_control(key="page").options == SHORT_LABELS
    for page in PAGE_IDS:
        at.segmented_control(key="page").set_value(page).run()
        assert not at.exception, (page, at.exception)
        assert at.segmented_control(key="page").value == page


def test_every_page_shows_the_brand_header():
    at = new_app()
    for page in PAGE_IDS:
        at.segmented_control(key="page").set_value(page).run()
        md = " ".join(m.value for m in at.markdown)
        assert "Shoreline Remediation" in md and "Scientific decision support for oil spill response" in md, page


def test_legacy_page_keeps_its_illustrative_warning():
    at = new_app()
    at.segmented_control(key="page").set_value("legacy").run()
    assert any("illustrative process model" in w.value for w in at.warning)


def test_home_renders_map_and_scenario_panel():
    at = new_app()
    assert at.get("deck_gl_json_chart")
    md = " ".join(m.value for m in at.markdown)
    assert "Site and spill scenario" in md
    assert at.selectbox(key="home_habitat").value is None            # nothing selected by default
    run = at.button(key="home_run")
    assert run.disabled                                              # no place and no shoreline type: nothing to run
    assert "In-scope salt-marsh edge cells (ESI 10A), Louisiana, Deepwater Horizon 2010" in md
    assert "Coverage outside these Louisiana basins is not in the repository" in md


def test_exactly_one_primary_button_on_home():
    at = new_app()
    assert [b.key for b in primary_buttons(at)] == ["home_run"]
    at.button(key="home_use_bay_jimmy").click().run()
    assert [b.key for b in primary_buttons(at)] == ["home_run"]
    assert not at.button(key="home_run").disabled


def test_exactly_one_primary_button_on_the_assessment_page():
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    assert [b.key for b in primary_buttons(at)] == ["run_marsh"]


def test_bay_jimmy_panel_shows_record_values():
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    assert at.session_state["home_cell"] == M.EXAMPLE_CELL
    md = " ".join(m.value for m in at.markdown)
    assert "Record values from the site table" in md and M.EXAMPLE_CELL in md and "Barataria" in md
    assert at.selectbox(key="home_habitat").value == "marsh"


def test_run_from_home_for_bay_jimmy_lands_on_site_page_with_a_stored_run():
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.session_state["page"] == "site"
    rec = at.session_state[SV.BOARD_RUN_KEY]
    assert rec["habitat"] == "marsh" and rec["spec"][0] == "site"
    assert M.EXAMPLE_CELL in rec["where"]
    assert at.segmented_control(key="site_habitat").value == "marsh"
    assert at.radio(key="site_mode").value == SV.SITE_MODE_WORKED
    # the Site page recognises it as its own run: no "changed since this run" warning, and the board is drawn
    assert not any("changed since this run" in w.value for w in at.warning)
    assert any("Remediation assessment" in m.value and "Bay Jimmy, Louisiana" in m.value for m in at.markdown)


def test_home_run_equals_the_site_page_run():
    """The Home button stores the record the Site page's own Run button stores for the same place and scenario."""
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    home_rec = dict(at.session_state[SV.BOARD_RUN_KEY])
    at.button(key="run_marsh").click().run()
    assert at.session_state[SV.BOARD_RUN_KEY] == home_rec


def test_other_cell_selected_in_the_panel_runs_that_cell():
    cell = M.cell_layer("barataria").iloc[5]
    at = new_app()
    at.session_state["home_cell"] = cell.cell
    at.run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.session_state["page"] == "site"
    assert at.session_state[SV.BOARD_RUN_KEY]["spec"][0] == "site"
    assert at.selectbox(key="pick_cell").value == cell.cell


def test_unknown_coordinate_creates_no_site_and_offers_screening():
    at = new_app()
    at.number_input(key="map_lat").set_value(25.0)
    at.number_input(key="map_lon").set_value(-90.0).run()
    assert any("No known site at this coordinate" in i.value for i in at.info)
    assert not any(b.key == "map_open_coord" for b in at.button)
    assert "home_cell" not in at.session_state
    assert at.selectbox(key="home_habitat").value is None and at.button(key="home_run").disabled
    # habitat screening for an unknown place: no cell, no in_scope status, generic scenario path
    at.selectbox(key="home_habitat").set_value("marsh").run()
    assert "home_cell" not in at.session_state
    assert any("No model scope status is assigned" in c.value for c in at.caption)
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    rec = at.session_state[SV.BOARD_RUN_KEY]
    assert rec["spec"][0] == "scenario" and rec["flags"] is None and "no site record" in rec["where"]


def test_clear_selection_removes_the_place():
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_clear").click().run()
    assert "home_cell" not in at.session_state
    assert any(b.key == "home_use_bay_jimmy" for b in at.button)


@pytest.mark.parametrize("habitat", ["mangrove", "beach_fine", "esi_1A"])
def test_non_gulf_habitats_are_labelled_not_plotted_and_run(habitat):
    at = new_app()
    at.selectbox(key="home_habitat").set_value(habitat).run()
    assert not at.exception, at.exception
    assert "not plotted" in " ".join(c.value for c in at.caption).lower()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.session_state["page"] == "site" and at.session_state[SV.BOARD_RUN_KEY]["habitat"] == habitat
    assert at.segmented_control(key="site_habitat").value == habitat


def test_no_spill_volume_or_age_inputs_exist():
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    labels = [w.label for group in (at.selectbox, at.number_input, at.slider, at.text_input, at.radio, at.checkbox) for w in group]
    assert labels and not [l for l in labels if FORBIDDEN_INPUTS.search(str(l))], labels


def test_home_panel_never_calls_the_decision_engine_directly():
    src = open(ui_site_panel.__file__, encoding="utf-8").read()
    imports = " ".join(re.findall(r"^(?:from|import) .*$", src, flags=re.M))
    assert "ui_pipeline" not in imports and "decision_pipeline" not in imports      # the board (site_view) is the only caller
    assert "run_decision" not in src


def test_map_view_zooms_to_the_selection_and_stays_bounded():
    row = M.cell_by_id(M.EXAMPLE_CELL)
    v = M.view_for(row)
    assert v["zoom"] > M.LOUISIANA_VIEW["zoom"] and v["latitude"] == row["lat"]
    assert M.view_for(None) == M.LOUISIANA_VIEW and M.view_for({"lat": "x", "lon": 1}) == M.LOUISIANA_VIEW
    assert len(M.cell_layer("barataria")) <= M.LAYER_CAP


def test_map_selected_layer_and_dark_basemap():
    from src.shoreline_remediation import ui_map
    layers = ui_map._layers("barataria", M.cell_by_id(M.EXAMPLE_CELL))
    ids = [l.id for l in layers]
    assert {"cells", "pins", "pin_label", "selected"} <= set(ids)
    assert "selected" not in [l.id for l in ui_map._layers("barataria", None)]
    src = open(ui_map.__file__, encoding="utf-8").read()
    assert 'map_style="dark"' in src
