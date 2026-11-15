"""V5.1 Session 2 Stage 2: reusable dashboard components (section header, status label, site card, card row, hero).

Software checks only. They show that the components display what the decision pipeline and the repository files give
them, and nothing else. They are not scientific validation of any model."""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import decision_pipeline as dp  # noqa: E402
from src.shoreline_remediation import ui_components as C  # noqa: E402
from src.shoreline_remediation import ui_theme as T  # noqa: E402
from tests.test_ui_theme import contrast  # noqa: E402

APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def run_snippet(body: str) -> AppTest:
    script = ("import sys\n"
              f"sys.path.insert(0, {str(ROOT)!r})\n"
              "import streamlit as st\n"
              "from src.shoreline_remediation import ui_components as C\n" + body)
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.fixture(scope="module")
def app():
    return fresh()


# ---------------------------------------------------------------------------------------------------------------
# section_header

def test_section_header_title_only():
    html = C.section_header_html("Featured locations")
    assert "<h2>Featured locations</h2>" in html and 'class="sr-section"' in html
    assert "sr-kicker" not in html and "sr-section-desc" not in html and "sr-section-meta" not in html


def test_section_header_optional_parts_and_escaping():
    html = C.section_header_html("Evidence <b>", kicker="Explore", description="What is known & what is not.", meta="3 sources",
                                 anchor="evidence")
    assert '<div class="sr-kicker">Explore</div>' in html
    assert "Evidence &lt;b&gt;" in html and "<b>" not in html
    assert "What is known &amp; what is not." in html
    assert '<div class="sr-section-meta">3 sources</div>' in html and 'id="evidence"' in html


def test_section_header_renders_in_streamlit():
    at = run_snippet("C.section_header('Remediation options', kicker='Compare', description='Against natural recovery.')\n")
    assert any("Remediation options" in m.value and "Against natural recovery." in m.value for m in at.markdown)


# ---------------------------------------------------------------------------------------------------------------
# status_label

def test_status_styles_cover_exactly_the_pipeline_categories():
    assert set(T.CATEGORY_STYLE) == set(dp.CATEGORY_ORDER)


@pytest.mark.parametrize("category", dp.CATEGORY_ORDER)
def test_status_label_uses_the_pipeline_wording(category):
    html = C.status_label(category)
    assert text_of(html).endswith(dp.CATEGORY_LABELS[category])
    assert f"--c:{T.CATEGORY_STYLE[category]['colour']}" in html
    assert T.CATEGORY_STYLE[category]["symbol"] in html
    assert "sr-status-unknown" not in html


def test_status_label_required_categories_keep_their_meaning():
    assert text_of(C.status_label(dp.CAT_RECOMMENDED)).endswith("Recommended")
    assert text_of(C.status_label(dp.CAT_CONDITIONAL)).endswith("Conditional")
    assert text_of(C.status_label(dp.CAT_EXCLUDED)).endswith("Excluded")
    assert text_of(C.status_label(dp.CAT_INSUFFICIENT)).endswith("Insufficient evidence")
    no_benefit = text_of(C.status_label(dp.CAT_NO_BENEFIT))
    assert "Allowed, no demonstrated benefit" in no_benefit
    for word in ("Recommended", "effective", "safe", "harmless"):
        assert word.lower() not in no_benefit.lower()


def test_status_symbols_and_colours_are_distinct_and_visible_on_cards():
    symbols = [s["symbol"] for s in T.CATEGORY_STYLE.values()]
    assert len(set(symbols)) == len(symbols)
    recommended = T.CATEGORY_STYLE[dp.CAT_RECOMMENDED]
    for key, style in T.CATEGORY_STYLE.items():
        assert contrast(style["colour"], T.PALETTE["card"]) >= 3.0, key
        if key != dp.CAT_RECOMMENDED:
            assert style["colour"] != recommended["colour"] and style["symbol"] != recommended["symbol"]
    assert contrast(T.PALETTE["text"], T.PALETTE["card"]) >= 4.5


@pytest.mark.parametrize("value", [None, "", "  ", "approved", "RECOMMENDED", "A", 0])
def test_unknown_or_missing_status_is_never_shown_as_a_real_category(value):
    html = C.status_label(value)
    txt = text_of(html)
    assert "sr-status-unknown" in html
    assert T.STATUS_MISSING_TEXT in txt or T.STATUS_UNRECOGNISED_TEXT in txt
    for key in dp.CATEGORY_ORDER:
        assert f"sr-status-{key.replace('_', '-')}" not in html
        assert dp.CATEGORY_LABELS[key] not in txt
    assert T.CATEGORY_STYLE[dp.CAT_RECOMMENDED]["symbol"] not in html


