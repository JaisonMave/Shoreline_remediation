"""Phase 1: reproduction validation against Mohammadiun et al. (2022), J. Hazard. Mater. 436:129282.

Runs the paper's protocol (random 70/30 split, repeated, top-method accuracy, Pearson r, MSE on
0-1 scores) on the paper's 70-incident dataset and compares with the published Tables 3 and 4.
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import SVR
from xgboost import XGBRegressor

from validation.paper_dataset import FEATURES, TARGETS, load_dataset, verify_dataset

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "reproduction"
TRAIN_FRACTION = 0.70
BASE_SEED = 2022

# Table 2 of the paper: (left foot, peak, right foot) of triangular membership functions.
MEMBERSHIPS = {
    "oil_api": {"low": (45, 45, 30), "medium": (45, 30, 15), "high": (30, 15, 15)},
    "slick_thickness_mm": {"low": (0.1, 0.1, 1.5), "medium": (0.1, 1.5, 3), "high": (1.5, 3, 3)},
    "slick_continuity_pct": {"low": (30, 30, 60), "medium": (30, 60, 90), "high": (60, 90, 90)},
    "wave_height_m": {"low": (0, 0, 0.75), "medium": (0, 0.75, 1.5), "high": (0.75, 1.5, 1.5)},
    "remoteness_km": {"low": (100, 100, 300), "medium": (100, 300, 500), "high": (300, 500, 500)},
    "sea_ice_pct": {"low": (0, 0, 10), "medium": (0, 10, 20), "high": (10, 20, 20)},
}

# Paper Table 3 (accuracy, %) and Table 4 (Pearson r, MSE on 0-1 scores).
PAPER = {
    "GPR": {"train_acc": 93.49, "test_acc": 80.93, "train_r": 0.976, "test_r": 0.884, "train_mse": 0.003, "test_mse": 0.016},
    "SVR": {"train_acc": 86.39, "test_acc": 80.30, "train_r": 0.919, "test_r": 0.867, "train_mse": 0.011, "test_mse": 0.018},
    "ANN-GD": {"train_acc": 70.80, "test_acc": 60.20, "train_r": 0.720, "test_r": 0.555, "train_mse": 0.046, "test_mse": 0.076},
    "ANN-LM": {"train_acc": 82.54, "test_acc": 68.84, "train_r": 0.865, "test_r": 0.689, "train_mse": 0.019, "test_mse": 0.046},
    "ANN-BR": {"train_acc": 90.01, "test_acc": 77.98, "train_r": 0.954, "test_r": 0.845, "train_mse": 0.008, "test_mse": 0.025},
    "FDT-LR": {"train_acc": 78.94, "test_acc": 72.29},
    "OFDTs": {"train_acc": 84.57, "test_acc": 85.60},
}
PAPER_MAP = {"GPR (SE kernel)": "GPR", "SVR linear (paper)": "SVR", "ANN-GD (paper)": "ANN-GD"}
MODELS = [
    "GPR (SE kernel)", "SVR linear (paper)", "ANN-GD (paper)",
    "SVM-RBF (project)", "ANN-Adam 64-32 (project)", "Random Forest (project)",
    "XGBoost (project)", "Linear regression (project)",
]
NEURAL = {"ANN-GD (paper)", "ANN-Adam 64-32 (project)"}
METRICS = ["train_acc", "test_acc", "train_r", "test_r", "train_mse", "test_mse"]


def triangular(x, a, b, c):
    x = np.asarray(x, dtype=float)
    lo, hi = min(a, c), max(a, c)
    if b == lo:
        return np.where(x <= b, 1.0, np.clip((hi - x) / (hi - b), 0, 1))
    if b == hi:
        return np.where(x >= b, 1.0, np.clip((x - lo) / (b - lo), 0, 1))
    return np.clip(np.minimum((x - lo) / (b - lo), (hi - x) / (hi - b)), 0, 1)


def fuzzify(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {}
    for feature in FEATURES:
        for level, (a, b, c) in MEMBERSHIPS[feature].items():
            columns[f"{feature}_{level}"] = triangular(frame[feature].to_numpy(), a, b, c)
    return pd.DataFrame(columns)


class LinearSVRMulti(RegressorMixin, BaseEstimator):
    """One linear epsilon-SVR per output; C and epsilon from the IQR rule (assumed MATLAB-style defaults)."""

    def fit(self, X, Y):
        self.models_ = []
        for k in range(Y.shape[1]):
            iqr = np.subtract(*np.percentile(Y[:, k], [75, 25]))
            model = SVR(kernel="linear", C=max(iqr / 1.349, 1e-2), epsilon=max(iqr / 13.49, 1e-2), max_iter=200_000)
            self.models_.append(model.fit(X, Y[:, k]))
        return self

    def predict(self, X):
        return np.column_stack([m.predict(X) for m in self.models_])


class SVRRbfMulti(RegressorMixin, BaseEstimator):
    def fit(self, X, Y):
        self.models_ = [SVR(kernel="rbf", C=10.0, epsilon=0.1).fit(X, Y[:, k]) for k in range(Y.shape[1])]
        return self

    def predict(self, X):
        return np.column_stack([m.predict(X) for m in self.models_])


class ScaledTargetMLP(RegressorMixin, BaseEstimator):
    """MLP trained on scores/10; optionally holds out an inner partition as in the paper's 70/15/15 split."""

    def __init__(self, params: dict, inner_holdout: float = 0.0, seed: int = 0, signed_targets: bool = False):
        self.params, self.inner_holdout, self.seed, self.signed_targets = params, inner_holdout, seed, signed_targets

    def fit(self, X, Y):
        keep = np.arange(len(X))
        if self.inner_holdout:
            rng = np.random.default_rng(self.seed)
            keep = rng.permutation(len(X))[int(round(self.inner_holdout * len(X))):]
        scaled = Y[keep] / 5.0 - 1.0 if self.signed_targets else Y[keep] / 10.0
        self.model_ = MLPRegressor(random_state=self.seed, **self.params).fit(X[keep], scaled)
        return self

    def predict(self, X):
        raw = self.model_.predict(X)
        return 5.0 * (raw + 1.0) if self.signed_targets else 10.0 * raw


