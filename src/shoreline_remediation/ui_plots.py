"""Figures of the Assessment page (V5.4 plot-first). Drawing only: every value comes from comparison.plot_records() or from the
report's packaged curve, which have already decided what is drawn and in which order. Nothing here filters, sorts, ranks or
computes an estimate."""
from __future__ import annotations

import altair as alt
import pandas as pd

from src.shoreline_remediation import comparison as K, ui_theme as T

_SHAPES = {K.FIELD: "circle", K.FIELD_MODEL: "diamond", K.SCENARIO_MODEL: "square"}


def effect_chart(comp: K.Comparison, text_colour: str = "#F4F7FA", mark_colour: str | None = None) -> alt.Chart | None:
    """Horizontal dot-and-interval plot of treatment contrasts against the comparator, with a dashed zero line. Each row is
    labelled inside the plot with the method, its evidence basis, its value and (when it is not ranked) why, so the figure does
    not depend on hover or on colour and keeps its full width on a narrow screen. Returns None when there is nothing to draw."""
    records = K.plot_records(comp)
    if not records:
        return None
    d = pd.DataFrame(records)
    order = list(d["row"])
    lo, hi = min(0.0, float(d["lo"].min())), max(0.0, float(d["hi"].max()))
    pad = (hi - lo) * 0.08 or 1.0
    unit = comp.target.unit_short or comp.target.unit
    d["x0"] = lo - pad
    d["text"] = [f"{r['label']} ({r['basis'].lower()})\n{r['value_text']} {unit}" + (f"\n{r['status']}" if r["status"] else "")
                 for r in records]
    colour = mark_colour or T.BRAND["dark"]
    x = alt.X("lo:Q", title=comp.target.axis_short or comp.target.axis, scale=alt.Scale(domain=[lo - pad, hi + pad], nice=False),
              axis=alt.Axis(titleLimit=1000, labelFontSize=12, titleFontSize=12, format="+.0f" if hi - lo >= 5 else "+.1f", grid=True,
                            tickCount=5, labelOverlap=True))
    y = alt.Y("row:N", sort=order, axis=None, scale=alt.Scale(paddingInner=0, paddingOuter=0))
    tip = [alt.Tooltip("label:N", title="Method"), alt.Tooltip("basis:N", title="Evidence basis"),
           alt.Tooltip("value_text:N", title="Estimate (90% interval)")]
    base = alt.Chart(d)
    bars = base.mark_rule(size=3, color=colour, yOffset=26).encode(x=x, x2="hi:Q", y=y, tooltip=tip)
    dots = base.mark_point(filled=True, size=170, opacity=1, color=colour, stroke=text_colour, strokeWidth=1, yOffset=26).encode(
        x="estimate:Q", y=y, tooltip=tip,
        shape=alt.Shape("basis:N", scale=alt.Scale(domain=list(_SHAPES), range=list(_SHAPES.values())),
                        legend=alt.Legend(title="Evidence basis", orient="bottom") if d["basis"].nunique() > 1 else None))
    labels = base.mark_text(align="left", baseline="bottom", dx=4, yOffset=-2, fontSize=12.5, fontWeight=600, lineBreak="\n",
                            lineHeight=15, color=text_colour).encode(x="x0:Q", y=y, text="text:N")
    zero = alt.Chart(pd.DataFrame({"x": [0.0]})).mark_rule(strokeDash=[6, 4], strokeWidth=2, color=text_colour, opacity=0.75).encode(x="x:Q")
    return (zero + bars + dots + labels).properties(height=64 + 100 * len(d))


def persistence_chart(horizons, median, lo, hi, text_colour: str = "#F4F7FA", mark_colour: str | None = None) -> alt.Chart:
    """Share of survey segments still recorded with visible oil at each packaged time point, with its 90% interval and the value
    written beside each point. The time points are the model card's; the line only joins them and nothing is interpolated."""
    colour = mark_colour or T.BRAND["dark"]
    d = pd.DataFrame({"day": [f"Day {int(h)}" for h in horizons], "median": median, "lo": lo, "hi": hi})
    d["text"] = [f"{m:.0%}" for m in d["median"]]
    x = alt.X("day:N", sort=list(d["day"]), title="Days after the first oiled survey",
              axis=alt.Axis(labelAngle=0, labelFontSize=12, titleFontSize=12))
    y = alt.Y("lo:Q", title="Segments still oiled", scale=alt.Scale(domain=[0, 1]),
              axis=alt.Axis(format="%", tickCount=5, labelFontSize=12, titleFontSize=12))
    tip = ["day", alt.Tooltip("median:Q", format=".0%", title="Share still oiled"), alt.Tooltip("lo:Q", format=".0%", title="90% low"),
           alt.Tooltip("hi:Q", format=".0%", title="90% high")]
    base = alt.Chart(d)
    line = base.mark_line(color=colour, strokeWidth=2, opacity=0.55).encode(x=x, y=alt.Y("median:Q"))
    bars = base.mark_rule(size=3, color=colour).encode(x=x, y=y, y2="hi:Q", tooltip=tip)
    dots = base.mark_point(filled=True, size=150, opacity=1, color=colour, stroke=text_colour, strokeWidth=1).encode(x=x, y="median:Q", tooltip=tip)
    labels = base.mark_text(dx=24, fontSize=12.5, fontWeight=600, color=text_colour).encode(x=x, y="median:Q", text="text:N")
    return (line + bars + dots + labels).properties(height=280)


