"""Habitat table keyed to the ESI code (decision D36). Table: data/knowledge/tables/habitat.csv.

Every habitat string used anywhere in the code ("sand_beach", "sandy_beach", "mixed_sediment", "mixed", "gravel_beach", "cobble",
"marsh", "salt_marsh", "salt marsh", "rock", "bedrock", "rocky_shore", "mangrove", ...) is an ALIAS of one ESI row. Strings are not
renamed across the codebase; `normalise()` is the fix.

    normalise("sand_beach")            -> "3A"
    normalise("cobble")                -> "6A"   (resolved explicitly, D36: the Shoreline Assessment Manual puts pebbles to boulders in ESI 6A)
    normalise("bedrock", "low")        -> "8A"   (ASSUMED: low wave exposure = sheltered rocky shore)
    normalise("something odd")         -> "unknown"  (strict=True raises KeyError)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

HABITAT_CSV = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "tables" / "habitat.csv"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Habitat:
    esi_code: str
    name: str
    tier: str
    rule_key: str
    habitat_class: str
    evidence_family: str
    noaa_ratings_esi: str
    oil_penetration_depth: str
    burial_risk: str
    persistence_driver: str
    asphalt_pavement_risk: str
    descriptor_pages: str
    scope_note: str
    variant_of: str
    variant_when_exposure: tuple


def _key(text: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(text).strip().lower())


@lru_cache(maxsize=1)
def _load() -> tuple[dict, dict]:
    df = pd.read_csv(HABITAT_CSV, dtype=str).fillna("")
    rows, aliases = {}, {}
    for r in df.itertuples():
        rows[r.esi_code] = Habitat(
            r.esi_code, r.name, r.tier, r.rule_key, r.habitat_class, r.evidence_family, r.noaa_ratings_esi,
            r.oil_penetration_depth, r.burial_risk, r.persistence_driver, r.asphalt_pavement_risk, r.descriptor_pages,
            r.scope_note, r.variant_of, tuple(x for x in r.variant_when_exposure.split("|") if x))
        for a in [r.esi_code, *r.aliases.split("|")]:
            k = _key(a)
            if not k:
                continue
            if k in aliases and aliases[k] != r.esi_code:
                raise ValueError(f"habitat alias '{k}' belongs to both {aliases[k]} and {r.esi_code}")
            aliases[k] = r.esi_code
    return rows, aliases


def table() -> dict:
    """ESI code -> Habitat."""
    return dict(_load()[0])


def normalise(name, wave_exposure: str | None = None, *, strict: bool = False) -> str:
    """ESI code for any habitat string in use; "unknown" when not recognised (KeyError if strict)."""
    rows, aliases = _load()
    esi = aliases.get(_key(name)) if name is not None else None
    if esi is None:
        if strict:
            raise KeyError(f"unknown habitat '{name}'")
        return UNKNOWN
    if wave_exposure:
        for variant in rows.values():
            if variant.variant_of == esi and str(wave_exposure).lower() in variant.variant_when_exposure:
                return variant.esi_code
    return esi


def get(name, wave_exposure: str | None = None) -> Habitat | None:
    """Habitat row for a string or ESI code (None when unknown)."""
    esi = normalise(name, wave_exposure)
    return _load()[0].get(esi)


def rule_key(name, wave_exposure: str | None = None, default: str | None = None) -> str | None:
    """Shoreline string the screening rules understand (screening_rule.csv `shoreline` field)."""
    h = get(name, wave_exposure)
    return h.rule_key if h else default


def habitat_class(name, wave_exposure: str | None = None) -> str:
    """Habitat class of evidence_verdicts.csv ("marsh", "mangrove", "rocky/hard", "sand/gravel beach", "other")."""
    h = get(name, wave_exposure)
    return h.habitat_class if h else "other"
