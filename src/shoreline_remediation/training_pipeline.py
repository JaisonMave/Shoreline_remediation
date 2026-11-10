from __future__ import annotations

from typing import Dict, List
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

try:
    from xgboost import XGBRegressor
except ImportError:  # pragma: no cover - handled as an unavailable optional model
    XGBRegressor = None

from .data_dictionary import generate_training_dataset


class SimpleFuzzyDecisionTreeRegressor:
    """A lightweight fuzzy-rule baseline that mimics a fuzzy decision tree."""

    def __init__(self):
        self.feature_names_ = FEATURE_COLUMNS

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self._n_features = len(X.columns)
        return self

    def _membership(self, value: float, low: float, mid: float, high: float) -> float:
        if value <= low:
            return 1.0
        if low < value < mid:
            return 1.0 - (value - low) / (mid - low)
        if mid <= value <= high:
            return (value - mid) / (high - mid)
        return 0.0

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        predictions = []
        for _, row in X.iterrows():
            score = 5.0
            shoreline = str(row.get("shoreline_type", "mixed_sediment")).lower()
            oil = str(row.get("oil_category", "medium")).lower()
            coverage = float(row.get("oil_coverage_pct", 50.0))
            penetration = float(row.get("penetration_depth_cm", 5.0))
            sensitivity = str(row.get("shoreline_sensitivity", "moderate")).lower()

            if shoreline in {"marsh", "mudflat", "peat", "tundra"}:
                score += 1.2
            if shoreline in {"sand_beach", "mixed_sediment", "gravel_beach"}:
                score += 0.4
            if oil == "heavy":
                score -= 1.0
            if oil == "solid":
                score -= 1.5
            if coverage > 60:
                score += 0.8
            if penetration > 10:
                score += 0.7
            if sensitivity in {"high", "very_high"}:
                score -= 1.0

            score += self._membership(coverage, 0, 50, 100) * 1.2
            score -= self._membership(penetration, 0, 10, 25) * 1.5
            score = max(0.0, min(10.0, score))
            predictions.append(score)
        return np.array(predictions, dtype=float)


TARGET_TREATMENTS = [
    "natural_attenuation",
    "manual_removal",
    "passive_sorbents",
    "vacuum_removal",
    "low_pressure_flushing",
    "mechanical_removal",
    "high_pressure_washing",
    "surface_washing_agents",
    "bioremediation",
]


def export_dataset(path: str = "scenario_training_dataset.csv", n_rows: int = 600) -> pd.DataFrame:
    """Create a CSV dataset file with FAST + SCAT feature columns and treatment targets."""
    df = generate_training_dataset(n_rows=n_rows)
    df.to_csv(path, index=False)
    return df

NUMERIC_FEATURES = [
    "grain_size_mm",
    "slope_deg",
    "api_gravity",
    "viscosity_cP",
    "pour_point_C",
    "weathering_pct",
    "stabilized_oil_fraction",
    "oil_coverage_pct",
    "oil_thickness_cm",
    "penetration_depth_cm",
    "tidal_range_m",
    "current_m_s",
    "temperature_C",
]

CATEGORICAL_FEATURES = [
    "shoreline_type",
    "substrate_permeability",
    "oil_category",
    "oil_distribution",
    "wave_exposure",
    "season",
    "habitat_type",
    "shoreline_sensitivity",
    "vegetation",
    "recovery_potential",
    "accessibility",
    "equipment_access",
    "waste_handling",
    "safety_constraint",
    "subsurface_oil",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


class TreatmentModelTrainer:
    """Train and benchmark a Gaussian Process and Random Forest regression model."""

    def __init__(self, treatment: str):
        self.treatment = treatment

    def prepare_data(self, df: pd.DataFrame):
        X = df[FEATURE_COLUMNS]
        y = df[self.treatment]
        return X, y

    def _build_pipeline(self, model_name: str):
        scale_numeric = model_name in {"linear", "svm", "ann"}
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    StandardScaler() if scale_numeric else "passthrough",
                    NUMERIC_FEATURES,
                ),
                ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ]
        )

        if model_name == "linear":
            model = LinearRegression()
        elif model_name == "svm":
            model = SVR(C=10.0, epsilon=0.1, kernel="rbf")
        elif model_name == "ann":
            model = MLPRegressor(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                alpha=0.001,
                learning_rate_init=0.01,
                max_iter=250,
                early_stopping=True,
                random_state=0,
            )
        elif model_name == "gpr":
            model = GaussianProcessRegressor(
                kernel=ConstantKernel(1.0) * RBF(length_scale=1.0),
                random_state=0,
                n_restarts_optimizer=0,
            )
        elif model_name == "rf":
            model = RandomForestRegressor(n_estimators=100, random_state=0, n_jobs=1)
        elif model_name == "xgb":
            if XGBRegressor is None:
                raise ImportError("XGBoost is not installed; install xgboost to run this benchmark.")
            model = XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                objective="reg:squarederror",
                eval_metric="mae",
                random_state=0,
                n_jobs=1,
            )
        elif model_name == "fdt":
            return SimpleFuzzyDecisionTreeRegressor()
        else:
            raise ValueError(f"Unknown model: {model_name}")

        return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

    def train_and_evaluate(self, model_name: str, test_size: float = 0.2, df: pd.DataFrame | None = None):
        if df is None:
            df = generate_training_dataset(n_rows=300)
        X, y = self.prepare_data(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        pipeline = self._build_pipeline(model_name)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        metrics = {
            "mae": mean_absolute_error(y_test, predictions),
            "r2": r2_score(y_test, predictions),
            "model": model_name,
            "treatment": self.treatment,
        }
        return pipeline, metrics


def benchmark_models(n_rows: int = 120) -> Dict[str, List[dict]]:
    results = {"linear": [], "svm": [], "ann": [], "rf": [], "xgb": [], "gpr": [], "fdt": []}
    model_names = list(results)
    for treatment in TARGET_TREATMENTS:
        training_data = generate_training_dataset(n_rows=n_rows)
        trainer = TreatmentModelTrainer(treatment)
        for model_name in model_names:
            _, metrics = trainer.train_and_evaluate(model_name, df=training_data)
            results[model_name].append(metrics)
    return results


def summarize_benchmark(results: Dict[str, List[dict]]) -> Dict[str, dict]:
    summary = {}
    for model_name, metrics in results.items():
        mae_values = [item["mae"] for item in metrics]
        r2_values = [item["r2"] for item in metrics]
        summary[model_name] = {
            "mean_mae": float(np.mean(mae_values)),
            "mean_r2": float(np.mean(r2_values)),
            "best_treatment": max(metrics, key=lambda m: m["r2"])["treatment"],
        }
    return summary


def export_comparison_report(path: str = "comparison_report.csv", results: Dict[str, List[dict]] | None = None) -> pd.DataFrame:
    """Flatten benchmark results into a CSV for report viewing."""
    if results is None:
        results = benchmark_models()

    rows = []
    for model_name, metrics_list in results.items():
        for metrics in metrics_list:
            rows.append({
                "model": model_name,
                "treatment": metrics["treatment"],
                "mae": metrics["mae"],
                "r2": metrics["r2"],
            })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df
