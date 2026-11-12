# CRMS soil properties (CPRA, Louisiana)

- Source: Coastal Protection and Restoration Authority (CPRA) of Louisiana, Coastwide Reference Monitoring System
  (CRMS), Coastal Information Management System (CIMS) weekly full-table export "Soil Properties".
  URL: https://cims.coastal.la.gov/RequestedDownloads/ZippedFiles/CRMS_Soil_Properties.zip (HTTP 200,
  application/x-zip-compressed, 544,476 bytes). Listed at https://cims.coastal.la.gov/FullTableExports.aspx.
- Acquired: 2026-11-12.
- Checksums (SHA-256): zip `a5b67ff49f71479161012708034d6c4fbc377d7827ca1b99f1999f4a917c6335` (the zip is not
  stored here); `CRMS_Soil_Properties.csv` (3,852,970 bytes, copied unchanged from the zip)
  `0bf7f73b048c9c5c188c1a40ac08fa6942a4885aca82972627c772fa81deeb50`.
- Not copied: the zip's SoilProperties.html and SoilProperties.xml (metadata; no unit table found by text search)
  and RESTORE_disclaimer.txt. The RESTORE disclaimer says the data were prepared under an award from the Gulf Coast
  Ecosystem Restoration Council (RESTORE Council) and that the views expressed are the authors' and not the Council's.
- Format: CSV, encoding latin-1, 34 columns, 16,508 data rows. Columns used here: Station ID, Sample Date
  (mm/dd/yyyy), Sample Depth (cm, ranges such as "0 to 4"), Wet Soil pH (pH units), Soil Specific Conductance
  (uS/cm), Bulk Density (g/cm3), Organic Matter (%), Latitude, Longitude. "Group" is empty in all rows.
- Coverage (computed on download): 3,171 station IDs, 392 CRMS site codes, 2006-03-23 to 2023-03-02, latitude 29.04 to
  30.41, longitude -93.83 to -89.13; every station has coordinates. Rows with a value: Soil Salinity 7,495; Bulk
  Density 15,152; Organic Matter 15,133.
- Licence: no licence text found for this dataset. The CRMS disclaimer page
  (https://www.lacoast.gov/crms/legal.aspx?type=disclaimer) says "Information presented on this website is considered
  public information (unless otherwise noted) and may be distributed or copied. Use of appropriate byline/photo/image
  credit is requested." That page's text refers to USGS data, so its applicability to CRMS is ASSUMED, not verified.
- Suggested citation (https://www.lacoast.gov/crms/legal.aspx?type=citation): "Coastal Protection and Restoration
  Authority (CPRA) of Louisiana. YYYY. Coastwide Reference Monitoring System-Wetlands Monitoring Data. Retrieved from
  Coastal Information Management System (CIMS) database."
- Known problems: "Soil Salinity (ppt)" is not labelled as porewater or soil-extract salinity in the header, and
  this was not resolved in the metadata checked. Units of the CSV columns are taken from the header only.
- Used by: validation/soil_layer_check.py (docs/SOIL_LAYER_CHECK_PLAN.md).
