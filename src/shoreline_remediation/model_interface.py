"""Standard model interface (D15, V4 F3). Every model, simple or complex, is called the same way:

    predict(site: SiteRecord, scenario: ScenarioRequest) -> Prediction

A model that cannot give an interval, or cannot say when it is extrapolating, does not satisfy the interface
and cannot be shown. The `explanation` dict describes the model's arithmetic (per-predictor contribution in
the target's units), not a causal claim.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Allowed values (documented once).
SCOPE_IN_RANGE = "in range"
SCOPE_NEW_REGION = "new region"
SCOPE_OUTSIDE = "outside training range"
SCOPES = (SCOPE_IN_RANGE, SCOPE_NEW_REGION, SCOPE_OUTSIDE)

STATE_VALIDATED = "validated"
STATE_EXPERIMENTAL = "experimental"
STATES = (STATE_VALIDATED, STATE_EXPERIMENTAL)


@dataclass
class SiteRecord:
    """A fixed place plus the predictors a model declares it needs (in `fields`)."""
    site_id: str
    habitat: str = ""
    region: str = ""
    lat: float | None = None
    lon: float | None = None
    oiling: str | None = None
    fields: dict = field(default_factory=dict)


@dataclass
class ScenarioRequest:
    """A treatment (or none) and a horizon in years."""
    treatment: str | None = None
    horizon_years: int = 5


@dataclass
class Prediction:
    value: float
    unit: str
    interval_lo: float
    interval_hi: float
    interval_level: float
    interval_method: str
    scope: str
    scope_reasons: list
    explanation: dict
    evidence_grade: str
    model_id: str
    model_version: str
    state: str

    def __post_init__(self):
        if self.scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}, got {self.scope!r}")
        if self.state not in STATES:
            raise ValueError(f"state must be one of {STATES}, got {self.state!r}")
        if not (self.interval_lo <= self.value <= self.interval_hi):
            raise ValueError(f"prediction value {self.value} is outside its interval "
                             f"[{self.interval_lo}, {self.interval_hi}]")


@runtime_checkable
class Model(Protocol):
    model_id: str
    model_version: str
    state: str

    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        ...


class BaseModel(ABC):
    """Convenience base for registry adapters; sets model_id/version/state and enforces predict()."""
    model_id: str = ""
    model_version: str = ""
    state: str = STATE_EXPERIMENTAL

    @abstractmethod
    def predict(self, site: SiteRecord, scenario: ScenarioRequest) -> Prediction:
        raise NotImplementedError