def make_estimator(name: str, seed: int, mode: str):
    if name == "GPR (SE kernel)":
        kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(1.0, (1e-2, 1e3)) + WhiteKernel(0.1, (1e-5, 1.0))
        core = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2, normalize_y=True, random_state=seed)
    elif name == "SVR linear (paper)":
        core = LinearSVRMulti()
    elif name == "ANN-GD (paper)":
        core = ScaledTargetMLP(
            dict(hidden_layer_sizes=(12,), activation="tanh", solver="sgd", learning_rate_init=0.01,
                 momentum=0.0, nesterovs_momentum=False, batch_size=64, max_iter=1000,
                 early_stopping=True, validation_fraction=0.16, n_iter_no_change=6, tol=1e-5),
            inner_holdout=0.15, seed=seed, signed_targets=True)
    elif name == "SVM-RBF (project)":
        core = SVRRbfMulti()
    elif name == "ANN-Adam 64-32 (project)":
        core = ScaledTargetMLP(
            dict(hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=0.001,
                 learning_rate_init=0.01, max_iter=250, early_stopping=True), seed=seed)
    elif name == "Random Forest (project)":
        core = RandomForestRegressor(n_estimators=100, random_state=seed, n_jobs=1)
    elif name == "XGBoost (project)":
        core = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.85,
                            colsample_bytree=0.85, random_state=seed, n_jobs=1)
    elif name == "Linear regression (project)":
        core = LinearRegression()
    else:
        raise KeyError(name)
    if name == "ANN-GD (paper)":
        return make_pipeline(MinMaxScaler((-1, 1)), core)
    return make_pipeline(StandardScaler(), core) if mode == "crisp" else core


def evaluate(pred: np.ndarray, true: np.ndarray) -> tuple[float, float, float]:
    accuracy = float(np.mean(pred.argmax(axis=1) == true.argmax(axis=1)))
    correlations = []
    for k in range(true.shape[1]):
        flat = np.std(pred[:, k]) == 0 or np.std(true[:, k]) == 0
        correlations.append(0.0 if flat else abs(np.corrcoef(pred[:, k], true[:, k])[0, 1]))
    return accuracy, float(np.mean(correlations)), float(np.mean(((pred - true) / 10.0) ** 2))


