# Handoff: Shoreline Remediation Model (state on 12 November 2026)

## Who and what

Jaison is a soil scientist (PhD, soil science and agricultural chemistry) learning machine learning by
building a real tool. The tool recommends shoreline cleanup options after an oil spill and is meant to
improve on the FAST feasibility tool (fastshores.com) by adding data-based predictions of whether a
treatment works and how long recovery takes. Explain methods in plain language; he has applied statistics
but is new to ML.

## Where things are

- Repository: https://github.com/JaisonMave/Shoreline_remediation (public). `main` is at commit 4b0c118.
- Unpushed work: branch `process-model-audit`, thirty-one commits on top of `main`, held only in
  `Shoreline_remediation-full.zip` (remade 12 Nov 2026). The zip contains the whole repository including its
  `.git` folder, so unzipping it restores the branch and history directly; no need to clone first. Run
  `python -m pytest tests` (all tests should pass; install `requirements-analysis.txt` first). Do not push unless asked; pushing needs the Claude GitHub
  App installed on the repository. Raw SCAT shapefiles are not in the zip; `scripts/download_scat.sh` fetches them.
- Design document: https://claude.ai/artifact/BidoqGEG4kFHQ6A4YPUzQi
- Literature review: https://claude.ai/artifact/4eR98SrUVEmUZ1Ygddh5cW
- Project docs: `claude/process-model-audit.md`, `claude/data-acquisition.md`, `claude/handoff.md`,
  `claude/findings-2026-11-11.md`, `claude/roadmap.md`, `claude/changelog.md`, `claude/review-notes.md`,
  `claude/data-catalogue.md`, `claude/variable-dictionary.md`, `claude/p5-worked-example.md`.
- Demo: `streamlit run src/shoreline_remediation/dashboard.py` (first tab "Site evidence (real data)");
  model card `models/p5_edge_loss_v1.json`; rebuild with `python scripts/build_p5_demo.py`.
- Data: `docs/DATA_CATALOGUE.md` and `docs/VARIABLE_DICTIONARY.md` (rebuild with `python scripts/build_catalogue.py`).
- Review notes: `docs/REVIEW_NOTES.md` (open concerns). Missing soil/sediment chemistry: `data/meta/planned_variables.csv`.
- Change log: `CHANGELOG.md` lists every improvement on the branch (why, files, rerun command, result, status).
- Repository docs: `docs/PROCESS_MODEL_AUDIT.md`, `docs/RANKING_FIXES.md`,
  `docs/EXPERT_SCORING_PROTOCOL.md`, `docs/DATA_ACQUISITION.md`, `docs/FINDINGS_2026-11-11.md`,
  `docs/ROADMAP.md` (milestones and decision register), `docs/NAIP_EDGE_LOSS_PLAN.md`, `docs/P1_PRESPILL_CHECK_PLAN.md`,
  `docs/P2_BASIN_HOLDOUT_PLAN.md`, `docs/P3_TREATMENT_PLAN.md`, `docs/P5_DEMO_PLAN.md`, `docs/P5_WORKED_EXAMPLE.md`, `docs/P6_POC_REPORT.md`.
- The earlier seven-commit history was not in the previous zip, so it was restored as one commit.
  Network egress now works for NOAA, PLOS, Planetary Computer, Earth Search and PyPI (FTP is blocked).

## In progress when the session was paused (12 Nov 2026, afternoon): read this first

Jaison set usage limits (stop and hand off at 90% of the top-model allowance or 95% overall). Claude cannot
see the usage meter, so this section is kept current at every checkpoint.

Plan for the new work: `docs/SCENARIO_PROGRAMME_PLAN.md` (committed before any analysis). Direction from
Jaison: Phase A compare treatments including untested ones from literature; Phase B long-term forecast
(months to years) at a new place; Phase C mangroves, not beaches.

State of the three jobs (updated at each checkpoint):

| Job | State |
| --- | --- |
| A1 vegetation recovery curve | Done, checked, committed. Suggestive only (FINDINGS 14). |
| A2 scenario composer + check C1 | Done, checked, committed. C1 passes; single-cell option ranges overlap (FINDINGS 15). Not in the dashboard. |
| Phase C mangrove inventory | Done, committed (`docs/MANGROVE_INVENTORY.md`, FINDINGS 16). Web items partly unchecked. |
| A3 literature evidence for untested treatments | Done, committed (`data/knowledge/`, FINDINGS 17). First pass: most primary papers not opened. Elicited ranges set by the plan's rule, all Proposed; no untested option is distinguishable from natural recovery. |

