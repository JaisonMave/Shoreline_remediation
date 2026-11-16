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
from src.shoreline_remediation import ui_compare, ui_decision_board, ui_evidence as E, ui_pipeline as P, ui_report, ui_theme as T
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


# ---------------------------------------------------------------------------------------------------------------
# Scenario form and decision board (V5.1 Stage 2). The controls are the existing ones (oil category, season, oiling class, wave
# exposure) relocated into one short form; one button runs the cached pipeline (ui_pipeline) and ui_decision_board draws it.

_SCENARIO_FIELDS = ("oil", "season", "oiling", "exposure", "named_q", "named_id")
OIL_CATEGORIES = ["light", "medium", "heavy", "solid"]
SEASONS = ["site default (summer)", "spring", "summer", "autumn", "winter"]
EXPOSURES = ["low", "moderate", "high", "very_high"]
BOARD_RUN_KEY = "site_board_run"


def _skey(habitat: str, name: str) -> str:
    """Widget key of a scenario control. Marsh keeps its original site_* keys; the other habitats their beach_<habitat>_* keys."""
    return f"site_{name}" if habitat == "marsh" else f"beach_{habitat}_{name}"


def scenario_state_keys() -> tuple:
    """Session keys of the scenario form for every habitat, for ui_nav.keep_alive (the controls vanish while another page shows)."""
    keys = [_skey(h.key, n) for h in HABITATS for n in _SCENARIO_FIELDS]
    return tuple(keys) + (BOARD_RUN_KEY,)


@dataclass(frozen=True)
class ScenarioValues:
    oil_category: str
    oil: str                       # category, or an ADIOS oil id the pipeline resolves to a category
    season: str | None
    oiling: str | None
    exposure: str | None


def _named_oil(habitat: str) -> str | None:
    """Optional named oil from the NOAA ADIOS library (oil_library.search_options). None means: use the category."""
    from src.shoreline_remediation.oil_library import search_options
    query = st.text_input("Search NOAA ADIOS oils by name", key=_skey(habitat, "named_q"),
                          help="Optional. A named oil is turned into a category from its API gravity and pour point.")
    options = search_options(query) if query.strip() else []
    if query.strip() and not options:
        st.caption("No oil with a measured API gravity matches that search; the oil category above is used.")
    if not options:
        return None
    labels = dict(options)
    return st.selectbox("Matching oils", [None, *labels], format_func=lambda x: "Use the oil category above" if x is None else labels[x],
                        key=_skey(habitat, "named_id"))


def _scenario_form(habitat: str, *, oiling_from_record: str | None = None, ask_oiling: bool = True, ask_exposure: bool = False,
                   default_oil: str = "light", default_oiling: str = "Moderate") -> ScenarioValues:
    """Required: oil category and oiling class (read from the cell's record when it has one). Optional, collapsed: season and a
    named oil. Wave exposure is asked only for habitats whose screening reads it (beaches and rocky shores)."""
    cols = st.columns(3 if ask_exposure else 2)
    cat = cols[0].selectbox("Oil category (required)", OIL_CATEGORIES, index=OIL_CATEGORIES.index(default_oil), key=_skey(habitat, "oil"),
                            help="Deepwater Horizon oil was a light crude that arrived weathered and emulsified.")
    oiling = None
    if oiling_from_record:
        cols[1].markdown("**Oiling class (from the record)**")
        cols[1].markdown(f"{T.OILING_LABELS.get(oiling_from_record, oiling_from_record)}: SCAT record of this cell. Change the place "
                         "to change it.")
    elif ask_oiling:
        oiling = cols[1].selectbox("Oiling class (required)", CLASSES, index=CLASSES.index(default_oiling),
                                   format_func=lambda x: T.OILING_LABELS[x], key=_skey(habitat, "oiling"))
    exposure = None
    if ask_exposure:
        exposure = cols[2].selectbox("Wave exposure", EXPOSURES, index=1, format_func=_label, key=_skey(habitat, "exposure"))
    with st.expander("Optional: season and a named oil"):
        season = st.selectbox("Season of cleanup", SEASONS, key=_skey(habitat, "season"),
                              help="Used to check season-dependent conditions in the literature.")
        oil_id = _named_oil(habitat)
    return ScenarioValues(cat, oil_id or cat, None if season.startswith("site") else season, oiling_from_record or oiling, exposure)


def _record_table(rows: list) -> None:
    """Read-only (field, value, type) table. `type` is record, observed, derived or entered; nothing here is editable."""
    st.dataframe(pd.DataFrame(rows, columns=["Field", "Value", "Type"]), hide_index=True, width="stretch")


