"""Build the data catalogue and the human-readable data documentation (milestone P4).

Inputs : the hand-written dataset metadata below, data/meta/variable_dictionary.csv, and the data files.
Outputs: data/meta/catalogue.csv  (one row per file: dataset, role, checksum, rows, columns)
         docs/DATA_CATALOGUE.md   (datasets, provenance, files)
         docs/VARIABLE_DICTIONARY.md
Run after any data change:  python scripts/build_catalogue.py
tests/test_data_catalogue.py fails if a data file changes, appears or disappears without a rebuild, or if a
dictionary variable is missing from its files or falls outside its valid range.
"""
from __future__ import annotations

import csv
import fnmatch
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "meta"
SKIP = {"README.md", "LICENSE", "SOURCE.md"}

# role: external (as obtained), derived (computed here from external data), synthetic (generated, not
# evidence), instrument (forms with no outcome data), reference (third-party table typed or read from a report)
DATASETS = [
    dict(id="EXT-SCAT", role="external (not committed)", patterns=[],
         name="Deepwater Horizon SCAT shoreline oiling, Louisiana",
         source="NOAA ERMA SCAT layers archived at NCEI, Accession 0163818, DOI 10.7289/v53t9ffx; layers 18611 "
                "(maximum oiling per zone) and 18612 (all ground surveys incl. No Oil Observed)",
         licence="US Government work, public", acquired="2026-11-11",
         method="HTTPS archive folder arc0110/0163818/1.1 (scripts/download_scat.sh); read with geopandas",
         checksums="18611 .shp 616806d1..., .dbf f8dcba8f...; 18612 .shp ab2c89b4..., .dbf 97c80130... (SHA-256)",
         notes="65 MB; not committed; every derived edge-cell table starts here", used_by="P1, P2, CRMS match, Landsat site choice"),
    dict(id="EXT-NAIP", role="external (not stored)", patterns=[],
         name="USDA NAIP aerial imagery, Louisiana, 2010/2013/2015/2017",
         source="Microsoft Planetary Computer STAC collection 'naip'", licence="public domain (USDA)", acquired="read 2026-11-11",
         method="Cloud-optimised GeoTIFFs read through rasterio overviews (2 m, 8 m, 16 m); tile IDs and dates kept in "
                "tile_classifiers.csv", checksums="not stored; tile IDs recorded",
         notes="Land/water rule fails on water-dominated and plume tiles (REVIEW_NOTES B1)", used_by="NAIP edge loss, P1, P2"),
    dict(id="EXT-LANDSAT", role="external (not stored)", patterns=[],
         name="Landsat 5/7/8 Collection 2 Level-2 surface reflectance",
         source="Microsoft Planetary Computer STAC collection 'landsat-c2-l2'", licence="public domain (USGS)",
         acquired="read 2026-11-11", method="SWIR1, red, NIR and QA_PIXEL warped to UTM 15N; scene IDs kept",
         checksums="not stored; scene IDs recorded", notes="Sensor change L5 to L8 between epochs (REVIEW_NOTES B4)",
         used_by="Landsat NDVI recovery, P1, P2"),
    dict(id="EXT-CRMS", role="external", patterns=["data/external/crms/*.csv"],
         name="Louisiana CRMS marsh vegetation by site and year, 2006-2025",
         source="github.com/anamikadristi/coastal-marsh-vegetation-extreme-events, commit 76e2143 (derived by A. Dristi "
                "from CPRA CRMS, NOAA HURDAT2, NASA MOD13Q1)", licence="MIT", acquired="previous session (source commit dated 2026-10-24)",
         method="Copied unchanged; read with pandas", checksums="see catalogue.csv",
         notes="Not checked against the original CRMS export; no oil information", used_by="event studies"),
    dict(id="EXT-ZENGEL2015", role="external", patterns=["data/external/zengel2015/zengel2015_S1_Table.xlsx"],
         name="Zengel et al. 2015 S1 Table: heavily oiled marsh, treatment groups 2010-2012",
         source="PLoS ONE 10(7):e0132324, doi:10.1371/journal.pone.0132324, supplementary S1 Table",
         licence="CC BY 4.0", acquired="2026-11-11", method="Downloaded from journals.plos.org; parsed with openpyxl",
         checksums="see catalogue.csv", notes="Same site and largely the same plots as Zengel 2022", used_by="treatment priors"),
    dict(id="EXT-ZENGEL2022", role="external", patterns=["data/external/zengel2022/*.xlsx"],
         name="Zengel et al. 2022 marsh erosion by treatment, plot data 1956-2018",
         source="GRIIDC doi:10.7266/VF524143 (UDI R6.x813.000:0007); paper Sci. Rep. 12:13802", licence="CC0",
         acquired="2026-11-11", method="https://data.griidc.org/download/dataset/4762; read with pandas",
         checksums="see catalogue.csv; GRIIDC's listed checksum does not match (SOURCE.md)",
         notes="5-9 plots per group, one site", used_by="P3, erosion priors"),
    dict(id="EXT-ADIOS", role="external (derived table)", patterns=["data/oil_properties.csv"],
         name="NOAA ADIOS oil properties, 1,460 oils",
         source="github.com/NOAA-ORR-ERD/noaa-oil-data", licence="public (NOAA)", acquired="previous session",
         method="scripts/build_oil_table.py from a local clone", checksums="see catalogue.csv",
         notes="Measured values only; missing where not measured", used_by="oil_library, dashboard"),
    dict(id="REF-NOAA-MARSH", role="reference (read from report)", patterns=["data/marsh_recovery_cases.csv"],
         name="63 published marsh oil-spill cases (NOAA 'Oil Spills in Marshes', Appendices A-D)",
         source="NOAA/ORR report, see docs/PROCESS_MODEL_AUDIT.md", licence="US Government work",
         acquired="previous session", method="Read from the PDF by an automated reader", checksums="see catalogue.csv",
         notes="Rows need checking against the PDF; model on it fails the baseline (D4)", used_by="marsh_recovery_model"),
    dict(id="REF-MOHAMMADIUN", role="reference (read from thesis)", patterns=["data/mohammadiun_appendixC_dataset.csv"],
         name="Mohammadiun et al. 2022 Appendix C dataset (marine response method choice)",
         source="J. Hazard. Mater. 436:129282 and the UBC thesis holding Appendix C", licence="see source",
         acquired="previous session", method="Typed from the thesis appendix", checksums="see catalogue.csv",
         notes="Open-water response, not shoreline; used only in the validation panel", used_by="validation_panel"),
    dict(id="DER-CRMS-SCAT", role="derived", patterns=["data/external/scat_dwh/*.csv"],
         name="CRMS sites matched to SCAT oiling", source="EXT-CRMS + EXT-SCAT", licence="as inputs", acquired="2026-11-11",
         method="scripts/match_crms_scat.py", checksums="see catalogue.csv", notes="", used_by="validation/oil_event_study.py"),
    dict(id="DER-LANDSAT-NDVI", role="derived", patterns=["data/external/landsat_barataria/*"],
         name="Landsat NDVI per SCAT segment, northern Barataria Bay, 2006-2016", source="EXT-LANDSAT + EXT-SCAT",
         licence="as inputs", acquired="2026-11-11", method="scripts/select_barataria_sites.py, landsat_ndvi.py, pool_ndvi_for_runner.py",
         checksums="see catalogue.csv", notes="Null result; 4 reference segments only", used_by="validation/satellite_recovery.py"),
    dict(id="DER-NAIP-EDGE", role="derived", patterns=["data/external/naip_edge/*"],
         name="NAIP edge cells, Barataria Bay box, 2010-2017", source="EXT-NAIP + EXT-SCAT", licence="as inputs",
         acquired="2026-11-11", method="scripts/build_edge_cells.py, naip_edge_extract.py (docs/NAIP_EDGE_LOSS_PLAN.md)",
         checksums="see catalogue.csv", notes="", used_by="validation/naip_edge_loss.py, P1"),
    dict(id="DER-P1", role="derived", patterns=["data/external/p1/*"],
         name="P1 exposure and Landsat epochs for the Barataria box", source="EXT-NAIP + EXT-LANDSAT", licence="as inputs",
         acquired="2026-11-11", method="scripts/exposure_metrics.py, landsat_edge_fraction.py (docs/P1_PRESPILL_CHECK_PLAN.md)",
         checksums="see catalogue.csv", notes="", used_by="validation/p1_prespill_check.py"),
    dict(id="DER-P2", role="derived", patterns=["data/external/p2/*", "data/external/p2/*/*"],
         name="P2 Louisiana edge cells by basin: NAIP 2010/2015, exposure, Landsat pre-spill", source="EXT-NAIP + EXT-LANDSAT + EXT-SCAT",
         licence="as inputs", acquired="2026-11-11",
         method="build_edge_cells.py --louisiana, assign_basins.py, run_p2_measurements.sh, landsat_split.sh (docs/P2_BASIN_HOLDOUT_PLAN.md)",
         checksums="see catalogue.csv", notes="Birdfoot excluded; Breton and Barataria keep only valid quadrants", used_by="validation/p2_basin_holdout.py, P3 C"),
    dict(id="DER-ZENGEL2015", role="derived", patterns=["data/external/zengel2015/zengel2015_group_means.csv"],
         name="Zengel 2015 S1 Table as a tidy table (86 values)", source="EXT-ZENGEL2015", licence="CC BY 4.0",
         acquired="2026-11-11", method="Parsed from the xlsx; no typing", checksums="see catalogue.csv", notes="", used_by="treatment_effects.py"),
    dict(id="DER-P5", role="derived", patterns=["data/demo/p5_sites.csv"],
         name="P5 demo site table: every Louisiana SCAT edge cell with model inputs, scope status, observed rate and held-out predictions",
         source="DER-P2 + results/p2_basin_holdout/predictions.csv", licence="as inputs", acquired="2026-11-11",
         method="scripts/build_p5_demo.py (docs/P5_DEMO_PLAN.md); model artefact models/p5_edge_loss_v1.json built alongside",
         checksums="see catalogue.csv; training-file checksums also in the model artefact",
         notes="status says why a cell has no prediction (site_evidence.STATUS_TEXT)", used_by="dashboard Site evidence tab, tests/test_p5_demo.py"),
    dict(id="SYN-SCENARIOS", role="synthetic (not evidence)", patterns=["data/scenario_training_dataset.csv", "data/lhs_scat_process_dataset.csv"],
         name="Synthetic scenario and process datasets", source="Generated by training_pipeline.py and process_model.py",
         licence="project", acquired="previous sessions", method="Latin hypercube sampling + rule-based labels",
         checksums="see catalogue.csv", notes="Rule-generated labels; models trained on them only copy the rules (REVIEW_NOTES A4)",
         used_by="run_benchmark.py, dashboard benchmark tab"),
    dict(id="INS-EXPERT", role="instrument (no outcome data)", patterns=["data/expert_scoring_*.csv"],
         name="Blind expert scoring sheet and template", source="expert_scoring.py", licence="project", acquired="previous session",
         method="Generated; awaiting scores (M6, on hold)", checksums="see catalogue.csv", notes="", used_by="expert_scoring.py"),
    dict(id="META", role="metadata", patterns=["data/meta/variable_dictionary.csv", "data/meta/planned_variables.csv"],
         name="Variable dictionary and planned (missing) variables", source="hand-written", licence="project", acquired="2026-11-11",
         method="edited by hand; checked by tests/test_data_catalogue.py", checksums="see catalogue.csv", notes="", used_by="docs"),
]


