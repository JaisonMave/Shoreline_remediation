from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.shoreline_remediation.data_model import Scenario
from src.shoreline_remediation.decision_framework import HybridDecisionModel


SCENARIO_LIBRARY = [
    Scenario(
        shoreline_type="marsh",
        shoreline_sensitivity="very_high",
        oil_category="heavy",
        oil_coverage=35,
        oil_thickness=6,
        penetration_depth_cm=4,
        wave_exposure="low",
        tidal_range="low",
        temperature_c=12,
        season="spring",
        substrate_permeability="low",
        surface_oil=True,
        subsurface_oil=False,
        accessibility="restricted",
        habitat_type="salt_marsh",
        recovery_potential="high",
        waste_handling="moderate",
    ),
    Scenario(
        shoreline_type="sand_beach",
        shoreline_sensitivity="moderate",
        oil_category="heavy",
        oil_coverage=80,
        oil_thickness=15,
        penetration_depth_cm=10,
        wave_exposure="moderate",
        tidal_range="moderate",
        temperature_c=18,
        season="summer",
        substrate_permeability="moderate",
        surface_oil=True,
        subsurface_oil=False,
        accessibility="good",
        habitat_type="sandy_beach",
        recovery_potential="moderate",
        waste_handling="manageable",
    ),
    Scenario(
        shoreline_type="mixed_sediment",
        shoreline_sensitivity="high",
        oil_category="heavy",
        oil_coverage=65,
        oil_thickness=12,
        penetration_depth_cm=8,
        wave_exposure="moderate",
        tidal_range="moderate",
        temperature_c=14,
        season="summer",
        substrate_permeability="moderate",
        surface_oil=True,
        subsurface_oil=False,
        accessibility="good",
        habitat_type="mixed_sediment",
        recovery_potential="moderate",
        waste_handling="manageable",
    ),
    Scenario(
        shoreline_type="cobble",
        shoreline_sensitivity="moderate",
        oil_category="light",
        oil_coverage=40,
        oil_thickness=4,
        penetration_depth_cm=2,
        wave_exposure="high",
        tidal_range="high",
        temperature_c=16,
        season="autumn",
        substrate_permeability="high",
        surface_oil=True,
        subsurface_oil=False,
        accessibility="good",
        habitat_type="gravel_beach",
        recovery_potential="high",
        waste_handling="manageable",
    ),
    Scenario(
        shoreline_type="mudflat",
        shoreline_sensitivity="high",
        oil_category="medium",
        oil_coverage=50,
        oil_thickness=8,
        penetration_depth_cm=7,
        wave_exposure="low",
        tidal_range="moderate",
        temperature_c=11,
        season="spring",
        substrate_permeability="low",
        surface_oil=True,
        subsurface_oil=True,
        accessibility="restricted",
        habitat_type="mudflat",
        recovery_potential="moderate",
        waste_handling="moderate",
    ),
    Scenario(
        shoreline_type="bedrock",
        shoreline_sensitivity="low",
        oil_category="light",
        oil_coverage=25,
        oil_thickness=2,
        penetration_depth_cm=1,
        wave_exposure="high",
        tidal_range="moderate",
        temperature_c=20,
        season="summer",
        substrate_permeability="high",
        surface_oil=True,
        subsurface_oil=False,
        accessibility="good",
        habitat_type="rocky_shore",
        recovery_potential="high",
        waste_handling="manageable",
    ),
]


def get_key_drivers(scenario: Scenario) -> str:
    drivers = []
    if scenario.shoreline_sensitivity in {"high", "very_high"}:
        drivers.append("high ecological sensitivity")
    if scenario.oil_category in {"heavy", "solid"}:
        drivers.append("heavy oil persistence")
    if scenario.wave_exposure == "high":
        drivers.append("high wave exposure")
    if scenario.penetration_depth_cm > 5:
        drivers.append("penetration below surface")
    if scenario.accessibility == "restricted":
        drivers.append("restricted operational access")
    if not drivers:
        drivers.append("low disturbance and accessible shoreline")
    return "; ".join(drivers[:3])


