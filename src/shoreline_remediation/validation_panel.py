"""Streamlit panel documenting validation results, challenges, and the process-model basis."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
REPRO = ROOT / "results" / "reproduction"
HIST = ROOT / "results" / "historical"
EXPLAIN = ROOT / "results" / "explainability"

LITERATURE = [
    ("Geng X., An C., Lee K., Boufadel M.C. (2021)", "Modeling oil biodegradation and bioremediation within beaches. Curr. Opin. Chem. Eng. 35:100751", "Supplied PDF", "Kinetics (first-order, Monod), O2 and N limitation, tidal washout, salinity effects - used directly"),
    ("Geng X. and Boufadel M.C. (2015)", "Biodegradation of subsurface oil in a tidally influenced sand beach: impact of hydraulics and interaction with pore water chemistry. Water Resour. Res. DOI 10.1002/2014WR016870", "Verified via Crossref (not read in full)", "Reactive-transport beach model family; sandy beaches rather than marsh"),
    ("Torlapati J. et al. (2014)", "Shoreline Bioremediation Model (SBM). Int. Oil Spill Conf. DOI 10.7901/2169-3358-2014.1.1099", "Verified via Crossref (not read in full)", "Packaged beach biodegradation tool; candidate for benchmarking"),
    ("Gundlach E.R. (1987)", "Oil-holding capacities and removal coefficients for different shoreline types. Int. Oil Spill Conf. DOI 10.7901/2169-3358-1987-1-451", "Verified via Crossref (values not retrieved)", "Shoreline-type retention and removal-rate concept used by trajectory models; numeric values must be taken from the paper"),
    ("Beegle-Krause J. (2001)", "General NOAA Oil Modeling Environment (GNOME). Int. Oil Spill Conf. DOI 10.7901/2169-3358-2001-2-865", "Verified via Crossref (not read in full)", "Open trajectory model with shoreline interaction; no marsh-interior transport"),
    ("Nixon Z., Michel J., Zengel S. et al. (2017)", "Remotely-sensed oil and shoreline interaction modeling. Int. Oil Spill Conf. DOI 10.7901/2169-3358-2017.1.2600", "Verified via Crossref (not read in full)", "Closest found to oil-shoreline interaction on complex shorelines; check for transferable parameters"),
    ("Michel J. et al. (2013)", "Extent and degree of shoreline oiling: Deepwater Horizon. PLoS ONE 8(6):e65087. DOI 10.1371/journal.pone.0065087", "Read (open access)", "Marsh oil geometry, thickness, tidal range and endpoints - used for parameters and validation"),
]


def _read(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def _metric_value(metrics: pd.DataFrame | None, key: str, default=np.nan):
    if metrics is None or key not in set(metrics.iloc[:, 0]):
        return default
    return metrics.loc[metrics.iloc[:, 0] == key, metrics.columns[1]].iloc[0]


def make_transect_figure(scenario, treatment: str):
    from src.shoreline_remediation.shoreline_transport import simulate_transect

    days = [0, 7, 30, 90, 365]
    _, x_axis, profiles = simulate_transect(scenario, treatment, days, return_profiles=True)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    palette = plt.cm.viridis(np.linspace(0.05, 0.9, len(days)))
    for color, day, profile in zip(palette, days, profiles):
        ax.plot(x_axis, profile, color=color, lw=2.2, label=f"day {day}")
    ax.axhline(10.0, color="#a84c4c", ls="--", lw=1.2, label="10 mm thick-oil endpoint")
    ax.set_xlabel("Cross-shore distance from waterline (m)")
    ax.set_ylabel("Oil thickness equivalent (mm)")
    ax.set_title("Oil movement across the shore (cross-shore transport model)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=9)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.tight_layout()
    return fig


def _render_plausibility() -> None:
    paper = _read(EXPLAIN / "paper_expectation_check.csv")
    scat = _read(EXPLAIN / "shoreline_scat_checks.csv")
    perm = _read(EXPLAIN / "shoreline_permutation_importance.csv")
    audit = _read(EXPLAIN / "shoreline_training_target_audit.csv")
    if paper is None or scat is None or perm is None:
        st.info("Run validation/feature_validation.py to generate the explainability results.")
        return

    st.markdown("**3a. Paper dataset: do learned drivers match the paper's own favourable conditions (Table 1)?**")
    counts = paper["verdict"].value_counts()
    st.write("Verdicts across 18 factor-method pairs: " + ", ".join(f"{k} = {v}" for k, v in counts.items()) + ".")
    for name in ("paper_permutation_importance.png", "paper_shap_beeswarm.png"):
        if (EXPLAIN / name).exists():
            st.image(str(EXPLAIN / name), use_container_width=True)
    flagged = paper[~paper["verdict"].isin(["Consistent"])][["output", "feature", "documented_expectation", "basis", "mean_share", "spearman_feature_vs_shap", "spearman_feature_vs_expert_score", "verdict"]]
    st.dataframe(flagged.round(3), hide_index=True, use_container_width=True)
    with st.expander("All 18 factor-method pairs"):
        st.dataframe(paper.round(3), hide_index=True, use_container_width=True)
    st.caption(
        "Importance is the rise in held-out squared error when a factor is shuffled (5-fold x 6 repeats; GPR and random forest), "
        "shown as a share of the total. SHAP is computed out-of-fold on a random forest. A relationship is 'Consistent' when an expected driver "
        "holds at least 8 % of importance with the documented sign, and a 'not sensitive' factor holds less than 25 %. These cut-offs are judgement calls."
    )

    st.markdown("**3b. Shoreline model: checks against NOAA / SCAT logic**")
    n_pass = int((scat["verdict"] == "PASS").sum())
    (st.success if n_pass == len(scat) else st.error)(f"{n_pass} of {len(scat)} SCAT-logic checks pass.", icon=":material/rule:")
    st.dataframe(scat, hide_index=True, use_container_width=True)
    if (EXPLAIN / "shoreline_feature_importance.png").exists():
        st.image(str(EXPLAIN / "shoreline_feature_importance.png"), use_container_width=True)
    inert = perm[perm["mean_rank_shift"] < 0.05]["feature"].tolist()
    if inert:
        st.warning("Inputs that do not change the treatment ranking: " + ", ".join(f.replace("_", " ") for f in inert) + ".", icon=":material/tune:")
    if audit is not None:
        n_treat = audit["treatment"].nunique()
        flat = audit.groupby("feature")["variance_explained_eta2"].max()
        flat = sorted(flat[flat < 0.05].index)
        if flat:
            st.warning(
                f"The learned suitability layer is trained on rule-generated scores. In all {n_treat} trained treatments, "
                + ", ".join(f.replace("_", " ") for f in flat) + " explain under 5 % of the target variance, so the model cannot have learned any dependence on them.",
                icon=":material/science:",
            )
    st.markdown("**Challenges in the plausibility analysis**")
    st.markdown(
        "- Only 70 expert-scored incidents exist, and they are hypothetical; importance estimates carry wide uncertainty and say what the experts' scores look like, not what works in the field.\n"
        "- The shoreline model has no expert-labelled data, so its check is against documented guidance, not against measured outcomes.\n"
        "- Permutation importance and SHAP both describe the model, not nature; correlated inputs can share credit.\n"
        "- The SCAT checks use a handful of qualitative statements from the cited sources, so a pass shows consistency with those statements only."
    )


def render_validation_tab() -> None:
    st.subheader("Validation: what was tested, what held up, and what did not")
    st.warning(
        "Read this before relying on any recommendation. The model is a screening prototype. The checks below test it against the "
        "published paper's dataset and against a small set of cited historical decisions; they do not establish operational validity.",
        icon=":material/rule:",
    )

    metrics = _read(HIST / "metrics.csv")
    results = _read(HIST / "inference_results.csv")

    # ---- Section 1: reproduction
    st.markdown("### 1. Reproduction of the published machine-learning study")
    st.write(
        "Reference: Mohammadiun et al. (2022), *J. Hazard. Mater.* 436:129282, and the UBC thesis that holds its dataset (Appendix C). "
        "That study selects between three **offshore** response methods (mechanical containment and recovery, in-situ burning, dispersants) "
        "from six slick and sea-state factors. It is **not** a shoreline-cleanup model, so this tests the model families, not the shoreline decision logic."
    )
    comparison = _read(REPRO / "metric_comparison.csv")
    if comparison is None:
        st.info("Run validation/reproduction_validation.py to generate the reproduction results.")
    else:
        view = comparison[(comparison["input_mode"] == "fuzzy") & (comparison["metric"].isin(["test_acc", "train_acc", "test_r", "test_mse"]))].copy()
        view["metric"] = view["metric"].map({"test_acc": "Testing accuracy (%)", "train_acc": "Training accuracy (%)", "test_r": "Testing correlation", "test_mse": "Testing MSE (0-1 scale)"})
        view = view.rename(columns={"model": "Model", "paper": "Paper", "reproduced": "Reproduced", "reproduced_sd": "SD across splits", "relative_difference_pct": "Difference (%)", "classification": "Verdict", "metric": "Metric"})
        st.dataframe(view[["Model", "Metric", "Paper", "Reproduced", "SD across splits", "Difference (%)", "Verdict"]], hide_index=True, use_container_width=True)
        st.caption("Difference (%) = |paper - reproduced| / paper x 100. Under 5 % excellent, 5-10 % acceptable, over 10 % requires investigation. Fuzzified inputs shown, as the paper states.")
        chart = REPRO / "paper_vs_reproduced_test_accuracy.png"
        if chart.exists():
            st.image(str(chart), use_container_width=True)
        good = comparison[(comparison["input_mode"] == "fuzzy") & (comparison["model"].isin(["GPR", "SVR"])) & (comparison["metric"].isin(["test_acc", "test_r"]))]
        ann = comparison[(comparison["input_mode"] == "fuzzy") & (comparison["model"] == "ANN-GD") & (comparison["metric"] == "test_acc")]
        if len(good) and len(ann):
            st.success(f"GPR and SVR reproduce the paper's testing accuracy and correlation within {good['relative_difference_pct'].max():.1f} %.", icon=":material/check_circle:")
            st.error(f"ANN-GD does not: testing accuracy differs by {ann['relative_difference_pct'].iloc[0]:.0f} % (the reproduction trains better than the paper reports).", icon=":material/error:")
    items = _read(REPRO / "item_comparison.csv")
    if items is not None:
        with st.expander("Item-by-item comparison with the paper (inputs, preprocessing, split, hyperparameters, metrics)"):
            st.dataframe(items, hide_index=True, use_container_width=True)

    st.markdown("**Challenges in the reproduction**")
    st.markdown(
        "- Four of the paper's seven models (ANN-LM, ANN-BR, FDT-LR, OFDTs) have no scikit-learn equivalent and are not reproduced.\n"
        "- The paper does not state SVR's C and epsilon, GPR's basis function, or whether fuzzy inputs means 6 or 18 values; these were assumed and both input readings are reported.\n"
        "- Two settings were changed after a pilot run (a noise term for GPR; [-1, 1] scaling for ANN-GD). The GPR change was informed by the paper's training accuracy, so GPR's close match is partly tuned.\n"
        "- The paper's ranking of models is not statistically supported: plain linear regression scores about the same as GPR, and test scores vary by roughly 7 points across splits of only 21 test incidents.\n"
        "- 500 splits were run (150 for neural networks) rather than the paper's 10,000."
    )

    # ---- Section 2: historical
    st.markdown("### 2. Historical case studies")
    cases = _read(HIST / "historical_cases.csv")
    if cases is None or results is None or metrics is None:
        st.info("Run validation/historical_validation.py to generate the historical validation results.")
    else:
        sourced = cases[cases["Documented_Response"] != "NOT_SOURCED"]
        unsourced = cases[cases["Documented_Response"] == "NOT_SOURCED"]
        n_cases = int(float(_metric_value(metrics, "n_cases", 0)))
        agree = int(float(_metric_value(metrics, "class_agreement", 0)))
        base = float(_metric_value(metrics, "always_active_baseline_agreement", np.nan))
        distinct = int(float(_metric_value(metrics, "distinct_top1_predictions_across_cases", 0)))
        rank = float(_metric_value(metrics, "mean_median_best_documented_rank", np.nan))
        rank_random = float(_metric_value(metrics, "random_ordering_expected_rank", np.nan))
        n_rank = int(float(_metric_value(metrics, "n_ranked_treatments", 15)))
        st.markdown(f"**The model agreed with the documented active-versus-natural decision in {agree} of {n_cases} cases.**")
        st.error(
            f"This is no better than a model that always answers 'active cleanup' ({base:.0%} of the documented decisions were active). "
            f"The model returned {distinct} distinct top-ranked treatment across {n_cases} different shorelines, including a marsh and a rocky shore. "
            f"The documented method sat at an average rank of {rank:.1f} of {n_rank} (random ordering would give about {rank_random:.1f}).",
            icon=":material/warning:",
        )
        columns = st.columns(4)
        for column, (label, key) in zip(columns, [("Class agreement", "class_agreement_rate"), ("Precision (active)", "precision_active"), ("Recall (active)", "recall_active"), ("F1 (active)", "f1_active")]):
            value = float(_metric_value(metrics, key, np.nan))
            column.metric(label, f"{value:.0%}" if value == value else "n/a")
        st.caption(f"With only {n_cases} cases, precision, recall and F1 carry very wide uncertainty (95 % interval for class agreement: {_metric_value(metrics, 'class_agreement_ci95', 'n/a')}). Treat them as a diagnostic, not a score.")
        image = HIST / "historical_agreement.png"
        if image.exists():
            st.image(str(image), use_container_width=True)
        st.markdown("**Case table (every value is cited; blanks mean the source does not state it)**")
        st.dataframe(sourced.drop(columns=[], errors="ignore"), hide_index=True, use_container_width=True)
        if len(unsourced):
            st.info(f"{len(unsourced)} spills requested in the plan have no usable source retrieved and are kept as NOT_SOURCED rows rather than filled in: {', '.join(unsourced['Spill_Name'])}.")
        with st.expander("Traceability matrix: source, extracted variable, mapped model variable, confidence"):
            trace = _read(HIST / "traceability_matrix.csv")
            if trace is not None:
                counts = trace["Confidence"].value_counts()
                st.write("Confidence counts: " + ", ".join(f"{k} = {v}" for k, v in counts.items()) + ". High = directly reported; Medium = inferred from a documented shoreline description; Low = not stated (sampled over a plausible range).")
                st.dataframe(trace, hide_index=True, use_container_width=True)
        with st.expander("Failure analysis"):
            failures = _read(HIST / "failure_analysis.csv")
            if failures is not None and len(failures):
                st.dataframe(failures, hide_index=True, use_container_width=True)
            else:
                st.write("No failures recorded.")
        with st.expander("Sources"):
            sources = _read(HIST / "sources.csv")
            if sources is not None:
                st.dataframe(sources, hide_index=True, use_container_width=True)
        st.markdown("**Challenges in the historical validation**")
        st.markdown(
            "- Documented responses are qualitative (for example 'manual and mechanical cleanup'), so agreement is judged by method class and by whether the documented method appears in the model's ranking.\n"
            "- Sources rarely state oil coverage, penetration, exposure or sensitivity. These were sampled (40 Latin-hypercube draws per case) instead of fixed, so results show robustness to missing information.\n"
            "- Ten of the fifteen treatments have no trained suitability model and receive a constant score of 5.0, which limits how much the ranking can discriminate between shorelines.\n"
            "- Real responses also weighed net environmental benefit, access, waste and seasonal use, none of which the model has as inputs.\n"
            "- Prestige, Sea Empress and Wakashio could not be sourced here (ITOPF was unavailable; Europe PMC returned unrelated papers)."
        )

    # ---- Section 3: scientific plausibility
    st.markdown("### 3. Scientific plausibility of the learned relationships")
    _render_plausibility()

    # ---- Section 4: process model basis
    st.markdown("### 4. Process-model basis for marshes and complex shorelines")
    st.write(
        "The earlier process model used open-water oil-spill (DHI) kinetics, which describe slicks on the sea surface. "
        "It is replaced by a cross-shore advection-dispersion-reaction model of oil in shoreline sediment: "
        "tidal and swash dispersion with a retention (retardation) term for vegetation and soil, evaporation, infiltration, "
        "and biodegradation with multiplicative Monod oxygen and nutrient limits."
    )
    st.latex(r"R_i\,\frac{\partial C_i}{\partial t} = D_i\,\frac{\partial^2 C_i}{\partial x^2} - \left(k_{evap}+k_{inf,i}+k_{bio}\,\frac{O_i}{K_O+O_i}\,\frac{N_i}{K_N+N_i}+k_{treat}\right) C_i")
    st.dataframe(pd.DataFrame(LITERATURE, columns=["Reference", "Title", "Evidence status here", "What it contributes"]), hide_index=True, use_container_width=True)
    st.info(
        "No off-the-shelf, verified model of oil transport inside marsh interiors was found. The beach reactive-transport family (Geng and Boufadel) is the closest "
        "established basis; marsh retention and dispersion magnitudes are unpublished in the material read, so they are assumed and flagged.",
        icon=":material/science:",
    )
    from src.shoreline_remediation.shoreline_transport import PARAMETER_TABLE

    parameters = pd.DataFrame(PARAMETER_TABLE, columns=["Parameter", "Value used", "Status", "Basis"])
    st.dataframe(parameters, hide_index=True, use_container_width=True)
    sourced_count = int((parameters["Status"] == "SOURCED").sum())
    st.caption(f"{sourced_count} of {len(parameters)} parameters are taken from documents read; the rest are screening placeholders that must be calibrated to repeat SCAT observations before the process outputs are used for decisions.")

    st.markdown("### 5. Recommended next steps")
    st.markdown(
        "1. Collect expert scores for all 15 treatments (docs/EXPERT_SCORING_PROTOCOL.md); six treatments have no suitability labels and are listed after the scored ones. Then re-run the historical check.\n"
        "2. Add inputs the real responses used (net environmental benefit, access, waste, season) and a 'natural recovery' decision threshold.\n"
        "3. Source Prestige, Sea Empress and Wakashio from their agency reports and add them with the same traceability matrix.\n"
        "4. Calibrate the transport model's retention, dispersion and rate parameters against the Deepwater Horizon marsh and beach SCAT time series.\n"
        "5. Re-run validation/feature_validation.py after retraining and confirm the SCAT checks in section 3 pass."
    )