def test_status_label_escapes_unknown_text():
    assert "<script>" not in C.status_label("<script>")


def test_status_label_does_not_change_the_pipeline_rules():
    assert dp.CATEGORY_ORDER == ("recommended", "conditional", "natural_recovery_monitoring", "no_demonstrated_benefit",
                                 "insufficient_evidence", "excluded")
    assert dp.CATEGORY_LABELS[dp.CAT_NO_BENEFIT] == "Allowed, no demonstrated benefit over natural recovery"
    assert dp.PIPELINE_VERSION == "f9-v3"


# ---------------------------------------------------------------------------------------------------------------
# site_card

FULL = C.SiteCard(site_id="demo_site", name="Demo <site>", kicker="Worked example", location="Somewhere", habitat="Salt marsh",
                  description="A description.",
                  facts=(C.SiteFact("Oiling", "Heavy", "observed"), C.SiteFact("Fetch", "100 m", "derived"),
                         C.SiteFact("Edge loss", "1.2 m/yr", "model"), C.SiteFact("Coordinates", None)),
                  evidence=(("validated", "Validated: one model"), ("rules_literature", "Rules and literature only")))


def test_site_card_complete_metadata():
    html = C.site_card_html(FULL)
    txt = text_of(html)
    assert "Demo &lt;site&gt;" in html
    assert "Somewhere | Salt marsh" in txt and "A description." in txt and "Worked example" in txt
    assert "Heavy Observed" in txt and "100 m Derived" in txt and "1.2 m/yr Model estimate" in txt
    assert "Coordinates not available" in txt
    assert "sr-g-validated" in html and "sr-g-rules" in html


def test_site_card_missing_optional_metadata_adds_nothing():
    html = C.site_card_html(C.SiteCard(site_id="x", name="Only a name"))
    assert text_of(html) == "Only a name"
    assert not re.search(r"\d", text_of(html))
    assert "sr-chip" not in html and "<dl>" not in html and "sr-status" not in html


def test_site_card_button_passes_the_site_identifier_unchanged():
    at = run_snippet(
        "def pick(site_id):\n"
        "    st.session_state['picked'] = site_id\n"
        "C.site_card(C.SiteCard(site_id='beach_fine', name='A beach', action_label='Open it'), on_select=pick)\n"
        "st.write('picked=' + str(st.session_state.get('picked')))\n")
    assert [b.label for b in at.button] == ["Open it"]
    at.button[0].click().run()
    assert not at.exception
    assert any("picked=beach_fine" in m.value for m in at.markdown)


def test_site_card_without_navigation_has_no_button():
    at = run_snippet("C.site_card(C.SiteCard(site_id='x', name='No action'))\n")
    assert len(at.button) == 0


# ---------------------------------------------------------------------------------------------------------------
# card_row

@pytest.mark.parametrize("n", [0, 1, 3])
def test_card_row_empty_single_and_multiple(n):
    at = run_snippet(
        f"cards = [C.SiteCard(site_id=f's{{i}}', name=f'Site {{i}}') for i in range({n})]\n"
        "n = C.card_row(cards, lambda c: C.site_card(c, on_select=lambda s: None), key='t', empty_text='No sites.')\n"
        "st.write(f'drawn={n}')\n")
    assert any(f"drawn={n}" in m.value for m in at.markdown)
    assert len(at.button) == n
    assert sum("sr-site" in m.value for m in at.markdown) == n
    assert any("No sites." in c.value for c in at.caption) == (n == 0)


def test_card_row_layout_wraps_and_never_forces_page_overflow():
    rule = re.search(r'\[class\*="st-key-sr_row_"\]>\*\{([^}]*)\}', T.CSS).group(1)
    assert "min-width:min(280px,100%)" in rule          # a card can shrink to the screen width
    small = T.CSS[T.CSS.index("@media (max-width:640px)"):]
    assert '[class*="st-key-sr_row_"]>*{max-width:100%;}' in small


# ---------------------------------------------------------------------------------------------------------------
# hero_feature and hero