Next steps: (1) move the treatment conditions from the evidence notes into the rule screening and re-check key numbers against primary papers; (2) plan and
build option-difference and block-level outputs in the composer; (3) put the composer in the dashboard;
(4) Galeta mangrove natural-recovery description; (5) Jaison's decisions on D14-D21.

## Session of 12 November 2026 (read this first)

1. **P1 against the literature (FINDINGS 11).** Challenger et al. 2021 and Turner et al. 2016 do not
   contradict P1 on whether heavy oiling raised erosion; they disagree on duration (1 to 2.5 years). P1's
   0.85 m/yr is an average over 2010-2015. "For at least seven years" is withdrawn. Full texts were not
   readable; `docs/LITERATURE_TO_DOWNLOAD.md` lists what to get and what each would settle.
2. **Period-split check (FINDINGS 12): inconclusive.** 0.42 (0.07 to 0.76) in 2010-2015, 0.28 (-0.27 to 0.84)
   in 2015-2017, fully adjusted. Quote the headline with the adjusted range 0.42 to 0.85 (D9a).
3. **Inventory (`docs/STAGE2_INVENTORY.md`).** In repo: Turner islands, Zengel meta-analysis (1,158 rows, 10
   studies, no coordinates), Chandeleur shoreline and fingerprinting, Huettel beach series, CRMS soil cores.
   Not committed, refetch with `scripts/download_diver.sh`: NOAA DIVER wetland chemistry (14,926 soil sample
   IDs, 202 stations, 2010-2013, censoring flags) and nearshore sediment. Not obtained: plant-oiling layers,
   beach treatment data.
4. **Soil layer check (FINDINGS 13): null.** SSURGO and SoilGrids do not beat the regional median in marsh.
   Do not use them as predictors (D21 proposed).
5. **Architecture (`docs/ARCHITECTURE_FOUNDATION.md`).** D14-D20 proposed, nothing built.

Waiting on Jaison: decisions D14-D21; his check of DIVER soil units (some soil rows are in mg/L) and
analytes; editing the P6 report and decks with the correction in `docs/P6_POC_REPORT.md`; the parked
reviews of P1-P5.

Next step (proposed): build the D14 schema with loaders for DIVER wetland chemistry and the Zengel table,
then two pre-specified analyses: vegetation recovery held out by study, and soil PAH decline with censoring.

Model routing used this session: small models for reachability and downloads, a mid model for loaders,
scripts and tests, the orchestrator for judgement and for checking every reported number against files.

## What has been done

| Area | State |
| --- | --- |
| Process model (`shoreline_transport.py`) | Mass-balance bug fixed. Still ignores oil thickness, penetration, season and sensitivity, and treats treatment harm as negligible. Rate constants are assumed. |
| Treatment ranking | No placeholder scores; all five SCAT sanity checks pass; top choice matches a documented method in 3 of 5 historical cases. Not independent tests. Labels are still rule-generated. |
| Marsh recovery model (`marsh_recovery_model.py`) | Fitted to 63 published marsh cases from NOAA's "Oil Spills in Marshes". Does not beat a no-predictor baseline out of sample, with or without season, latitude and wetland type. Do not use it to rank treatments. |
| Expert scoring | Blind sheet of 30 scenarios, ICC agreement statistic and protocol are ready. No scores collected yet. |
| Satellite recovery (`recovery_timeseries.py`, `scripts/landsat_ndvi.py`) | Run once on real Landsat (1,044 scenes, 2006-2016) for 34 heavily oiled vs 4 reference segments in northern Barataria Bay. No detectable drop (+0.025, interval -0.057 to 0.113); placebo check failed. Does not reproduce Mo et al. (2017). |
| Event study (`event_study.py`) | Run on Isaac and Ida (3 of 4 rejected by the pre-event check) and on the 2010 spill (`validation/oil_event_study.py`): 20 oiled vs 24 unoiled CRMS sites, no detectable effect. Most CRMS plots are hundreds of metres from the oiled edge, so they cannot see the spill. |
| SCAT oiling (`scripts/download_scat.sh`, `data/external/scat_dwh/`) | NCEI 0163818 Louisiana layers downloaded (max oiling, and all surveys including No Oil Observed). CRMS sites matched by distance. |
| Treatment effects (`treatment_effects.py`, `data/external/zengel2015/`) | Zengel et al. 2015 S1 Table loaded. Manual vs none: +34 points vegetation cover at year 2 (19 to 49); mechanical: +5 (-12 to 22); planting (randomized): +69 points Spartina. One site; observational except planting. Priors only. |
| Marsh-edge loss (`validation/naip_edge_loss.py`, plan `docs/NAIP_EDGE_LOSS_PLAN.md`) | NAIP 2010-2017, 4,779 salt-marsh edge cells in Barataria Bay. Heavily oiled edge lost 1.0 m/yr more than clean edge in the same 2 km block (90% interval 0.58 to 1.43), rising with oiling class. P1 Landsat check (1999-2015): part of that predates the spill and is explained by wave exposure; revised headline 0.85 m/yr (0.49 to 1.22), 0.62 to 0.85 across exposure adjustments. See FINDINGS section 7. |
| Basin hold-out (`validation/p2_basin_holdout.py`, plan `docs/P2_BASIN_HOLDOUT_PLAN.md`) | Louisiana edge cells in 4 basins; birdfoot, eastern Breton and south-west Barataria excluded (land/water rule fails in plume/open-water tiles). Held out Barataria and western Breton: model beats the no-predictor baseline (pooled 8-10% lower error), 90% intervals cover 89%; oiling class adds no cell-level accuracy over exposure; heavy uplift 0.34-0.83 m/yr depending on training basins. |
| Treatment and erosion (`validation/p3_treatment_erosion.py`, plan `docs/P3_TREATMENT_PLAN.md`) | Zengel et al. 2022 GRIIDC plot data: vs untreated in 2010-2012, manual -0.63 m/yr, mechanical +0.28 (n.s.), planting -1.47; oiling +1.88 vs reference, fading after 2012. Priors in `treatment_effects.erosion_prior()`. NAIP ranks like field data but reads 1.2 m/yr low. Segment-level cleanup records: none public. |
| Oil properties (`oil_library.py`, `data/oil_properties.csv`) | 1,460 oils from NOAA ADIOS. Dashboard chooses an oil by name (spill oils only by default) and sets the category from measured properties. |
| Demo (P5: `site_evidence.py`, `site_view.py`, plan `docs/P5_DEMO_PLAN.md`) | Map, site picker, expected edge loss with 90% interval, scope and extrapolation flags, rule screening beside field evidence per option. Worked example at Bay Jimmy: 1.42 m/yr (-1.74 to 4.30), observed 1.54. Runs from a clean install. |
| Marsh field data (`data/external/crms/`) | 341 Louisiana CRMS sites, 2006-2025, from a third-party GitHub repository. No oil information. Not checked against the original CRMS export. |

