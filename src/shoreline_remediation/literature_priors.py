"""Provenance view of the process-parameter priors table (V5.2). No Streamlit, no calculation, no decision logic.

data/knowledge/process_parameter_priors.csv holds the priors that the F5 process model samples. Its `evidence` column says where
each row came from:

- SOURCED: a published study or supplied manual states the value.
- LITERATURE: a value derived from literature_effects.csv records (a bracket, not a marsh rate).
- ASSUMED: a project placeholder or a wide guess. Not measured and not validated.

`provenance_rows()` returns only the SOURCED and LITERATURE rows, so the cited material is never mixed with assumptions. The table
is an input record for an experimental, illustrative process model. It is not a remediation-outcome model and gives no
literature-derived estimate of cleanup performance.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .evidence_catalog import NOT_IN_REPO

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data" / "knowledge" / "process_parameter_priors.csv"

CITED_EVIDENCE = ("SOURCED", "LITERATURE")
PROVENANCE_COLUMNS = ["parameter_id", "table_name", "median", "low", "high", "unit", "evidence", "source", "doi"]
REQUIRED_COLUMNS = PROVENANCE_COLUMNS + ["notes"]

ASSUMED_STATEMENT = ("Assumed coefficients are wide placeholders that are not used to estimate a cleanup result, and this table is not a "
                     "remediation-outcome model: the F5 process model that samples it failed its promotion gate (calibrated held-out error "
                     "0.7748 against 0.7499 for the empirical comparison, results/f5_process/summary.txt).")
NO_ESTIMATE_STATEMENT = ("No literature-derived estimate is available for this habitat, technology and outcome in the repository.")


def load_priors(path=DEFAULT) -> pd.DataFrame:
    """The whole priors table. A missing file raises FileNotFoundError; a missing required column raises ValueError."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"doi": str, "source": str, "notes": str, "evidence": str})
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} lacks required column(s): {', '.join(missing)}")
    return df


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def provenance_rows(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rows whose evidence is SOURCED or LITERATURE, with the columns needed to cite them. An empty DOI reads NOT_IN_REPO."""
    if df is None:
        df = load_priors()
    cited = df[df["evidence"].map(_clean).isin(CITED_EVIDENCE)][PROVENANCE_COLUMNS].copy()
    cited["doi"] = cited["doi"].map(lambda v: _clean(v) or NOT_IN_REPO)
    return cited.reset_index(drop=True)


def assumed_count(df: pd.DataFrame | None = None) -> int:
    """Number of ASSUMED rows (excluded from provenance_rows)."""
    if df is None:
        df = load_priors()
    return int((df["evidence"].map(_clean) == "ASSUMED").sum())
