"""One place for every colour, label and piece of user-facing wording in the dashboard (decision D40).

Why this file exists: colours and wording used to be scattered over three files as hard-coded hex values, which broke dark
mode and used red against green on one scale. Nothing here imports Streamlit at module level, so the HTML report can use it
too.

Rules the palette follows
    * Oiling class: one single-hue ramp (dark brown to pale orange), never red against green. "No oil observed" is a blue ring.
    * Recommendation classes A to E: Okabe-Ito colours (safe for the common kinds of colour blindness). Colour is never the
      only signal: every chip also carries a letter, a symbol and words.
    * Evidence grades: encoded by the fill style as well as the hue (solid, hatched, dashed outline, dotted), so the weak
      grades look visibly different from the validated one even in greyscale.
    * Chips use a translucent tint and the inherited text colour, so they read on the dark dashboard and in the light report.
    * PALETTE holds the eight V5.1 design colours. COMPONENT_CSS (chips, class labels) is shared with the HTML report;
      CSS adds the dark dashboard shell on top of it. Evidence meaning is never changed by the theme, only contrast.
"""
from __future__ import annotations

from html import escape

# ---------------------------------------------------------------------------------------------------------------
# Okabe-Ito categorical palette (Okabe and Ito 2008). Used for recommendation classes and for chart series.
OKABE_ITO = {"orange": "#E69F00", "sky_blue": "#56B4E9", "bluish_green": "#009E73", "yellow": "#F0E442",
             "blue": "#0072B2", "vermillion": "#D55E00", "reddish_purple": "#CC79A7"}
SERIES_COLOURS = [OKABE_ITO["blue"], OKABE_ITO["orange"], OKABE_ITO["bluish_green"], OKABE_ITO["reddish_purple"],
                  OKABE_ITO["sky_blue"], OKABE_ITO["vermillion"]]
BRAND = {"light": "#0F5C5C", "dark": "#28B8A5"}

# ---------------------------------------------------------------------------------------------------------------
# V5.1 design palette (CLAUDE.md section 6). The dashboard is dark only; the HTML report stays light for printing.
# The same eight values are set in .streamlit/config.toml (a test keeps the two in step).
PALETTE = {
    "background": "#080D17",            # page
    "secondary_background": "#111A29",  # sidebar, inputs, table headers
    "card": "#182438",                  # cards, expanders, panels
    "teal": "#28B8A5",                  # primary accent, primary actions
    "blue": "#4E9BE8",                  # secondary accent, links
    "highlight": "#B6D9CF",             # kickers, hover, emphasis
    "text": "#F4F7FA",                  # primary text
    "text_secondary": "#A6B2C2",        # captions, labels
}
# Derived from the palette (not new brand colours): hairline border and a raised-card tone.
PALETTE_DERIVED = {"border": "#26344D", "card_raised": "#1F2E47"}
# Evidence-grade chip colours on the dark dashboard. Same hue family as GRADES[...]["hex"] (which the light HTML
# report keeps), lightened so the outline has at least 3:1 contrast against the card colour. Meanings are unchanged.
GRADE_COLOURS_DARK = {"validated": "#28B8A5", "experimental": "#E0A83A", "rules": "#4E9BE8", "ai": "#B3A8C4",
                      "illustrative": "#A6B2C2"}
NEUTRAL = "#6B7280"       # mid grey that reads on both light and dark backgrounds (stroke, not text)

# ---------------------------------------------------------------------------------------------------------------
# Oiling class (SCAT maximum oiling). Single hue, sequential. Values from the UI review colour table.
OILING_ORDER = ["Heavy", "Moderate", "Light", "Very_Light", "NOO"]
OILING_LABELS = {"Heavy": "Heavy", "Moderate": "Moderate", "Light": "Light", "Very_Light": "Very light",
                 "NOO": "No oil observed"}
OILING_COLOURS = {
    "light": {"Heavy": "#7F2704", "Moderate": "#D94801", "Light": "#FD8D3C", "Very_Light": "#FDD0A2", "NOO": "#5B8FB0"},
    "dark": {"Heavy": "#FF9A5A", "Moderate": "#F07A2E", "Light": "#C2561A", "Very_Light": "#8A4A22", "NOO": "#7FB0D0"},
}
SELECTED_SITE_COLOUR = {"light": "#000000", "dark": "#FFFFFF"}


def oiling_colour(oiling: str, dark: bool = False) -> str:
    return OILING_COLOURS["dark" if dark else "light"].get(str(oiling), NEUTRAL)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


# ---------------------------------------------------------------------------------------------------------------
# Recommendation classes (decision pipeline classes A to E). Okabe-Ito hues + a symbol so colour is never alone.
CLASS_STYLE = {
    "A": {"colour": OKABE_ITO["bluish_green"], "symbol": "✓", "name": "Field evidence of benefit",
          "plain": "Allowed, and field plots show a benefit over natural recovery."},
    "B": {"colour": OKABE_ITO["sky_blue"], "symbol": "?", "name": "Allowed by screening, benefit not established",
          "plain": "Allowed by screening. Either the evidence shows no clear difference from natural recovery, or no eligible "
                   "evidence exists yet; each option says which. Neither is a finding of harm or of no effect."},
    "C": {"colour": OKABE_ITO["blue"], "symbol": "=", "name": "Natural recovery (the reference)",
          "plain": "Do nothing active and monitor. Every other option is compared with this."},
    "D": {"colour": OKABE_ITO["orange"], "symbol": "!", "name": "Harm reported under some conditions",
          "plain": "Allowed, but harm is reported under some conditions. Check them first."},
    "E": {"colour": NEUTRAL, "symbol": "×", "name": "Excluded",
          "plain": "Excluded by a rule or by evidence of harm. Not recommended here."},
}
CLASS_ORDER = ["A", "B", "C", "D", "E"]