def get_uncertainty_breakdown(scenario: Scenario, results) -> dict:
    top = results[0]
    second = results[1] if len(results) > 1 else top
    utility_gap = max(0.0, abs(top.utility - second.utility))
    separation_uncertainty = 1.0 - min(utility_gap / 2.0, 1.0)
    scenario_complexity = min(
        1.0,
        0.30 * scenario.oil_coverage / 100.0
        + 0.25 * min(scenario.penetration_depth_cm / 20.0, 1.0)
        + 0.20 * (scenario.subsurface_oil or scenario.penetration_depth_cm > 5)
        + 0.15 * (scenario.accessibility == "restricted")
        + 0.10 * (scenario.shoreline_sensitivity in {"high", "very_high"}),
    )
    model_confidence = 1.0 - float(top.confidence)
    score = round(min(1.0, max(0.0, 0.45 * separation_uncertainty + 0.35 * scenario_complexity + 0.20 * model_confidence)), 2)
    if score < 0.33:
        category = "Low uncertainty"
        interpretation = "The leading option is clearly separated and the scenario has limited complexity flags."
    elif score < 0.66:
        category = "Moderate uncertainty"
        interpretation = "The leading option is usable for screening, but alternatives or scenario conditions remain relevant."
    else:
        category = "High uncertainty"
        interpretation = "Treat the ranking as provisional and prioritize expert review, monitoring, and contingency planning."
    return {
        "score": score,
        "category": category,
        "confidence": round(1.0 - score, 2),
        "utility_gap": round(utility_gap, 2),
        "scenario_complexity": round(scenario_complexity, 2),
        "model_confidence": round(float(top.confidence), 2),
        "interpretation": interpretation,
    }


def get_uncertainty_score(scenario: Scenario, results) -> float:
    return get_uncertainty_breakdown(scenario, results)["score"]


def evaluate_scenario(scenario: Scenario, model: HybridDecisionModel):
    results = model.rank_treatments(scenario)
    top = results[0]
    uncertainty = get_uncertainty_score(scenario, results)
    print(f"\nScenario: {scenario.shoreline_type} | sensitivity={scenario.shoreline_sensitivity} | oil={scenario.oil_category} | exposure={scenario.wave_exposure}")
    print("-" * 90)
    for result in results[:6]:
        print(
            f"{result.treatment:30s} | feasibility={result.feasibility:10s} | "
            f"suitability={result.suitability:5.2f} | utility={result.utility:5.2f} | "
            f"confidence={result.confidence:4.2f}"
        )
    print(f"Top recommendation: {top.treatment} (utility={top.utility:.2f}, feasibility={top.feasibility})")
    print(f"Uncertainty score: {uncertainty:.2f} | Drivers: {get_key_drivers(scenario)}")
    return results, top, uncertainty, get_key_drivers(scenario)