def data_files() -> list[str]:
    out = []
    for p in sorted((ROOT / "data").rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and p.name not in SKIP and not rel.startswith("data/raw/") and "__pycache__" not in rel \
                and rel != "data/meta/catalogue.csv":
            out.append(rel)
    return out


def dataset_of(rel: str) -> str | None:
    hits = [d["id"] for d in DATASETS if any(fnmatch.fnmatch(rel, pat) and rel.count("/") == pat.count("/")
                                              for pat in d["patterns"])]
    return hits[0] if hits else None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def shape(path: Path) -> tuple[str, str]:
    try:
        if path.suffix == ".csv":
            d = pd.read_csv(path, low_memory=False)
            return str(len(d)), ";".join(map(str, d.columns))
        if path.suffix == ".xlsx":
            x = pd.ExcelFile(path)
            return "", "sheets: " + ";".join(x.sheet_names)
    except Exception as e:  # noqa: BLE001
        return "", f"unreadable: {e}"
    return "", ""


def build() -> pd.DataFrame:
    rows = []
    for rel in data_files():
        ds = dataset_of(rel)
        r, cols = shape(ROOT / rel)
        rows.append({"file": rel, "dataset_id": ds or "UNCATALOGUED", "sha256": sha256(ROOT / rel),
                     "bytes": (ROOT / rel).stat().st_size, "rows": r, "columns": cols})
    return pd.DataFrame(rows)


def write_docs(cat: pd.DataFrame) -> None:
    lines = ["# Data catalogue", "",
             "Generated by `scripts/build_catalogue.py` from the metadata in that script and the files themselves; do not",
             "edit by hand. Machine-readable version with checksums: `data/meta/catalogue.csv`. Variables:",
             "`docs/VARIABLE_DICTIONARY.md`. Roles: external = as obtained; derived = computed here; synthetic = generated,",
             "not evidence; reference = read or typed from a report; instrument = forms without outcome data.", ""]
    lines += ["| ID | Role | Dataset | Source | Licence | Obtained | Files |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in DATASETS:
        n = int((cat.dataset_id == d["id"]).sum())
        lines.append(f"| {d['id']} | {d['role']} | {d['name']} | {d['source']} | {d['licence']} | {d['acquired']} | {n} |")
    for d in DATASETS:
        lines += ["", f"## {d['id']}: {d['name']}", "",
                  f"- Role: {d['role']}", f"- Source: {d['source']}", f"- Licence: {d['licence']}",
                  f"- Obtained: {d['acquired']}", f"- How obtained and read: {d['method']}",
                  f"- Checksums: {d['checksums']}", f"- Used by: {d['used_by']}"]
        if d["notes"]:
            lines.append(f"- Notes: {d['notes']}")
        files = cat[cat.dataset_id == d["id"]]
        if len(files):
            lines += ["", "| File | Rows | SHA-256 (first 12) |", "| --- | --- | --- |"]
            lines += [f"| `{r.file}` | {r.rows} | {r.sha256[:12]} |" for r in files.itertuples()]
    (ROOT / "docs" / "DATA_CATALOGUE.md").write_text("\n".join(lines) + "\n")

    v = pd.read_csv(META / "variable_dictionary.csv", dtype=str).fillna("")
    out = ["# Variable dictionary", "",
           "Generated from `data/meta/variable_dictionary.csv` by `scripts/build_catalogue.py`; edit the CSV, not this",
           "file. Valid ranges and allowed values are checked against the files by `tests/test_data_catalogue.py`.",
           "Module numbers follow the project brief (1 data, 2 characterisation, 3 remediation, 4 recovery,",
           "5 generalisation).", "",
           "| Variable | Definition | Unit | Type | Valid range / values | Missing | Derived by | Source | Module | Files |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in v.itertuples():
        rng = r.allowed_values.replace("|", ", ") if r.allowed_values else (
            f"{r.valid_min or '-inf'} to {r.valid_max or 'inf'}" if (r.valid_min or r.valid_max) else "")
        files = "<br>".join(f"`{f}`" for f in r.files.split(";"))
        out.append(f"| `{r.variable}` | {r.definition} | {r.unit} | {r.dtype} | {rng} | {r.missing_rule} | "
                   f"{r.derived_by} | {r.source_dataset} | {r.module} | {files} |")
    pv = pd.read_csv(META / "planned_variables.csv", dtype=str).fillna("")
    out += ["", "## Required by the project brief but not in the proof of concept (flagged)", "",
            "Soil, sediment and porewater variables from brief section 4 that the PoC does not use. Status: absent = no",
            "data in hand; partial = some data in hand but not usable in a cell-level model yet. Open sources are",
            "candidates; their coverage of our sites is unverified unless stated. Edit `data/meta/planned_variables.csv`.", "",
            "| Variable | Matrix | Unit | Status | Why it matters here | Open-source candidates | Comment |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    out += [f"| `{r.variable}` | {r.matrix} | {r.unit} | {r.status} | {r.why_it_matters_here} | "
            f"{r.open_source_candidates} | {r.comment} |" for r in pv.itertuples()]
    (ROOT / "docs" / "VARIABLE_DICTIONARY.md").write_text("\n".join(out) + "\n")


def main() -> None:
    META.mkdir(parents=True, exist_ok=True)
    cat = build()
    cat.to_csv(META / "catalogue.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    write_docs(cat)
    un = cat[cat.dataset_id == "UNCATALOGUED"]
    print(f"{len(cat)} files catalogued; {len(un)} uncatalogued")
    if len(un):
        print(un.file.to_string(index=False))


if __name__ == "__main__":
    main()