def class_style(cls: str) -> dict:
    return CLASS_STYLE.get(str(cls), {"colour": NEUTRAL, "symbol": "·", "name": f"Class {cls}", "plain": ""})


# ---------------------------------------------------------------------------------------------------------------
# Evidence grades. Strongest first; the "weakest" of several grades is the one with the highest index.
GRADES = {
    "validated": {"label": "Validated", "icon": ":material/verified:", "badge": "primary", "hex": "#0F766E",
                  "css": "sr-g-validated",
                  "legend": "Tested on data the model never saw (whole basins or studies held out). Still one spill and one coast."},
    "experimental": {"label": "Experimental", "icon": ":material/science:", "badge": "yellow", "hex": "#B7791F",
                     "css": "sr-g-experimental",
                     "legend": "Built from real field data but not passed a held-out test, or a test it only partly passed."},
    "rules_literature": {"label": "Rules and literature only", "icon": ":material/menu_book:", "badge": "blue", "hex": "#2F6DB5",
                         "css": "sr-g-rules",
                         "legend": "Screening rules and published findings. No site-specific forecast. The literature table is "
                                   "AI-extracted and not yet checked by a person."},
    "ai_proposed": {"label": "AI-proposed", "icon": ":material/smart_toy:", "badge": "violet", "hex": "#8A7F99",
                    "css": "sr-g-ai",
                    "legend": "A range or verdict written by an AI assistant from the literature. It is not field evidence and "
                              "has not been reviewed by a person."},
    "illustrative": {"label": "Illustrative", "icon": ":material/draw:", "badge": "gray", "hex": "#6B7280",
                     "css": "sr-g-illustrative",
                     "legend": "Shows how a method behaves. Uses assumed numbers or did not beat a simple baseline on held-out data."},
}
GRADE_ORDER = list(GRADES)
OUT_OF_SCOPE = {"label": "Out of scope", "icon": ":material/block:", "badge": "gray", "hex": "#6B7280", "css": "sr-g-illustrative",
                "legend": "The tool does not cover this request."}


# Coverage tiers of the landing page habitat cards (V5.1 Session 2 Stage 3). Derived in site_view.habitat_coverage().
COVERAGE_TIERS = {
    "numerical": {"label": "Numerical validation available", "grade": "validated",
                  "legend": "A model passed a held-out test, for a limited scope that the card states."},
    "experimental": {"label": "Experimental evidence", "grade": "experimental",
                     "legend": "Built from real field data but not passed a held-out test."},
    "screening": {"label": "Screening and literature only", "grade": "rules_literature",
                  "legend": "Rules and published findings; no numerical forecast."},
    "unsupported": {"label": "Unsupported or insufficient evidence", "grade": "out_of_scope",
                    "legend": "No assessment is made; the platform abstains."},
}


def grade_info(grade: str) -> dict:
    if grade == "out_of_scope":
        return OUT_OF_SCOPE
    return GRADES.get(grade) or {"label": str(grade).replace("_", " ").capitalize(), "icon": ":material/help:", "badge": "gray",
                                 "hex": NEUTRAL, "css": "sr-g-illustrative", "legend": ""}


def weakest_grade(grades) -> str:
    """The least well supported of several grades (unknown names count as the weakest)."""
    known = [g for g in grades if g]
    if not known:
        return "rules_literature"
    return max(known, key=lambda g: GRADE_ORDER.index(g) if g in GRADE_ORDER else len(GRADE_ORDER))


def grade_md(grade: str, text: str | None = None) -> str:
    """Streamlit markdown badge, e.g. ':yellow-badge[:material/science: Experimental]'."""
    info = grade_info(grade)
    return f":{info['badge']}-badge[{info['icon']} {text or info['label']}]"


def grade_html(grade: str, text: str | None = None) -> str:
    info = grade_info(grade)
    return f'<span class="sr-chip {info["css"]}" title="{escape(info["legend"])}">{escape(text or info["label"])}</span>'


def class_html(cls: str, with_name: bool = True) -> str:
    s = class_style(cls)
    name = f' <span class="sr-cls-name">{escape(s["name"])}</span>' if with_name else ""
    return (f'<span class="sr-cls sr-cls-{escape(str(cls))}" style="--c:{s["colour"]}" title="{escape(s["plain"])}">'
            f'<b>{escape(s["symbol"])} {escape(str(cls))}</b>{name}</span>')


# ---------------------------------------------------------------------------------------------------------------
# Recommendation categories (decision D41). Keys are decision_pipeline.CATEGORY_ORDER; tests/test_ui_stage2.py checks
# that the two stay in step. This is presentation only: a symbol and a colour that reads on dark cards. The wording
# comes from decision_pipeline.CATEGORY_LABELS, and the category itself is assigned only by run_decision().
CATEGORY_STYLE = {
    "recommended": {"symbol": "\u2713", "colour": PALETTE["teal"]},
    "conditional": {"symbol": "!", "colour": "#E0A83A"},
    "natural_recovery_monitoring": {"symbol": "=", "colour": PALETTE["blue"]},
    "no_demonstrated_benefit": {"symbol": "\u2248", "colour": PALETTE["highlight"]},
    "insufficient_evidence": {"symbol": "?", "colour": "#B3A8C4"},
    "excluded": {"symbol": "\u00d7", "colour": "#9AA5B5"},
}
# A missing or unrecognised category is shown as such. It is never given the look of a real category.
CATEGORY_UNKNOWN = {"symbol": "\u00b7", "colour": "#9AA5B5"}
STATUS_MISSING_TEXT = "Status not available"
STATUS_UNRECOGNISED_TEXT = "Unrecognised status"

