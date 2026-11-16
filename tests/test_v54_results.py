"""V5.4 Stages 3 to 5: the single results view on the Assessment page. Dashboard wiring only; not scientific validation.

Run from the repository root:  python -m pytest tests/test_v54_results.py
"""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import map_sites as M, site_view as SV, ui_decision_board as B, ui_pipeline as P, ui_results as R  # noqa: E402
from src.shoreline_remediation.decision_pipeline import CATEGORY_LABELS  # noqa: E402


def new_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def run_habitat(key: str) -> AppTest:
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    at.segmented_control(key="site_habitat").set_value(key).run()
    at.button(key=f"run_{key}").click().run()
    assert not at.exception, at.exception
    return at


def run_bay_jimmy() -> AppTest:
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    return at


def text(at: AppTest) -> str:
    raw = " ".join(str(e.value) for g in (at.markdown, at.caption, at.info, at.warning, at.error, at.subheader) for e in g)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", raw, flags=re.S)))


def outcome_html(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown if "sr-oc-title" in m.value)


def report_of(at: AppTest):
    rec = at.session_state[SV.BOARD_RUN_KEY]
    report, err = P.decision_for_site(*rec["spec"][1:]) if rec["spec"][0] == "site" else P.decision_for_scenario(*rec["spec"][1:])
    assert err is None
    return report


def top_options(report) -> tuple:
    m = B.board_model(report)
    card = R.top_card(m)
    return card.category, card.options


def primary(at: AppTest) -> list:
    return [b.key for b in at.button if b.proto.type == "primary"]


# ---- primary card equals the report -------------------------------------------------------------------------------

def test_bay_jimmy_primary_card_is_the_reports_outcome_and_top_category():
    at = run_bay_jimmy()
    report = report_of(at)
    html = outcome_html(at)
    assert report.decision_outcome_label in html
    cat, options = top_options(report)
    assert cat == "recommended" and options == ["manual_removal"]
    assert "Manual removal" in html or any("Manual removal" in m.value for m in at.markdown if "sr-oc-opt" in m.value)
    assert any(CATEGORY_LABELS[cat] in m.value for m in at.markdown if "sr-status" in m.value)


def test_rocky_1a_primary_card_is_conditional_not_recommended():
    at = run_habitat("esi_1A")
    report = report_of(at)
    assert report.decision_outcome_label in outcome_html(at)
    cat, options = top_options(report)
    assert cat == "conditional" and report.decision_outcome == "conditional_only" and options
    card = " ".join(m.value for m in at.markdown if "sr-oc" in m.value or "sr-status" in m.value)
    assert CATEGORY_LABELS["conditional"] in card and "Recommended<" not in card
    assert "No intervention is recommended outright" in outcome_html(at)


@pytest.mark.parametrize("key", ["esi_8A", "mangrove"])
def test_abstaining_habitats_name_natural_recovery_as_the_reference(key):
    at = run_habitat(key)
    report = report_of(at)
    html = outcome_html(at)
    assert report.decision_outcome_label in html and "Abstention" in html           # equal-prominence abstention pill
    cat, options = top_options(report)
    assert cat == "natural_recovery_monitoring" and options == ["natural_attenuation"]
    assert "reference every intervention is compared with" in text(at)
    card = " ".join(m.value for m in at.markdown if "sr-oc" in m.value or "sr-status" in m.value).lower()
    assert "best" not in card and "recommended<" not in card


def test_mangrove_primary_card_matches_the_report():
    at = run_habitat("mangrove")
    report = report_of(at)
    assert report.decision_outcome_label in outcome_html(at)
    assert not report.recommendation_summary.get("recommended")


def test_unsupported_habitat_abstention_has_no_technology_cards():
    from src.shoreline_remediation.data_model import Scenario
    report, err = P.decision_for_scenario(P.scenario_items(Scenario(shoreline_type="coral_reef")), None, None, None, "coral reef")
    assert err is None and report.scope_tier in ("unsupported_habitat", "out_of_scope")
    m = B.board_model(report)
    assert m.refused and m.cards == [] and R.top_card(m) is None
    assert R.OUTCOME_PILL[m.outcome][0] == "abstain" and "valid outcome" in R.OUTCOME_PILL[m.outcome][1]


