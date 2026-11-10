"""Phase 2/4: historical case-study validation of the hybrid shoreline decision model.

Only values stated in the cited sources are fixed. Everything the sources do not state is sampled
(Latin hypercube) so that agreement is reported as robustness to missing information, not as a
single point prediction. Unsourced spills are kept as explicit NOT_SOURCED rows.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.decision_framework import HybridDecisionModel  # noqa: E402

RESULTS_DIR = ROOT / "results" / "historical"
N_DRAWS = 40
ACCESSED = "2026-10-27"

SOURCES = {
    "S1": "Michel J. et al. (2013) Extent and Degree of Shoreline Oiling: Deepwater Horizon Oil Spill, Gulf of Mexico, USA. PLoS ONE 8(6): e65087. https://doi.org/10.1371/journal.pone.0065087",
    "S2": f"NOAA OR&R, Response to the Exxon Valdez Spill (page last updated 3 Oct 2012). https://response.restoration.noaa.gov/oil-and-chemical-spills/significant-incidents/exxon-valdez-oil-spill/response-exxon-valdez.html (accessed {ACCESSED})",
    "S3": f"NOAA OR&R, High-pressure, Hot-water Washing and Oil Spills (page last updated 16 Mar 2019). https://response.restoration.noaa.gov/oil-and-chemical-spills/significant-incidents/exxon-valdez-oil-spill/high-pressure-hot-water-washing.html (accessed {ACCESSED})",
    "S4": "NOAA (2013) Shoreline Assessment Manual, 4th ed. (supplied as manual_shore_assess_aug2013.pdf), ESI 10A salt marsh response considerations.",
}

ACTIVE_UNSPECIFIED = "active"
NATURAL = {"natural_attenuation"}

# Historical case table. Fields not stated by a source are left blank on purpose.
CASES = [
    dict(Case_ID="DWH-01", Spill_Name="Deepwater Horizon (2010)", Shoreline_Type="Sand beach (amenity / high-use)",
         Substrate="Sand (some shell and mixed sand-shell)", Oiling_Intensity="Surface residue balls, patties, mats; penetration up to a few cm on some beaches",
         Exposure="", Habitat_Sensitivity="",
         Documented_Response="Extensive manual and mechanical cleanup; endpoint: no visible oil above background levels or as low as reasonably practicable",
         Documented_Outcome="Treatment conducted on 660 km (73.3%) of 900 km oiled beaches; chronic trace re-oiling persisted on eastern beaches",
         Source="S1", response_class="active", method_set="manual_removal|mechanical_removal"),
    dict(Case_ID="DWH-02", Spill_Name="Deepwater Horizon (2010)", Shoreline_Type="Sand beach (non-amenity, federally managed land)",
         Substrate="Sand", Oiling_Intensity="", Exposure="", Habitat_Sensitivity="Managed refuge / park shoreline (qualitative)",
         Documented_Response="Less intensive cleanup to minimise ecological impact; endpoint <1% visible oil plus site-specific endpoints",
         Documented_Outcome="Included in the 73.3% of oiled beaches treated; method not specified in source",
         Source="S1", response_class="active", method_set=""),
    dict(Case_ID="DWH-03", Spill_Name="Deepwater Horizon (2010)", Shoreline_Type="Marsh (general)",
         Substrate="Marsh soils", Oiling_Intensity="Emulsified oil pooled on surface, little penetration into soils",
         Exposure="Small tidal range (~0.5 m); wave exposure not stated", Habitat_Sensitivity="",
         Documented_Response="Treatment allowed on 71 km (8.9%) of 796 km oiled marsh; natural attenuation often recommended to avoid further damage; endpoints: no flushable oil, no sheens, no thick (>1 cm) oil on platform",
         Documented_Outcome="Much of the oil remaining at two years was where further treatment gave no net environmental benefit or endpoints were met",
         Source="S1", response_class="natural", method_set="natural_attenuation"),
    dict(Case_ID="DWH-04", Spill_Name="Deepwater Horizon (2010)", Shoreline_Type="Salt marsh, northern Barataria Bay (Spartina, Juncus)",
         Substrate="Marsh platform", Oiling_Intensity="Heavily oiled; emulsified oil layer averaging 2-3 cm on marsh platform (fall 2010); oiled vegetation mats and wrack",
         Exposure="Oil spread 10-15 m into marsh; small tidal range (~0.5 m)", Habitat_Sensitivity="",
         Documented_Response="Over 11 km cleaned by intensive manual and mechanical raking and cutting, removal/reduction of thick oil layers, limited loose organic sorbents",
         Documented_Outcome="Cleanup applied only to the most heavily oiled marsh; remaining marsh left to natural recovery",
         Source="S1", response_class="active", method_set="manual_removal|mechanical_removal|vegetation_cutting|passive_sorbents"),
    dict(Case_ID="DWH-05", Spill_Name="Deepwater Horizon (2010)", Shoreline_Type="Sand beach with buried oil residues (SRBs/SRPs)",
         Substrate="Sand", Oiling_Intensity="Surface residue balls and patties buried >1 m in places; subtidal oil mats",
         Exposure="Beach erosion/accretion cycles; storms re-exposed and buried oil", Habitat_Sensitivity="",
         Documented_Response="Extensive mechanical and manual excavation and sieving; >180,000 pits, trenches and auger holes used to delineate buried oil",
         Documented_Outcome="Removal of deeply buried residues continued through 2012; oil repeatedly buried, exposed and remobilised",
         Source="S1", response_class="active", method_set="manual_removal|mechanical_removal"),
    dict(Case_ID="EVOS-01", Spill_Name="Exxon Valdez (1989)", Shoreline_Type="Rocky intertidal / hard substrate (rocks, seawalls)",
         Substrate="Rock", Oiling_Intensity="", Exposure="", Habitat_Sensitivity="",
         Documented_Response="High-pressure hot-water washing of rocky intertidal areas",
         Documented_Outcome="Oiled and hot-water-washed sites initially declined more in population abundance than oiled, unwashed sites",
         Source="S2;S3", response_class="active", method_set="high_pressure_heated_washing|high_pressure_washing"),
    dict(Case_ID="PRE-NS", Spill_Name="Prestige (2002)", Shoreline_Type="", Substrate="", Oiling_Intensity="", Exposure="", Habitat_Sensitivity="",
         Documented_Response="NOT_SOURCED", Documented_Outcome="NOT_SOURCED", Source="none retrieved", response_class="", method_set=""),
    dict(Case_ID="SEA-NS", Spill_Name="Sea Empress (1996)", Shoreline_Type="", Substrate="", Oiling_Intensity="", Exposure="", Habitat_Sensitivity="",
         Documented_Response="NOT_SOURCED", Documented_Outcome="NOT_SOURCED", Source="none retrieved", response_class="", method_set=""),
    dict(Case_ID="WAK-NS", Spill_Name="Wakashio (2020)", Shoreline_Type="", Substrate="", Oiling_Intensity="", Exposure="", Habitat_Sensitivity="",
         Documented_Response="NOT_SOURCED", Documented_Outcome="NOT_SOURCED", Source="none retrieved", response_class="", method_set=""),
]

# Traceability: source -> extracted variable -> mapped model variable -> confidence.
TRACE = [
    ("DWH-01", "S1", "'mostly sand beach but includes shell and mixed sand and shell beaches'", "shoreline_type", "sand_beach", "High"),
    ("DWH-01", "S1", "'the oil penetrated up to a few centimeters into the sediments' (some sand beaches)", "penetration_depth_cm", "0-5 (sampled)", "Medium"),
    ("DWH-01", "S1", "'thick, viscous emulsion, containing up to 60% water'", "oil_category", "heavy", "Medium"),
    ("DWH-01", "S1", "'extensive manual and mechanical cleanup operations were required'", "documented method", "manual_removal | mechanical_removal", "High"),
    ("DWH-01", "-", "Not stated in source", "oil_coverage, wave_exposure, shoreline_sensitivity", "sampled over plausible range", "Low"),
    ("DWH-02", "S1", "'less intensive cleanup was conducted to minimize ecological impacts'", "documented class", "active (method unspecified)", "Medium"),
    ("DWH-02", "S1", "federally managed lands: national parks and wildlife refuges", "shoreline_type", "sand_beach", "Medium"),
    ("DWH-02", "-", "Not stated in source", "oil_coverage, penetration_depth_cm, wave_exposure, shoreline_sensitivity", "sampled over plausible range", "Low"),
    ("DWH-03", "S1", "'796 km of marshes that were oiled ... treatment was allowed along 71 km, or 8.9%'", "documented class", "natural (majority)", "High"),
    ("DWH-03", "S1", "'natural attenuation was often the recommended response action'", "documented method", "natural_attenuation", "High"),
    ("DWH-03", "S1", "'emulsified oil pooled on the surface with little penetration into the marsh soils'", "penetration_depth_cm", "0-3 (sampled)", "Medium"),
    ("DWH-03", "S1", "marsh habitat (mostly coastal herbaceous marsh)", "shoreline_type", "marsh", "High"),
    ("DWH-03", "S4", "ESI 10A: aggressive cleanup only when other resources are at great risk", "shoreline_sensitivity", "high / very_high (sampled)", "Medium"),
    ("DWH-04", "S1", "'heavily oiled layer on marsh platforms averaged 2-3 cm in thickness'", "oil_thickness (mm)", "20-30 (sampled)", "High"),
    ("DWH-04", "S1", "'Over 11 km ... cleaned using intensive manual and mechanical raking and cutting ... limited application of loose organic sorbents'", "documented method", "manual_removal | mechanical_removal | vegetation_cutting | passive_sorbents", "Medium"),
    ("DWH-04", "S1", "'emulsified oil ... pooled on the surface'; 'Heavy' oiling in northern Barataria Bay", "oil_category / oil_coverage", "heavy / 50-100 (sampled)", "Medium"),
    ("DWH-04", "S1", "'small tidal range (~0.5 m)'", "wave_exposure", "low / moderate (sampled)", "Low"),
    ("DWH-05", "S1", "'SRBs and SRPs became buried (>1 m in places)'", "penetration_depth_cm", "30 (model cap; documented >100)", "High"),
    ("DWH-05", "S1", "'extensive mechanical and manual excavation and sieving'", "documented method", "manual_removal | mechanical_removal", "High"),
    ("DWH-05", "-", "Not stated for the specific beaches", "oil_coverage, shoreline_sensitivity, wave_exposure", "sampled over plausible range", "Low"),
    ("EVOS-01", "S2", "'washing oiled beaches with hot water and mechanical scrubbing of beach rocks'", "documented method", "high_pressure_heated_washing | high_pressure_washing", "Medium"),
    ("EVOS-01", "S3", "'viable method for removing stranded oil from hard surfaces, like large rocks and seawalls'", "shoreline_type", "bedrock / boulder (sampled)", "Medium"),
    ("EVOS-01", "S3", "'oiled and hot-water washed sites initially suffered more severe declines ... than oiled and not-washed sites'", "outcome flag", "documented adverse outcome", "High"),
    ("EVOS-01", "-", "Oil described only as crude oil; coverage, penetration, exposure not stated", "oil_category, oil_coverage, penetration_depth_cm, wave_exposure", "sampled over plausible range", "Low"),
]

# Per-case model inputs. Fixed = documented; ranges / choices = sampled because the source is silent.
INPUT_SPECS = {
    "DWH-01": dict(fixed=dict(shoreline_type="sand_beach", oil_category="heavy"),
                   ranges=dict(oil_coverage=(5, 80), oil_thickness=(1, 15), penetration_depth_cm=(0, 5)),
                   choices=dict(shoreline_sensitivity=["low", "moderate", "high"], wave_exposure=["low", "moderate", "high"])),
    "DWH-02": dict(fixed=dict(shoreline_type="sand_beach", oil_category="heavy"),
                   ranges=dict(oil_coverage=(5, 60), oil_thickness=(1, 15), penetration_depth_cm=(0, 10)),
                   choices=dict(shoreline_sensitivity=["moderate", "high", "very_high"], wave_exposure=["low", "moderate", "high"])),
    "DWH-03": dict(fixed=dict(shoreline_type="marsh", oil_category="heavy"),
                   ranges=dict(oil_coverage=(5, 80), oil_thickness=(5, 30), penetration_depth_cm=(0, 3)),
                   choices=dict(shoreline_sensitivity=["high", "very_high"], wave_exposure=["low", "moderate"])),
    "DWH-04": dict(fixed=dict(shoreline_type="marsh", oil_category="heavy"),
                   ranges=dict(oil_coverage=(50, 100), oil_thickness=(20, 30), penetration_depth_cm=(0, 3)),
                   choices=dict(shoreline_sensitivity=["high", "very_high"], wave_exposure=["low", "moderate"])),
    "DWH-05": dict(fixed=dict(shoreline_type="sand_beach", oil_category="heavy", penetration_depth_cm=30.0, subsurface_oil=True),
                   ranges=dict(oil_coverage=(5, 60), oil_thickness=(1, 15)),
                   choices=dict(shoreline_sensitivity=["low", "moderate", "high"], wave_exposure=["moderate", "high"])),
    "EVOS-01": dict(fixed=dict(),
                    ranges=dict(oil_coverage=(20, 90), oil_thickness=(1, 15), penetration_depth_cm=(0, 5)),
                    choices=dict(shoreline_type=["bedrock", "boulder"], oil_category=["medium", "heavy"],
                                 shoreline_sensitivity=["low", "moderate", "high"], wave_exposure=["moderate", "high"])),
}


def sample_scenarios(case_id: str, seed: int = 11) -> list[Scenario]:
    spec = INPUT_SPECS[case_id]
    names = list(spec["ranges"]) + list(spec["choices"])
    unit = qmc.LatinHypercube(d=max(len(names), 1), seed=seed).random(N_DRAWS)
    scenarios = []
    for row in unit:
        values = dict(spec["fixed"])
        for index, (name, (low, high)) in enumerate(spec["ranges"].items()):
            values[name] = float(low + row[index] * (high - low))
        offset = len(spec["ranges"])
        for index, (name, options) in enumerate(spec["choices"].items()):
            values[name] = options[min(int(row[offset + index] * len(options)), len(options) - 1)]
        scenarios.append(Scenario(**values))
    return scenarios


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def treatment_class(treatment: str) -> str:
    return "natural" if treatment in NATURAL else "active"


def run_inference(model: HybridDecisionModel) -> pd.DataFrame:
    rows = []
    for case in CASES:
        if case["Case_ID"] not in INPUT_SPECS:
            continue
        acceptable = set(filter(None, case["method_set"].split("|")))
        tops, top3_hits, method_hits, class_hits, infeasible_doc, best_ranks = [], [], [], [], [], []
        for scenario in sample_scenarios(case["Case_ID"]):
            ranked = model.rank_treatments(scenario)
            top = ranked[0].treatment
            tops.append(top)
            class_hits.append(treatment_class(top) == case["response_class"])
            if acceptable:
                method_hits.append(top in acceptable)
                top3_hits.append(any(r.treatment in acceptable for r in ranked[:3]))
                feas = {r.treatment: r.feasibility for r in ranked}
                infeasible_doc.append(all(feas.get(t) == "ineligible" for t in acceptable))
                names = [r.treatment for r in ranked]
                best_ranks.append(min(names.index(t) + 1 for t in acceptable if t in names))
        modal = pd.Series(tops).mode().iloc[0]
        rows.append(dict(
            Case_ID=case["Case_ID"], documented_class=case["response_class"], documented_methods=case["method_set"],
            model_modal_top1=modal, model_modal_class=treatment_class(modal),
            top1_distribution="; ".join(f"{k}:{v}" for k, v in pd.Series(tops).value_counts().items()),
            class_agreement_frac=float(np.mean(class_hits)),
            method_agreement_frac=float(np.mean(method_hits)) if method_hits else np.nan,
            top3_hit_frac=float(np.mean(top3_hits)) if top3_hits else np.nan,
            documented_methods_all_ineligible_frac=float(np.mean(infeasible_doc)) if infeasible_doc else np.nan,
            median_best_documented_rank=float(np.median(best_ranks)) if best_ranks else np.nan,
            random_expected_best_rank=(len(ranked) + 1) / (len(acceptable & {r.treatment for r in ranked}) + 1) if acceptable else np.nan,
            n_ranked_treatments=len(ranked),
            n_draws=N_DRAWS))
    return pd.DataFrame(rows)


def confusion_and_metrics(results: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    truth = results["documented_class"]
    pred = results["model_modal_class"]
    labels = ["active", "natural"]
    matrix = pd.DataFrame([[int(((truth == t) & (pred == p)).sum()) for p in labels] for t in labels],
                          index=[f"documented_{x}" for x in labels], columns=[f"model_{x}" for x in labels])
    tp = int(((truth == "active") & (pred == "active")).sum())
    fp = int(((truth == "natural") & (pred == "active")).sum())
    fn = int(((truth == "active") & (pred == "natural")).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and precision + recall else float("nan")
    agree = int((truth == pred).sum())
    low, high = wilson(agree, len(results))
    method = results.dropna(subset=["method_agreement_frac"]).copy()
    method_hits = sum(
        row["model_modal_top1"] in set(row["documented_methods"].split("|")) for _, row in method.iterrows())
    m_low, m_high = wilson(method_hits, len(method))
    return matrix, dict(
        n_cases=len(results), class_agreement=agree, class_agreement_rate=agree / len(results),
        class_agreement_ci95=(round(float(low), 3), round(float(high), 3)),
        precision_active=precision, recall_active=recall, f1_active=f1,
        method_cases=len(method), method_agreement=method_hits, method_agreement_rate=method_hits / len(method) if len(method) else float("nan"),
        method_agreement_ci95=(round(float(m_low), 3), round(float(m_high), 3)),
        mean_top3_hit=float(results["top3_hit_frac"].mean()),
        mean_draw_level_method_agreement=float(results["method_agreement_frac"].mean()),
        majority_class_baseline=float(truth.value_counts(normalize=True).max()),
        always_active_baseline_agreement=float((truth == "active").mean()),
        distinct_top1_predictions_across_cases=int(results["model_modal_top1"].nunique()),
        mean_median_best_documented_rank=float(results["median_best_documented_rank"].mean()),
        random_ordering_expected_rank=float(results["random_expected_best_rank"].mean()),
        n_ranked_treatments=int(results["n_ranked_treatments"].iloc[0]))


def failure_analysis(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cases = {c["Case_ID"]: c for c in CASES}
    for _, row in results.iterrows():
        method_miss = row["model_modal_top1"] not in set(filter(None, row["documented_methods"].split("|"))) if row["documented_methods"] else False
        class_miss = row["model_modal_class"] != row["documented_class"]
        if not (method_miss or class_miss):
            continue
        if row["documented_methods_all_ineligible_frac"] and row["documented_methods_all_ineligible_frac"] >= 0.5:
            cause = "model limitation: FAST rules mark the documented method ineligible"
        elif 0.2 <= row["method_agreement_frac"] <= 0.8 if row["method_agreement_frac"] == row["method_agreement_frac"] else False:
            cause = "uncertainty: agreement depends on inputs the source does not state"
        elif class_miss:
            cause = "model limitation: class-level decision differs (active vs natural)"
        else:
            cause = "feature mismatch: model scores methods without oil-state, containment or net-benefit inputs the response used"
        rows.append(dict(
            Case=row["Case_ID"], Prediction=row["model_modal_top1"], Observed_Outcome=cases[row["Case_ID"]]["Documented_Response"][:140],
            Failure_Type="false positive (active predicted, natural documented)" if row["documented_class"] == "natural" and row["model_modal_class"] == "active"
            else "false negative (natural predicted, active documented)" if class_miss else "method mismatch (class agrees)",
            Potential_Cause=cause, Cause_Basis="analyst classification from computed signals"))
    return pd.DataFrame(rows)


def plot_results(results: pd.DataFrame, matrix: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})
    plot = results.copy()
    x = np.arange(len(plot))
    axes[0].bar(x - 0.2, plot["class_agreement_frac"], 0.4, label="Active-vs-natural class", color="#176b87")
    axes[0].bar(x + 0.2, plot["method_agreement_frac"].fillna(0), 0.4, label="Documented method as top-1", color="#db8b3e")
    axes[0].set_xticks(x, plot["Case_ID"], rotation=30, ha="right")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("Share of 40 input draws agreeing")
    axes[0].set_title("Agreement under unstated inputs")
    axes[0].legend(frameon=False, fontsize=9, loc="upper right")
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axes[1])
    axes[1].set_title("Class confusion (modal prediction)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "historical_agreement.png", dpi=300)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{k: v for k, v in c.items() if k not in {"response_class", "method_set"}} for c in CASES]).to_csv(RESULTS_DIR / "historical_cases.csv", index=False)
    pd.DataFrame(TRACE, columns=["Case_ID", "Source", "Extracted_Variable", "Mapped_Model_Variable", "Mapped_Value", "Confidence"]).to_csv(RESULTS_DIR / "traceability_matrix.csv", index=False)
    pd.DataFrame([{"Source_ID": k, "Citation": v} for k, v in SOURCES.items()]).to_csv(RESULTS_DIR / "sources.csv", index=False)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = run_inference(HybridDecisionModel())
    matrix, metrics = confusion_and_metrics(results)
    failures = failure_analysis(results)
    results.to_csv(RESULTS_DIR / "inference_results.csv", index=False)
    matrix.to_csv(RESULTS_DIR / "confusion_matrix.csv")
    failures.to_csv(RESULTS_DIR / "failure_analysis.csv", index=False)
    pd.Series(metrics).to_csv(RESULTS_DIR / "metrics.csv", header=["value"])
    plot_results(results, matrix)

    confidence_counts = pd.DataFrame(TRACE, columns=["Case_ID", "Source", "x", "y", "z", "Confidence"])["Confidence"].value_counts()
    print(results[["Case_ID", "documented_class", "model_modal_top1", "class_agreement_frac", "method_agreement_frac", "top3_hit_frac"]].round(2).to_string(index=False))
    print(matrix.to_string())
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print("TRACE_CONFIDENCE", confidence_counts.to_dict())
    print(failures.to_string(index=False) if len(failures) else "NO_FAILURES")


if __name__ == "__main__":
    main()