# How a value on a site card was obtained (CLAUDE.md section 4: keep observed, derived and modelled values apart).
VALUE_KINDS = {"observed": "Observed", "derived": "Derived", "model": "Model estimate", "screening": "Screening level",
               "record": "Site record", "unavailable": "Not available"}

# Tier of a whole report (DecisionReport.scope_tier) -> grade used for its chip. New tiers fall back to a grey chip.
TIER_TO_GRADE = {"validated": "validated", "experimental": "experimental", "rules_and_literature": "rules_literature",
                 "rules_literature": "rules_literature", "out_of_scope": "out_of_scope",
                 "unsupported_habitat": "out_of_scope",
                 "insufficient_evidence": "rules_literature", "insufficient": "rules_literature"}
TIER_TEXT = {"validated": "Validated", "experimental": "Experimental", "rules_and_literature": "Rules and literature only",
             "out_of_scope": "Out of scope", "unsupported_habitat": "Unsupported habitat", "insufficient_evidence": "Insufficient evidence", "insufficient": "Insufficient evidence"}

# ---------------------------------------------------------------------------------------------------------------
# Plain-language labels (the leads are not machine-learning specialists).
LABELS = {
    "edge_loss": "Expected marsh-edge loss, metres per year, with a 90% range",
    "edge_loss_short": "Marsh-edge loss, metres per year",
    "edge_saved": "Marsh edge saved compared with natural recovery (metres, 90% range)",
    "veg_gain": "Extra vegetation cover compared with natural recovery (fraction of reference cover, 90% range)",
    "natural_recovery": "Natural recovery (doing nothing active)",
    "rule_order": "Rule-screening order",
    "assumed_score": "Assumed ecological score (0 to 10, higher means less disturbance)",
    "interval_note": ("The 90% range means: if the model is right, 9 times out of 10 the real value falls inside it. A range that "
                      "crosses zero means the difference cannot be told apart from doing nothing."),
    "overlap_note": "These ranges overlap. The order shown is not evidence that one option is better than another.",
    "illustrative_chart": ("Illustrative only: this process model did not beat a simple empirical curve on held-out stations "
                           "(FINDINGS_V4 section 37)."),
    "ai_range": "AI-proposed range, not evidence",
    "rule_screen_text": ("Rule screening (existing shoreline-cleanup rules), ordered inside each tier by an ASSUMED ecological "
                         "score. It is not an effectiveness ranking."),
}

# ---------------------------------------------------------------------------------------------------------------
# Scope and limits (one panel; replaces many same-weight caveat boxes). Keys are habitat keys.
SCOPE_ONE_LINE = {
    "marsh": "Scope: Deepwater Horizon 2010, light crude, Louisiana salt marsh. Results are associations, not proven causes.",
    "mangrove": "Scope: one spill (Panama, 1986), red mangrove fringe, years 1 to 5. Describes oiling damage only, not cleanup.",
    "beach": "Scope: rules and literature only. No site-specific beach forecast yet.",
    "rocky": "Scope: rules and literature only. No site record and no forecast for rocky shores.",
    "scenario": "Scope: rule screening and an assumed process model. Illustrative only; nothing here is validated against field outcomes.",
}
SCOPE_LIMITS = {
    "marsh": [
        "One spill (Deepwater Horizon 2010), one oil, Louisiana salt marsh. Transfer was tested between Louisiana basins, not to other spills.",
        "Associations, not proven causes: heavy oiling and the cleanup that followed are mixed together in the edge-loss data.",
        "Treatment differences come from one site (Bay Jimmy), 5 to 9 plots per group, and are the same at every heavily oiled site. "
        "The scenario composer that makes them is experimental.",
        "Physical (edge loss) and biological (vegetation) recovery only. There is no soil or sediment chemistry model, so no chemical recovery forecast.",
        "Out of scope: active river delta, water-dominated or plume areas where land and water mapping fails, and any non-salt-marsh shoreline.",
        "AI-proposed ranges (shown hatched) come from an AI reading of the literature. They are not field evidence and have not been reviewed by a person.",
    ],
    "mangrove": [
        "One spill only: Bahia Las Minas, Panama, April 1986. Nothing here has been tested on another spill or oil.",
        "Caribbean coast, red mangrove (Rhizophora mangle) fringe only. Other regions and mangrove types were not tested.",
        "Years 1 to 5 after the spill only (leaves per shoot: years 3 to 5). Nothing is said about later years.",
        "No treatment or cleanup data: the model estimates the oiling effect (oiled minus unoiled sites), not the effect of any cleanup.",
        "The cleanup verdicts are AI-proposed from the literature and were not tested with the Galeta data.",
        "Licence of the source data is unclear; only site-level summaries are used.",
    ],
    "beach": [
        "No beach outcome model is connected yet. The options shown come from screening rules and published findings only.",
        "The literature table was extracted by AI assistants and has not been checked by a person.",
        "Beach habitats differ a lot (grain size, wave energy, how deep oil is buried). One verdict does not transfer between them without checking.",
    ],
    "rocky": [
        "No rocky-shore outcome model and no observed rocky-shore site records are connected. The options shown come from screening rules and published findings only.",
        "Screening eligibility is not demonstrated remediation benefit. 'Insufficient evidence' means the platform cannot compare an option with natural recovery; it is not a finding of no benefit.",
        "The literature table was extracted by AI assistants and has not been checked by a person. NOAA ESI ratings need source verification before use.",
        "Natural recovery with monitoring stays the reference option unless a defensible comparison exists.",
    ],
    "scenario": [
        "The rule screening uses existing shoreline-cleanup rules. It orders options inside each tier by an ASSUMED ecological score. It is not an effectiveness ranking.",
        "The process model uses assumed rates. It did not beat a simple empirical curve on held-out stations (FINDINGS_V4 section 37), so its curves are illustrative.",
        "The suitability model trained on rule-generated (synthetic) labels is outside the decision path and is shown only as a method test.",
        "Time-to-endpoint figures multiply assumed factors together. They carry no interval and should be read as rough orders of magnitude.",
        "What the evidence supports for the same scenario is in the section headed 'What the evidence supports'.",
    ],
}

