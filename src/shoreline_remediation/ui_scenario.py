"""Legacy "Scenario screening" view, kept and re-based on the decision pipeline (decision D40).

What it is: the existing shoreline-cleanup rule screening, ordered inside each tier by an ASSUMED ecological score, plus a
process model with ASSUMED rates. Neither is validated against field outcomes. What changed:
  * the fabricated uncertainty band and the constant "decision confidence" percentages are gone (the old numbers were 0.6, 0.4
    or 0.2 by tier, not estimates); an evidence chip replaces them;
  * "ML-ranked" wording is gone (it is rule screening ordered by an assumed score);
  * the pipeline's recommendation classes, evidence grades and sources are shown first, and beside the process-model chart;
  * only the section chosen in the segmented control runs, so a click does not redraw everything.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.shoreline_remediation import ui_components as C
from src.shoreline_remediation import ui_evidence as E, ui_pipeline as P, ui_theme as T
from src.shoreline_remediation.data_model import Scenario
from src.shoreline_remediation.decision_framework import HybridDecisionModel
from src.shoreline_remediation.noaa_crosswalk import NOAA_TREATMENT_CROSSWALK
from src.shoreline_remediation.oil_library import scenario_oil_inputs, search_options
from src.shoreline_remediation.process_model import generate_lhs_scats, simulate_selected_scenario
from src.shoreline_remediation.scenario_runner import SCENARIO_LIBRARY, get_key_drivers
from src.shoreline_remediation.validation_panel import make_transect_figure, render_validation_tab

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ILLUSTRATIVE = T.LABELS["illustrative_chart"]
SECTIONS = ["Treatment ranking", "Process model", "Method test (synthetic data)", "NOAA cross-check", "Validation",
            "Constraints and endpoint", "Treatment details", "Scenario inputs"]


@st.cache_resource
def load_model() -> HybridDecisionModel:
    return HybridDecisionModel()


@st.cache_data
def load_benchmark_results() -> pd.DataFrame:
    path = PROJECT_ROOT / "reports" / "comparison_report.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["model", "treatment", "mae", "r2"])


@st.cache_data
def load_lhs_dataset() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "lhs_scat_process_dataset.csv"
    return pd.read_csv(path) if path.exists() else generate_lhs_scats(n_segments=100, seed=42)


@st.cache_data(show_spinner=False)
def _trajectory(items: tuple, treatment: str, days: tuple | None = None) -> pd.DataFrame:
    scenario = Scenario(**dict(items))
    return simulate_selected_scenario(scenario, treatment, survey_days=list(days) if days else None)


def traj(scenario: Scenario, treatment: str, days=None) -> pd.DataFrame:
    return _trajectory(P.scenario_items(scenario), treatment, tuple(days) if days else None)


def _name(x: str) -> str:
    return x.replace("_", " ").title()


def preset_name(index: int, scenario: Scenario) -> str:
    return f"Scenario {index + 1}: {scenario.shoreline_type.replace('_', ' ').title()}"


def selectbox_value(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def build_scenario(preset: Scenario | None) -> Scenario:
    source = preset or Scenario(shoreline_type="marsh")
    with st.sidebar:
        st.subheader("Scenario inputs")
        shoreline_type = st.selectbox(
            "Shoreline type", ["marsh", "sand_beach", "mixed_sediment", "cobble", "mudflat", "bedrock", "boulder", "peat", "tundra"],
            index=selectbox_value(["marsh", "sand_beach", "mixed_sediment", "cobble", "mudflat", "bedrock", "boulder", "peat", "tundra"], source.shoreline_type),
            format_func=lambda value: value.replace("_", " ").title(),
        )
        shoreline_sensitivity = st.selectbox("Ecological sensitivity", ["low", "moderate", "high", "very_high"], index=selectbox_value(["low", "moderate", "high", "very_high"], source.shoreline_sensitivity), format_func=lambda value: value.replace("_", " ").title())
        temperature_c = st.slider("Temperature (°C)", -5.0, 35.0, float(source.temperature_c), 0.5)
        oil_input = st.radio("Oil", ["Choose oil by name", "Enter category"], horizontal=True)
        oil_category = None
        if oil_input == "Choose oil by name":
            query = st.text_input("Search NOAA ADIOS oils", value="South Louisiana")
            other_products = st.checkbox("Include other products (additives, solvents, lubricants)", value=False)
            options = search_options(query, spill_oils_only=not other_products)
            if options:
                labels = dict(options)
                oil_id = st.selectbox("Matching oils", list(labels), format_func=labels.get)
                oil = scenario_oil_inputs(oil_id, temperature_c)
                oil_category = oil["oil_category"]
                viscosity = ("not measured" if oil["kinematic_viscosity_cst"] is None
                             else f"{oil['kinematic_viscosity_cst']:.1f} cSt at {oil['viscosity_measured_at_c']:.0f} °C")
                pour = "not measured" if oil["pour_point_c"] is None else f"{oil['pour_point_c']:.0f} °C"
                st.caption(f"Category **{oil_category}** at {temperature_c:.1f} °C (API {oil['api_gravity']:.1f}; "
                           f"viscosity {viscosity}; pour point {pour}). Source: NOAA ADIOS oil database.")
            else:
                st.caption("No oil with a measured API gravity matches that search. Enter a category instead.")
        if oil_category is None:
            oil_category = st.selectbox("Oil category", ["light", "medium", "heavy", "solid"], index=selectbox_value(["light", "medium", "heavy", "solid"], source.oil_category), format_func=str.title)
        oil_coverage = st.slider("Oil coverage (%)", 0, 100, int(source.oil_coverage), 1)
        oil_thickness = st.slider("Oil thickness (mm)", 0.0, 30.0, float(source.oil_thickness), 0.5)
        penetration_depth_cm = st.slider("Penetration depth (cm)", 0.0, 30.0, float(source.penetration_depth_cm), 0.5)
        wave_exposure = st.selectbox("Wave exposure", ["low", "moderate", "high", "very_high"], index=selectbox_value(["low", "moderate", "high", "very_high"], source.wave_exposure), format_func=lambda value: value.replace("_", " ").title())
        tidal_range = st.selectbox("Tidal range", ["low", "moderate", "high"], index=selectbox_value(["low", "moderate", "high"], source.tidal_range), format_func=str.title)
        season = st.selectbox("Season", ["spring", "summer", "autumn", "winter"], index=selectbox_value(["spring", "summer", "autumn", "winter"], source.season), format_func=str.title)
        substrate_permeability = st.selectbox("Substrate permeability", ["low", "moderate", "high"], index=selectbox_value(["low", "moderate", "high"], source.substrate_permeability), format_func=str.title)
        surface_oil = st.checkbox("Surface oil present", value=source.surface_oil)
        subsurface_oil = st.checkbox("Subsurface oil present", value=source.subsurface_oil)
        accessibility = st.selectbox("Operational access", ["good", "moderate", "restricted"], index=selectbox_value(["good", "moderate", "restricted"], source.accessibility), format_func=str.title)
        habitat_type = st.text_input("Habitat type", value=source.habitat_type)
        recovery_potential = st.selectbox("Recovery potential", ["low", "moderate", "high"], index=selectbox_value(["low", "moderate", "high"], source.recovery_potential), format_func=str.title)
        waste_handling = st.selectbox("Waste handling", ["manageable", "moderate", "difficult"], index=selectbox_value(["manageable", "moderate", "difficult"], source.waste_handling), format_func=str.title)

    return Scenario(
        shoreline_type=shoreline_type,
        shoreline_sensitivity=shoreline_sensitivity,
        oil_category=oil_category,
        oil_coverage=oil_coverage,
        oil_thickness=oil_thickness,
        penetration_depth_cm=penetration_depth_cm,
        wave_exposure=wave_exposure,
        tidal_range=tidal_range,
        temperature_c=temperature_c,
        season=season,
        substrate_permeability=substrate_permeability,
        surface_oil=surface_oil,
        subsurface_oil=subsurface_oil,
        accessibility=accessibility,
        habitat_type=habitat_type,
        recovery_potential=recovery_potential,
        waste_handling=waste_handling,
    )
def estimate_endpoint(scenario: Scenario, result) -> dict:
    shoreline_days = {
        "bedrock": 45, "cobble": 60, "sand_beach": 75, "mixed_sediment": 90,
        "marsh": 150, "mudflat": 180, "peat": 210, "tundra": 240,
    }
    treatment_factor = {
        "manual_removal": 0.75, "vacuum_removal": 0.80, "passive_sorbents": 0.90,
        "low_pressure_flushing": 0.85, "low_pressure_heated_flushing": 0.78,
        "natural_attenuation": 1.45, "bioremediation": 1.15,
        "mechanical_removal": 0.82, "sediment_relocation": 1.00,
        "sediment_mixing": 1.10, "surface_washing_agents": 0.88,
        "solidifiers": 0.92, "high_pressure_washing": 0.72,
        "high_pressure_heated_washing": 0.68, "vegetation_cutting": 1.25,
    }
    recovery_factor = {"low": 1.35, "moderate": 1.0, "high": 0.78}[scenario.recovery_potential]
    oil_factor = {"light": 0.85, "medium": 1.0, "heavy": 1.25, "solid": 1.35}[scenario.oil_category]
    access_factor = {"good": 1.0, "moderate": 1.15, "restricted": 1.35}[scenario.accessibility]
    exposure_factor = {"low": 1.0, "moderate": 1.08, "high": 1.18, "very_high": 1.28}[scenario.wave_exposure]
    penetration_factor = 1.0 + min(scenario.penetration_depth_cm / 40.0, 0.75)
    base_days = shoreline_days.get(scenario.shoreline_type, 120)
    days_to_endpoint = base_days * treatment_factor.get(result.treatment, 1.0)
    days_to_endpoint *= recovery_factor * oil_factor * access_factor * exposure_factor * penetration_factor
    if result.feasibility == "conditional":
        days_to_endpoint *= 1.12
    if result.feasibility == "ineligible":
        days_to_endpoint *= 1.35
    days_to_endpoint = int(round(max(21, min(days_to_endpoint, 720))))
    return {
        "days": days_to_endpoint,
        "months": round(days_to_endpoint / 30.4, 1),
        "target": 0.80,
        "definition": "Rough time to 80% of the modelled recovery target, assuming the treatment is carried out and monitoring confirms progress.",
    }


def environmental_constraints(scenario: Scenario, result) -> list[str]:
    constraints = []
    if scenario.shoreline_sensitivity in {"high", "very_high"}:
        constraints.append("High ecological sensitivity: minimize foot traffic, equipment staging, and habitat disturbance.")
    if scenario.accessibility == "restricted":
        constraints.append("Restricted access: plan low-impact access routes, tide windows, and manual or lightweight equipment options.")
    if scenario.wave_exposure in {"high", "very_high"}:
        constraints.append("High wave exposure: work windows may be short and containment or sorbent deployment may be weather-limited.")
    if scenario.tidal_range == "high":
        constraints.append("Large tidal range: schedule operations around tide cycles and protect intertidal habitat during staging.")
    if scenario.subsurface_oil or scenario.penetration_depth_cm > 5:
        constraints.append("Subsurface or penetrating oil: excavation, flushing, and waste handling may create secondary disturbance and require confirmation sampling.")
    if scenario.habitat_type in {"salt_marsh", "mudflat"}:
        constraints.append("Sensitive wetland habitat: avoid rutting, sediment redistribution, vegetation damage, and uncontrolled washing residues.")
    if scenario.waste_handling in {"moderate", "difficult"}:
        constraints.append("Waste handling is constrained: define segregation, temporary storage, transport, and disposal controls before field work.")
    if result.feasibility == "conditional":
        constraints.append("The first option is conditional under the rule screening: confirm permits, method controls, and a contingency option before execution.")
    if not constraints:
        constraints.append("No major constraint flags were triggered by the current inputs; standard spill-response controls and monitoring still apply.")
    return constraints

def recovery_profiles(scenario: Scenario, results: list):
    candidates = [r for r in results if r.feasibility != "ineligible"][:5] or results[:5]
    endpoint_days = [estimate_endpoint(scenario, r)["days"] for r in candidates]
    horizon = max(365, int(max(endpoint_days, default=365) * 1.25))
    time = np.linspace(0, horizon, 500)
    days = sorted(set(np.linspace(0, horizon, 80, dtype=int).tolist()))
    profiles = {}

    def index(df):
        oil = 1.0 - df["residual_oil_pct_of_initial"].to_numpy(dtype=float) / 100.0
        return 2.0 * (0.70 * oil + 0.30 * df["habitat_recovery_index"].to_numpy(dtype=float)) - 1.0

    for r in candidates:
        df = traj(scenario, r.treatment, days)
        profiles[r.treatment] = np.interp(time, df["survey_day"].to_numpy(dtype=float), index(df))
    df = traj(scenario, "no_cleanup", days)
    profiles["no_cleanup"] = np.interp(time, df["survey_day"].to_numpy(dtype=float), index(df))
    return time, profiles, horizon


def make_recovery_chart(scenario: Scenario, results: list):
    time, profiles, horizon = recovery_profiles(scenario, results)
    fig, ax = C.themed_fig((9, 5.2))
    for i, (key, values) in enumerate(profiles.items()):
        label = "No cleanup" if key == "no_cleanup" else _name(key)
        colour = T.NEUTRAL if key == "no_cleanup" else T.SERIES_COLOURS[i % len(T.SERIES_COLOURS)]
        ax.plot(time, values, lw=2.0, color=colour, ls=":" if key == "no_cleanup" else "--", label=label)
    ax.axhline(0.60, color=T.NEUTRAL, ls="-.", lw=0.9)
    ax.text(horizon * 0.02, 0.63, "80% planning endpoint (assumed)", fontsize=8, color=C.text_colour())
    ax.axhline(0, color=T.NEUTRAL, lw=1.2)
    ax.set_xlim(0, horizon)
    ax.set_ylim(-0.8, 1.15)
    ax.set_xlabel("Time since intervention (days)")
    ax.set_ylabel("Process-model recovery index (illustrative)")
    ax.set_title("ILLUSTRATIVE ONLY: process-model trajectories, no interval shown")
    ax.grid(alpha=.2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


def make_process_chart(df: pd.DataFrame):
    fig, ax = C.themed_fig((9, 4.6))
    ax.plot(df["survey_day"], df["surface_oil_mass_kg"], color=T.OKABE_ITO["blue"], lw=2.2, label="Surface oil")
    ax.plot(df["survey_day"], df["subsurface_oil_mass_kg"], color=T.OKABE_ITO["reddish_purple"], lw=2.2, label="Subsurface oil")
    ax.plot(df["survey_day"], df["residual_oil_kg"], color=T.OKABE_ITO["vermillion"], lw=2.0, label="Total residual oil")
    ax2 = ax.twinx()
    ax2.plot(df["survey_day"], df["habitat_recovery_index"] * 100, color=T.OKABE_ITO["bluish_green"], lw=2.2, ls="--", label="Habitat recovery index")
    ax.set_xlabel("Days since treatment")
    ax.set_ylabel("Oil mass (kg)")
    ax2.set_ylabel("Habitat recovery index (%)")
    ax.set_title("Illustrative oil and habitat trajectory (assumed rates)")
    ax.grid(alpha=.2)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", frameon=False)
    C.style_axes(fig, ax, ax2)
    fig.tight_layout()
    return fig


def _bar_chart(frame: pd.DataFrame, xcol: str, xlabel: str, title: str):
    colours = frame["Feasibility"].map({"eligible": T.OKABE_ITO["bluish_green"], "conditional": T.OKABE_ITO["orange"],
                                        "ineligible": T.NEUTRAL}).fillna(T.NEUTRAL)
    fig, ax = C.themed_fig((8, 5))
    bars = ax.barh(frame["Treatment"], frame[xcol], color=colours)
    for b, f in zip(bars, frame["Feasibility"]):
        if f == "ineligible":
            b.set_hatch("//")
        elif f == "conditional":
            b.set_hatch("..")
    ax.axvline(0, color=T.NEUTRAL, lw=1.2)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def make_ranking_chart(results: list):
    frame = pd.DataFrame([{"Treatment": _name(r.treatment), "Score": r.utility, "Feasibility": r.feasibility} for r in results]).sort_values("Score")
    return _bar_chart(frame, "Score", "Assumed ecological score, 0 to 10 (ineligible options score 0). Solid = eligible, dots = conditional, stripes = ineligible",
                      "Rule screening ordered by an ASSUMED ecological score (not effectiveness)")


def make_endpoint_chart(scenario: Scenario, results: list):
    frame = pd.DataFrame([{"Treatment": _name(r.treatment), "Months": estimate_endpoint(scenario, r)["months"], "Feasibility": r.feasibility}
                          for r in results]).sort_values("Months")
    return _bar_chart(frame, "Months", "Rough months to an 80% planning endpoint (product of ASSUMED factors, no interval)",
                      "Illustrative only: time to endpoint")


def make_tradeoff_chart(results: list):
    frame = pd.DataFrame([{"Treatment": _name(r.treatment), "Eco": r.ecological_suitability, "Feasibility": r.feasibility} for r in results])
    fig, ax = C.themed_fig((8, 4.4))
    colours = frame["Feasibility"].map({"eligible": T.OKABE_ITO["bluish_green"], "conditional": T.OKABE_ITO["orange"], "ineligible": T.NEUTRAL})
    ax.barh(frame["Treatment"], frame["Eco"], color=colours)
    ax.axvline(0, color=T.NEUTRAL, lw=1.2)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Assumed ecological score (higher means less disturbance)")
    ax.set_title("Ecological score by option (assumed, colour = rule tier)")
    fig.tight_layout()
    return fig


def make_constraint_chart(scenario: Scenario):
    ordinal = {"low": 1, "moderate": 2, "high": 3, "very_high": 4, "good": 1, "restricted": 3}
    frame = pd.DataFrame({
        "Constraint": ["Ecological sensitivity", "Wave exposure", "Access limitation", "Oil coverage", "Penetration depth", "Waste handling"],
        "v": [ordinal.get(scenario.shoreline_sensitivity, 2), ordinal.get(scenario.wave_exposure, 2), ordinal.get(scenario.accessibility, 2),
              scenario.oil_coverage / 25.0, min(scenario.penetration_depth_cm / 2.5, 4),
              {"manageable": 1, "moderate": 2, "difficult": 3}.get(scenario.waste_handling, 2)]}).sort_values("v")
    fig, ax = C.themed_fig((8, 4.2))
    ax.barh(frame["Constraint"], frame["v"], color=T.OKABE_ITO["blue"])
    ax.set_xlim(0, 4.2)
    ax.set_xticks([1, 2, 3, 4], ["Low", "Moderate", "High", "Very high"])
    ax.axvline(0, color=T.NEUTRAL, lw=1.2)
    ax.set_title("Environmental and operational constraint profile")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    return fig


def _run_pipeline(scenario: Scenario):
    oiling = None  # derived by the pipeline from oil coverage (ASSUMED breaks, stated in its report)
    report, err = P.decision_for_scenario(P.scenario_items(scenario), oiling, scenario.oil_category, scenario.season)
    return (E.report_view(report) if report is not None else None), err


def render_scenario_view() -> None:
    with st.sidebar:
        st.header("Scenario screening inputs")
        preset_options = ["Custom scenario"] + [preset_name(i, s) for i, s in enumerate(SCENARIO_LIBRARY)]
        selected = st.selectbox("Starting point", preset_options)
        preset = None if selected == "Custom scenario" else SCENARIO_LIBRARY[preset_options.index(selected) - 1]
        st.caption("Change any input below. The analysis runs only when you press the button.")
    scenario = build_scenario(preset)
    run = st.sidebar.button("Run scenario analysis", type="primary", width="stretch")
    C.scope_panel("scenario")
    st.markdown(T.grade_html("illustrative", "Illustrative: rule screening and assumed process model"), unsafe_allow_html=True)
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if run:
        with st.spinner("Scoring treatment options for this scenario..."):
            st.session_state.analysis = (scenario, load_model().rank_treatments(scenario))
    if st.session_state.analysis is None:
        st.write("Choose a preset or custom inputs in the sidebar, then select Run scenario analysis.")
        st.caption("You will see: what the evidence supports for the scenario, the rule screening, illustrative process-model curves, "
                   "and the checks behind them.")
        return

    scen, results = st.session_state.analysis
    top = results[0]
    view, err = _run_pipeline(scen)

    st.subheader("What the evidence supports for this scenario")
    C.answer_card(view, f"{_name(scen.shoreline_type)} | {scen.oil_category} oil | {scen.oil_coverage:.0f}% coverage")
    if err:
        st.error(f"The decision pipeline could not run ({err}).")
    C.render_pipeline_section(view, "scenario")

    st.subheader("Legacy rule screening")
    st.caption(T.LABELS["rule_screen_text"])
    st.markdown(f"**{_name(top.treatment)}** is first in the rule-screening order for this scenario. It is **{top.feasibility}** and has an "
                f"assumed ecological score of **{top.ecological_suitability:.1f} of 10**. {top.reason}")
    cols = st.columns(4)
    cols[0].metric("First in rule-screening order", _name(top.treatment), border=True)
    cols[1].metric("Rule tier", top.feasibility.title(), border=True)
    cols[2].metric("Assumed ecological score", f"{top.ecological_suitability:.1f} / 10", border=True,
                   help="An assumed score for how little the method disturbs the habitat. It is not an estimate of effectiveness.")
    with cols[3]:
        with st.container(border=True):
            st.caption("Evidence tier of this ordering")
            st.markdown(T.grade_html("illustrative", "Illustrative"), unsafe_allow_html=True)
            st.caption("No outcome data behind it.")
    st.write("Key drivers: " + get_key_drivers(scen).replace("; ", ", "))

    endpoint = estimate_endpoint(scen, top)
    st.subheader("Rough time to endpoint (illustrative)")
    st.metric("About", f"{endpoint['months']:.0f} months", border=True,
              help="Multiplies ASSUMED factors (shoreline type, treatment, oil, access, exposure). It carries no interval; read it as an order of magnitude.")
    st.caption(endpoint["definition"] + " Assumed multipliers, no interval.")

    st.subheader("Process-model curves beside the field evidence")
    left, right = st.columns(2)
    with left:
        st.markdown(f":gray-badge[:material/draw: Illustrative] **{ILLUSTRATIVE}**")
        C.show_fig(make_recovery_chart(scen, results))
    with right:
        st.markdown("**Field evidence for the same scenario**")
        if view is not None and E.available_outcomes(view.options):
            C.render_interval_comparison(view, "scenario_side")
        else:
            st.info("The decision pipeline has no field-evidence forecast for this scenario (rules and literature only). "
                    "The process-model curves on the left are the only forecast-like output here and they are illustrative.",
                    icon=":material/info:")

    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], required=True, key="scenario_section")
    _section(section, scen, results, top, endpoint)


def _section(section: str, scen: Scenario, results: list, top, endpoint: dict) -> None:
    if section == "Treatment ranking":
        left, right = st.columns([1.35, 1])
        with left:
            C.show_fig(make_ranking_chart(results))
        with right:
            C.show_fig(make_tradeoff_chart(results))
        st.dataframe(pd.DataFrame([{"Rule-screening order": i, "Treatment": _name(r.treatment), "Rule tier": r.feasibility.title(),
                                    T.LABELS["assumed_score"]: round(r.ecological_suitability, 2)} for i, r in enumerate(results, 1)]),
                     hide_index=True, width="stretch")
        st.caption("Order: rule tier first (eligible, conditional, ineligible), then an ASSUMED ecological score (lower disturbance first). "
                   "This is not an effectiveness ranking. The suitability model trained on rule-generated labels is outside the decision path.")
    elif section == "Process model":
        st.markdown(f":gray-badge[:material/draw: Illustrative] **{ILLUSTRATIVE}**")
        st.caption("Oil moves across the shore by tidal and swash dispersion with retention in vegetation and soil, and is lost by evaporation, "
                   "infiltration and biodegradation. Parameters marked ASSUMED in the Validation section are not calibrated.")
        df = traj(scen, top.treatment)
        C.show_fig(make_transect_figure(scen, top.treatment))
        C.show_fig(make_process_chart(df))
        last = df.iloc[-1]
        c = st.columns(4)
        c[0].metric("Treatment simulated", _name(top.treatment), border=True)
        c[1].metric("Final residual oil", f"{last['residual_oil_kg']:.1f} kg", border=True)
        c[2].metric("Habitat recovery index", f"{last['habitat_recovery_index']:.0%}", border=True)
        c[3].metric("Latest endpoint state", str(last["endpoint_decision"]), border=True)
        st.dataframe(df[["survey_date", "survey_day", "surface_oil_mass_kg", "subsurface_oil_mass_kg", "residual_oil_kg",
                         "residual_oil_pct_of_initial", "habitat_recovery_index", "endpoint_decision", "continued_monitoring"]],
                     hide_index=True, width="stretch")
        st.download_button("Download selected process trajectory CSV", data=df.to_csv(index=False),
                           file_name="selected_scenario_process_trajectory.csv", mime="text/csv")
        lhs = load_lhs_dataset()
        st.subheader("Synthetic LHS SCAT dataset")
        st.write(f"Generated dataset: {lhs['segment_id'].nunique()} segments and {len(lhs)} repeat-survey observations.")
        st.download_button("Download LHS SCAT process dataset", data=lhs.to_csv(index=False),
                           file_name="lhs_scat_process_dataset.csv", mime="text/csv")
        st.caption("Replace the synthetic file with real SCAT repeat-survey data before calibrating rates.")
    elif section == "Method test (synthetic data)":
        _method_test()
    elif section == "NOAA cross-check":
        st.caption("Crosswalk based on manual_shore_assess_aug2013.pdf (PDF page numbers). An audit aid, not a substitute for an approved "
                   "Shoreline Treatment Recommendation.")
        cw = pd.DataFrame(NOAA_TREATMENT_CROSSWALK)
        cw["treatment"] = cw["treatment"].str.replace("_", " ").str.title()
        st.dataframe(cw, hide_index=True, width="stretch")
    elif section == "Validation":
        render_validation_tab()
    elif section == "Constraints and endpoint":
        C.show_fig(make_constraint_chart(scen))
        for c in environmental_constraints(scen, top):
            st.markdown(f"- {c}")
        st.write(f"The first option in the rule-screening order reaches a rough 80% planning endpoint in about {endpoint['months']:.0f} months "
                 "(assumed multipliers, no interval). This is not a regulatory closure date.")
        C.show_fig(make_endpoint_chart(scen, results))
        st.caption("Recommended monitoring: repeat shoreline observations, document residual oiling, track habitat recovery, and confirm "
                   "endpoint criteria with the incident management team and regulators.")
    elif section == "Treatment details":
        for i, r in enumerate(results, 1):
            with st.expander(f"{i}. {_name(r.treatment)} | {r.feasibility.title()}", expanded=i == 1):
                eco = load_model().ecological_score_explanation(r.treatment, scen)
                st.metric("Assumed ecological score", f"{r.ecological_suitability:.2f} / 10", border=True)
                st.write(r.reason)
                st.markdown(f"**Basis of the assumed score:** {eco['basis']}")
    else:
        st.dataframe(pd.DataFrame({"Input": [f.replace("_", " ").title() for f in scen.__dataclass_fields__],
                                   "Value": [str(v) for v in scen.__dict__.values()]}), hide_index=True, width="stretch")


def _method_test() -> None:
    benchmark = load_benchmark_results()
    st.markdown(T.grade_html("illustrative", "Method test on synthetic data, not evidence"), unsafe_allow_html=True)
    st.caption("Every model here was trained and scored on synthetic, rule-generated scenarios. Good scores show the models can copy the rules; "
               "they say nothing about real cleanup outcomes. The live screening keeps the rules as a hard gate.")
    if benchmark.empty:
        st.warning("comparison_report.csv was not found. Run run_benchmark.py to generate it.")
    else:
        labels = {"linear": "Linear regression", "svm": "SVM / SVR", "ann": "ANN / MLP", "rf": "Random Forest", "xgb": "XGBoost",
                  "gpr": "Gaussian Process", "fdt": "Fuzzy baseline"}
        s = benchmark.groupby("model", as_index=False).agg(Mean_MAE=("mae", "mean"), Mean_R2=("r2", "mean"))
        s["Model"] = s.pop("model").map(labels).fillna("Unknown")
        fig, axes = C.themed_fig((9, 3.6))
        fig.clf()
        a1, a2 = fig.subplots(1, 2)
        a1.bar(s["Model"], s["Mean_MAE"], color=T.OKABE_ITO["blue"])
        a1.set_title("Mean absolute error (lower is better)")
        a2.bar(s["Model"], s["Mean_R2"], color=T.OKABE_ITO["orange"])
        a2.axhline(0, color=T.NEUTRAL, lw=1.2)
        a2.set_title("Mean R2 (higher is better)")
        for a in (a1, a2):
            a.tick_params(axis="x", rotation=35)
        fig.tight_layout()
        C.show_fig(fig)
        st.dataframe(s[["Model", "Mean_MAE", "Mean_R2"]].round(3), hide_index=True, width="stretch")
    st.latex(r"\text{assumed score } E \text{ from treatment type, shoreline type and sensitivity (rules, not data)}")