def _trace_expander(report) -> None:
    with st.expander("Technical trace: pipeline steps, sources and version"):
        version = report.version or {}
        st.markdown(f"Pipeline {version.get('pipeline_version', '?')}"
                    + (f", code commit {str(version['git_commit'])[:9]}" if version.get("git_commit") else "")
                    + (f", random seed {version['seed']}, {version['n_draws']} Monte Carlo draws" if "seed" in version else "") + ".")
        if report.trace:
            st.dataframe(pd.DataFrame([{"Step": t.get("step"), "Name": str(t.get("name", "")).replace("_", " "),
                                        "Sources": "; ".join(map(str, t.get("sources", []) or []))} for t in report.trace]),
                         hide_index=True, width="stretch")
            st.caption("Raw step inputs and outputs are in the downloadable report (JSON) of the pipeline; the table lists each step and its sources.")


def _provenance_panel(habitat: str, habitat_label: str) -> None:
    """Collapsed provenance of the literature priors table. Display only: reads literature_priors, never alters a recommendation."""
    from src.shoreline_remediation import literature_priors as LP
    with st.expander("Provenance of the literature priors"):
        try:
            rows = LP.provenance_rows()
            n_assumed = LP.assumed_count()
        except (OSError, ValueError) as exc:
            st.warning(f"Provenance table: unavailable ({type(exc).__name__}).")
            return
        show = rows.rename(columns={"parameter_id": "Parameter", "source": "Citation", "doi": "DOI", "unit": "Unit", "low": "Low", "high": "High"})
        st.dataframe(show[["Parameter", "Citation", "DOI", "Unit", "Low", "High"]], hide_index=True, width="stretch")
        st.caption(f"{len(rows)} cited rows (SOURCED or LITERATURE); {n_assumed} further rows are ASSUMED and are not listed. "
                   "These are inputs of an experimental process model, not outcome estimates.")
        st.markdown(LP.ASSUMED_STATEMENT)
        st.markdown(f"**For {habitat_label}:** {LP.NO_ESTIMATE_STATEMENT}")


def _run_spec(spec: tuple):
    kind, *args = spec
    return P.decision_for_site(*args) if kind == "site" else P.decision_for_scenario(*args)


