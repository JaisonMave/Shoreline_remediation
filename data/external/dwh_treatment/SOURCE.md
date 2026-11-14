# DWH treatment-record search files (F6)

Checked 14 November 2026. Inventory only. These files are **not** a segment-level
treatment-method table.

## NOAA Technical Memorandum NOS OR&R 42

- **Title:** Deepwater Horizon Oil Spill: Salt Marsh Oiling Conditions, Treatment
  Testing, and Treatment History in Northern Barataria Bay, Louisiana (Interim
  Report October 2011)
- **Authors:** Zengel, S. and Michel, J.
- **Series / year:** NOAA Technical Memorandum NOS OR&R 42, April 2013
- **Landing page:** https://repository.library.noaa.gov/view/noaa/380
- **PDF URL:** https://repository.library.noaa.gov/view/noaa/380/noaa_380_DS1.pdf
- **Stated size:** 16.89 MB (library page); linearized PDF `/L 17713154` in the
  file header (web fetch of the PDF stream).
- **Licence on landing page:** CC0 1.0 Public Domain
- **Checksum on landing page:** urn:sha-512:f507933e82aacd26f2e86fee68d7fae8d92b6ff36cf45d36f90cf2e81ebcb45f7c444911ef3c14ba731ab6ebe85528deae5f48200d7905c74e8c99dd609820c2
- **Local copy:** not saved. curl and PowerShell from this host returned HTTP 403
  (406–439 byte blocks). Playwright download of the PDF aborted (`net::ERR_ABORTED`).
  The HTML landing page opened in the browser (HTTP 200). Use
  `scripts/download_orr42.ps1` from a machine that can open the NOAA IR in a
  browser.

## DIVER CWV-MarshResponseCleanupAreas (downloaded)

NCEI DIVER archive, Shoreline workplan folders. Public NOAA archive; NOAA/NCEI
"no warranty" wording; no licence identifier on the index pages.

Base: `https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/Shoreline/`

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| CWV_Feb2011_ArchivePackageContents.txt | 89248 | 141fb814edc24152ce11a4c805b2ef826ef60b503024ae01fa7907a59f086e08 |
| CWV_Spring2011_ArchivePackageContents.txt | 161912 | 866c5c09d8ce5d1dee37d13c48ffae1559a78588742b667d1947144622dd0a07 |
| CWV_Fall2011_ArchivePackageContents.txt | 205516 | e1729e2cd47d0e47bb5d130abc57445c8dc17d3e5175b4c406a4a491a1410ffe |
| CWV_Feb2011_FieldObservations.tar | 2754560 | fa0150aea17585ff94f3bded1dcc06fcadeb9214233babf4f44fb7101b4af604 |

Photographs tars (622 MB / 990 MB / 1.44 GB) and RelatedFiles tars were **not**
downloaded (over the 300 MB cap).

## Fields in February 2011 FieldObservations (described, not analysed)

Cover-plot CSV (59 data rows): `siteid` values B-06, B-07, C-10, C-11, D-12,
D-13, E-14, H-01, H-02, H-03, H-04, I-01, I-03, I-04 (14 named Bay Jimmy NRDA
plots). Columns include oilingextent, oilingheight, vegcovertotal, habitattype,
wateronmarsh. **No treatment-method, STR, cleanup, manual/mechanical, or
flushing column.**

Other CSVs in the tar: site-visit waypoints/lat-long, sample collection, leaf
fluorometry. Same conclusion.

This is plot monitoring inside a "Marsh Response Cleanup Areas" workplan, not a
SCAT-segment treatment GIS layer.
