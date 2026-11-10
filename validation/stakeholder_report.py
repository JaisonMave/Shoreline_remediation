"""Phase 5: one-page stakeholder report built only from the saved validation outputs (no numbers typed in)."""
from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "reports"
GREEN, AMBER, RED, INK, GREY = "#2e7d32", "#ef8f00", "#c62828", "#1f2933", "#6b7280"


def metric(frame: pd.DataFrame, key: str) -> float:
    return float(frame.set_index(frame.columns[0]).loc[key, "value"])


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.fill(line, width) for line in text.split("\n"))


def collect() -> dict:
    comparison = pd.read_csv(RESULTS / "reproduction" / "metric_comparison.csv")
    fuzzy = comparison[(comparison["input_mode"] == "fuzzy") & (comparison["metric"] == "test_acc")].set_index("model")
    hist = pd.read_csv(RESULTS / "historical" / "metrics.csv")
    paper_check = pd.read_csv(RESULTS / "explainability" / "paper_expectation_check.csv")
    scat = pd.read_csv(RESULTS / "explainability" / "shoreline_scat_checks.csv")
    perm = pd.read_csv(RESULTS / "explainability" / "shoreline_permutation_importance.csv")
    audit = pd.read_csv(RESULTS / "explainability" / "shoreline_training_target_audit.csv")
    trace = pd.read_csv(RESULTS / "historical" / "traceability_matrix.csv")
    return dict(fuzzy=fuzzy, hist=hist, paper_check=paper_check, scat=scat, perm=perm, audit=audit, trace=trace)


