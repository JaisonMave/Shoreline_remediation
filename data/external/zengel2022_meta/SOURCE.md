# Zengel et al. synthesis of wetland vegetation response to oiling (GRIIDC compiled dataset)

- File: `dataset_compiled_for_GRIIDC.xlsx` (sheets Metadata, Sources, Dataset), copied unchanged.
- Dataset: "Synthesis of wetland vegetation response to oiling" (Zengel, Mendelssohn, Graham, Fleeger, Johnson, Deis),
  GRIIDC, doi:10.7266/n7-cn03-z792, UDI R6.x813.000:0001 (GRIIDC dataset id 3632), published 2020-12-07 per the landing page.
- URL: https://data.griidc.org/data/R6.x813.000:0001
- Licence: CC0, from the JSON-LD `license` field on the GRIIDC landing page (visible wording not found; Terms &
  Conditions not fetched). The article itself is CC BY 4.0 per the NOAA repository record; a different object.
- Acquired 2026-11-12. How obtained: https://data.griidc.org/download/dataset/3632 returned a zip (116,378 bytes,
  SHA-256 9d3d5b3ac691951d2dc14eac2501e7ec911de7a61ae48cbe34b1c182e1cd4bba); the workbook was extracted and copied unchanged.
- SHA-256 of the xlsx: bb2b4891422805ffdf05018ea93af01de9d7ad7e3372c8f6f0f5466744d2b020.
- Link to the paper: the NOAA repository record (https://repository.library.noaa.gov/view/noaa/49055) for Zengel et al.
  2022, Ecol. Appl. 32(1):e02489, doi:10.1002/eap.2489, links this DOI as "Available dataset". UNCONFIRMED that this
  workbook is exactly the dataset used in the paper or equals the paper's supplement: the Wiley page and supplement
  returned a Cloudflare 403 challenge and were not bypassed.
- Known problems:
  - 1,158 data rows in sheet Dataset; no coordinates (site IDs are per source only).
  - Missing values are the string "NA", not blanks (for example JuncusCover missing in 904 of 1,158 rows).
  - No detection limits or censoring flags. Data compiled by the authors from GRIIDC, NRDA and published studies;
    original sources are in the Sources sheet (not checked beyond the columns listed in the inventory).
  - Units are those in the file's Metadata sheet; see docs/DATA_CATALOGUE.md notes. Not added to the variable dictionary.
