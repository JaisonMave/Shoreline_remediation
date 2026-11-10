from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.shoreline_remediation.scenario_runner import (  # noqa: E402
    SCENARIO_LIBRARY,
    get_key_drivers,
    get_uncertainty_breakdown,
    get_uncertainty_score,
)
from src.shoreline_remediation.noaa_crosswalk import NOAA_TREATMENT_CROSSWALK  # noqa: E402
from src.shoreline_remediation.process_model import generate_lhs_scats, simulate_selected_scenario  # noqa: E402
from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.decision_framework import HybridDecisionModel  # noqa: E402
from src.shoreline_remediation.validation_panel import make_transect_figure, render_validation_tab  # noqa: E402


st.set_page_config(
    page_title="Shoreline Remediation Decision Support",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f6f7f2; color: #24323a; font-family: "Segoe UI", sans-serif; }
    .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"] { color: #24323a; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #173f3f; }
    [data-testid="stSidebar"] { background: #173f3f; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #f5f3e8 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] > div { background: #f5f3e8 !important; color: #173f3f !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] input { color: #173f3f !important; }
    [data-testid="stSidebar"] .stButton button { color: #ffffff !important; background: #db8b3e !important; border: 0; }
    [data-testid="stAlert"] p { color: #24323a !important; }
    [data-testid="stDataFrame"] { background: #ffffff; }
    .hero { background: #173f3f; color: #f5f3e8; padding: 2rem 2.2rem; border-radius: 0 0 18px 18px; margin: -1rem -1rem 1.5rem -1rem; }
    .hero h1 { font-size: 2.25rem; margin: 0 0 .35rem 0; letter-spacing: 0; }
    .hero p { margin: 0; color: #c9ddd0; font-size: 1.05rem; }
    .metric-card { background: white; border: 1px solid #dce4db; border-radius: 10px; padding: 1rem; min-height: 110px; }
    .metric-label { color: #61716a; font-size: .82rem; text-transform: uppercase; letter-spacing: .04em; }
    .metric-value { color: #173f3f; font-size: 1.35rem; font-weight: 700; margin-top: .4rem; }
    .callout { background: #e7f0e6; border-left: 5px solid #db8b3e; border-radius: 8px; padding: 1rem 1.2rem; margin: .75rem 0 1rem 0; }
    .small-note { color: #61716a; font-size: .9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def style_figure(fig: plt.Figure) -> plt.Figure:
    fig.patch.set_facecolor("white")
    for axis in fig.axes:
        axis.set_facecolor("white")
        axis.tick_params(colors="#24323a", labelsize=9)
        axis.xaxis.label.set_color("#24323a")
        axis.yaxis.label.set_color("#24323a")
        axis.title.set_color("#173f3f")
        for label in axis.get_xticklabels() + axis.get_yticklabels():
            label.set_color("#24323a")
        legend = axis.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_color("#24323a")
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_edgecolor("#dce4db")
    return fig


@st.cache_resource
def load_model() -> HybridDecisionModel:
    return HybridDecisionModel()


@st.cache_data
def load_benchmark_results() -> pd.DataFrame:
    path = PROJECT_ROOT / "reports" / "comparison_report.csv"
    if not path.exists():
        return pd.DataFrame(columns=["model", "treatment", "mae", "r2"])
    return pd.read_csv(path)


@st.cache_data
def load_lhs_dataset() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "lhs_scat_process_dataset.csv"
    if path.exists():
        return pd.read_csv(path)
    return generate_lhs_scats(n_segments=100, seed=42)


def make_process_chart(process_data: pd.DataFrame) -> plt.Figure:
    fig, axis = plt.subplots(figsize=(11, 5.8))
    axis.plot(process_data["survey_day"], process_data["surface_oil_mass_kg"], color="#2862a0", lw=2.5, label="Surface oil")
    axis.plot(process_data["survey_day"], process_data["subsurface_oil_mass_kg"], color="#a35c9d", lw=2.5, label="Subsurface oil")
    axis.plot(process_data["survey_day"], process_data["residual_oil_kg"], color="#e31b23", lw=2.2, label="Total residual oil")
    recovery_axis = axis.twinx()
    recovery_axis.plot(process_data["survey_day"], process_data["habitat_recovery_index"] * 100, color="#2d7d6d", lw=2.5, ls="--", label="Habitat recovery index")
    axis.set_xlabel("Days since treatment")
    axis.set_ylabel("Oil mass (kg)")
    recovery_axis.set_ylabel("Habitat recovery index (%)")
    axis.set_title("First-order process-informed oil and habitat trajectory")
    axis.grid(alpha=.2)
    lines, labels = axis.get_legend_handles_labels()
    lines2, labels2 = recovery_axis.get_legend_handles_labels()
    axis.legend(lines + lines2, labels + labels2, loc="upper right", frameon=False)
    return style_figure(fig)


def make_benchmark_chart(benchmark: pd.DataFrame) -> plt.Figure:
    summary = benchmark.groupby("model", as_index=False).agg(mean_mae=("mae", "mean"), mean_r2=("r2", "mean"))
    model_labels = {"linear": "Linear", "svm": "SVM", "ann": "ANN", "rf": "Random Forest", "xgb": "XGBoost", "gpr": "Gaussian Process", "fdt": "Fuzzy baseline"}
    summary["label"] = summary["model"].map(model_labels).fillna(summary["model"].str.upper())
    palette = ["#176b87", "#db8b3e", "#7a6aa6", "#2d7d6d", "#a84c4c", "#6d8ca0", "#9bb8a8"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    axes[0].bar(summary["label"], summary["mean_mae"], color=palette[:len(summary)])
    axes[0].set_title("Mean absolute error")
    axes[0].set_ylabel("Lower is better")
    axes[1].bar(summary["label"], summary["mean_r2"], color=palette[:len(summary)])
    axes[1].set_title("Mean R² score")
    axes[1].set_ylabel("Higher is better")
    for axis in axes:
        axis.tick_params(axis="x", rotation=35)
        axis.grid(axis="y", alpha=.2)
        axis.set_axisbelow(True)
        for spine in ["top", "right", "left"]:
            axis.spines[spine].set_visible(False)
    fig.tight_layout()
    return style_figure(fig)


def ecological_explanation(model: HybridDecisionModel, treatment: str, scenario: Scenario) -> dict:
    return model.ecological_score_explanation(treatment, scenario)


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
        oil_category = st.selectbox("Oil category", ["light", "medium", "heavy", "solid"], index=selectbox_value(["light", "medium", "heavy", "solid"], source.oil_category), format_func=str.title)
        oil_coverage = st.slider("Oil coverage (%)", 0, 100, int(source.oil_coverage), 1)
        oil_thickness = st.slider("Oil thickness (mm)", 0.0, 30.0, float(source.oil_thickness), 0.5)
        penetration_depth_cm = st.slider("Penetration depth (cm)", 0.0, 30.0, float(source.penetration_depth_cm), 0.5)
        wave_exposure = st.selectbox("Wave exposure", ["low", "moderate", "high", "very_high"], index=selectbox_value(["low", "moderate", "high", "very_high"], source.wave_exposure), format_func=lambda value: value.replace("_", " ").title())
        tidal_range = st.selectbox("Tidal range", ["low", "moderate", "high"], index=selectbox_value(["low", "moderate", "high"], source.tidal_range), format_func=str.title)
        temperature_c = st.slider("Temperature (°C)", -5.0, 35.0, float(source.temperature_c), 0.5)
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


def metric_card(label: str, value: str) -> str:
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>'


def make_ranking_chart(results: list) -> plt.Figure:
    frame = pd.DataFrame([
        {"Treatment": result.treatment.replace("_", " ").title(), "Utility": result.utility, "Feasibility": result.feasibility}
        for result in results
    ]).sort_values("Utility")
    colors = frame["Feasibility"].map({"eligible": "#2d7d6d", "conditional": "#db8b3e", "ineligible": "#a84c4c"}).fillna("#61716a")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(frame["Treatment"], frame["Utility"], color=colors)
    ax.set_xlabel("Decision utility (higher is better)")
    ax.set_xlim(0, max(10, frame["Utility"].max() + 1))
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return style_figure(fig)


def make_score_chart(top_results: list) -> plt.Figure:
    frame = pd.DataFrame([
        {"Treatment": result.treatment.replace("_", " ").title(), "Suitability": result.suitability, "Ecological fit": result.ecological_suitability, "Confidence": result.confidence * 10}
        for result in top_results
    ]).set_index("Treatment")
    fig, ax = plt.subplots(figsize=(10, 5))
    frame.plot(kind="bar", ax=ax, color=["#2d7d6d", "#db8b3e", "#6d8ca0"])
    ax.set_ylim(0, 10)
    ax.set_ylabel("Score (0-10)")
    ax.grid(axis="y", alpha=.2)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right")
    plt.xticks(rotation=25, ha="right")
    fig.tight_layout()
    return style_figure(fig)


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
        "definition": "Indicative time to 80% of the modeled recovery target, assuming treatment is implemented and monitoring confirms progress.",
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
        constraints.append("The leading treatment is conditional under FAST screening: confirm permits, method controls, and a contingency option before execution.")
    if not constraints:
        constraints.append("No major constraint flags were triggered by the current inputs; standard spill-response controls and monitoring still apply.")
    return constraints


def recovery_profiles(scenario: Scenario, results: list) -> tuple[np.ndarray, dict[str, np.ndarray], int]:
    candidate_results = [result for result in results if result.feasibility != "ineligible"][:5]
    if not candidate_results:
        candidate_results = results[:5]
    endpoint_days = [estimate_endpoint(scenario, result)["days"] for result in candidate_results]
    horizon = max(365, int(max(endpoint_days, default=365) * 1.25))
    time = np.linspace(0, horizon, 500)
    simulation_days = sorted(set(np.linspace(0, horizon, 80, dtype=int).tolist()))
    profiles = {"conditions_absence": np.full_like(time, 0.92, dtype=float)}

    # The ML ranking selects the treatment candidates; the DHI-informed process
    # model supplies the time-dependent recovery response for each candidate.
    for result in candidate_results:
        process_data = simulate_selected_scenario(
            scenario,
            result.treatment,
            survey_days=simulation_days,
        )
        oil_recovery = 1.0 - process_data["residual_oil_pct_of_initial"].to_numpy(dtype=float) / 100.0
        habitat_recovery = process_data["habitat_recovery_index"].to_numpy(dtype=float)
        recovery_index = 0.70 * oil_recovery + 0.30 * habitat_recovery
        profiles[result.treatment] = np.interp(
            time,
            process_data["survey_day"].to_numpy(dtype=float),
            (2.0 * recovery_index) - 1.0,
        )

    no_cleanup = simulate_selected_scenario(scenario, "no_cleanup", survey_days=simulation_days)
    profiles["no_cleanup"] = np.interp(
        time,
        no_cleanup["survey_day"].to_numpy(dtype=float),
        (2.0 * (0.70 * (1.0 - no_cleanup["residual_oil_pct_of_initial"].to_numpy(dtype=float) / 100.0) + 0.30 * no_cleanup["habitat_recovery_index"].to_numpy(dtype=float))) - 1.0,
    )
    return time, profiles, horizon


def make_recovery_chart(scenario: Scenario, results: list) -> plt.Figure:
    time, profiles, horizon = recovery_profiles(scenario, results)
    fig, ax = plt.subplots(figsize=(11, 6.2))
    colors = ["#2862a0", "#a35c9d", "#65a823", "#db8b3e", "#176b87"]
    ax.plot(time, profiles.pop("conditions_absence"), lw=2.4, color="#f28e2b", label="Conditions in the Absence of a Spill")
    treatment_keys = list(profiles.keys())
    for index, treatment in enumerate(treatment_keys):
        label = "No Cleanup" if treatment == "no_cleanup" else treatment.replace("_", " ").title()
        line_color = "#e31b23" if treatment == "no_cleanup" else colors[index % len(colors)]
        ax.plot(time, profiles[treatment], lw=2.1, color=line_color, label=label)
        if treatment != "no_cleanup":
            matching = next((result for result in results if result.treatment == treatment), None)
            confidence = matching.confidence if matching is not None else 0.5
            band = 0.04 + (1.0 - confidence) * 0.16
            ax.fill_between(
                time,
                profiles[treatment] - band,
                profiles[treatment] + band,
                color=line_color,
                alpha=0.10,
                linewidth=0,
            )
    ax.axhline(0.60, color="#555", ls="--", lw=0.9, label="80% planning endpoint")
    ax.text(horizon * 0.02, 0.63, "80% planning endpoint", fontsize=8, color="#555")
    ax.axhline(0, color="#555", lw=0.8)
    ax.set_xlim(0, horizon)
    ax.set_ylim(-0.8, 1.15)
    ax.set_xlabel("Time since intervention (days)")
    ax.set_ylabel("Predicted impact / recovery index")
    ax.set_title("ML-ranked treatments with DHI-informed recovery predictions")
    ax.grid(alpha=.2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    return style_figure(fig)


def make_endpoint_chart(scenario: Scenario, results: list) -> plt.Figure:
    frame = pd.DataFrame([
        {"Treatment": result.treatment.replace("_", " ").title(), "Days": estimate_endpoint(scenario, result)["days"], "Feasibility": result.feasibility}
        for result in results
    ]).sort_values("Days", ascending=True)
    colors = frame["Feasibility"].map({"eligible": "#2d7d6d", "conditional": "#db8b3e", "ineligible": "#a84c4c"})
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(frame["Treatment"], frame["Days"], color=colors)
    ax.set_xlabel("Indicative time to 80% modeled recovery endpoint (days)")
    ax.set_title("Expected time to endpoint by treatment")
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return style_figure(fig)


def make_tradeoff_chart(results: list) -> plt.Figure:
    frame = pd.DataFrame([
        {"Treatment": result.treatment.replace("_", " ").title(), "Suitability": result.suitability, "Ecological fit": result.ecological_suitability, "Feasibility": result.feasibility, "Utility": result.utility}
        for result in results
    ])
    colors = frame["Feasibility"].map({"eligible": "#2d7d6d", "conditional": "#db8b3e", "ineligible": "#a84c4c"})
    sizes = 50 + frame["Utility"] * 35
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(frame["Suitability"], frame["Ecological fit"], s=sizes, c=colors, alpha=.85, edgecolor="white", linewidth=.8)
    for _, row in frame.iterrows():
        ax.annotate(row["Treatment"], (row["Suitability"], row["Ecological fit"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Operational / ML suitability")
    ax.set_ylabel("Ecological fit")
    ax.set_title("Treatment trade-off space")
    ax.grid(alpha=.2)
    fig.tight_layout()
    return style_figure(fig)


def make_constraint_chart(scenario: Scenario) -> plt.Figure:
    ordinal = {"low": 1, "moderate": 2, "high": 3, "very_high": 4, "good": 1, "restricted": 3}
    frame = pd.DataFrame({
        "Constraint": ["Ecological sensitivity", "Wave exposure", "Access limitation", "Oil coverage", "Penetration depth", "Waste handling"],
        "Relative intensity": [
            ordinal.get(scenario.shoreline_sensitivity, 2),
            ordinal.get(scenario.wave_exposure, 2),
            ordinal.get(scenario.accessibility, 2),
            scenario.oil_coverage / 25.0,
            min(scenario.penetration_depth_cm / 2.5, 4),
            {"manageable": 1, "moderate": 2, "difficult": 3}.get(scenario.waste_handling, 2),
        ],
    }).sort_values("Relative intensity")
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    colors = ["#9bb8a8" if value < 2 else "#db8b3e" if value < 3 else "#a84c4c" for value in frame["Relative intensity"]]
    ax.barh(frame["Constraint"], frame["Relative intensity"], color=colors)
    ax.set_xlim(0, 4.2)
    ax.set_xlabel("Relative constraint intensity (1 = low, 4 = high)")
    ax.set_title("Environmental and operational constraint profile")
    ax.set_xticks([1, 2, 3, 4], ["Low", "Moderate", "High", "Very high"])
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return fig


def main() -> None:
    st.markdown('<div class="hero"><h1>Shoreline Remediation Decision Support</h1><p>Select one shoreline scenario, run the analysis, and compare treatment options in plain language.</p></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("Choose a scenario")
        preset_options = ["Custom scenario"] + [preset_name(index, scenario) for index, scenario in enumerate(SCENARIO_LIBRARY)]
        selected = st.selectbox("Starting point", preset_options)
        preset = None if selected == "Custom scenario" else SCENARIO_LIBRARY[preset_options.index(selected) - 1]
        st.caption("Change any input below. The analysis runs only when you press the button.")

    scenario = build_scenario(preset)
    run_analysis = st.sidebar.button("Run scenario analysis", type="primary", use_container_width=True)

    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if run_analysis:
        with st.spinner("Scoring treatment options for this scenario..."):
            results = load_model().rank_treatments(scenario)
        st.session_state.analysis = (scenario, results)

    if st.session_state.analysis is None:
        st.info("Choose a preset or custom inputs in the sidebar, then select Run scenario analysis.")
        st.subheader("What you will see")
        st.write("A ranked recommendation, feasibility screening, uncertainty signal, key decision drivers, and clear treatment-by-treatment score explanations.")
        return

    analyzed_scenario, results = st.session_state.analysis
    top = results[0]
    uncertainty = get_uncertainty_breakdown(analyzed_scenario, results)
    drivers = get_key_drivers(analyzed_scenario)
    benchmark = load_benchmark_results()

    st.subheader("Recommendation")
    st.markdown(f'<div class="callout"><strong>{top.treatment.replace("_", " ").title()}</strong> is the leading option for this scenario. It is <strong>{top.feasibility}</strong> with a utility score of <strong>{top.utility:.2f}</strong>. {top.reason}</div>', unsafe_allow_html=True)

    metric_columns = st.columns(5)
    metrics = [
        ("Top treatment", top.treatment.replace("_", " ").title()),
        ("Feasibility", top.feasibility.title()),
        ("Utility", f"{top.utility:.2f} / 10"),
        ("Confidence", f"{uncertainty['confidence']:.0%}"),
        ("Uncertainty", f"{uncertainty['category']} ({uncertainty['score']:.2f})"),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        column.markdown(metric_card(label, value), unsafe_allow_html=True)

    st.subheader("Key decision drivers")
    st.write(drivers.replace("; ", " • "))
    st.info(
        f"**How to read uncertainty:** {uncertainty['category']}. "
        f"This is a screening signal, not a probability of correctness. "
        f"{uncertainty['interpretation']} Treatment utility gap: {uncertainty['utility_gap']:.2f}; "
        f"scenario complexity: {uncertainty['scenario_complexity']:.2f}; "
        f"top-option model confidence: {uncertainty['model_confidence']:.0%}.",
        icon=":material/info:",
    )

    endpoint = estimate_endpoint(analyzed_scenario, top)
    constraints = environmental_constraints(analyzed_scenario, top)
    st.subheader("Expected endpoint")
    endpoint_columns = st.columns(4)
    endpoint_metrics = [
        ("Modeled endpoint", "80% recovery"),
        ("Indicative duration", f"{endpoint['days']} days"),
        ("Approximate duration", f"{endpoint['months']} months"),
        ("Interpretation", "Monitoring-based target"),
    ]
    for column, (label, value) in zip(endpoint_columns, endpoint_metrics):
        column.markdown(metric_card(label, value), unsafe_allow_html=True)
    st.caption(endpoint["definition"])

    st.subheader("Scientific result plots")
    st.caption("The recovery plot uses the ML-ranked top treatments as inputs to the cross-shore transport model (advection-dispersion-reaction in shoreline sediment). Shaded bands reflect the decision confidence signal; all curves remain screening predictions until calibrated with repeat SCAT observations.")
    st.markdown("#### Impact and recovery trajectories")
    st.pyplot(make_recovery_chart(analyzed_scenario, results), use_container_width=True)
    trajectory_rows = []
    for ranked_result in [result for result in results if result.feasibility != "ineligible"][:5]:
        trajectory = simulate_selected_scenario(analyzed_scenario, ranked_result.treatment)
        trajectory_rows.append({
            "Treatment": ranked_result.treatment.replace("_", " ").title(),
            "Utility": round(ranked_result.utility, 2),
            "Process residual oil (kg)": round(float(trajectory["residual_oil_kg"].iloc[-1]), 1),
            "Process recovery index": f"{float(trajectory['habitat_recovery_index'].iloc[-1]):.0%}",
            "Decision confidence": f"{ranked_result.confidence:.0%}",
        })
    st.dataframe(pd.DataFrame(trajectory_rows), hide_index=True, use_container_width=True)
    scientific_left, scientific_right = st.columns(2)
    with scientific_left:
        st.markdown("#### Time to recovery endpoint")
        st.pyplot(make_endpoint_chart(analyzed_scenario, results), use_container_width=True)
    with scientific_right:
        st.markdown("#### Suitability versus ecological fit")
        st.pyplot(make_tradeoff_chart(results), use_container_width=True)
    st.markdown("#### Environmental and operational constraint profile")
    st.pyplot(make_constraint_chart(analyzed_scenario), use_container_width=True)
    st.caption("Interpretation: the recovery chart shows process-model predictions for the ML-ranked treatments; the endpoint chart compares indicative time to 80% recovery; the trade-off chart compares operational suitability with ecological fit; the constraint chart summarizes relative planning constraints.")

    ranking_tab, process_tab, model_tab, noaa_tab, validation_tab, constraints_tab, detail_tab, inputs_tab = st.tabs([
        "Treatment ranking", "Process model", "ML model evidence", "NOAA cross-check", "Validation", "Constraints & endpoint", "Treatment details", "Scenario inputs"
    ])
    with ranking_tab:
        left, right = st.columns([1.35, 1])
        with left:
            st.caption("Overall utility ranking. Green = eligible, amber = conditional, red = ineligible.")
            st.pyplot(make_ranking_chart(results), use_container_width=True)
        with right:
            st.caption("Top options: suitability, ecological fit, and confidence.")
            st.pyplot(make_score_chart(results[:6]), use_container_width=True)
        ranking_frame = pd.DataFrame([
            {
                "Rank": index,
                "Treatment": result.treatment.replace("_", " ").title(),
                "Feasibility": result.feasibility.title(),
                "Utility": round(result.utility, 2),
                "Suitability": round(result.suitability, 2),
                "Ecological fit": round(result.ecological_suitability, 2),
                "Confidence": f"{result.confidence:.0%}",
            }
            for index, result in enumerate(results, start=1)
        ])
        st.dataframe(ranking_frame, hide_index=True, use_container_width=True)

    with process_tab:
        st.subheader("Cross-shore transport simulation")
        st.caption("Screening model: oil moves across the shore by tidal and swash dispersion with retention in vegetation and soil, and is lost by evaporation, infiltration and biodegradation (oxygen- and nutrient-limited). Marsh interiors are oxygen-poor, so oil persists there. Parameters marked ASSUMED in the Validation tab are not yet calibrated.")
        process_data = simulate_selected_scenario(analyzed_scenario, top.treatment)
        st.pyplot(make_transect_figure(analyzed_scenario, top.treatment), use_container_width=True)
        st.pyplot(make_process_chart(process_data), use_container_width=True)
        process_columns = st.columns(4)
        final_row = process_data.iloc[-1]
        process_metrics = [
            ("Treatment simulated", top.treatment.replace("_", " ").title()),
            ("Final residual oil", f"{final_row['residual_oil_kg']:.1f} kg"),
            ("Habitat recovery index", f"{final_row['habitat_recovery_index']:.0%}"),
            ("Latest endpoint state", final_row["endpoint_decision"]),
        ]
        for column, (label, value) in zip(process_columns, process_metrics):
            column.markdown(metric_card(label, value), unsafe_allow_html=True)
        st.dataframe(process_data[[
            "survey_date", "survey_day", "surface_oil_mass_kg", "subsurface_oil_mass_kg",
            "residual_oil_kg", "residual_oil_pct_of_initial", "habitat_recovery_index",
            "endpoint_decision", "continued_monitoring",
        ]], hide_index=True, use_container_width=True)
        st.download_button(
            "Download selected process trajectory CSV",
            data=process_data.to_csv(index=False),
            file_name="selected_scenario_process_trajectory.csv",
            mime="text/csv",
        )
        lhs_data = load_lhs_dataset()
        st.subheader("Synthetic LHS SCAT dataset")
        st.write(f"Generated dataset: {lhs_data['segment_id'].nunique()} segments and {len(lhs_data)} repeat-survey observations.")
        st.download_button(
            "Download LHS SCAT process dataset",
            data=lhs_data.to_csv(index=False),
            file_name="lhs_scat_process_dataset.csv",
            mime="text/csv",
        )
        st.info("Replace the synthetic LHS file with real SCAT/SOS/STR repeat-survey data before calibrating rates or using endpoint results operationally.")

    with model_tab:
        st.subheader("Benchmark evidence")
        st.info("The live dashboard keeps FAST feasibility as a hard gate and uses the current Gaussian Process suitability path for the treatments supported by the decision framework. These benchmark results are shown as evidence, not silently blended into the recommendation.")
        if benchmark.empty:
            st.warning("comparison_report.csv was not found. Run run_benchmark.py to generate model comparison results.")
        else:
            summary = benchmark.groupby("model", as_index=False).agg(
                Mean_MAE=("mae", "mean"), Mean_R2=("r2", "mean")
            )
            model_labels = {"linear": "Linear regression", "svm": "SVM / SVR", "ann": "ANN / MLP", "rf": "Random Forest", "xgb": "XGBoost", "gpr": "Gaussian Process", "fdt": "Fuzzy baseline"}
            summary["Model"] = summary.pop("model").map(model_labels).fillna("Unknown")
            summary["Mean_MAE"] = summary["Mean_MAE"].round(3)
            summary["Mean_R2"] = summary["Mean_R2"].round(3)
            st.pyplot(make_benchmark_chart(benchmark), use_container_width=True)
            st.dataframe(summary[["Model", "Mean_MAE", "Mean_R2"]], hide_index=True, use_container_width=True)
            st.caption("These metrics are calculated from the current synthetic benchmark dataset. They should not be treated as production validation until real expert-labelled or incident data are used.")
            st.subheader("Why the models are not blended yet")
            best_model = summary.sort_values("Mean_R2", ascending=False).iloc[0]["Model"]
            st.write(f"The current synthetic benchmark ranks {best_model} highest by mean R². The live suitability path remains Gaussian Process based for a subset of treatments because the benchmark models have not yet been trained and calibrated on the same real incident-labelled dataset. A defensible ensemble should be introduced only after that validation step.")
        st.subheader("How ecological suitability is calculated")
        st.write("Ecological suitability is currently a transparent rule-based score from 0 to 10. It is separate from the ML suitability score and reflects habitat disturbance and recovery compatibility.")
        st.latex(r"U = 0.6 \times F \times S + 0.4 \times E")
        st.write("Here, $U$ is utility, $F$ is the FAST feasibility weight, $S$ is ML suitability, and $E$ is ecological suitability. Ecological rules currently use treatment type, shoreline type, and shoreline sensitivity.")
        ecological_rules = pd.DataFrame([
            {"Treatment group": "Natural attenuation", "Typical E score": "8.5 in high-sensitivity marsh/mudflat; otherwise 7.0", "Reason": "Low disturbance, but NOAA requires natural-removal evidence and monitoring"},
            {"Treatment group": "Bioremediation", "Typical E score": "6.0 pending nutrient/oxygen and effectiveness evidence", "Reason": "Potentially low physical disturbance, but evidence and treatment controls are required"},
            {"Treatment group": "Manual / vacuum / mechanical removal", "Typical E score": "3.0 in marsh/mudflat/tundra; otherwise 6.0", "Reason": "Physical disturbance depends strongly on substrate and habitat"},
            {"Treatment group": "High-pressure washing / sediment mixing", "Typical E score": "2.0", "Reason": "High disturbance and sediment or residual-oil redistribution risk"},
            {"Treatment group": "Low-pressure flushing / washing agents", "Typical E score": "4.5", "Reason": "Moderate disturbance and mobilization or residue concerns"},
            {"Treatment group": "Passive sorbents", "Typical E score": "6.5", "Reason": "Low-contact recovery with limited substrate disturbance"},
        ])
        st.dataframe(ecological_rules, hide_index=True, use_container_width=True)

    with noaa_tab:
        st.subheader("NOAA / SCAT treatment cross-check")
        st.caption("Crosswalk based on manual_shore_assess_aug2013.pdf. Page references are PDF page numbers from the supplied manual. This is an audit aid, not a substitute for an approved Shoreline Treatment Recommendation.")
        crosswalk = pd.DataFrame(NOAA_TREATMENT_CROSSWALK)
        crosswalk["treatment"] = crosswalk["treatment"].str.replace("_", " ").str.title()
        st.dataframe(crosswalk, hide_index=True, use_container_width=True)
        st.warning("The current synthetic scores are not NOAA scores. NOAA provides method objectives, habitat applicability, constraints, and monitoring considerations; numeric suitability scores require calibrated expert or incident data.", icon=":material/verified_user:")

    with validation_tab:
        render_validation_tab()

    with constraints_tab:
        st.subheader("Environmental and operational constraints")
        for constraint in constraints:
            st.warning(constraint, icon=":material/warning:")
        st.subheader("Endpoint interpretation")
        st.write(f"The selected leading option is estimated to reach the modeled 80% recovery endpoint in approximately {endpoint['days']} days ({endpoint['months']} months). This is an indicative planning estimate, not a regulatory closure date.")
        st.info("Recommended monitoring: repeat shoreline observations, document residual oiling, track habitat recovery, and confirm endpoint criteria with the incident management team and regulators.")

    with detail_tab:
        for index, result in enumerate(results, start=1):
            with st.expander(f"{index}. {result.treatment.replace('_', ' ').title()} | {result.feasibility.title()} | utility {result.utility:.2f}", expanded=index == 1):
                ecological = ecological_explanation(load_model(), result.treatment, analyzed_scenario)
                detail_columns = st.columns(4)
                detail_columns[0].metric("Suitability", f"{result.suitability:.2f} / 10")
                detail_columns[1].metric("Ecological fit", f"{result.ecological_suitability:.2f} / 10")
                detail_columns[2].metric("Utility", f"{result.utility:.2f} / 10")
                detail_columns[3].metric("Confidence", f"{result.confidence:.0%}")
                st.write(result.reason)
                st.markdown(f"**Ecological suitability basis:** {ecological['basis']} Score: **{ecological['score']:.1f}/10**.")

    with inputs_tab:
        input_frame = pd.DataFrame({"Input": [field.replace("_", " ").title() for field in analyzed_scenario.__dataclass_fields__], "Value": [str(value) for value in analyzed_scenario.__dict__.values()]})
        st.dataframe(input_frame, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