def test_hero_feature_html_title_description_and_optional_parts():
    bare = C.hero_feature_html("A title", "A description.")
    assert "<h1>A title</h1>" in bare and "<p>A description.</p>" in bare
    assert "sr-kicker" not in bare and "sr-hero-points" not in bare and "sr-meta" not in bare
    full = C.hero_feature_html("T", "D", kicker="K", points=["one", "two"], meta=["m1", "m2"])
    assert full.count("<li>") == 2 and "<span>m1</span>" in full and '<div class="sr-kicker">K</div>' in full


def test_hero_feature_actions_are_optional_and_work():
    none = run_snippet("C.hero_feature('T', 'D')\n")
    assert len(none.button) == 0
    at = run_snippet(
        "def go():\n"
        "    st.session_state['went'] = True\n"
        "pressed = C.hero_feature('T', 'D', primary=C.HeroAction('Go', 'go', go), secondary=C.HeroAction('More', 'more'))\n"
        "st.write(f'pressed={pressed} went={st.session_state.get(\"went\")}')\n")
    assert [b.label for b in at.button] == ["Go", "More"]
    at.button[1].click().run()
    assert any("pressed=more went=None" in m.value for m in at.markdown)
    at.button[0].click().run()
    assert any("pressed=go went=True" in m.value for m in at.markdown)


def test_hero_states_the_platform_purpose_without_overclaiming():
    html = C.hero_feature_html(C.HERO_TITLE, C.HERO_DESCRIPTION, C.HERO_KICKER, C.HERO_POINTS)
    txt = text_of(html)
    assert "Shoreline Remediation Intelligence" in txt
    assert "scientifically governed decision-support platform" in txt
    for point in ("Explore shoreline environments and assessment sites.", "Compare remediation pathways with natural recovery.",
                  "Understand the evidence, uncertainty and limitations behind decisions."):
        assert point in txt
    assert not re.search(r"\d", txt)                    # no statistic in the platform message
    for claim in ("validated", "proven", "accurate", "all habitats", "%"):
        assert claim not in txt.lower()


def test_old_hero_call_signature_still_works():
    at = run_snippet("C.hero('A custom subtitle.', [('Scope tag', 'green')])\n")
    md = " ".join(m.value for m in at.markdown)
    assert "A custom subtitle." in md and "<span>Scope tag</span>" in md and md.count("<h1>") == 1


def test_there_is_one_hero_implementation():
    src = (ROOT / "src" / "shoreline_remediation" / "ui_components.py").read_text(encoding="utf-8")
    assert src.count("def hero(") == 1 and src.count("def hero_feature(") == 1
    assert src.count("<h1>") == 1                       # only hero_feature_html writes the page title


# ---------------------------------------------------------------------------------------------------------------
# Real data on the cards

def test_featured_site_values_come_from_repository_files():
    from src.shoreline_remediation import registry, site_view
    from src.shoreline_remediation.site_evidence import load_sites

    cards = {c.site_id: c for c in site_view.featured_sites()}
    assert set(cards) <= set(site_view.HABITAT_BY_KEY)      # every card opens an existing habitat entry
    row = load_sites()
    row = row[row.cell == site_view.EXAMPLE_CELL].iloc[0]
    facts = {f.label: f for f in cards["marsh"].facts}
    assert facts["Coordinates"].value == f"{row.lat:.3f}° N, {abs(row.lon):.3f}° W"
    assert facts["SCAT maximum oiling"].value == T.OILING_LABELS[row.max_oiling] and facts["SCAT maximum oiling"].kind == "observed"
    assert facts["Edge loss 2010 to 2015 (aerial images)"].value == f"{row.observed_rate:.2f} m/yr"
    assert facts["Mean fetch"].value == f"{row.fetch_mean_m:,.0f} m" and facts["Mean fetch"].kind == "derived"

    eff = pd.read_csv(ROOT / "results" / "mangrove" / "effect_by_year.csv")
    eff = eff[eff.outcome == "root_documented_dead_share"]
    mfacts = {f.label: f for f in cards["mangrove"].facts}
    assert mfacts["Study sites"].value == f"{eff.n_oiled_sites.iloc[0]} oiled, {eff.n_unoiled_sites.iloc[0]} unoiled"
    assert mfacts["Coordinates"].value is None and mfacts["Cleanup outcome data"].value is None

    assert all(f.value is None for f in cards["beach_fine"].facts)   # a habitat entry has no site numbers at all

    states = {r["model_id"]: r["state"] for r in registry.governance_table()}
    for model_id, card in (("edge_loss_v1", "marsh"), ("composer_natural_recovery_v1", "marsh"), ("mangrove_damage_v1", "mangrove"),
                           ("beach_sand_persistence_v1", "beach_fine")):
        grade = T.TIER_TO_GRADE[states[model_id]]
        assert any(g == grade and t.startswith(T.GRADES[grade]["label"]) for g, t in cards[card].evidence), model_id
    # Only the marsh card carries a Validated chip; no card states a recommendation, a model estimate or a percentage.
    assert [k for k, c in cards.items() if any(g == "validated" for g, _ in c.evidence)] == ["marsh"]
    for c in cards.values():
        txt = text_of(C.site_card_html(c))
        assert "sr-status" not in C.site_card_html(c) and "%" not in txt and "Model estimate" not in txt
        assert "recommended" not in txt.lower() and "confidence" not in txt.lower()


