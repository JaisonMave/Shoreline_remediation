"""V5.2 pages in the running app (Streamlit AppTest): load, controls work, state persists, content is honest.

Run from the repository root:  python -m pytest tests/test_v52_pages.py
Dashboard rendering checks only; they are not scientific validation.
"""
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")


def text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info] + [w.value for w in at.warning] \
            + [e.value for e in at.error] + [m.label + " " + str(m.value) for m in at.metric]
    for t in at.dataframe:
        parts += [str(c) for c in t.value.columns] + [str(v) for v in t.value.to_numpy().ravel()]
    return re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", " ".join(parts), flags=re.S))


def page(name: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.segmented_control(key="page").set_value(name).run()
    assert not at.exception, at.exception
    return at


# ---- Evidence explorer ----------------------------------------------------------------------------------------
def test_evidence_page_states_provenance_limits_and_counts():
    t = text(page("evidence")).replace("**", "")
    assert "AI-extracted and marked Proposed" in t and "not human-verified" in t and "no expert review exists" in t
    for line in ("144 AI-extracted study record (Proposed)", "148 Screening metadata (AI-proposed or AI-transcribed)",
                 "33 Evidence verdict read by the pipeline", "10 Field-plot effect (experimental composer input)"):
        assert line in t, line
    assert "an evidence gap, not a finding that the option does not work" in t


def test_filters_and_record_detail_work():
    at = page("evidence")
    total = re.search(r"(\d+) of (\d+) records match", text(at))
    assert total and total.group(1) == total.group(2) == "389"
    at.multiselect(key="ev_kinds").set_value(["AI-extracted study record (Proposed)"]).run()
    assert "144 of 389 records match" in text(at)
    at.multiselect(key="ev_classes").set_value(["rocky/hard"]).run()
    n = int(re.search(r"(\d+) of 389 records match", text(at)).group(1))
    assert 0 < n < 144
    labels = at.selectbox(key="ev_pick").options          # AppTest returns the formatted labels
    assert len(labels) == n
    at.selectbox(key="ev_pick").set_value(labels[1].split(" | ")[0]).run()
    t = text(at)
    assert "Source and provenance" in t and "Repository file: data/knowledge" in t and "Grade as recorded" in t
    assert labels[1].split(" | ")[0].split(":")[1] in t                              # the chosen record's id is the one shown


def test_a_search_with_no_match_says_so_without_claiming_anything_about_the_option():
    at = page("evidence")
    at.text_input(key="ev_text").set_value("zzz-no-such-text").run()
    assert not at.exception, at.exception
    assert "0 of 389 records match" in text(at) and "not about the option or habitat" in text(at)
    at.text_input(key="ev_text").set_value("").run()
    assert not at.exception, at.exception
    assert "389 of 389 records match" in text(at)


def test_noaa_rating_detail_says_proposed_and_not_effectiveness():
    at = page("evidence")
    at.text_input(key="ev_text").set_value("noaa_1A_087").run()
    t = text(at)
    assert "Screening metadata" in t and "Proposed" in t and "Letters rate adverse habitat impact, not how well oil is removed" in t


def test_gap_tab_and_context_tab_render_and_context_follows_the_site_selection():
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.segmented_control(key="page").set_value("site").run()
    at.segmented_control(key="site_habitat").set_value("esi_1A").run()
    at.segmented_control(key="page").set_value("evidence").run()
    assert not at.exception, at.exception
    assert at.selectbox(key="ev_ctx_esi").value == "1A"
    t = text(at)
    assert "does not mean the option is ineffective" in t and "have no study record in the marsh class" in t
    assert "do not measure the strength of evidence" in t and "not a measured null effect" in t
    assert "Pipeline report for default inputs" in t and "not a site assessment" in t
    assert "Eligibility reflects habitat-impact screening, not demonstrated remediation effectiveness" in t
    at.segmented_control(key="page").set_value("site").run()
    assert at.segmented_control(key="site_habitat").value == "esi_1A"


# ---- Model validation -----------------------------------------------------------------------------------------
def test_models_page_states_scope_failed_gates_and_f5_d32():
    t = text(page("models"))
    assert "2** validated within a narrow scope" in t or "2 validated within a narrow scope" in t
    assert "validated within the stated scope only" in t
    assert "F5 process model: promotion gate failed" in t and "0.775" in t and "0.750" in t
    assert "heavy-cell bias gate failed" in t and "+0.549" in t and "+0.330" in t and "+/-0.25" in t
    assert "not a calibrated probability" in t
    assert "Partly transfers" in t


def test_validated_model_detail_shows_its_failed_gate_and_selection_changes_the_detail():
    at = page("models")
    assert at.selectbox(key="mv_model").value == "edge_loss_v1"
    assert "Failed gates" in text(at) and "V5-0.2" in text(at)
    at.selectbox(key="mv_model").set_value("process_model_v2").run()
    t = text(at)
    assert "Illustrative only" in t and "F5" in t and "Failed gates" in t
    assert "0.750 against 0.775" in t
    at.selectbox(key="mv_model").set_value("composer_natural_recovery_v1").run()
    assert "D32-heavy-bias" in text(at) and "Experimental" in text(at)


def test_models_selection_survives_a_round_trip_through_another_page():
    at = page("models")
    at.selectbox(key="mv_model").set_value("pah_decline_v1").run()
    at.segmented_control(key="page").set_value("landing").run()
    at.segmented_control(key="page").set_value("models").run()
    assert at.selectbox(key="mv_model").value == "pah_decline_v1"


# ---- Navigation and regression -----------------------------------------------------------------------------------
def test_other_pages_still_load_and_invalid_page_falls_back_to_home():
    for name in ("landing", "site", "legacy"):
        at = page(name)
        assert at.segmented_control(key="page").value == name
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["page"] = "no-such-page"
    at.run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "landing"


@pytest.mark.parametrize("name", ["evidence", "models"])
def test_each_new_page_can_go_home_and_is_reachable_from_the_url(name):
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["page"] = name
    at.run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == name
    at.button(key="sr_nav_home").click().run()
    assert at.segmented_control(key="page").value == "landing"


def test_gap_view_switches_habitat_class_and_highlights_zero_counts():
    at = page("evidence")
    at.segmented_control(key="ev_gap_class").set_value("mangrove").run()
    assert not at.exception, at.exception
    t = text(at)
    assert "no study record in the mangrove class" in t
    gap_tables = [d for d in at.dataframe if "Study records" in list(d.value.columns)]
    assert gap_tables and (gap_tables[0].value["Study records"] <= 1).all()          # mangrove: at most one record per option
