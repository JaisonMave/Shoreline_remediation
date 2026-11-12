# Chandeleur Islands salt marsh oil residue fingerprinting (categorical results)

- File committed: `GRIIDC Metadata - oil residue.csv` (1,013 bytes), copied unchanged.
- Dataset: "Oil residue analysis from Chandeleur Island salt marsh sediments, September 2016 to February 2017",
  GRIIDC, doi:10.7266/N7GQ6WCZ, UDI R4.x262.000:0042 (GRIIDC dataset id 4020). Authors: not checked.
- URL: https://data.griidc.org/data/R4.x262.000:0042
- Licence: CC0, from the JSON-LD `license` field on the landing page (visible wording not found; Terms & Conditions not fetched).
- Acquired 2026-11-12. How obtained: https://data.griidc.org/download/dataset/4020 returned a zip (9,812,560 bytes,
  SHA-256 806aacf01e88859d46ea2fc53e0d0b1d42415acf0f2bcd997df6e649e702f9c0). Only the CSV was copied.
- SHA-256 of the CSV: dbaa25b6fe584201cbbd42d7cf21f24e048bbf5629669c045ca4b8d87e5ffd4a.
- NOT committed: `GRIIDC Metadata - oil residue chromatograms.pdf`, 9,811,117 bytes, SHA-256
  161bc727b7aa797f577b37e75a515635a80d75c137c8aa0bbadd7d3d5da57775 (the landing page says the numeric compound-group
  results are in this PDF; not read).
- Known problems:
  - Categorical results only (Result column); no concentrations and no detection limits in the CSV.
  - 12 data rows; one has a blank Date and one has "NA" in several fields; kept as served.
  - Dates are text ("20 Sep. 2016"). Latitude/Longitude are text with a stray degree-symbol byte; the file is not valid
    UTF-8 (probably Windows-1252, not confirmed). Datum not stated (WGS84 ASSUMED).
