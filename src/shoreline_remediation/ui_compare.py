"""Detailed option-comparison tables for a marsh edge cell (the earlier "Compare options" section, kept; decision D40).

What changed: AI-proposed ranges (data/knowledge/elicited_priors.csv) are shown in their own hatched block labelled "AI-proposed
range, not evidence" and never get a "distinguished" or "supported" flag. Rows with field evidence keep their 90% ranges and a
plain "range excludes zero" column. Internal plan and decision ids moved out of the text.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from . import ui_components as C
from .site_evidence import FEATURES

_KNOWLEDGE = Path(__file__).resolve().parents[2] / "data" / "knowledge"
COMPARE_DRAWS = 2000
MEASURED_OPTIONS = ["natural_attenuation", "manual_removal", "mechanical_removal", "planting (after mechanical cleanup)"]
YEARS = (2, 5, 8)

NOTE = ("How to read the field-evidence rows: each option is compared with natural recovery draw by draw (the same simulated "
        "baseline in each draw), so the site's own shared uncertainty cancels. 'Range excludes zero' means the 90% range of the "
        "difference does not include zero. The difference does not depend on this site: it reflects one site's field plots "
        "(Zengel et al. 2015, 2022, Bay Jimmy) and is the same at every heavily oiled site, not a measurement here. "
        "Negative edge-loss differences mean less land lost than natural recovery.")


def _label(x: str) -> str:
    return x.replace("_", " ")


def is_ai_row(evidence_label: str) -> bool:
    return str(evidence_label).startswith(("ELICITED", "AI-proposed"))


@st.cache_data
def _elicited() -> dict:
    d = pd.read_csv(_KNOWLEDGE / "elicited_priors.csv")
    return {r.option: (float(r.tau_multiplier_lo), float(r.tau_multiplier_hi)) for r in d.itertuples()}


@st.cache_data
def _conditions() -> pd.DataFrame:
    return pd.read_csv(_KNOWLEDGE / "treatment_conditions.csv")


@st.cache_data(show_spinner="Composing option outcomes (cell)...")
def _compare_cell(inputs: tuple) -> pd.DataFrame:
    from src.shoreline_remediation import scenario_composer as sc
    site = dict(inputs)
    el = _elicited()
    _, summ = sc.compose(site, MEASURED_OPTIONS + list(el), n_draws=COMPARE_DRAWS, elicited=el)
    return summ


@st.cache_data(show_spinner="Composing option outcomes (2 km block)...")
def _compare_block(block: str, _sites: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    from src.shoreline_remediation import scenario_composer as sc
    cells = _sites[(_sites.cell_2km == block) & (_sites.status == "in_scope")]
    if cells.empty:
        return pd.DataFrame(), 0
    el = _elicited()
    _, summ = sc.compose_block(cells, MEASURED_OPTIONS + list(el), n_draws=COMPARE_DRAWS, elicited=el)
    return summ, len(cells)


def _rng_text(r, prefix: str, y: int, unit_fmt: str = "{:+.2f}") -> str:
    med, lo, hi = (r.get(f"{prefix}_y{y}_{k}") for k in ("median", "lo90", "hi90"))
    if med is None or pd.isna(med):
        return "-"
    f = unit_fmt.format
    return f"{f(med)} ({f(lo)} to {f(hi)})"


def _excludes_zero(r, col: str) -> str:
    out = []
    for y in YEARS:
        v = r.get(f"{col}_y{y}")
        out.append("-" if v is None or pd.isna(v) else ("yes" if bool(v) else "no"))
    return " / ".join(out)


def measured_table(summ: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Rows with field evidence (and the natural-recovery baseline). AI-proposed rows are excluded."""
    rows = []
    for _, r in summ.iterrows():
        if is_ai_row(r.evidence):
            continue
        base = r.option == "natural_attenuation"
        row = {"Option": _label(r.option), "Evidence": "Comparison group" if base else "Field plots (experimental composer)"}
        if kind == "cell":
            for y in YEARS:
                row[f"Edge loss vs natural recovery, year {y} (m)"] = "baseline" if base else _rng_text(r, "paired_diff_cum_edge_loss", y)
            row["Range excludes zero, edge loss (yr 2 / 5 / 8)"] = _excludes_zero(r, "edge_distinguished")
            for y in YEARS:
                row[f"Vegetation vs natural recovery, year {y} (fraction of reference cover)"] = "baseline" if base else _rng_text(r, "paired_diff_veg_ratio", y)
            row["Range excludes zero, vegetation (yr 2 / 5 / 8)"] = _excludes_zero(r, "veg_distinguished")
        else:
            for y in YEARS:
                row[f"Marsh area lost vs natural recovery, year {y} (ha)"] = "baseline" if base else _rng_text(r, "paired_diff_area_ha", y, "{:+.2f}")
            row["Range excludes zero (yr 2 / 5 / 8)"] = _excludes_zero(r, "area_distinguished")
        rows.append(row)
    return pd.DataFrame(rows)


