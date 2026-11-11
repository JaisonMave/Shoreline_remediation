# Handoff: Shoreline Remediation Model (state on 11 November 2026)

## Who and what

Jaison is a soil scientist (PhD, soil science and agricultural chemistry) learning machine learning by
building a real tool. The tool recommends shoreline cleanup options after an oil spill and is meant to
improve on the FAST feasibility tool (fastshores.com) by adding data-based predictions of whether a
treatment works and how long recovery takes. Explain methods in plain language; he has applied statistics
but is new to ML.

## Where things are

- Repository: https://github.com/JaisonMave/Shoreline_remediation (public). `main` is at commit 4b0c118.
- Unpushed work: seven commits on a branch called `process-model-audit`. They exist only in the file
  `shoreline-improvements-files.zip` (46 changed or new files). To restore: clone `main`, unzip over it,
  run `python -m pytest tests` (33 tests should pass), commit on a branch. Do not push unless asked;
  pushing needs the Claude GitHub App installed on the repository.
- Design document: https://claude.ai/artifact/BidoqGEG4kFHQ6A4YPUzQi
- Literature review: https://claude.ai/artifact/4eR98SrUVEmUZ1Ygddh5cW
- Project docs: `claude/process-model-audit.md`, `claude/data-acquisition.md`, `claude/handoff.md`.
- Repository docs: `docs/PROCESS_MODEL_AUDIT.md`, `docs/RANKING_FIXES.md`,
  `docs/EXPERT_SCORING_PROTOCOL.md`, `docs/DATA_ACQUISITION.md`.

## What has been done

| Area | State |
| --- | --- |
| Process model (`shoreline_transport.py`) | Mass-balance bug fixed. Still ignores oil thickness, penetration, season and sensitivity, and treats treatment harm as negligible. Rate constants are assumed. |
| Treatment ranking | No placeholder scores; all five SCAT sanity checks pass; top choice matches a documented method in 3 of 5 historical cases. Not independent tests. Labels are still rule-generated. |
| Marsh recovery model (`marsh_recovery_model.py`) | Fitted to 63 published marsh cases from NOAA's "Oil Spills in Marshes". Does not beat a no-predictor baseline out of sample, with or without season, latitude and wetland type. Do not use it to rank treatments. |
| Expert scoring | Blind sheet of 30 scenarios, ICC agreement statistic and protocol are ready. No scores collected yet. |
| Satellite recovery (`recovery_timeseries.py`, `scripts/gee_export_ndvi.py`) | Built and tested on simulated data only. Never run on real imagery. |
| Event study (`event_study.py`) | Built, tested on simulated panels, and run on real marsh data for Hurricanes Isaac and Ida. The pre-event check rejected 3 of 4 comparisons; the clean one found no detectable loss of cover after Isaac. |
| Oil properties (`oil_library.py`, `data/oil_properties.csv`) | 1,460 oils from NOAA ADIOS. Not yet wired into the dashboard or `Scenario`. |
| Marsh field data (`data/external/crms/`) | 341 Louisiana CRMS sites, 2006-2025, from a third-party GitHub repository. No oil information. Not checked against the original CRMS export. |

## Main conclusion so far

The limiting factor is outcome data, not the type of model. No open-source model covers oil fate on the
shoreline together with treatment effects. Models trained on rule-generated or simulated labels only copy
those rules.

## Why work stopped

The session's network reached GitHub only. NOAA, PLOS, satellite archives and PyPI were blocked. Jaison is
turning on "Allow network egress" (Settings > Capabilities) and starting a new chat.

## Next steps, in order

1. Test which hosts are reachable. Install `rasterio`, `pystac-client`, `geopandas` and `statsmodels` if
   package installs work.
2. Download the Deepwater Horizon SCAT shoreline oiling layers (NCEI Accession 0163818,
   DOI 10.7289/v53t9ffx, https://accession.nodc.noaa.gov/0163818) or the NCEI DIVER archive.
3. Match the 341 CRMS sites to oiled and unoiled shoreline by distance, then run `event_study.py` for the
   2010 spill (first post-event survey 2010). Check how far each site is from the marsh edge first.
   Hurricane Gustav (2008) falls in the pre-period and Isaac (2012) in the post-period.
4. Get Landsat NDVI for oiled and reference marsh edges in northern Barataria Bay, through Microsoft
   Planetary Computer or Earth Search if Earth Engine is not available, and run
   `python -m validation.satellite_recovery`. Benchmark: Mo, Kearney and Riter (2017) found the major
   aboveground impact lasted about two years.
5. Extract treatment-group means from Zengel et al. 2015 (PLoS ONE 10(7):e0132324): untreated, manual and
   mechanical cleanup, with and without planting. Use them as priors for a treatment-effect model.
6. Wire `oil_library.py` into the dashboard so an oil is chosen by name.
7. Collect expert scores from three or more people (needs Jaison).

## Working rules agreed during the project

- Always compare against a simple baseline and report the result even when it is a null.
- Specify a model before validating it, and validate once. Hold out whole spills, not rows.
- Never code predictors from information chosen after the outcome was known.
- Label every assumed parameter as assumed, and every dataset with its source and how it was read.
- The NOAA marsh case table was read from the PDF by an automated reader; rows need checking.