## Main conclusion so far

The limiting factor is outcome data, not the type of model. No open-source model covers oil fate on the
shoreline together with treatment effects. Models trained on rule-generated or simulated labels only copy
those rules.

## Next steps, in order (updated 11 Nov 2026; steps 1-6 of the earlier list are done, see FINDINGS)

1. Done: NAIP marsh-edge loss (see FINDINGS section 6).
2. Done (P1, pending Jaison's review): pre-spill Landsat check and finer exposure; see FINDINGS section 7.
   Proof-of-concept track and decisions D1-D13 are in docs/ROADMAP.md; every change is in CHANGELOG.md.
   P2 done (pending review): leave-one-basin-out within Louisiana; partly transfers (FINDINGS section 8).
   P3 done (pending review): no public segment-level cleanup records; Zengel 2022 plot data give treatment
   effects on erosion, now tool priors (FINDINGS section 9). Next: P4 (data documentation), P5 (demo), P6.
   Backlog D10: robust land/water classifier.
3. P4 done (pending review): `docs/DATA_CATALOGUE.md`, `docs/VARIABLE_DICTIONARY.md` (generated by
   `scripts/build_catalogue.py`, checked by tests). Open concerns: `docs/REVIEW_NOTES.md`.
4. P5 done (pending Jaison's test as a user): Site evidence view with the deployed edge-loss model
   (held-out error 1.30 vs 1.42 m/yr baseline), 90% intervals, scope flags, and rule screening beside Zengel
   evidence per option (FINDINGS section 10). D13 (treatment mapping) proposed, needs Jaison.
   Soil and sediment chemistry flagged as missing, with priorities (REVIEW_NOTES E0).
5. P6 done (pending Jaison's review): report https://claude.ai/artifact/LKTwAyFJpAGwSGvYBqHYHr and slides
   https://claude.ai/artifact/PdsU2ppjW3TmsTcVrVNMGc; walkthrough deck
   https://claude.ai/artifact/C2YHim6F847wJDt2BRTfXd; sources of every number in `docs/P6_POC_REPORT.md`.
   D13 approved. Jaison parked his reviews of P1-P5, the variable check and the dashboard test (11 Nov).
   Expert scores (M6) remain on hold until Jaison has collaborators.
   Candidate before P6: segment- or block-level predictions, which would be much tighter than single cells
   (REVIEW_NOTES C7; needs its own plan).

## Earlier next steps (11 Nov 2026, first session)

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
- Zengel 2015 values were taken from the authors' Excel supplement, not read from figures or PDF.