def _decision_section(habitat: str, spec: tuple, where: str, site_flags=None, esi: str | None = None, habitat_label: str = "") -> None:
    """One button runs the cached pipeline for `spec`; the board then shows the last run of this habitat. If the place or the
    scenario changed since that run, the board says so instead of silently showing a different scenario."""
    if st.button("Run decision pipeline", key=f"run_{habitat}", type="primary", icon=":material/play_arrow:"):
        st.session_state[BOARD_RUN_KEY] = {"habitat": habitat, "spec": spec, "where": where, "flags": site_flags,
                                           "esi": esi, "habitat_label": habitat_label or habitat}
    rec = st.session_state.get(BOARD_RUN_KEY)
    if not rec or rec.get("habitat") != habitat:
        st.info("Nothing has been run yet. Set the scenario and press Run: the board then shows what the pipeline returns, including "
                "when the answer is that the evidence is insufficient.")
        _provenance_panel(habitat, habitat_label or habitat)
        return
    if rec["spec"] != spec:
        st.warning("The place or the scenario changed since this run. The board shows the earlier run below; press Run again to "
                   "update it.", icon=":material/warning:")
    report, err = _run_spec(rec["spec"])
    st.markdown(f"**Decision board for:** {rec['where']}")
    if err:
        st.error(f"The decision pipeline could not run ({err}).")
        return
    ui_decision_board.render_decision_board(report, rec.get("flags"), {"key": habitat, "habitat": rec.get("habitat_label") or habitat,
                                                                       "esi": rec.get("esi")})
    _provenance_panel(habitat, rec.get("habitat_label") or habitat)
    _trace_expander(report)


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
    C.section_header("Assess this place", kicker="Site assessment", description="1. Place. 2. Scenario. 3. Run the pipeline. The decision "
                     "board shows what the platform recommends, what it cannot recommend, and why.")
    st.markdown("**1. Place**")
    site = _pick_site(sites)
    if site is None:
        return
    values = {f: site.get(f) for f in FEATURES}
    flags = site_flags(values, site["status"], site["esi_main"], site["max_oiling"], site.get("lat"), site.get("lon"), m)
    is_new = site["source"] == "new site"
    obs0 = site.get("observed_rate")
    rows = [("Cell", site["cell"], "entered" if is_new else "record"), ("Basin", str(site["basin"]).title(), "entered" if is_new else "record"),
            ("SCAT segment", site.get("segment", "-"), "record"), ("Shoreline (ESI)", site["esi_main"], "entered" if is_new else "record"),
            ("SCAT maximum oiling", T.OILING_LABELS.get(site["max_oiling"], site["max_oiling"]), "entered" if is_new else "record"),
            ("Latitude, longitude", f"{site['lat']:.5f}, {site['lon']:.5f}", "entered" if is_new else "record"),
            ("Edge loss 2010 to 2015 (aerial images)", "not available" if obs0 is None or pd.isna(obs0) else f"{obs0:.2f} m/yr",
             "not available" if is_new else "observed")]
    if not is_new:
        rows.append(("Model scope status in the site table", STATUS_TEXT.get(site["status"], site["status"]).split(":")[0], "record"))
    rows += [(FEATURE_LABELS[f], "missing" if pd.isna(site.get(f)) else (f"{float(site[f]):,.0f}" if f == "fetch_mean_m" else f"{float(site[f]):.2f}"),
              "entered" if is_new else "derived") for f in FEATURES]
    _record_table(rows)
    if is_new:
        st.caption("A typed site has no row in the site table, so no model scope status is assigned. The board runs the generic salt-marsh "
                   "scenario path and shows the scope tier the pipeline returns; the typed edge-loss inputs are not used by that path.")
    st.markdown("**2. Scenario**")
    sv = _scenario_form("marsh", oiling_from_record=None if is_new or site["max_oiling"] not in CLASSES else site["max_oiling"],
                        ask_oiling=is_new or site["max_oiling"] not in CLASSES, default_oiling=site["max_oiling"] if site["max_oiling"] in CLASSES else "Moderate")
    oil, season = sv.oil, sv.season
    st.markdown("**3. Run**")
    where_board = (f"{'Worked example: ' if site.get('cell') == EXAMPLE_CELL else ''}{'typed site' if is_new else 'cell ' + str(site['cell'])} | "
                   f"Salt marsh | oiling: {T.OILING_LABELS.get(site['max_oiling'], site['max_oiling'])} | oil: {sv.oil_category}"
                   + (f" (named oil {sv.oil})" if sv.oil != sv.oil_category else "") + (f" | season: {season}" if season else ""))
    if is_new:
        scen = _scenario("salt_marsh", oil_category=sv.oil_category)
        spec = ("scenario", P.scenario_items(scen), site["max_oiling"], oil, season, "salt_marsh")
    else:
        spec = ("site", P.site_items(site), oil, season)
    _decision_section("marsh", spec, where_board, flags if not is_new else None, esi=str(site["esi_main"]), habitat_label="salt marsh")
    st.divider()
    C.section_header("Detailed evidence", kicker="Existing views", description="The earlier site views, for the same place and scenario "
                     "inputs. They update as you change the inputs; the decision board above shows only the scenario you ran.")
    if is_new:
        st.caption("The detailed views below take the typed values as measured and treat the site as in scope of the edge-loss model; "
                   "the decision board above does not.")
    answer = st.container()
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
    C.section_header("Assess this habitat", kicker="Site assessment", description="Limited evidence: one field study of oiling damage. "
                     "The pipeline takes no oil, oiling or season input for mangroves and may abstain from a cleanup recommendation.")
    st.markdown("**1. Place**")
    _record_table([("Study site", "Bahía Las Minas, Panama (Rhizophora fringe), spill of 1986", "record"),
                   ("Cleanup outcome data", "not available", "not available"),
                   ("Numerical cleanup forecast", "not available for mangroves", "not available")])
    st.markdown("**2. Scenario**")
    st.caption("No scenario inputs: the mangrove evidence does not depend on oil category, oiling class or season, so none are asked for.")
    st.markdown("**3. Run**")
    spec = ("scenario", P.scenario_items(_scenario("mangrove")), None, None, None, "mangrove")
    _decision_section("mangrove", spec, "Mangrove (Rhizophora fringe) | Bahía Las Minas, Panama, 1986", habitat_label="mangrove")
    st.divider()
    C.section_header("Detailed evidence", kicker="Existing views", description="The earlier mangrove evidence views. The decision board above "
                     "shows only the run you started.")
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


