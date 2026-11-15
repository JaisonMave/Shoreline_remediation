"""V5.1 design foundation: the CLAUDE.md palette is the single source of colour for the dashboard, the Streamlit config
agrees with it, text contrast meets WCAG AA, and the theme does not change evidence semantics or darken the HTML report."""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import ui_theme as T  # noqa: E402

CLAUDE_MD_PALETTE = {"background": "#080D17", "secondary_background": "#111A29", "card": "#182438", "teal": "#28B8A5",
                     "blue": "#4E9BE8", "highlight": "#B6D9CF", "text": "#F4F7FA", "text_secondary": "#A6B2C2"}


def _lum(hex_colour: str) -> float:
    def chan(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(v) for v in T.hex_to_rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_palette_is_the_claude_md_palette():
    assert T.PALETTE == CLAUDE_MD_PALETTE


def test_streamlit_config_is_dark_and_matches_the_palette():
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    assert theme["base"] == "dark"
    assert "light" not in theme and "dark" not in theme          # one theme only: no light variant left behind
    assert theme["backgroundColor"] == T.PALETTE["background"]
    assert theme["secondaryBackgroundColor"] == T.PALETTE["secondary_background"]
    assert theme["primaryColor"] == T.PALETTE["teal"]
    assert theme["textColor"] == T.PALETTE["text"]
    assert theme["linkColor"] == T.PALETTE["blue"]
    assert theme["borderColor"] == T.PALETTE_DERIVED["border"]
    assert theme["sidebar"]["backgroundColor"] == T.PALETTE["secondary_background"]


def test_dashboard_css_exposes_every_palette_colour_as_a_variable():
    for key, value in T.PALETTE.items():
        assert f"--sr-{key.replace('_', '-')}:{value};" in T.CSS
    assert T.CSS.count("<style>") == 1 and T.CSS.strip().endswith("</style>")


def test_text_contrast_meets_wcag_aa_on_every_surface():
    for surface in ("background", "secondary_background", "card"):
        for text in ("text", "text_secondary", "highlight", "blue", "teal"):
            assert contrast(T.PALETTE[text], T.PALETTE[surface]) >= 4.5, (text, surface)
    assert contrast(T.PALETTE["background"], T.PALETTE["teal"]) >= 4.5       # dark label on the teal primary button
    assert contrast(T.PALETTE["background"], T.PALETTE["highlight"]) >= 4.5  # and on its hover state


def test_grade_and_class_outlines_are_visible_on_dark_cards():
    for colour in T.GRADE_COLOURS_DARK.values():
        assert contrast(colour, T.PALETTE["card"]) >= 3.0, colour             # WCAG 1.4.11 non-text contrast
    for cls in T.CLASS_ORDER:
        assert contrast(T.CLASS_STYLE[cls]["colour"], T.PALETTE["card"]) >= 3.0, cls


def test_theme_keeps_evidence_semantics():
    assert T.GRADE_ORDER == ["validated", "experimental", "rules_literature", "ai_proposed", "illustrative"]
    assert T.CLASS_ORDER == ["A", "B", "C", "D", "E"]
    # Weak grades stay distinguishable without colour: hatched, dashed, dotted.
    assert "repeating-linear-gradient" in T.CSS.split(".sr-g-experimental{")[1].split("}")[0]
    assert "border-style:dashed" in T.CSS.split(".sr-g-rules{")[1].split("}")[0]
    assert "border-style:dotted" in T.CSS.split(".sr-g-ai{")[1].split("}")[0]
    assert "border-style:dotted" in T.CSS.split(".sr-g-illustrative{")[1].split("}")[0]
    assert "line-through" in T.CSS                                            # excluded options stay struck through


def test_html_report_css_stays_light_and_printable():
    for value in T.PALETTE.values():
        assert value not in T.COMPONENT_CSS
    assert ".stApp" not in T.COMPONENT_CSS and ".sr-chip" in T.COMPONENT_CSS


def test_css_has_focus_reduced_motion_and_small_screen_rules():
    assert ":focus-visible" in T.CSS
    assert "prefers-reduced-motion" in T.CSS
    assert "@media (max-width:640px)" in T.CSS