def test_unsupported_habitat_render_via_app_shows_message_and_no_cards():
    from src.shoreline_remediation.data_model import Scenario
    report, _ = P.decision_for_scenario(P.scenario_items(Scenario(shoreline_type="coral_reef")), None, None, None, "coral reef")
    rec = SV.run_request("marsh", ("scenario",), "x", None, None, "marsh", crumb={"place": "p", "shoreline": "s", "oil": "o", "oiling": "i"})

    def app():
        import streamlit as st
        from src.shoreline_remediation import ui_results as RR
        RR.render_results(st.session_state["_r"], st.session_state["_rec"], {"key": "marsh", "habitat": "x", "esi": None})

    at = AppTest.from_function(app, default_timeout=120)
    at.session_state["_r"], at.session_state["_rec"] = report, rec
    at.run()
    assert not at.exception, at.exception
    html = outcome_html(at)
    assert report.decision_outcome_label in html and "Abstention" in html
    assert B.NO_ASSESSMENT_TEXT in text(at)
    assert not any("sr-alt-opt" in m.value for m in at.markdown)


# ---- groups ---------------------------------------------------------------------------------------------------------

def test_natural_recovery_never_called_recommended_or_best_when_it_is_the_reference():
    at = run_habitat("esi_1A")
    t = text(at).lower()
    assert "natural recovery with monitoring (reference option)" in t
    assert not re.search(r"natural (recovery|attenuation)[^.]{0,40}(is the best|best option|is recommended)", t)


def test_no_demonstrated_benefit_is_a_separate_group_from_insufficient_evidence():
    at = run_bay_jimmy()
    ndb = next(m for m in at.markdown if CATEGORY_LABELS["no_demonstrated_benefit"] in m.value and "sr-status" in m.value)
    ins = next(m for m in at.markdown if CATEGORY_LABELS["insufficient_evidence"] in m.value and "sr-status" in m.value)
    assert ndb is not ins and ndb.value != ins.value
    assert R.GROUP_NOTE["no_demonstrated_benefit"] in text(at) and R.GROUP_NOTE["insufficient_evidence"] in text(at)
    assert any(e.label.startswith("Excluded (") for e in at.expander)        # excluded group collapsed with reasons available


# ---- this-site block ------------------------------------------------------------------------------------------------

def test_this_site_block_for_the_worked_cell_uses_the_csv_values():
    at = run_bay_jimmy()
    t = text(at)
    assert "This site: cell 8018_32612" in t
    row = SV.site_for_cell(M.EXAMPLE_CELL)
    assert f"{row['observed_rate']:.2f} m/yr" in t and "1.54 m/yr" in t
    assert f"{row['lobo_pred']:.2f} m/yr" in t and "1.31 m/yr" in t
    assert "0.23 m/yr" in t and R.ONE_CELL_NOTE.split(".")[0] in t
    assert "1.296 m/yr" in t and "12,696" in t and "leave-one-basin-out" in t


def test_this_site_helper_rules():
    report, _ = P.decision_for_site(P.site_items(SV.site_for_cell(M.EXAMPLE_CELL)), "light", None)
    row = SV.site_for_cell(M.EXAMPLE_CELL)
    ts = R.this_site(report, row, "marsh")
    assert ts and abs(ts.observed - 1.5397) < 1e-6 and abs(ts.lobo - 1.3104) < 1e-6 and abs(ts.abs_diff - 0.2293) < 1e-6
    assert abs(ts.deployed - 1.418) < 0.01 and ts.pct is not None
    assert R.this_site(report, {**row, "observed_rate": 0.0}, "marsh").pct is None       # percentage only where observed != 0
    assert R.this_site(report, {**row, "lobo_pred": float("nan")}, "marsh") is None
    assert R.this_site(report, None, "marsh") is None
    assert R.this_site(report, row, "esi_1A") is None and R.this_site(report, {**row, "status": "out_of_scope"}, "marsh") is None


def test_this_site_block_absent_for_typed_site_and_for_other_habitats():
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    at.radio(key="site_mode").set_value("New site (enter values)").run()
    at.button(key="run_marsh").click().run()
    assert not at.exception, at.exception
    assert "This site: cell" not in text(at)
    for key in ("esi_1A", "mangrove", "beach_fine"):
        assert "This site: cell" not in text(run_habitat(key)), key


# ---- validation embed -----------------------------------------------------------------------------------------------

