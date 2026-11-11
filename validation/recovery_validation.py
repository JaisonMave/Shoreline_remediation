"""Validation of the marsh recovery model against the published case histories it was fitted to.

Every score here is out-of-sample: each spill (with all its strata) is held out in turn, the model is fitted
to the other spills, and the held-out cases are predicted. Three questions are answered:

1. Does the full model predict held-out cases better than a model with no predictors at all?
2. Which predictors carry that skill: oil and oiling degree, or treatment?
3. Does a more flexible learner (random forest) do better than the regression?

Run:  python -m validation.recovery_validation
Writes results/recovery/{cv_scores,time_ratios,case_predictions,scenario_forecasts}.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.marsh_recovery_model import (  # noqa: E402
    ALL_FEATURES, FEATURES, SOURCE, MarshRecoveryModel, bootstrap_time_ratios, design_matrix, load_cases,
)

RESULTS_DIR = ROOT / "results" / "recovery"
MODEL_SPECS = {
    "no predictors (baseline)": ["intercept"],
    "oil type and oiling degree": ["intercept", "oil_light_refined", "oil_heavy_fuel", "oiling_heavy", "oiling_light", "field_experiment"],
    "treatment only": ["intercept", "treat_cutting_raking", "treat_intensive", "treat_burn", "field_experiment"],
    "full model": FEATURES,
    "extended model (adds season, latitude, wetland type)": ALL_FEATURES,
}
N_BASE = len(FEATURES)


def _log_distance(median: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """0 when the predicted median lies inside the observed interval; otherwise the distance to it in
    natural-log units (0.69 = a factor of two)."""
    with np.errstate(divide="ignore"):
        below = np.log(lo) - np.log(median)
        above = np.log(median) - np.log(hi)
    return np.maximum(0.0, np.maximum(below, above))


def _forest_target(cases: pd.DataFrame) -> np.ndarray:
    """A random forest needs one number per case, so bounds are imputed: an interval becomes its geometric
    mean, '<x' becomes x/2 and '>x' becomes 1.5x. This is cruder than the interval likelihood."""
    lo, hi = cases["lo"].to_numpy(float), cases["hi"].to_numpy(float)
    value = np.sqrt(np.where(lo > 0, lo, hi / 4.0) * np.where(np.isfinite(hi), hi, lo * 2.25))
    return np.log(value)


def cross_validate(cases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    spills = cases["spill"].unique()
    held_out = {name: np.zeros(len(cases)) for name in MODEL_SPECS}
    forests = {"random forest (imputed bounds)": N_BASE, "random forest, extended features": len(ALL_FEATURES)}
    medians = {name: np.zeros(len(cases)) for name in [*MODEL_SPECS, *forests]}
    for spill in spills:
        test = (cases["spill"] == spill).to_numpy()
        train_cases, test_cases = cases[~test], cases[test]
        for name, columns in MODEL_SPECS.items():
            model = MarshRecoveryModel(columns=columns).fit(train_cases)
            held_out[name][test] = model.log_prob(test_cases)
            medians[name][test] = model.predict_median(test_cases)
        for name, width in forests.items():
            forest = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=0)
            forest.fit(design_matrix(train_cases)[:, 1:width], _forest_target(train_cases))
            medians[name][test] = np.exp(forest.predict(design_matrix(test_cases)[:, 1:width]))

    lo, hi = cases["lo"].to_numpy(float), cases["hi"].to_numpy(float)
    baseline = held_out["no predictors (baseline)"]
    rows = []
    for name, median in medians.items():
        distance = _log_distance(median, lo, hi)
        row = {
            "model": name,
            "median_inside_observed_interval": round(float((distance == 0).mean()), 3),
            "mean_log_distance_to_interval": round(float(distance.mean()), 3),
            "within_factor_2_of_interval": round(float((distance <= np.log(2)).mean()), 3),
        }
        if name in held_out:
            gain = held_out[name] - baseline
            row["mean_heldout_log_prob"] = round(float(held_out[name].mean()), 3)
            row["gain_over_baseline"] = round(float(gain.mean()), 3)
            # Standard error of the mean gain, from per-spill sums so strata of a spill are not double counted.
            per_spill = pd.Series(gain).groupby(cases["spill"].to_numpy()).sum()
            row["gain_standard_error"] = round(float(per_spill.std(ddof=1) * np.sqrt(len(per_spill)) / len(cases)), 3)
        rows.append(row)
    predictions = cases[["case_id", "spill", "stratum", "oil_group", "oiling", "treatment_class", "recovery_as_written"]].copy()
    extended = "extended model (adds season, latitude, wetland type)"
    predictions["heldout_median_years_full_model"] = medians["full model"].round(2)
    predictions["heldout_median_years_extended_model"] = medians[extended].round(2)
    predictions["log_distance_to_interval"] = _log_distance(medians[extended], lo, hi).round(2)
    return pd.DataFrame(rows), predictions


def scenario_forecasts(model: MarshRecoveryModel) -> pd.DataFrame:
    rows = []
    for oil in ["crude", "heavy_fuel"]:
        for oiling in ["light", "heavy"]:
            for treatment in ["none_or_light", "cutting_raking", "intensive", "burn"]:
                forecast = model.forecast(oil, oiling, treatment)
                rows.append({"oil_group": oil, "oiling": oiling, "treatment_class": treatment,
                             **{key: round(value, 2) for key, value in vars(forecast).items()}})
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    print(f"Source: {SOURCE}")
    print(f"{len(cases)} cases from {cases['spill'].nunique()} spills and field studies "
          f"({len(load_cases(included_only=False)) - len(cases)} rows excluded; see the 'flags' column).")

    scores, predictions = cross_validate(cases)
    ratios = bootstrap_time_ratios(cases, columns=ALL_FEATURES)
    forecasts = scenario_forecasts(MarshRecoveryModel().fit(cases))
    scores.to_csv(RESULTS_DIR / "cv_scores.csv", index=False)
    predictions.to_csv(RESULTS_DIR / "case_predictions.csv", index=False)
    ratios.to_csv(RESULTS_DIR / "time_ratios.csv")
    forecasts.to_csv(RESULTS_DIR / "scenario_forecasts.csv", index=False)

    pd.set_option("display.width", 220)
    print("\nLeave-one-spill-out scores (higher log prob is better; lower distance is better):")
    print(scores.to_string(index=False))
    print("\nTime ratios with 90% bootstrap intervals (1.0 = no difference from the reference case):")
    print(ratios.to_string())
    print("\nLargest held-out misses of the extended model:")
    print(predictions.sort_values("log_distance_to_interval", ascending=False).head(6).to_string(index=False))


if __name__ == "__main__":
    main()
