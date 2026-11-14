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
    * Chips use a translucent tint and the theme's own text colour, so they read in light and in dark mode.
"""
from __future__ import annotations

from html import escape

# ---------------------------------------------------------------------------------------------------------------
# Okabe-Ito categorical palette (Okabe and Ito 2008). Used for recommendation classes and for chart series.
OKABE_ITO = {"orange": "#E69F00", "sky_blue": "#56B4E9", "bluish_green": "#009E73", "yellow": "#F0E442",
             "blue": "#0072B2", "vermillion": "#D55E00", "reddish_purple": "#CC79A7"}
SERIES_COLOURS = [OKABE_ITO["blue"], OKABE_ITO["orange"], OKABE_ITO["bluish_green"], OKABE_ITO["reddish_purple"],
                  OKABE_ITO["sky_blue"], OKABE_ITO["vermillion"]]
BRAND = {"light": "#0F5C5C", "dark": "#4FB3B3"}
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
    "B": {"colour": OKABE_ITO["sky_blue"], "symbol": "?", "name": "No clear evidence either way",
          "plain": "Allowed, but the evidence does not show a benefit or a harm."},
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


# Tier of a whole report (DecisionReport.scope_tier) -> grade used for its chip. New tiers fall back to a grey chip.
TIER_TO_GRADE = {"validated": "validated", "experimental": "experimental", "rules_and_literature": "rules_literature",
                 "rules_literature": "rules_literature", "out_of_scope": "out_of_scope",
                 "insufficient_evidence": "rules_literature", "insufficient": "rules_literature"}
TIER_TEXT = {"validated": "Validated", "experimental": "Experimental", "rules_and_literature": "Rules and literature only",
             "out_of_scope": "Out of scope", "insufficient_evidence": "Insufficient evidence", "insufficient": "Insufficient evidence"}

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
    "scenario": [
        "The rule screening uses existing shoreline-cleanup rules. It orders options inside each tier by an ASSUMED ecological score. It is not an effectiveness ranking.",
        "The process model uses assumed rates. It did not beat a simple empirical curve on held-out stations (FINDINGS_V4 section 37), so its curves are illustrative.",
        "The suitability model trained on rule-generated (synthetic) labels is outside the decision path and is shown only as a method test.",
        "Time-to-endpoint figures multiply assumed factors together. They carry no interval and should be read as rough orders of magnitude.",
        "What the evidence supports for the same scenario is in the section headed 'What the evidence supports'.",
    ],
}

# ---------------------------------------------------------------------------------------------------------------
# CSS. Only what Streamlit's theme cannot do: chips, cards, hatched AI-proposed blocks. No fixed text or background colours.
CSS = """
<style>
.sr-hero{padding:.2rem 0 .6rem 0;}
.sr-hero h1{font-size:2rem;margin:0 0 .25rem 0;letter-spacing:0;}
.sr-hero p{margin:0;opacity:.85;font-size:1.02rem;}
.sr-chip{display:inline-flex;align-items:center;gap:.3em;padding:.06rem .6rem;border-radius:999px;font-size:.78rem;font-weight:600;
  border:1.5px solid var(--c);white-space:nowrap;line-height:1.35;vertical-align:middle;}
.sr-g-validated{--c:#0F766E;background:color-mix(in srgb,var(--c) 32%,transparent);}
.sr-g-experimental{--c:#B7791F;background:repeating-linear-gradient(45deg,transparent 0 4px,color-mix(in srgb,var(--c) 34%,transparent) 4px 6px);}
.sr-g-rules{--c:#2F6DB5;border-style:dashed;background:transparent;}
.sr-g-ai{--c:#8A7F99;border-style:dotted;background:repeating-linear-gradient(135deg,transparent 0 3px,color-mix(in srgb,var(--c) 26%,transparent) 3px 4px);}
.sr-g-illustrative{--c:#6B7280;border-style:dotted;font-style:italic;background:transparent;}
.sr-cls{display:inline-flex;align-items:center;gap:.35em;padding:.06rem .55rem;border-radius:6px;font-size:.85rem;
  border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 18%,transparent);white-space:nowrap;vertical-align:middle;}
.sr-cls b{font-weight:700;}
.sr-cls-E .sr-cls-name{text-decoration:line-through;opacity:.8;}
.sr-ai-block{border:1.5px dotted #8A7F99;border-radius:8px;padding:.6rem .9rem;margin:.4rem 0;
  background:repeating-linear-gradient(135deg,transparent 0 6px,color-mix(in srgb,#8A7F99 12%,transparent) 6px 8px);}
.sr-ai-block table{border-collapse:collapse;width:100%;font-size:.9rem;opacity:.85;}
.sr-ai-block th,.sr-ai-block td{text-align:left;padding:.2rem .5rem;border-bottom:1px solid color-mix(in srgb,#8A7F99 35%,transparent);}
.sr-opt-title{font-weight:650;font-size:1.02rem;margin:.1rem 0 .25rem 0;}
.sr-muted{opacity:.75;font-size:.88rem;}
.sr-scope{border-left:4px solid var(--c,#0F5C5C);padding:.35rem .8rem;margin:.2rem 0 .6rem 0;
  background:color-mix(in srgb,var(--c,#0F5C5C) 10%,transparent);border-radius:0 8px 8px 0;font-size:.92rem;}
.sr-answer{font-size:1.12rem;line-height:1.45;font-weight:560;margin:.2rem 0 .4rem 0;}
.sr-legend-row{margin:.25rem 0;font-size:.88rem;}
</style>
"""
