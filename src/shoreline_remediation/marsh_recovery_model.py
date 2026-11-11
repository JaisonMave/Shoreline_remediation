"""Evidence-based model of marsh vegetation recovery time after oiling.

Why this exists: the process models in this package (process_model.py, shoreline_transport.py) compute
habitat recovery as an algebraic function of oil removed, with a treatment "disturbance" term that fades in
about 90 days. That structure cannot represent the best-documented effect in marshes: aggressive cleanup
can slow recovery by years. This module learns recovery time from observed outcomes instead.

Data: data/marsh_recovery_cases.csv, transcribed from Appendices A-D of
    NOAA Office of Response and Restoration, "Oil Spills in Marshes: Planning and Response Considerations",
    https://response.restoration.noaa.gov/sites/default/files/Oil_Spills_in_Marshes.pdf
The table was read by an automated reader, not typed from the PDF by a person. Treat every row as
unverified until it has been checked against the report. Columns ending in "_as_written" hold the source
wording; oil_group, oiling and treatment_class are codings added for this model and are open to revision.

Model: a log-normal accelerated-failure-time (AFT) regression fitted by penalised maximum likelihood.
Recovery times in the source are mostly intervals or bounds ("<2 yr", "4-12+ yr"), so every case enters the
likelihood as the probability of its interval rather than as a point value:

    log T = b0 + b.x + sigma * e,   e ~ N(0, 1)
    P(case) = Phi((log hi - mu) / sigma) - Phi((log lo - mu) / sigma)

A Gaussian prior N(0, 1) on each coefficient (a ridge penalty of 0.5) keeps estimates stable with about 60
cases. exp(b) is a time ratio: 2.0 means recovery takes twice as long as the reference case.

Validation result (python -m validation.recovery_validation, leave-one-spill-out): the full model does not
predict held-out spills better than a model with no predictors, with or without EXTRA_FEATURES. Until it does, read a forecast as the
general range of marsh recovery times, and do not use the differences between treatments to rank them.

Limits: these are observational case histories. Treatment was not assigned at random, burn cases are mostly
small Louisiana crude spills, and only three included rows describe intensive treatment. The coefficients
are associations, not causal effects. The model covers marshes and other wetlands only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "marsh_recovery_cases.csv"
SOURCE = (
    "NOAA Office of Response and Restoration. Oil Spills in Marshes: Planning and Response Considerations, "
    "Appendices A-D. https://response.restoration.noaa.gov/sites/default/files/Oil_Spills_in_Marshes.pdf"
)

OIL_GROUPS = ["crude", "light_refined", "heavy_fuel"]  # first entry is the reference level
TREATMENT_CLASSES = ["none_or_light", "cutting_raking", "intensive", "burn"]
FEATURES = [
    "intercept", "oil_light_refined", "oil_heavy_fuel", "oiling_heavy", "oiling_light",
    "treat_cutting_raking", "treat_intensive", "treat_burn", "field_experiment",
]
# Drivers the source report names, coded from facts fixed before the outcome was known: the month of the
# spill or burn, the wetland type printed in the table, and the site's approximate latitude. The report's
# own lists of "longest recovery" examples are deliberately not used as features: those examples were
# picked because they recovered slowly, so coding from them would leak the outcome into the predictors.
EXTRA_FEATURES = ["dormant_season", "high_latitude", "non_salt_wetland"]
ALL_FEATURES = FEATURES + EXTRA_FEATURES
PRIOR_SD = 1.0  # prior standard deviation of each coefficient on the log time-ratio scale
EXACT_TOLERANCE = 0.25  # a recovery time reported as a single number is treated as that number +/- 25%

# How this tool's treatment names map onto the evidence classes. None means the source table has no cases
# for that treatment, so the model gives no forecast. This mapping is a judgement; edit it as needed.
TOOL_TREATMENT_TO_CLASS = {
    "no_cleanup": "none_or_light",
    "natural_attenuation": "none_or_light",
    "passive_sorbents": "none_or_light",
    "low_pressure_flushing": "none_or_light",
    "vacuum_removal": "none_or_light",
    "manual_removal": "cutting_raking",
    "vegetation_cutting": "cutting_raking",
    "mechanical_removal": "intensive",
    "sediment_relocation": "intensive",
    "sediment_mixing": "intensive",
    "high_pressure_washing": "intensive",
    "high_pressure_heated_washing": "intensive",
    "low_pressure_heated_flushing": None,
    "surface_washing_agents": None,
    "solidifiers": None,
    "bioremediation": None,
}
TOOL_OIL_TO_GROUP = {"light": "light_refined", "medium": "crude", "heavy": "heavy_fuel", "solid": "heavy_fuel"}
MARSH_SHORELINES = {"marsh", "mudflat", "peat", "tundra"}


def load_cases(path: str | Path | None = None, included_only: bool = True) -> pd.DataFrame:
    """Load the case table. Blank rec_lo_yr means no lower bound; blank rec_hi_yr means no upper bound."""
    cases = pd.read_csv(path or DATA_PATH)
    lo = cases["rec_lo_yr"].astype(float)
    hi = cases["rec_hi_yr"].astype(float)
    exact = lo.notna() & hi.notna() & (lo == hi)
    cases["lo"] = np.where(exact, lo * (1 - EXACT_TOLERANCE), lo.fillna(0.0))
    cases["hi"] = np.where(exact, hi * (1 + EXACT_TOLERANCE), hi.fillna(np.inf))
    if not (cases["lo"] < cases["hi"]).all():
        raise ValueError("Every case needs rec_lo_yr < rec_hi_yr (or one of them blank).")
    return cases[cases["include"] == 1].reset_index(drop=True) if included_only else cases


def design_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Build the feature matrix. Needs oil_group, oiling, treatment_class and setting columns."""
    unknown_oil = set(frame["oil_group"]) - set(OIL_GROUPS)
    unknown_treatment = set(frame["treatment_class"]) - set(TREATMENT_CLASSES)
    if unknown_oil or unknown_treatment:
        raise ValueError(f"Unknown oil_group {unknown_oil} or treatment_class {unknown_treatment}.")
    columns = {
        "intercept": np.ones(len(frame)),
        "oil_light_refined": frame["oil_group"] == "light_refined",
        "oil_heavy_fuel": frame["oil_group"] == "heavy_fuel",
        "oiling_heavy": frame["oiling"] == "heavy",
        "oiling_light": frame["oiling"] == "light",
        "treat_cutting_raking": frame["treatment_class"] == "cutting_raking",
        "treat_intensive": frame["treatment_class"] == "intensive",
        "treat_burn": frame["treatment_class"] == "burn",
        "field_experiment": frame["setting"] == "field_experiment",
    }
    # Unknown season or wetland type is coded 0.5, halfway between the two known levels.
    n = len(frame)
    season = pd.to_numeric(frame["dormant_season"], errors="coerce") if "dormant_season" in frame else pd.Series(np.nan, index=frame.index)
    habitat = frame["habitat_class"] if "habitat_class" in frame else pd.Series(["unstated"] * n, index=frame.index)
    latitude = frame["abs_latitude_ge_45"] if "abs_latitude_ge_45" in frame else pd.Series(np.zeros(n), index=frame.index)
    columns["dormant_season"] = season.fillna(0.5)
    columns["non_salt_wetland"] = habitat.map({"salt": 0.0, "non_salt": 1.0}).fillna(0.5)
    columns["high_latitude"] = latitude
    return np.column_stack([np.asarray(columns[name], dtype=float) for name in ALL_FEATURES])


