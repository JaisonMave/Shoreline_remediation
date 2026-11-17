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
