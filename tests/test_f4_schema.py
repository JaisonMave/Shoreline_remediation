"""Tests for Task F4 (D14 common multi-site data schema): validation rules and small-table reconciliation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.shoreline_remediation import schema

ROOT = Path(__file__).resolve().parents[1]


def test_validate_rejects_unknown_variable():
    df = pd.DataFrame([{
        "event_id": "ev1",
        "variable": "nonexistent_variable_xyz",
        "value": 1.5,
        "unit": "m/yr",
        "original_value": 1.5,
        "original_unit": "m/yr",
        "matrix": "shoreline",
        "depth_top": np.nan,
        "depth_bottom": np.nan,
        "basis": "na",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": "",
        "lab_method": "test",
        "value_type": "measured",
    }])
    with pytest.raises(ValueError, match="not in dictionary"):
        schema.validate("observation", df)


def test_unit_conversion_keeps_original_value_and_unit():
    raw = pd.DataFrame([
        {
            "event_id": "ev1",
            "variable": "tpah_soil",
            "value": 2500.0,
            "unit": "PPB",
            "matrix": "soil",
            "depth_top": 0.0,
            "depth_bottom": 2.0,
            "basis": "dry",
            "censor_flag": "measured",
            "detection_limit": np.nan,
            "qualifier": "",
            "lab_method": "GCMS",
            "value_type": "measured",
        },
        {
            "event_id": "ev2",
            "variable": "shoreline_retreat_rate",
            "value": 2.4,
            "unit": "m yr-1",
            "matrix": "shoreline",
            "depth_top": np.nan,
            "depth_bottom": np.nan,
            "basis": "na",
            "censor_flag": "measured",
            "detection_limit": np.nan,
            "qualifier": "",
            "lab_method": "transect",
            "value_type": "measured",
        },
    ])
    conv = schema.convert_units(raw)
    valid = schema.validate("observation", conv)
    assert np.isclose(valid.loc[0, "value"], 2.5)
    assert valid.loc[0, "unit"] == "mg/kg"
    assert np.isclose(valid.loc[0, "original_value"], 2500.0)
    assert valid.loc[0, "original_unit"] == "PPB"
    assert valid.loc[1, "unit"] == "m/yr"
    assert valid.loc[1, "original_unit"] == "m yr-1"


def test_censoring_rules_never_zero_or_limit():
    base = {
        "event_id": "ev1",
        "variable": "Naphthalene",
        "value": np.nan,
        "unit": "ug/kg",
        "original_value": 5.0,
        "original_unit": "PPB",
        "matrix": "soil",
        "depth_top": 0.0,
        "depth_bottom": 2.0,
        "basis": "dry",
        "censor_flag": "below_detection",
        "detection_limit": 5.0,
        "qualifier": "U",
        "lab_method": "SIM",
        "value_type": "measured",
    }
    # Valid: raw below_detection has value=NaN and original_value preserved
    schema.validate("observation", pd.DataFrame([base]))

    # Valid: assumed/modelled imputation strictly between 0 and detection_limit
    assumed_row = {**base, "value": 2.1, "value_type": "assumed"}
    schema.validate("observation", pd.DataFrame([assumed_row]))

    # Invalid: censored value stored as zero
    with pytest.raises(ValueError, match="never be stored as zero"):
        schema.validate("observation", pd.DataFrame([{**base, "value": 0.0, "value_type": "assumed"}]))

    # Invalid: censored value stored as the detection limit
    with pytest.raises(ValueError, match="never be stored as the detection limit"):
        schema.validate("observation", pd.DataFrame([{**base, "value": 5.0, "value_type": "assumed"}]))

    # Invalid: numeric value on below_detection still marked value_type='measured'
    with pytest.raises(ValueError, match="value=NaN"):
        schema.validate("observation", pd.DataFrame([{**base, "value": 2.1, "value_type": "measured"}]))


def test_site_coordinate_quality_none_and_spatial_guard():
    sites = pd.DataFrame([
        {
            "site_id": "s_no_coord",
            "source_id": "EXT-ZENGEL2015",
            "lat": np.nan,
            "lon": np.nan,
            "datum": "",
            "coordinate_quality": "none",
            "region": "barataria",
            "spill_id": "DWH_2010",
            "habitat": "10A",
            "zone": "intertidal",
            "geometry_type": "group",
        },
        {
            "site_id": "s_with_coord",
            "source_id": "EXT-ZENGEL2022",
            "lat": 29.4435,
            "lon": -89.8870,
            "datum": "WGS84",
            "coordinate_quality": "gps",
            "region": "barataria",
            "spill_id": "DWH_2010",
            "habitat": "10A",
            "zone": "intertidal",
            "geometry_type": "plot",
        },
    ])
    validated = schema.validate("site", sites)
    spatial = schema.filter_spatial_sites(validated)
    assert list(spatial["site_id"]) == ["s_with_coord"]

    bad_site = sites.copy()
    bad_site.loc[0, "coordinate_quality"] = "gps"
    with pytest.raises(ValueError, match="coordinate_quality='none'"):
        schema.validate("site", bad_site)


def test_small_schema_tables_and_reconciliation():
    loaded: dict[str, pd.DataFrame] = {}
    for tname in schema.TABLE_COLUMNS:
        p = ROOT / "data" / "schema" / f"{tname}.csv"
        assert p.exists(), f"Missing schema table {p}"
        assert p.stat().st_size < 20 * 1024 * 1024, f"{p.name} exceeds 20 MB"
        df = pd.read_csv(p, low_memory=False)
        loaded[tname] = schema.validate(tname, df)

    recon = schema.reconcile(loaded, root=ROOT)
    assert bool(recon["reconciled"].all()), recon[~recon["reconciled"]].to_string()

    # Spot-check key reconciliation numbers
    by_check = recon.set_index(["dataset", "check"])
    assert by_check.loc[("zengel2015", "total_rows"), "actual"] == "86"
    assert by_check.loc[("zengel2015", "measured_rows"), "actual"] == "83"
    assert by_check.loc[("zengel2022", "dsas_plot_count"), "actual"] == "33"
    assert by_check.loc[("edge_cells", "total_louisiana_cells"), "actual"] == "45404"
    assert by_check.loc[("edge_cells", "p5_in_scope_cells"), "actual"] == "12696"
    assert by_check.loc[("edge_cells", "naip_edge_2010-2015_cells"), "actual"] == "4779"
    assert by_check.loc[("edge_cells", "naip_edge_2010-2017_cells"), "actual"] == "4727"
    assert by_check.loc[("galeta", "raw_data_check"), "actual"] == "not loaded: raw data absent"
