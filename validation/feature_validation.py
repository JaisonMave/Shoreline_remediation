"""Phase 3: scientific plausibility of learned relationships (permutation importance + SHAP vs documented logic).

Part A uses the only expert-labelled data available (Mohammadiun 2022, Appendix C) and checks the
learned drivers against the paper's own Table 1 favourable conditions.
Part B probes the shoreline hybrid model itself against SCAT / NOAA guidance already cited in the
historical module, and audits what its synthetic training target can possibly teach.
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RepeatedKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.data_model import TREATMENT_LIBRARY, Scenario  # noqa: E402
from src.shoreline_remediation.decision_framework import HybridDecisionModel  # noqa: E402
from src.shoreline_remediation.ml_models import make_synthetic_dataset  # noqa: E402
from validation.paper_dataset import FEATURES, TARGETS, load_dataset  # noqa: E402
from validation.reproduction_validation import make_estimator  # noqa: E402

RESULTS_DIR = ROOT / "results" / "explainability"
DRIVER_MIN_SHARE = 0.08
UNEXPECTED_MIN_SHARE = 0.25
SIGN_MIN_RHO = 0.20

# Paper Table 1 (Hu et al. 2020 via Mohammadiun 2022): favourable conditions per method.
# driver+/driver-: monotone driver; none: "not sensitive"; threshold: only a minimum is required
# (>= 0.1 mm, always met in the data range); window: favourable band, sign not testable.
PAPER_EXPECTATION = {
    ("MCR", "oil_api"): ("none", "Table 1: not sensitive"),
    ("MCR", "slick_thickness_mm"): ("threshold", "Table 1: needs >= 0.1 mm only"),
    ("MCR", "slick_continuity_pct"): ("none", "Table 1: not sensitive"),
    ("MCR", "wave_height_m"): ("driver-", "Table 1: favourable <= 1 m"),
    ("MCR", "remoteness_km"): ("driver-", "Table 1: negatively affected"),
    ("MCR", "sea_ice_pct"): ("driver-", "Table 1: negatively affected"),
    ("ISB", "oil_api"): ("none", "Table 1: not sensitive"),
    ("ISB", "slick_thickness_mm"): ("driver+", "Table 1: favourable >= 2-3 mm"),
    ("ISB", "slick_continuity_pct"): ("driver+", "Table 1: sensitive (required)"),
    ("ISB", "wave_height_m"): ("driver-", "Table 1: favourable <= 1 m"),
    ("ISB", "remoteness_km"): ("none", "Table 1: not sensitive"),
    ("ISB", "sea_ice_pct"): ("none", "Table 1: not sensitive"),
    ("UCD", "oil_api"): ("driver+", "Table 1: favourable API >= 22 (light oils)"),
    ("UCD", "slick_thickness_mm"): ("driver-", "Table 1: favourable 0.02-1 mm (thin slicks)"),
    ("UCD", "slick_continuity_pct"): ("none", "Table 1: not sensitive"),
    ("UCD", "wave_height_m"): ("window", "Table 1: favourable 0.2-3 m (band, no monotone sign)"),
    ("UCD", "remoteness_km"): ("none", "Table 1: not sensitive"),
    ("UCD", "sea_ice_pct"): ("driver-", "Table 1: negatively affected"),
}

SH_FEATURES = [
    "shoreline_type", "shoreline_sensitivity", "oil_category", "oil_coverage", "oil_thickness",
    "penetration_depth_cm", "wave_exposure", "surface_oil", "accessibility", "substrate_permeability",
    "tidal_range", "temperature_c", "season", "habitat_type", "recovery_potential", "waste_handling",
]
CATEGORICAL = {
    "shoreline_type": ["sand_beach", "mixed_sediment", "marsh", "bedrock", "mudflat", "cobble"],
    "shoreline_sensitivity": ["low", "moderate", "high", "very_high"],
    "oil_category": ["light", "medium", "heavy", "solid"],
    "wave_exposure": ["low", "moderate", "high"],
    "accessibility": ["good", "limited", "poor"],
    "substrate_permeability": ["low", "moderate", "high"],
    "tidal_range": ["low", "moderate", "high"],
    "season": ["spring", "summer", "autumn", "winter"],
    "habitat_type": ["mixed_sediment", "vegetated", "rocky", "sandy"],
    "recovery_potential": ["low", "moderate", "high"],
    "waste_handling": ["limited", "manageable", "good"],
}
NUMERIC = {
    "oil_coverage": (5.0, 90.0), "oil_thickness": (0.5, 25.0),
    "penetration_depth_cm": (0.0, 25.0), "temperature_c": (0.0, 30.0),
}
ML_INPUTS = {"shoreline_type", "oil_category", "oil_coverage", "oil_thickness", "penetration_depth_cm",
             "wave_exposure", "shoreline_sensitivity", "surface_oil"}
TRAINED = ["natural_attenuation", "manual_removal", "vacuum_removal", "mechanical_removal", "high_pressure_washing"]


# ---------------------------------------------------------------- Part A: paper dataset
def permutation_importance_cv(X, Y, name, n_splits=5, n_repeats=6, shuffles=10, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for fold, (tr, te) in enumerate(RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=seed).split(X)):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if name == "Random forest":
                model = RandomForestRegressor(n_estimators=150, random_state=seed + fold, n_jobs=1).fit(X[tr], Y[tr])
            else:
                model = make_estimator("GPR (SE kernel)", seed + fold, "crisp").fit(X[tr], Y[tr])
            base = ((model.predict(X[te]) - Y[te]) ** 2).mean(axis=0)
            for j, feature in enumerate(FEATURES):
                increase = np.zeros(Y.shape[1])
                for _ in range(shuffles):
                    Xp = X[te].copy()
                    Xp[:, j] = rng.permutation(Xp[:, j])
                    increase += ((model.predict(Xp) - Y[te]) ** 2).mean(axis=0) - base
                for k, target in enumerate(TARGETS):
                    rows.append(dict(model=name, fold=fold, output=target, feature=feature, mse_increase=increase[k] / shuffles))
    frame = pd.DataFrame(rows)
    summary = frame.groupby(["model", "output", "feature"])["mse_increase"].agg(["mean", "std"]).reset_index()
    summary["importance"] = summary["mean"].clip(lower=0)
    summary["share"] = summary["importance"] / summary.groupby(["model", "output"])["importance"].transform("sum")
    summary["rank"] = summary.groupby(["model", "output"])["importance"].rank(ascending=False, method="min").astype(int)
    return summary.rename(columns={"mean": "mse_increase_mean", "std": "mse_increase_sd"})


def oof_shap(X, Y, n_splits=5, seed=7):
    """TreeSHAP of a random forest, computed only on held-out rows (every row explained out-of-fold)."""
    shap_values = np.zeros((len(X), X.shape[1], Y.shape[1]))
    order = np.random.default_rng(seed).permutation(len(X))
    for te in np.array_split(order, n_splits):
        tr = np.setdiff1d(order, te)
        forest = RandomForestRegressor(n_estimators=200, random_state=seed, n_jobs=1).fit(X[tr], Y[tr])
        values = shap.TreeExplainer(forest).shap_values(X[te])
        values = np.stack(values, axis=-1) if isinstance(values, list) else np.asarray(values)
        shap_values[te] = values
    return shap_values


def paper_expectation_check(importance: pd.DataFrame, shap_values, X, Y) -> pd.DataFrame:
    rows = []
    for k, target in enumerate(TARGETS):
        for j, feature in enumerate(FEATURES):
            expectation, basis = PAPER_EXPECTATION[(target, feature)]
            shares = importance[(importance["output"] == target) & (importance["feature"] == feature)].set_index("model")["share"]
            share = float(shares.mean())
            rho_shap = float(spearmanr(X[:, j], shap_values[:, j, k]).statistic)
            rho_data = float(spearmanr(X[:, j], Y[:, k]).statistic)
            expected_sign = {"driver+": 1, "driver-": -1}.get(expectation)
            if expectation in {"driver+", "driver-"}:
                if share < DRIVER_MIN_SHARE:
                    verdict = "Expected driver not learned"
                elif abs(rho_shap) >= SIGN_MIN_RHO and np.sign(rho_shap) != expected_sign:
                    verdict = "Opposite direction to documented logic"
                else:
                    verdict = "Consistent"
            elif expectation in {"none", "threshold"}:
                verdict = "Unexpected driver (not in documented logic)" if share > UNEXPECTED_MIN_SHARE else "Consistent"
            else:
                verdict = "Not tested (band effect)"
            rows.append(dict(
                output=target, feature=feature, documented_expectation=expectation, basis=basis,
                gpr_share=float(shares.get("GPR", np.nan)), rf_share=float(shares.get("Random forest", np.nan)),
                mean_share=share, spearman_feature_vs_shap=rho_shap, spearman_feature_vs_expert_score=rho_data,
                mean_abs_shap=float(np.abs(shap_values[:, j, k]).mean()), verdict=verdict))
    return pd.DataFrame(rows)


def plot_paper(importance: pd.DataFrame, shap_values, X) -> None:
    sns.set_theme(style="white", context="paper", font_scale=1.15)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, model in zip(axes, ["GPR", "Random forest"]):
        grid = importance[importance["model"] == model].pivot(index="feature", columns="output", values="share").loc[FEATURES, TARGETS]
        sns.heatmap(grid, annot=True, fmt=".2f", cmap="YlGnBu", vmin=0, vmax=0.6, cbar=model != "GPR", ax=ax,
                    cbar_kws={"label": "Share of permutation importance"})
        ax.set_title(f"{model}")
        ax.set_xlabel("")
        ax.set_ylabel("")
    fig.suptitle("Permutation importance on held-out folds (Mohammadiun 2022 dataset, crisp inputs)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "paper_permutation_importance.png", dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    rng = np.random.default_rng(0)
    for k, (ax, target) in enumerate(zip(axes, TARGETS)):
        order = np.argsort(np.abs(shap_values[:, :, k]).mean(axis=0))
        for position, j in enumerate(order):
            column = X[:, j]
            colour = (column - column.min()) / (np.ptp(column) or 1.0)
            ax.scatter(shap_values[:, j, k], position + rng.uniform(-0.25, 0.25, len(column)), c=colour,
                       cmap="coolwarm", s=14, alpha=0.85, linewidths=0)
        ax.set_yticks(range(len(order)), [FEATURES[j] for j in order])
        ax.axvline(0, color="grey", lw=0.8)
        ax.set_title(f"{target} suitability")
        ax.set_xlabel("SHAP value (score points)")
    sm = plt.cm.ScalarMappable(cmap="coolwarm")
    fig.colorbar(sm, ax=axes, label="Feature value (low to high)", fraction=0.02)
    fig.suptitle("Out-of-fold SHAP values, random forest, 70 expert-scored incidents")
    fig.savefig(RESULTS_DIR / "paper_shap_beeswarm.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Part B: shoreline model
def random_scenarios(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = {name: rng.choice(options, n) for name, options in CATEGORICAL.items()}
    for name, (low, high) in NUMERIC.items():
        data[name] = np.round(rng.uniform(low, high, n), 1)
    data["surface_oil"] = rng.random(n) < 0.8
    return pd.DataFrame(data)[SH_FEATURES]


def to_scenario(row) -> Scenario:
    values = {k: (bool(v) if k == "surface_oil" else float(v) if k in NUMERIC else str(v)) for k, v in row.items()}
    return Scenario(**values)


def score_table(model: HybridDecisionModel, frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, row in enumerate(frame.to_dict("records")):
        for score in model.rank_treatments(to_scenario(row)):
            rows.append(dict(scenario=index, treatment=score.treatment, utility=score.utility, suitability=score.suitability,
                             ecological=score.ecological_suitability, feasibility=score.feasibility))
    table = pd.DataFrame(rows)
    table["rank"] = table.groupby("scenario")["utility"].rank(ascending=False, method="first")
    return table


def shoreline_permutation(model, frame, repeats, seed):
    base = score_table(model, frame).set_index(["scenario", "treatment"]).sort_index()
    top1 = base[base["rank"] == 1].reset_index().set_index("scenario")["treatment"]
    rng = np.random.default_rng(seed)
    rows = []
    for feature in SH_FEATURES:
        parts = []
        for _ in range(repeats):
            shuffled = frame.copy()
            shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
            new = score_table(model, shuffled).set_index(["scenario", "treatment"]).sort_index().reindex(base.index)
            top_new = new[new["rank"] == 1].reset_index().set_index("scenario")["treatment"]
            parts.append(dict(
                mean_abs_utility_change=float((new["utility"] - base["utility"]).abs().mean()),
                mean_abs_suitability_change=float((new.loc[new.index.get_level_values(1).isin(TRAINED), "suitability"]
                                                   - base.loc[base.index.get_level_values(1).isin(TRAINED), "suitability"]).abs().mean()),
                mean_abs_ecological_change=float((new["ecological"] - base["ecological"]).abs().mean()),
                feasibility_class_change=float((new["feasibility"] != base["feasibility"]).mean()),
                mean_rank_shift=float((new["rank"] - base["rank"]).abs().mean()),
                top1_change=float((top_new != top1.reindex(top_new.index)).mean())))
        rows.append(dict(feature=feature, **pd.DataFrame(parts).mean().to_dict()))
    result = pd.DataFrame(rows)
    result["used_by"] = [
        "FAST rules + ML + ecological" if f in ML_INPUTS else ("FAST rules" if f in {"accessibility", "substrate_permeability"} else "not used by ranking")
        for f in result["feature"]]
    return result.sort_values("mean_rank_shift", ascending=False).reset_index(drop=True)


def encode(frame: pd.DataFrame) -> np.ndarray:
    columns = []
    for name in SH_FEATURES:
        if name in CATEGORICAL:
            columns.append(frame[name].map({v: i for i, v in enumerate(CATEGORICAL[name])}).to_numpy(float))
        else:
            columns.append(frame[name].astype(float).to_numpy())
    return np.column_stack(columns)


def decode(matrix: np.ndarray) -> list[Scenario]:
    scenarios = []
    for row in np.atleast_2d(matrix):
        values = {}
        for name, value in zip(SH_FEATURES, row):
            if name in CATEGORICAL:
                values[name] = CATEGORICAL[name][int(round(np.clip(value, 0, len(CATEGORICAL[name]) - 1)))]
            elif name == "surface_oil":
                values[name] = bool(round(value))
            else:
                values[name] = float(value)
        scenarios.append(Scenario(**values))
    return scenarios


def shoreline_shap(model, frame, treatments, n_explain, n_background, seed):
    X = encode(frame)
    rows, store = [], {}
    for treatment in treatments:
        def predict(matrix, treatment=treatment):
            return np.array([model.score_treatment(s, treatment).utility for s in decode(matrix)])
        explainer = shap.PermutationExplainer(predict, X[:n_background], seed=seed)
        values = explainer(X[n_background:n_background + n_explain], max_evals=2 * X.shape[1] + 1, silent=True).values
        store[treatment] = (X[n_background:n_background + n_explain], values)
        for j, feature in enumerate(SH_FEATURES):
            rows.append(dict(treatment=treatment, feature=feature, mean_abs_shap=float(np.abs(values[:, j]).mean())))
    summary = pd.DataFrame(rows)
    summary["share"] = summary["mean_abs_shap"] / summary.groupby("treatment")["mean_abs_shap"].transform("sum")
    return summary, store


def eta_squared(feature: pd.Series, target: pd.Series) -> float:
    groups = feature if feature.dtype == object else pd.qcut(feature, 5, duplicates="drop")
    total = ((target - target.mean()) ** 2).sum()
    between = sum(len(g) * (g.mean() - target.mean()) ** 2 for _, g in target.groupby(groups, observed=True))
    return float(between / total) if total else 0.0


def training_target_audit() -> pd.DataFrame:
    data = make_synthetic_dataset(n_rows=220)
    inputs = ["shoreline_type", "oil_category", "oil_coverage", "oil_thickness", "penetration_depth_cm",
              "wave_exposure", "shoreline_sensitivity", "surface_oil"]
    rows = []
    for treatment in TRAINED:
        for feature in inputs:
            series = data[feature].astype(object) if feature in CATEGORICAL or feature == "surface_oil" else data[feature]
            rows.append(dict(treatment=treatment, feature=feature, variance_explained_eta2=eta_squared(series, data[treatment])))
    return pd.DataFrame(rows)


def scat_checks(model, seed, n=60) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = dict(shoreline_type="marsh", oil_category="heavy", surface_oil=True)

    def draw(**fixed):
        values = {**base, **fixed}
        return Scenario(shoreline_type=values["shoreline_type"], oil_category=values["oil_category"],
                        shoreline_sensitivity=values.get("shoreline_sensitivity", str(rng.choice(CATEGORICAL["shoreline_sensitivity"]))),
                        oil_coverage=float(values.get("oil_coverage", rng.uniform(20, 90))),
                        oil_thickness=float(values.get("oil_thickness", rng.uniform(1, 25))),
                        penetration_depth_cm=float(values.get("penetration_depth_cm", rng.uniform(0, 10))),
                        wave_exposure=values.get("wave_exposure", str(rng.choice(["low", "moderate"]))),
                        surface_oil=values["surface_oil"])

    def utility(scenarios, treatment):
        return float(np.mean([model.score_treatment(s, treatment).utility for s in scenarios]))

    def mean_rank(scenarios, treatment):
        return float(np.mean([[r.treatment for r in model.rank_treatments(s)].index(treatment) + 1 for s in scenarios]))

    rows = []
    low = [draw(shoreline_sensitivity="low") for _ in range(n)]
    high = [draw(shoreline_sensitivity="very_high") for _ in range(n)]
    u_low, u_high = utility(low, "natural_attenuation"), utility(high, "natural_attenuation")
    rows.append(dict(check="E1 Natural attenuation preferred more as marsh sensitivity rises",
                     basis="S1: natural attenuation often recommended in marsh; S4 ESI 10A: aggressive cleanup only when other resources at great risk",
                     expected="utility(very_high) > utility(low)", observed=f"{u_high:.2f} vs {u_low:.2f} (very_high vs low)",
                     verdict="PASS" if u_high > u_low + 0.05 else "FAIL"))

    marsh = [draw() for _ in range(n)]
    intrusive = ["high_pressure_washing", "high_pressure_heated_washing", "mechanical_removal"]
    share = float(np.mean([any(r.treatment in intrusive for r in model.rank_treatments(s)[:3]) for s in marsh]))
    rows.append(dict(check="E2 Intrusive methods not in the top 3 for heavily oiled marsh",
                     basis="S4 ESI 10A / S1: intrusive treatment avoided where it causes further damage",
                     expected="share of marsh scenarios with an intrusive method in top 3 is low (< 0.20)",
                     observed=f"{share:.2f}", verdict="PASS" if share < 0.20 else "FAIL"))

    thin = [draw(oil_thickness=2.0) for _ in range(n)]
    thick = [draw(oil_thickness=25.0) for _ in range(n)]
    changed = float(np.mean([[r.treatment for r in model.rank_treatments(a)] != [r.treatment for r in model.rank_treatments(b)]
                             for a, b in zip(thin, thick)]))
    na_thin, na_thick = mean_rank(thin, "natural_attenuation"), mean_rank(thick, "natural_attenuation")
    rows.append(dict(check="E3 Thick oil (> 1 cm) should push ranking away from natural attenuation",
                     basis="S1: marsh endpoints require no thick (> 1 cm) oil, so thick oil triggers treatment",
                     expected="natural attenuation rank worsens (number rises) when thickness 2 mm -> 25 mm",
                     observed=f"rank {na_thin:.2f} -> {na_thick:.2f}; ranking identical in {1 - changed:.0%} of paired cases",
                     verdict="PASS" if na_thick > na_thin + 0.25 else "FAIL"))

    surface = [draw(penetration_depth_cm=0.0) for _ in range(n)]
    buried = [draw(penetration_depth_cm=30.0) for _ in range(n)]
    same = float(np.mean([[r.treatment for r in model.rank_treatments(a)][:3] == [r.treatment for r in model.rank_treatments(b)][:3]
                          for a, b in zip(surface, buried)]))
    rows.append(dict(check="E4 Buried oil (30 cm vs surface-only) should change the recommended methods",
                     basis="S1 (DWH-05): buried oil required excavation / sieving, not surface methods",
                     expected="top-3 methods differ in most paired scenarios (identical share < 0.5)",
                     observed=f"top-3 identical in {same:.0%} of paired cases", verdict="PASS" if same < 0.5 else "FAIL"))

    rock = [Scenario(shoreline_type="bedrock", oil_category="heavy", oil_coverage=float(rng.uniform(20, 90)),
                     oil_thickness=float(rng.uniform(1, 15)), penetration_depth_cm=0.0,
                     shoreline_sensitivity=str(rng.choice(["low", "moderate"])), wave_exposure="moderate") for _ in range(n)]
    sand = [Scenario(shoreline_type="sand_beach", oil_category="heavy", oil_coverage=float(rng.uniform(20, 90)),
                     oil_thickness=float(rng.uniform(1, 15)), penetration_depth_cm=0.0,
                     shoreline_sensitivity=str(rng.choice(["low", "moderate"])), wave_exposure="moderate") for _ in range(n)]
    r_rock, r_sand = mean_rank(rock, "high_pressure_washing"), mean_rank(sand, "high_pressure_washing")
    rows.append(dict(check="E5 High-pressure washing ranks better on bedrock than on sand",
                     basis="S3: hot/high-pressure washing is a viable method for hard surfaces such as large rocks and seawalls",
                     expected="mean rank on bedrock < mean rank on sand beach", observed=f"{r_rock:.2f} vs {r_sand:.2f}",
                     verdict="PASS" if r_rock < r_sand - 0.25 else "FAIL"))
    return pd.DataFrame(rows)


def plot_shoreline(importance: pd.DataFrame, shap_summary: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.15)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    ordered = importance.sort_values("mean_rank_shift")
    colours = ordered["used_by"].map({"FAST rules + ML + ecological": "#176b87", "FAST rules": "#db8b3e", "not used by ranking": "#b0b0b0"})
    axes[0].barh(ordered["feature"], ordered["mean_rank_shift"], color=colours)
    axes[0].set_xlabel("Mean rank shift of a treatment when the input is shuffled")
    axes[0].set_title("Permutation importance on the full 15-treatment ranking")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#176b87", "#db8b3e", "#b0b0b0"]]
    axes[0].legend(handles, ["FAST + ML + ecological", "FAST rules only", "not used by ranking"], frameon=False, loc="lower right")
    grid = shap_summary.pivot(index="feature", columns="treatment", values="share").loc[SH_FEATURES]
    sns.heatmap(grid, annot=True, fmt=".2f", cmap="YlGnBu", vmin=0, ax=axes[1], cbar_kws={"label": "Share of mean |SHAP|"})
    axes[1].set_title("SHAP share per treatment utility")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "shoreline_feature_importance.png", dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=int, default=120)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--shap-explain", type=int, default=40)
    parser.add_argument("--shap-background", type=int, default=15)
    parser.add_argument("--paper-only", action="store_true", help="Skip the shoreline-model analysis")
    args = parser.parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    data = load_dataset()
    X, Y = data[FEATURES].to_numpy(float), data[TARGETS].to_numpy(float)
    importance = pd.concat([permutation_importance_cv(X, Y, "GPR"), permutation_importance_cv(X, Y, "Random forest")], ignore_index=True)
    shap_values = oof_shap(X, Y)
    check = paper_expectation_check(importance, shap_values, X, Y)
    importance.to_csv(RESULTS_DIR / "paper_permutation_importance.csv", index=False)
    check.to_csv(RESULTS_DIR / "paper_expectation_check.csv", index=False)
    shap_table = pd.DataFrame(
        [dict(output=t, feature=f, mean_abs_shap=float(np.abs(shap_values[:, j, k]).mean()))
         for k, t in enumerate(TARGETS) for j, f in enumerate(FEATURES)])
    shap_table.to_csv(RESULTS_DIR / "paper_shap_summary.csv", index=False)
    plot_paper(importance, shap_values, X)
    print("PART_A_DONE", round(time.time() - started, 1), "s")
    print(check.groupby("verdict").size().to_string())
    if args.paper_only:
        return

    model = HybridDecisionModel()
    model.train_treatment_models()
    frame = random_scenarios(args.scenarios + args.shap_background, seed=5)
    importance_b = shoreline_permutation(model, frame.iloc[:args.scenarios].reset_index(drop=True), args.repeats, seed=5)
    importance_b.to_csv(RESULTS_DIR / "shoreline_permutation_importance.csv", index=False)
    print("PART_B_PERM_DONE", round(time.time() - started, 1), "s")
    shap_summary, _ = shoreline_shap(model, frame, ["natural_attenuation", "manual_removal", "high_pressure_washing"],
                                     args.shap_explain, args.shap_background, seed=5)
    shap_summary.to_csv(RESULTS_DIR / "shoreline_shap_summary.csv", index=False)
    training_target_audit().to_csv(RESULTS_DIR / "shoreline_training_target_audit.csv", index=False)
    checks = scat_checks(model, seed=5)
    checks.to_csv(RESULTS_DIR / "shoreline_scat_checks.csv", index=False)
    plot_shoreline(importance_b, shap_summary)
    print("PART_B_DONE", round(time.time() - started, 1), "s")
    print(importance_b.to_string())
    print(checks[["check", "observed", "verdict"]].to_string())


if __name__ == "__main__":
    main()
