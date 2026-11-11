"""Event study for panel data: many sites observed once a year, some exposed to an event and some not.

This is the estimator for outcome data that comes as site-by-year tables: field vegetation surveys, annual
satellite composites, or SCAT segments once they are matched to an outcome. (recovery_timeseries.py handles
the other case, one dense monthly series for a single pair of sites.)

Model, fitted by least squares:

    y[site, year] = site effect + year effect (optionally one per group) + sum over k of b[k] * exposed * 1[event time = k]

    event time k = year - first post-event survey year of that site; k = -1 is the reference.
    b[k] for k >= 0 is the effect k surveys after the event, relative to unexposed sites.
    b[k] for k < -1 should be near zero. If it is not, exposed and unexposed sites were already diverging
    before the event and the later estimates cannot be trusted (the "parallel trends" check).

Standard errors are clustered by site, so repeated years of one site are not counted as independent.
The estimates are comparisons between exposed and less exposed sites, not proof of cause: anything else
that hit the exposed sites in the same years is included in b[k].
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm


@dataclass
class EventStudyResult:
    effects: pd.DataFrame  # event_time, estimate, std_error, ci_low, ci_high (90% interval)
    pretrend_p_value: float  # joint test that all pre-event effects are zero; small values are a warning
    n_exposed_sites: int
    n_control_sites: int
    n_observations: int

    def recovery_lag(self) -> int | None:
        """First event time, at or after the largest post-event effect, whose 90% interval includes zero.
        None if the largest effect is itself not distinguishable from zero, or if no recovery is seen."""
        post = self.effects[self.effects["event_time"] >= 0].reset_index(drop=True)
        peak = int(post["estimate"].abs().idxmax())
        if post.loc[peak, "ci_low"] <= 0 <= post.loc[peak, "ci_high"]:
            return None
        later = post.iloc[peak + 1:]
        recovered = later[(later["ci_low"] <= 0) & (later["ci_high"] >= 0)]
        return int(recovered["event_time"].iloc[0]) if len(recovered) else None


def _dummies(values: pd.Series) -> np.ndarray:
    return pd.get_dummies(values, dtype=float).to_numpy()


def event_study(panel: pd.DataFrame, outcome: str, exposed: str, first_post: str, unit: str = "site",
                time: str = "year", group: str | None = None, leads: int = 3, lags: int = 5) -> EventStudyResult:
    """Fit the event study.

    panel       one row per site and year
    outcome     column with the measured value
    exposed     column, True for exposed sites and False for comparison sites (constant within a site)
    first_post  column with each site's first post-event survey year (needed for comparison sites too)
    group       optional column; if given, each group gets its own year effects, so exposed sites are only
                compared with unexposed sites of the same group (for example the same marsh type)
    """
    data = panel.dropna(subset=[outcome, exposed, first_post]).copy()
    data["_k"] = (data[time] - data[first_post]).astype(int)
    data = data[(data["_k"] >= -leads) & (data["_k"] <= lags)].reset_index(drop=True)
    is_exposed = data[exposed].astype(bool).to_numpy()
    event_times = [k for k in range(-leads, lags + 1) if k != -1]
    terms = np.column_stack([(is_exposed & (data["_k"].to_numpy() == k)).astype(float) for k in event_times])

    period = data[time].astype(str) if group is None else data[group].astype(str) + "|" + data[time].astype(str)
    fixed = np.column_stack([_dummies(data[unit]), _dummies(period)])
    # Remove site and year effects from the outcome and from the event terms, then regress one on the other.
    y = data[outcome].to_numpy(float)
    y_resid = y - fixed @ np.linalg.lstsq(fixed, y, rcond=None)[0]
    x_resid = terms - fixed @ np.linalg.lstsq(fixed, terms, rcond=None)[0]
    xtx_inv = np.linalg.pinv(x_resid.T @ x_resid)
    beta = xtx_inv @ x_resid.T @ y_resid
    residual = y_resid - x_resid @ beta

    # Cluster-robust covariance (sites as clusters), with the usual small-sample correction.
    sites = data[unit].to_numpy()
    scores = pd.DataFrame(x_resid * residual[:, None]).groupby(sites).sum().to_numpy()
    n, n_sites = len(data), len(scores)
    n_params = terms.shape[1] + np.linalg.matrix_rank(fixed)
    correction = n_sites / (n_sites - 1) * (n - 1) / max(n - n_params, 1)
    covariance = correction * xtx_inv @ (scores.T @ scores) @ xtx_inv
    std_error = np.sqrt(np.diag(covariance))

    z = norm.ppf(0.95)
    effects = pd.DataFrame({"event_time": event_times, "estimate": beta, "std_error": std_error,
                            "ci_low": beta - z * std_error, "ci_high": beta + z * std_error})
    reference = pd.DataFrame({"event_time": [-1], "estimate": [0.0], "std_error": [0.0], "ci_low": [0.0], "ci_high": [0.0]})
    effects = pd.concat([effects, reference]).sort_values("event_time").reset_index(drop=True)

    pre = [i for i, k in enumerate(event_times) if k < -1]
    if pre:
        wald = float(beta[pre] @ np.linalg.pinv(covariance[np.ix_(pre, pre)]) @ beta[pre])
        pretrend_p = float(chi2.sf(wald, len(pre)))
    else:
        pretrend_p = float("nan")
    site_exposure = data.groupby(unit)[exposed].first().astype(bool)
    return EventStudyResult(effects, pretrend_p, int(site_exposure.sum()), int((~site_exposure).sum()), n)
