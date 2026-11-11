"""Tests for the oil property lookup.

Run from the repository root:  python -m pytest tests
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shoreline_remediation.oil_library import find_oil, load_oils, oil_category, scenario_oil_inputs, search_options  # noqa: E402


def test_table_is_complete_and_plausible():
    oils = load_oils()
    assert len(oils) > 1400 and oils["oil_id"].is_unique
    crude = oils[oils["product_type"] == "Crude Oil NOS"]
    assert crude["api_gravity"].between(0, 70).mean() > 0.99
    assert crude["density_kg_m3"].dropna().between(700, 1100).all()


def test_search_finds_oils_by_name():
    found = find_oil("alaska north slope")
    assert len(found) >= 5 and found["name"].str.lower().str.contains("alaska north slope").all()
    assert find_oil("no such oil name").empty


def test_category_rule():
    assert oil_category(35) == "light"
    assert oil_category(20) == "medium"
    assert oil_category(12) == "heavy"
    assert oil_category(35, pour_point_c=30, temperature_c=10) == "solid"
    assert oil_category(35, pour_point_c=float("nan")) == "light"


def test_scenario_inputs_use_measured_values():
    bunker = scenario_oil_inputs(find_oil("bunker c fuel oil").iloc[0]["oil_id"], temperature_c=25)
    assert bunker["oil_category"] == "heavy" and bunker["api_gravity"] < 15
    light = scenario_oil_inputs(find_oil("south louisiana").iloc[0]["oil_id"])
    assert light["oil_category"] == "light"
    with pytest.raises(KeyError):
        scenario_oil_inputs("XX00000")


def test_search_options_for_dashboard():
    options = search_options("alaska north slope")
    assert options and all(label.startswith("ALASKA NORTH SLOPE") or "API" in label for _, label in options)
    ids = [oil_id for oil_id, _ in options]
    assert all(scenario_oil_inputs(oil_id)["oil_category"] in {"light", "medium", "heavy", "solid"} for oil_id in ids)
    assert search_options("   ") == [] and search_options("no such oil name") == []