def ai_rows(summ: pd.DataFrame, kind: str) -> list[dict]:
    """AI-proposed ranges only: no flags, no 'distinguished' wording."""
    el = _elicited()
    out = []
    for _, r in summ.iterrows():
        if not is_ai_row(r.evidence):
            continue
        lo, hi = el.get(r.option, (None, None))
        row = {"Option": _label(r.option)}
        if lo is not None:
            row["AI-proposed recovery-time multiplier"] = f"{lo:.1f} to {hi:.1f}"
        if kind == "cell":
            for y in YEARS:
                row[f"Vegetation vs natural recovery, year {y}"] = _rng_text(r, "paired_diff_veg_ratio", y)
        out.append(row)
    return out


def conditions_table(options: list[str]) -> pd.DataFrame:
    c = _conditions()
    rows = []
    for opt in options:
        d = c[c.treatment == _label(opt)]
        for r in d.itertuples():
            askable = str(r.site_data_can_check).lower().startswith("no")
            text = (f"Is this true: {r.condition.rstrip('.')}? If so, the literature reports it {r.effect_when_met}." if askable
                    else f"{r.condition} ({r.effect_when_met}; the site data can only partly check this: {r.site_data_can_check})")
            rows.append({"Option": _label(opt), "Condition to check": text, "Evidence class": r.evidence_class, "Source": r.source})
    return pd.DataFrame(rows)


def render_detailed_comparison(site: dict, flags, sites: pd.DataFrame) -> None:
    """All the tables behind the option cards (inside one expander, so the landing page stays short)."""
    if not flags.in_scope:
        st.info("No prediction for this site: the option comparison needs the edge-loss model, and this site is outside what it was "
                "fitted and tested on (see the reason above). No numbers are shown rather than a guess.", icon=":material/block:")
        return
    from src.shoreline_remediation import scenario_composer as sc
    nrs = sc.natural_recovery_summary(site)
    mr = nrs["mean_rate_y1_5"]
    st.caption(f"Natural recovery as the option comparison uses it (includes the field-measured oil excess for heavy sites): {mr['median']:.2f} m/yr mean marsh-edge loss over years 1 to 5 "
               f"(90% range {mr['lo90']:.2f} to {mr['hi90']:.2f}). Every option below is compared with this.")
    inputs = tuple((k, site.get(k)) for k in (*FEATURES, "max_oiling"))
    summ = _compare_cell(inputs)
    st.markdown("**This cell: options with field evidence**")
    st.dataframe(measured_table(summ, "cell"), hide_index=True, width="stretch")
    verdict = str(summ.veg_curve_verdict.iloc[0])
    veg_scope = summ.veg_curve_scope.iloc[0] if "veg_curve_scope" in summ.columns and pd.notna(summ.veg_curve_scope.iloc[0]) else None
    st.caption(f"Vegetation recovery curve status: {verdict.split(' (')[0].upper()} ('suggestive' means it did not pass its held-out test). "
               "Vegetation differences exist only where a field shift or an AI-proposed range exists."
               + (f" For this heavily oiled site: the vegetation curve is {veg_scope}." if veg_scope else ""))
    ai = ai_rows(summ, "cell")
    if ai:
        st.markdown("**Other options: AI-proposed ranges only (no field evidence)**")
        C.render_ai_ranges(ai)
    block = site.get("cell_2km")
    if site.get("source") == "edge cell" and block is not None and not pd.isna(block):
        bsumm, n = _compare_block(str(block), sites)
        if n:
            st.markdown(f"**Its 2 km block ({block}, {n} in-scope cells; one cell ASSUMED to hold 100 m of edge, a known underestimate)**")
            st.dataframe(measured_table(bsumm, "block"), hide_index=True, width="stretch")
            ai_b = ai_rows(bsumm, "block")
            if ai_b:
                C.render_ai_ranges(ai_b)
            st.caption("Block totals add up the retreat of every in-scope cell, with one block-level error shared by all cells plus "
                       "independent within-block errors. Block ranges are only modestly narrower than single-cell ranges, because "
                       "the shared error and the oil excess do not average out.")
    else:
        st.caption("No 2 km block for a typed-in site: only the single-cell comparison is shown.")
    cond = conditions_table(list(summ.option))
    st.markdown("**Conditions to check**")
    if cond.empty:
        st.caption("No conditions listed.")
    else:
        st.dataframe(C.ai_style_dataframe(cond), hide_index=True, width="stretch")
        st.caption("AI-proposed conditions under which the literature reports benefit or harm, shown as questions because the site "
                   "data cannot check them (season, water over the soil, days since oiling). They are not reviewed by a person.")
    st.caption(NOTE)
