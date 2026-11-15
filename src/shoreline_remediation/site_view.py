"""Site evidence view (real data) with a habitat switcher (decision D40).

Layout: answer first (site, headline recommendation, key number with its 90% range, evidence chips), then the option
comparison, the forecast, the map and the detailed tables. Logic lives in site_evidence.py, scenario_composer.py and
decision_pipeline.py; this module lays it out. Reads committed files only and needs no network except for the map's tiles.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.shoreline_remediation import ui_components as C
from src.shoreline_remediation import ui_compare, ui_evidence as E, ui_pipeline as P, ui_report, ui_theme as T
from src.shoreline_remediation.site_evidence import (FEATURE_LABELS, FEATURES, STATUS_TEXT, load_model, load_sites,
                                                     site_flags, site_scenario, site_scenario_inputs, treatment_evidence)

CLASSES = ["Heavy", "Moderate", "Light", "Very_Light", "NOO"]
BASINS = ["barataria", "breton", "terrebonne", "birdfoot"]
EXAMPLE_CELL = "8018_32612"  # docs/P5_WORKED_EXAMPLE.md
_KNOWLEDGE = Path(__file__).resolve().parents[2] / "data" / "knowledge"
SITE_MODE_WORKED = "Worked example (Bay Jimmy, Barataria Bay)"


@st.cache_data
def _sites() -> pd.DataFrame:
    return load_sites()


def _label(x: str) -> str:
    return x.replace("_", " ")


# ---------------------------------------------------------------------------------------------------------------
# Site choice

def _pick_site(sites: pd.DataFrame) -> dict | None:
    mode = st.radio("Site", [SITE_MODE_WORKED, "Pick a Louisiana edge cell", "New site (enter values)"],
                    horizontal=True, key="site_mode")
    if mode.startswith("Worked"):
        row = sites[sites.cell == EXAMPLE_CELL]
        if row.empty:
            st.error("Worked-example cell not found; rebuild with scripts/build_p5_demo.py.")
            return None
        st.caption("Chosen by a fixed rule: the heavily oiled Barataria cell nearest the Zengel et al. (2022) field plots, so site "
                   "and treatment evidence come from the same marsh.")
        return {**row.iloc[0].to_dict(), "source": "edge cell"}
    if mode.startswith("Pick"):
        c1, c2, c3 = st.columns(3)
        basin = c1.selectbox("Basin", BASINS, format_func=str.title, key="pick_basin")
        oiling = c2.selectbox("SCAT maximum oiling", ["any"] + CLASSES, format_func=lambda x: T.OILING_LABELS.get(x, x), key="pick_oil")
        in_scope_only = c3.checkbox("In-scope cells only", value=True, key="pick_scope")
        d = sites[(sites.basin == basin) & (sites.esi_main == "10A")]
        if oiling != "any":
            d = d[d.max_oiling == oiling]
        if in_scope_only:
            d = d[d.status == "in_scope"]
        if d.empty:
            st.warning("No cells match. Untick 'In-scope cells only' to see out-of-scope cells and why they are excluded.")
            return None
        segs = sorted(d.segment.dropna().unique())
        c4, c5 = st.columns(2)
        seg = c4.selectbox(f"SCAT segment ({len(segs)})", segs, key="pick_seg")
        cells = d[d.segment == seg]
        cell = c5.selectbox(f"Cell ({len(cells)})", cells.cell.tolist(), key="pick_cell")
        return {**cells[cells.cell == cell].iloc[0].to_dict(), "source": "edge cell"}
    st.caption("Type values measured the same way as the training data (2010 aerial land/water map; Landsat pre-spill trend). "
               "Values outside the training range are flagged as extrapolation.")
    r = load_model()["training_range"]
    c1, c2, c3, c4 = st.columns(4)
    v = {
        "water_1km_2010": c1.number_input(FEATURE_LABELS["water_1km_2010"], 0.0, 1.0, round((r["water_1km_2010"]["p01"] + r["water_1km_2010"]["p99"]) / 2, 2), 0.01, key="new_w1"),
        "water_250m_2010": c2.number_input(FEATURE_LABELS["water_250m_2010"], 0.0, 1.0, round((r["water_250m_2010"]["p01"] + r["water_250m_2010"]["p99"]) / 2, 2), 0.01, key="new_w2"),
        "fetch_mean_m": c3.number_input(FEATURE_LABELS["fetch_mean_m"], 0.0, 10000.0, 1500.0, 50.0, key="new_fetch"),
        "pre_rate": c4.number_input(FEATURE_LABELS["pre_rate"], -10.0, 10.0, 0.3, 0.1, key="new_pre"),
    }
    c5, c6, c7, c8 = st.columns(4)
    lat = c5.number_input("Latitude", -90.0, 90.0, 29.40, 0.01, key="new_lat")
    lon = c6.number_input("Longitude", -180.0, 180.0, -89.90, 0.01, key="new_lon")
    habitat = c7.selectbox("Shoreline (ESI)", ["10A", "other"], format_func=lambda x: "10A salt marsh" if x == "10A" else "other", key="new_esi")
    oiling = c8.selectbox("Oiling class", CLASSES, format_func=lambda x: T.OILING_LABELS.get(x, x), key="new_oil")
    return {**v, "lat": lat, "lon": lon, "esi_main": habitat, "max_oiling": oiling, "status": "in_scope",
            "basin": "new site", "cell": "new site", "segment": "-", "source": "new site"}


def _assumptions() -> tuple[str, str | None]:
    st.markdown("**Assumptions for the rule screening**")
    c1, c2 = st.columns(2)
    oil = c1.selectbox("Oil category", ["light", "medium", "heavy", "solid"], key="site_oil",
                       help="Deepwater Horizon oil was a light crude that arrived weathered and emulsified.")
    season = c2.selectbox("Season of cleanup", ["site default (summer)", "spring", "summer", "autumn", "winter"], key="site_season",
                          help="Used to check season-dependent conditions in the literature.")
    return oil, (None if season.startswith("site") else season)


# ---------------------------------------------------------------------------------------------------------------
# Map and forecast chart

def _map(sites: pd.DataFrame, site: dict) -> None:
    dark = C.is_dark()
    sel = T.SELECTED_SITE_COLOUR["dark" if dark else "light"]
    if site["source"] == "new site":
        pts = pd.DataFrame([{"lat": site["lat"], "lon": site["lon"], "color": sel, "size": 120.0}])
    else:
        d = sites[(sites.basin == site["basin"]) & (sites.esi_main == "10A")][["lat", "lon", "max_oiling"]]
        pts = d.assign(color=d.max_oiling.map(lambda o: T.oiling_colour(o, dark)), size=40.0)[["lat", "lon", "color", "size"]]
        pts = pd.concat([pts, pd.DataFrame([{"lat": site["lat"], "lon": site["lon"], "color": sel, "size": 160.0}])])
    st.map(pts, latitude="lat", longitude="lon", color="color", size="size", zoom=9 if site["source"] != "new site" else 7, width="stretch")
    st.caption("Salt-marsh edge cells in this basin, shaded by SCAT maximum oiling: darkest orange-brown Heavy, then Moderate, Light, "
               "pale Very light; blue is no oil observed. A black dot (white in dark mode) is the selected site.")


def _edge_chart(pred: dict, observed, sites: pd.DataFrame) -> alt.Chart:
    train = sites.loc[sites.status == "in_scope", "observed_rate"].dropna().clip(-8, 10)
    counts, edges = np.histogram(train, bins=60)
    hist = pd.DataFrame({"x0": edges[:-1], "x1": edges[1:], "n": counts})
    bars = alt.Chart(hist).mark_bar(opacity=0.35, color=T.NEUTRAL).encode(
        x=alt.X("x0:Q", title="Marsh-edge loss, metres per year (positive = land lost)"), x2="x1:Q", y=alt.Y("n:Q", axis=None))
    band = alt.Chart(pd.DataFrame({"lo": [pred["lo"]], "hi": [pred["hi"]]})).mark_rect(opacity=0.2, color=T.OKABE_ITO["blue"]).encode(
        x="lo:Q", x2="hi:Q")
    marks = [("Expected at this site", pred["rate"]), ("Zero (no net loss)", 0.0)]
    if observed is not None and not math.isnan(observed):
        marks.append(("Observed at this cell", float(observed)))
    domain = ["Expected at this site", "Observed at this cell", "Zero (no net loss)"]
    rng = [T.OKABE_ITO["blue"], T.OKABE_ITO["vermillion"], T.NEUTRAL]
    dash = [[1, 0], [6, 4], [2, 3]]
    rules = alt.Chart(pd.DataFrame(marks, columns=["mark", "x"])).mark_rule(size=2.5).encode(
        x="x:Q", color=alt.Color("mark:N", scale=alt.Scale(domain=domain, range=rng), legend=alt.Legend(title=None, orient="bottom")),
        strokeDash=alt.StrokeDash("mark:N", scale=alt.Scale(domain=domain, range=dash), legend=None))
    return (bars + band + rules).properties(height=200, title="All training cells (grey), with this site's 90% range shaded")


# ---------------------------------------------------------------------------------------------------------------
# Marsh

@st.cache_data
def _oil_excess_card() -> dict:
    import json
    path = Path(__file__).resolve().parents[2] / "models" / "oil_excess_oos_v1.json"
    return json.loads(path.read_text()) if path.exists() else {}


@st.cache_data
def _interval_coverage_range() -> tuple[float, float] | None:
    """Held-out coverage of the per-class 90% interval across basin x oiling-class groups with 100 or more cells."""
    path = Path(__file__).resolve().parents[2] / "results" / "v5_p0" / "interval_by_basin_class.csv"
    if not path.exists():
        return None
    d = pd.read_csv(path)
    d = d[d["n_cells"] >= 100]
    return (float(d["m1_class_oos_coverage"].min()), float(d["m1_class_oos_coverage"].max())) if len(d) else None


def _ref_grade(view, text: str, default: str = "experimental") -> str:
    if view is None:
        return default
    for r in view.reference:
        if text in str(E.field(r, "quantity", "")):
            return E.reference_grade(r)
    return default


def render_marsh() -> None:
    m = load_model()
    sites = _sites()
    C.scope_panel("marsh")
    answer = st.container()
    with st.expander("Site and assumptions: change the site, the oil type or the season"):
        site = _pick_site(sites)
        st.divider()
        oil, season = _assumptions()
    if site is None:
        return
    values = {f: site.get(f) for f in FEATURES}
    flags = site_flags(values, site["status"], site["esi_main"], site["max_oiling"], site.get("lat"), site.get("lon"), m)
    report, err = P.decision_for_site(P.site_items(site), oil, season)
    view = E.report_view(report) if report is not None else None
    nrs = None
    if flags.in_scope:
        from src.shoreline_remediation import scenario_composer as sc
        nrs = sc.natural_recovery_summary(site)
    obs = site.get("observed_rate")
    where = (f"{'Worked example: ' if site.get('cell') == EXAMPLE_CELL else ''}Cell {site['cell']} | {str(site['basin']).title()} | "
             f"Salt marsh | SCAT oiling: {T.OILING_LABELS.get(site['max_oiling'], site['max_oiling'])}")
    metrics = None
    if nrs is not None:
        bl = nrs["baseline"]
        up = _oil_excess_card().get("excess_by_class_deployable", {}).get(str(site["max_oiling"]))
        has_rng = bl["lo90"] is not None
        metrics = [
            {"label": T.LABELS["edge_loss"], "value": f"{bl['rate']:.2f} m/yr",
             "range": f"90% range: {bl['lo90']:.1f} to {bl['hi90']:.1f}" if has_rng else None, "grade": _ref_grade(view, "edge-loss rate", "validated"),
             "help": "Clean-edge prediction with no oiling term. The extra loss in oiled marsh is shown separately, as an average."},
            {"label": "Observed at this cell, 2010 to 2015 (aerial images)", "value": "not available" if obs is None or pd.isna(obs) else f"{obs:.2f} m/yr",
             "help": "Aerial-image measurements read about 1.2 m/yr lower than field erosion measurements, so compare sites rather than absolute values."},
            {"label": f"AVERAGE extra loss where oiling was {T.OILING_LABELS.get(site['max_oiling'], site['max_oiling']).lower()} (m/yr)",
             "value": f"+{up['excess_m_per_yr']:.2f}" if up else "not estimated",
             "range": f"90% range: {up['lo90']:.2f} to {up['hi90']:.2f}" if up else None, "grade": "experimental" if up else None,
             "grade_text": "Experimental: failed validation",
             "help": "An average over sites in other basins, NOT added to this site's number: adding it did not improve cell-level accuracy."},
            {"label": "Typical error, basin held out (m/yr)", "value": f"{m['lobo_mae']:.2f}",
             "range": f"predicting the average everywhere: {m['lobo_mae_no_predictor']:.2f}",
             "help": "Single 100 m cells are noisy, so the model beats the plain average only slightly."},
        ]
    with answer:
        for x in flags.out_of_scope:
            st.error(x, icon=":material/block:")
        if flags.extrapolation:
            st.warning("Extrapolation: " + " ".join(flags.extrapolation), icon=":material/warning:")
        if err:
            st.error(f"The decision pipeline could not run for this site ({err}).")
        C.answer_card(view, where, metrics)

    st.subheader("How each option compares with natural recovery")
    C.render_pipeline_section(view, "marsh")

    st.subheader("Expected marsh-edge loss at this site")
    if nrs is not None:
        bl = nrs["baseline"]
        if bl["lo90"] is not None:
            st.altair_chart(_edge_chart({"rate": bl["rate"], "lo": bl["lo90"], "hi": bl["hi90"]}, obs, sites), theme="streamlit", width="stretch")
        cov = _interval_coverage_range()
        if cov:
            st.caption(f"The 90% range is wide because single 100 m cells are noisy. Checked on basins held out, it covered the observed value "
                       f"between {cov[0]:.0%} and {cov[1]:.0%} of the time, depending on basin and oiling class (the target is 90%).")
        up = _oil_excess_card().get("excess_by_class_deployable", {}).get(str(site["max_oiling"]))
        if up:
            st.caption(f"Extra loss in {T.OILING_LABELS.get(site['max_oiling'], site['max_oiling']).lower()} oiling is an AVERAGE effect "
                       f"(+{up['excess_m_per_yr']:.2f} m/yr, 90% range {up['lo90']:.2f} to {up['hi90']:.2f}), not part of the site number above. "
                       "Adding it did not improve cell-level accuracy.")
        with st.expander("How this number was built"):
            bl = nrs["baseline"]
            text = (f"The site number is a baseline model that uses only open water nearby, wind exposure and the pre-spill trend, with no "
                    f"oiling term of its own: {bl['rate']:.2f} m/yr (90% range {bl['lo90']:.1f} to {bl['hi90']:.1f}). ")
            if nrs["heavy"]:
                text += "The option comparison below adds the field-measured extra loss for heavily oiled marsh. "
                oe = nrs["oil_excess"]
                text += (f"That extra loss, measured on untreated oiled plots (Zengel et al. 2022): "
                         f"+{oe['2010-2012']['effect']:.2f} m/yr in years 1 to 2 (90% range {oe['2010-2012']['lo90']:.2f} to {oe['2010-2012']['hi90']:.2f}) and "
                         f"+{oe['2012-2018']['effect']:.2f} m/yr in years 3 to 8 (90% range {oe['2012-2018']['lo90']:.2f} to {oe['2012-2018']['hi90']:.2f}). "
                         + nrs["bias_note"] + " ")
            else:
                text += "This site is not heavily oiled, so no oil excess is added (the field evidence covers heavy oiling only). "
            held = site.get("p2_heldout_M1")
            if held is not None and not pd.isna(held):
                text += f"With this basin left out entirely, the edge-loss model predicted {held:.2f} m/yr. "
            text += (f"The range is wide because single 100 m cells are noisy: the held-out error is {m['lobo_mae']:.2f} m/yr against "
                     f"{m['lobo_mae_no_predictor']:.2f} m/yr for predicting the average. " + m["measurement_note"])
            st.write(text)
    else:
        st.write("No prediction: the site is outside what the model was fitted and tested on (see the reason above).")

    st.subheader("Where the site is")
    left, right = st.columns([1.25, 1])
    with left:
        _map(sites, site)
    with right:
        info = [("Cell", site["cell"]), ("Basin", str(site["basin"]).title()), ("SCAT segment", site.get("segment", "-")),
                ("Shoreline (ESI)", site["esi_main"]), ("SCAT maximum oiling", T.OILING_LABELS.get(site["max_oiling"], site["max_oiling"]))]
        info += [(FEATURE_LABELS[f], "missing" if pd.isna(site.get(f)) else (f"{float(site[f]):,.0f}" if f == "fetch_mean_m" else f"{float(site[f]):.2f}"))
                 for f in FEATURES]
        st.dataframe(pd.DataFrame(info, columns=["Input", "Value"]), hide_index=True, width="stretch")

    with st.expander("Detailed tables: rule screening, field plots, AI-proposed ranges"):
        if site["esi_main"] == "10A":
            _rule_table(site, oil, report)
        ui_compare.render_detailed_comparison(site, flags, sites)
    C.render_sources_and_decisions(view, "Edge-loss model p5-edge-loss-v1, composer baseline p5-edge-loss-clean-v1.")
    _download(view, report, where, "marsh")


def _rule_table(site: dict, oil: str, report) -> None:
    """Rule screening beside the field plots. V5.1: the screening verdicts and the order come from the decision pipeline
    report (run_decision), not from a second call to the legacy rule-ranking model."""
    if report is None:
        st.info("Rule screening is unavailable because the decision pipeline did not return a report for this site.")
        return
    from src.shoreline_remediation.site_evidence import RESTORATION_ADDONS
    ranked = [o for o in report.options if o["option"] not in RESTORATION_ADDONS]   # add-ons are listed below
    ev = treatment_evidence([r["option"] for r in ranked], site["max_oiling"]).set_index("treatment")
    rows = []
    for i, r in enumerate(ranked, 1):
        e = ev.loc[r["option"]]
        rows.append({"Pipeline order (display)": i, "Option": _label(r["option"]),
                     "Pipeline category": r["recommendation_category_label"], "Rule screening": r["rule_verdict"],
                     T.LABELS["assumed_score"]: round(float(r["ecological_score_assumed"]), 2),
                     "Extra erosion vs natural recovery, years 0 to 2": e.erosion_0_2, "Same, years 2 to 8": e.erosion_2_8,
                     "Vegetation cover vs natural recovery, year 2": e.veg_cover_yr2})
    for name in ev.index[~ev.index.isin([r["option"] for r in ranked])]:
        e = ev.loc[name]
        rows.append({"Pipeline order (display)": None, "Option": name, "Pipeline category": None,
                     "Rule screening": "restoration add-on", T.LABELS["assumed_score"]: None,
                     "Extra erosion vs natural recovery, years 0 to 2": e.erosion_0_2, "Same, years 2 to 8": e.erosion_2_8,
                     "Vegetation cover vs natural recovery, year 2": e.veg_cover_yr2})
    st.markdown("**Rule screening and field plots (heavily oiled marsh at Bay Jimmy)**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Screening verdicts, categories and order are read from the decision pipeline report for this site. The order is "
               "the pipeline's display order (class, then benefit lower bound where one exists, then the ASSUMED ecological "
               "score); it is not an effectiveness ranking. Field columns are differences against untreated plots with 90% ranges: erosion in "
               "m/yr (positive = more edge lost), vegetation cover in percentage points. One site, 5 to 9 plots per group; "
               "observational except planting, which was randomised. Where rules and evidence disagree (for example mechanical "
               "removal) both are shown and neither overrides the other.")
    with st.expander("Rule-screening inputs implied by this site"):
        st.dataframe(pd.DataFrame(site_scenario_inputs(site, oil), columns=["Input", "Value", "Basis"]), hide_index=True, width="stretch")
    st.caption("Scope codes for every cell: " + "; ".join(f"`{k}` {v.split(':')[0].lower()}" for k, v in STATUS_TEXT.items()) + ".")


def _download(view, report, where: str, key: str) -> None:
    if view is None or report is None:
        return
    st.download_button("Download this report (HTML)", data=ui_report.build_html(view, title=where, habitat=key),
                       file_name=f"shoreline_report_{key}.html", mime="text/html", key=f"dl_{key}", icon=":material/download:")


# ---------------------------------------------------------------------------------------------------------------
# Mangrove

_MANGROVE_RESULTS = Path(__file__).resolve().parents[2] / "results" / "mangrove"
_OUTCOME_TITLES = {"root_documented_dead_share": "Share of prop roots recorded dead (primary)",
                   "leaves_per_shoot": "Leaves per shoot (primary)", "root_oil_cover": "Root oil cover, % (secondary)"}
_VERDICT_TEXT = {"validated": "oiling information predicts held-out sites better than ignoring it",
                 "suggestive": "better than ignoring oiling, but the range includes zero",
                 "not usable": "no better than ignoring oiling; show site-year means only"}
_VERDICT_GRADE = {"validated": "experimental", "suggestive": "experimental", "not usable": "illustrative"}


@st.cache_data
def _mangrove_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(_MANGROVE_RESULTS / "effect_by_year.csv"), pd.read_csv(_MANGROVE_RESULTS / "summary.csv")


@st.cache_data
def _mangrove_screening() -> pd.DataFrame:
    return pd.read_csv(_KNOWLEDGE / "mangrove_screening.csv")


def _effect_chart(e: pd.DataFrame, ytitle: str) -> alt.Chart:
    d = pd.DataFrame({"year": e.year_since_spill, "effect": e.effect, "lo": e.lo90, "hi": e.hi90})
    base = alt.Chart(d).encode(x=alt.X("year:O", title="Year since spill (1 = 1987)"))
    bars = base.mark_rule(size=3, color=T.OKABE_ITO["vermillion"]).encode(y=alt.Y("lo:Q", title=ytitle), y2="hi:Q")
    dots = base.mark_point(filled=True, size=90, color=T.OKABE_ITO["vermillion"]).encode(y="effect:Q")
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(strokeDash=[5, 4], strokeWidth=2, color=T.NEUTRAL).encode(y="y:Q")
    return (zero + bars + dots).properties(height=200)


def render_mangrove() -> None:
    eff, summ = _mangrove_results()
    C.scope_panel("mangrove")
    report, err = P.decision_for_scenario(P.scenario_items(_scenario("mangrove")), None, None, None, "mangrove")
    view = E.report_view(report) if report is not None else None
    st.markdown("Mangrove mode shows what one field study found: how much worse oiled red mangrove fringe sites were than unoiled "
                "sites in the first five years after a spill. It is not a cleanup recommendation and applies no marsh model.")
    metrics = []
    for outcome in ("root_documented_dead_share", "leaves_per_shoot"):
        e = eff[eff.outcome == outcome].sort_values("year_since_spill").iloc[-1]
        s = summ[summ.outcome == outcome].set_index("row")
        verdict = next(k[len("verdict_"):].replace("_", " ") for k in s.index if k.startswith("verdict_"))
        metrics.append({"label": _OUTCOME_TITLES[outcome] + f", year {int(e.year_since_spill)}: oiled minus unoiled", "value": f"{e.effect:+.2f}",
                        "range": f"90% range: {e.lo90:+.2f} to {e.hi90:+.2f}", "grade": _VERDICT_GRADE.get(verdict, "illustrative"),
                        "grade_text": f"Experimental (one spill); test: {verdict}"})
    C.answer_card(view, "Mangrove (Rhizophora fringe) | Bahia Las Minas, Panama, 1986", metrics)
    if err:
        st.error(f"The decision pipeline could not run ({err}).")
    st.subheader("Oiling effect by year since the spill")
    for outcome, title in _OUTCOME_TITLES.items():
        e = eff[eff.outcome == outcome]
        s = summ[summ.outcome == outcome].set_index("row")
        verdict = next(k[len("verdict_"):].replace("_", " ") for k in s.index if k.startswith("verdict_"))
        d = s.loc["MAE_M1_minus_M0"]
        st.markdown(f"**{title}**: {e.n_oiled_sites.iloc[0]} oiled and {e.n_unoiled_sites.iloc[0]} unoiled sites. Model test: **{verdict}** "
                    f"({_VERDICT_TEXT[verdict]}). Held-out error with the oiling effect minus without: {d.estimate:+.3f} "
                    f"(90% range {d.lo90:+.3f} to {d.hi90:+.3f}).")
        st.altair_chart(_effect_chart(e, "Oiled minus unoiled"), theme="streamlit", width="stretch")
        with st.expander("Numbers"):
            st.dataframe(pd.DataFrame({"Year since spill": e.year_since_spill, "Oiled minus unoiled": e.effect.round(3),
                                       "90% low": e.lo90.round(3), "90% high": e.hi90.round(3)}), hide_index=True, width="stretch")
    st.caption("Ranges are 90% intervals from a mixed model with a random intercept per site. Oiled and unoiled sites were chosen by the "
               "investigators, so differences are associations. A dashed line marks zero (no difference).")
    st.subheader("Cleanup options in mangroves")
    C.render_pipeline_section(view, "mangrove", show_chart=False)
    with st.expander("AI-proposed screening table (not human-reviewed)"):
        t = _mangrove_screening()
        st.dataframe(C.ai_style_dataframe(t.rename(columns={"treatment": "Treatment", "verdict": "Verdict", "reason": "Reason",
                                                            "conditions": "Conditions", "source": "Source", "evidence_class": "Evidence class",
                                                            "provenance": "Provenance"})
                                          [["Treatment", "Verdict", "Reason", "Conditions", "Source", "Evidence class", "Provenance"]]),
                     hide_index=True, width="stretch")
        st.caption("Verdicts are AI-proposed from the literature and were not tested with the Galeta data (no treatment variable).")
    C.render_sources_and_decisions(view)
    _download(view, report, "Mangrove (Rhizophora fringe)", "mangrove")


# ---------------------------------------------------------------------------------------------------------------
# Beaches (rules and literature only; the persistence model plugs in through render_beach_persistence)

def _scenario(shoreline_type: str, **kw):
    from src.shoreline_remediation.data_model import Scenario
    return Scenario(shoreline_type=shoreline_type, **kw)


def _beach_renderer(h: "HabitatView") -> Callable[[], None]:
    def render() -> None:
        C.scope_panel("beach")
        st.caption(h.note)
        c1, c2, c3 = st.columns(3)
        oiling = c1.selectbox("Oiling (SCAT maximum oiling)", CLASSES, index=1, format_func=lambda x: T.OILING_LABELS[x], key=f"beach_{h.key}_oiling")
        oil = c2.selectbox("Oil category", ["light", "medium", "heavy", "solid"], index=1, key=f"beach_{h.key}_oil")
        exposure = c3.selectbox("Wave exposure", ["low", "moderate", "high", "very_high"], index=1,
                                format_func=_label, key=f"beach_{h.key}_exposure")
        scen = _scenario(h.shoreline_type, wave_exposure=exposure, oil_category=oil)
        report, err = P.decision_for_scenario(P.scenario_items(scen), oiling, oil, None, h.esi)
        view = E.report_view(report) if report is not None else None
        C.answer_card(view, f"{h.label} | oiling: {T.OILING_LABELS[oiling]} | {oil} oil | {_label(exposure)} wave exposure")
        if err:
            st.error(f"The decision pipeline could not run ({err}).")
        ref = next((r for r in (view.reference if view else []) if E.field(r, "curves_by_group")), None)
        C.render_beach_persistence({"habitat": h.key, "esi": h.esi, "label": h.label, "oiling_class": oiling, "oil_category": oil,
                                    "exposure": exposure, "reference": ref, "literature_notes": view.literature_notes if view else []})
        if view is not None and view.advisories:
            with st.expander("Advisory notes (AI-proposed, not used to set the classes)"):
                for a in view.advisories:
                    st.markdown(f"- {a}")
        st.subheader("Options and what the evidence says")
        C.render_pipeline_section(view, f"beach_{h.key}")
        C.render_sources_and_decisions(view)
        _download(view, report, h.label, h.key)
    return render


@dataclass(frozen=True)
class HabitatView:
    key: str
    label: str
    render: Callable[[], None]
    shoreline_type: str = ""
    note: str = ""
    esi: str = ""


_BEACH_NOTE = ("The beach type you picked is passed to the decision pipeline by its shoreline class (ESI code). The generic rule "
               "screening has only a sand-beach and a mixed-sediment type: ")
HABITATS = [
    HabitatView("marsh", "Salt marsh", render_marsh),
    HabitatView("mangrove", "Mangrove", render_mangrove),
]
for _k, _l, _t, _e, _n in [("beach_fine", "Fine-to-medium sand beach", "sand_beach", "3A", "sand beach (ESI 3A)."),
                           ("beach_coarse", "Coarse sand beach", "sand_beach", "4", "sand beach (ESI 4)."),
                           ("beach_mixed", "Mixed sand and gravel beach", "mixed_sediment", "5", "mixed sediment (ESI 5)."),
                           ("beach_gravel", "Gravel beach", "mixed_sediment", "6A", "mixed sediment (ESI 6A).")]:
    _h = HabitatView(_k, _l, lambda: None, _t, _BEACH_NOTE + _n, _e)
    HABITATS.append(HabitatView(_k, _l, _beach_renderer(_h), _t, _h.note, _e))
HABITAT_BY_KEY = {h.key: h for h in HABITATS}


# ---------------------------------------------------------------------------------------------------------------
# Featured entries for the site cards (V5.1 Session 2 Stage 2). Data access only: every value is read from a repository
# file, every evidence chip takes its state from the model registry, and nothing here states a recommendation.

@st.cache_data
def _model_states() -> dict:
    from src.shoreline_remediation import registry
    return {row["model_id"]: row["state"] for row in registry.governance_table()}


def _model_chip(model_id: str, what: str) -> tuple[str, str] | None:
    """(evidence grade, chip text) for a registered model, using the state the registry resolves. None if unknown."""
    state = _model_states().get(model_id)
    grade = T.TIER_TO_GRADE.get(state) if state else None
    if grade not in T.GRADES:
        return None
    return grade, f"{T.GRADES[grade]['label']}: {what}"


def _chips(*chips) -> tuple:
    return tuple(c for c in chips if c)


def featured_sites() -> list:
    """Site cards for the entries the dashboard can open today. `site_id` is the habitat key of render_site_evidence.
    An entry whose source data cannot be read is left out; a value the repository does not hold is shown as not available."""
    cards = []
    row = _sites()
    row = row[row.cell == EXAMPLE_CELL]
    if not row.empty:
        r = row.iloc[0]
        has_xy = pd.notna(r.get("lat")) and pd.notna(r.get("lon"))
        obs, fetch = r.get("observed_rate"), r.get("fetch_mean_m")
        cards.append(C.SiteCard(
            site_id="marsh", name="Bay Jimmy, Barataria Bay", kicker="Worked example", location="Louisiana, USA", habitat="Salt marsh (ESI 10A)",
            description=f"Marsh-edge cell {r['cell']}, oiled in the Deepwater Horizon spill (2010). Chosen by a fixed rule: the heavily "
                        "oiled Barataria cell nearest the Zengel et al. (2022) field plots.",
            facts=(
                C.SiteFact("Coordinates", f"{abs(r['lat']):.3f}\u00b0 {'N' if r['lat'] >= 0 else 'S'}, {abs(r['lon']):.3f}\u00b0 {'E' if r['lon'] >= 0 else 'W'}"
                           if has_xy else None, "record"),
                C.SiteFact("SCAT maximum oiling", T.OILING_LABELS.get(r["max_oiling"], str(r["max_oiling"])) if pd.notna(r.get("max_oiling")) else None,
                           "observed"),
                C.SiteFact("Edge loss 2010 to 2015 (aerial images)", f"{obs:.2f} m/yr" if pd.notna(obs) else None, "observed"),
                C.SiteFact("Mean fetch", f"{fetch:,.0f} m" if pd.notna(fetch) else None, "derived"),
            ),
            evidence=_chips(_model_chip("edge_loss_v1", "marsh-edge loss model"),
                            _model_chip("composer_natural_recovery_v1", "treatment comparison")),
            action_label="Open the Bay Jimmy assessment"))
    try:
        eff, _ = _mangrove_results()
        e = eff[eff.outcome == "root_documented_dead_share"]
    except Exception:  # result files missing: no mangrove card, rather than a card with made-up content
        e = pd.DataFrame()
    if not e.empty:
        cards.append(C.SiteCard(
            site_id="mangrove", name="Bah\u00eda Las Minas", kicker="Limited evidence", location="Caribbean coast of Panama",
            habitat="Red mangrove fringe",
            description="One field study of the 1986 spill: how oiled fringe sites differed from unoiled ones. It describes oiling "
                        "damage only. There is no cleanup forecast for mangroves.",
            facts=(
                C.SiteFact("Coordinates", None),
                C.SiteFact("Study sites", f"{int(e.n_oiled_sites.iloc[0])} oiled, {int(e.n_unoiled_sites.iloc[0])} unoiled", "observed"),
                C.SiteFact("Years after the spill covered", f"{int(e.year_since_spill.min())} to {int(e.year_since_spill.max())}", "observed"),
                C.SiteFact("Cleanup outcome data", None),
            ),
            evidence=_chips(_model_chip("mangrove_damage_v1", "oiling-damage model"),
                            ("ai_proposed", "AI-proposed: cleanup verdicts")),
            action_label="Open the mangrove evidence"))
    beach = HABITAT_BY_KEY.get("beach_fine")
    if beach is not None:
        cards.append(C.SiteCard(
            site_id=beach.key, name=beach.label, kicker="Habitat screening", location="No site record",
            habitat=f"ESI {beach.esi}",
            description="A habitat-level entry, not a surveyed site. Cleanup options are screened with rules and published findings "
                        "for the conditions you enter. There is no site-specific forecast.",
            facts=(C.SiteFact("Site observations", None), C.SiteFact("Numerical cleanup forecast", None)),
            evidence=_chips(("rules_literature", "Rules and literature only: cleanup options"),
                            _model_chip("beach_sand_persistence_v1", "visible-oil persistence reference")),
            action_label="Open the beach screening"))
    return cards


def select_site(site_id: str) -> None:
    """Button callback for a site card: point the existing habitat switcher (and, for the marsh, the existing site picker)
    at the chosen entry. Unknown ids are ignored, so the current page stays as it is."""
    if site_id not in HABITAT_BY_KEY:
        return
    st.session_state["site_habitat"] = site_id
    if site_id == "marsh":
        st.session_state["site_mode"] = SITE_MODE_WORKED


def render_site_evidence() -> None:
    key = st.segmented_control("Habitat", [h.key for h in HABITATS], default="marsh", required=True, key="site_habitat",
                               format_func=lambda k: HABITAT_BY_KEY[k].label)
    HABITAT_BY_KEY[key].render()
