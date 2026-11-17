"""V5.1 Session 3 Stage 3: dashboard navigation, habitat coverage tiers and missing-data behaviour.

Software checks only. They show that the navigation, the coverage tiers and the cards do what the contract says and never
present a screening result, a placeholder or a missing value as a validated number. They are not scientific validation of
any model.

Modules that the parallel implementation is still adding (ui_nav, ui_landing, COVERAGE_TIERS, habitat_coverage,
habitat_cards) are imported inside the tests, so a missing module fails only the tests that need it."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import habitat  # noqa: E402
from src.shoreline_remediation import site_view as SV  # noqa: E402
from src.shoreline_remediation import ui_components as C  # noqa: E402
from src.shoreline_remediation import ui_theme as T  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.site_evidence import load_sites  # noqa: E402

APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")
DRAWS = 400
PAGE_IDS = ["landing", "site", "evidence", "models", "legacy"]
PAGE_LABELS = {"landing": "Map", "site": "Assessment", "evidence": "Evidence", "models": "Models", "legacy": "Research"}   # V5.4 short labels
PAGE_TITLES = {"landing": "Home", "site": "Site assessment", "evidence": "Evidence explorer", "models": "Model validation",
               "legacy": "Legacy and research"}
OPENABLE_HABITATS = ["marsh", "mangrove", "beach_fine", "beach_coarse", "beach_mixed", "beach_gravel",
                    "esi_1A", "esi_8A"]
TIER_KEYS = ["numerical", "experimental", "screening", "unsupported"]
TIER_LABELS = {"numerical": "Numerical validation available", "experimental": "Experimental evidence",
               "screening": "Screening and literature only", "unsupported": "Unsupported or insufficient evidence"}
EXPECTED_TIERS = [("marsh", "numerical"), ("mangrove", "experimental"), ("beach_fine", "experimental"),
                  ("beach_coarse", "screening"), ("beach_mixed", "screening"), ("beach_gravel", "screening")]
SITE_COLUMNS = ["cell", "lat", "lon", "max_oiling", "observed_rate", "fetch_mean_m"]
RATE = re.compile(r"\d+(\.\d+)?\s*(m/yr|%|years?)")
ESI_ROCKY = re.compile(r"\b(1A|8A)\b")


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def new_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def go(at: AppTest, page: str) -> None:
    at.segmented_control(key="page").set_value(page).run()
    assert not at.exception, at.exception


def all_md(at: AppTest) -> str:
    """Visible page text: markdown, info boxes and captions, without the injected stylesheet and HTML tags."""
    raw = " ".join(str(e.value) for group in (at.markdown, at.info, at.caption) for e in group)
    return re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", raw, flags=re.S))


def snippet(body: str) -> AppTest:
    script = ("import sys\n"
              f"sys.path.insert(0, {str(ROOT)!r})\n"
              "import streamlit as st\n" + body)
    at = AppTest.from_string(script, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.fixture(scope="module")
def landing():
    return new_app()


# ---------------------------------------------------------------------------------------------------------------
# Landing page

def test_landing_renders_title_coverage_line_and_one_coverage_section(landing):
    from src.shoreline_remediation import ui_landing
    md = all_md(landing)
    assert not landing.exception
    assert "Shoreline Remediation" in md and "Site and spill scenario" in md
    assert ui_landing.COVERAGE_LINE in md
    assert [e.label for e in landing.expander].count(ui_landing.COVERAGE_TITLE) == 1
    for header in ("Featured locations", "Explore habitats"):
        assert header not in md, header


def test_coverage_section_lists_every_habitat_with_its_tier(landing):
    from src.shoreline_remediation import ui_landing
    rows = ui_landing.coverage_rows()
    assert len(rows) == len(SV.habitat_coverage())
    assert {r["Coverage"] for r in rows} <= set(TIER_LABELS.values())
    assert any(r["Shoreline type"] == "Other shoreline types" for r in rows)       # unsupported habitats are named
    md = all_md(landing).lower()
    assert "explore and select" not in md and "get recommendation" not in md      # the setup step cards are gone


def test_home_run_action_opens_the_site_page():
    at = new_app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "site"


# ---------------------------------------------------------------------------------------------------------------
# Navigation

@pytest.mark.parametrize("page", PAGE_IDS)
def test_segmented_control_reaches_each_page(page):
    at = new_app()
    go(at, page)
    assert at.segmented_control(key="page").value == page





@pytest.mark.parametrize("habitat_key", OPENABLE_HABITATS)
def test_panel_run_opens_the_site_page_at_its_habitat(habitat_key):
    at = new_app()
    at.selectbox(key="home_habitat").set_value(habitat_key).run()
    at.button(key="home_run").click().run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "site"
    assert at.segmented_control(key="site_habitat").value == habitat_key


def test_map_page_has_no_open_card_buttons_and_offers_every_openable_habitat(landing):
    keys = [b.key or "" for b in landing.button]
    assert not any(k.startswith("sr_open_site") for k in keys)
    options = landing.selectbox(key="home_habitat").options
    assert len(options) == len(OPENABLE_HABITATS) and not any("unsupported" in str(o).lower() for o in options)


def test_landing_has_no_home_button(landing):
    assert not any(b.key == "sr_nav_home" for b in landing.button)


@pytest.mark.parametrize("page", ["site", "evidence", "models", "legacy"])
def test_home_button_returns_to_landing_from_each_page(page):
    at = new_app()
    go(at, page)
    at.button(key="sr_nav_home").click().run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "landing"


def test_site_selection_survives_a_round_trip_through_home():
    at = new_app()
    go(at, "site")
    at.segmented_control(key="site_habitat").set_value("mangrove").run()
    at.button(key="sr_nav_home").click().run()
    assert at.segmented_control(key="page").value == "landing"
    go(at, "site")
    assert at.segmented_control(key="site_habitat").value == "mangrove"


@pytest.mark.parametrize("page", ["evidence", "models"])
def test_evidence_and_models_pages_are_real_pages_since_v52(page):
    """V5.2 replaced the Session 3 placeholders for these two pages (tests/test_v52_pages.py covers their content). The placeholder
    function itself still refuses to show numbers; this checks that the two pages no longer route to it."""
    at = new_app()
    go(at, page)
    assert not at.exception, at.exception
    assert "not yet available" not in all_md(at).lower()
    assert len(at.tabs) == 3


def test_legacy_page_warns_that_it_does_not_drive_production():
    at = new_app()
    go(at, "legacy")
    assert any("legacy" in w.value.lower() for w in at.warning)


def test_legacy_page_offers_scenario_analysis_in_the_sidebar():
    at = new_app()
    go(at, "legacy")
    assert any("Run scenario analysis" in b.label for b in at.sidebar.button)


def test_site_page_has_no_scenario_analysis_sidebar_button():
    at = new_app()
    go(at, "site")
    assert not any("Run scenario analysis" in b.label for b in at.sidebar.button)


# ---------------------------------------------------------------------------------------------------------------
# Missing site data

def test_featured_sites_omits_marsh_card_without_a_site_table(monkeypatch):
    monkeypatch.setattr(SV, "_sites", lambda: pd.DataFrame(columns=SITE_COLUMNS))
    cards = SV.featured_sites()
    assert "marsh" not in [c.site_id for c in cards]
    assert not any("Bay Jimmy" in c.name for c in cards)     # nothing invented in its place


def test_featured_sites_omits_mangrove_card_when_its_results_cannot_be_read(monkeypatch):
    def unreadable():
        raise FileNotFoundError("results/mangrove missing")
    monkeypatch.setattr(SV, "_mangrove_results", unreadable)
    ids = [c.site_id for c in SV.featured_sites()]
    assert "mangrove" not in ids and "marsh" in ids


def test_missing_observed_rate_is_a_none_value_shown_as_not_available(monkeypatch):
    sites = load_sites().copy()
    sites.loc[sites.cell == SV.EXAMPLE_CELL, "observed_rate"] = np.nan
    monkeypatch.setattr(SV, "_sites", lambda: sites)
    marsh = next(c for c in SV.featured_sites() if c.site_id == "marsh")
    fact = next(f for f in marsh.facts if f.label.startswith("Edge loss"))
    assert fact.value is None
    txt = text_of(C.site_card_html(marsh))
    assert "Edge loss 2010 to 2015 (aerial images) not available" in txt
    assert "m/yr" not in txt


# ---------------------------------------------------------------------------------------------------------------
# Evidence coverage tiers

def test_coverage_tier_keys_and_labels_are_exact():
    assert list(T.COVERAGE_TIERS) == TIER_KEYS
    assert {k: v["label"] for k, v in T.COVERAGE_TIERS.items()} == TIER_LABELS


def test_coverage_tiers_carry_non_empty_label_grade_and_legend():
    for key, tier in T.COVERAGE_TIERS.items():
        for field in ("label", "grade", "legend"):
            assert isinstance(tier.get(field), str) and tier[field].strip(), (key, field)


@pytest.mark.parametrize("habitat_key,tier", EXPECTED_TIERS)
def test_habitat_coverage_tier_follows_the_registry(habitat_key, tier):
    by_key = {c.key: c for c in SV.habitat_coverage()}
    assert by_key[habitat_key].tier == tier


def test_rocky_shoreline_entries_screen_without_a_model():
    rocky = [c for c in SV.habitat_coverage() if ESI_ROCKY.search(str(c.esi or ""))]
    assert rocky
    for c in rocky:
        assert c.tier == "screening" and c.opens == c.key and not c.evidence[0][0].startswith("validated"), c.key


def test_unsupported_entry_is_the_only_abstaining_entry_and_says_so():
    entries = SV.habitat_coverage()
    unsupported = [c for c in entries if c.tier == "unsupported"]
    assert len(unsupported) == 1 and unsupported[0].opens is None
    summary = unsupported[0].summary.lower()
    assert "unsupported" in summary or "abstain" in summary


def test_numerical_tier_requires_a_validated_model(monkeypatch):
    real = SV._model_states()
    numerical = [c.key for c in SV.habitat_coverage() if c.tier == "numerical"]
    assert not numerical or "validated" in real.values()
    for fake in ({m: "experimental" for m in real}, {}):
        monkeypatch.setattr(SV, "_model_states", lambda fake=fake: fake)
        assert all(c.tier != "numerical" for c in SV.habitat_coverage())


def test_marsh_tier_is_demoted_when_every_model_is_experimental(monkeypatch):
    real = SV._model_states()
    monkeypatch.setattr(SV, "_model_states", lambda: {m: "experimental" for m in real})
    assert {c.key: c for c in SV.habitat_coverage()}["marsh"].tier == "experimental"


def test_marsh_tier_is_screening_without_any_registry_state(monkeypatch):
    monkeypatch.setattr(SV, "_model_states", lambda: {})
    assert {c.key: c for c in SV.habitat_coverage()}["marsh"].tier == "screening"


def test_every_card_kicker_is_the_coverage_tier_label():
    tiers = {c.key: c.tier for c in SV.habitat_coverage()}
    labels = set(TIER_LABELS.values())
    cards = list(SV.habitat_cards())
    assert all(card.kicker in labels for card in cards)
    matched = [card for card in cards if card.site_id in tiers]
    assert matched
    for card in matched:
        assert card.kicker == TIER_LABELS[tiers[card.site_id]], card.site_id


def test_only_the_marsh_entry_carries_a_validated_chip():
    for card in list(SV.habitat_cards()) + list(SV.featured_sites()):
        if any(grade == "validated" for grade, _ in card.evidence):
            assert card.site_id == "marsh", card.site_id


def test_coverage_section_uses_all_four_coverage_tier_labels():
    from src.shoreline_remediation import ui_landing
    assert {r["Coverage"] for r in ui_landing.coverage_rows()} == set(TIER_LABELS.values())


# ---------------------------------------------------------------------------------------------------------------
# Unsupported habitats abstain

@pytest.mark.parametrize("name", ["coral reef", "seagrass"])
def test_out_of_scope_habitat_names_normalise_to_unknown(name):
    assert habitat.normalise(name) == "unknown"


def test_unsupported_habitat_pipeline_abstains_instead_of_screening():
    r = dp.run_decision(Scenario(shoreline_type="coral_reef"), habitat="coral_reef", n_draws=DRAWS)
    assert r.scope_tier == "unsupported_habitat"
    assert r.options == []


# ---------------------------------------------------------------------------------------------------------------
# No fabricated numerical content

def test_habitat_cards_carry_no_numeric_facts():
    for card in SV.habitat_cards():
        for fact in card.facts:
            assert fact.value is None or not re.search(r"\d", str(fact.value)), (card.site_id, fact.label)


def test_habitat_descriptions_and_coverage_summaries_carry_no_rates():
    texts = [c.description for c in SV.habitat_cards()] + [c.summary for c in SV.habitat_coverage()]
    assert texts
    for text in texts:
        assert "%" not in text and not RATE.search(text), text


def test_rocky_and_unsupported_summaries_have_no_figures_beyond_the_esi_code():
    checked = 0
    for c in SV.habitat_coverage():
        if c.tier == "unsupported" or ESI_ROCKY.search(str(c.esi or "")):
            checked += 1
            assert not re.search(r"\d", ESI_ROCKY.sub("", c.summary)), c.key
    assert checked >= 2


def test_landing_shows_no_outcome_number_or_percentage_before_a_selection(landing):
    md = all_md(landing)
    assert "m/yr" not in md
    assert "%" not in md


# ---------------------------------------------------------------------------------------------------------------
# ui_nav module contract

def test_page_registry_is_ordered_with_landing_as_default():
    from src.shoreline_remediation import ui_nav
    assert list(ui_nav.PAGES) == PAGE_IDS
    assert dict(ui_nav.PAGES) == PAGE_LABELS
    assert dict(ui_nav.PAGE_TITLES) == PAGE_TITLES
    assert ui_nav.DEFAULT_PAGE == "landing"
    assert "Legacy" in ui_nav.PAGE_TITLES["legacy"] and ui_nav.PAGES["legacy"] == "Research"


def test_go_ignores_unknown_page_ids():
    at = snippet("from src.shoreline_remediation import ui_nav\n"
                 "st.session_state['page'] = 'site'\n"
                 "ui_nav.go('nonsense')\n"
                 "st.write('page=' + str(st.session_state.get('page')))\n")
    assert any("page=site" in m.value for m in at.markdown)


@pytest.mark.parametrize("page", PAGE_IDS)
def test_go_sets_each_known_page(page):
    at = snippet("from src.shoreline_remediation import ui_nav\n"
                 f"ui_nav.go({page!r})\n"
                 "st.write('page=' + str(st.session_state.get('page')))\n")
    assert any(f"page={page}" in m.value for m in at.markdown)


@pytest.mark.parametrize("bad", ["bogus", "", 42])
def test_current_page_falls_back_to_landing_for_an_invalid_session_value(bad):
    at = snippet("from src.shoreline_remediation import ui_nav\n"
                 f"st.session_state['page'] = {bad!r}\n"
                 "st.write('current=' + str(ui_nav.current_page()))\n")
    assert any("current=landing" in m.value for m in at.markdown)