# ---------------------------------------------------------------------------------------------------------------
# CSS, in two layers.
#   _COMPONENT: chips, class labels, AI-proposed blocks. No fixed text or background colours; chip colours are CSS
#               variables with light-safe fallbacks, so the printable HTML report can reuse it unchanged.
#   _APP:       the dark dashboard shell built on PALETTE: page, hero, cards, buttons, expanders, tables, focus rings.
# COMPONENT_CSS is what ui_report embeds; CSS is what the dashboard injects.
_COMPONENT = """
.sr-chip{display:inline-flex;align-items:center;gap:.3em;padding:.06rem .6rem;border-radius:999px;font-size:.78rem;font-weight:600;
  border:1.5px solid var(--c);white-space:nowrap;line-height:1.35;vertical-align:middle;}
.sr-g-validated{--c:var(--sr-g-validated,#0F766E);background:color-mix(in srgb,var(--c) 32%,transparent);}
.sr-g-experimental{--c:var(--sr-g-experimental,#B7791F);background:repeating-linear-gradient(45deg,transparent 0 4px,color-mix(in srgb,var(--c) 34%,transparent) 4px 6px);}
.sr-g-rules{--c:var(--sr-g-rules,#2F6DB5);border-style:dashed;background:transparent;}
.sr-g-ai{--c:var(--sr-g-ai,#8A7F99);border-style:dotted;background:repeating-linear-gradient(135deg,transparent 0 3px,color-mix(in srgb,var(--c) 26%,transparent) 3px 4px);}
.sr-g-illustrative{--c:var(--sr-g-illustrative,#6B7280);border-style:dotted;font-style:italic;background:transparent;}
.sr-cls{display:inline-flex;align-items:center;gap:.35em;padding:.06rem .55rem;border-radius:6px;font-size:.85rem;
  border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 18%,transparent);white-space:nowrap;vertical-align:middle;}
.sr-cls b{font-weight:700;}
.sr-cls-E .sr-cls-name{text-decoration:line-through;opacity:.8;}
.sr-ai-block{--c:var(--sr-g-ai,#8A7F99);border:1.5px dotted var(--c);border-radius:8px;padding:.6rem .9rem;margin:.4rem 0;
  background:repeating-linear-gradient(135deg,transparent 0 6px,color-mix(in srgb,var(--c) 12%,transparent) 6px 8px);}
.sr-ai-block table{border-collapse:collapse;width:100%;font-size:.9rem;opacity:.85;}
.sr-ai-block th,.sr-ai-block td{text-align:left;padding:.2rem .5rem;border-bottom:1px solid color-mix(in srgb,var(--c) 35%,transparent);}
.sr-opt-title{font-weight:650;font-size:1.02rem;margin:.1rem 0 .25rem 0;}
.sr-muted{opacity:.75;font-size:.88rem;}
.sr-scope{border-left:4px solid var(--c,var(--sr-teal,#0F5C5C));padding:.35rem .8rem;margin:.2rem 0 .6rem 0;
  background:color-mix(in srgb,var(--c,var(--sr-teal,#0F5C5C)) 10%,transparent);border-radius:0 8px 8px 0;font-size:.92rem;}
.sr-answer{font-size:1.12rem;line-height:1.45;font-weight:560;margin:.2rem 0 .4rem 0;}
.sr-legend-row{margin:.25rem 0;font-size:.88rem;}
.sr-hero{padding:.2rem 0 .6rem 0;}
.sr-hero h1{font-size:2rem;margin:0 0 .25rem 0;letter-spacing:0;}
.sr-hero p{margin:0;opacity:.85;font-size:1.02rem;}
"""

_ROOT_VARS = (":root{"
              + "".join(f"--sr-{k.replace('_', '-')}:{v};" for k, v in {**PALETTE, **PALETTE_DERIVED}.items())
              + "".join(f"--sr-g-{k}:{v};" for k, v in GRADE_COLOURS_DARK.items())
              + "--sr-radius:14px;--sr-radius-sm:8px;--sr-shadow:0 10px 30px rgba(0,0,0,.35);"
                "--sr-space-1:.25rem;--sr-space-2:.5rem;--sr-space-3:1rem;--sr-space-4:1.5rem;--sr-space-5:2.5rem;}")

