"""Provenance view of process_parameter_priors.csv (literature_priors.py). Data-access checks only; not scientific validation.

Run from the repository root:  python -m pytest tests/test_literature_priors.py
"""
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.shoreline_remediation import literature_priors as LP  # noqa: E402
from src.shoreline_remediation.evidence_catalog import NOT_IN_REPO  # noqa: E402


def test_row_counts_by_evidence():
    df = LP.load_priors()
    assert len(df) == 24
    assert LP.assumed_count(df) == 15
    assert (df["evidence"] == "SOURCED").sum() == 8
    assert (df["evidence"] == "LITERATURE").sum() == 1


def test_provenance_excludes_assumed_rows():
    prov = LP.provenance_rows()
    assert len(prov) == 9
    assert set(prov["evidence"]) == {"SOURCED", "LITERATURE"}
    assert "ASSUMED" not in set(prov["evidence"])
    assert list(prov.columns) == LP.PROVENANCE_COLUMNS


def test_missing_doi_uses_repository_phrase():
    prov = LP.provenance_rows()
    assert (prov["doi"] != "").all()
    no_doi = prov[prov["parameter_id"] == "surface_oil_depth_cm"]
    assert len(no_doi) == 1
    assert no_doi.iloc[0]["doi"] == NOT_IN_REPO == "Source not available in repository"


def test_statements_are_present():
    assert "not used to estimate a cleanup result" in LP.ASSUMED_STATEMENT
    assert "not a remediation-outcome model" in LP.ASSUMED_STATEMENT
    assert "0.7748" in LP.ASSUMED_STATEMENT and "0.7499" in LP.ASSUMED_STATEMENT
    assert "No literature-derived estimate" in LP.NO_ESTIMATE_STATEMENT


def test_module_has_no_forbidden_imports():
    source = inspect.getsource(LP)
    import_lines = [ln.strip() for ln in source.splitlines() if re.match(r"\s*(import|from)\s", ln)]
    for line in import_lines:
        assert "streamlit" not in line
        assert "process_model" not in line
        assert "process_uncertainty" not in line
    assert import_lines, "expected at least one import line"
