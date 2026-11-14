import numpy as np
import pandas as pd
import pytest

from src.shoreline_remediation import adaptive


def test_bayesian_block_posterior_matches_closed_form():
    prior_mean, prior_var = 0.0, 1.5
    sample_mean, likelihood_var = 0.9, 0.4
    post_mean, post_var = adaptive.bayesian_block_posterior(prior_mean, prior_var, sample_mean, likelihood_var)

    expected_var = 1.0 / ((1.0 / prior_var) + (1.0 / likelihood_var))
    expected_mean = expected_var * ((prior_mean / prior_var) + (sample_mean / likelihood_var))

    assert post_var == pytest.approx(expected_var)
    assert post_mean == pytest.approx(expected_mean)


def test_update_block_without_monitoring_returns_prior():
    block = pd.DataFrame(
        {
            "cell": ["c1", "c2", "c3", "c4"],
            "pred_rate": [0.4, 0.5, 0.6, 0.7],
            "max_oiling": ["NOO", "Heavy", "NOO", "Heavy"],
            "observed_rate": [0.45, 0.9, 0.62, 1.1],
        }
    )
    monitored = pd.DataFrame({"cell": [], "observed_rate": []})
    pools = (np.array([-0.2, 0.0, 0.2]), np.array([-0.1, 0.0, 0.1]))

    out = adaptive.update_block(block, monitored, pools, horizon_years=5, n_draws=1200, seed=7)

    assert len(out) == len(block)
    assert np.allclose(out["prior_median"], out["updated_median"])
    assert np.allclose(out["prior_lo90"], out["updated_lo90"])
    assert np.allclose(out["prior_hi90"], out["updated_hi90"])