def test_bay_jimmy_embeds_the_holdout_scatter_and_the_deep_link():
    at = run_bay_jimmy()
    t = text(at)
    assert "edge_loss_v1" in t and "MAE" in " ".join(m.value for m in at.markdown)
    assert any(b.key == "how_marsh" for b in at.button)
    assert "No per-station hold-out predictions are stored" in t            # PAH: text status only
    assert at.get("vega_lite_chart") or at.get("arrow_vega_lite_chart")


def test_rocky_has_no_validation_chart_and_states_no_forecast():
    at = run_habitat("esi_1A")
    assert B.NO_FORECAST_TEXT in text(at)
    assert "No value is available for this input" in text(at)
    assert not any("<table class=\"sr-reftable\"" in m.value for m in at.markdown)          # no table of "not stated" rows, no invented numbers
    assert not any(b.key == "how_esi_1A" for b in at.button)


# ---- structure ------------------------------------------------------------------------------------------------------

def test_no_share_button_anywhere():
    for at in (run_bay_jimmy(), run_habitat("mangrove")):
        assert not any("share" in str(b.label).lower() for b in at.button)
        assert "share" not in " ".join(str(b.label).lower() for b in at.get("download_button"))


def test_older_detail_views_are_inside_the_collapsed_technical_area_and_still_rendered():
    at = run_bay_jimmy()
    outer = next(e for e in at.expander if e.label == "Technical details and evidence")
    assert outer.proto.expanded is False
    labels = [e.label for e in outer.expander]
    for wanted in ("Evidence classifications and how each option compares", "Model assumptions and limitations",
                   "Provenance of the literature priors", "Applicability and scope warnings"):
        assert wanted in labels, labels
    assert any(l.startswith("Technical trace") for l in labels)
    inner = next(e for e in outer.expander if e.label.startswith("Evidence classifications"))
    inner_text = " ".join(str(x.value) for g in (inner.markdown, inner.caption) for x in g)
    assert "Evidence behind this answer" in inner_text                       # the answer card
    assert "scenario-composer baseline" in inner_text.lower()                # composer baseline labelled by source
    assert any("composer baseline (experimental)" in m.label.lower() for m in at.metric)


def test_change_place_expander_is_open_before_a_run_and_collapsed_after():
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    assert next(e for e in at.expander if e.label == "Change place or scenario").proto.expanded is True
    at.button(key="run_marsh").click().run()
    assert next(e for e in at.expander if e.label == "Change place or scenario").proto.expanded is False


def test_exactly_one_primary_button_before_and_after_a_run():
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    assert primary(at) == ["run_marsh"]
    at.button(key="run_marsh").click().run()
    assert primary(at) == ["run_marsh"]
    assert any(b.key == "dl_marsh" for b in at.get("download_button")) or at.get("download_button")


def test_stale_warning_is_kept():
    at = run_habitat("marsh")
    at.selectbox(key="site_oil").set_value("heavy").run()
    assert any("changed since this run" in w.value for w in at.warning)


def test_breadcrumb_carries_place_shoreline_oil_and_oiling_source():
    at = run_bay_jimmy()
    crumb = at.session_state[SV.BOARD_RUN_KEY]["crumb"]
    assert crumb["place"] == "Bay Jimmy, Louisiana" and crumb["shoreline"] == "Salt marsh (ESI 10A)"
    assert crumb["oil"] == "Oil: light" and crumb["oiling"] == "Oiling: Heavy (record)"
    assert R.breadcrumb_items({"where": "legacy"}) == ["legacy"]
    typed = new_app()
    typed.segmented_control(key="page").set_value("site").run()
    typed.radio(key="site_mode").set_value("New site (enter values)").run()
    typed.button(key="run_marsh").click().run()
    assert "(entered)" in typed.session_state[SV.BOARD_RUN_KEY]["crumb"]["oiling"]


def test_results_module_never_calls_the_decision_engine():
    src = open(R.__file__, encoding="utf-8").read().split('"""', 2)[2]          # code only, not the module docstring
    imports = " ".join(re.findall(r"^(?:from|import) .*$", src, flags=re.M))
    assert "ui_pipeline" not in imports and "decision_pipeline import run_decision" not in imports and "run_decision(" not in src


def test_models_page_caption_separates_overall_metrics_from_one_site_error():
    at = new_app()
    at.segmented_control(key="page").set_value("models").run()
    assert any("error at one site" in c.value and "nothing about the overall accuracy" in c.value for c in at.caption)
