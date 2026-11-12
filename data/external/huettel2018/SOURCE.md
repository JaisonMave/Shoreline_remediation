# Huettel et al. 2018: Pensacola Beach oxygen profiles and St. George Island reference cores

- Paper: Huettel M, Overholt WA, Kostka JE, Hagan C, Kaba J, Wells WB, Dudley S (2018) Degradation of Deepwater
  Horizon Oil Buried in a Florida Beach Influenced by Tidal Pumping. Mar. Pollut. Bull. 126:488-500,
  doi:10.1016/j.marpolbul.2017.10.061. The authors' page says the data sit under nine GRIIDC DOIs; only four were
  looked at, three copied here. Records R5.x278.000:0003, 0004 and 0005 return HTTP 404 at the GRIIDC data URL (checked 2026-11-12;
  no title, DOI or size available).
- Files copied unchanged (acquired 2026-11-12 from https://data.griidc.org/download/dataset/<id>, each zip holding one xlsx):
  1. `Beach oxygen profiles.xlsx` (42,832 bytes; SHA-256 695a5d4ba1dacdd8e55f0ea794df39040c01b492ad789cd2698f57bb9b0b8bca).
     "Oxygen profiles measured in Pensacola Beach dry sand sediments between 2010 and 2014", doi:10.7266/N7XW4HBZ,
     UDI R5.x278.000:0006, id 3500; zip 43,030 bytes, SHA-256 b7fc5b74f279e61cb2a31ef46473cb05081b080449b528d625ace3837dd3c49b.
  2. `Hydrocarbons and TOC St George reference cores.xlsx` (46,223 bytes; SHA-256 b7a11065535bd760bf3f2b2a4e1f3ca4797c0ebbdc232860f2520af191252140).
     "TPH, PAH and TOC data for uncontaminated beach sediment, St. George Island, Florida, June 6, 2010",
     doi:10.7266/N7BZ64J8, UDI R5.x278.000:0011, id 3510; zip 46,471 bytes, SHA-256 9b41410bf9079193170ce0ee92a442de56b54bab463d2715ce0762a1fbd56c22.
  3. `Alkanes.xlsx` (52,306 bytes; SHA-256 2692502d6e7b90cab1bf09a95399a0eadd404929d381fd43db3efcef73ef85c6).
     "Concentrations of saturated hydrocarbons measured during the standardized sediment-oil-agglomerate (sSOA)
     experiment from 2010-10-22 to 2013-12-16", doi:10.7266/n7-jjcn-y650, UDI R5.x278.000:0015; zip `dataset_4193.zip`
     52,476 bytes, SHA-256 c9b83d6447418e9607bc8e6aa50e240017f3bf22ac1008e12ececa22557ba25c. n-alkanes (C15 to C40 and
     sum) in mg/kg by day after start (0 to 1152; 11 distinct values) and depth (0, 10, 20, 30, 40, 50 cm); 51 data rows in
     sheet "Alkanes" (56 rows x 29 columns as read: title row, header on row 3, units row). Buried sediment-oil agglomerates
     (100 sSOAs from Pensacola Beach buried in the upper 50 cm of the beach, per the abstract), Pensacola Beach, Florida,
     2010-10-22 to 2013-12-16. Licence: not found (same as the other files). Not analysed.
- NOT copied (size): `Lab Tide Exp 1,2,3,4,s.xlsx`, 17,704,088 bytes, SHA-256
  9e89bf3ea012841a0e56d18fba4f2de68768526cb0c8defd829574f5e85386cc, from the GRIIDC record "Laboratory tide simulator
  measurements assessing the oil degradation in Pensacola Beach sands", doi:10.7266/N7765CV9, UDI R5.x278.000:0012,
  id 3511 (zip 17,704,288 bytes, SHA-256 d20a3e6dcbfff71cf32800f552d4c058ccca7cfdc026958ba801e76b6fdbbfc5). Laboratory
  oxygen and CO2 time series, not field chemistry.
- Licence: the GRIIDC record pages state none that was found; the footer links to Terms & Conditions
  (https://www.griidc.org/terms-and-conditions), not fetched. Licence: not found.
- Known problems:
  - Both workbooks are formatted for reading, not as tables: multi-row headers, units in a row below the header, and
    in the oxygen file side-by-side blocks (raw, "flagged data removed", averages). As read with pandas (header=None):
    oxygen sheet "Oxygen profiles Pensacola" 42 rows x 14 columns; "Controls" 64 rows x 13 columns.
  - Coordinates, detection limits and quality flags were not found in the portion read (first rows only).
  - The two files are a beach in Florida (Pensacola) and a Florida barrier island reference site, not Louisiana marsh.
  - Six of the nine GRIIDC DOIs for this study were not checked.
