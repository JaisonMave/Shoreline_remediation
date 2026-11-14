"""Cached calls into the decision pipeline for the dashboard (decision D40).

decision_pipeline.run_decision is the single source of truth for the recommendation classes. This module only wraps it in
Streamlit caches, so a click on an unrelated widget does not re-run it. The pipeline file is read-only for the dashboard.
"""
from __future__ import annotations

import dataclasses

import streamlit as st

from src.shoreline_remediation import site_evidence as se

UI_DRAWS = 3000                      # Monte Carlo draws used in the dashboard (the pipeline default is 5000)
SITE_KEYS = (*se.FEATURES, "max_oiling", "status", "esi_main", "lat", "lon", "cell", "basin", "segment", "cell_2km")


def _clean(value):
    try:
        import pandas as pd
        if value is not None and not isinstance(value, str) and pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def site_items(site: dict) -> tuple:
    """Hashable, small version of a site dict (what the pipeline reads)."""
    return tuple((k, _clean(site.get(k))) for k in SITE_KEYS)


@st.cache_data(show_spinner="Running the decision pipeline...")
def decision_for_site(items: tuple, oil: str | None, season: str | None, n_draws: int = UI_DRAWS):
    """Pipeline report for one marsh edge cell (site dict). Returns (report, error_text)."""
    from src.shoreline_remediation.decision_pipeline import run_decision
    site = {k: v for k, v in items if v is not None}
    try:
        return run_decision(site, habitat="salt_marsh", oil=oil, season=season, n_draws=n_draws), None
    except (ValueError, KeyError, TypeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


@st.cache_data(show_spinner="Running the decision pipeline...")
def decision_for_scenario(scenario_fields: tuple, oiling_class: str | None, oil: str | None, season: str | None,
                          habitat: str | None = None, n_draws: int = UI_DRAWS):
    """Pipeline report for a generic Scenario (given as a tuple of its fields). Returns (report, error_text)."""
    from src.shoreline_remediation.data_model import Scenario
    from src.shoreline_remediation.decision_pipeline import run_decision
    scenario = Scenario(**dict(scenario_fields))
    try:
        return run_decision(scenario, habitat=habitat, oiling_class=oiling_class, oil=oil, season=season, n_draws=n_draws), None
    except (ValueError, KeyError, TypeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def scenario_items(scenario) -> tuple:
    return tuple(dataclasses.asdict(scenario).items())
