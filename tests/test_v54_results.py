"""V5.4 Stages 3 to 5: the single results view on the Assessment page. Dashboard wiring only; not scientific validation.

Run from the repository root:  python -m pytest tests/test_v54_results.py
"""
import datetime as dt
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
    return " ".join(m.value for m in at.markdown if "sr-oc-title" in m.value or "sr-find" in m.value)


def table_html(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown if "sr-opttable" in m.value)


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

def test_bay_jimmy_finding_states_the_field_contrast_and_keeps_the_reports_outcome():
    at = run_bay_jimmy()
    report = report_of(at)
    html = outcome_html(at)
    assert report.decision_outcome_label in html
    assert "34 percentage points higher in manually treated plots than in untreated oiled plots at year 2" in html
    assert "Main limitation" in html and "not randomly assigned" in html
    cat, options = top_options(report)
    assert cat == "recommended" and options == ["manual_removal"]
    row = next(r for r in R.option_rows(report) if r["option"] == "manual_removal")
    assert row["category"] == "recommended" and row["status"] == CATEGORY_LABELS["recommended"]
    assert "Manual removal" in table_html(at) and CATEGORY_LABELS["recommended"] in table_html(at)


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
    assert R.REFERENCE_REASON in text(at)
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
    assert R.NOT_ASSESSED_TEXT in text(at)
    assert not table_html(at)


# ---- groups ---------------------------------------------------------------------------------------------------------

def test_natural_recovery_never_called_recommended_or_best_when_it_is_the_reference():
    at = run_habitat("esi_1A")
    t = text(at).lower()
    assert "natural recovery with monitoring (reference option)" in t
    assert not re.search(r"natural (recovery|attenuation)[^.]{0,40}(is the best|best option|is recommended)", t)


def test_statuses_stay_separate_and_excluded_rows_stay_visible_with_reasons():
    at = run_bay_jimmy()
    rows = R.option_rows(report_of(at))
    by = {r["option"]: r for r in rows}
    assert by["low_pressure_flushing"]["status"] == CATEGORY_LABELS["no_demonstrated_benefit"]
    assert by["passive_sorbents"]["status"] == CATEGORY_LABELS["insufficient_evidence"]
    assert by["mechanical_removal"]["category"] == "excluded" and "damage sensitive wetland" in by["mechanical_removal"]["reason"]
    html = table_html(at)
    for label in (CATEGORY_LABELS["no_demonstrated_benefit"], CATEGORY_LABELS["insufficient_evidence"], CATEGORY_LABELS["excluded"]):
        assert label in html
    assert "Mechanical removal" in html and "damage sensitive wetland" in html      # excluded rows are in the table, not hidden


# ---- this-site block ------------------------------------------------------------------------------------------------

def test_site_strip_for_the_worked_cell_labels_three_numbers_and_the_dataset_mae():
    at = run_bay_jimmy()
    t = text(at)
    assert "Marsh-edge loss at cell 8018_32612" in t
    row = SV.site_for_cell(M.EXAMPLE_CELL)
    assert f"{row['observed_rate']:.2f} m/yr" in t and "1.54 m/yr" in t
    assert f"{row['lobo_pred']:.2f} m/yr" in t and "1.31 m/yr" in t and "1.42 m/yr" in t
    for label in (R.DEPLOYED_LABEL, R.OBSERVED_LABEL, R.LOBO_LABEL):
        assert label in t
    assert "0.23 m/yr" not in t                              # one cell's error is not shown beside the dataset-level MAE
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
    assert "Marsh-edge loss at cell" not in text(at)
    for key in ("esi_1A", "mangrove", "beach_fine"):
        assert "Marsh-edge loss at cell" not in text(run_habitat(key)), key


# ---- validation embed -----------------------------------------------------------------------------------------------

def test_bay_jimmy_shows_one_effect_plot_and_links_to_the_scatter_on_models():
    at = run_bay_jimmy()
    t = text(at)
    assert "Total vegetation cover at year 2: comparison with natural recovery" in t
    assert "provisional order" not in t.lower().split("how the order is made")[0]      # one eligible method: no rank
    assert any(b.key == "how_marsh" for b in at.button)
    assert "No per-station hold-out predictions are stored" in t            # PAH: text status only
    charts = at.get("vega_lite_chart") or at.get("arrow_vega_lite_chart")
    assert charts
    assert "Leave-one-basin-out prediction, m/yr" not in str([c.proto for c in charts])[:200000]   # the scatter lives on Models


def test_rocky_uses_the_screening_table_and_states_no_forecast():
    at = run_habitat("esi_1A")
    assert not any(e.label == "Explore future scenarios" for e in at.expander)
    t = text(at)
    assert B.NO_FORECAST_TEXT in t
    assert "Screening result" in t and "No treatment has a comparable effect estimate" in t
    assert table_html(at) and "No comparative data" not in table_html(at)      # no comparison column where none exists
    assert not any(b.key == "how_esi_1A" for b in at.button)


# ---- structure ------------------------------------------------------------------------------------------------------

