"""Standalone figures for projection runs (matplotlib, Agg backend; no dashboard dependency).

A figure read on its own names the site, plot group, unit, observation span, extrapolation start, each curve's assumed rate(s)
and the conditional status. Several runs drawn together are a sensitivity comparison of separate assumptions; no band is drawn
between them because two chosen rates carry no probability.

Colours: reference categorical slots 1 and 2 (dataviz skill palette, light surface #fcfcfb), with line style as a second
encoding. Observations use neutral ink.
"""
from __future__ import annotations

import datetime as dt
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.shoreline_remediation.projections import catalogue as C  # noqa: E402

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1e", "#5f5e5a", "#e4e3df"
SERIES = ("#2a78d6", "#eb6834")
STYLES = ("-", (0, (6, 3)))
matplotlib.rcParams["svg.hashsalt"] = "shoreline-projection"     # deterministic SVG ids
matplotlib.rcParams["svg.fonttype"] = "none"                     # keep SVG text as text (searchable, screen-reader friendly)


def _d(s) -> dt.date:
    return dt.date.fromisoformat(str(s))


def _fmt(d: dt.date) -> str:
    return f"{d.day} {d:%b %Y}"


def draw(observed: pd.DataFrame, curves: list, spec, out_stem: Path, *, footer: str, comparison: bool = False) -> list:
    """Write <out_stem>.png and .svg. curves: [{'table': projection table, 'label': str}, ...]. Returns the written paths."""
    site = C.SITES[spec.site_id]
    group = site.plot_groups[spec.plot_group_id]
    allobs = observed.assign(d=pd.to_datetime(observed.date))
    avail = allobs.available_at_as_of.astype(str).str.lower() == "true"
    obs, later = allobs[avail], allobs[~avail]          # later surveys are never shown as available observations
    anchor = _d(curves[0]["table"].date.iloc[0])
    n = int(obs.n_plots.max())

    fig, ax = plt.subplots(figsize=(11, 6.6), dpi=110)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axvspan(obs.d.min(), pd.Timestamp(anchor), color=GRID, alpha=0.45, lw=0, zorder=0)
    ax.axvline(pd.Timestamp(anchor), color=INK, lw=1.2, zorder=2)
    ax.text(pd.Timestamp(anchor) + pd.Timedelta(days=60), 0.97,
            f"{_fmt(anchor)}: last survey on or before as_of;\nextrapolation starts",
            transform=ax.get_xaxis_transform(), va="top", color=INK, fontsize=9)

    has_iv = obs.interval_lo.notna()
    ax.errorbar(obs.d[has_iv], obs.value[has_iv], yerr=[obs.value[has_iv] - obs.interval_lo[has_iv], obs.interval_hi[has_iv] - obs.value[has_iv]],
                fmt="none", ecolor=INK, elinewidth=1.2, capsize=3, zorder=4)
    ax.plot(obs.d, obs.value, "o", ms=7, color=INK, mec=SURFACE, mew=1.5, zorder=5,
            label=f"Observed group mean, {len(obs)} survey dates available at as_of "
                  f"(n = {n} plots; whiskers 90% t interval of the mean)")
    if len(later):
        ax.plot(later.d, later.value, "o", ms=7, mfc=SURFACE, mec=MUTED, mew=1.5, zorder=5,
                label=f"Retrospective observations after as_of, {len(later)} survey dates (not available at as_of; "
                      "not used by the projection)")

    y_end = []
    for i, c in enumerate(curves):
        t = c["table"]
        x = pd.to_datetime(t.date)
        y = t.cumulative_retreat_since_origin_m
        ax.plot(x, y, color=SERIES[i % 2], ls=STYLES[i % 2], lw=2, zorder=3, label=f"{c['label']} (conditional)")
        for d in t.date[t["sample"] == "rate_change"]:
            ax.axvline(pd.Timestamp(d), color=SERIES[i % 2], lw=1, ls=":", zorder=1)
            ax.text(pd.Timestamp(d) + pd.Timedelta(days=50), 0.03, f"rate changes\n{_fmt(_d(d))}",
                    transform=ax.get_xaxis_transform(), color=MUTED, fontsize=8.5, va="bottom", ha="left")
        y_end.append((x.iloc[-1], y.iloc[-1], t.additional_retreat_since_anchor_m.iloc[-1], SERIES[i % 2]))
    for x, y, add, _col in y_end:
        ax.plot([x], [y], "o", ms=6, color=_col, mec=SURFACE, mew=1.5, zorder=6)
        ax.annotate(f"{y:.2f} m on {_fmt(x.date())}\n(+{add:.2f} m after the last survey)", (x, y), xytext=(-8, 8),
                    textcoords="offset points", ha="right", va="bottom", fontsize=9, color=INK)

    ax.set_ylabel("Cumulative marsh-edge retreat since 4 Dec 2010 (m)\npositive = land lost", color=INK)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=5 if (max(x for x, *_ in y_end).year - 2010) > 25 else 2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", color=GRID, lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.set_ylim(bottom=0, top=max([y for _, y, *_ in y_end] + [float(allobs.value.max())]) * 1.12)
    ax.set_xlim(right=max(x for x, *_ in y_end) + pd.Timedelta(days=365))
    lo, hi = ax.get_xlim()
    span = (mdates.date2num(pd.Timestamp(anchor)) - mdates.date2num(obs.d.min())) / (hi - lo)
    if span > 0.18:      # label the shaded span only when it is wide enough not to collide with the anchor label
        ax.text(obs.d.min() + pd.Timedelta(days=60), 0.97, "Observed surveys", transform=ax.get_xaxis_transform(), va="top",
                color=MUTED, fontsize=9)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.09), frameon=False, fontsize=9, ncol=1)

    title = (f"{site.label.split(' (')[0]}, northern Barataria Bay, Louisiana (Deepwater Horizon)\n"
             f"{spec.endpoint.replace('_', ' ').capitalize()} (m): {group.label}, n = {n}")
    sub = f"Observed to {_fmt(anchor)} (as_of {_fmt(spec.as_of_date)}). {C.CONDITIONAL_LABEL}"
    if comparison:
        sub += "\nCurves are separate assumptions (sensitivity), not a probability band."
    fig.suptitle(title, x=0.06, ha="left", y=0.99, fontsize=12, fontweight="bold", color=INK)
    fig.text(0.06, 0.885, sub, ha="left", va="top", fontsize=9.5, color=INK)
    fig.text(0.06, 0.012, textwrap.fill(footer, 190), ha="left", va="bottom", fontsize=7.5, color=MUTED)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.82 if comparison else 0.845, bottom=0.27)

    paths = [out_stem.with_suffix(".png"), out_stem.with_suffix(".svg")]
    fig.savefig(paths[0], facecolor=SURFACE, metadata={"Software": None})
    fig.savefig(paths[1], facecolor=SURFACE, metadata={"Date": None, "Creator": None})
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------------------------------------------
# User-defined what-if figures (retreat, cover, tPAH), drawn from the CSV text the dashboard downloads

