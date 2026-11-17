"""V5.1 Session 2 Stage 4: rocky-shoreline (ESI 1A, 8A) screening pages.

Software tests of navigation, labels and abstention. They are not scientific model validation: the pages show rules and
literature screening only, and no rocky-shore model, site record or forecast exists."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")

from src.shoreline_remediation import site_view as SV  # noqa: E402

ROCKY = ["esi_1A", "esi_8A"]
from tests._nav import open_habitat  # noqa: E402


def page_text(at: AppTest) -> str:
    raw = " ".join(str(e.value) for group in (at.markdown, at.info, at.caption, at.warning) for e in group)
    return re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", raw, flags=re.S))


def open_rocky(key: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    open_habitat(at, f"hab_{key.lower()}")
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("key", ROCKY)
def test_rocky_page_opens_from_the_habitat_switcher(key):
    at = open_rocky(key)
    assert at.segmented_control(key="page").value == "site"
    assert at.segmented_control(key="site_habitat").value == key
    assert at.segmented_control(key="site_habitat").options  # switcher lists it
    assert SV.HABITAT_BY_KEY[key].shoreline_type == "rocky_shore"


@pytest.mark.parametrize("key,esi", [("esi_1A", "1A"), ("esi_8A", "8A")])
def test_rocky_page_labels_and_abstention(key, esi):
    at = open_rocky(key)
    text = page_text(at)
    low = text.lower()
    assert SV.HABITAT_BY_KEY[key].label.lower() in low or esi in text
    assert "rules and literature only" in low
    assert "no site-specific numerical forecast" in low
    assert "insufficient evidence" in low or "insufficient_evidence" in low
    assert "natural recovery" in low
    assert "no outcome model" in low
    # nothing presented as validated or as a numerical forecast
    assert "validated prediction" not in low


@pytest.mark.parametrize("key", ROCKY)
def test_no_outcome_chart_or_site_data_on_rocky_page(key):
    at = open_rocky(key)
    assert not at.exception
    # no persistence group switcher (sand-beach reference) and no marsh site picker on a rocky page
    keys = [c.key or "" for c in at.segmented_control]
    assert not any(k.startswith("beach_group_") for k in keys)
    assert not at.dataframe or all("observed" not in " ".join(map(str, d.value.columns)).lower() for d in at.dataframe)


@pytest.mark.parametrize("key", ROCKY)
def test_rocky_coverage_is_screening_with_no_validated_state(key):
    c = next(c for c in SV.habitat_coverage() if c.key == key)
    assert c.tier == "screening" and c.opens == key
    assert all(grade == "rules_literature" for grade, _ in c.evidence)
    assert SV.HABITAT_MODELS.get(key, ()) == ()
    assert not re.search(r"\d", re.sub(r"ESI\s*\w+", "", c.summary))


@pytest.mark.parametrize("key,esi", [("esi_1A", "1A"), ("esi_8A", "8A")])
def test_pipeline_abstains_for_rocky_shores(key, esi):
    from src.shoreline_remediation import ui_pipeline as P, ui_evidence as E
    h = SV.HABITAT_BY_KEY[key]
    from src.shoreline_remediation.data_model import Scenario
    scen = Scenario(shoreline_type=h.shoreline_type, wave_exposure="moderate", oil_category="medium")
    report, err = P.decision_for_scenario(P.scenario_items(scen), "Moderate", "medium", None, esi)
    assert err is None and report is not None
    v = E.report_view(report)
    kinds = {a["kind"] if isinstance(a, dict) else a.kind for a in v.abstentions}
    assert {"no_site_forecast", "no_recommendation"} <= kinds
    assert not v.recommendation_summary.get("recommended")
    assert "natural_attenuation" in v.recommendation_summary["natural_recovery_monitoring"]


def test_no_rocky_site_in_featured_sites():
    for s in SV.featured_sites():
        assert "rock" not in str(s).lower() and "1A" not in str(getattr(s, "habitat", ""))


@pytest.mark.parametrize("key", ["marsh", "mangrove", "beach_fine", "beach_gravel"])
def test_existing_pathways_still_render(key):
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    open_habitat(at, f"hab_{key}")
    assert not at.exception, at.exception
    assert at.segmented_control(key="site_habitat").value == key
    if key.startswith("beach_"):
        assert "rocky" not in page_text(at).lower().split("options and what")[0]


def test_return_to_landing_from_rocky_page():
    at = open_rocky("esi_1A")
    at.segmented_control(key="page").set_value("landing").run()
    assert not at.exception and at.segmented_control(key="page").value == "landing"


# ---- Phase 3 corrections (software checks; the chart overlap itself was checked in a browser) -------------------------

def _contrast(fg: str, bg: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_ai_proposed_table_text_meets_wcag_aa_on_dark_surfaces():
    import pandas as pd
    from src.shoreline_remediation import ui_components as C
    css = C.ai_style_dataframe(pd.DataFrame({"a": [1]})).to_html()
    colour = re.search(r"color:\s*(#[0-9A-Fa-f]{6})", css).group(1)
    for bg in ("#080D17", "#111A29", "#182438"):
        assert _contrast(colour, bg) >= 4.5, (colour, bg)


def test_interval_chart_height_leaves_room_for_every_row():
    import pandas as pd
    from src.shoreline_remediation import ui_components as C
    rows = [{"option": f"o{i}", "median": 1.0, "lo": 0.0, "hi": 2.0, "grade": "experimental", "cls": "A"} for i in range(2)]
    h = C.interval_chart(rows, "t", "x").to_dict()["height"]
    assert h >= 2 * 40 + C._INTERVAL_CHROME


def test_habitat_cards_carry_a_structured_tier():
    from src.shoreline_remediation import ui_theme as T
    cards = SV.habitat_cards()
    assert cards and all(c.tier in T.COVERAGE_TIERS for c in cards)
    by = {c.site_id: c for c in cards}
    assert by["marsh"].tier == "numerical" and by["esi_1A"].tier == "screening" and by["unsupported"].tier == "unsupported"


def test_fine_sand_chips_keep_reference_and_cleanup_options_separate():
    c = next(c for c in SV.habitat_coverage() if c.key == "beach_fine")
    grades = [g for g, _ in c.evidence]
    assert "experimental" in grades and "rules_literature" in grades
    rules_text = next(t for g, t in c.evidence if g == "rules_literature")
    assert "cleanup options" in rules_text and "no experimental evidence" in rules_text
