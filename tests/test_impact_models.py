"""Tests for the shoreline transport model and the marsh recovery model.

Run from the repository root:  python -m pytest tests
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.data_model import Scenario  # noqa: E402
from src.shoreline_remediation.marsh_recovery_model import (  # noqa: E402
    OIL_GROUPS, TREATMENT_CLASSES, MarshRecoveryModel, design_matrix, forecast_for_scenario, load_cases,
)
from src.shoreline_remediation.shoreline_transport import simulate_transect  # noqa: E402

DAYS = [0, 7, 30, 90, 180, 365, 730]


@pytest.mark.parametrize("shoreline", ["sand_beach", "mixed_sediment", "cobble", "marsh", "bedrock"])
@pytest.mark.parametrize("oil", ["light", "heavy"])
def test_untreated_oil_mass_never_grows(shoreline, oil):
    """With no cleanup, oil can only leave the segment. Before the dispersion term was put in flux form,
    heavy oil on a sand beach rose to 117% of its initial mass by day 30."""
    scenario = Scenario(shoreline, oil_category=oil, oil_coverage=60, oil_thickness=10)
    residual = simulate_transect(scenario, "no_cleanup", DAYS)["residual_oil_pct_of_initial"].to_numpy()
    assert residual[0] == pytest.approx(100.0, abs=0.01)
    assert residual.max() <= 100.01
    assert np.all(np.diff(residual) <= 0.01)


def test_case_table_is_well_formed():
    everything = load_cases(included_only=False)
    included = load_cases()
    assert len(included) >= 50
    assert set(included["oil_group"]) <= set(OIL_GROUPS)
    assert set(included["treatment_class"]) <= set(TREATMENT_CLASSES)
    assert (included["lo"] < included["hi"]).all()
    assert everything["case_id"].is_unique
    # Every excluded row must say why.
    assert everything.loc[everything["include"] == 0, "flags"].notna().all()


def test_estimator_recovers_known_effects():
    """Simulate recovery times with known effects, observe them only as bounds at inspection times chosen
    independently of the outcome, and check that the fit returns the effects it was given."""
    rng = np.random.default_rng(7)
    n = 4000
    cases = pd.DataFrame({
        "oil_group": rng.choice(OIL_GROUPS, size=n),
        "oiling": rng.choice(["light", "moderate", "heavy", "unstated"], size=n),
        "treatment_class": rng.choice(TREATMENT_CLASSES, size=n),
        "setting": rng.choice(["spill", "field_experiment"], size=n),
    })
    truth = np.array([np.log(3.0), 0.0, 0.0, 0.7, -0.7, 0.0, 0.9, -0.5, 0.0])
    sigma = 0.8
    time = np.exp(design_matrix(cases)[:, :len(truth)] @ truth + sigma * rng.standard_normal(len(cases)))
    first = rng.choice([0.5, 1.0, 2.0, 4.0], size=len(cases))
    second = first * rng.choice([2.0, 4.0], size=len(cases))
    cases["lo"] = np.where(time <= first, 0.0, np.where(time <= second, first, second))
    cases["hi"] = np.where(time <= first, first, np.where(time <= second, second, np.inf))
    model = MarshRecoveryModel(prior_sd=10.0).fit(cases)
    assert np.abs(model.coef_ - truth).max() < 0.15
    assert model.sigma_ == pytest.approx(sigma, abs=0.1)


def test_forecast_is_only_given_where_there_is_evidence():
    model = MarshRecoveryModel().fit(load_cases())
    marsh = Scenario("marsh", oil_category="heavy", oil_coverage=80, oil_thickness=25)
    forecast = forecast_for_scenario(marsh, "manual_removal", model)
    assert forecast.low_years < forecast.median_years < forecast.high_years
    assert 0.0 <= forecast.prob_within_2yr <= forecast.prob_within_5yr <= 1.0
    assert forecast_for_scenario(marsh, "bioremediation", model) is None  # no cases in the source table
    assert forecast_for_scenario(Scenario("sand_beach"), "manual_removal", model) is None  # not a marsh