WHATIF_OUTCOMES = {
    "retreat": {"x": "date", "value": "cumulative_retreat_m", "diff": "difference_from_natural_m", "unit": "m",
                "axis": "Cumulative retreat since 4 Dec 2010 (m)", "diff_axis": "Treatment minus natural (m)",
                "sign": "Below zero: less cumulative retreat than natural recovery (land kept). Above zero: more retreat."},
    "cover": {"x": "plot_date", "value": "total_cover", "diff": "difference_from_natural", "unit": "percentage points",
              "axis": "Total vegetation cover (%)", "diff_axis": "Treatment minus natural (percentage points)",
              "sign": "Above zero: more vegetation cover than natural recovery. Below zero: less cover (damage)."},
    "tpah": {"x": "plot_date", "value": "soil_tpah", "diff": "difference_from_natural", "unit": "mg/kg",
             "axis": "Soil tPAH, 0-10 cm (mg/kg)", "diff_axis": "Treatment minus natural (mg/kg)",
             "sign": "Below zero: lower soil tPAH than natural recovery. Above zero: higher soil tPAH."},
}


def _rows_from_csv(csv_text: str) -> pd.DataFrame:
    import io
    return pd.read_csv(io.StringIO(csv_text), dtype={"date": str, "plot_date": str})


def difference_rows(csv_text: str, outcome: str) -> pd.DataFrame:
    """Treatment-minus-natural rows exactly as the CSV holds them, in file order (both tPAH rows on the intervention date stay,
    so the drop is a vertical step). Empty when no treatment arm was exported (a blank assumption)."""
    m = WHATIF_OUTCOMES[outcome]
    rows = _rows_from_csv(csv_text)
    d = rows[(rows.arm == "treatment_what_if") & rows[m["diff"]].notna()]
    return pd.DataFrame({"x": d[m["x"]].astype(str), "difference": d[m["diff"]].astype(float), "sample": d.get("sample")})


