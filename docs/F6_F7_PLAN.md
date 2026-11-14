# F6/F7 plan: treatment-record and second-spill data feasibility

Written 14 November 2026, before any URL check, listing or download. Inventory only: no modelling,
no join to edge cells, no treatment-effect comparison.

## Question

1. **F6.** Does a public, machine-readable, segment-level Deepwater Horizon shoreline treatment record
   exist (method per SCAT segment or equivalent), or are treated stretches available only as map figures
   in NOAA Technical Memorandum OR&R 42?
2. **F7.** Does any other spill have open data with **all three** of: oiling per segment, treatment per
   segment, and outcome over time, sufficient for a whole-spill hold-out (V4 F7 / D5)?

## Data (to be checked; none assumed present)

- NOAA TM OR&R 42 (Zengel and Michel, year and exact title to be verified).
- NOAA ERMA Gulf layers; DIVER “Shoreline Treatment” / SCAT treatment recommendations (STR);
  GRIIDC; Louisiana CPRA; Unified Command reports; NOAA OR&R SCAT ArcGIS REST.
- NCEI DIVER archive listing: https://www.ncei.noaa.gov/data/deepwater-horizon-diver-system/archive/
- Candidate second spills listed in `docs/V4_PROGRAMME_PLAN.md` F7 and this task brief:
  Exxon Valdez, Cosco Busan, Refugio/Plains 2015, Bouchard 120, M/V Selendang Ayu,
  Hebei Spirit, Prestige, Wakashio, Bahia Las Minas (Galeta; partly held), TROPICS.

Local context already in the repo (not re-analysed): `docs/P3_TREATMENT_PLAN.md`,
`docs/FINDINGS_2026-11-11.md` section 9, `docs/STAGE2_INVENTORY.md`, `docs/MANGROVE_INVENTORY.md`,
`docs/DATA_ACQUISITION.md`, `data/meta/catalogue.csv`. Galeta files if present under `data/`.

## Method

1. HEAD/GET each candidate URL; record HTTP status, final URL, bytes if given, and date.
   Failures are recorded, not invented.
2. For DIVER archive listing: list folder names and sizes from the HTML index.
3. If a machine-readable treatment-per-segment file exists and is under 300 MB, download to
   `data/external/dwh_treatment/` with `SOURCE.md` (URL, date, licence, checksum) and list fields.
   Do not analyse.
4. If only map figures exist: record figure pages and write a digitisation protocol.
5. For F7: same URL check; download only open datasets under 200 MB that are usable or partial
   to `data/external/<spill>/` with `SOURCE.md`. Larger: URL plus a download script under `scripts/`;
   do not run if over 200 MB.
6. Write `docs/F6_TREATMENT_RECORDS.md`, `docs/F7_SECOND_SPILL_INVENTORY.md`,
   `results/f6_f7/url_checks.csv`.

## Baseline

The P3 search conclusion (11 Nov 2026): no public segment-level DWH cleanup table; TM OR&R 42
treated stretches as map figures only; Zengel 2022 GRIIDC is plot-level, not segment-level.

## Gate (feasibility, not a model)

- **F6 pass:** either (a) a machine-readable treatment-per-segment source is located and documented,
  or (b) it is shown not to exist in the public sources checked, with figure pages and a
  digitisation protocol recorded.
- **F7 pass:** every named candidate has a verdict usable / partial / not usable, with HTTP status
  for each URL checked. “Usable” requires oiling, treatment and outcome over time at segment or
  equivalent unit, open licence, and a path to files.
- Fail only if a source is claimed without a recorded URL check, or a dataset/URL is fabricated.

## Pass/fail rule for this activity

The activity passes if the three named output files exist, every row in `url_checks.csv` has a
recorded status (including failures), and no analysis of treatment effects is run.
