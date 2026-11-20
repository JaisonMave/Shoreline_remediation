"""Research projections: versioned scenario specs, an offline runner and standalone run records.

Research workflow only (docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md). The production dashboard and decision engine must not import this
package; tests/test_projections.py enforces that. Outputs are observed records and, from Session 3, conditional scenario
projections. Neither is a validated forecast or a recommendation.
"""
from src.shoreline_remediation.projections.catalogue import SCHEMA_VERSION
from src.shoreline_remediation.projections.runner import OutputExistsError, RunResult, normalized, run
from src.shoreline_remediation.projections.spec import ScenarioSpec, SpecError, Unsupported, check_scope, from_dict, load

__all__ = ["SCHEMA_VERSION", "OutputExistsError", "RunResult", "ScenarioSpec", "SpecError", "Unsupported", "check_scope",
           "from_dict", "load", "normalized", "run"]