def _interval_log_prob(mu: np.ndarray, sigma: float, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        a = (np.log(lo) - mu) / sigma
        b = (np.log(hi) - mu) / sigma
    # Use the upper tail when both bounds are above the mean, which keeps the difference accurate.
    prob = np.where(a > 0, norm.sf(a) - norm.sf(b), norm.cdf(b) - norm.cdf(a))
    return np.log(np.clip(prob, 1e-300, None))


@dataclass
class Forecast:
    median_years: float
    low_years: float  # 10th percentile
    high_years: float  # 90th percentile
    prob_within_2yr: float
    prob_within_5yr: float


class MarshRecoveryModel:
    """Interval-censored log-normal AFT regression with a Gaussian prior on the coefficients."""

    def __init__(self, columns: list[str] | None = None, prior_sd: float = PRIOR_SD):
        self.columns = columns or FEATURES
        self.prior_sd = prior_sd
        self.coef_: np.ndarray | None = None
        self.sigma_: float | None = None

    def _select(self, matrix: np.ndarray) -> np.ndarray:
        return matrix[:, [ALL_FEATURES.index(name) for name in self.columns]]

    def fit(self, cases: pd.DataFrame) -> "MarshRecoveryModel":
        x = self._select(design_matrix(cases))
        lo, hi = cases["lo"].to_numpy(float), cases["hi"].to_numpy(float)
        penalty = 0.5 / self.prior_sd**2

        def objective(params: np.ndarray) -> float:
            beta, sigma = params[:-1], np.exp(params[-1])
            log_prob = _interval_log_prob(x @ beta, sigma, lo, hi)
            return -log_prob.sum() + penalty * np.sum(beta[1:] ** 2)  # the intercept is not penalised

        start = np.zeros(x.shape[1] + 1)
        start[0] = np.log(2.0)
        best = min(
            (minimize(objective, start + shift, method="BFGS") for shift in (0.0, 0.3, -0.3)),
            key=lambda result: result.fun,
        )
        self.coef_, self.sigma_ = best.x[:-1], float(np.exp(best.x[-1]))
        return self

    def log_prob(self, cases: pd.DataFrame) -> np.ndarray:
        """Log probability the fitted model gives to each case's observed recovery interval."""
        mu = self._select(design_matrix(cases)) @ self.coef_
        return _interval_log_prob(mu, self.sigma_, cases["lo"].to_numpy(float), cases["hi"].to_numpy(float))

    def predict_median(self, cases: pd.DataFrame) -> np.ndarray:
        return np.exp(self._select(design_matrix(cases)) @ self.coef_)

    def forecast(self, oil_group: str, oiling: str, treatment_class: str, field_experiment: bool = False) -> Forecast:
        row = pd.DataFrame([{
            "oil_group": oil_group, "oiling": oiling, "treatment_class": treatment_class,
            "setting": "field_experiment" if field_experiment else "spill",
        }])
        mu = float((self._select(design_matrix(row)) @ self.coef_)[0])
        z = norm.ppf(0.9)
        within = lambda years: float(norm.cdf((np.log(years) - mu) / self.sigma_))  # noqa: E731
        return Forecast(float(np.exp(mu)), float(np.exp(mu - z * self.sigma_)), float(np.exp(mu + z * self.sigma_)),
                        within(2.0), within(5.0))

    def time_ratios(self) -> pd.Series:
        """exp(coefficient): how many times longer recovery takes than in the reference case."""
        return pd.Series(np.exp(self.coef_[1:]), index=self.columns[1:], name="time_ratio")


def bootstrap_time_ratios(cases: pd.DataFrame, n_boot: int = 300, seed: int = 0, columns: list[str] | None = None) -> pd.DataFrame:
    """Time ratios with 90% intervals from resampling whole spills, so strata of one spill stay together."""
    rng = np.random.default_rng(seed)
    spills = cases["spill"].unique()
    groups = {spill: cases[cases["spill"] == spill] for spill in spills}
    draws = []
    for _ in range(n_boot):
        sample = pd.concat([groups[s] for s in rng.choice(spills, size=len(spills), replace=True)], ignore_index=True)
        draws.append(MarshRecoveryModel(columns).fit(sample).time_ratios().to_numpy())
    draws = np.array(draws)
    table = MarshRecoveryModel(columns).fit(cases).time_ratios().to_frame()
    table["low_90"], table["high_90"] = np.percentile(draws, 5, axis=0), np.percentile(draws, 95, axis=0)
    counts = design_matrix(cases).sum(axis=0)
    table["n_cases"] = [int(round(counts[ALL_FEATURES.index(name)])) for name in table.index]
    return table.round(2)


def forecast_for_scenario(scenario, treatment: str, model: MarshRecoveryModel | None = None) -> Forecast | None:
    """Forecast for a Scenario from data_model. Returns None where the evidence table has no cases:
    non-marsh shorelines, and treatments that TOOL_TREATMENT_TO_CLASS maps to None.

    The differences between treatments have not been validated out of sample (see the module docstring),
    so this is not yet a basis for ranking treatments."""
    if scenario.shoreline_type not in MARSH_SHORELINES:
        return None
    treatment_class = TOOL_TREATMENT_TO_CLASS.get(treatment)
    if treatment_class is None:
        return None
    # Screening rule (an assumption, not from the source): thick oil over most of the band counts as heavy.
    if scenario.oil_coverage >= 50 and scenario.oil_thickness >= 10:
        oiling = "heavy"
    elif scenario.oil_coverage < 20 and scenario.oil_thickness < 5:
        oiling = "light"
    else:
        oiling = "moderate"
    model = model or MarshRecoveryModel().fit(load_cases())
    return model.forecast(TOOL_OIL_TO_GROUP[scenario.oil_category], oiling, treatment_class)