# ---------------------------------------------------------------------------------------------------------------
# Illustrative recovery curves (Bay Jimmy). SYNTHETIC: fixed formulas written here, not data, not a fitted model and not
# a forecast. They are kept in this drawing module on purpose so nothing in the evidence, comparison or decision code can
# read them. The solid part (to 2018) is synthetic too; it is not an observation.

ILLUSTRATIVE_LABEL = "Illustrative scenarios \u00b7 synthetic values"
PROJECTION_LABEL = "Illustrative projection"
ILLUSTRATIVE_NOTE = ("Every value in this figure is synthetic, including the solid lines before 2018. The curves are fixed shapes "
                     "chosen for illustration: they are not observations, not model output and not a forecast, and they are not "
                     "used by the findings, the screening statuses or the recommendations above. Dotted lines and shading mark "
                     "the illustrative projection after 2018.")
_SPLIT_YEAR = 2018
_SERIES = {"Untreated baseline": "#A6B2C2", "Manual removal": "#28B8A5", "Mechanical removal": "#E0A83A",
           "Mechanical removal + planting": "#D07BA8"}
_PANELS = ("Marsh-edge erosion rate (m/year)", "Total vegetation cover (%)", "Residual soil PAH concentration index")
# series -> (erosion floor, erosion pulse, vegetation ceiling, vegetation time constant, PAH decay rate). Synthetic constants.
_SHAPES_SYNTHETIC = {"Untreated baseline": (0.97, 0.55, 80.0, 8.0, 0.170), "Manual removal": (0.95, 0.27, 82.0, 5.5, 0.215),
                     "Mechanical removal": (0.95, 0.72, 80.0, 9.0, 0.200), "Mechanical removal + planting": (0.84, 0.38, 82.0, 4.0, 0.195)}


def illustrative_recovery_data() -> pd.DataFrame:
    """Deterministic synthetic curves, 2010 to 2030 in quarter-year steps: columns year, value, series, panel, segment
    ("solid" to 2018, "dotted" from 2018; the 2018 point is in both so the two parts join)."""
    import math
    rows = []
    for i in range(81):
        t = i / 4.0
        year = 2010 + t
        for name, (floor, pulse, ceiling, tau, k) in _SHAPES_SYNTHETIC.items():
            values = (floor + (1.2 - floor) * math.exp(-t / 6.0) + pulse * t * math.exp(-t / 2.5),
                      17.0 + (ceiling - 17.0) * (1.0 - math.exp(-t / tau)), 10.0 * math.exp(-k * t))
            for panel, value in zip(_PANELS, values):
                for segment in (["solid"] if year < _SPLIT_YEAR else ["solid", "dotted"] if year == _SPLIT_YEAR else ["dotted"]):
                    rows.append({"year": year, "value": round(value, 4), "series": name, "panel": panel, "segment": segment})
    return pd.DataFrame(rows)


def illustrative_recovery_chart(text_colour: str = "#F4F7FA") -> alt.VConcatChart:
    """Three stacked panels on one year axis (2010 to 2030) with one legend: four absolute-value curves per panel, solid to 2018
    and dotted after it, the dotted span shaded and labelled. No uncertainty bands: nothing here is estimated."""
    d = illustrative_recovery_data()
    colour = alt.Color("series:N", title=None, scale=alt.Scale(domain=list(_SERIES), range=list(_SERIES.values())),
                       legend=alt.Legend(orient="top", direction="horizontal", columns=2, labelLimit=260, symbolStrokeWidth=3))
    span = pd.DataFrame({"x": [_SPLIT_YEAR], "x2": [2030], "label": [PROJECTION_LABEL]})
    panels = []
    for i, panel in enumerate(_PANELS):
        last = i == len(_PANELS) - 1
        x = alt.X("year:Q", scale=alt.Scale(domain=[2010, 2030], nice=False), title="Year" if last else None,
                  axis=alt.Axis(format="d", values=[2010, 2012, 2015, 2018, 2022, 2026, 2030], labelFontSize=12))
        y = alt.Y("value:Q", title=panel, scale=alt.Scale(zero=True), axis=alt.Axis(labelFontSize=12, titleFontSize=12, titleLimit=400))
        base = alt.Chart(d[d["panel"] == panel])
        tip = [alt.Tooltip("series:N", title="Synthetic scenario"), alt.Tooltip("year:Q", format=".0f"), alt.Tooltip("value:Q", format=".2f")]
        shade = alt.Chart(span).mark_rect(color="#4E9BE8", opacity=0.10).encode(x="x:Q", x2="x2:Q")
        split = alt.Chart(span).mark_rule(color=text_colour, opacity=0.6).encode(x="x:Q")
        note = alt.Chart(span).mark_text(align="left", baseline="top", dx=6, dy=4, fontSize=11, color=text_colour, opacity=0.85).encode(
            x="x:Q", y=alt.value(0), text="label:N")
        solid = base.transform_filter(alt.datum.segment == "solid").mark_line(strokeWidth=2.6).encode(x=x, y=y, color=colour, tooltip=tip)
        dotted = base.transform_filter(alt.datum.segment == "dotted").mark_line(strokeWidth=2.6, strokeDash=[2, 4]).encode(
            x=x, y=y, color=colour, tooltip=tip)
        panels.append((shade + split + solid + dotted + note).properties(height=190, title=alt.TitleParams(panel, anchor="start", fontSize=13)))
    return alt.vconcat(*panels, spacing=18).resolve_scale(color="shared", x="shared").properties(
        title=alt.TitleParams(ILLUSTRATIVE_LABEL, subtitle="Bay Jimmy. Solid to 2018, dotted after 2018. Not observations.", anchor="start",
                              fontSize=15, subtitleColor=text_colour))
