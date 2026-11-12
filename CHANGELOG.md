# Changelog

All changes on branch `process-model-audit` relative to `main` (commit 4b0c118). Newest first.
Each entry gives what changed, why, where it lives, the result, and its status. Statuses follow
`docs/ROADMAP.md`: Completed means validated and documented, not just coded. Decisions are numbered as in
the decision register in `docs/ROADMAP.md`.

How to reproduce the analyses: `pip install -r requirements-analysis.txt`, then the commands listed per entry.
Raw SCAT shapefiles come from `scripts/download_scat.sh`; imagery is read on demand from Microsoft Planetary
Computer (no account needed).

---

## 2026-11-12 (session 3): literature reconciliation and data inventory

### Scenario programme (Phase A1, A2; Phase C step 1)
- **Plan:** `docs/SCENARIO_PROGRAMME_PLAN.md`, committed before any analysis.
- **A1:** `validation/veg_recovery_curve.py`, tests, `results/veg_recovery/`, `models/veg_recovery_v1.json`.
  Result: suggestive only (held-out error 0.417 vs 0.450 baseline, interval of the difference includes zero;
  worse than baseline for heavily oiled sites). FINDINGS 14. Rerun: `python -m validation.veg_recovery_curve`.
- **A2:** `src/shoreline_remediation/scenario_composer.py`, `validation/scenario_composer_check.py`, tests,
  `results/scenario_composer/`. Check C1 passes (94% and 81% coverage); single-cell option ranges all overlap.
  FINDINGS 15. Not in the dashboard.
- **Phase C:** `docs/MANGROVE_INVENTORY.md`. FINDINGS 16.
- **A3:** `data/knowledge/` (evidence table, notes, elicited ranges; catalogued). No untested treatment is
  distinguishable from natural recovery; conditions for use recorded. FINDINGS 17.
- **Status:** Under validation.

### Phase A4: option differences, block-level composer, conditions, dashboard section
- **Plan:** A4 section of `docs/SCENARIO_PROGRAMME_PLAN.md` (committed first; amends the A2 labelling rule).
- **What:** paired-difference flags and `compose_block()` in `scenario_composer.py`;
  `validation/scenario_block_check.py`; "Compare options" in `site_view.py`;
  `data/knowledge/treatment_conditions.csv`; tests (149 pass).
- **Result:** check C2 passes (88% and 93% block coverage) but block ranges are only 17% narrower than cell
  ranges. Planting after mechanical cleanup is distinguished from natural recovery (-2.5 ha, -4.3 to -0.8, in
  the worked block by year 8); manual and mechanical are not; untested options cannot be ranked. FINDINGS 18.
