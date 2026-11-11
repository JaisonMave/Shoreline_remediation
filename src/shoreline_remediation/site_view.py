"""Streamlit view for P5 'Site evidence (real data)' (plan: docs/P5_DEMO_PLAN.md).

Logic lives in site_evidence.py; this module only lays it out. Reads committed files, needs no network except
for the map's base tiles.
"""
from __future__ import annotations

import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.shoreline_remediation.site_evidence import (FEATURE_LABELS, FEATURES, STATUS_TEXT, load_model, load_sites,
                                                     predict_edge_loss, site_flags, site_scenario,
                                                     site_scenario_inputs, treatment_evidence)

OIL_COLOURS = {"Heavy": "#a32a2a", "Moderate": "#db8b3e", "Light": "#e8c547", "Very_Light": "#9bb8a8", "NOO": "#5b8fb0"}
CLASSES = ["Heavy", "Moderate", "Light", "Very_Light", "NOO"]
BASINS = ["barataria", "breton", "terrebonne", "birdfoot"]
EXAMPLE_CELL = "8018_32612"  # docs/P5_WORKED_EXAMPLE.md (rule in docs/P5_DEMO_PLAN.md section 5)


@st.cache_data
def _sites() -> pd.DataFrame:
    return load_sites()


@st.cache_data(show_spinner="Running the rule screening...")
def _screen(inputs: tuple, oil_category: str) -> list[dict]:
    from src.shoreline_remediation.decision_framework import HybridDecisionModel
    site = dict(inputs)
    ranked = HybridDecisionModel().rank_treatments(site_scenario(site, oil_category))
    return [{"treatment": r.treatment, "feasibility": r.feasibility, "utility": r.utility, "reason": r.reason} for r in ranked]


def _label(x: str) -> str:
    return x.replace("_", " ")


def _pick_site(sites: pd.DataFrame) -> dict | None:
    mode = st.radio("Site", ["Worked example (Bay Jimmy, Barataria Bay)", "Pick a Louisiana edge cell", "New site (enter values)"],
                    horizontal=True, key="site_mode")
    if mode.startswith("Worked"):
        row = sites[sites.cell == EXAMPLE_CELL]
        if row.empty:
            st.error("Worked-example cell not found; rebuild with scripts/build_p5_demo.py.")
            return None
        st.caption("Chosen by a fixed rule: the heavily oiled Barataria cell nearest the Zengel et al. (2022) field plots, "
                   "so site and treatment evidence come from the same marsh. Written up in docs/P5_WORKED_EXAMPLE.md.")
        return {**row.iloc[0].to_dict(), "source": "edge cell"}
    if mode.startswith("Pick"):
        c1, c2, c3 = st.columns(3)
        basin = c1.selectbox("Basin", BASINS, format_func=str.title, key="pick_basin")
        oiling = c2.selectbox("SCAT maximum oiling", ["any"] + CLASSES, format_func=_label, key="pick_oil")
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
    m = load_model()
    r = m["training_range"]
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
    oiling = c8.selectbox("Oiling class", CLASSES, format_func=_label, key="new_oil")
    return {**v, "lat": lat, "lon": lon, "esi_main": habitat, "max_oiling": oiling, "status": "in_scope",
            "basin": "new site", "cell": "new site", "segment": "-", "source": "new site"}


def _map(sites: pd.DataFrame, site: dict) -> None:
    if site["source"] == "new site":
        pts = pd.DataFrame([{"lat": site["lat"], "lon": site["lon"], "color": "#111111", "size": 120.0}])
    else:
        d = sites[(sites.basin == site["basin"]) & (sites.esi_main == "10A")][["lat", "lon", "max_oiling"]]
        pts = d.assign(color=d.max_oiling.map(OIL_COLOURS).fillna("#888888"), size=40.0)[["lat", "lon", "color", "size"]]
        pts = pd.concat([pts, pd.DataFrame([{"lat": site["lat"], "lon": site["lon"], "color": "#111111", "size": 160.0}])])
    st.map(pts, latitude="lat", longitude="lon", color="color", size="size", zoom=9 if site["source"] != "new site" else 7,
           width="stretch")
    st.caption("Salt-marsh edge cells in this basin, coloured by SCAT maximum oiling: dark red Heavy, orange Moderate, "
               "yellow Light, green Very light, blue no oil observed. Black = selected site.")


