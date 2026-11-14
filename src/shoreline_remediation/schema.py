"""D14 common multi-site data schema (Task F4; plan: docs/F4_SCHEMA_PLAN.md).

Five tables (`source`, `site`, `event`, `observation`, `intervention`), validation rules (`validate`),
unit conversion (`convert_units`), spatial-join guard (`filter_spatial_sites`), dataset loaders
(Zengel 2015, Zengel 2022, NAIP/P2/P5 edge cells, DIVER wetland soil chemistry, Galeta mangrove check),
and reconciliation against existing per-analysis tables.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DICT_MAIN = ROOT / "data" / "meta" / "variable_dictionary.csv"
DICT_SCHEMA = ROOT / "data" / "meta" / "schema_variables.csv"
SCHEMA_DIR = ROOT / "data" / "schema"
SCHEMA_LOCAL_DIR = ROOT / "data" / "schema_local"
RECON_DIR = ROOT / "results" / "f4_schema"
GALETA_RAW_DIR = ROOT / "data" / "raw" / "galeta_ncei_9400033" / "data"

TABLE_COLUMNS: dict[str, list[str]] = {
    "source": ["source_id", "citation", "doi", "licence", "acquired", "method_read", "checksum"],
    "site": [
        "site_id", "source_id", "lat", "lon", "datum", "coordinate_quality",
        "region", "spill_id", "habitat", "zone", "geometry_type",
    ],
    "event": ["event_id", "site_id", "date", "date_precision", "method", "campaign"],
    "observation": [
        "event_id", "variable", "value", "unit", "original_value", "original_unit",
        "matrix", "depth_top", "depth_bottom", "basis", "censor_flag",
        "detection_limit", "qualifier", "lab_method", "value_type",
    ],
    "intervention": ["site_id", "treatment", "start", "end", "intensity", "assigned", "source_id"],
}

TABLE_DTYPES: dict[str, dict[str, str]] = {
    "source": {c: "string" for c in TABLE_COLUMNS["source"]},
    "site": {
        "site_id": "string", "source_id": "string", "lat": "float64", "lon": "float64",
        "datum": "string", "coordinate_quality": "string", "region": "string",
        "spill_id": "string", "habitat": "string", "zone": "string", "geometry_type": "string",
    },
    "event": {c: "string" for c in TABLE_COLUMNS["event"]},
    "observation": {
        "event_id": "string", "variable": "string", "value": "float64", "unit": "string",
        "original_value": "float64", "original_unit": "string", "matrix": "string",
        "depth_top": "float64", "depth_bottom": "float64", "basis": "string",
        "censor_flag": "string", "detection_limit": "float64", "qualifier": "string",
        "lab_method": "string", "value_type": "string",
    },
    "intervention": {c: "string" for c in TABLE_COLUMNS["intervention"]},
}

ALLOWED_CENSOR_FLAGS = {
    "measured", "below_detection", "below detection",
    "between_limits", "between limits", "no_limit_available", "no limit available",
}
BELOW_DETECTION_FLAGS = {"below_detection", "below detection"}
ALLOWED_VALUE_TYPES = {"measured", "derived", "modelled", "assumed"}
ALLOWED_ASSIGNED = {"randomized", "chosen", "unknown"}
ALLOWED_MATRICES = {"soil", "sediment", "water", "tissue", "vegetation", "shoreline"}
ALLOWED_COORDINATE_QUALITY = {
    "gps", "grid_cell_centroid", "station_median", "approximate", "exact", "measured", "derived", "none",
}
ALLOWED_GEOMETRY_TYPES = {"point", "100 m cell", "100m_cell", "plot", "segment", "island", "group"}

# Multipliers converting (from_unit, to_unit) -> scale factor
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("PPB", "ug/kg"): 1.0,
    ("ppb", "ug/kg"): 1.0,
    ("ng/g", "ug/kg"): 1.0,
    ("PPB", "mg/kg"): 1e-3,
    ("ppb", "mg/kg"): 1e-3,
    ("ug/kg", "mg/kg"): 1e-3,
    ("mg/kg", "ug/kg"): 1e3,
    ("PPM", "mg/kg"): 1.0,
    ("ppm", "mg/kg"): 1.0,
    ("PPM", "ug/kg"): 1e3,
    ("PCT", "%"): 1.0,
    ("% by Weight", "%"): 1.0,
    ("percent", "%"): 1.0,
    ("g/cubic cm", "g/cm3"): 1.0,
    ("kg/m3", "g/cm3"): 1e-3,
    ("g/cm3", "kg/m3"): 1e3,
    ("m yr-1", "m/yr"): 1.0,
    ("m/year", "m/yr"): 1.0,
    ("cm/yr", "m/yr"): 0.01,
    ("cm", "m"): 0.01,
    ("mm", "m"): 1e-3,
    ("W/m", "W/m"): 1.0,
}

ZENGEL2015_METRICS: dict[str, tuple[str, str, str]] = {
    "Oiled Vegetation Mat Cover (%)": ("oiled_veg_mat_cover", "%", "vegetation"),
    "Surface Oil Cover (%)": ("surface_oil_cover", "%", "shoreline"),
    "tPAH (mg/kg)": ("tpah_soil", "mg/kg", "soil"),
    "Total Vegetation Cover (%)": ("total_veg_cover", "%", "vegetation"),
    "Spartina alterniflora Cover (%)": ("spartina_cover", "%", "vegetation"),
    "Total Periwinkle Density (m-2)": ("periwinkle_density_total", "m-2", "tissue"),
    "Juvenile Periwinkle Density (m-2)": ("periwinkle_density_juvenile", "m-2", "tissue"),
    "Sub-Adult Periwinkle Density (m-2)": ("periwinkle_density_subadult", "m-2", "tissue"),
    "Adult Periwinkle Density (m-2)": ("periwinkle_density_adult", "m-2", "tissue"),
    "Crab Burrow Density (m-2)": ("crab_burrow_density", "m-2", "sediment"),
    "Shoreline Retreat (m yr-1)": ("shoreline_retreat_rate", "m yr-1", "shoreline"),
}

# Reversed or space-padded plot IDs in Zengel 2022 sheets mapped to the 33 canonical DSAS plot IDs
ZENGEL2022_PLOT_ALIAS: dict[str, str] = {
    "1 - 2": "1-2",
    "7 - 8": "7-8",
    "8 - 9": "8-9",
    "9 - 10": "9-10",
    "17-16": "16-17",
    "18-17": "17-18",
    "21-20": "20-21",
    "23-22": "22-23",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def empty_table(table_name: str) -> pd.DataFrame:
    if table_name not in TABLE_COLUMNS:
        raise ValueError(f"Unknown schema table: {table_name}")
    return pd.DataFrame({c: pd.Series(dtype=dt) for c, dt in TABLE_DTYPES[table_name].items()})


def coerce_table(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    cols = TABLE_COLUMNS[table_name]
    out = df[cols].copy()
    for col, dt in TABLE_DTYPES[table_name].items():
        if dt == "float64":
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
        else:
            out[col] = out[col].where(out[col].notna(), None)
    return out


def load_variable_dictionary(
    main_path: Path = DICT_MAIN, schema_path: Path = DICT_SCHEMA
) -> dict[str, str]:
    units: dict[str, str] = {}
    if main_path.exists():
        d_main = pd.read_csv(main_path, dtype=str).fillna("")
        for _, r in d_main.iterrows():
            var, u = r["variable"].strip(), r["unit"].strip()
            if var and u and u != "per metric":
                units[var] = u
    if schema_path.exists():
        d_sch = pd.read_csv(schema_path, dtype=str).fillna("")
        for _, r in d_sch.iterrows():
            var, u = r["variable"].strip(), r["unit"].strip()
            if var and u:
                units[var] = u
    return units


def convert_units(df: pd.DataFrame, var_units: dict[str, str] | None = None) -> pd.DataFrame:
    """Convert observation values and units to dictionary canonical units, keeping original_value and original_unit."""
    var_units = load_variable_dictionary() if var_units is None else var_units
    out = df.copy()
    if "original_value" not in out.columns:
        out["original_value"] = pd.to_numeric(out["value"], errors="coerce")
    else:
        miss_ov = out["original_value"].isna() & out["value"].notna()
        out.loc[miss_ov, "original_value"] = pd.to_numeric(out.loc[miss_ov, "value"], errors="coerce")
    if "original_unit" not in out.columns:
        out["original_unit"] = out["unit"].astype(str)
    else:
        miss_ou = out["original_unit"].isna() | (out["original_unit"].astype(str).str.strip() == "")
        out.loc[miss_ou, "original_unit"] = out.loc[miss_ou, "unit"].astype(str)

    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    unknown_vars = sorted(set(out["variable"].dropna().astype(str)) - set(var_units))
    if unknown_vars:
        raise ValueError(f"Variables not in variable dictionary: {unknown_vars[:10]}")

    target_units = out["variable"].map(var_units)
    diff = out["unit"].astype(str) != target_units.astype(str)
    if diff.any():
        for (u_from, u_to), idx in out.loc[diff].groupby([out.loc[diff, "unit"], target_units.loc[diff]]).groups.items():
            if u_from == u_to:
                continue
            if (u_from, u_to) not in UNIT_CONVERSIONS:
                raise ValueError(f"Unsupported unit conversion from '{u_from}' to '{u_to}'")
            factor = UNIT_CONVERSIONS[(u_from, u_to)]
            out.loc[idx, "value"] = out.loc[idx, "value"] * factor
            out.loc[idx, "unit"] = u_to
    return out


def filter_spatial_sites(site_df: pd.DataFrame) -> pd.DataFrame:
    """Bar sites with coordinate_quality == 'none' or missing coordinates from any spatial join (D14)."""
    cq = site_df["coordinate_quality"].fillna("none").astype(str).str.strip().str.lower()
    return site_df[(cq != "none") & site_df["lat"].notna() & site_df["lon"].notna()].copy()


def validate(table_name: str, df: pd.DataFrame, var_units: dict[str, str] | None = None) -> pd.DataFrame:
    """Enforce D14 schema rules on a table DataFrame. Raises ValueError on any rule violation."""
    if table_name not in TABLE_COLUMNS:
        raise ValueError(f"Unknown table name '{table_name}'. Expected one of {sorted(TABLE_COLUMNS)}")
    req_cols = TABLE_COLUMNS[table_name]
    missing_cols = [c for c in req_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Table '{table_name}' is missing required columns: {missing_cols}")

    if len(df) == 0:
        return coerce_table(table_name, df)

    if table_name == "source":
        if df["source_id"].isna().any() or (df["source_id"].astype(str).str.strip() == "").any():
            raise ValueError("source.source_id cannot be null or empty")
        if df["source_id"].duplicated().any():
            raise ValueError("source.source_id must be unique")

    elif table_name == "site":
        for key in ("site_id", "source_id", "coordinate_quality", "geometry_type"):
            if df[key].isna().any() or (df[key].astype(str).str.strip() == "").any():
                raise ValueError(f"site.{key} cannot be null or empty")
        if df["site_id"].duplicated().any():
            raise ValueError("site.site_id must be unique")
        cq = df["coordinate_quality"].astype(str).str.strip()
        bad_cq = sorted(set(cq) - ALLOWED_COORDINATE_QUALITY)
        if bad_cq:
            raise ValueError(f"Invalid coordinate_quality values: {bad_cq}")
        lat = pd.to_numeric(df["lat"], errors="coerce")
        lon = pd.to_numeric(df["lon"], errors="coerce")
        no_coord = lat.isna() | lon.isna()
        if (no_coord & (cq != "none")).any():
            raise ValueError("Sites missing lat or lon must have coordinate_quality='none'")
        if ((~no_coord) & (cq == "none")).any():
            raise ValueError("Sites with coordinate_quality='none' must not carry numeric lat/lon")
        gt = df["geometry_type"].astype(str).str.strip()
        bad_gt = sorted(set(gt) - ALLOWED_GEOMETRY_TYPES)
        if bad_gt:
            raise ValueError(f"Invalid geometry_type values: {bad_gt}")

    elif table_name == "event":
        for key in ("event_id", "site_id"):
            if df[key].isna().any() or (df[key].astype(str).str.strip() == "").any():
                raise ValueError(f"event.{key} cannot be null or empty")
        if df["event_id"].duplicated().any():
            raise ValueError("event.event_id must be unique")

    elif table_name == "observation":
        var_units = load_variable_dictionary() if var_units is None else var_units
        for key in ("event_id", "variable", "unit", "censor_flag", "value_type", "matrix"):
            if df[key].isna().any() or (df[key].astype(str).str.strip() == "").any():
                raise ValueError(f"observation.{key} cannot be null or empty")
        vars_present = set(df["variable"].astype(str))
        unknown_vars = sorted(vars_present - set(var_units))
        if unknown_vars:
            raise ValueError(f"Variables not in dictionary (rejected per D14): {unknown_vars[:10]}")

        expected_unit = df["variable"].astype(str).map(var_units)
        unit_mismatch = df["unit"].astype(str) != expected_unit
        if unit_mismatch.any():
            bad_rows = df.loc[unit_mismatch, ["variable", "unit"]].drop_duplicates().to_dict("records")
            raise ValueError(f"observation.unit does not match dictionary unit: {bad_rows[:5]}")

        if df["original_unit"].isna().any() or (df["original_unit"].astype(str).str.strip() == "").any():
            raise ValueError("observation.original_unit must be kept for all rows")

        val = pd.to_numeric(df["value"], errors="coerce")
        orig_val = pd.to_numeric(df["original_value"], errors="coerce")
        if (val.notna() & orig_val.isna()).any():
            raise ValueError("observation.original_value must be kept whenever value is present")

        cf = df["censor_flag"].astype(str).str.strip()
        bad_cf = sorted(set(cf) - ALLOWED_CENSOR_FLAGS)
        if bad_cf:
            raise ValueError(f"Invalid censor_flag values: {bad_cf}")

        vt = df["value_type"].astype(str).str.strip()
        bad_vt = sorted(set(vt) - ALLOWED_VALUE_TYPES)
        if bad_vt:
            raise ValueError(f"Invalid value_type values: {bad_vt}")

        mat = df["matrix"].astype(str).str.strip()
        bad_mat = sorted(set(mat) - ALLOWED_MATRICES)
        if bad_mat:
            raise ValueError(f"Invalid matrix values: {bad_mat}")

        # D14 censoring rule: censored values are never stored as zero or as the detection limit
        is_cens = cf.isin(BELOW_DETECTION_FLAGS)
        if is_cens.any():
            cens_val = val[is_cens]
            if (cens_val == 0.0).any():
                raise ValueError("Censored (below_detection) values must never be stored as zero")
            dl = pd.to_numeric(df.loc[is_cens, "detection_limit"], errors="coerce")
            both_present = cens_val.notna() & dl.notna()
            if both_present.any() and np.isclose(cens_val[both_present], dl[both_present], rtol=1e-9, atol=1e-12).any():
                raise ValueError("Censored (below_detection) values must never be stored as the detection limit")
            if (cens_val.notna() & (vt[is_cens] == "measured")).any():
                raise ValueError(
                    "Raw left-censored observations with value_type='measured' must have value=NaN "
                    "(imputed values must be marked derived/modelled/assumed)"
                )

    elif table_name == "intervention":
        for key in ("site_id", "treatment", "assigned", "source_id"):
            if df[key].isna().any() or (df[key].astype(str).str.strip() == "").any():
                raise ValueError(f"intervention.{key} cannot be null or empty")
        ass = df["assigned"].astype(str).str.strip()
        bad_ass = sorted(set(ass) - ALLOWED_ASSIGNED)
        if bad_ass:
            raise ValueError(f"Invalid intervention.assigned values: {bad_ass}")

    return coerce_table(table_name, df)


# ---------------------------------------------------------------------------
# 1. Zengel 2015 and Zengel 2022 loaders
# ---------------------------------------------------------------------------
def load_zengel2015(root: Path = ROOT) -> dict[str, pd.DataFrame]:
    csv_path = root / "data" / "external" / "zengel2015" / "zengel2015_group_means.csv"
    xlsx_path = root / "data" / "external" / "zengel2015" / "zengel2015_S1_Table.xlsx"
    df = pd.read_csv(csv_path)

    sources = pd.DataFrame([{
        "source_id": "EXT-ZENGEL2015",
        "citation": "Zengel et al. (2015) PLoS ONE 10(7):e0132324 S1 Table",
        "doi": "10.1371/journal.pone.0132324",
        "licence": "CC BY 4.0",
        "acquired": "2026-11-11",
        "method_read": "pandas.read_csv(data/external/zengel2015/zengel2015_group_means.csv)",
        "checksum": sha256_file(xlsx_path) if xlsx_path.exists() else sha256_file(csv_path),
    }])

    def _slug(s: str) -> str:
        return s.strip().replace(" ", "_").replace("(", "").replace(")", "")

    site_rows, int_rows = [], []
    treatment_map = {
        ("main", "Reference"): ("none", None),
        ("main", "No Treatment"): ("none", None),
        ("main", "Manual Treatment"): ("manual_removal", ("chosen", "2011-02", "2011-06")),
        ("main", "Mechanical Treatment"): ("mechanical_removal", ("chosen", "2011-05", "2011-06")),
        ("planting", "Mechanical (Control)"): ("mechanical_removal", ("chosen", "2011-05", "2011-06")),
        ("planting", "Mechanical (Planted)"): ("mechanical_plus_planting", ("randomized", "2011-06", "2011-07")),
        ("pre_treatment", "Manual Treatment"): ("manual_removal", ("chosen", "2011-02", "2011-06")),
        ("pre_treatment", "Mechanical Treatment"): ("mechanical_removal", ("chosen", "2011-05", "2011-06")),
        ("pre_treatment", "No Treatment"): ("none", None),
    }

    for (study, trt), _ in df.groupby(["study", "treatment"], sort=False):
        sid = f"zengel2015_{study}_{_slug(trt)}"
        site_rows.append({
            "site_id": sid,
            "source_id": "EXT-ZENGEL2015",
            "lat": np.nan,
            "lon": np.nan,
            "datum": "",
            "coordinate_quality": "none",
            "region": "northern_barataria_bay_la",
            "spill_id": "DWH_2010",
            "habitat": "10A",
            "zone": "intertidal",
            "geometry_type": "group",
        })
        code, spec = treatment_map[(study, trt)]
        if spec is not None:
            assigned, start, end = spec
            int_rows.append({
                "site_id": sid,
                "treatment": code,
                "start": start,
                "end": end,
                "intensity": f"study={study}; group={trt}",
                "assigned": assigned,
                "source_id": "EXT-ZENGEL2015",
            })

    ev_rows, obs_rows = [], []
    for (study, trt, year), g in df.groupby(["study", "treatment", "year"], sort=False):
        sid = f"zengel2015_{study}_{_slug(trt)}"
        eid = f"{sid}_{int(year)}"
        ev_rows.append({
            "event_id": eid,
            "site_id": sid,
            "date": str(int(year)),
            "date_precision": "year",
            "method": "field_plot_group_mean",
            "campaign": f"zengel2015_{study}_{int(year)}",
        })
        for _, r in g.iterrows():
            var_name, orig_unit, matrix = ZENGEL2015_METRICS[r["metric"]]
            is_nd = pd.isna(r["mean"])
            obs_rows.append({
                "event_id": eid,
                "variable": var_name,
                "value": np.nan if is_nd else float(r["mean"]),
                "unit": orig_unit,
                "original_value": np.nan if is_nd else float(r["mean"]),
                "original_unit": orig_unit,
                "matrix": matrix,
                "depth_top": 0.0 if matrix == "soil" else np.nan,
                "depth_bottom": 5.0 if matrix == "soil" else np.nan,
                "basis": "dry" if matrix == "soil" else "na",
                "censor_flag": "no_limit_available" if is_nd else "measured",
                "detection_limit": np.nan,
                "qualifier": "ND" if is_nd else f"se={r['se']};n={int(r['n'])}",
                "lab_method": "Zengel2015_S1_group_mean",
                "value_type": "measured",
            })

    obs_df = convert_units(pd.DataFrame(obs_rows))
    return {
        "source": validate("source", pd.DataFrame(sources)),
        "site": validate("site", pd.DataFrame(site_rows)),
        "event": validate("event", pd.DataFrame(ev_rows)),
        "observation": validate("observation", obs_df),
        "intervention": validate("intervention", pd.DataFrame(int_rows)),
    }


def load_zengel2022(root: Path = ROOT) -> dict[str, pd.DataFrame]:
    xlsx_path = root / "data" / "external" / "zengel2022" / "zengel2022_griidc_erosion.xlsx"
    lumped = pd.read_excel(xlsx_path, sheet_name="DSAS lumped")
    annual = pd.read_excel(xlsx_path, sheet_name="DSAS annual")
    field_er = pd.read_excel(xlsx_path, sheet_name="GIS field erosion")
    pts = pd.read_excel(xlsx_path, sheet_name="GIS field erosion points")
    wave = pd.read_excel(xlsx_path, sheet_name="Wave Power")
    shear = pd.read_excel(xlsx_path, sheet_name="Shear strength")

    sources = pd.DataFrame([{
        "source_id": "EXT-ZENGEL2022",
        "citation": "Zengel et al. (2022) Sci. Rep. 12:13802; GRIIDC R6.x813.000:0007",
        "doi": "10.7266/VF524143",
        "licence": "CC0",
        "acquired": "2026-11-11",
        "method_read": "pandas.read_excel(data/external/zengel2022/zengel2022_griidc_erosion.xlsx)",
        "checksum": sha256_file(xlsx_path),
    }])

    def _canon_plot(val) -> str:
        raw = str(val).strip()
        return ZENGEL2022_PLOT_ALIAS.get(raw, raw)

    pts["canon_plot"] = pts["PLOT_ID"].map(_canon_plot)
    gps_by_plot = pts.groupby("canon_plot")[["LAT_DD", "LON_DD"]].mean()

    lumped["canon_plot"] = lumped["PLOT_ID"].map(_canon_plot)
    plot_meta = lumped.drop_duplicates("canon_plot")[["canon_plot", "PLOT_TYPE", "OILED"]].set_index("canon_plot")

    trt_map = {
        "REFERENCE": ("none", None),
        "UNTREATED": ("none", None),
        "TREATED - MANUAL": ("manual_removal", ("chosen", "2011-02", "2011-06")),
        "TREATED - MECHANICAL": ("mechanical_removal", ("chosen", "2011-05", "2011-06")),
        "TREATED - PLANTED": ("mechanical_plus_planting", ("randomized", "2011-06", "2011-07")),
    }

    site_rows, int_rows = [], []
    for pid, meta in plot_meta.iterrows():
        sid = f"zengel2022_plot_{pid}"
        has_gps = pid in gps_by_plot.index
        lat = float(gps_by_plot.loc[pid, "LAT_DD"]) if has_gps else np.nan
        lon = float(gps_by_plot.loc[pid, "LON_DD"]) if has_gps else np.nan
        ptype = str(meta["PLOT_TYPE"]).strip()
        site_rows.append({
            "site_id": sid,
            "source_id": "EXT-ZENGEL2022",
            "lat": lat,
            "lon": lon,
            "datum": "WGS84" if has_gps else "",
            "coordinate_quality": "gps" if has_gps else "none",
            "region": "northern_barataria_bay_la",
            "spill_id": "DWH_2010",
            "habitat": "10A",
            "zone": "intertidal",
            "geometry_type": "plot",
        })
        code, spec = trt_map[ptype]
        if spec is not None:
            assigned, start, end = spec
            int_rows.append({
                "site_id": sid,
                "treatment": code,
                "start": start,
                "end": end,
                "intensity": f"PLOT_TYPE={ptype}; OILED={meta['OILED']}",
                "assigned": assigned,
                "source_id": "EXT-ZENGEL2022",
            })

    ev_rows, obs_rows = [], []
    seen_events: set[str] = set()

    def _add_event(eid: str, sid: str, date_str: str, precision: str, method: str, campaign: str) -> None:
        if eid not in seen_events:
            seen_events.add(eid)
            ev_rows.append({
                "event_id": eid, "site_id": sid, "date": date_str,
                "date_precision": precision, "method": method, "campaign": campaign,
            })

    for sheet_tag, d_sheet, method in [
        ("dsas_lumped", lumped, "DSAS_aerial_photo_transects_lumped"),
        ("dsas_annual", annual, "DSAS_aerial_photo_transects_annual"),
    ]:
        for _, r in d_sheet.iterrows():
            raw_pid = str(r["PLOT_ID"]).strip()
            pid = _canon_plot(raw_pid)
            sid = f"zengel2022_plot_{pid}"
            period = str(r["TIME_PERIOD"]).strip()
            eid = f"{sid}_{sheet_tag}_{period}"
            _add_event(eid, sid, period, "period", method, f"zengel2022_{sheet_tag}")
            val = float(r["EROSION_RATE"])
            obs_rows.append({
                "event_id": eid,
                "variable": "EROSION_RATE",
                "value": val,
                "unit": "m/yr",
                "original_value": val,
                "original_unit": "m/yr",
                "matrix": "shoreline",
                "depth_top": np.nan,
                "depth_bottom": np.nan,
                "basis": "na",
                "censor_flag": "measured",
                "detection_limit": np.nan,
                "qualifier": f"PLOT_TYPE={str(r['PLOT_TYPE']).strip()};N={r['N']};SD={r['SD']};SE={r['SE']}",
                "lab_method": method,
                "value_type": "measured",
            })

    for _, r in field_er.iterrows():
        raw_pid = str(r["PLOT_ID"]).strip()
        pid = _canon_plot(raw_pid)
        sid = f"zengel2022_plot_{pid}"
        period = str(r["TIME_PERIOD"]).strip()
        eid = f"{sid}_field_erosion_{period}"
        _add_event(eid, sid, period, "period", "GIS_field_erosion_transects", "zengel2022_field_erosion")
        val = float(r["EROSION_RATE"])
        obs_rows.append({
            "event_id": eid,
            "variable": "EROSION_RATE",
            "value": val,
            "unit": "m/yr",
            "original_value": val,
            "original_unit": "m/yr",
            "matrix": "shoreline",
            "depth_top": np.nan,
            "depth_bottom": np.nan,
            "basis": "na",
            "censor_flag": "measured",
            "detection_limit": np.nan,
            "qualifier": f"PLOT_TYPE={str(r['PLOT_TYPE']).strip()};raw_plot_id={raw_pid}",
            "lab_method": "GIS_field_erosion_transects",
            "value_type": "measured",
        })

    for _, r in wave.iterrows():
        raw_pid = str(r["PLOT_ID"]).strip()
        pid = _canon_plot(raw_pid)
        sid = f"zengel2022_plot_{pid}"
        period = str(r["TIME_PERIOD"]).strip()
        eid = f"{sid}_wave_power_{period}"
        _add_event(eid, sid, period, "period", "wave_power_hindcast", "zengel2022_wave_power")
        for var in ("WE_WM", "WE_MAX"):
            val = float(r[var])
            obs_rows.append({
                "event_id": eid,
                "variable": var,
                "value": val,
                "unit": "W/m",
                "original_value": val,
                "original_unit": "W/m",
                "matrix": "shoreline",
                "depth_top": np.nan,
                "depth_bottom": np.nan,
                "basis": "na",
                "censor_flag": "measured",
                "detection_limit": np.nan,
                "qualifier": f"PLOT_TYPE={str(r['PLOT_TYPE']).strip()};raw_plot_id={raw_pid}",
                "lab_method": "wave_power_model",
                "value_type": "modelled",
            })

    for _, r in shear.iterrows():
        raw_pid = str(r["PLOT_ID"]).strip()
        pid = _canon_plot(raw_pid)
        sid = f"zengel2022_plot_{pid}"
        eid = f"{sid}_shear_strength"
        _add_event(eid, sid, "2011-2012", "period", "field_shear_vane", "zengel2022_shear_strength")
        val = float(r["SHST_KPA"])
        obs_rows.append({
            "event_id": eid,
            "variable": "SHST_KPA",
            "value": val,
            "unit": "kPa",
            "original_value": val,
            "original_unit": "kPa",
            "matrix": "soil",
            "depth_top": np.nan,
            "depth_bottom": np.nan,
            "basis": "wet",
            "censor_flag": "measured",
            "detection_limit": np.nan,
            "qualifier": f"PLOT_TYPE={str(r['PLOT_TYPE']).strip()};raw_plot_id={raw_pid}",
            "lab_method": "shear_vane",
            "value_type": "measured",
        })

    obs_df = convert_units(pd.DataFrame(obs_rows))
    return {
        "source": validate("source", pd.DataFrame(sources)),
        "site": validate("site", pd.DataFrame(site_rows)),
        "event": validate("event", pd.DataFrame(ev_rows)),
        "observation": validate("observation", obs_df),
        "intervention": validate("intervention", pd.DataFrame(int_rows)),
    }


# ---------------------------------------------------------------------------
# 2. NAIP edge cells (data/external/naip_edge/ and data/external/p2/*/)
# ---------------------------------------------------------------------------
def load_naip_edge_cells(root: Path = ROOT) -> dict[str, pd.DataFrame]:
    from validation.naip_edge_loss import cell_rates

    naip_dir = root / "data" / "external" / "naip_edge"
    p2_dir = root / "data" / "external" / "p2"
    p5_path = root / "data" / "demo" / "p5_sites.csv"
    la_cells_path = p2_dir / "la_cells_basins.csv"

    sources = pd.DataFrame([
        {
            "source_id": "DER-NAIP-EDGE",
            "citation": "Barataria Bay 100 m SCAT salt-marsh edge cells and NAIP land fractions 2010-2017",
            "doi": "10.7289/v53t9ffx",
            "licence": "public domain (USDA NAIP / NOAA SCAT)",
            "acquired": "2026-11-11",
            "method_read": "pandas.read_csv(data/external/naip_edge/{cells_10A.csv,cell_land_by_year.csv})",
            "checksum": sha256_file(naip_dir / "cell_land_by_year.csv"),
        },
        {
            "source_id": "DER-P2",
            "citation": "Louisiana SCAT 100 m edge cells by basin (Terrebonne, Barataria, Breton, Birdfoot)",
            "doi": "10.7289/v53t9ffx",
            "licence": "public domain (USDA NAIP / USGS Landsat / NOAA SCAT)",
            "acquired": "2026-11-11",
            "method_read": "pandas.read_csv(data/external/p2/la_cells_basins.csv) and basin folders",
            "checksum": sha256_file(la_cells_path),
        },
        {
            "source_id": "DER-P5",
            "citation": "P5 Louisiana SCAT edge-cell site table with scope status and observed 2010-2015 rate",
            "doi": "10.7289/v53t9ffx",
            "licence": "public domain (derived in scripts/build_p5_demo.py)",
            "acquired": "2026-11-11",
            "method_read": "pandas.read_csv(data/demo/p5_sites.csv)",
            "checksum": sha256_file(p5_path),
        },
    ])

    la_cells = pd.read_csv(la_cells_path)
    p5_sites = pd.read_csv(p5_path)
    naip_cells_set = set(pd.read_csv(naip_dir / "cells_10A.csv")["cell"])

    site_df = pd.DataFrame({
        "site_id": la_cells["cell"].astype(str),
        "source_id": np.where(la_cells["cell"].isin(naip_cells_set), "DER-NAIP-EDGE", "DER-P2"),
        "lat": pd.to_numeric(la_cells["lat"], errors="coerce"),
        "lon": pd.to_numeric(la_cells["lon"], errors="coerce"),
        "datum": "WGS84",
        "coordinate_quality": "grid_cell_centroid",
        "region": la_cells["basin"].astype(str),
        "spill_id": "DWH_2010",
        "habitat": la_cells["esi_main"].astype(str),
        "zone": "intertidal",
        "geometry_type": "100 m cell",
    })

    # Combine NAIP cell_land_by_year across P2 basins and Barataria naip_edge (years 2010, 2013, 2015, 2017)
    p2_land = pd.concat(
        [pd.read_csv(p2_dir / b / "cell_land_by_year.csv").assign(source_tag=f"p2_{b}")
         for b in ("terrebonne", "barataria", "breton")],
        ignore_index=True,
    )
    naip_land = pd.read_csv(naip_dir / "cell_land_by_year.csv").assign(source_tag="naip_edge")
    comb_land = pd.concat([p2_land, naip_land], ignore_index=True).drop_duplicates(subset=["cell", "year"], keep="first")
    comb_land = comb_land[comb_land["land_fraction"].notna()].copy()

    ev_land = pd.DataFrame({
        "event_id": "naip_land_" + comb_land["cell"].astype(str) + "_" + comb_land["year"].astype(str),
        "site_id": comb_land["cell"].astype(str),
        "date": comb_land["flight_date"].fillna(comb_land["year"].astype(str)).astype(str),
        "date_precision": np.where(comb_land["flight_date"].notna(), "day", "year"),
        "method": "NAIP_2m_classifier",
        "campaign": "naip_" + comb_land["year"].astype(str),
    })
    obs_land = pd.DataFrame({
        "event_id": ev_land["event_id"].values,
        "variable": "land_fraction",
        "value": comb_land["land_fraction"].astype(float).values,
        "unit": "fraction",
        "original_value": comb_land["land_fraction"].astype(float).values,
        "original_unit": "fraction",
        "matrix": "shoreline",
        "depth_top": np.nan,
        "depth_bottom": np.nan,
        "basis": "na",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": (
            "vf=" + comb_land["valid_fraction"].round(4).astype(str)
            + ";blf=" + comb_land["block_land_fraction"].round(4).astype(str)
        ).values,
        "lab_method": "naip_edge_extract",
        "value_type": "derived",
    })

    # Barataria box NAIP edge-loss rates (2010-2015 primary: 4,779 cells; 2010-2017 secondary: 4,727 cells)
    rate_evs, rate_obs = [], []
    for period, yr in [("2010-2015", 2015), ("2010-2017", 2017)]:
        d_rate = cell_rates(naip_dir, yr)
        eid = "naip_edge_rate_" + d_rate["cell"].astype(str) + "_" + period.replace("-", "_")
        rate_evs.append(pd.DataFrame({
            "event_id": eid,
            "site_id": d_rate["cell"].astype(str),
            "date": period,
            "date_precision": "period",
            "method": "NAIP_edge_loss_rate",
            "campaign": f"naip_edge_{period}",
        }))
        rate_obs.append(pd.DataFrame({
            "event_id": eid.values,
            "variable": "rate",
            "value": d_rate["rate"].astype(float).values,
            "unit": "m/yr",
            "original_value": d_rate["rate"].astype(float).values,
            "original_unit": "m/yr",
            "matrix": "shoreline",
            "depth_top": np.nan,
            "depth_bottom": np.nan,
            "basis": "na",
            "censor_flag": "measured",
            "detection_limit": np.nan,
            "qualifier": ("max_oiling=" + d_rate["max_oiling"].astype(str) + ";cell_2km=" + d_rate["cell_2km"].astype(str)).values,
            "lab_method": "validation/naip_edge_loss.py:cell_rates",
            "value_type": "derived",
        }))

    # P5 in-scope cells (12,696 cells across Terrebonne, Barataria, Breton)
    in_scope = p5_sites[p5_sites["status"] == "in_scope"].copy()
    eid_p5 = "p5_rate_" + in_scope["cell"].astype(str) + "_2010_2015"
    rate_evs.append(pd.DataFrame({
        "event_id": eid_p5,
        "site_id": in_scope["cell"].astype(str),
        "date": "2010-2015",
        "date_precision": "period",
        "method": "P5_in_scope_edge_loss_rate",
        "campaign": "p5_2010_2015",
    }))
    rate_obs.append(pd.DataFrame({
        "event_id": eid_p5.values,
        "variable": "observed_rate",
        "value": in_scope["observed_rate"].astype(float).values,
        "unit": "m/yr",
        "original_value": in_scope["observed_rate"].astype(float).values,
        "original_unit": "m/yr",
        "matrix": "shoreline",
        "depth_top": np.nan,
        "depth_bottom": np.nan,
        "basis": "na",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": ("basin=" + in_scope["basin"].astype(str) + ";max_oiling=" + in_scope["max_oiling"].astype(str)).values,
        "lab_method": "scripts/build_p5_demo.py",
        "value_type": "derived",
    }))

    ev_df = pd.concat([ev_land, *rate_evs], ignore_index=True)
    obs_df = convert_units(pd.concat([obs_land, *rate_obs], ignore_index=True))
    return {
        "source": validate("source", sources),
        "site": validate("site", site_df),
        "event": validate("event", ev_df),
        "observation": validate("observation", obs_df),
        "intervention": validate("intervention", empty_table("intervention")),
    }


# ---------------------------------------------------------------------------
# 3. DIVER wetland soil chemistry loader (via diver_soil.py)
# ---------------------------------------------------------------------------
def load_diver_wetland_soil(root: Path = ROOT) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    from src.shoreline_remediation import diver_soil as ds

    csv_dir = root / "data" / "external" / "diver_dwh" / "extracted_csv"
    shp_path = root / "data" / "raw" / "scat" / "18611" / "SCAT_Max_OilZones_Louisiana_2014_09_30Sorted.shp"
    log = ds.Log()
    prep = ds.prepare(csv_dir, shp_path, log)
    sample_sums_df, station_campaign_df = ds.build(prep, mode="tobit", surface_only=False, log=log)

    # Read soil rows once more only to attach per-(sample, compound) non-ND Detection_Extent and Qualifier_Code
    soil_all = ds.read_soil(csv_dir, ds.Log())
    rows_filtered, toc_rows = ds.filter_rows(soil_all, ds.Log())
    between_set = set(
        rows_filtered.loc[
            rows_filtered["Detection_Extent"] == "Between Detection Limit and Reporting Limit",
            ["Sample_ID", "Analysis"],
        ].itertuples(index=False, name=None)
    )
    qual_map = (
        rows_filtered.groupby(["Sample_ID", "Analysis"])["Qualifier_Code"]
        .first()
        .to_dict()
    )

    camp_hashes = [
        f"{fn}:{sha256_file(csv_dir / fn)[:12]}"
        for fn in sorted({**ds.EXTRA_FILE, **ds.CAMPAIGN_FILES}.values())
    ]
    sources = pd.DataFrame([{
        "source_id": "EXT-DIVER-WETLAND",
        "citation": "NOAA DIVER DWH Shoreline Coastal Wetland Vegetation Plan soil samples 2010-2013",
        "doi": "10.7289/v5mw2fcq",
        "licence": "Public (NOAA DWH NRDA DIVER archive; local non-committed copy)",
        "acquired": "2026-11-12",
        "method_read": "src/shoreline_remediation/diver_soil.py:prepare+build",
        "checksum": ";".join(camp_hashes),
    }])

    st = prep.stations.copy()
    site_df = pd.DataFrame({
        "site_id": "diver_station_" + st["station"].astype(str),
        "source_id": "EXT-DIVER-WETLAND",
        "lat": pd.to_numeric(st["lat"], errors="coerce"),
        "lon": pd.to_numeric(st["lon"], errors="coerce"),
        "datum": "WGS84",
        "coordinate_quality": "station_median",
        "region": st["state"].astype(str),
        "spill_id": "DWH_2010",
        "habitat": "10A",
        "zone": "intertidal",
        "geometry_type": "point",
    })

    smp = prep.smp.copy()
    ev_df = pd.DataFrame({
        "event_id": "diver_sample_" + smp["sample"].astype(str),
        "site_id": "diver_station_" + smp["station"].astype(str),
        "date": smp["date"].dt.strftime("%Y-%m-%d").fillna(""),
        "date_precision": "day",
        "method": "soil_" + smp["depth_class"].astype(str),
        "campaign": smp["campaign"].astype(str),
    })

    smp_depth = smp.set_index("sample")[["upper", "lower", "depth_class"]]
    all_resolved = pd.concat([prep.res, prep.hop], ignore_index=True)
    all_resolved = all_resolved.merge(smp_depth, left_on="sample", right_index=True, how="left")

    keys = list(zip(all_resolved["sample"], all_resolved["compound"]))
    is_nd = all_resolved["nd"].values.astype(bool)
    is_btw = np.array([k in between_set for k in keys], dtype=bool)
    censor_flags = np.where(is_nd, "below_detection", np.where(is_btw, "between_limits", "measured"))
    quals = [str(qual_map.get(k, "")) for k in keys]

    # Per D14: raw left-censored observations have value=NaN (never 0, never the limit); original_value kept
    raw_vals = all_resolved["value"].astype(float).values
    obs_compounds = pd.DataFrame({
        "event_id": ("diver_sample_" + all_resolved["sample"].astype(str)).values,
        "variable": all_resolved["compound"].astype(str).values,
        "value": np.where(is_nd, np.nan, raw_vals),
        "unit": "PPB",
        "original_value": raw_vals,
        "original_unit": "PPB",
        "matrix": "soil",
        "depth_top": all_resolved["upper"].astype(float).values,
        "depth_bottom": all_resolved["lower"].astype(float).values,
        "basis": "dry",
        "censor_flag": censor_flags,
        "detection_limit": np.nan,
        "qualifier": quals,
        "lab_method": "Alpha_Analytical_PAH_SIM",
        "value_type": "measured",
    })

    toc_merged = prep.toc.merge(smp[["sample", "upper", "lower"]], on="sample", how="inner")
    obs_toc = pd.DataFrame({
        "event_id": ("diver_sample_" + toc_merged["sample"].astype(str)).values,
        "variable": ds.TOC,
        "value": toc_merged["toc"].astype(float).values,
        "unit": "PCT",
        "original_value": toc_merged["toc"].astype(float).values,
        "original_unit": "PCT",
        "matrix": "soil",
        "depth_top": toc_merged["upper"].astype(float).values,
        "depth_bottom": toc_merged["lower"].astype(float).values,
        "basis": "dry",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": "",
        "lab_method": "TOC_dry_weight_pct",
        "value_type": "measured",
    })

    # Derived per-sample 58-PAH sum (value_type='assumed' when non-detects were Tobit-imputed, else 'derived')
    s_df = sample_sums_df.copy()
    obs_sum = pd.DataFrame({
        "event_id": ("diver_sample_" + s_df["sample"].astype(str)).values,
        "variable": "pah_sum_58",
        "value": s_df["pah_sum"].astype(float).values,
        "unit": "PPB",
        "original_value": s_df["pah_sum"].astype(float).values,
        "original_unit": "PPB",
        "matrix": "soil",
        "depth_top": s_df["upper"].astype(float).values,
        "depth_bottom": s_df["lower"].astype(float).values,
        "basis": "dry",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": (
            "n_nd=" + s_df["n_nd"].astype(str)
            + ";est_share=" + s_df["est_share"].round(4).astype(str)
            + ";flag_est_gt50=" + s_df["flag_est_gt50"].astype(str)
        ).values,
        "lab_method": "diver_soil.py:sample_sums(tobit)",
        "value_type": np.where(s_df["n_nd"] > 0, "assumed", "derived"),
    })

    s_ratio = s_df[s_df["ratio"].notna()].copy()
    obs_ratio = pd.DataFrame({
        "event_id": ("diver_sample_" + s_ratio["sample"].astype(str)).values,
        "variable": "pah_hopane_ratio",
        "value": s_ratio["ratio"].astype(float).values,
        "unit": "ratio",
        "original_value": s_ratio["ratio"].astype(float).values,
        "original_unit": "ratio",
        "matrix": "soil",
        "depth_top": s_ratio["upper"].astype(float).values,
        "depth_bottom": s_ratio["lower"].astype(float).values,
        "basis": "dry",
        "censor_flag": "measured",
        "detection_limit": np.nan,
        "qualifier": ("n_nd=" + s_ratio["n_nd"].astype(str)).values,
        "lab_method": "diver_soil.py:sample_sums(ratio)",
        "value_type": np.where(s_ratio["n_nd"] > 0, "assumed", "derived"),
    })

    obs_all = convert_units(pd.concat([obs_compounds, obs_toc, obs_sum, obs_ratio], ignore_index=True))
    tables = {
        "source": validate("source", sources),
        "site": validate("site", site_df),
        "event": validate("event", ev_df),
        "observation": validate("observation", obs_all),
        "intervention": validate("intervention", empty_table("intervention")),
    }
    stats = {
        "soil_rows_all_5_files": int(len(soil_all)),
        "soil_samples_all_5_files": int(soil_all["Sample_ID"].nunique()),
        "filtered_pah_hopane_rows": int(len(rows_filtered)),
        "pah_samples": int( len(prep.smp) ),
        "stations": int(prep.stations["station"].nunique()),
        "resolved_sample_compound_keys": int(len(all_resolved)),
        "pah_nd_count": int(prep.res["nd"].sum()),
        "hopane_nd_count": int(prep.hop["nd"].sum()),
        "complete_samples_with_sum": int(len(sample_sums_df)),
        "samples_with_hopane_ratio": int(sample_sums_df["ratio"].notna().sum()),
        "station_campaign_rows": int(len(station_campaign_df)),
        "station_campaign_df": station_campaign_df,
    }
    return tables, stats


# ---------------------------------------------------------------------------
# 4. Galeta mangrove check
# ---------------------------------------------------------------------------
def load_galeta_mangrove(root: Path = ROOT) -> tuple[dict[str, pd.DataFrame], str]:
    raw_dir = root / "data" / "raw" / "galeta_ncei_9400033" / "data"
    if not raw_dir.exists() or not any(raw_dir.iterdir()):
        status = "not loaded: raw data absent"
        sources = pd.DataFrame([{
            "source_id": "EXT-GALETA",
            "citation": "Keller & Jackson (1993) OCS Study MMS 93-0048; NCEI accession 9400033 (Bahia Las Minas mangrove)",
            "doi": "",
            "licence": "UNCLEAR (CC0 vs non-public in NCEI catalogue; raw files not committed)",
            "acquired": "2026-11-12",
            "method_read": status,
            "checksum": "",
        }])
        return {
            "source": validate("source", sources),
            "site": empty_table("site"),
            "event": empty_table("event"),
            "observation": empty_table("observation"),
            "intervention": empty_table("intervention"),
        }, status

    status = "loaded"
    sources = pd.DataFrame([{
        "source_id": "EXT-GALETA",
        "citation": "Keller & Jackson (1993) OCS Study MMS 93-0048; NCEI accession 9400033",
        "doi": "",
        "licence": "UNCLEAR",
        "acquired": "2026-11-12",
        "method_read": f"loaded from {raw_dir.as_posix()}",
        "checksum": "",
    }])
    return {
        "source": validate("source", sources),
        "site": empty_table("site"),
        "event": empty_table("event"),
        "observation": empty_table("observation"),
        "intervention": empty_table("intervention"),
    }, status


# ---------------------------------------------------------------------------
# 5. Build, write, and reconcile
# ---------------------------------------------------------------------------
def combine_tables(table_dicts: list[dict[str, pd.DataFrame]]) -> dict[str, pd.DataFrame]:
    var_units = load_variable_dictionary()
    merged: dict[str, pd.DataFrame] = {}
    for tname in TABLE_COLUMNS:
        parts = [d[tname] for d in table_dicts if len(d[tname]) > 0]
        df = pd.concat(parts, ignore_index=True) if parts else empty_table(tname)
        if tname == "source":
            df = df.drop_duplicates(subset=["source_id"], keep="first").reset_index(drop=True)
        elif tname == "site":
            df = df.drop_duplicates(subset=["site_id"], keep="first").reset_index(drop=True)
        elif tname == "event":
            df = df.drop_duplicates(subset=["event_id"], keep="first").reset_index(drop=True)
        merged[tname] = validate(tname, df, var_units=var_units)
    return merged


def build_small_tables(root: Path = ROOT) -> dict[str, pd.DataFrame]:
    z15 = load_zengel2015(root)
    z22 = load_zengel2022(root)
    naip = load_naip_edge_cells(root)
    gal, _ = load_galeta_mangrove(root)
    return combine_tables([z15, z22, naip, gal])


def reconcile(
    small: dict[str, pd.DataFrame],
    diver_tables: dict[str, pd.DataFrame] | None = None,
    diver_stats: dict[str, object] | None = None,
    root: Path = ROOT,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def _add(dataset: str, check: str, expected: object, actual: object, match: bool, note: str = "") -> None:
        rows.append({
            "dataset": dataset,
            "check": check,
            "expected": str(expected),
            "actual": str(actual),
            "reconciled": bool(match),
            "note": note,
        })

    obs = small["observation"]
    sites = small["site"]
    events = small["event"]
    interventions = small["intervention"]

    # 1. Zengel 2015 reconciliation against data/external/zengel2015/zengel2015_group_means.csv
    z15_ref = pd.read_csv(root / "data" / "external" / "zengel2015" / "zengel2015_group_means.csv")
    z15_ev = events[events["campaign"].str.startswith("zengel2015_", na=False)]
    z15_obs = obs[obs["event_id"].isin(z15_ev["event_id"])]
    _add("zengel2015", "total_rows", len(z15_ref), len(z15_obs), len(z15_ref) == len(z15_obs),
         "data/external/zengel2015/zengel2015_group_means.csv")
    _add("zengel2015", "measured_rows", int(z15_ref["mean"].notna().sum()), int(z15_obs["value"].notna().sum()),
         int(z15_ref["mean"].notna().sum()) == int(z15_obs["value"].notna().sum()),
         "83 numeric group means + 3 ND rows")
    _add("zengel2015", "nd_rows_censor_flag", int(z15_ref["mean"].isna().sum()),
         int((z15_obs["censor_flag"] == "no_limit_available").sum()),
         int(z15_ref["mean"].isna().sum()) == int((z15_obs["censor_flag"] == "no_limit_available").sum()),
         "3 ND rows carried as censor_flag=no_limit_available, value=NaN")
    ref_sum = round(float(z15_ref["mean"].dropna().sum()), 6)
    act_sum = round(float(z15_obs["value"].dropna().sum()), 6)
    _add("zengel2015", "sum_of_group_means_checksum", ref_sum, act_sum, abs(ref_sum - act_sum) < 1e-6,
         "Exact sum over all 83 numeric group means")
    z15_int = interventions[interventions["source_id"] == "EXT-ZENGEL2015"]
    _add("zengel2015", "interventions_randomized_vs_chosen", "randomized:1;chosen:5",
         f"randomized:{int((z15_int['assigned']=='randomized').sum())};chosen:{int((z15_int['assigned']=='chosen').sum())}",
         int((z15_int["assigned"] == "randomized").sum()) == 1 and int((z15_int["assigned"] == "chosen").sum()) == 5,
         "Planting randomized; manual/mechanical chosen")

    # 2. Zengel 2022 reconciliation against workbook and results/p3_treatment/
    z22_sites = sites[sites["source_id"] == "EXT-ZENGEL2022"]
    _add("zengel2022", "dsas_plot_count", 33, len(z22_sites), len(z22_sites) == 33,
         "33 plots in DSAS lumped and annual sheets")
    _add("zengel2022", "plots_with_gps_vs_none", "gps:25;none:8",
         f"gps:{int((z22_sites['coordinate_quality']=='gps').sum())};none:{int((z22_sites['coordinate_quality']=='none').sum())}",
         int((z22_sites["coordinate_quality"] == "gps").sum()) == 25 and int((z22_sites["coordinate_quality"] == "none").sum()) == 8,
         "8 DSAS plots (6A-6E, 19-20, 20-21, 22-23) have no GPS rows in GIS field erosion points")

    for camp, exp_n in [
        ("zengel2022_dsas_lumped", 165),
        ("zengel2022_dsas_annual", 165),
        ("zengel2022_field_erosion", 132),
        ("zengel2022_wave_power", 330),
        ("zengel2022_shear_strength", 17),
    ]:
        eids = events.loc[events["campaign"] == camp, "event_id"]
        n_obs = int(obs["event_id"].isin(eids).sum())
        _add("zengel2022", f"rows_{camp}", exp_n, n_obs, n_obs == exp_n)

    # Check pre-spill adjusted treatment group change means against results/p3_treatment/A_prespill_adjusted.csv
    p3_a = pd.read_csv(root / "results" / "p3_treatment" / "A_prespill_adjusted.csv")
    ev_lumped = events[events["campaign"] == "zengel2022_dsas_lumped"][["event_id", "site_id", "date"]]
    obs_lumped = obs[obs["event_id"].isin(ev_lumped["event_id"])].merge(ev_lumped, on="event_id")
    piv = obs_lumped.pivot(index="site_id", columns="date", values="value")
    change_10_12 = piv["2010-2012"] - piv["2005-2010"]
    z22_int = interventions[interventions["source_id"] == "EXT-ZENGEL2022"].set_index("site_id")["treatment"]
    manual_ids = z22_int[z22_int == "manual_removal"].index
    planted_ids = z22_int[z22_int == "mechanical_plus_planting"].index
    exp_man = round(float(p3_a.loc[0, "mean_a"]), 4)
    act_man = round(float(change_10_12.loc[manual_ids].mean()), 4)
    _add("zengel2022", "p3_A_manual_2010_2012_change_mean", exp_man, act_man, abs(exp_man - act_man) <= 1e-4,
         "results/p3_treatment/A_prespill_adjusted.csv row 0")
    exp_pl = round(float(p3_a.loc[2, "mean_a"]), 4)
    act_pl = round(float(change_10_12.loc[planted_ids].mean()), 4)
    _add("zengel2022", "p3_A_planted_2010_2012_change_mean", exp_pl, act_pl, abs(exp_pl - act_pl) <= 1e-4,
         "results/p3_treatment/A_prespill_adjusted.csv row 2")

    # Document raw PLOT_ID formatting mismatches in Zengel 2022 workbook plainly
    _add("zengel2022", "raw_sheet_plot_id_formatting_note",
         "33 canonical DSAS plot IDs",
         "Wave Power has 4 space-padded IDs ('1 - 2','7 - 8','8 - 9','9 - 10'); Shear strength has 4 reversed hyphen IDs ('17-16','18-17','21-20','23-22')",
         True,
         "MISMATCH REPORTED: canonicalized in schema.py while keeping raw_plot_id in observation.qualifier; in p3_treatment_erosion.py A2_wave_power unstripped Wave Power PLOT_IDs left 4 of 33 plots unmatched")

    # 3. NAIP and P2/P5 edge cells reconciliation against results/naip_edge_loss/summary.csv and data/demo/p5_sites.csv
    p5_ref = pd.read_csv(root / "data" / "demo" / "p5_sites.csv")
    edge_sites = sites[sites["source_id"].isin(["DER-NAIP-EDGE", "DER-P2"])]
    _add("edge_cells", "total_louisiana_cells", len(p5_ref), len(edge_sites), len(p5_ref) == len(edge_sites),
         "data/demo/p5_sites.csv and data/external/p2/la_cells_basins.csv")

    p5_ev = events[events["campaign"] == "p5_2010_2015"]
    p5_obs = obs[obs["event_id"].isin(p5_ev["event_id"])]
    exp_in_scope = int((p5_ref["status"] == "in_scope").sum())
    _add("edge_cells", "p5_in_scope_cells", exp_in_scope, len(p5_obs), exp_in_scope == len(p5_obs),
         "data/demo/p5_sites.csv status=='in_scope'")
    exp_p5_sum = round(float(p5_ref["observed_rate"].dropna().sum()), 4)
    act_p5_sum = round(float(p5_obs["value"].sum()), 4)
    _add("edge_cells", "p5_observed_rate_sum_checksum", exp_p5_sum, act_p5_sum, abs(exp_p5_sum - act_p5_sum) <= 1e-3,
         "Sum of observed_rate across all 12,696 in-scope cells")

    naip_sum = pd.read_csv(root / "results" / "naip_edge_loss" / "summary.csv").set_index("period")
    for period in ("2010-2015", "2010-2017"):
        ev_p = events[events["campaign"] == f"naip_edge_{period}"]
        obs_p = obs[obs["event_id"].isin(ev_p["event_id"])]
        exp_cells = int(naip_sum.loc[period, "cells"])
        _add("edge_cells", f"naip_edge_{period}_cells", exp_cells, len(obs_p), exp_cells == len(obs_p),
             f"results/naip_edge_loss/summary.csv ({period})")
        noo_mask = obs_p["qualifier"].str.contains("max_oiling=NOO;", na=False)
        heavy_mask = obs_p["qualifier"].str.contains("max_oiling=Heavy;", na=False)
        _add("edge_cells", f"naip_edge_{period}_n_NOO", int(naip_sum.loc[period, "n_NOO"]), int(noo_mask.sum()),
             int(naip_sum.loc[period, "n_NOO"]) == int(noo_mask.sum()))
        _add("edge_cells", f"naip_edge_{period}_n_Heavy", int(naip_sum.loc[period, "n_Heavy"]), int(heavy_mask.sum()),
             int(naip_sum.loc[period, "n_Heavy"]) == int(heavy_mask.sum()))
        exp_noo_mean = round(float(naip_sum.loc[period, "noo_mean_rate"]), 3)
        act_noo_mean = round(float(obs_p.loc[noo_mask, "value"].mean()), 3)
        _add("edge_cells", f"naip_edge_{period}_noo_mean_rate", exp_noo_mean, act_noo_mean,
             abs(exp_noo_mean - act_noo_mean) <= 1e-3)

    # 4. DIVER wetland soil chemistry reconciliation against docs/DIVER_SOIL_STRUCTURE.md and results/pah_decline/
    if diver_tables is not None and diver_stats is not None:
        sc_ref = pd.read_csv(root / "results" / "pah_decline" / "station_campaign.csv")
        d_obs = diver_tables["observation"]
        d_sites = diver_tables["site"]
        d_events = diver_tables["event"]
        _add("diver_soil", "soil_rows_5_campaign_files", 330464, diver_stats["soil_rows_all_5_files"],
             diver_stats["soil_rows_all_5_files"] == 330464, "docs/DIVER_SOIL_STRUCTURE.md")
        _add("diver_soil", "soil_samples_5_campaign_files", 14926, diver_stats["soil_samples_all_5_files"],
             diver_stats["soil_samples_all_5_files"] == 14926, "docs/DIVER_SOIL_STRUCTURE.md")
        _add("diver_soil", "filtered_pah_hopane_rows", 127585, diver_stats["filtered_pah_hopane_rows"],
             diver_stats["filtered_pah_hopane_rows"] == 127585, "results/pah_decline/processing_log.txt")
        _add("diver_soil", "pah_hopane_samples", 1698, len(d_events), len(d_events) == 1698,
             "results/pah_decline/processing_log.txt")
        _add("diver_soil", "assigned_stations", 200, len(d_sites), len(d_sites) == 200,
             "200 stations in results/pah_decline/processing_log.txt (201 station labels in raw 5-file soil before filtering Fall2010-only stations)")
        _add("diver_soil", "resolved_sample_compound_keys", 100181, diver_stats["resolved_sample_compound_keys"],
             diver_stats["resolved_sample_compound_keys"] == 100181, "results/pah_decline/processing_log.txt")
        _add("diver_soil", "pah_below_detection_count", 24705, diver_stats["pah_nd_count"],
             diver_stats["pah_nd_count"] == 24705,
             "24,705 non-detect PAH sample-compound observations; stored with value=NaN and original_value preserved")
        _add("diver_soil", "complete_samples_with_58_compound_sum", 1697,
             int((d_obs["variable"] == "pah_sum_58").sum()),
             int((d_obs["variable"] == "pah_sum_58").sum()) == 1697,
             "1 sample dropped for missing compounds (1,697 of 1,698)")
        _add("diver_soil", "samples_with_hopane_ratio", 1587,
             int((d_obs["variable"] == "pah_hopane_ratio").sum()),
             int((d_obs["variable"] == "pah_hopane_ratio").sum()) == 1587,
             "110 samples with hopane non-detected have no ratio (1,587 of 1,697)")
        sc_act = diver_stats["station_campaign_df"]
        _add("diver_soil", "station_campaign_depth_rows", len(sc_ref), len(sc_act), len(sc_ref) == len(sc_act),
             "results/pah_decline/station_campaign.csv")
        exp_sc_sum = round(float(sc_ref["pah_sum"].sum()), 4)
        act_sc_sum = round(float(sc_act["pah_sum"].sum()), 4)
        _add("diver_soil", "station_campaign_pah_sum_checksum", exp_sc_sum, act_sc_sum,
             abs(exp_sc_sum - act_sc_sum) / exp_sc_sum <= 1e-6,
             "Sum of station-campaign median pah_sum across 684 rows (rel diff 3.6e-9 from L-BFGS-B Tobit solver across OS)")

    # 5. Galeta check
    gal_src = small["source"][small["source"]["source_id"] == "EXT-GALETA"]
    gal_status = gal_src["method_read"].iloc[0] if len(gal_src) else "missing"
    _add("galeta", "raw_data_check", "not loaded: raw data absent", gal_status,
         gal_status == "not loaded: raw data absent",
         "Checked scripts/download_galeta.sh default path data/raw/galeta_ncei_9400033/data")

    return pd.DataFrame(rows)


def build_all(root: Path = ROOT) -> dict[str, object]:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    RECON_DIR.mkdir(parents=True, exist_ok=True)

    small = build_small_tables(root)
    for tname, df in small.items():
        out_path = SCHEMA_DIR / f"{tname}.csv"
        df.to_csv(out_path, index=False)

    diver_tables, diver_stats = load_diver_wetland_soil(root)
    for tname, df in diver_tables.items():
        out_path = SCHEMA_LOCAL_DIR / f"{tname}.csv"
        df.to_csv(out_path, index=False)

    recon_df = reconcile(small, diver_tables, diver_stats, root=root)
    recon_df.to_csv(RECON_DIR / "reconciliation.csv", index=False)
    return {"small": small, "diver": diver_tables, "reconciliation": recon_df}


if __name__ == "__main__":
    res = build_all()
    print(res["reconciliation"].to_string(index=False))