def test_bay_jimmy_future_scenario_controls_use_the_observed_anchor():
    at = run_bay_jimmy()
    assert any(e.label == "Explore future scenarios" for e in at.expander)
    before = outcome_html(at)
    at.session_state["bj_future_panel"] = True
    at.run()
    assert not at.exception, at.exception
    assert "31.06 m since December 2010" in text(at)
    at.number_input(key="bj_future_rate").set_value(0.0).run()
    assert "0.00 m additional retreat" in text(at)
    assert "12.13 m since December 2010" in text(at)
    at.date_input(key="bj_future_end").set_value(dt.date(2050, 1, 1)).run()
    at.number_input(key="bj_future_rate").set_value(1.43).run()
    at.checkbox(key="bj_future_change").check().run()
    assert "74.86 m since December 2010" in text(at)
    at.date_input(key="bj_future_end").set_value(dt.date(2017, 1, 1)).run()
    assert not at.exception
    assert "These planning horizons extend beyond" not in text(at)
    at.checkbox(key="bj_future_change").uncheck().run()
    assert "Historical tests on these nine plots covered lead times up to about four years" in text(at)
    assert "Neither candidate improved on the constant-rate baseline enough to meet the study criteria" in text(at)
    assert "Longer projections depend on the rates you choose" in text(at)
    assert "12.47 m since December 2010" in text(at)
    assert outcome_html(at) == before

def test_no_share_button_anywhere():
    for at in (run_bay_jimmy(), run_habitat("mangrove")):
        assert not any("share" in str(b.label).lower() for b in at.button)
        assert "share" not in " ".join(str(b.label).lower() for b in at.get("download_button"))


def test_methods_and_sources_is_collapsed_and_keeps_the_detail_views_and_trace():
    at = run_bay_jimmy()
    outer = next(e for e in at.expander if e.label == "Methods and sources")
    assert outer.proto.expanded is False
    labels = [e.label for e in outer.expander]
    for wanted in ("Option evidence in detail (current inputs)", "Model assumptions and limitations", "Provenance of the literature priors"):
        assert wanted in labels, labels
    assert any(l.startswith("Technical trace") for l in labels)
    inner = next(e for e in outer.expander if e.label.startswith("Option evidence in detail"))
    inner_text = " ".join(str(x.value) for g in (inner.markdown, inner.caption) for x in g)
    assert "scenario-composer baseline" in inner_text.lower()                # composer baseline labelled by source
    assert any("composer baseline (experimental)" in m.label.lower() for m in at.metric)
    outer_text = " ".join(str(x.value) for g in (outer.markdown, outer.caption) for x in g)
    assert "Model estimates in the order:** none" in outer_text and "composer_natural_recovery_v1" in outer_text


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


# ---- plot-first scenarios (V5.4 plot-first) ---------------------------------------------------------------------------

def test_typed_heavy_marsh_shows_the_field_plots_unranked_and_is_never_a_model_cell():
    at = new_app()
    at.segmented_control(key="page").set_value("site").run()
    at.radio(key="site_mode").set_value("New site (enter values)").run()
    at.selectbox(key="new_oil").set_value("Heavy").run()
    at.button(key="run_marsh").click().run()
    assert not at.exception, at.exception
    rec = at.session_state[SV.BOARD_RUN_KEY]
    assert rec["spec"][0] == "scenario" and rec["flags"] is None
    report = report_of(at)
    comp = R.comparisons_for(report, rec)["veg_cover_year2"]
    assert comp.applicable and comp.mode == "none" and [r.option for r in comp.shown] == ["manual_removal"]
    assert comp.row_for("manual_removal").reason.startswith("Conditions not established")
    html = outcome_html(at)
    assert "34 percentage points higher" in html and "not this scenario" in html
    t = text(at)
    assert "Marsh-edge loss at cell" not in t and "provisional rank" not in t and "Extrapolation" not in t
    assert not any(m.label.startswith("Expected marsh-edge loss") for m in at.metric)   # the detail views use the same scope


def test_fine_sand_shows_the_historical_response_curve_and_a_screening_table():
    at = run_habitat("beach_fine")
    report = report_of(at)
    ref = R.beach_reference(report)
    pt = R.sand_point(ref)
    assert pt and pt["day"] == 365 and abs(pt["median"] - ref["curves_by_group"][pt["group"]]["median"][2]) < 1e-12
    html = outcome_html(at)
    assert f"{pt['median']:.0%}" in html and "365 days after the first oiled survey" in html and "not natural recovery" in html
    t = text(at)
    assert "Historical response: visible oil on fine-to-medium sand beaches" in t and "200 refits" in t
    assert table_html(at) and "No comparative data" not in table_html(at) and "harm_flags" not in table_html(at)
    assert at.get("vega_lite_chart") or at.get("arrow_vega_lite_chart")


def test_non_heavy_marsh_cell_says_no_comparative_data_and_draws_no_effect_plot():
    report, _ = P.decision_for_site(P.site_items(SV.site_for_cell(M.EXAMPLE_CELL)), "light", None)
    rec = {"habitat": "marsh", "spec": ("site", tuple({**dict(P.site_items(SV.site_for_cell(M.EXAMPLE_CELL))), "max_oiling": "Moderate"}.items()), "light", None)}
    comps = R.comparisons_for(report, rec)
    assert comps and all(not c.applicable for c in comps.values())
    rows = R.option_rows(report, comps["veg_cover_year2"])
    assert {r["comparison"] for r in rows if r["option"] != "natural_attenuation"} == {"No comparative data"}
    sentence, limit = R.finding_for(report, B.board_model(report), comps, rec)
    assert sentence.startswith("No comparative data") and "heavily oiled salt marsh only" in limit