def _interval_chart(pred: dict, observed: float | None, sites: pd.DataFrame) -> plt.Figure:
    train = sites.loc[sites.status == "in_scope", "observed_rate"].dropna()
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.hist(train.clip(-8, 10), bins=80, color="#c9d6cf", label="Observed rates, all training cells (NAIP 2010-2015)")
    ax.axvspan(pred["lo"], pred["hi"], color="#2d7d6d", alpha=.18, label="90% prediction interval")
    ax.axvline(pred["rate"], color="#2d7d6d", lw=2.5, label="Expected rate at this site")
    if observed is not None and not math.isnan(observed):
        ax.axvline(observed, color="#a32a2a", lw=1.8, ls="--", label="Observed at this cell")
    ax.set_xlabel("Marsh-edge loss, m/yr (positive = land lost)")
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    return fig


def render_site_evidence() -> None:
    m = load_model()
    sites = _sites()
    st.markdown("Everything in this tab comes from real data: Deepwater Horizon shoreline surveys (SCAT), aerial and "
                "Landsat imagery, and field plots from Zengel et al. (2015, 2022). Numbers come with 90% intervals.")
    site = _pick_site(sites)
    if site is None:
        return
    left, right = st.columns([1.25, 1])
    with left:
        _map(sites, site)
    with right:
        st.markdown("#### Site")
        info = [("Cell", site["cell"]), ("Basin", str(site["basin"]).title()), ("SCAT segment", site.get("segment", "-")),
                ("Shoreline (ESI)", site["esi_main"]), ("SCAT maximum oiling", _label(str(site["max_oiling"])))]
        info += [(FEATURE_LABELS[f], "missing" if pd.isna(site.get(f)) else
                  (f"{float(site[f]):,.0f}" if f == "fetch_mean_m" else f"{float(site[f]):.2f}")) for f in FEATURES]
        st.dataframe(pd.DataFrame(info, columns=["Input", "Value"]), hide_index=True, width="stretch")

    values = {f: site.get(f) for f in FEATURES}
    flags = site_flags(values, site["status"], site["esi_main"], site["max_oiling"], site.get("lat"), site.get("lon"), m)
    for x in flags.out_of_scope:
        st.error(x, icon=":material/block:")
    for x in flags.extrapolation:
        st.warning(x, icon=":material/warning:")

    st.subheader("Expected marsh-edge loss")
    if flags.in_scope:
        pred = predict_edge_loss(values, m)
        up = m["heavy_uplift_range_m_per_yr"]
        cols = st.columns(4)
        cols[0].metric("Expected rate", f"{pred['rate']:.2f} m/yr")
        cols[1].metric("90% interval", f"{pred['lo']:.1f} to {pred['hi']:.1f}")
        cols[2].metric("Heavy-oil uplift, m/yr", f"+{up[0]:.1f} to {up[1]:.1f}")
        obs = site.get("observed_rate")
        cols[3].metric("Observed at this cell", "-" if obs is None or pd.isna(obs) else f"{obs:.2f} m/yr")
        st.pyplot(_interval_chart(pred, obs if obs is not None else None, sites), width="stretch")
        held = site.get("p2_heldout_M1")
        st.caption(
            "Expected rate: marsh edge with this exposure and pre-spill trend, from model p5-edge-loss-v1 (exposure only, no oiling term). "
            f"Heavy-oiling uplift: extra loss associated with heavy oiling in P2's training folds, shown separately because it was unstable "
            f"between basins (P1 headline 0.85, 0.49 to 1.22). "
            + (f"When this basin was held out entirely in P2, the model predicted {held:.2f} m/yr here. " if held is not None and not pd.isna(held) else "")
            + f"The interval is wide because single 100 m cells are noisy: the model's held-out error is {m['lobo_mae']:.2f} m/yr against "
            f"{m['lobo_mae_no_predictor']:.2f} m/yr for predicting the average everywhere (leave-one-basin-out). " + m["measurement_note"])
    else:
        st.write("No prediction: the site is outside what the model was fitted and tested on (see the reason above).")

    st.subheader("Cleanup options for this site")
    oil = st.selectbox("Oil category for the rule screening", ["light", "medium", "heavy", "solid"], key="site_oil",
                       help="Deepwater Horizon oil was a light crude that arrived weathered and emulsified.")
    if site["esi_main"] != "10A":
        st.info("Rule screening here is set up for salt marsh only; use the Scenario screening tab for other shorelines.")
        return
    inputs = tuple((k, site.get(k)) for k in ("max_oiling", "fetch_mean_m"))
    ranked = _screen(inputs, oil)
    ev = treatment_evidence([r["treatment"] for r in ranked], site["max_oiling"]).set_index("treatment")
    rows = []
    for i, r in enumerate(ranked, 1):
        e = ev.loc[r["treatment"]]
        rows.append({"Rank": i, "Treatment": _label(r["treatment"]), "Rule screening": r["feasibility"], "Utility": round(r["utility"], 2),
                     "Extra erosion vs natural recovery, yr 0-2": e.erosion_0_2, "Same, yr 2-8": e.erosion_2_8,
                     "Vegetation cover vs natural recovery, yr 2": e.veg_cover_yr2})
    for name in ev.index[~ev.index.isin([r["treatment"] for r in ranked])]:
        e = ev.loc[name]
        rows.append({"Rank": None, "Treatment": name, "Rule screening": "restoration add-on", "Utility": None,
                     "Extra erosion vs natural recovery, yr 0-2": e.erosion_0_2, "Same, yr 2-8": e.erosion_2_8,
                     "Vegetation cover vs natural recovery, yr 2": e.veg_cover_yr2})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    for x in flags.evidence_scope:
        st.info(x, icon=":material/info:")
    st.caption("Rule screening: existing FAST-like rules (eligible, conditional, ineligible) with the inputs listed below. "
               "Evidence columns: differences against untreated (natural recovery) plots with 90% intervals, heavily oiled marsh at Bay Jimmy; "
               "erosion in m/yr (positive = more edge lost), vegetation cover in percentage points. One site, 5-9 plots per group; "
               "observational except planting, which was randomized. Where rules and evidence disagree (e.g. mechanical removal), "
               "both are shown and neither overrides the other. Treatment mapping (manual, mechanical, natural recovery) follows decision D13 (approved).")
    with st.expander("Rule-screening inputs implied by this site"):
        st.dataframe(pd.DataFrame(site_scenario_inputs(site, oil), columns=["Input", "Value", "Basis"]),
                     hide_index=True, width="stretch")
    with st.expander("Limits of this evidence"):
        st.markdown(
            "- One spill (Deepwater Horizon 2010), one oil, Louisiana salt marsh only. Transfer was tested between Louisiana basins (P2), not to other spills.\n"
            "- Associations, not proven causes; heavy oiling and the cleanup that followed are mixed together in the edge-loss data.\n"
            "- Physical (edge loss) and biological (vegetation) recovery only: no soil or sediment chemistry, so no chemical recovery prediction.\n"
            "- Out of scope: active river delta, water-dominated or plume areas where land/water mapping fails, and any non-salt-marsh shoreline.\n"
            "- Scope codes for every cell: " + "; ".join(f"`{k}` {v.split(':')[0].lower()}" for k, v in STATUS_TEXT.items()) + ".")