def generate_comparison_plot(output_path: str):
    fig = plt.figure(figsize=(12.8, 7.0), facecolor="white")
    ax = fig.add_axes([0.12, 0.16, 0.75, 0.68])

    t = np.linspace(0.0, 12.0, 800)
    curves = {
        "Conditions in the Absence of a Spill": 0.93 + 0.15 * np.exp(-((t - 7.0) / 3.8) ** 2) + 0.08 * np.sin(t / 2.4),
        "Cleanup 1": 0.60 + 0.46 * np.exp(-((t - 4.8) / 2.7) ** 2) - 0.18 * np.exp(-((t - 1.5) / 1.0) ** 2),
        "Cleanup 2": 0.48 + 0.44 * np.exp(-((t - 5.2) / 3.2) ** 2) - 0.22 * np.exp(-((t - 1.8) / 1.3) ** 2),
        "Cleanup 3": 0.30 + 0.42 * np.exp(-((t - 6.0) / 3.5) ** 2) - 0.16 * np.exp(-((t - 2.0) / 1.6) ** 2),
        "No Cleanup": -0.28 + 0.45 * np.exp(-((t - 2.0) / 1.3) ** 2) - 0.52 * np.exp(-((t - 0.9) / 0.8) ** 2),
    }

    colors = ["#f28e2b", "#1f77b4", "#9b59b6", "#d62728", "#2ca02c"]
    for idx, (label, y) in enumerate(curves.items()):
        ax.plot(t, y, color=colors[idx], lw=2.8, alpha=0.95)

    ax.set_xlim(-0.5, 12.0)
    ax.set_ylim(-1.1, 1.3)
    ax.set_xlabel("Time", fontsize=20)
    ax.set_ylabel("Impact / Recovery", fontsize=20)
    ax.tick_params(axis="both", labelsize=14)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_position(("data", 0))
    ax.spines["bottom"].set_position(("data", 0))
    ax.spines["left"].set_linewidth(2.3)
    ax.spines["bottom"].set_linewidth(2.3)

    ax.annotate('', xy=(12.2, 0), xytext=(0, 0), arrowprops=dict(arrowstyle='-|>', lw=2.2, color='black'))
    ax.annotate('', xy=(0, 1.18), xytext=(0, -1.0), arrowprops=dict(arrowstyle='-|>', lw=2.2, color='black'))

    label_positions = [
        ("Conditions in the Absence of a Spill", 8.9, 0.86),
        ("Cleanup 1", 7.6, 0.58),
        ("Cleanup 2", 7.4, 0.38),
        ("Cleanup 3", 6.6, 0.12),
        ("No Cleanup", 6.5, -0.12),
    ]
    for text, x, y in label_positions:
        ax.text(x, y, text, fontsize=16, rotation=0, ha="center", va="center", color="black")

    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def generate_pdf_report(summary_df: pd.DataFrame, plot_path: str, output_path: str):
    fig = plt.figure(figsize=(12, 8), facecolor="white")
    gs = fig.add_gridspec(2, 1, height_ratios=[3.0, 1.6])
    ax = fig.add_subplot(gs[0])

    t = np.linspace(0.0, 12.0, 800)
    curves = {
        "Conditions in the Absence of a Spill": 0.93 + 0.15 * np.exp(-((t - 7.0) / 3.8) ** 2) + 0.08 * np.sin(t / 2.4),
        "Cleanup 1": 0.60 + 0.46 * np.exp(-((t - 4.8) / 2.7) ** 2) - 0.18 * np.exp(-((t - 1.5) / 1.0) ** 2),
        "Cleanup 2": 0.48 + 0.44 * np.exp(-((t - 5.2) / 3.2) ** 2) - 0.22 * np.exp(-((t - 1.8) / 1.3) ** 2),
        "Cleanup 3": 0.30 + 0.42 * np.exp(-((t - 6.0) / 3.5) ** 2) - 0.16 * np.exp(-((t - 2.0) / 1.6) ** 2),
        "No Cleanup": -0.28 + 0.45 * np.exp(-((t - 2.0) / 1.3) ** 2) - 0.52 * np.exp(-((t - 0.9) / 0.8) ** 2),
    }
    colors = ["#f28e2b", "#1f77b4", "#9b59b6", "#d62728", "#2ca02c"]
    for idx, (_, y) in enumerate(curves.items()):
        ax.plot(t, y, color=colors[idx], lw=2.8)

    ax.set_xlim(-0.5, 12.0)
    ax.set_ylim(-1.1, 1.3)
    ax.set_xlabel("Time", fontsize=15)
    ax.set_ylabel("Impact / Recovery", fontsize=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_position(("data", 0))
    ax.spines["bottom"].set_position(("data", 0))
    ax.spines["left"].set_linewidth(2.0)
    ax.spines["bottom"].set_linewidth(2.0)
    ax.tick_params(labelsize=11)

    table_ax = fig.add_subplot(gs[1])
    table_ax.axis("off")
    table_data = summary_df[["scenario_id", "shoreline_type", "top_treatment", "utility", "uncertainty", "key_decision_drivers"]].copy()
    table_data.columns = ["ID", "Shoreline", "Top treatment", "Utility", "Uncertainty", "Key drivers"]
    table = table_ax.table(
        cellText=table_data.values,
        colLabels=table_data.columns,
        loc="center",
        cellLoc="center",
        colLoc="center",
        fontsize=9,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.5)

    fig.suptitle("Shoreline Remediation Comparison Report", fontsize=18, y=0.97)
    fig.savefig(output_path, format="pdf", dpi=220, bbox_inches="tight")
    plt.close(fig)


def generate_html_dashboard(summary_df: pd.DataFrame, image_path: str, output_path: str):
    cards = []
    for _, row in summary_df.iterrows():
        cards.append(f"""
        <div class=\"card\">
          <h3>Scenario {int(row['scenario_id'])}: {row['shoreline_type']}</h3>
          <p><strong>Top treatment:</strong> {row['top_treatment']}</p>
          <p><strong>Utility:</strong> {row['utility']}</p>
          <p><strong>Uncertainty:</strong> {row['uncertainty']}</p>
          <p><strong>Key drivers:</strong> {row['key_decision_drivers']}</p>
        </div>
        """)

    cards_html = "\n".join(cards)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset=\"utf-8\" />
      <title>Shoreline Remediation Dashboard</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 24px; color: #1d1d1f; }}
        h1 {{ text-align: center; margin-bottom: 18px; }}
        .plot {{ text-align: center; margin: 24px auto 18px auto; }}
        .plot img {{ max-width: 100%; border: 1px solid #d0d0d0; background: white; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
        .card {{ background: white; border: 1px solid #d7d7d7; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }}
        .card h3 {{ margin-top: 0; color: #1f3b74; }}
        p {{ margin: 8px 0; line-height: 1.4; }}
      </style>
    </head>
    <body>
      <h1>Shoreline Remediation Comparison Dashboard</h1>
      <div class=\"plot\">
        <img src=\"{image_path}\" alt=\"Shoreline remediation comparison plot\" />
      </div>
      <div class=\"cards\">{cards_html}</div>
    </body>
    </html>
    """
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)


def main():
    model = HybridDecisionModel()
    rows = []

    for index, scenario in enumerate(SCENARIO_LIBRARY, start=1):
        results, top, uncertainty, drivers = evaluate_scenario(scenario, model)
        rows.append(
            {
                "scenario_id": index,
                "shoreline_type": scenario.shoreline_type,
                "shoreline_sensitivity": scenario.shoreline_sensitivity,
                "oil_category": scenario.oil_category,
                "wave_exposure": scenario.wave_exposure,
                "top_treatment": top.treatment,
                "utility": round(top.utility, 2),
                "feasibility": top.feasibility,
                "uncertainty": uncertainty,
                "key_decision_drivers": drivers,
            }
        )

    summary_df = pd.DataFrame(rows)
    output_dir = Path(__file__).resolve().parents[2]
    report_dir = output_dir / "reports"
    report_dir.mkdir(exist_ok=True)
    summary_path = report_dir / "scenario_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    plot_path = report_dir / "scenario_comparison_report.png"
    pdf_path = report_dir / "scenario_comparison_report.pdf"
    html_path = report_dir / "scenario_dashboard.html"

    generate_comparison_plot(str(plot_path))
    generate_pdf_report(summary_df, str(plot_path), str(pdf_path))
    generate_html_dashboard(summary_df, "scenario_comparison_report.png", str(html_path))

    print("\nScenario summary saved to:", summary_path)
    print("PNG plot saved to:", plot_path)
    print("PDF report saved to:", pdf_path)
    print("HTML dashboard saved to:", html_path)
    print("\nSummary table:")
    print(summary_df[[
        "scenario_id",
        "shoreline_type",
        "top_treatment",
        "utility",
        "uncertainty",
        "key_decision_drivers",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