- **Rerun:** `python -m validation.scenario_block_check`; `streamlit run src/shoreline_remediation/dashboard.py`.
- **Status:** Under validation (awaiting Jaison's test as a user).

### Stage 3b: foundation architecture (design only)
- **What:** `docs/ARCHITECTURE_FOUNDATION.md`: common data schema, model interface, knowledge tables,
  orchestration, process-informed layer in gated steps, offshore models as an upstream provider, model
  registry. Decisions D14 to D20, all **Proposed**; nothing built.
- **Status:** Not started (design awaiting Jaison's decisions).

### Stage 3a: soil layer check (SSURGO and SoilGrids against CRMS cores)
- **Why:** can soil maps stand in for measurements at sites without cores?
- **What:** plan committed first (`docs/SOIL_LAYER_CHECK_PLAN.md`); `scripts/fetch_soil_layers.py`,
  `validation/soil_layer_check.py`, tests; CRMS soil cores in `data/external/crms_soil/`, retrieved map values
  cached in `data/external/soil_layers/`.
- **Result:** null. Neither map beats the regional median for bulk density, organic matter or pH at 392
  sites; SoilGrids bulk density is 1.06 g/cm3 too high. SSURGO salinity ranks sites moderately (0.42).
  FINDINGS section 13.
- **Rerun:** `python -m validation.soil_layer_check` (uses the cache; `scripts/fetch_soil_layers.py` refetches).
- **Status:** Under validation (awaiting Jaison's review).

### Period-split check (did the heavy-oiling excess fade?)
- **What:** `validation/period_split_check.py`, tests, `results/period_split/`; plan committed first.
- **Result:** inconclusive. Heavy minus clean 0.42 (0.07 to 0.76) in 2010-2015 and 0.28 (-0.27 to 0.84) in
  2015-2017; Light shore shows an unexpected +0.78 in 2015-2017. Adjusted range for the headline is now 0.42
  to 0.85. Part B (Landsat split) not run and not recommended (sensor gap in 2012). FINDINGS section 12.
- **Rerun:** `python -m validation.period_split_check`.
- **Status:** Under validation.

### Stage 3 downloads
- GRIIDC Landsat marsh cover fetched (1.11 GB, one 2009-09-02 scene, not committed; catalogue entry updated).
  Huettel 2018: buried-oil n-alkane series found (GRIIDC R5.x278.000:0015) and committed; records 0003-0005
  return 404.

### Stage 2: dataset inventory (no modelling)
- **Why:** find chemistry, vegetation and erosion data beyond the proof of concept, and say what is reachable.
- **What:** ten sources checked (`docs/STAGE2_INVENTORY.md`). Five small datasets committed under
  `data/external/` with `SOURCE.md` (Turner 2016 islands, Zengel 2022 meta-analysis, Chandeleur shoreline and
  fingerprinting, Huettel 2018); ten catalogue entries added (`scripts/build_catalogue.py`);
  `scripts/download_diver.sh` (not run) for the 630 MB NOAA DIVER files, which are git-ignored;
  DIVER pointers added to 7 rows of `data/meta/planned_variables.csv`.
- **Result:** DIVER wetland files hold 14,926 soil sample IDs at 202 stations, 2010-2013, with censoring
  flags (counts verified from the files); nearshore files 1,870 sediment sample IDs. These do not match the
  counts in the brief (1,894; 1,731). Not obtained: plant-oiling layers, Michel 2017 data (none found),
  Landsat marsh cover (1.11 GB, reachable, not downloaded), six of nine Huettel records.
- **Also:** `docs/LITERATURE_TO_DOWNLOAD.md` (papers not reachable); `docs/PERIOD_SPLIT_CHECK_PLAN.md`
  (proposed, not run); dashboard uplift caption now says "average over 2010-2015"; correction note for the P6
  artifacts in `docs/P6_POC_REPORT.md` (artifacts themselves not edited).
- **Rerun:** `python scripts/build_catalogue.py`; `python -m pytest tests` (108 pass).
- **Status:** Under validation (awaiting Jaison's review of the inventory).

### Stage 1: P1 headline against Challenger et al. 2021 and Turner et al. 2016
- **Why:** Challenger et al. report extra loss on heavily oiled shore only in the first year; P1 reports
  0.85 m/yr averaged over 2010-2015.
- **What:** comparison of periods, sites, oiling definitions and methods (`docs/FINDINGS_2026-11-11.md`
  section 11; extraction in `docs/STAGE1_PAPER_EXTRACTION.md`; `docs/REVIEW_NOTES.md` C0). No analysis rerun.
- **Result:** not contradictory; P1 gets a note, not a revision. 0.85 m/yr is a period average, compatible with
  a 1 to 2.5 year effect; "for at least seven years" (section 6) withdrawn. Our NAIP data show no fade
  (implied 2015-2017 excess about 1.04 m/yr), so residual exposure confounding remains possible.
- **Not done:** full texts not reachable (abstracts, Turner's data file and Zengel 2022 Table 1 only).
  Period-split check proposed, not run. Dashboard and P6 wording not changed (needs Jaison).
- **Status:** Under validation (awaiting Jaison's review).

## 2026-11-11 (session 2): proof-of-concept track

### P6: walkthrough deck for non-specialists
- 69 slides in six parts, with aerial photos of the worked-example edge (2010 vs 2015, true colour and
  near-infrared), a study-area map, step charts and 13 dashboard screenshots. Link in `docs/P6_POC_REPORT.md`;
  generators in `scripts/walkthrough_deck/`. Dashboard caption updated: D13 approved.

### P6: proof-of-concept report and slides
- **Why:** the deliverable for project leads (roadmap P6).
- **What:** an editable report (claim, what the tool does, evidence with two charts, failures, limits, a phased
  path to scale with gates, method, sources) and a 12-slide deck with speaker notes. Links and the source of
  every number: `docs/P6_POC_REPORT.md`.
- **Checked:** numbers against results files; citations against publishers' records (one wrong title corrected).
- **Status:** Under validation (awaiting Jaison's review). D13 approved by Jaison.

### Corrected: rounding of P3 results
- Several P3 values had been rounded up in the docs (e.g. 1.8849 reported as 1.89, -0.6347 as -0.64). Corrected in
  FINDINGS section 9, HANDOFF and here from `results/p3_treatment/A_prespill_adjusted.csv`. No analysis changed.

### P5: demo dashboard ("Site evidence (real data)" view)
- **Why:** leads need to see the tool working on a real site, with intervals and scope flags (roadmap P5; D9, D11).
- **What:** a new first tab: map of Louisiana salt-marsh edge cells; site picker (worked example, any edge cell,
  or a new site typed in); expected edge loss with a 90% interval and the heavy-oiling uplift as a separate range;
  out-of-scope and extrapolation flags with reasons; rule screening for the site beside field evidence per option
  (Zengel 2022 erosion, years 0-2 and 2-8; Zengel 2015 vegetation cover). The old view is now the second tab,
  labelled as rules and synthetic data; its model tab is relabelled "Method test (synthetic data)". The oil search
  offers spill oils only by default.
- **Files:** `docs/P5_DEMO_PLAN.md` (committed before the build), `scripts/build_p5_demo.py`,
  `models/p5_edge_loss_v1.json` (model card with coefficients, interval, training ranges and checksums),
  `data/demo/p5_sites.csv`, `docs/P5_WORKED_EXAMPLE.md`, `src/shoreline_remediation/site_evidence.py` (logic),
  `src/shoreline_remediation/site_view.py` (layout), `dashboard.py`, `oil_library.py` (`SPILL_OIL_TYPES`),
  `tests/test_p5_demo.py` (12 checks incl. Streamlit AppTest), `tests/test_oil_library.py`.
- **Run:** `python scripts/build_p5_demo.py` after any change to `data/external/p2`; then
  `streamlit run src/shoreline_remediation/dashboard.py`.
- **Result:** held-out error 1.30 vs 1.42 m/yr for the no-predictor baseline; worked example 1.42 m/yr (-1.74 to
  4.30), observed 1.54. See FINDINGS section 10.
- **Fixed on the way:** `openpyxl` added to `requirements.txt` (clean-install check failed without it);
  `streamlit>=1.67` (map colours and the `width` argument; `use_container_width` is deprecated); hero title was
  invisible (dark text on the dark banner).
- **Status:** Under validation (awaiting Jaison's test as a user). D13 (treatment mapping) proposed.

### Flagged: soil and sediment chemistry not in the PoC
- **Why:** Jaison asked for the missing soil and sediment chemistry to be flagged with comments.
- **What:** `data/meta/planned_variables.csv` (15 variables: why each matters, status absent/partial, open-source
  candidates, comments), rendered at the end of `docs/VARIABLE_DICTIONARY.md`; soil shear strength (`SHST_KPA`,
  Zengel 2022) added to the dictionary; REVIEW_NOTES E0 gives the reasoning and priorities.
- **Status:** Completed as documentation; the variables themselves are future work.

### P4: data catalogue and variable dictionary
- **Why:** every input to the demo must be traceable to source, date and method (roadmap P4).
- **What:** 18 datasets and 49 files catalogued with role (external, derived, synthetic, reference,
  instrument), source, licence, date, how obtained and read, and SHA-256; 40 variables defined with unit,
  type, valid range or allowed values, missing-value rule, derivation and module.
- **Files:** `scripts/build_catalogue.py`, `data/meta/catalogue.csv`, `data/meta/variable_dictionary.csv`,
  `docs/DATA_CATALOGUE.md`, `docs/VARIABLE_DICTIONARY.md`, `tests/test_data_catalogue.py` (42 checks).
  Also `scripts/run_p2_measurements.sh` and `scripts/landsat_split.sh`, which record how the P2 tables were
  built (previously only in a scratch folder), and `docs/REVIEW_NOTES.md` (open scientific concerns).
- **Run:** `python scripts/build_catalogue.py` after any data change; `pytest tests/test_data_catalogue.py`.
- **Found:** the oil table includes non-oils (an anti-knock additive at API -37.2); noted for P5.
- **Status:** Under validation (awaiting Jaison's check of definitions). D11 approved; D12 implemented.

### P3: cleanup treatment and marsh-edge erosion
- **Why:** the tool needs data-based treatment effects, not only rules (roadmap P3).
- **What:** searched SCAT, the NCEI DIVER archive, NOAA TM OR&R 42 and the DWH administrative record for
  segment-level cleanup records (none public in usable form); obtained Zengel et al. 2022 plot data from GRIIDC
  (CC0); pre-specified contrasts of erosion change by treatment; checked NAIP edge loss against field erosion.
- **Files:** `docs/P3_TREATMENT_PLAN.md`, `data/external/zengel2022/` (with `SOURCE.md`),
  `validation/p3_treatment_erosion.py`, `tests/test_p3_treatment_erosion.py`, `results/p3_treatment/`;
  `treatment_effects.erosion_effects()` and `erosion_prior()` added with tests.
- **Run:** `python -m validation.p3_treatment_erosion`
- **Result:** 2010-2012 vs untreated: manual -0.63 m/yr (-1.25 to -0.02), mechanical +0.28 (-0.17 to 0.73),
  mechanical + planting -1.47 (-2.06 to -0.88); oiling +1.88 vs reference, fading to +0.21 by 2012-2018.
  NAIP ranks plots like field data (Spearman 0.68) but reads 1.2 m/yr low.
- **Status:** Under validation (awaiting Jaison's review). D11 proposed.

### Changed: documentation and tracking
- `CHANGELOG.md` (this file) and `requirements-analysis.txt` added. `README.md` gains a section on the
  real-data evidence. D9 approved by Jaison.

### P2: leave-one-basin-out test of edge-loss prediction
- **Why:** leads will ask whether the model works on marsh it was not fitted to (D6).
- **What:** 39,320 salt-marsh edge cells along the oiled Louisiana coast, split into four basins by fixed
  geographic lines (D8). Models fitted on other basins predict the held-out basin: no-predictor baseline (M0),
  exposure + pre-spill trend (M1), M1 + oiling class (M2, primary), boosted trees (M3). 90% intervals from
  inner leave-one-basin-out residuals.
- **Files:** `docs/P2_BASIN_HOLDOUT_PLAN.md` (plan and 5 amendments, committed before the run),
  `scripts/build_edge_cells.py --louisiana`, `scripts/assign_basins.py`, `validation/p2_basin_holdout.py`,
  `tests/test_p2_basin_holdout.py`, `data/external/p2/`, `results/p2_basin_holdout/`.
- **Run:** `python -m validation.p2_basin_holdout data/external/p2`
- **Result:** "partly transfers". Beats the baseline in both tested basins (pooled error 1.35 vs 1.47 m/yr),
  90% intervals cover 89%; oiling class adds no cell-level accuracy over exposure; heavy-oiling uplift 0.34 to
  0.83 m/yr depending on training basins. Boosted trees worse than linear.
- **Found:** the 2010 land/water rule fails on tiles dominated by open water or river plume. Birdfoot delta,
  eastern Breton Sound and south-west Barataria excluded by a class-blind rule; backlog D10.
- **Status:** Under validation (awaiting Jaison's review).

### P1: pre-spill erosion check and finer exposure
- **Why:** the NAIP result had no pre-spill image; heavy oil landed on exposed shore, which erodes anyway.
- **What:** Landsat short-wave infrared unmixed per scene, three epochs (1998-2000, 2007-2009, 2014-2016);
  open water within 250 m and fetch from 2010 NAIP; four pre-specified checks.
- **Files:** `docs/P1_PRESPILL_CHECK_PLAN.md`, `scripts/exposure_metrics.py`, `scripts/landsat_edge_fraction.py`,
  `validation/p1_prespill_check.py`, `tests/test_p1_prespill_check.py`, `data/external/p1/`,
  `results/p1_prespill/`.
- **Run:** `python -m validation.p1_prespill_check data/external/p1`
- **Result:** "revised". Landsat confirms the post-spill gap (1.15 m/yr) but heavy-oil shore was already
  eroding 0.30 m/yr faster before the spill; headline 0.85 m/yr (0.49 to 1.22); 0.62 to 0.85 across exposure
  adjustments (exploratory). Robust to the P2 measurement problem (0.80 m/yr after filtering).
- **Status:** Under validation. Jaison: Landsat land-fraction maps not very clean; revisit (D10).

### Roadmap and decision register
- `docs/ROADMAP.md` (mirrored to the claude.ai project as `claude/roadmap.md`): module status, the six
  proof-of-concept milestones P1-P6, the full programme M1-M10, and decisions D1-D10.

## 2026-11-11 (session 1, continued): marsh-edge loss from NAIP

### NAIP marsh-edge loss, Barataria Bay
- **Why:** CRMS plots and 30 m Landsat pixels were too coarse for the 10-20 m oiled marsh band.
- **What:** 100 m edge cells from SCAT; NAIP 1 m imagery 2010-2017; land/water per tile (2010 Otsu rule;
  later years a classifier trained on 2010 interior pixels); edge loss vs oiling class within 2 km blocks.
- **Files:** `docs/NAIP_EDGE_LOSS_PLAN.md` (plan, then amendments), `scripts/build_edge_cells.py`,
  `scripts/naip_edge_extract.py`, `validation/naip_edge_loss.py`, `tests/test_naip_edge_loss.py`,
  `data/external/naip_edge/`, `results/naip_edge_loss/`.
- **Run:** `python -m validation.naip_edge_loss data/external/naip_edge`
- **Result:** heavy-oiled edge lost 1.00 m/yr more than clean edge (0.58 to 1.43), rising with oiling class
  (later revised by P1). NAIP 2013 dropped as too hazy (D2).
- **Status:** superseded as headline by P1.

## 2026-11-11 (session 1): first real Deepwater Horizon data

### SCAT shoreline oiling
- NCEI Accession 0163818 Louisiana layers (maximum oiling; all surveys including No Oil Observed).
  `scripts/download_scat.sh`. The NCEI download service failed; the HTTPS archive path works.

### 2010 event study at CRMS marsh stations
- `scripts/match_crms_scat.py`, `validation/oil_event_study.py`, `data/external/scat_dwh/`.
- Result: no detectable effect (20 oiled vs 24 unoiled sites); most stations sit hundreds of metres from the
  oiled edge, so they cannot see it. Status: Completed (null, documented).

### Landsat NDVI recovery, northern Barataria Bay
- `scripts/select_barataria_sites.py`, `scripts/landsat_ndvi.py`, `scripts/pool_ndvi_for_runner.py`,
  `data/external/landsat_barataria/`, `results/satellite/`.
- Result: no detectable drop; placebo check failed; does not reproduce Mo et al. (2017). Status: Completed
  (null, documented).

### Treatment effects from Zengel et al. (2015)
- `src/shoreline_remediation/treatment_effects.py`, `data/external/zengel2015/` (authors' Excel supplement),
  `tests/test_treatment_effects.py`.
- Result: manual cleanup +34 points vegetation cover at year 2 vs untreated (19 to 49); mechanical +5
  (-12 to 22); planting (randomized) +69 points Spartina. Priors only (D3). Status: Completed.

### Dashboard: oil chosen by name
- `src/shoreline_remediation/dashboard.py`, `oil_library.search_options()`, `tests/test_oil_library.py`.
- 1,460 NOAA ADIOS oils; category set from measured API gravity and pour point at the scenario temperature.
  Status: Completed (checked with Streamlit's app tester).

## Earlier (previous chat, restored from zip as commit 6647423)
- Process-model mass-balance fix; ranking fixes (no placeholder scores); marsh recovery model fitted to 63
  published cases (fails baseline, D4); expert scoring protocol; event-study and satellite-recovery code;
  NOAA ADIOS oil library; CRMS marsh data. Details: `docs/PROCESS_MODEL_AUDIT.md`, `docs/RANKING_FIXES.md`,
  `docs/HANDOFF.md`.

## Known open issues
- See `docs/REVIEW_NOTES.md` for the full list of open scientific and technical concerns.
- No soil or sediment chemistry in any model (REVIEW_NOTES E0; `data/meta/planned_variables.csv`).
- D10: land/water classification fails on water-dominated and plume tiles; Landsat maps not clean (Jaison).
- One spill only; transfer shown within Louisiana, not to a new spill (D6).
- Cleanup method per shoreline segment: no public machine-readable records (P3); treated stretches exist only
  as map figures in NOAA TM OR&R 42.
- NAIP absolute edge-loss rates read about 1.2 m/yr below field measurements (P3, analysis C).
- `seaborn` was imported by existing code but missing from `requirements.txt` (now in requirements-analysis.txt).
- `openpyxl` was missing from `requirements.txt` (fixed in P5).
