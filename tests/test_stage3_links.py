"""V5.3 Stage 3-4: edge-loss scatter reader, deep-link callbacks, provenance panel, narrow-width structure.

Run from the repository root:  python -m pytest tests/test_stage3_links.py
Presentation and data-reader checks only. They do not validate any model.
"""
import inspect
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import model_validation_data as MV, site_view, ui_decision_board as B, ui_models  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation import ui_pipeline as P  # noqa: E402


# ---- scatter reader -----------------------------------------------------------------------------------------------
def _csv(tmp_path, rows):
    p = tmp_path / "s.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p)
from tests._nav import open_habitat  # noqa: E402


def test_scatter_reader_uses_only_lobo_pred_and_skips_nulls(tmp_path):
    rows = [{"basin": "a", "observed_rate": 1.0, "lobo_pred": 2.0, "p2_heldout_M1": 99.0},
            {"basin": "a", "observed_rate": 0.0, "lobo_pred": 1.0, "p2_heldout_M1": 99.0},
            {"basin": "b", "observed_rate": None, "lobo_pred": 3.0, "p2_heldout_M1": 99.0},
            {"basin": "b", "observed_rate": 2.0, "lobo_pred": None, "p2_heldout_M1": 99.0},
            {"basin": "b", "observed_rate": 4.0, "lobo_pred": 3.0, "p2_heldout_M1": 99.0}]
    res = MV.edge_loss_scatter(_csv(tmp_path, rows))
    assert res["available"] and res["n"] == 3
    assert abs(res["MAE"] - 1.0) < 1e-9                       # |2-1|, |1-0|, |3-4| -> mean 1.0; p2_heldout_M1 (99) ignored
    assert res["n_nonzero_observed"] == 2                     # percentage error only where observed != 0
    assert abs(res["MAPE_pct"] - 62.5) < 1e-9                 # (100% + 25%) / 2
    assert set(res["points"].columns) == {"basin", "observed_rate", "lobo_pred"}
    assert sum(r["n"] for r in res["per_basin"]) == 3


def test_scatter_reader_unavailable_fallback(tmp_path):
    assert MV.edge_loss_scatter("no/such/file.csv")["available"] is False
    assert MV.edge_loss_scatter(_csv(tmp_path, [{"basin": "a", "x": 1}]))["available"] is False
    assert MV.edge_loss_scatter(_csv(tmp_path, [{"basin": "a", "observed_rate": None, "lobo_pred": 1.0}]))["available"] is False


def test_scatter_on_real_file_counts_all_pairs_and_downsamples_only_for_plot():
    res = MV.edge_loss_scatter()
    assert res["available"]
    df = pd.read_csv(ROOT / "data/demo/p5_sites.csv")
    assert res["n"] == int(df[["observed_rate", "lobo_pred"]].notna().all(axis=1).sum())
    assert res["n_plotted"] <= MV.SCATTER_MAX_POINTS and len(res["points"]) == res["n_plotted"]
    assert res["axis_min"] <= 0


def test_scatter_code_never_references_p2_heldout_or_v2_intervals():
    src = inspect.getsource(MV.edge_loss_scatter) + inspect.getsource(ui_models._scatter_block)
    assert "p2_heldout" not in src and "edge_loss_v2" not in src


def test_scatter_caption_states_required_scope():
    c = MV.SCATTER_CAPTION
    for phrase in ("leave-one-basin-out (trained on the other two basins)", "m/yr", "one spill", "northern Gulf salt marsh",
                   "Terrebonne", "not a P2 gate basin", "all-cells refit", "NOT what is plotted"):
        assert phrase in c, phrase


# ---- deep links ---------------------------------------------------------------------------------------------------
def test_open_model_sets_exactly_mv_model_and_page():
    st.session_state.clear()
    B.open_model("edge_loss_v1")
    assert st.session_state["mv_model"] == "edge_loss_v1" and st.session_state["page"] == "models"
    assert set(st.session_state.keys()) == {"mv_model", "page"}


def test_open_evidence_sets_class_esi_option_and_page():
    st.session_state.clear()
    B.open_evidence("salt marsh", "10A", ("in_situ_burning",))
    assert set(st.session_state.keys()) == {"ev_classes", "ev_esi", "ev_options", "page"}
    assert st.session_state["page"] == "evidence"
    assert st.session_state["ev_classes"] == ["marsh"] and st.session_state["ev_esi"] == ["10A"]
    assert st.session_state["ev_options"] == ["In-situ burning"]               # code resolved to the catalogue display name


def test_open_evidence_drops_values_the_catalogue_does_not_offer():
    st.session_state.clear()
    B.open_evidence("mangrove", None, ("not_a_real_option",))
    assert st.session_state["ev_classes"] == ["mangrove"] and st.session_state["ev_esi"] == [] and st.session_state["ev_options"] == []


def _report(shoreline_type, habitat, oiling="Moderate"):
    scen = Scenario(shoreline_type=shoreline_type, wave_exposure="moderate", oil_category="medium")
    r, err = P.decision_for_scenario(P.scenario_items(scen), oiling, "medium", None, habitat, 200)
    assert err is None, err
    return r


def test_referenced_model_only_for_linkable_models():
    assert B.referenced_model(_report("rocky_shore", "1A")) is None
    assert B.referenced_model(_report("salt_marsh", "salt_marsh")) in (None, *B.LINKABLE_MODELS)


def _open(key):
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    open_habitat(at, f"{key}")
    assert not at.exception, at.exception
    return at


def _text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])


def test_rocky_board_has_statement_not_a_model_button():
    at = _open("hab_esi_1a")
    at.button(key="run_esi_1A").click().run()
    assert not at.exception, at.exception
    assert not any(b.key and b.key.startswith("how_") for b in at.button)
    assert B.NO_FORECAST_TEXT in _text(at)
    assert any(b.key == "whyboard_esi_1A" for b in at.button)


def test_marsh_board_links_work_in_the_app():
    at = _open("marsh")
    at.button(key="run_marsh").click().run()
    assert not at.exception, at.exception
    how = [b for b in at.button if b.key == "how_marsh"]
    if how:
        how[0].click().run()
        assert at.session_state["page"] == "models" and at.session_state["mv_model"] in B.LINKABLE_MODELS
        assert not at.exception, at.exception
    at = _open("marsh")
    at.button(key="run_marsh").click().run()
    at.button(key="whyboard_marsh").click().run()
    assert not at.exception, at.exception
    assert at.session_state["page"] == "evidence" and at.session_state["ev_classes"] == ["marsh"]


def test_provenance_panel_present_collapsed_and_isolated():
    at = _open("marsh")
    assert any(e.label == "Provenance of the literature priors" for e in at.expander)     # shown even before Run
    src = inspect.getsource(site_view._provenance_panel)
    assert "process_model" not in src and "process_uncertainty" not in src
    assert "literature_priors" in src


def test_decision_board_module_does_not_import_process_models():
    src = inspect.getsource(B)
    assert not re.search(r"^\s*(from|import)\s+.*process_(model|uncertainty)", src, flags=re.M)


# ---- narrow-width structure (no browser) ---------------------------------------------------------------------------
def test_no_fixed_width_tables_or_charts_in_new_ui_modules():
    for name in ("ui_models.py", "ui_decision_board.py", "ui_map.py"):
        text = (ROOT / "src" / "shoreline_remediation" / name).read_text(encoding="utf-8")
        for m in re.finditer(r"st\.(dataframe|altair_chart|table)\(.*", text):
            assert "width=" not in m.group(0) or 'width="stretch"' in m.group(0), (name, m.group(0))
        assert not re.search(r"width=\d{3,}", text), name
