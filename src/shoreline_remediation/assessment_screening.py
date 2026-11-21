"""Reproduce the assessment behind a replayed what-if scenario (projection spec version 2).

Two tested boundaries stay as they were: the research package (`projections`) never imports the decision engine, and only the
dashboard panel imports the research package. A user-defined what-if must still respect screening when it is replayed outside
the dashboard, so the projections CLI loads this adapter lazily, for version-2 files only, and passes `reproduce` to the runner.
It re-runs the authoritative pipeline (`decision_pipeline.run_decision`) from the recorded assessment context and returns the
report; the runner reads the technique's retreat row from the existing inventory. Nothing here changes a screening status, a
recommendation or an order, and Streamlit is never imported. Eligibility text saved in a download is ignored.

Only the Bay Jimmy worked-example path is replayable: a mapped marsh cell from the site table, run as the dashboard runs it
(`ui_pipeline.decision_for_site`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache

# Must equal ui_pipeline.SITE_KEYS and ui_pipeline.UI_DRAWS (ui_pipeline imports Streamlit, so they are restated here; a test
# keeps them equal).
EXTRA_SITE_KEYS = ("max_oiling", "status", "esi_main", "lat", "lon", "cell", "basin", "segment", "cell_2km")
DASHBOARD_DRAWS = 3000


def site_keys() -> tuple:
    from src.shoreline_remediation import site_evidence as se
    return (*se.FEATURES, *EXTRA_SITE_KEYS)


def _clean(value):
    import pandas as pd
    try:
        if value is not None and not isinstance(value, str) and pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def site_items_sha256(items) -> str:
    """Checksum of the site values the pipeline reads, so a replay notices a changed site table."""
    return hashlib.sha256(json.dumps([[k, v] for k, v in items], default=str).encode()).hexdigest()


@lru_cache(maxsize=8)
def site_items(cell: str) -> tuple:
    """The site values for a mapped cell, in the form ui_pipeline.site_items gives the pipeline."""
    from src.shoreline_remediation import site_evidence as se
    sites = se.load_sites()
    match = sites[sites.cell == cell]
    if match.empty:
        raise LookupError(f"cell '{cell}' is not in the site table")
    row = match.iloc[0].to_dict()
    return tuple((k, _clean(row.get(k))) for k in site_keys())


def context_from_run_spec(run_spec) -> dict | None:
    """The assessment context of a dashboard run record spec ('site', items, oil, season[, n_draws]); None for other entries."""
    if not run_spec or run_spec[0] != "site":
        return None
    _, items, oil, season, *rest = run_spec
    return {"entry": "mapped_site", "cell": str(dict(items).get("cell")), "habitat": "salt_marsh", "oil": oil, "season": season,
            "n_draws": int(rest[0]) if rest else DASHBOARD_DRAWS, "site_sha256": site_items_sha256(items)}


@lru_cache(maxsize=8)
def _report(cell: str, oil, season, n_draws: int):
    from src.shoreline_remediation.decision_pipeline import run_decision
    site = {k: v for k, v in site_items(cell) if v is not None}
    return run_decision(site, habitat="salt_marsh", oil=oil, season=season, n_draws=n_draws)


@dataclass(frozen=True)
class Assessment:
    report: object | None          # DecisionReport, or None when the assessment cannot be reproduced
    status: str                    # "reproduced", "site_not_found" or "site_changed"
    reason: str
    pipeline: dict


def reproduce(spec) -> Assessment:
    """Re-run the assessment recorded in spec.assessment_context. Never raises for an outcome the user should see."""
    ctx = spec.assessment_context or {}
    try:
        items = site_items(ctx["cell"])
    except (LookupError, KeyError) as exc:
        return Assessment(None, "site_not_found", f"The assessment cannot be reproduced: {exc}.", {})
    if site_items_sha256(items) != ctx.get("site_sha256"):
        return Assessment(None, "site_changed", "The site values in this checkout differ from those the download was made "
                          "with, so the technique cannot be re-screened for the same assessment.", {})
    report = _report(ctx["cell"], ctx.get("oil"), ctx.get("season"), int(ctx["n_draws"]))
    version = getattr(report, "version", {}) or {}
    pipeline = {"function": "decision_pipeline.run_decision", "pipeline_version": version.get("pipeline_version"),
                "seed": version.get("seed"), "n_draws": version.get("n_draws"),
                "decision_outcome": getattr(report, "decision_outcome", None)}
    return Assessment(report, "reproduced", "", pipeline)