def one_iteration(name: str, mode: str, seed: int, X: np.ndarray, Y: np.ndarray) -> dict:
    order = np.random.default_rng(seed).permutation(len(X))
    n_train = int(round(TRAIN_FRACTION * len(X)))
    train, test = order[:n_train], order[n_train:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = make_estimator(name, seed, mode).fit(X[train], Y[train])
        tr = evaluate(model.predict(X[train]), Y[train])
        te = evaluate(model.predict(X[test]), Y[test])
    return dict(model=name, mode=mode, iteration=seed - BASE_SEED,
                train_acc=tr[0], test_acc=te[0], train_r=tr[1], test_r=te[1], train_mse=tr[2], test_mse=te[2])


def run_protocol(n_fast: int, n_neural: int) -> pd.DataFrame:
    data = load_dataset()
    Y = data[TARGETS].to_numpy(float)
    inputs = {"fuzzy": fuzzify(data[FEATURES]).to_numpy(float), "crisp": data[FEATURES].to_numpy(float)}
    jobs = [
        (name, mode, BASE_SEED + i, inputs[mode], Y)
        for mode in inputs for name in MODELS
        for i in range(n_neural if name in NEURAL else n_fast)
    ]
    rows = Parallel(n_jobs=-1, batch_size=8)(delayed(one_iteration)(*job) for job in jobs)
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(["model", "mode"])[METRICS]
    mean, sd, n = grouped.mean(), grouped.std(), grouped.size()
    summary = mean.add_suffix("_mean").join(sd.add_suffix("_sd"))
    for metric in METRICS:
        summary[f"{metric}_ci95"] = 1.96 * summary[f"{metric}_sd"] / np.sqrt(n)
    summary["n_iterations"] = n
    return summary.reset_index()


def classify(difference_pct: float) -> str:
    if difference_pct < 5:
        return "Excellent reproduction"
    if difference_pct <= 10:
        return "Acceptable reproduction"
    return "Requires investigation"


def compare_to_paper(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary[summary["model"].isin(PAPER_MAP)].iterrows():
        paper_name = PAPER_MAP[row["model"]]
        for metric in METRICS:
            scale = 100.0 if metric.endswith("acc") else 1.0
            paper_value = PAPER[paper_name][metric]
            repro = row[f"{metric}_mean"] * scale
            spread = row[f"{metric}_sd"] * scale
            difference = abs(paper_value - repro) / paper_value * 100.0
            rows.append(dict(
                model=paper_name, input_mode=row["mode"], metric=metric, paper=paper_value,
                reproduced=round(repro, 4), reproduced_sd=round(spread, 4),
                relative_difference_pct=round(difference, 2), classification=classify(difference),
                paper_within_1sd=bool(abs(paper_value - repro) <= spread)))
    return pd.DataFrame(rows)


def item_comparison(n_fast: int, n_neural: int) -> pd.DataFrame:
    items = [
        ("Dataset", "70 hypothetical Arctic incidents with expert suitability scores (Hu et al. 2020)", "Same 70 incidents parsed from thesis Appendix C; 6 integrity checks pass", "Match"),
        ("Input variables", "F1 oil type (API), F2 slick thickness, F3 continuity, F4 wave height, F5 remoteness, F6 floating ice", "Same six variables; thesis column order is A5 = ice, A6 = remoteness (paper F5/F6 are swapped)", "Match (naming only)"),
        ("Outputs", "Suitability 0-10 for MCR, ISB, UCD", "Same three outputs", "Match"),
        ("Preprocessing", "Triangular fuzzification of inputs (Table 2); crisp outputs for regression models", "Same membership functions; reproduced as 18 membership degrees (3 per factor)", "Partial - paper does not say 6 or 18 inputs"),
        ("Feature engineering", "None beyond fuzzification", "None beyond fuzzification", "Match"),
        ("Train/test split", "Random 70 % / 30 % per iteration", "Random 49 / 21 per iteration, paired seeds across models", "Match"),
        ("Repetitions", "10,000 (ANN, GPR, SVR, FDT-LR); 15 x 200 generations (OFDTs)", f"{n_fast} (non-neural) and {n_neural} (neural) iterations", "Partial - reduced; Monte Carlo error reported"),
        ("ANN architecture", "1 hidden layer, 12 neurons, MSE loss, 1000 epochs", "Same; tanh hidden activation assumed", "Match (activation assumed)"),
        ("ANN-GD", "Learning rate 0.01; inner 70/15/15 partition", "Full-batch SGD, lr 0.01, no momentum; inputs and targets scaled to [-1, 1] (MATLAB default, assumed); inner test partition held out", "Match (scaling assumed)"),
        ("ANN-LM", "Levenberg-Marquardt training", "Not implemented (no scikit-learn equivalent)", "Not reproduced"),
        ("ANN-BR", "Bayesian regularization, 85/15 split", "Not implemented (no scikit-learn equivalent)", "Not reproduced"),
        ("SVR", "Linear mapping, dual QP, no input normalization; C and epsilon not reported", "Linear kernel, no normalization; C and epsilon from IQR rule (assumed)", "Partial - hyperparameters unreported"),
        ("GPR", "Squared-exponential kernel, learned hyperparameters", "Constant x RBF + learned noise (fitrgp estimates noise), 2 restarts, isotropic", "Partial - basis function and noise settings unreported"),
        ("FDT-LR / OFDTs", "ID3 fuzzy trees with regression leaves; NSDE optimization", "Not implemented; the project's fuzzy baseline is a different hand-coded model", "Not reproduced"),
        ("Metrics", "Top-method accuracy, Pearson r, MSE (0-1)", "Same; MSE computed on scores / 10", "Match (normalization assumed)"),
        ("Software", "MATLAB R2021a", "Python scikit-learn / XGBoost", "Differs"),
    ]
    return pd.DataFrame(items, columns=["Item", "Paper", "Reproduced model", "Match status"])


def scope_audit() -> pd.DataFrame:
    rows = [
        ("Environment", "Offshore, on-water, Arctic/sub-arctic", "Shoreline / intertidal", "Not comparable"),
        ("Decision", "3 methods: MCR, ISB, UCD", "15 shoreline treatments", "Not comparable"),
        ("Inputs", "API, slick thickness, continuity, waves, ice, remoteness", "Shoreline type, oil category/coverage/thickness, penetration, exposure, sensitivity", "Not comparable"),
        ("Training data", "70 expert-scored hypothetical incidents", "Rule-generated synthetic scores (no expert labels)", "Different"),
        ("Metric", "Top-method selection accuracy", "MAE / R2 on suitability score", "Different"),
        ("Model families", "ANN, SVR, GPR, FDT", "GPR live; Linear, SVM, ANN, RF, XGB, fuzzy baseline benchmarked", "Overlap: GPR, SVR, ANN"),
    ]
    return pd.DataFrame(rows, columns=["Aspect", "Paper (Mohammadiun 2022)", "Existing project model", "Comparable?"])


def plot_results(results: pd.DataFrame, comparison: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    test = comparison[comparison["metric"] == "test_acc"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    labels = ["GPR", "SVR", "ANN-GD"]
    width = 0.26
    positions = np.arange(len(labels))
    ax.bar(positions - width, [PAPER[m]["test_acc"] for m in labels], width, label="Paper", color="#4d4d4d")
    for offset, mode, color in [(0, "fuzzy", "#176b87"), (width, "crisp", "#db8b3e")]:
        subset = test[test["input_mode"] == mode].set_index("model").loc[labels]
        ax.bar(positions + offset, subset["reproduced"], width, yerr=subset["reproduced_sd"], capsize=3,
               label=f"Reproduced ({mode} inputs)", color=color)
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Testing accuracy (%)")
    ax.set_ylim(0, 112)
    ax.set_title("Testing accuracy: paper vs reproduction (error bars = SD across splits)")
    ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=9)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "paper_vs_reproduced_test_accuracy.png", dpi=300)
    plt.close(fig)

    fuzzy = results[results["mode"] == "fuzzy"].assign(test_acc=lambda d: d["test_acc"] * 100)
    order = fuzzy.groupby("model")["test_acc"].median().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=fuzzy, y="model", x="test_acc", order=order, color="#9bb8a8", ax=ax)
    ax.set_xlabel("Testing accuracy (%) across random 70/30 splits")
    ax.set_ylabel("")
    ax.set_title("Distribution of testing accuracy by model (fuzzified inputs)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "test_accuracy_distribution.png", dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--neural-iterations", type=int, default=150)
    parser.add_argument("--replot", action="store_true", help="Rebuild figures from saved iteration_results.csv")
    args = parser.parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.replot:
        saved = pd.read_csv(RESULTS_DIR / "iteration_results.csv")
        plot_results(saved, compare_to_paper(summarize(saved)))
        print("REPLOTTED")
        return

    data = load_dataset()
    checks = verify_dataset(data)
    ties = int((np.sort(data[TARGETS].to_numpy(), axis=1)[:, -1] == np.sort(data[TARGETS].to_numpy(), axis=1)[:, -2]).sum())
    pd.DataFrame({**checks, "tied_top_scores": ties}, index=[0]).T.rename(columns={0: "value"}).to_csv(RESULTS_DIR / "dataset_checks.csv")
    if not all(checks.values()):
        raise SystemExit("Dataset integrity checks failed; aborting.")

    results = run_protocol(args.iterations, args.neural_iterations)
    summary = summarize(results)
    comparison = compare_to_paper(summary)
    results.to_csv(RESULTS_DIR / "iteration_results.csv", index=False)
    summary.to_csv(RESULTS_DIR / "model_summary.csv", index=False)
    comparison.to_csv(RESULTS_DIR / "metric_comparison.csv", index=False)
    item_comparison(args.iterations, args.neural_iterations).to_csv(RESULTS_DIR / "item_comparison.csv", index=False)
    scope_audit().to_csv(RESULTS_DIR / "scope_audit.csv", index=False)
    scorecard = comparison.groupby(["model", "input_mode", "classification"]).size().unstack(fill_value=0)
    scorecard.to_csv(RESULTS_DIR / "reproduction_scorecard.csv")
    plot_results(results, comparison)

    print("TIED_TOP_SCORES", ties)
    print(summary[["model", "mode", "test_acc_mean", "test_acc_sd", "train_acc_mean", "n_iterations"]].round(3).to_string(index=False))
    print(scorecard.to_string())


if __name__ == "__main__":
    main()