def whatif_labels(outcome, computed, technique):
    """Describe the recomputed anchor and baseline identically in dashboard and offline exports."""
    from . import cover, pah, projection
    if outcome == "retreat":
        anchor = computed.anchor
        baseline = f"natural recovery at the stated rate schedule ({projection.describe_rates(computed.what.segments)})"
        last = f"{dt.date.fromisoformat(anchor.date):%d %b %Y} (n = {int(anchor.n_plots)} plots)"
    elif outcome == "cover":
        anchor = computed.what.anchor
        baseline = cover.BASELINE_LABEL.split(": ", 1)[1]
        last = f"{anchor.survey} survey (month precision; n = {anchor.n_plots} plots)"
    elif outcome == "tpah":
        anchor = computed.what.anchor
        baseline = pah.baseline_label(computed.what.half_life).split(": ", 1)[1]
        last = f"{anchor.survey_period} (month precision; n = {anchor.n_plots} plots; {anchor.depth})"
    else:
        raise ValueError(f"Unknown what-if figure outcome: {outcome}")
    return {"technique": technique or "natural recovery only", "baseline": baseline, "last_observation": last}


def whatif_figure(csv_text: str, outcome: str, *, technique: str, baseline: str, last_observation: str) -> dict:
    """PNG and SVG bytes of one what-if figure drawn from the downloaded CSV text. The figure names Bay Jimmy, the technique,
    the natural-recovery baseline, the units, the last observation date and the User-defined what-if label."""
    import io
    m = WHATIF_OUTCOMES[outcome]
    rows = _rows_from_csv(csv_text)
    obs = rows[rows.arm == "observed"]
    nat = rows[rows.arm == "natural_recovery"]
    trt = rows[rows.arm == "treatment_what_if"]
    diff = difference_rows(csv_text, outcome)
    x = lambda s: pd.to_datetime(s.str.slice(0, 10).where(s.str.len() >= 10, s + "-28"))     # month-precision dates
    two = not diff.empty
    fig, axes = plt.subplots(2 if two else 1, 1, figsize=(10, 7.6 if two else 5.6), dpi=110, sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.3]} if two else None, squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    ax = axes[0][0]
    for a in axes[:, 0]:
        a.set_facecolor(SURFACE)
        a.grid(color=GRID, lw=0.6)
        a.spines[["top", "right"]].set_visible(False)
    ox = x(obs[m["x"]].astype(str))
    ax.scatter(ox, obs[m["value"]], color=INK, s=22, zorder=4, label="Observed group mean (untreated plots)")
    if "interval_lo" in obs and obs.interval_lo.notna().any():
        ok = obs.interval_lo.notna()
        ax.vlines(ox[ok], obs.interval_lo[ok], obs.interval_hi[ok], color=INK, lw=1, zorder=3)
    ax.plot(x(nat[m["x"]].astype(str)), nat[m["value"]], color=SERIES[0], ls=STYLES[1], lw=2, label=baseline)
    if not trt.empty:
        ax.plot(x(trt[m["x"]].astype(str)), trt[m["value"]], color=SERIES[1], ls=":", lw=2.4,
                label=f"User-defined what-if: {technique}")
    ax.set_ylabel(m["axis"], color=INK)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    title = f"Bay Jimmy (northern Barataria Bay, Louisiana): User-defined what-if, {technique}"
    sub = f"Natural-recovery baseline: {baseline}. Last observation: {last_observation}."
    if two:
        sub += f" Lower panel: treatment minus natural recovery. {m['sign']}"
    fig.suptitle("\n".join(textwrap.wrap(title, 95)), x=0.06, ha="left", fontsize=12, color=INK)
    fig.text(0.06, 0.905 if two else 0.875, "\n".join(textwrap.wrap(sub, 120)), fontsize=8.5, color=MUTED, va="top")
    if two:
        b = axes[1][0]
        b.axhline(0, color=INK, lw=1)
        b.plot(x(diff.x), diff.difference, color=SERIES[1], lw=2)
        b.set_ylabel(m["diff_axis"], color=INK, fontsize=8.5)
    axes[-1][0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.06, 0.012, "Conditional scenarios, not forecasts. The what-if is a user assumption, not a measured treatment "
             "effect, and changes no recommendation. Drawn from the downloaded CSV rows.", fontsize=7.5, color=MUTED)
    fig.subplots_adjust(top=0.84 if two else 0.8, bottom=0.08, left=0.09, right=0.98, hspace=0.12)
    out = {}
    for fmt in ("png", "svg"):
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, facecolor=SURFACE, metadata={"Date": None} if fmt == "svg" else None)
        out[fmt] = buf.getvalue()
    plt.close(fig)
    return out

