"""Figures of the Assessment page (V5.4 plot-first). Drawing only: every value comes from comparison.plot_records() or from the
report's packaged curve, which have already decided what is drawn and in which order. Nothing here filters, sorts, ranks or
computes an estimate."""
from __future__ import annotations

import math

import altair as alt
import pandas as pd

from src.shoreline_remediation import comparison as K, recovery_view as RV, ui_theme as T

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


def illustrative_recovery_charts(text_colour: str = "#F4F7FA") -> list[tuple[str, alt.LayerChart]]:
    """Separate responsive panels, all synthetic, with the same explicit scale on every time-bearing layer."""
    d = illustrative_recovery_data()
    colour = alt.Color("series:N", title=None, scale=alt.Scale(domain=list(_SERIES), range=list(_SERIES.values())),
                       legend=alt.Legend(orient="top", columns=1, labelLimit=240, symbolStrokeWidth=3))
    span = pd.DataFrame({"x": [_SPLIT_YEAR], "x2": [2030], "label": [PROJECTION_LABEL]})
    panels = []
    for panel, unit in zip(_PANELS, ("m/year", "%", "PAH index")):
        scale = alt.Scale(domain=[2010, 2030], nice=False, zero=False)
        axis = alt.Axis(format="d", values=[2010, 2015, 2020, 2025, 2030], labelFontSize=12, labelOverlap=True)
        x = alt.X("year:Q", scale=scale, title="Year", axis=axis)
        span_x = alt.X("x:Q", scale=scale, title="Year", axis=axis)
        y = alt.Y("value:Q", title=unit, scale=alt.Scale(zero=True), axis=alt.Axis(labelFontSize=12, titleFontSize=12))
        base = alt.Chart(d[d["panel"] == panel])
        tip = [alt.Tooltip("series:N", title="Synthetic scenario"), alt.Tooltip("year:Q", format=".2f"), alt.Tooltip("value:Q", format=".2f")]
        shade = alt.Chart(span).mark_rect(color=T.PALETTE["blue"], opacity=0.10).encode(x=span_x, x2="x2:Q")
        split = alt.Chart(span).mark_rule(color=text_colour, opacity=0.6).encode(x=span_x)
        note = alt.Chart(span).mark_text(align="left", baseline="top", dx=6, dy=4, fontSize=11, color=text_colour, opacity=0.85).encode(
            x=span_x, y=alt.value(0), text="label:N")
        solid = base.transform_filter(alt.datum.segment == "solid").mark_line(strokeWidth=2.6).encode(x=x, y=y, color=colour, tooltip=tip)
        dotted = base.transform_filter(alt.datum.segment == "dotted").mark_line(strokeWidth=2.6, strokeDash=[2, 4]).encode(
            x=x, y=y, color=colour, tooltip=tip)
        chart = (shade + split + solid + dotted + note).properties(
            height=360, autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        panels.append((panel, chart))
    return panels


# ---------------------------------------------------------------------------------------------------------------
# Recovery view panels (recovery_view.Panel). Drawing only: marks follow the series kind, nothing is computed or extended here.
#   point positions are exact dates or period midpoints; horizontal segments show the full period, never a cosmetic date offset
#   fitted decline reference                  -> solid line with an interval band between the first and last campaign
# There is no dotted line: no series here is a forward projection.

X_DOMAIN = [2010.0, 2018.5]
_RECOVERY_SHAPES = {RV.FIELD: "circle", RV.SCENARIO: "square", RV.REFERENCE: "diamond", RV.OBSERVATION: "triangle-up"}


def _fmt(v, lo, hi, digits=2) -> str:
    base = f"{v:.{digits}f}"
    return base + (f" (90% {lo:.{digits}f} to {hi:.{digits}f})" if lo is not None and hi is not None else "")


def panel_records(panel: RV.Panel) -> dict[str, pd.DataFrame]:
    """Plot records retain true survey dates, full period support and the identity of every interval."""
    segs, whisk, pts, curve = [], [], [], []
    for s in panel.series:
        for q in s.points:
            row = {"series": s.label, "key": s.key, "kind": s.kind, "x0": q.x0, "x1": q.x1, "x": (q.x0 + q.x1) / 2,
                   "value": q.value, "lo": q.lo, "hi": q.hi, "time": s.time_support, "interval": s.interval or "No interval available",
                   "source": s.source, "estimate": _fmt(q.value, q.lo, q.hi), "basis": RV.KIND_TEXT[s.kind]}
            if s.kind == RV.DECLINE:
                curve.append(row)
                continue
            pts.append(row)
            if q.x1 > q.x0:
                segs.append(row)
            if q.lo is not None and q.hi is not None:
                whisk.append(row)
    return {k: pd.DataFrame(v) for k, v in (("segs", segs), ("whisk", whisk), ("pts", pts), ("curve", curve))}


def recovery_panel_chart(panel: RV.Panel, colours: dict[str, str], text_colour: str = "#F4F7FA",
                         height: int = 340, common_year_axis: bool = False) -> alt.LayerChart | None:
    """Absolute values over supported time only. Axis padding is whitespace, never extrapolation."""
    if not panel.series:
        return None
    d = panel_records(panel)
    keys = list(dict.fromkeys(s.key for s in panel.series))
    colour = alt.Color("key:N", scale=alt.Scale(domain=keys, range=[colours[k] for k in keys]), legend=None)
    lows = [v for s in panel.series for q in s.points for v in (q.value, q.lo) if v is not None]
    highs = [v for s in panel.series for q in s.points for v in (q.value, q.hi) if v is not None]
    lo, hi = min(lows + [0.0]), max(highs + ([100.0] if panel.unit == "%" else []))
    pad = (hi - lo) * 0.06
    first = min(q.x0 for s in panel.series for q in s.points)
    last = max(q.x1 for s in panel.series for q in s.points)
    time_pad = max(0.35, (last - first) * 0.05)
    domain = X_DOMAIN if common_year_axis else [first - time_pad, last + time_pad]
    years = list(range(math.ceil(domain[0]), math.floor(domain[1]) + 1))
    ticks = years[::max(1, math.ceil(len(years) / 5))]
    xscale = alt.Scale(domain=domain, nice=False, zero=False)
    yscale = alt.Scale(domain=[lo - pad if lo < 0 else 0, hi + pad], nice=False, zero=False)
    xaxis = alt.Axis(format="d", values=ticks, labelFontSize=12, titleFontSize=12, labelOverlap=True)
    ytitle = panel.unit if panel.unit != "index" else "PAH index"
    x = alt.X("x:Q", scale=xscale, title="Year", axis=xaxis)
    y = alt.Y("value:Q", scale=yscale, title=ytitle, axis=alt.Axis(labelFontSize=12, titleFontSize=12, titleLimit=420))
    tip = [alt.Tooltip("series:N", title="Series"), alt.Tooltip("basis:N", title="Evidence"),
           alt.Tooltip("x0:Q", title="Time start (year)", format=".2f"), alt.Tooltip("x1:Q", title="Time end (year)", format=".2f"),
           alt.Tooltip("estimate:N", title=f"Estimate ({panel.unit}; 90% interval)"),
           alt.Tooltip("time:N", title="Time support"), alt.Tooltip("interval:N", title="Interval type"),
           alt.Tooltip("source:N", title="Source")]
    layers = [alt.Chart(pd.DataFrame({"v": [0.0]})).mark_rule(color=text_colour, opacity=0.35, strokeWidth=1).encode(y=alt.Y("v:Q", scale=yscale))] if lo < 0 else []
    if not d["curve"].empty:
        c = alt.Chart(d["curve"])
        layers += [c.mark_area(opacity=0.22).encode(x=x, y=alt.Y("lo:Q", scale=yscale, title=ytitle), y2="hi:Q", color=colour),
                   c.mark_line(strokeWidth=3).encode(x=x, y=y, color=colour, tooltip=tip, order="x:Q")]
    if not d["segs"].empty:
        s = alt.Chart(d["segs"])
        layers.append(s.mark_rule(strokeWidth=3, opacity=0.65).encode(
            x=alt.X("x0:Q", scale=xscale, axis=xaxis, title="Year"), x2="x1:Q", y=y, color=colour, tooltip=tip))
    if not d["whisk"].empty:
        w = alt.Chart(d["whisk"])
        layers.append(w.mark_rule(strokeWidth=1.8, opacity=0.75).encode(
            x=x, y=alt.Y("lo:Q", scale=yscale, title=ytitle), y2="hi:Q", color=colour, tooltip=tip))
        for bound in ("lo", "hi"):
            layers.append(w.mark_tick(orient="horizontal", size=10, thickness=1.5).encode(
                x=x, y=alt.Y(f"{bound}:Q", scale=yscale, title=ytitle), color=colour, tooltip=tip))
    if not d["pts"].empty:
        p = alt.Chart(d["pts"])
        kinds = list(dict.fromkeys(d["pts"]["kind"]))
        layers.append(p.mark_point(filled=True, size=95, opacity=1, stroke=text_colour, strokeWidth=0.8).encode(
            x=x, y=y, color=colour, tooltip=tip,
            shape=alt.Shape("kind:N", scale=alt.Scale(domain=kinds, range=[_RECOVERY_SHAPES[k] for k in kinds]), legend=None)))
    return alt.layer(*layers).properties(height=height, autosize=alt.AutoSizeParams(type="fit", contains="padding"))


TRAJECTORY_DASH = {"fit": [1, 0], "conditional": [7, 5]}


def trajectory_records(panel) -> dict[str, pd.DataFrame]:
    """Long tables of one recovery_trajectories.TrajectoryPanel: curve samples with their band, and observed group means."""
    curve, obs = [], []
    for c in panel.curves:
        for x, y, lo, hi in zip(c.x, c.y, c.lo, c.hi):
            curve.append({"key": c.key, "series": c.label, "role": c.role, "x": x, "value": y, "lo": lo, "hi": hi,
                          "estimate": _fmt(y, lo, hi), "equation": c.equation, "interval": c.interval})
    for o in panel.observed:
        for x, m, lo, hi, n in zip(o.x, o.mean, o.lo, o.hi, o.n):
            obs.append({"key": o.key, "series": o.label, "x": x, "value": m, "lo": lo, "hi": hi, "n": n,
                        "estimate": _fmt(m, lo, hi), "time": o.dates, "source": o.source})
    return {"curve": pd.DataFrame(curve), "obs": pd.DataFrame(obs)}


def trajectory_chart(panel, colours: dict[str, str], text_colour: str = "#F4F7FA", height: int = 340) -> alt.LayerChart | None:
    """Continuous fitted or conditional curves (solid or dashed, with their band) over the observed group means (circles and 90%
    whiskers). One layered chart; every layer shares explicit x and y scales. Axis padding is whitespace, never extrapolation."""
    if not panel.curves and not panel.observed:
        return None
    d = trajectory_records(panel)
    both = pd.concat([d["curve"], d["obs"]], ignore_index=True)
    keys = list(dict.fromkeys(both["key"]))
    colour = alt.Color("key:N", scale=alt.Scale(domain=keys, range=[colours[k] for k in keys]), legend=None)
    first, last = float(both["x"].min()), float(both["x"].max())
    time_pad = max(0.2, (last - first) * 0.04)
    domain = [first - time_pad, last + time_pad]
    lo = min(0.0, float(both[["value", "lo"]].min().min()))
    hi = 100.0 if panel.unit == "%" else float(both[["value", "hi"]].max().max())
    pad = (hi - lo) * 0.05
    years = list(range(math.ceil(domain[0]), math.floor(domain[1]) + 1))
    xscale = alt.Scale(domain=domain, nice=False, zero=False)
    yscale = alt.Scale(domain=[lo - pad if lo < 0 else 0.0, hi + pad], nice=False, zero=False)
    xaxis = alt.Axis(format="d", values=years[::max(1, math.ceil(len(years) / 6))], labelFontSize=12, titleFontSize=12, labelOverlap=True)
    x = alt.X("x:Q", scale=xscale, title="Year", axis=xaxis)
    ytitle = f"{panel.title} ({panel.unit})"
    y = alt.Y("value:Q", scale=yscale, title=ytitle, axis=alt.Axis(labelFontSize=12, titleFontSize=12, titleLimit=420))
    ylo = alt.Y("lo:Q", scale=yscale, title=ytitle)
    layers = []
    if not d["curve"].empty:
        c = alt.Chart(d["curve"])
        tip = [alt.Tooltip("series:N", title="Curve"), alt.Tooltip("role:N", title="Role"), alt.Tooltip("x:Q", title="Year", format=".2f"),
               alt.Tooltip("estimate:N", title=f"Value ({panel.unit}; 90% band)"), alt.Tooltip("equation:N", title="Equation"),
               alt.Tooltip("interval:N", title="Band")]
        dash = alt.StrokeDash("role:N", scale=alt.Scale(domain=list(TRAJECTORY_DASH), range=list(TRAJECTORY_DASH.values())), legend=None)
        layers += [c.mark_area(opacity=0.16).encode(x=x, y=ylo, y2="hi:Q", color=colour, detail="series:N", tooltip=tip),
                   c.mark_line(strokeWidth=2.6).encode(x=x, y=y, color=colour, strokeDash=dash, detail="series:N", order="x:Q", tooltip=tip)]
    if not d["obs"].empty:
        o = alt.Chart(d["obs"])
        tip = [alt.Tooltip("series:N", title="Observed"), alt.Tooltip("x:Q", title="Survey (year)", format=".2f"),
               alt.Tooltip("estimate:N", title=f"Group mean ({panel.unit}; 90% t interval)"), alt.Tooltip("n:Q", title="Plots"),
               alt.Tooltip("time:N", title="Survey dates"), alt.Tooltip("source:N", title="Source")]
        layers.append(o.mark_rule(strokeWidth=1.6, opacity=0.8).encode(x=x, y=ylo, y2="hi:Q", color=colour, tooltip=tip))
        layers.append(o.mark_point(filled=True, size=70, opacity=1, stroke=text_colour, strokeWidth=0.8).encode(
            x=x, y=y, color=colour, shape=alt.value("circle"), tooltip=tip))
    return alt.layer(*layers).properties(height=height, autosize=alt.AutoSizeParams(type="fit", contains="padding"))