_APP = _ROOT_VARS + """
/* ---- Page shell ---- */
.stApp{background:
  radial-gradient(1100px 520px at 12% -8%,color-mix(in srgb,var(--sr-teal) 13%,transparent),transparent 62%),
  radial-gradient(900px 480px at 96% 0%,color-mix(in srgb,var(--sr-blue) 11%,transparent),transparent 60%),
  var(--sr-background);background-attachment:fixed;color:var(--sr-text);}
[data-testid="stHeader"]{background:transparent;height:2.25rem;min-height:2.25rem;}
[data-testid="stMainBlockContainer"]{max-width:1440px;padding-top:1.1rem;padding-bottom:3rem;}
[data-testid="stSidebar"]{background:var(--sr-secondary-background);border-right:1px solid var(--sr-border);}
::selection{background:color-mix(in srgb,var(--sr-teal) 45%,transparent);}
*{scrollbar-color:var(--sr-border) transparent;}

/* ---- Typography ---- */
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--sr-text);letter-spacing:-.012em;line-height:1.2;}
.stApp h2{font-size:1.55rem;font-weight:700;}
.stApp h3{font-size:1.2rem;font-weight:650;}
.stApp [data-testid="stCaptionContainer"],.stApp small{color:var(--sr-text-secondary);opacity:1;}  /* default .6 opacity fails AA on dark */
.stApp a{color:var(--sr-blue);text-underline-offset:2px;}
.stApp a:hover{color:var(--sr-highlight);}
.stApp hr{border-color:var(--sr-border);}

/* ---- Hero: featured banner (gradients only, no imagery). hero_feature() renders into a container keyed sr_hero_* ---- */
.sr-hero,[class*="st-key-sr_hero_"]{position:relative;overflow:hidden;padding:clamp(1.4rem,3.2vw,2.6rem) clamp(1.2rem,3.4vw,2.8rem);margin:0 0 var(--sr-space-3) 0;
  border:1px solid var(--sr-border);border-radius:calc(var(--sr-radius) + 4px);box-shadow:var(--sr-shadow);
  background:
    linear-gradient(100deg,var(--sr-background) 0%,color-mix(in srgb,var(--sr-background) 72%,transparent) 46%,transparent 100%),
    radial-gradient(120% 150% at 100% 0%,color-mix(in srgb,var(--sr-teal) 42%,transparent),transparent 58%),
    radial-gradient(90% 130% at 78% 115%,color-mix(in srgb,var(--sr-blue) 38%,transparent),transparent 62%),
    var(--sr-secondary-background);}
.sr-hero::after,[class*="st-key-sr_hero_"]::after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;
  background:linear-gradient(90deg,var(--sr-teal),var(--sr-blue) 55%,transparent);}
[class*="st-key-sr_hero_"] .sr-hero{padding:0;margin:0;border:0;border-radius:0;box-shadow:none;background:none;overflow:visible;}
[class*="st-key-sr_hero_"] .sr-hero::after{content:none;}
.sr-hero h1{font-size:clamp(1.7rem,3.4vw,2.75rem);font-weight:750;letter-spacing:-.022em;margin:0 0 .5rem 0;padding:0;max-width:22ch;}
.sr-hero p{font-size:clamp(.98rem,1.25vw,1.12rem);line-height:1.55;color:var(--sr-text-secondary);opacity:1;max-width:68ch;}
.sr-hero-points{list-style:none;margin:.9rem 0 0 0;padding:0;display:grid;gap:.35rem;max-width:68ch;}
.sr-hero-points li{position:relative;margin:0;padding:0 0 0 1.15rem;color:var(--sr-text);font-size:.96rem;line-height:1.45;}
.sr-hero-points li::before{content:"";position:absolute;left:0;top:.55em;width:.45rem;height:.45rem;border-radius:50%;background:var(--sr-teal);}
.sr-meta{display:flex;flex-wrap:wrap;gap:.4rem;margin:.9rem 0 .35rem 0;}
.sr-meta span{font-size:.78rem;font-weight:600;color:var(--sr-text-secondary);border:1px solid var(--sr-border);border-radius:999px;
  padding:.1rem .65rem;background:color-mix(in srgb,var(--sr-background) 55%,transparent);}

/* ---- Reusable layout pieces (used by the component layer) ---- */
.sr-kicker{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sr-highlight);margin:0 0 .3rem 0;}
.sr-section{margin:var(--sr-space-5) 0 var(--sr-space-3) 0;}
.sr-section h2{margin:0;padding:0;}
.sr-card{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);padding:var(--sr-space-3) 1.15rem;
  transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;}
.sr-card:hover{border-color:color-mix(in srgb,var(--sr-teal) 55%,var(--sr-border));box-shadow:var(--sr-shadow);transform:translateY(-2px);}
.sr-row{display:flex;gap:var(--sr-space-3);overflow-x:auto;padding:.3rem .1rem 1rem .1rem;scroll-snap-type:x proximity;}
.sr-row>*{flex:0 0 clamp(230px,24vw,320px);scroll-snap-align:start;}
/* Section header: kicker, heading, optional description and right-hand metadata */
.sr-section-head{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:.4rem 1.5rem;}
.sr-section p.sr-section-desc{margin:.35rem 0 0 0;color:var(--sr-text-secondary);font-size:.95rem;line-height:1.5;max-width:72ch;}
.sr-section-meta{color:var(--sr-text-secondary);font-size:.85rem;}
/* Status label: recommendation category from the decision pipeline (symbol + words; colour never carries meaning alone) */
.sr-status{display:inline-flex;align-items:baseline;gap:.4em;padding:.1rem .6rem;border-radius:6px;font-size:.8rem;font-weight:650;
  line-height:1.4;border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);color:var(--sr-text);
  vertical-align:middle;max-width:100%;}
.sr-status-unknown{border-style:dotted;background:transparent;font-style:italic;}
/* Card row: card_row() renders a wrapping Streamlit flex container keyed sr_row_*, so cards keep working buttons */
[class*="st-key-sr_row_"]{align-items:stretch;}
[class*="st-key-sr_row_"]>*{flex:1 1 280px;min-width:min(280px,100%);max-width:440px;}
/* Site card: site_card() renders into a container keyed sr_site_*, styled like .sr-card */
[class*="st-key-sr_site_"]{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);
  padding:var(--sr-space-3) 1.15rem;height:100%;transition:border-color .18s ease,box-shadow .18s ease;}
[class*="st-key-sr_site_"]:hover{border-color:color-mix(in srgb,var(--sr-teal) 55%,var(--sr-border));box-shadow:var(--sr-shadow);}
/* Habitat coverage cards (landing page): one top-border colour per tier; unopenable and unsupported entries are dashed and dimmed */
[class*="st-key-sr_site_hab_numerical_"]{border-top:4px solid var(--sr-g-validated);}
[class*="st-key-sr_site_hab_experimental_"]{border-top:4px solid var(--sr-g-experimental);}
[class*="st-key-sr_site_hab_screening_"]{border-top:4px solid var(--sr-g-rules);}
[class*="st-key-sr_site_hab_unsupported_"]{border:1px dashed var(--sr-text-secondary);border-top:4px dashed var(--sr-text-secondary);opacity:.85;}
[class*="st-key-sr_site_hab_screening_esi_"]{border-style:dashed;border-top-style:solid;}
[class*="st-key-sr_site_hab_numerical_"] .sr-kicker{color:var(--sr-g-validated);}
[class*="st-key-sr_site_hab_experimental_"] .sr-kicker{color:var(--sr-g-experimental);}
[class*="st-key-sr_site_hab_screening_"] .sr-kicker{color:var(--sr-g-rules);}
[class*="st-key-sr_site_hab_unsupported_"] .sr-kicker{color:var(--sr-text-secondary);}
/* Coverage legend and "how it works" steps */
.sr-tiers{display:flex;flex-wrap:wrap;gap:.4rem .6rem;margin:.25rem 0 .9rem 0;}
.sr-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin:.5rem 0 1rem 0;}
.sr-step{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);padding:1rem 1.15rem;}
.sr-step b{display:inline-flex;align-items:center;justify-content:center;width:1.7rem;height:1.7rem;border-radius:50%;
  background:color-mix(in srgb,var(--sr-teal) 22%,transparent);border:1px solid var(--sr-teal);margin-bottom:.5rem;}
.sr-step p{margin:0;color:var(--sr-text);font-size:.95rem;line-height:1.5;}
.sr-site h3{font-size:1.12rem;font-weight:700;margin:0;padding:0;}
.sr-site-where{color:var(--sr-text-secondary);font-size:.86rem;margin:.15rem 0 .5rem 0;}
.sr-site p.sr-site-desc{font-size:.9rem;line-height:1.5;margin:0 0 .6rem 0;color:var(--sr-text);}
.sr-site dl{margin:0 0 .6rem 0;display:grid;gap:.3rem;}
.sr-site dl div{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.1rem .75rem;font-size:.85rem;
  border-top:1px solid var(--sr-border);padding-top:.3rem;}
.sr-site dt{color:var(--sr-text-secondary);font-weight:500;}
.sr-site dd{margin:0;font-weight:600;text-align:right;}
.sr-site dd small{font-weight:500;color:var(--sr-text-secondary);font-size:.76rem;margin-left:.35em;}
.sr-site dd.sr-unavailable{font-weight:500;font-style:italic;color:var(--sr-text-secondary);}
.sr-site-evidence{display:flex;flex-wrap:wrap;gap:.35rem;margin:0 0 .35rem 0;}
.sr-muted{opacity:1;color:var(--sr-text-secondary);}
.sr-answer{color:var(--sr-text);}
.sr-scope{border-radius:0 var(--sr-radius-sm) var(--sr-radius-sm) 0;color:var(--sr-text);}

/* ---- Streamlit surfaces ---- */
[data-testid="stExpander"] details{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);overflow:hidden;}
[data-testid="stExpander"] summary{font-weight:600;}
[data-testid="stExpander"] summary:hover{color:var(--sr-highlight);}
[data-testid="stSidebar"] [data-testid="stExpander"] details{background:var(--sr-card);}
[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlock"][class*="border"]{border-color:var(--sr-border);}
[data-testid="stMetric"]{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);padding:.85rem 1rem;}
[data-testid="stMetricLabel"]{color:var(--sr-text-secondary);}
[data-testid="stMetricValue"]{color:var(--sr-text);font-weight:700;letter-spacing:-.01em;}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--sr-border);border-radius:var(--sr-radius-sm);overflow:hidden;}
[data-testid="stAlert"]{border-radius:var(--sr-radius-sm);}
[data-testid="stWidgetLabel"] p{color:var(--sr-text-secondary);font-weight:600;}

/* ---- Buttons: teal primary with dark text (7.6:1), quiet secondary ---- */
.stApp button[kind="primary"],.stApp button[data-testid="stBaseButton-primary"]{background:var(--sr-teal);border-color:var(--sr-teal);
  color:var(--sr-background);font-weight:700;}
.stApp button[kind="primary"]:hover,.stApp button[data-testid="stBaseButton-primary"]:hover{background:var(--sr-highlight);
  border-color:var(--sr-highlight);color:var(--sr-background);}
.stApp button[kind="primary"] p,.stApp button[data-testid="stBaseButton-primary"] p{color:inherit;}
.stApp button[kind="secondary"],.stApp button[data-testid="stBaseButton-secondary"]{background:var(--sr-card);border:1px solid var(--sr-border);
  color:var(--sr-text);font-weight:600;}
.stApp button[kind="secondary"]:hover,.stApp button[data-testid="stBaseButton-secondary"]:hover{border-color:var(--sr-teal);color:var(--sr-highlight);}
.stApp button,.stApp [role="tab"],.stApp summary{transition:background-color .15s ease,border-color .15s ease,color .15s ease;}

/* ---- Tabs ---- */
.stApp [data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--sr-border);}
.stApp [data-baseweb="tab"]{color:var(--sr-text-secondary);font-weight:600;}
.stApp [data-baseweb="tab"][aria-selected="true"]{color:var(--sr-text);}

/* ---- V5.4 shell: brand header band with the navigation on the right (container keyed sr_shell; the nav widget is keyed page) ---- */
.st-key-sr_shell{background:linear-gradient(100deg,var(--sr-secondary-background),color-mix(in srgb,var(--sr-secondary-background) 80%,var(--sr-teal)));
  border:1px solid var(--sr-border);border-radius:var(--sr-radius);padding:.55rem 1rem;margin:0 0 .9rem 0;}
.st-key-sr_shell [data-testid="stHorizontalBlock"]{align-items:center;gap:.9rem 1rem;}
.st-key-sr_shell [data-testid="stColumn"]{min-width:0;}
.sr-brand{display:flex;align-items:center;gap:.7rem;min-height:2.6rem;}
.sr-brand-mark{width:2.3rem;height:2.3rem;flex:0 0 auto;}
.sr-brand-name{font-size:1.2rem;font-weight:750;letter-spacing:-.01em;line-height:1.15;color:var(--sr-text);}
.sr-brand-tag{font-size:.8rem;padding-bottom:.1rem;color:var(--sr-text-secondary);line-height:1.3;}
.st-key-page{margin-left:auto;width:fit-content;max-width:100%;}
.stApp button:disabled{opacity:.45;}
.st-key-page [role="radiogroup"],.st-key-page [data-testid="stButtonGroup"]{flex-wrap:wrap;}
.st-key-page button[aria-checked="true"],.st-key-page button[aria-pressed="true"]{background:color-mix(in srgb,var(--sr-teal) 22%,transparent);
  border-color:var(--sr-teal);color:var(--sr-highlight);font-weight:700;}
.sr-intro{margin:0;color:var(--sr-text-secondary);font-size:.95rem;line-height:1.45;max-width:90ch;}
.st-key-sr_act_hero_platform_evidence button{white-space:nowrap;}

/* ---- Home: map column, scenario panel, step cards ---- */
.sr-map-legend{background:var(--sr-secondary-background);border:1px solid var(--sr-border);border-radius:var(--sr-radius-sm);
  padding:.55rem .8rem;margin:.5rem 0 .4rem 0;font-size:.82rem;color:var(--sr-text);}
.sr-map-legend-title{font-weight:650;margin-bottom:.3rem;}
.sr-leg-row{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem 1rem;margin:.15rem 0;}
.sr-leg-label{color:var(--sr-text-secondary);font-weight:600;}
.sr-leg-item{display:inline-flex;align-items:center;gap:.35rem;color:var(--sr-text);}
.sr-leg-item i{display:inline-block;width:.8rem;height:.8rem;border-radius:50%;}
.sr-leg-item i.sr-leg-ring{background:transparent;border:2px solid #fff;}
.sr-leg-item i.sr-leg-pin{background:var(--sr-teal);border:2px solid #fff;}
.sr-map-legend-note{color:var(--sr-text-secondary);margin-top:.3rem;font-size:.8rem;line-height:1.4;}
.st-key-sr_panel{background:var(--sr-card);border:1px solid var(--sr-border);border-radius:var(--sr-radius);padding:1rem 1.1rem;}
.sr-panel-title{font-size:1.15rem;font-weight:700;letter-spacing:-.01em;margin:0 0 .5rem 0;color:var(--sr-text);}
.sr-place{background:var(--sr-secondary-background);border:1px solid var(--sr-border);border-radius:var(--sr-radius-sm);padding:.6rem .8rem;margin:0 0 .4rem 0;}
.sr-place-name{font-weight:700;font-size:1rem;}
.sr-place-src{color:var(--sr-text-secondary);font-size:.76rem;margin:.1rem 0 .35rem 0;}
.sr-place dl{margin:0;display:grid;gap:.2rem;}
.sr-place dl div{display:flex;justify-content:space-between;gap:.6rem;font-size:.82rem;border-top:1px solid var(--sr-border);padding-top:.2rem;}
.sr-place dt{color:var(--sr-text-secondary);}
.sr-place dd{margin:0;font-weight:600;text-align:right;}
.st-key-sr_panel [data-testid="stVerticalBlock"]{gap:.55rem;}
.st-key-sr_panel [data-testid="stMarkdownContainer"] p{font-size:.9rem;}
.st-key-sr_panel{padding:.85rem 1rem;}
.sr-stepcards{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin:1rem 0 .4rem 0;}
.sr-stepcard{display:flex;gap:.75rem;align-items:flex-start;background:var(--sr-card);border:1px solid var(--sr-border);
  border-radius:var(--sr-radius);padding:.8rem 1rem;}
.sr-stepcard b{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;width:1.9rem;height:1.9rem;border-radius:50%;
  background:color-mix(in srgb,var(--sr-teal) 22%,transparent);border:1px solid var(--sr-teal);color:var(--sr-highlight);}
.sr-stepcard h3{font-size:.98rem;margin:0 0 .15rem 0;padding:0;}
.sr-stepcard p{margin:0;font-size:.84rem;line-height:1.4;color:var(--sr-text-secondary);}
@media (max-width:1100px){.sr-stepcards{grid-template-columns:repeat(2,1fr);}}
@media (max-width:640px){.sr-stepcards{grid-template-columns:1fr;}
  .st-key-sr_shell [data-testid="stHorizontalBlock"]{flex-direction:column;align-items:stretch;}
  .st-key-sr_shell [data-testid="stColumn"]{width:100%;flex:1 1 auto;}
  .st-key-page{margin-left:0;}}

/* ---- V5.4 Assessment results: title row, outcome card, key flags, alternatives, expected outcome, validation ---- */
.sr-rtitle{font-size:clamp(1.45rem,2.4vw,1.9rem);font-weight:750;letter-spacing:-.015em;line-height:1.15;color:var(--sr-text);}
.sr-crumbs{display:flex;flex-wrap:wrap;gap:.15rem .55rem;margin-top:.3rem;color:var(--sr-text-secondary);font-size:.92rem;}
.sr-crumbs span+span::before{content:"|";margin-right:.55rem;color:var(--sr-border);}
[class*="st-key-sr_outcome_"],.st-key-sr_flags,.st-key-sr_expected,.st-key-sr_validation{border:1px solid var(--sr-border);border-radius:var(--sr-radius);
  background:var(--sr-card);padding:1rem 1.2rem;}
[class*="st-key-sr_outcome_"]{--c:var(--sr-blue);border:1.5px solid var(--c);box-shadow:var(--sr-shadow);
  background:linear-gradient(135deg,color-mix(in srgb,var(--c) 20%,var(--sr-card)),var(--sr-card) 72%);}
.st-key-sr_outcome_recommended{--c:var(--sr-teal);}
.st-key-sr_outcome_conditional{--c:#E0A83A;}
.st-key-sr_outcome_reference{--c:var(--sr-blue);}
.st-key-sr_outcome_abstain{--c:#B3A8C4;}
.sr-oc-kicker{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sr-highlight);}
.sr-oc-title{font-size:clamp(1.15rem,1.7vw,1.5rem);font-weight:740;line-height:1.28;letter-spacing:-.01em;margin:.2rem 0 .5rem 0;color:var(--sr-text);}
.sr-oc-pill{display:inline-block;margin:0 0 .55rem 0;padding:.1rem .65rem;border-radius:999px;font-size:.8rem;font-weight:650;color:var(--sr-text);
  border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 18%,transparent);}
.sr-oc-opt{font-size:1.2rem;font-weight:700;margin:.2rem 0;color:var(--sr-text);}
.sr-alt-opt{margin:.15rem 0 .1rem 0;}
[class*="st-key-sr_outcome_"] li{font-size:.86rem;line-height:1.35;margin-bottom:.15rem;}
.sr-alt-name{font-weight:650;}
.sr-fl-title{font-size:1.15rem;font-weight:700;margin:0 0 .35rem 0;color:var(--sr-text);}
.st-key-sr_flags{border-color:color-mix(in srgb,#E0A83A 55%,var(--sr-border));}
.st-key-sr_flags [data-testid="stMarkdownContainer"] li{font-size:.88rem;line-height:1.4;margin-bottom:.2rem;}
.sr-sec{font-size:.78rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sr-highlight);margin:.9rem 0 .1rem 0;}
.sr-card-title{font-size:1.1rem;font-weight:700;margin:0 0 .4rem 0;color:var(--sr-text);}
[class*="st-key-sr_alt_"]{background:var(--sr-card);}
.sr-reftable{width:100%;border-collapse:collapse;font-size:.85rem;margin:.1rem 0 .4rem 0;}
.sr-reftable th{text-align:left;color:var(--sr-text-secondary);font-weight:600;border-bottom:1px solid var(--sr-border);padding:.25rem .4rem;}
.sr-reftable td{padding:.35rem .4rem;border-bottom:1px solid var(--sr-border);vertical-align:top;}
.sr-reftable code{font-size:.78rem;}
.sr-thissite{background:var(--sr-secondary-background);border:1px solid var(--sr-border);border-radius:var(--sr-radius-sm);padding:.6rem .8rem;margin:.4rem 0;}
.sr-ts-title{font-weight:700;font-size:.95rem;margin-bottom:.3rem;}
.sr-thissite dl{margin:0;display:grid;gap:.2rem;}
.sr-thissite dl div{display:flex;justify-content:space-between;gap:.8rem;font-size:.84rem;border-top:1px solid var(--sr-border);padding-top:.2rem;}
.sr-thissite dt{color:var(--sr-text-secondary);}
.sr-thissite dd{margin:0;font-weight:700;text-align:right;white-space:nowrap;}
.sr-stats{display:flex;flex-wrap:wrap;gap:.35rem .5rem;margin:.2rem 0 .3rem 0;}
.sr-stats span{background:var(--sr-secondary-background);border:1px solid var(--sr-border);border-radius:var(--sr-radius-sm);padding:.2rem .6rem;font-size:.82rem;}
.sr-stats b{color:var(--sr-highlight);margin-right:.3rem;}
@media (max-width:640px){.sr-thissite dl div{flex-direction:column;gap:0;}.sr-thissite dd{text-align:left;white-space:normal;}
  .sr-reftable{table-layout:fixed;}.sr-reftable td,.sr-reftable th,.sr-reftable code{overflow-wrap:anywhere;word-break:break-word;}}

/* ---- Accessibility: visible keyboard focus, reduced motion, small screens ---- */
.stApp :is(button,a,summary,input,textarea,[role="tab"],[role="radio"],[role="checkbox"],[tabindex]):focus-visible{
  outline:2px solid var(--sr-highlight);outline-offset:2px;border-radius:6px;}
@media (prefers-reduced-motion:reduce){.stApp *,.sr-card{transition:none !important;animation:none !important;}
  .sr-card:hover{transform:none;}}
@media (max-width:640px){
  [data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem;padding-top:1rem;}
  .sr-hero{border-radius:var(--sr-radius);}
  .sr-row>*{flex-basis:78vw;}
  .sr-chip,.sr-cls{white-space:normal;}
  [class*="st-key-sr_row_"]>*{max-width:100%;}
  .sr-hero h1{max-width:none;}
}
"""

COMPONENT_CSS = "<style>" + _COMPONENT + "</style>"
CSS = "<style>" + _COMPONENT + _APP + "</style>"
