"""Build data/oil_properties.csv from a local clone of NOAA's ADIOS oil database.

    git clone --depth 1 https://github.com/NOAA-ORR-ERD/noaa-oil-data
    python scripts/build_oil_table.py path/to/noaa-oil-data

One row per oil record, using the fresh (unweathered) sample: API gravity, the density measured closest to
15 C, the viscosity measured closest to 20 C, and the pour point. Values are converted to common units and
otherwise left as recorded. A blank means the record has no usable value, not zero.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "oil_properties.csv"
FIELDS = ["oil_id", "name", "location", "product_type", "reference_year", "api_gravity", "api_source",
          "density_kg_m3", "density_ref_c", "kinematic_viscosity_cst", "viscosity_ref_c", "viscosity_source",
          "pour_point_c"]


def value_of(measurement: dict | None) -> float | None:
    """A measurement holds either `value` or a `min_value`/`max_value` pair; use the value or the midpoint."""
    if not measurement:
        return None
    if measurement.get("value") is not None:
        return float(measurement["value"])
    bounds = [measurement.get("min_value"), measurement.get("max_value")]
    bounds = [float(b) for b in bounds if b is not None]
    return sum(bounds) / len(bounds) if bounds else None


def celsius(measurement: dict | None) -> float | None:
    value = value_of(measurement)
    if value is None:
        return None
    unit = measurement.get("unit")
    return {"C": value, "K": value - 273.15, "F": (value - 32) / 1.8}.get(unit)


def density_kg_m3(measurement: dict | None) -> float | None:
    value = value_of(measurement)
    if value is None:
        return None
    return {"kg/m^3": value, "g/cm^3": value * 1000, "g/mL": value * 1000}.get(measurement.get("unit"))


def closest(rows: list[dict], key: str, convert, target_c: float) -> tuple[float, float] | None:
    best = None
    for row in rows or []:
        value, temp = convert(row.get(key)), celsius(row.get("ref_temp"))
        if value is None or temp is None:
            continue
        if best is None or abs(temp - target_c) < abs(best[1] - target_c):
            best = (value, temp)
    return best


def kinematic_cst(measurement: dict | None) -> float | None:
    value = value_of(measurement)
    if value is None:
        return None
    return {"m^2/s": value * 1e6, "cSt": value, "mm^2/s": value}.get(measurement.get("unit"))


def dynamic_pa_s(measurement: dict | None) -> float | None:
    value = value_of(measurement)
    if value is None:
        return None
    return {"kg/(m s)": value, "Pa s": value, "cP": value / 1000, "mPa s": value / 1000, "P": value / 10}.get(measurement.get("unit"))


def record_row(record: dict) -> dict:
    meta = record.get("metadata", {})
    samples = record.get("sub_samples") or [{}]
    physical = samples[0].get("physical_properties", {})
    density = closest(physical.get("densities"), "density", density_kg_m3, 15.0)
    kinematic = closest(physical.get("kinematic_viscosities"), "viscosity", kinematic_cst, 20.0)
    source = "kinematic" if kinematic else ""
    if kinematic is None and density:
        dynamic = closest(physical.get("dynamic_viscosities"), "viscosity", dynamic_pa_s, 20.0)
        if dynamic:  # kinematic = dynamic / density; Pa s / (kg/m3) = m2/s, times 1e6 for cSt
            kinematic, source = (dynamic[0] / density[0] * 1e6, dynamic[1]), "dynamic / density"
    api, api_source = meta.get("API"), "stated"
    if api is None and density and abs(density[1] - 15.0) <= 1.0:
        # Standard definition: API = 141.5 / specific gravity at 60 F - 131.5 (density of water 999 kg/m3).
        api, api_source = 141.5 / (density[0] / 999.0) - 131.5, "from density"
    pour = celsius((physical.get("pour_point") or {}).get("measurement"))
    rounded = lambda v, n: "" if v is None else round(v, n)  # noqa: E731
    return {
        "oil_id": record.get("oil_id"), "name": meta.get("name", ""), "location": meta.get("location", ""),
        "product_type": meta.get("product_type", ""), "reference_year": (meta.get("reference") or {}).get("year", ""),
        "api_gravity": rounded(api, 1), "api_source": api_source if api is not None else "",
        "density_kg_m3": rounded(density[0] if density else None, 1), "density_ref_c": rounded(density[1] if density else None, 1),
        "kinematic_viscosity_cst": rounded(kinematic[0] if kinematic else None, 2),
        "viscosity_ref_c": rounded(kinematic[1] if kinematic else None, 1), "viscosity_source": source,
        "pour_point_c": rounded(pour, 1),
    }


def main(repo: str) -> None:
    files = sorted(Path(repo, "data", "oil").glob("*/*.json"))
    rows = [record_row(json.loads(path.read_text(encoding="utf-8"))) for path in files]
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} oils to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
