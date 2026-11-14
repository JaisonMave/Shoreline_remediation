# F7: second-spill inventory (whole-spill hold-out)

Inventory 14 November 2026. Plan: `docs/F6_F7_PLAN.md`. URL log:
`results/f6_f7/url_checks.csv`. No modelling.

**Need for “usable”:** oiling per segment, treatment per segment, and outcome
over time, open, and hold-out of the whole spill (D5 / V4 F7).

**Result:** **no candidate is usable.** Several are **partial**. The system
should stay described as within-spill (Deepwater Horizon) validated until a
usable second spill exists.

## Summary

| Spill | Oiling | Treatment | Outcome over time | Licence / access | Size / what was saved | HTTP | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Exxon Valdez (1989) | Yes, historically; lingering-oil pits 2015 | Narrative (hot-water washing); no open per-segment STR table found | Monitoring and hydrocarbon DB exist | Public domain / no legal restriction stated on InPort 17283 | Not downloaded (portals, not a small table) | Portals 200 | **partial** |
| Cosco Busan (2007) | DIVER/ERMA holdings described | Not found as open GIS | Restoration, not shoreline recovery series | InPort 57310 | None | 200 | **not usable** |
| Refugio / Plains 2015 | ERMA SW incident location | InPort: data may be trustee-restricted | Not found | InPort 57720 | None | 200; NOAA incident URL 404 | **not usable** |
| Bouchard 120 (2003) | SCAT miles in a PDF | Cleanup discussed in the same PDF | End-of-cleanup site visits, not a time series table | DIVER admin-record PDF | 1.30 MB PDF saved | 200 | **partial** |
| M/V Selendang Ayu (2004) | NRDA plan quotes SCAT miles by habitat | 123 of 806 segments cleaned (narrative) | Not found as open table | FWS PDF | PDF **403** here | 403 | **not usable** (narrative only; file not obtained) |
| Hebei Spirit (2007) | Papers | Papers | Papers (e.g. rapid recovery article) | Journal pages | ScienceDirect **403**; MDPI **403** | 403 | **not usable** (full text/data not reached) |
| Prestige (2002) | CEDRE fact sheet | Fact sheet | Not found as open segment table | CEDRE HTML 200 | None | 200 | **not usable** |
| Wakashio (2020) | 5-site PAH snapshot (Mendeley record) | Not found | One date, 6 months later | CC BY 4.0 on Mendeley page | xlsx not obtained (HTML shell / S3 403) | 200 / 403 | **not usable** |
| Bahia Las Minas / Galeta (1986) | Oiled vs unoiled sites | No cleanup variable (planted vs natural seedlings only) | Multi-year mangrove files | CC0 vs “non-public” conflict | 7.0 MB mangrove files saved | 200 | **partial** |
| TROPICS (1984 experiment) | Experimental oiling | Oil vs dispersed vs reference | 40-year report (figures/tables) | US Gov report | 6.19 MB PDF saved | 200 | **partial** (n=3 sites, not a spill) |

## Per spill

### Exxon Valdez

Checked: EVOSTC https://evostc.state.ak.us/ (200); Gulf Watch Alaska
https://gulfwatchalaska.org/ (200); Gulf of Alaska Data Portal
https://search.dataone.org/portals/GOA (200); AOOS
https://portal.aoos.org/gulf-of-alaska.php (200); InPort hydrocarbon DB
https://www.fisheries.noaa.gov/inport/item/17283 (200, “no legal restrictions”);
NCCOS lingering-oil 2015 page (200); NOAA incident page (200); ERMA Alaska
(200, 8 024 B HTML). DataONE lingering-oil view URL 200 but did not yield a
file in this session.

Variables that exist in public descriptions: pit/site lingering oil, PAH
tissues/sediment/seawater (EVTHD), long-term monitoring. Treatment of 1989
(high-pressure hot water) is documented in NOAA narrative pages, not as a
joinable segment layer with those outcomes.

### Cosco Busan

InPort 57310 (200): DIVER case metadata; datasets from mixed producers. ERMA
Southwest (200). NOAA incident page (200). No SCAT treatment shapefile URL
found.

### Refugio / Plains 2015

InPort 57720 (200): incident location; access notes that data **may be
provisional and restricted to Trustees**. ERMA SW layer link on the record.
Guessed NOAA incident URL 404.

### Bouchard 120

Saved `data/external/bouchard_120/shoreline_injury_assessment.pdf` (SOURCE.md).
Search-indexed text: about 105 miles of shoreline with greater than trace oil;
SCAT used for maximum oiling; 2003 site visits after cleanup. Not a CSV of
method × segment × year.

### Selendang Ayu

FWS NRDA plan PDF 403 from this host. Search-indexed text (not the file): 86
miles classified; 123 of 806 segments warranted cleanup; methods included
manual removal, vegetation cutting, mechanical removal. Without the file and
without a table, verdict is not usable.

### Hebei Spirit, Prestige, Wakashio

CEDRE spill pages 200 (HTML fact sheets). Journal full texts 403. Wakashio
Mendeley landing 200; files not obtained (`data/external/wakashio/SOURCE.md`).

### Bahia Las Minas (Galeta)

Partial, already in the project. Files in `data/external/bahia_las_minas/`
(SOURCE.md). Outcome trajectories yes; treatment no.

### TROPICS

Partial experimental contrast. PDF in `data/external/tropics/` (SOURCE.md).
Three sites, not shoreline segments of an accidental spill.

## What was not reached

HTTP 000 (no response in 45 s): NCEI 0163814 ISO landing, CPRA home,
gulfofamerica.erma.noaa.gov ArcGIS, NCEI 9400033 ISO landing (the **data
folder** for Galeta did respond 200).

HTTP 403: NOAA IR PDF (curl), FWS Selendang PDF, ScienceDirect, MDPI, guessed
FWS DWH admin-record path, Mendeley S3 zip.

HTTP 404: guessed NOAA incident URLs for Refugio, Bouchard, Selendang; InPort
57299.

ERMA map homes all returned the same 8 024-byte HTML; no ArcGIS REST listing
for SCAT treatment was exposed without a login.

## Gate

F7 feasibility **passes as documentation**: every named candidate has a
verdict and a recorded HTTP status. **No usable whole-spill hold-out dataset
was found.** Do not claim transfer beyond Deepwater Horizon.