def _screening_renderer(h: "HabitatView") -> Callable[[], None]:
    """Rules-and-literature screening page for a shoreline class with no outcome model (beaches and rocky shores). The
    pipeline is the same one; only the scope text and the habitat code passed to it differ."""
    def render() -> None:
        C.scope_panel(h.family)
        C.section_header("Assess this habitat", kicker="Site assessment", description="1. Place. 2. Scenario. 3. Run the pipeline. This is "
                         "a habitat-level entry with rules and literature only; the board may conclude that evidence is insufficient.")
        st.markdown("**1. Place**")
        st.caption(h.note)
        _record_table([("Shoreline type", h.label, "record"), ("Shoreline (ESI)", h.esi, "record"),
                       ("Site observations", "not available: habitat-level entry, no surveyed site", "not available"),
                       ("Numerical cleanup forecast", "not available for this shoreline type", "not available")])
        st.markdown("**2. Scenario**")
        sv = _scenario_form(h.key, ask_exposure=True, default_oil="medium")
        oiling, oil, exposure, season = sv.oiling, sv.oil, sv.exposure, sv.season
        scen = _scenario(h.shoreline_type, wave_exposure=exposure, oil_category=sv.oil_category)
        st.markdown("**3. Run**")
        where_board = (f"{h.label} (ESI {h.esi}) | oiling: {T.OILING_LABELS[oiling]} | {sv.oil_category} oil"
                       + (f" (named oil {oil})" if oil != sv.oil_category else "") + f" | {_label(exposure)} wave exposure"
                       + (f" | season: {season}" if season else ""))
        _decision_section(h.key, ("scenario", P.scenario_items(scen), oiling, oil, season, h.esi), where_board, esi=h.esi, habitat_label=h.label)
        st.divider()
        C.section_header("Detailed evidence", kicker="Existing views", description="The earlier habitat views, for the same scenario "
                         "inputs. They update as you change the inputs; the decision board above shows only the scenario you ran.")
        report, err = P.decision_for_scenario(P.scenario_items(scen), oiling, oil, season, h.esi)
        view = E.report_view(report) if report is not None else None
        C.answer_card(view, f"{h.label} | oiling: {T.OILING_LABELS[oiling]} | {sv.oil_category} oil | {_label(exposure)} wave exposure")
        if err:
            st.error(f"The decision pipeline could not run ({err}).")
        ref = next((r for r in (view.reference if view else []) if E.field(r, "curves_by_group")), None)
        C.render_beach_persistence({"habitat": h.key, "esi": h.esi, "label": h.label, "oiling_class": oiling, "oil_category": sv.oil_category,
                                    "exposure": exposure, "reference": ref, "literature_notes": view.literature_notes if view else []})
        if view is not None and view.advisories:
            with st.expander("Advisory notes (AI-proposed, not used to set the classes)"):
                for a in view.advisories:
                    st.markdown(f"- {a}")
        st.subheader("Options and what the evidence says")
        if any(HABITAT_MODELS.get(h.key, ())):
            st.caption("The cleanup options below come from screening rules and published findings only. The experimental "
                       "persistence reference above is not evidence that any of these options works.")
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
    family: str = "beach"          # key of ui_theme.SCOPE_ONE_LINE / SCOPE_LIMITS: "beach" or "rocky"


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
    HABITATS.append(HabitatView(_k, _l, _screening_renderer(_h), _t, _h.note, _e))
_ROCKY_ESI = ("1A", "8A")
_ROCKY_NOTE = ("The rocky shore type you picked is passed to the decision pipeline by its ESI code. Rocky shores have no outcome "
               "model and no observed site records in this platform: ")


def _add_rocky_habitats() -> None:
    """ESI 1A and 8A entries. Labels come from the habitat table; if it cannot be read the entries are omitted."""
    from src.shoreline_remediation import habitat as _habitat
    try:
        rows = _habitat.table()
    except Exception:
        return
    for esi in _ROCKY_ESI:
        row = rows.get(esi)
        if row is None or not row.name:
            continue
        label = row.name[:1].upper() + row.name[1:]
        h = HabitatView(f"esi_{esi}", label, lambda: None, "rocky_shore", _ROCKY_NOTE + f"{row.name} (ESI {esi}).", esi, "rocky")
        HABITATS.append(HabitatView(h.key, h.label, _screening_renderer(h), h.shoreline_type, h.note, h.esi, "rocky"))


_add_rocky_habitats()
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


# ---------------------------------------------------------------------------------------------------------------
# Habitat coverage for the landing page (V5.1 Session 2 Stage 3). Data access only: the coverage tier of each habitat is
# DERIVED from the model registry states of the models linked to it, so a registry demotion flows through. Nothing here
# is a recommendation or a prediction.

