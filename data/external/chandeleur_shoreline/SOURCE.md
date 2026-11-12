# Chandeleur Islands shoreline movement, 2012-2017

- Files: 52 files copied unchanged from the GRIIDC zip: shapefile sets (.shp, .shx, .dbf, .cpg, .prj, .qpj and some
  .shp.xml) for ACERShorelines, Sites, Transects, Baselines and four dated shorelines (2012_10OCT29.shp,
  2014_11NOV26, 2015_08AUG25, 2017_09SEP08), plus `NetShorelineMovement.xlsx` (sheets NetShorelineMovement, Metadata).
- Dataset: "Analyses of shoreline movement to assess sediment stabilization from 2012-10-29 to 2017-09-08", GRIIDC,
  doi:10.7266/n7-0caw-d652, UDI R4.x262.212:0004 (GRIIDC dataset id 1916). Authors: not checked.
- URL: https://data.griidc.org/data/R4.x262.212:0004
- Licence: CC0, from the JSON-LD `license` field on the landing page (visible wording not found; Terms & Conditions not fetched).
- Acquired 2026-11-12. How obtained: https://data.griidc.org/download/dataset/1916 returned a zip (523,567 bytes,
  SHA-256 edadaba5f553abe4619c3eaf086c058ca8438d2eb4196754b74bfb68add12732), extracted and copied unchanged
  (all 52 copies verified identical by sha256). Per-file SHA-256 in data/meta/catalogue.csv. NetShorelineMovement.xlsx
  SHA-256 4d6235de8ad69ff7561d7dfee0a345f1dc031cc803c1bd6b14774fb26aec87f8.
- Counts as read: NetShorelineMovement sheet 488 rows x 12 columns; dbf records ACERShorelines 16, Sites 24, Transects 126,
  Baselines 12 (from the .dbf headers; shapefile geometry not read).
- Known problems:
  - The workbook Metadata sheet calls IntersectX/IntersectY "Decimal degree". What was seen: the .prj of
    ACERShorelines and Sites reads `NAD_1983_UTM_Zone_16N` (central meridian -87, unit Meter), and the IntersectX/IntersectY
    values in the workbook run 322,164.7 to 323,644.6 and 3,305,083 to 3,312,677, which are projected metres, not degrees.
    The .prj files of the other shapefiles were not individually read here (the inventory found the same text in
    Baselines and Transects).
  - "Rate of Change" has no unit in the workbook; m/yr is implied (ASSUMED). The Metadata sheet's T1 date has a typo
    ("11/26/204"); the data value is 2014-11-26.
  - Shapefile naming is inconsistent (2012_10OCT29.shp with 2012_OCT29.dbf/.shx, and similar for 2015); copied as served.
  - Not checked: geometry validity, consistency of 24 Sites records and 12 Baselines with the 12 plots in the landing
    text, the shapefile XML metadata.
