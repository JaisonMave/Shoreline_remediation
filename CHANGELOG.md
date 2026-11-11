# Changelog

All changes on branch `process-model-audit` relative to `main` (commit 4b0c118). Newest first.
Each entry gives what changed, why, where it lives, the result, and its status. Statuses follow
`docs/ROADMAP.md`: Completed means validated and documented, not just coded. Decisions are numbered as in
the decision register in `docs/ROADMAP.md`.

How to reproduce the analyses: `pip install -r requirements-analysis.txt`, then the commands listed per entry.
Raw SCAT shapefiles come from `scripts/download_scat.sh`; imagery is read on demand from Microsoft Planetary
Computer (no account needed).

---

## 2026-11-11 (session 2): proof-of-concept track

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
- D10: land/water classification fails on water-dominated and plume tiles; Landsat maps not clean (Jaison).
- One spill only; transfer shown within Louisiana, not to a new spill (D6).
- Cleanup method per shoreline segment unknown (P3).
- `seaborn` was imported by existing code but missing from `requirements.txt` (now in requirements-analysis.txt).