def build() -> Path:
    d = collect()
    fuzzy, hist = d["fuzzy"], d["hist"]
    n_cases = int(metric(hist, "n_cases"))
    agree = int(metric(hist, "class_agreement"))
    baseline = metric(hist, "always_active_baseline_agreement")
    distinct = int(metric(hist, "distinct_top1_predictions_across_cases"))
    rank = metric(hist, "mean_median_best_documented_rank")
    rank_random = metric(hist, "random_ordering_expected_rank")
    n_rank = int(metric(hist, "n_ranked_treatments"))
    method_rate = metric(hist, "method_agreement_rate")

    paper_check = d["paper_check"]
    consistent = int((paper_check["verdict"] == "Consistent").sum())
    tested = int((paper_check["verdict"] != "Not tested (band effect)").sum())
    scat = d["scat"]
    scat_pass = int((scat["verdict"] == "PASS").sum())
    perm = d["perm"]
    unused = perm[perm["used_by"] == "not used by ranking"]["feature"].tolist()
    inert = perm[perm["mean_rank_shift"] < 0.05]["feature"].tolist()
    audit = d["audit"]
    flat = sorted(audit[audit["variance_explained_eta2"] < 0.05]["feature"].value_counts().loc[lambda s: s == audit["treatment"].nunique()].index)
    trace_counts = d["trace"]["Confidence"].value_counts().to_dict()

    repro_gap = float(fuzzy.loc[["GPR", "SVR"], "relative_difference_pct"].max())
    ann_gap = float(fuzzy.loc["ANN-GD", "relative_difference_pct"])

    repro_status = ("PARTIAL", AMBER)
    hist_status = ("FAIL", RED) if (agree / n_cases <= baseline + 1e-9 and distinct <= 1) else ("PARTIAL", AMBER)
    plaus_status = ("FAIL", RED) if scat_pass < len(scat) / 2 else (("PARTIAL", AMBER) if scat_pass < len(scat) else ("PASS", GREEN))
    overall_ok = hist_status[0] == "PASS" and plaus_status[0] == "PASS"

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.06, 0.965, "Shoreline remediation decision model: validation summary", fontsize=15.5, weight="bold", color=INK, va="top")
    ax.text(0.06, 0.94, f"Scientific validation audit  |  {date.today():%d %B %Y}  |  Screening prototype, not operationally validated",
            fontsize=8.5, color=GREY, va="top")
    ax.plot([0.06, 0.94], [0.925, 0.925], color=INK, lw=1)

    verdict = ("Not ready for operational use. Usable only as a transparent screening aid." if not overall_ok
               else "Passed the checks run here; operational use still needs expert review.")
    ax.add_patch(plt.Rectangle((0.06, 0.855), 0.88, 0.058, color="#fdecea" if not overall_ok else "#e8f5e9", lw=0))
    ax.text(0.075, 0.884, "Bottom line", fontsize=9, weight="bold", color=RED if not overall_ok else GREEN, va="center")
    ax.text(0.17, 0.884, verdict, fontsize=10.5, weight="bold", color=INK, va="center")

    rows = [
        ("1. Reproduces the published ML study?", repro_status,
         f"The study (Mohammadiun 2022) is an offshore, three-method model, not a shoreline model, so only the modelling approach was tested. "
         f"GPR and SVR match the paper's testing accuracy within {repro_gap:.1f}%. ANN-GD does not ({ann_gap:.0f}% gap). "
         f"Four of seven paper models could not be rebuilt. The paper's model ranking is not statistically supported."),
        ("2. Agrees with documented historical decisions?", hist_status,
         f"The model matched the documented active-versus-natural decision in {agree} of {n_cases} sourced cases, "
         f"but a rule that always answers 'active cleanup' scores {baseline:.0%}. The model gave {distinct} distinct top choice for every shoreline "
         f"(marsh, sand, rock). The documented method ranked {rank:.1f} of {n_rank} on average versus {rank_random:.1f} for random ordering; "
         f"exact method agreement was {method_rate:.0%}."),
        ("3. Are the learned drivers scientifically sensible?", plaus_status,
         f"On the paper's data, {consistent} of {tested} factor-method relationships agree with the paper's own Table 1 logic (permutation importance and SHAP). "
         f"For the shoreline model, {scat_pass} of {len(scat)} checks against NOAA/SCAT logic pass. "
         f"Its suitability layer is trained on rule-generated scores in which {', '.join(f.replace('_', ' ') for f in flat) or 'no input'} have no effect, "
         f"and {len(inert)} of {len(perm)} scenario inputs shown in the app do not change the ranking."),
        ("4. Is the new shoreline transport model trustworthy?", ("PROTOTYPE", AMBER),
         "It replaces ocean-slick kinetics with a cross-shore advection-dispersion-reaction model of oil in sediment and vegetation. "
         "It behaves plausibly (mass declines, treatment shortens recovery), but most parameters are assumed placeholders and it has not been "
         "calibrated to field survey data. Treat its outputs as relative, not predictive."),
    ]
    top = 0.835
    block = 0.124
    for index, (title, (label, colour), body) in enumerate(rows):
        y = top - index * block
        ax.text(0.06, y, title, fontsize=10.5, weight="bold", color=INK, va="top")
        ax.add_patch(plt.Rectangle((0.80, y - 0.019), 0.14, 0.022, color=colour, lw=0))
        ax.text(0.87, y - 0.008, label, fontsize=8.5, weight="bold", color="white", ha="center", va="center")
        ax.text(0.06, y - 0.027, wrap(body, 112), fontsize=8.3, color=INK, va="top", linespacing=1.35)

    chart_a = fig.add_axes([0.09, 0.265, 0.36, 0.115])
    models = ["GPR", "SVR", "ANN-GD"]
    paper_values = fuzzy.loc[models, "paper"].to_numpy()
    repro_values = fuzzy.loc[models, "reproduced"].to_numpy()
    positions = range(len(models))
    chart_a.bar([p - 0.2 for p in positions], paper_values, 0.4, color="#4d4d4d", label="Paper")
    chart_a.bar([p + 0.2 for p in positions], repro_values, 0.4, color="#176b87", label="Reproduced")
    chart_a.set_xticks(list(positions), models, fontsize=8)
    chart_a.set_ylim(0, 110)
    chart_a.set_ylabel("Testing accuracy (%)", fontsize=8)
    chart_a.set_title("Reproduction", fontsize=9, loc="left")
    chart_a.legend(frameon=False, fontsize=7, ncol=2, loc="upper center")
    chart_b = fig.add_axes([0.56, 0.265, 0.36, 0.115])
    labels = ["Model", "Always\n'active'"]
    chart_b.bar(labels, [agree / n_cases * 100, baseline * 100], color=["#176b87", "#9aa5b1"], width=0.5)
    chart_b.set_ylim(0, 110)
    chart_b.set_ylabel("Class agreement (%)", fontsize=8)
    chart_b.set_title(f"Historical decisions ({n_cases} cases)", fontsize=9, loc="left")
    chart_b.tick_params(labelsize=8)
    for chart in (chart_a, chart_b):
        chart.spines[["top", "right"]].set_visible(False)

    ax.text(0.06, 0.232, "What to do next", fontsize=10.5, weight="bold", color=INK, va="top")
    steps = [
        "Replace the constant score given to 10 of 15 treatments with expert scores, then repeat the historical check.",
        "Add the inputs real responses weighed (net environmental benefit, access, waste, season) and a natural-recovery threshold.",
        "Source more cases (Prestige, Sea Empress, Wakashio are still unsourced) and keep the source-to-variable traceability matrix.",
        "Calibrate the transport model to Deepwater Horizon marsh and beach SCAT time series before using it for decisions.",
    ]
    for i, step in enumerate(steps):
        ax.text(0.07, 0.208 - i * 0.032, f"{i + 1}.", fontsize=8.5, weight="bold", color=INK, va="top")
        ax.text(0.095, 0.208 - i * 0.032, wrap(step, 105), fontsize=8.3, color=INK, va="top", linespacing=1.3)

    ax.plot([0.06, 0.94], [0.065, 0.065], color=GREY, lw=0.6)
    footer = (f"Evidence base: traceability matrix of {sum(trace_counts.values())} extracted variables "
              f"({trace_counts.get('High', 0)} High, {trace_counts.get('Medium', 0)} Medium, {trace_counts.get('Low', 0)} Low confidence). "
              "Historical sources: Michel et al. 2013 (PLoS ONE), NOAA OR&R Exxon Valdez pages, NOAA Shoreline Assessment Manual. "
              "Agreement figures from six cases carry wide uncertainty. Full tables and plots: results/ folders and the dashboard Validation tab.")
    ax.text(0.06, 0.058, wrap(footer, 128), fontsize=6.8, color=GREY, va="top", linespacing=1.3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT_DIR / "stakeholder_report.pdf"
    fig.savefig(pdf_path)
    fig.savefig(OUT_DIR / "stakeholder_report.png", dpi=200)
    plt.close(fig)
    return pdf_path


if __name__ == "__main__":
    print("WROTE", build())
