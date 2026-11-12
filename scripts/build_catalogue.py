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
    dict(id="EXT-GALETA", role="external (not committed)", patterns=[],
         name="Bahia Las Minas (Galeta), Panama 1986 refinery oil spill: mangrove forest (MGF) and mangrove fringe/prop-root (MGR) monitoring, 1987-1992",
         source="NCEI/NODC accession 9400033 (MMS OCS Study 93-0048, Keller and Jackson eds. 1993; Duke 1993 and Garrity and Levings 1993), "
                "https://www.ncei.noaa.gov/archive/accession/9400033; files from https://www.ncei.noaa.gov/data/oceans/archive/arc0001/9400033/1.1/data/0-data",
         licence="UNCLEAR: catalogue record says CC0 1.0 but access level 'non-public' and rights 'otherRestrictions' (conflict, ask NCEI); .doc files request citation",
         acquired="2026-11-12", method="Directory index over HTTPS (scripts/download_galeta.sh); comma-separated text, no header row, column names "
                "from mgf.doc and mgr.doc; read with pandas (scripts/galeta_description.py)",
         checksums="25 data files; SHA-256 listed in scripts/download_galeta.sh and docs/MANGROVE_INVENTORY.md",
         notes="No pre-spill data, no cleanup variable, no coordinates. Raw files not committed; summaries in results/galeta/ (results are not catalogued).",
         used_by="Phase C1 description (docs/GALETA_MANGROVE_DESCRIPTION.md)"),
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
    dict(id="EXT-CRMS-SOIL", role="external", patterns=["data/external/crms_soil/*.csv"],
         name="CPRA CRMS soil properties (cores by station, date and depth slice), Louisiana, 2006-2023",
         source="CPRA CIMS full-table export https://cims.coastal.la.gov/RequestedDownloads/ZippedFiles/CRMS_Soil_Properties.zip",
         licence="not found; CRMS disclaimer page says public information, may be copied, byline requested (wording refers to USGS data; applicability ASSUMED)",
         acquired="2026-11-12", method="curl download of the zip; CSV (latin-1, 16,508 rows, 392 sites) copied unchanged; read with pandas",
         checksums="zip a5b67ff4...; csv 0bf7f73b... (SHA-256; see SOURCE.md)",
         notes="Soil Salinity (ppt) not labelled as porewater or extract salinity. Marsh interiors, not the oiled edge.",
         used_by="validation/soil_layer_check.py"),
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
    dict(id="REF-TREATMENT-EVIDENCE", role="reference (compiled from literature)",
         patterns=["data/knowledge/*.csv", "data/knowledge/*.md"],
         name="Literature evidence for cleanup treatments without project outcome data, and elicited prior ranges",
         source="Compiled 2026-11-12 by a reading agent from NOAA marsh guidance (2022 update), Hoff 1995, Pezeshki et al. 2000, "
                "Michel and Rutherford 2014 (abstract) and others; each row carries its citation and access level",
         licence="facts compiled from cited sources", acquired="2026-11-12",
         method="Web search and reading; rows marked FULL TEXT, ABSTRACT or SECONDARY. elicited_priors.csv set by the "
                "orchestrator with the rule in docs/SCENARIO_PROGRAMME_PLAN.md (A3)",
         checksums="see catalogue.csv",
         notes="Most primary papers were not opened; numbers came through text extraction of guidance PDFs and are not "
               "re-checked against originals. Prior ranges are ASSUMED, wide, and Proposed.", used_by="scenario_composer (elicited options)"),
    dict(id="EXT-TURNER2016", role="external", patterns=["data/external/turner2016/*.xlsx"],
         name="Turner et al. island erosion rates, Barataria Bay, Breton Sound, Terrebonne Bay, 1988-2013",
         source="GRIIDC doi:10.7266/N72J68WS (UDI R4.x264.196:0008)", licence="CC0 (landing-page JSON-LD; visible wording not found)",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/2486; copied unchanged; read with pandas",
         checksums="see catalogue.csv; SOURCE.md",
         notes="Sheet1 (width) has 41 island rows, Sheet2 (length) 46 (Terrebonne 5 vs 10), unresolved; multi-row headers; "
               "lat/lon in degrees and minutes, datum not stated. Not analysed.", used_by="catalogue only (no model uses it yet)"),
    dict(id="EXT-ZENGEL2022-META", role="external", patterns=["data/external/zengel2022_meta/*.xlsx"],
         name="Zengel et al. synthesis of wetland vegetation response to oiling (compiled dataset, 1,158 rows)",
         source="GRIIDC doi:10.7266/n7-cn03-z792 (UDI R6.x813.000:0001); linked from the NOAA repository record of "
                "Ecol. Appl. 32(1):e02489", licence="CC0 (landing-page JSON-LD; visible wording not found)",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/3632; copied unchanged; read with pandas",
         checksums="see catalogue.csv; SOURCE.md",
         notes="No coordinates; missing values are the string 'NA'; no detection limits. Link to the Ecol. Appl. supplement "
               "unconfirmed (Wiley page blocked by a bot challenge, not bypassed). Not analysed.", used_by="catalogue only"),
    dict(id="EXT-CHANDELEUR-SHORELINE", role="external", patterns=["data/external/chandeleur_shoreline/*"],
         name="Chandeleur Islands shoreline movement 2012-2017 (shapefiles and net shoreline movement table)",
         source="GRIIDC doi:10.7266/n7-0caw-d652 (UDI R4.x262.212:0004)", licence="CC0 (landing-page JSON-LD; visible wording not found)",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/1916; 52 files copied unchanged; table read with pandas, "
                "geometry not read", checksums="see catalogue.csv; SOURCE.md",
         notes="NetShorelineMovement 488 rows x 12 columns. Metadata calls IntersectX/Y decimal degrees, but the values (322,164 to "
               "323,645 and 3,305,083 to 3,312,677) are projected metres; .prj of ACERShorelines and Sites reads NAD_1983_UTM_Zone_16N. "
               "Rate-of-change unit not written (m/yr ASSUMED). Not analysed.", used_by="catalogue only"),
    dict(id="EXT-CHANDELEUR-FINGERPRINT", role="external", patterns=["data/external/chandeleur_fingerprint/*.csv"],
         name="Chandeleur Island salt marsh oil residue fingerprinting, 2016-2017 (categorical results)",
         source="GRIIDC doi:10.7266/N7GQ6WCZ (UDI R4.x262.000:0042)", licence="CC0 (landing-page JSON-LD; visible wording not found)",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/4020; only the CSV copied unchanged; the 9.8 MB "
                "chromatogram PDF is not committed (name, size, sha256 in SOURCE.md)", checksums="see catalogue.csv; SOURCE.md",
         notes="12 rows; categorical results only, no concentrations, no detection limits; one blank-date row and one NA row; file is "
               "not valid UTF-8 (read as cp1252). PDF not read.", used_by="catalogue only"),
    dict(id="EXT-HUETTEL2018", role="external", patterns=["data/external/huettel2018/*.xlsx"],
         name="Huettel et al. 2018: Pensacola Beach oxygen profiles, buried-agglomerate n-alkanes, and St. George Island reference-core hydrocarbons and TOC",
         source="GRIIDC doi:10.7266/N7XW4HBZ (R5.x278.000:0006), doi:10.7266/n7-jjcn-y650 (R5.x278.000:0015) and doi:10.7266/N7BZ64J8 "
                "(R5.x278.000:0011); paper Mar. Pollut. Bull. 126:488-500, doi:10.1016/j.marpolbul.2017.10.061", licence="not found (GRIIDC terms not fetched)",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/3500, /3510 and (0015) dataset_4193.zip; xlsx copied unchanged; read with pandas",
         checksums="see catalogue.csv; SOURCE.md",
         notes="Florida beaches, not Louisiana marsh. Report-style sheets with multi-row headers. Alkanes.xlsx (R5.x278.000:0015; zip sha256 "
               "c9b83d64...) holds n-alkanes C15-C40 in mg/kg by day after start (0-1152) and depth (0-50 cm) for sediment-oil agglomerates "
               "buried in Pensacola Beach, 2010-10-22 to 2013-12-16. The 17.7 MB lab tide file (R5.x278.000:0012) is not committed. "
               "Records R5.x278.000:0003, 0004 and 0005 return HTTP 404 at the GRIIDC data URL (2026-11-12); other records of the study "
               "were not checked. Not analysed.",
         used_by="catalogue only"),
    dict(id="EXT-DIVER-WETLAND", role="external (not committed)", patterns=[],
         name="NOAA DIVER DWH Shoreline package: Coastal Wetland Vegetation Plan samples 2010-2013 (soil, sediment, tissue chemistry)",
         source="NCEI DWH DIVER archive https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/Shoreline/ (five "
                "CoastalWetlandVegetationPlan Samples tars: Fall 2010, Spring 2011, Fall 2011, Fall 2012, Fall 2013; also read: "
                "RapidMarshOilingAssessment and Shoreline-Baseline-2010 Samples tars). The DIVER packages carry no accession number. "
                "Related ERMA GIS accession 0163814, DOI 10.7289/v5mw2fcq, was NOT downloaded (download timed out)",
         licence="Access level 'Public' and NOAA/NCEI no-warranty wording in the Fall 2010 metadata XML; no licence identifier found; "
                 "full text of the access constraints not read",
         acquired="2026-11-12 (downloaded and counted, not kept)",
         method="scripts/download_diver.sh into data/external/diver_dwh/ (git-ignored); long-format CSV, 60 columns, one row per analytical result",
         checksums="tar SHA-256 values are in /home/claude/work/stage2/inventory_noaa_beach.md (not in the repository)",
         notes="Counts as verified by the orchestrator (not the 1,894 samples or 2,779 sites first asked for): five CWVP CSVs plus "
               "rapid marsh oiling plus baseline 2010 = 484,289 result rows, 2010-05-24 to 2013-12-11; distinct Sample_ID by matrix "
               "Soil 14,926, Tissue 3,078, Sediment 998, Water 6, Water-Blank 3, Tarball 2; stations by matrix Soil 202, Tissue 188, "
               "Sediment 151; lat 28.998 to 30.483, lon -91.112 to -87.003. Units as recorded (PPB 348,901 rows; ug/L, mg/L, PCT, "
               "% by Weight, m2 also present; soil rows carry mg/L and ug/L, which was not checked for correctness). Basis: Dry Weight "
               "356,165 rows, Not Defined 119,662, Wet Weight 7,670. Censoring: only a Detection_Extent category and Qualifier_Code, no "
               "numeric detection or reporting limit column found; 'At or Below Detection Limit' 115,991 rows and 'No Detection Limit "
               "Available' 95,090 rows. Sharing flag: Publicly Available 475,493 rows, Trustee and RP 8,796 rows (the Trustee and RP "
               "rows may not be redistributable; not checked). Datum NAD83 from the Fall 2010 metadata only. NOT checked: whether any "
               "package is the 1,894-sample soil set, the CVHSS package (not located), FieldObservations tars, other datums, the full "
               "licence text, depth intervals, analytical methods. No analysis done.", used_by="planned_variables.csv (candidate source), not yet used"),
    dict(id="EXT-DIVER-NEARSHORE", role="external (not committed)", patterns=[],
         name="NOAA DIVER DWH Nearshore Sediment and Water samples, 2010-2011",
         source="NCEI dataset gov.noaa.ncdc:C02078, DOI 10.25921/4E7E-MS59; archive folder "
                "https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/NearshoreSedimentandWater/ (Baseline Sampling for "
                "Louisiana, Preassessment Sampling for Louisiana, Blank Study 2011). No NCEI accession number stated on the page",
         licence="ISO record lists https://creativecommons.org/publicdomain/zero/1.0/ but also an access level of 'non-public'; the NCEI "
                 "page says 'All data is publicly available'. Conflict unresolved",
         acquired="2026-11-12 (downloaded and counted, not kept)",
         method="scripts/download_diver.sh into data/external/diver_dwh/ (git-ignored); 15 long-format CSVs, 60 columns",
         checksums="tar SHA-256 values are in /home/claude/work/stage2/inventory_noaa_beach.md (not in the repository)",
         notes="Counts as verified by the orchestrator: 176,816 result rows, 2010-06-21 to 2011-03-24; distinct Sample_ID Sediment 1,870, "
               "Water 651, Blank 135 (not the 1,731 first asked for); lat 29.0 to 30.151, lon -93.897 to -89.035. Units as recorded: PPB "
               "83,414 rows, ug/L 80,590, PCT 5,639, ng/L 3,164, PPM 605, mg/L 535. Basis: Dry Weight 89,069 rows, Total (water) 84,289, "
               "Wet Weight 589. Censoring by category only: 'At or Below Detection Limit' 90,992 rows, 'Between Detection Limit and "
               "Reporting Limit' 25,705, no numeric limit column found. Sharing flag: Publicly Available 167,140 rows, Trustee and RP 9,676. "
               "Subtidal and nearshore sediment, not marsh soil. NOT checked: datum, analyte list, Photographs and RelatedFiles tars (4.9 and "
               "9.6 GB, 0.4 GB), FieldObservations tar, which licence applies. No analysis done.", used_by="planned_variables.csv (candidate source), not yet used"),
    dict(id="EXT-GRIIDC-LANDSAT-MARSH", role="external (not committed)", patterns=[],
         name="Landsat TM-derived marsh cover and vulnerability, Terrebonne, Barataria and Breton Sound basins (clear-sky data set with missing pixels)",
         source="GRIIDC doi:10.7266/N7Z31X2K (UDI R4.x264.000:0051, dataset id 3209)", licence="CC0 per the landing-page JSON-LD; visible wording not found; licence not checked",
         acquired="2026-11-12", method="https://data.griidc.org/download/dataset/3209 (302 to /api/datasets/zip/3209, HTTP 200); "
                "zip 1,113,115,709 bytes, not committed; ENVI rasters read from headers and one raster",
         checksums="zip SHA-256 51a3f39fa50920c2eaffb9168ac5da4dd24681ea0f207e496e3006324d0c5bc0; s_2009_0902_veg_md 7447cb4930c229c6d37367a9597ef87d060a8080cb830327b9976a6cd218ffe7",
         notes="Downloaded (not committed). Single base scene 2009-09-02, Landsat TM path 022 rows 039/040 (a 2010-10-07 clear-sky scene "
               "fills a thin line of missing data per the ReadMe). 27 ENVI rasters, 5298 x 3964 at 30 m, UTM zone 15N (EPSG code not stated in the header): "
               "three-class vegetation maps (0 unclassified, 1 vegetation <= 40 %, 2 vegetation > 40 %), plus surface reflectance (-sr, 3 bands) "
               "and unmixing fractions (-spun; ReadMe says 3 bands, header says 4, unresolved). The landing page lists a 2009-09-02 collection "
               "period while the abstract says scenes span 1984-2011; the archive holds the 2009 scene only. Only the headers and one raster were "
               "read. Relevant to decision D10 (land/water classifier cross-check).",
         used_by="none yet"),
    dict(id="EXT-PLANT-OILING", role="external (not committed)", patterns=[],
         name="Plant oiling observations (DIVER FieldObservations and ERMA vegetation layers)",
         source="NCEI DIVER FieldObservations tars in the Shoreline CWVP folders; ERMA accession 0163814 (DOI 10.7289/v5mw2fcq)",
         licence="not checked", acquired="not obtained",
         method="Not downloaded: the FieldObservations tars were not fetched and the ERMA download endpoint timed out",
         checksums="none", notes="Nothing was read. Whether these hold oiling length or percent cover per plant or site is not known. "
               "Sample tars checked for Rapid Marsh Oiling contain tissue and water rows only.", used_by="none yet"),
    dict(id="EXT-MICHEL2017", role="external (not committed)", patterns=[],
         name="Michel et al. 2017 sand-beach shoreline treatment data",
         source="Mar. Ecol. Prog. Ser. 576:203-218, doi:10.3354/meps11917 (DOI taken from the NOAA repository record)",
         licence="article CC BY per the NOAA repository record; no data licence found", acquired="not obtained",
         method="No public dataset found on the abstract and repository pages read",
         checksums="none", notes="Not found. The full text and supplement were not read, so a data availability statement may exist. "
               "NOAA ERMA shoreline treatment layers (accession 0163818 appeared in a search) were not opened for treatment fields.",
         used_by="none yet"),
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
    dict(id="DER-SOIL-LAYERS", role="derived (retrieved values, tabulated)", patterns=["data/external/soil_layers/*.csv"],
         name="SSURGO map-unit horizons and SoilGrids v2 values at the 392 CRMS site positions",
         source="USDA NRCS Soil Data Access (SSURGO) and ISRIC SoilGrids v2.0 cloud rasters, at positions from EXT-CRMS-SOIL",
         licence="not checked", acquired="2026-11-12", method="scripts/fetch_soil_layers.py (docs/SOIL_LAYER_CHECK_PLAN.md)",
         checksums="see catalogue.csv; SOURCE.md",
         notes="Values as returned by the services; SoilGrids has no raster value at 90 of 392 sites (bdod).",
         used_by="validation/soil_layer_check.py, tests/test_soil_layer_check.py"),
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
        if p.is_file() and p.name not in SKIP and not rel.startswith(("data/raw/", "data/external/diver_dwh/")) \
                and "__pycache__" not in rel \
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
            try:
                d = pd.read_csv(path, low_memory=False)
            except UnicodeDecodeError:
                d = pd.read_csv(path, low_memory=False, encoding="cp1252")
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