HABITAT_MODELS = {"marsh": ("edge_loss_v1", "pah_decline_v1", "composer_natural_recovery_v1", "veg_recovery_v1"),
                  "mangrove": ("mangrove_damage_v1",), "beach_fine": ("beach_sand_persistence_v1",)}
_MODEL_WHAT = {"edge_loss_v1": "marsh-edge loss model", "pah_decline_v1": "soil PAH decline model",
               "composer_natural_recovery_v1": "treatment comparison", "veg_recovery_v1": "vegetation recovery curve",
               "mangrove_damage_v1": "oiling-damage model", "beach_sand_persistence_v1": "visible-oil persistence reference"}
_HABITAT_SUMMARY = {
    "marsh": "Numbers are validated only for salt-marsh edge loss in three Louisiana basins and Deepwater Horizon soil PAH, "
             "from one spill. The treatment comparison is experimental.",
    "mangrove": "Oiling-damage evidence from one study. There is no cleanup forecast for mangroves.",
    "beach_fine": "Only an experimental visible-oil persistence reference exists. There is no site forecast; cleanup options "
                  "are screened with rules and published findings.",
}
_BEACH_SUMMARY = "Rules and published findings only. There is no numerical forecast for this beach type."
_BEACH_CHIP = ("rules_literature", "Rules and literature only: cleanup options (no experimental evidence)")
_ROCKY_CHIP = _BEACH_CHIP
_ROCKY_SUMMARY = ("Rules and published findings only. There is no site record, no outcome model and no numerical forecast "
                  "for this rocky shore type; natural recovery with monitoring stays the reference option.")


@dataclass(frozen=True)
class HabitatCoverage:
    key: str
    label: str
    esi: str
    tier: str                      # key of ui_theme.COVERAGE_TIERS
    summary: str
    evidence: tuple                # (grade, text) chips
    opens: str | None              # habitat key the dashboard can open, else None
    availability: str | None = None


def _coverage_tier(model_ids) -> str:
    """Derived from registry states: any validated -> numerical; else any experimental -> experimental; else screening.
    A model id the registry does not know counts as no evidence."""
    states = [_model_states().get(m) for m in model_ids]
    if "validated" in states:
        return "numerical"
    if "experimental" in states:
        return "experimental"
    return "screening"


def habitat_coverage() -> list:
    """One entry per openable habitat (salt marsh, mangrove, beaches and the rocky-shore rows of the habitat table), and a final
    'other shoreline types' entry for habitats the platform does not support."""
    from src.shoreline_remediation import habitat as _habitat
    out = []
    for h in HABITATS:
        esi = h.esi or _habitat.normalise(h.key)
        ids = HABITAT_MODELS.get(h.key, ())
        chips = [c for c in (_model_chip(m, _MODEL_WHAT[m]) for m in ids) if c]
        if h.key.startswith("beach_") or h.family == "rocky":
            chips.append(_BEACH_CHIP if h.family == "beach" else _ROCKY_CHIP)   # after the model chip: separate lines of evidence
        elif h.key == "mangrove":
            chips.append(("ai_proposed", "AI-proposed: cleanup verdicts"))
        out.append(HabitatCoverage(h.key, h.label, "" if esi == _habitat.UNKNOWN else esi, _coverage_tier(ids),
                                   _HABITAT_SUMMARY.get(h.key, _ROCKY_SUMMARY if h.family == "rocky" else _BEACH_SUMMARY), tuple(chips), h.key))
    from src.shoreline_remediation.decision_pipeline import OUTCOME_LABELS
    out.append(HabitatCoverage(
        "unsupported", "Other shoreline types", "", "unsupported",
        "Habitats without a row in the platform's habitat table (for example coral reef or seagrass) get no screening, comparison "
        f"or recommendation. The pipeline abstains: {OUTCOME_LABELS['unsupported_habitat']}.",
        (("out_of_scope", T.TIER_TEXT["unsupported_habitat"]),), None, "No assessment is made"))
    return out


def habitat_cards() -> list:
    """SiteCards for habitat_coverage(). Entries that cannot be opened carry their availability as `location` and no
    button is drawn for them (the landing page passes on_select=None for them)."""
    cards = []
    for c in habitat_coverage():
        openable = c.opens is not None
        action = f"Open the {c.label.lower()} assessment" if openable else ""
        cards.append(C.SiteCard(site_id=c.opens or c.key, name=c.label, kicker=T.COVERAGE_TIERS[c.tier]["label"],
                                location="" if openable else (c.availability or ""), habitat=f"ESI {c.esi}" if c.esi else "",
                                description=c.summary, facts=(), evidence=c.evidence, action_label=action, tier=c.tier))
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