def test_select_site_ignores_unknown_identifiers():
    at = run_snippet("from src.shoreline_remediation import site_view\n"
                     "site_view.select_site('rocky_shore_not_wired')\n"
                     "st.write('habitat=' + str(st.session_state.get('site_habitat')))\n")
    assert any("habitat=None" in m.value for m in at.markdown)


# ---------------------------------------------------------------------------------------------------------------
# Integration with the dashboard

def test_dashboard_shows_hero_section_headers_and_real_cards(app):
    md = " ".join(m.value for m in app.markdown)
    assert md.count("<h1>") == 1 and "Shoreline Remediation Intelligence" in md
    assert "<h2>Featured locations</h2>" in md and "<h2>Explore habitats</h2>" in md
    for name in ("Bay Jimmy, Barataria Bay", "Bahía Las Minas", "Fine-to-medium sand beach"):
        assert name in md
    labels = [b.label for b in app.button]
    for label in ("Explore shoreline sites", "How evidence is graded", "Open the Bay Jimmy assessment",
                  "Open the mangrove evidence", "Open the beach screening"):
        assert label in labels


@pytest.mark.parametrize("site_id", ["mangrove", "beach_fine", "marsh"])
def test_site_card_opens_the_existing_assessment(site_id):
    at = fresh()
    at.segmented_control(key="page").set_value("site").run()
    at.segmented_control(key="page").set_value("landing").run()   # start on another page, then use the landing cards
    at.button(key=f"sr_open_site_{site_id}").click().run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "site"
    assert at.segmented_control(key="site_habitat").value == site_id
    if site_id == "marsh":
        assert at.radio(key="site_mode").value.startswith("Worked example")


def test_hero_primary_action_opens_the_site_assessment_page():
    at = fresh()
    at.button(key="sr_act_hero_platform_explore").click().run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="page").value == "site"
    assert at.segmented_control(key="site_habitat").value == "marsh"


def test_hero_secondary_action_opens_the_evidence_legend():
    at = fresh()
    before = sum("sr-legend-row" in m.value for m in at.markdown)
    at.button(key="sr_act_hero_platform_evidence").click().run()
    assert not at.exception, at.exception
    assert sum("sr-legend-row" in m.value for m in at.markdown) > before


def test_option_cards_show_the_category_the_pipeline_assigned():
    app = fresh()
    app.segmented_control(key="page").set_value("site").run()   # the option cards are on the site page
    from src.shoreline_remediation import site_view, ui_evidence as E, ui_pipeline as P
    from src.shoreline_remediation.site_evidence import load_sites

    sites = load_sites()
    site = {**sites[sites.cell == site_view.EXAMPLE_CELL].iloc[0].to_dict(), "source": "edge cell"}
    report, err = P.decision_for_site(P.site_items(site), "light", None)
    assert err is None
    view = E.report_view(report)
    md = [m.value for m in app.markdown]
    shown = [o for o in view.options if o.cls != "E"]       # class E options are listed in a table, not as cards
    assert shown
    for o in shown:
        card = next(m for m in md if f'<div class="sr-opt-title">{o.name}</div>' in m)
        assert f"sr-status-{o.category.replace('_', '-')}" in card
        assert dp.CATEGORY_LABELS[o.category] in text_of(card)
        assert text_of(C.status_label(o.category, o.category_label)) == text_of(C.status_label(o.category))


def test_components_take_only_the_category_wording_from_the_pipeline():
    import ast
    tree = ast.parse((ROOT / "src" / "shoreline_remediation" / "ui_components.py").read_text(encoding="utf-8"))
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("decision_pipeline")
             for a in n.names]
    assert names == ["CATEGORY_LABELS"]                 # no rule, no classifier, no run_decision in the component layer
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_category" not in called and "run_decision" not in called
