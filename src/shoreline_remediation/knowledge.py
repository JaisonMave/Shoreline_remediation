"""Knowledge-base loader (D16, V4 F2): the FAST-like screening rules and the ASSUMED ecological scores live in
editable CSV tables, not in Python. This module reads them and reproduces the engine's answers exactly.

Tables (data/knowledge/tables/):
    screening_rule.csv   ordered feasibility rules (replaces fast_engine._classify_treatment)
    ecological_score.csv ordered ecological (do-no-harm) scores (replaces decision_framework._ecological_score)
    technology.csv       descriptive technology catalogue
    evidence_effect.csv  Zengel 2015 vegetation and Zengel 2022 erosion priors, with source/design/n/period

Condition mini-language (documented, machine-readable)
------------------------------------------------------
A rule matches a treatment if its `technology` field lists that treatment (a `|`-separated set) or is `*`,
AND its `condition` is true. A condition is zero or more clauses joined by `;` (logical AND); an empty
condition is always true. Each clause is `field op value`:

    fields : shoreline, oil, exposure, sensitivity (lowercased strings); coverage, penetration (floats);
             surface_oil (bool); permeability, accessibility (strings, case preserved as in the Scenario)
    ops    : in, not_in (value is a `|`-separated set); <, <=, >, >=, == (single value)

Rules are tried in ascending `order`; the first matching rule wins. This mirrors the original sequential
`if ... return` fall-through: each `return` is one row and compound OR conditions are split into rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import pandas as pd

TABLES = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "tables"
SCREENING_RULE_CSV = TABLES / "screening_rule.csv"
ECOLOGICAL_SCORE_CSV = TABLES / "ecological_score.csv"
TECHNOLOGY_CSV = TABLES / "technology.csv"
EVIDENCE_EFFECT_CSV = TABLES / "evidence_effect.csv"

REQUIRED_PROVENANCE = ("source", "status")

# field name -> function reading it from a Scenario, preserving the original case handling exactly.
_FIELDS: dict[str, Callable] = {
    "shoreline": lambda s: s.shoreline_type.lower(),
    "oil": lambda s: s.oil_category.lower(),
    "exposure": lambda s: s.wave_exposure.lower(),
    "sensitivity": lambda s: s.shoreline_sensitivity.lower(),
    "coverage": lambda s: float(s.oil_coverage),
    "penetration": lambda s: float(s.penetration_depth_cm),
    "surface_oil": lambda s: bool(s.surface_oil),
    "permeability": lambda s: s.substrate_permeability,
    "accessibility": lambda s: s.accessibility,
}
_NUMERIC_OPS: dict[str, Callable] = {
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
}


@dataclass(frozen=True)
class _Clause:
    field: str
    op: str
    value: object


@dataclass
class Rule:
    rule_id: str
    order: int
    technologies: frozenset
    any_technology: bool
    clauses: tuple
    verdict: str

    def matches_treatment(self, treatment: str) -> bool:
        return self.any_technology or treatment in self.technologies

    def condition_holds(self, scenario) -> bool:
        return all(_clause_holds(c, scenario) for c in self.clauses)


def _parse_bool(text: str) -> bool:
    return text.strip().lower() == "true"


def _parse_clause(raw: str) -> _Clause:
    field, op, value = raw.strip().split(None, 2)
    if field not in _FIELDS:
        raise ValueError(f"unknown condition field '{field}' in clause '{raw}'")
    if op in ("in", "not_in"):
        return _Clause(field, op, frozenset(value.split("|")))
    if op in _NUMERIC_OPS:
        return _Clause(field, op, float(value))
    if op == "==":
        parsed = _parse_bool(value) if field == "surface_oil" else value
        return _Clause(field, op, parsed)
    raise ValueError(f"unknown operator '{op}' in clause '{raw}'")


def _parse_condition(text: object) -> tuple:
    if text is None or (isinstance(text, float) and pd.isna(text)) or str(text).strip() == "":
        return ()
    return tuple(_parse_clause(part) for part in str(text).split(";") if part.strip())


def _clause_holds(clause: _Clause, scenario) -> bool:
    actual = _FIELDS[clause.field](scenario)
    if clause.op == "in":
        return actual in clause.value
    if clause.op == "not_in":
        return actual not in clause.value
    if clause.op == "==":
        return actual == clause.value
    return _NUMERIC_OPS[clause.op](actual, clause.value)


def _parse_technologies(text: str) -> tuple[frozenset, bool]:
    text = str(text).strip()
    if text == "*":
        return frozenset(), True
    return frozenset(text.split("|")), False


def _load_rules(path: Path, verdict_column: str) -> tuple[Rule, ...]:
    df = pd.read_csv(path)
    _check_provenance(df, path)
    rules = []
    for _, r in df.sort_values("order").iterrows():
        techs, any_tech = _parse_technologies(r["technology"])
        rules.append(Rule(rule_id=str(r["rule_id"]), order=int(r["order"]), technologies=techs,
                          any_technology=any_tech, clauses=_parse_condition(r.get("condition")),
                          verdict=r[verdict_column]))
    return tuple(rules)


def _check_provenance(df: pd.DataFrame, path: Path) -> None:
    for column in REQUIRED_PROVENANCE:
        if column not in df.columns:
            raise ValueError(f"{path.name} is missing the required '{column}' column")
        blank = df[column].isna() | (df[column].astype(str).str.strip() == "")
        if blank.any():
            raise ValueError(f"{path.name} has rows without a {column}: ids {list(df.loc[blank, df.columns[0]])}")


@lru_cache(maxsize=1)
def load_screening_rules(path: str = str(SCREENING_RULE_CSV)) -> tuple[Rule, ...]:
    return _load_rules(Path(path), "verdict")


@lru_cache(maxsize=1)
def _ecological_rules(path: str = str(ECOLOGICAL_SCORE_CSV)) -> tuple:
    df = pd.read_csv(Path(path))
    _check_provenance(df, Path(path))
    rules = []
    for _, r in df.sort_values("order").iterrows():
        techs, any_tech = _parse_technologies(r["technology"])
        rules.append((Rule(rule_id=str(r["rule_id"]), order=int(r["order"]), technologies=techs,
                           any_technology=any_tech, clauses=_parse_condition(r.get("condition")), verdict=""),
                      float(r["score"]), str(r["basis"])))
    return tuple(rules)


def classify(treatment: str, scenario) -> str:
    """Feasibility verdict for a treatment and scenario, read from screening_rule.csv (D16, F2)."""
    for rule in load_screening_rules():
        if rule.matches_treatment(treatment) and rule.condition_holds(scenario):
            return rule.verdict
    return "conditional"


def ecological_score(treatment: str, scenario) -> float:
    """ASSUMED ecological (do-no-harm) score, read from ecological_score.csv (D16, F2)."""
    return ecological_score_explanation(treatment, scenario)["score"]


def ecological_score_explanation(treatment: str, scenario) -> dict:
    """Score and rule rationale for the ecological suitability of a treatment."""
    for rule, score, basis in _ecological_rules():
        if rule.matches_treatment(treatment) and rule.condition_holds(scenario):
            return {"score": score, "basis": basis}
    return {"score": 5.0, "basis": "Neutral ecological baseline because no treatment-specific rule was triggered."}


@lru_cache(maxsize=1)
def load_technology(path: str = str(TECHNOLOGY_CSV)) -> pd.DataFrame:
    df = pd.read_csv(Path(path))
    _check_provenance(df, Path(path))
    return df


@lru_cache(maxsize=1)
def load_evidence_effects(path: str = str(EVIDENCE_EFFECT_CSV)) -> pd.DataFrame:
    df = pd.read_csv(Path(path))
    _check_provenance(df, Path(path))
    return df


def all_table_paths() -> tuple[Path, ...]:
    return (SCREENING_RULE_CSV, ECOLOGICAL_SCORE_CSV, TECHNOLOGY_CSV, EVIDENCE_EFFECT_CSV)
