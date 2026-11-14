"""F5 priors, default transport path, and the Sobol estimator. Does not run the gated analysis."""
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
from src.shoreline_remediation.process_model import simulate_selected_scenario  # noqa: E402
from src.shoreline_remediation.process_uncertainty import saltelli_units, sobol_indices  # noqa: E402
from src.shoreline_remediation.shoreline_transport import PARAMETER_TABLE, simulate_transect  # noqa: E402

PRIORS = ROOT / "data" / "knowledge" / "process_parameter_priors.csv"
DAYS = [0, 7, 30, 90, 180, 365, 730]


def test_priors_cover_every_transport_parameter():
    table = pd.read_csv(PRIORS)
    names = {row[0] for row in PARAMETER_TABLE}
    assert names <= set(table.table_name)
    assert len(names) == 19
    assert set(table.distribution) <= {"lognormal", "uniform", "normal", "fixed"}
    for row in table.itertuples(index=False):
        text = " ".join(str(part) for part in (row.source, row.doi, row.literature_row))
        sourced = ("10." in text) or ("NOAA Shoreline Assessment Manual" in text)
        assumed = "ASSUMED, wide" in text
        assert sourced or assumed, row.parameter_id


def test_optional_inputs_default_to_the_screening_path():
    scenario = Scenario("marsh", oil_category="heavy", oil_coverage=80, oil_thickness=25,
                        penetration_depth_cm=8, season="winter", temperature_c=15)
    frame = simulate_transect(scenario, "no_cleanup", DAYS)
    forwarded = simulate_selected_scenario(scenario, "no_cleanup", DAYS)
    expected = [100.00, 95.79, 84.79, 67.19, 53.73, 41.46, 31.75]
    assert frame.residual_oil_pct_of_initial.tolist() == expected
    assert forwarded.residual_oil_pct_of_initial.tolist() == expected
    # Passing the new arguments is what makes thickness, penetration and season matter.
    thicker = simulate_transect(scenario, "no_cleanup", [365], oil_thickness=25)
    assert thicker.residual_oil_pct_of_initial.iloc[0] != expected[5]
    summer = simulate_transect(scenario, "no_cleanup", [365], season="summer")
    assert summer.residual_oil_pct_of_initial.iloc[0] != expected[5]
    buried = simulate_transect(scenario, "no_cleanup", [0, 1], penetration_depth_cm=20)
    buried = buried.loc[buried.survey_day == 0]
    assert buried.subsurface_oil_mass_kg.iloc[0] > 0
    assert buried.residual_oil_pct_of_initial.iloc[0] == pytest.approx(100.0, abs=0.01)


def test_sobol_estimator_on_an_additive_function():
    """Y = 2 X1 + 0.5 X2, Xi uniform on [0, 1]. Analytical S1 = 4/4.25, S2 = 0.25/4.25."""
    n, k = 512, 2
    a, b = saltelli_units(n, k, seed=20261114)

    def y(unit):
        return 2.0 * unit[:, 0] + 0.5 * unit[:, 1]

    y_ab = np.empty((k, n))
    for i in range(k):
        ab = a.copy()
        ab[:, i] = b[:, i]
        y_ab[i] = y(ab)
    s1, st = sobol_indices(y(a), y(b), y_ab)
    analytical = np.array([4.0 / 4.25, 0.25 / 4.25])
    assert s1 == pytest.approx(analytical, abs=0.05)
    assert st == pytest.approx(analytical, abs=0.05)
