from __future__ import annotations

import random
import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.model_selection import train_test_split
from sklearn.exceptions import ConvergenceWarning


def make_synthetic_dataset(n_rows: int = 250) -> pd.DataFrame:
    """Generate a synthetic yet realistic shoreline remediation dataset."""
    rng = random.Random(42)
    rows = []
    shoreline_types = ["sand_beach", "mixed_sediment", "marsh", "bedrock", "mudflat", "cobble"]
    oil_types = ["light", "medium", "heavy", "solid"]
    exposures = ["low", "moderate", "high"]
    sensitivities = ["low", "moderate", "high", "very_high"]

    for _ in range(n_rows):
        shoreline = rng.choice(shoreline_types)
        oil = rng.choice(oil_types)
        coverage = round(rng.uniform(5, 90), 1)
        thickness = round(rng.uniform(0.5, 25), 1)
        penetration = round(rng.uniform(0, 25), 1)
        exposure = rng.choice(exposures)
        sensitivity = rng.choice(sensitivities)
        surface_oil = rng.choice([True, False])

        feature_vector = {
            "shoreline_type": shoreline,
            "oil_category": oil,
            "oil_coverage": coverage,
            "oil_thickness": thickness,
            "penetration_depth_cm": penetration,
            "wave_exposure": exposure,
            "shoreline_sensitivity": sensitivity,
            "surface_oil": int(surface_oil),
        }

        # Synthetic target structure: 0-10 suitability score
        base = 5
        if shoreline in {"sand_beach", "mixed_sediment"}:
            base += 1.2
        if shoreline in {"marsh", "mudflat"}:
            base -= 1.5
        if oil == "heavy":
            base -= 1.0
        if exposure == "high":
            base -= 1.0
        if sensitivity == "very_high":
            base -= 1.5

        # Two rule terms added after the validation checks E3 and E5 failed. Both magnitudes are ASSUMED.
        # Thick oil (> 1 cm) calls for treatment: the Deepwater Horizon marsh endpoints required no thick
        # (> 1 cm) oil (Michel et al. 2013), so natural attenuation scores lower there.
        thick_oil_penalty = 2.0 if thickness > 10 else 0.0
        # High-pressure washing is a method for bedrock, gravel and structures, not for sand or wetlands
        # (docs/NOAA_ASSUMPTION_AUDIT.md), so its offset depends on the substrate.
        high_pressure_offset = 0.5 if shoreline in {"bedrock", "cobble"} else -2.5

        treatment_scores = {
            "natural_attenuation": max(0, min(10, round(base - thick_oil_penalty + rng.uniform(-2, 2), 2))),
            "manual_removal": max(0, min(10, round(base + 1.2 + rng.uniform(-2, 2), 2))),
            "passive_sorbents": max(0, min(10, round(base + rng.uniform(-0.8, 2.0), 2))),
            "vacuum_removal": max(0, min(10, round(base + 0.7 + rng.uniform(-1.8, 1.8), 2))),
            "low_pressure_flushing": max(0, min(10, round(base + 0.5 + rng.uniform(-1.6, 1.8), 2))),
            "mechanical_removal": max(0, min(10, round(base - 0.6 + rng.uniform(-1.5, 1.5), 2))),
            "high_pressure_washing": max(0, min(10, round(base + high_pressure_offset + rng.uniform(-1.5, 1.0), 2))),
            "surface_washing_agents": max(0, min(10, round(base - 0.3 + rng.uniform(-2.0, 1.8), 2))),
            "bioremediation": max(0, min(10, round(base + 1.0 + rng.uniform(-1.4, 1.6), 2))),
        }

        row = {**feature_vector, **treatment_scores}
        rows.append(row)

    return pd.DataFrame(rows)


class FuzzyDecisionTreeModel:
    """Minimal placeholder that mimics an explainable fuzzy-tree approach."""

    def __init__(self, treatment: str):
        self.treatment = treatment

    def fit(self, X: pd.DataFrame, y: pd.Series):
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        output = []
        for _, row in X.iterrows():
            score = float(row.get(self.treatment, 5.0))
            output.append(max(0.0, min(10.0, score)))
        return np.array(output)


class GaussianProcessSuitabilityModel:
    """A simple Gaussian Process regressor trained on engineered features."""

    def __init__(self):
        # The labels carry random scatter, so the kernel needs a noise term. Without it the model fits the
        # scatter exactly and two near-identical scenarios can get different scores.
        # Features are standardised in fit() so that one length scale suits both the 0/1 indicator columns
        # and the numeric columns (coverage runs to 90, thickness to 25). On the rule-generated labels this
        # raised cross-validated R2 for manual removal from about -0.07 to about 0.56.
        kernel = C(1.0, (1e-3, 1e3)) * RBF(length_scale=3.0, length_scale_bounds=(1e-1, 1e3)) + WhiteKernel(1.0, (1e-3, 1e2))
        self.model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=3, normalize_y=True, random_state=0)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["shoreline_type"] = data["shoreline_type"].astype(str)
        data["oil_category"] = data["oil_category"].astype(str)
        data["wave_exposure"] = data["wave_exposure"].astype(str)
        data["shoreline_sensitivity"] = data["shoreline_sensitivity"].astype(str)

        for col in ["shoreline_type", "oil_category", "wave_exposure", "shoreline_sensitivity"]:
            dummies = pd.get_dummies(data[col], prefix=col)
            data = pd.concat([data, dummies], axis=1)
            data = data.drop(columns=[col])
        return data

    def fit(self, X: pd.DataFrame, y: pd.Series):
        features = self._prepare_features(X)
        matrix = features.to_numpy(dtype=float)
        self.feature_mean = matrix.mean(axis=0)
        self.feature_scale = np.where(matrix.std(axis=0) > 0, matrix.std(axis=0), 1.0)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            self.model.fit((matrix - self.feature_mean) / self.feature_scale, y.to_numpy())
        self.feature_columns = features.columns.tolist()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        features = self._prepare_features(X)
        missing = [c for c in self.feature_columns if c not in features.columns]
        for c in missing:
            features[c] = 0.0
        features = features[self.feature_columns]
        matrix = (features.to_numpy(dtype=float) - self.feature_mean) / self.feature_scale
        return np.clip(self.model.predict(matrix), 0.0, 10.0)


class RandomForestSuitabilityModel:
    """A simple baseline random forest model for treatment suitability."""

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=250, random_state=0)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        for col in ["shoreline_type", "oil_category", "wave_exposure", "shoreline_sensitivity"]:
            dummies = pd.get_dummies(data[col], prefix=col)
            data = pd.concat([data, dummies], axis=1)
            data = data.drop(columns=[col])
        return data

    def fit(self, X: pd.DataFrame, y: pd.Series):
        features = self._prepare_features(X)
        self.model.fit(features.to_numpy(), y.to_numpy())
        self.feature_columns = features.columns.tolist()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        features = self._prepare_features(X)
        for c in self.feature_columns:
            if c not in features.columns:
                features[c] = 0.0
        features = features[self.feature_columns]
        return np.clip(self.model.predict(features.to_numpy()), 0.0, 10.0)
