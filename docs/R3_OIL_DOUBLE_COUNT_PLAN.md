# R3: suspected double count of the oil effect in the scenario composer

Fixes `docs/V4_PROGRAMME_PLAN.md` section R3. Written and committed before any diagnostic number, model
coefficient or check result below is computed, per that section's rule ("choice fixed in the plan before
C1b/B1b are run", D27). Nothing in this plan is changed after seeing a result.

## 1. Why this is suspected

The composer baseline model (`models/p5_edge_loss_v1.json`, "P2 model M1: exposure + pre-spill trend, no
oiling term") is fitted on all 12,696 in-scope 2010-2015 NAIP edge cells across Terrebonne, Barataria and
Breton (`scripts/build_p5_demo.py::build()`), **including the 552 Heavy cells**. `scenario_composer.compose()`
then adds the full Zengel et al. (2022) untreated-plot oil excess (+1.88 m/yr years 1-2, +0.21 m/yr years
3-8) on top of that baseline for every Heavy cell. If M1 already absorbs part of the extra erosion on Heavy
cells (because they were in its own training data), the excess is added twice: once implicitly, through
whatever M1 learned from heavily oiled cells, and once explicitly, through the Zengel term. The existing
checks are consistent with this: B1 shows Heavy cells over-predicted by +0.534 m/yr (clean/NOO cells
+0.064) and C1's worked numbers show the heavy-cell composed mean (1.66 m/yr) about 0.6 m/yr above the
observed mean (1.09 m/yr) (`results/scenario_composer/summary.txt`, `results/scenario_composer/b1_horizon_coverage.csv`).
Neither check was designed to isolate this cause (both also carry the stated NAIP-vs-field 1.2 m/yr low
bias and uncleaned-vs-cleaned shoreline mismatch), so a dedicated diagnostic is needed before changing
anything.

## 2. Diagnostic (run once, no outcome comparison, pre-specified)

**Data:** the exact training panel for `p5-edge-loss-v1`: `pd.concat([validation.p2_basin_holdout.load_basin(p, b)
for b in BASINS])` over `data/external/p2/{terrebonne,barataria,breton}` (12,696 rows; this is the same
panel `scripts/build_p5_demo.py::build()` fits on). As a sanity check (reported, not gated) the script
refits M1 on this panel with `statsmodels` and confirms the coefficients match `models/p5_edge_loss_v1.json`
to within 1e-6 before computing anything else; if they do not match, the diagnostic is reported as
"model mismatch, numbers below do not describe the deployed model" rather than silently proceeding.

**Statistic:** in-sample residual = observed `rate` minus the fitted value, for every training cell, grouped
by `max_oiling` (NOO, Very_Light, Light, Moderate, Heavy). Reported: n cells, n distinct 2 km blocks
(`cell_2km`), and the mean residual, per class.

**Interval:** 90% cluster bootstrap by 2 km block. 2,000 resamples (ASSUMED count); each resample draws,
with replacement, as many 2 km blocks as appear in the class's own cells, keeping every cell of each drawn
block (so cells in the same block are resampled together, not independently) and recomputes the mean
residual for that class on the resampled rows. The interval is the 5th/95th percentile of the 2,000 class
means. If a resample happens to contain zero cells of a class (possible for the smaller classes), that
resample is dropped from that class's distribution only; the number dropped is reported.

**Confirmation rule (pre-specified):** the double count is confirmed if the Heavy class's bootstrap interval
lies entirely above zero (5th percentile > 0). NOO is reported for reference (expected near zero in-sample,
by construction of OLS, but not exactly zero within a subgroup).

**Output:** `results/scenario_composer/r3_diagnostic.csv`, columns `oiling_class, n_cells, n_blocks,
mean_residual, ci_lo90, ci_hi90, n_bootstrap_draws, n_dropped_resamples, confirmed_above_zero`. A short
paragraph is appended to a **new** summary file, `results/scenario_composer/summary_v4_r3.txt` (original
`summary.txt` is not touched).

**If the diagnostic does not confirm the double count** (Heavy interval touches or crosses zero): the fix
below is still built and the checks below are still run exactly as specified in section 3-4, because the
fix (a clean-edge baseline) is self-evidently correct whether or not the specific in-sample-residual
mechanism is the dominant cause (a biased baseline fitted partly on the thing you are about to add a
separate correction for is a defect either way). The final reading will say plainly that the diagnostic did
not confirm the mechanism, and that the fix's own before/after numbers (C1b/C2b/B1b bias) are therefore the
better evidence for whether double-counting was real and whether the fix helps.

## 3. Fix (primary, chosen in advance per D27: option 1, clean-edge baseline)

Refit M1 (same four terms: `water_1km_2010`, `water_250m_2010`, `log_fetch`, `pre_rate`, OLS, same fetch
offset 16 m) on **clean-edge cells only**: `max_oiling` in `{NOO, Very_Light}`, pooled across the three
basins (10,772 of the 12,696 cells). The Zengel oil excess is unchanged and still added only to Heavy cells.

**New model card** `models/p5_edge_loss_clean_v1.json`, same structure as `p5_edge_loss_v1.json`:
- `coefficients` / `standard_errors_unclustered`: from the clean-only OLS fit.
- `interval_offsets`: built the same way as v1 (5th/95th percentile of leave-one-basin-out residuals), with
  one change forced by the fix itself: for each basin held out, the training fold is **that basin's clean
  cells excluded, i.e. the other two basins' clean cells only**; the held-out basin's prediction and
  residual are still computed for **all of its cells, any oiling class** (so the residual pool mixes in the
  now-visible heavy-cell under-prediction, exactly as v1's own pool mixes in whatever bias it had — "built
  the same way").
- `training_cells` / `training_cells_by_basin` / `training_range` / `training_box`: recomputed over the
  clean-only training set (so extrapolation flags describe what this baseline actually saw).
- `training_files_sha256`: unchanged (same raw P2 files; only the row filter differs).
- `heavy_uplift_range_m_per_yr`, `heavy_uplift_source`, `p1_headline`, `measurement_note`: copied verbatim
  from v1 (ASSUMED unchanged: these describe the independent P2 oil-effect-transfer estimate and the NAIP
  measurement gap, neither of which depends on which cells M1 was fitted on).
- Two added fields (additive, nothing removed): `clean_training_filter` (states the kept/excluded classes)
  and `fixes` (pointer to this plan and to V4_PROGRAMME_PLAN.md R3).
- Built by **new script** `scripts/build_clean_baseline.py` (preferred over extending `build_p5_demo.py`,
  per the task). Also writes `data/demo/p5_sites_clean_lobo.csv` (new file; `data/demo/p5_sites.csv` is not
  touched): one row per in-scope cell with `cell, basin, cell_2km, max_oiling, observed_rate,
  lobo_pred_clean`, the per-basin leave-one-out prediction described above. This plays the same role for the
  clean baseline that the `lobo_pred` column plays for v1, and is what `scenario_composer.py` reads for its
  residual pools (section below) instead of changing `site_evidence.load_sites()`.

**`scenario_composer.py` change:** a module constant (`CLEAN_MODEL_PATH`, pointing at the new card) and a
cached loader; `_lobo_residuals()` and `_block_pools()` read `data/demo/p5_sites_clean_lobo.csv` instead of
`site_evidence.load_sites()`'s `lobo_pred`; the baseline prediction call passes the clean model explicitly
to `site_evidence.predict_edge_loss(values, model=<clean model dict>)`. `site_evidence.py`'s own default
model (used by the dashboard and `site_view.py`) is untouched, so every other caller keeps using
`p5_edge_loss_v1.json` until the step that updates the dashboard. `compose()`, `compose_block()` and
`forecast()` keep their existing signatures and the Zengel-excess logic is untouched; `pred_rate` overrides
(used by the checks) are unaffected because they bypass the baseline model entirely, as before.

## 4. Checks C1b, C2b, B1b (run once each; originals C1/C2/B1 are not rerun or overwritten)

Same data, same units and the same 80-97% coverage gate as the corresponding original check, with the
baseline swapped for the clean-edge model's own leave-one-basin-out predictions/residuals
(`data/demo/p5_sites_clean_lobo.csv`) in place of `results/p2_basin_holdout/predictions.csv`'s `M1` column
and `data/demo/p5_sites.csv`'s `lobo_pred`. Nothing else about the simulation (oil excess, draws, seed,
n_draws, horizon) changes.

- **C1b** (`validation/scenario_composer_check_b.py`): heavy cells of Barataria and Breton, coverage of the
  90% range of the 2010-2015 mean rate around the observed rate — identical definition to C1.
- **C2b** (`validation/scenario_block_check_b.py`): 2 km blocks (>= 5 valid cells) in the same two basins,
  coverage of the block mean — identical definition to C2.
- **B1b** (`validation/forecast_horizon_check_b.py`): Barataria cells/blocks with a 2010-2017 NAIP rate,
  coverage of the 2010-2017 mean rate, by oiling class — identical definition to B1.

**New bias gate (all three), pre-specified, in addition to the coverage gate:**
1. Heavy-cell mean bias (composed median minus observed, averaged over heavy cells) within +/-0.25 m/yr.
2. NOO-cell bias must not be worse than the **original** (v1-baseline) NOO bias for the same cells by more
   than 0.1 m/yr in absolute value, i.e. `abs(noo_bias_clean) - abs(noo_bias_original) <= 0.1`.

For B1b the original NOO bias is read directly from the existing `results/scenario_composer/b1_horizon_coverage.csv`
("cells, oiling NOO" row). C1 and C2 never tested NOO cells, so C1b and C2b additionally compute, purely for
this comparison and **using the unchanged original v1 model and pool** (no new fitting), the same bias
statistic for the same NOO cells/cell-composition the clean check uses:
- C1b: NOO cells of the two held-out basins, composed with the original baseline and original pool, same as
  the heavy-cell C1 computation but for NOO cells (C1 itself never ran this; it is new, derived from existing
  artefacts, and written only into `c1b_*` files).
- C2b: because a 2 km block mixes oiling classes, the heavy/NOO bias legs are computed at single-cell
  resolution from the cells inside the >= 5-cell blocks already used for the block coverage gate (ASSUMED
  scope: cells in smaller, unused blocks are not included), composed one cell at a time exactly as C2's own
  per-cell width computation already does, with both the clean and the original baseline/pool for comparison.

**Pass/fail is reported per gate** (coverage 80-97%, heavy bias, NOO-bias-not-worse), and an overall pass
only if all three hold; a failing gate is reported as a failure, not rounded away, with the numeric margin.

**Outputs:** `results/scenario_composer/{c1b_coverage.csv, c1b_cells.csv, c1b_noo_bias_cells.csv,
c2b_block_coverage.csv, c2b_blocks.csv, b1b_horizon_coverage.csv, b1b_cells.csv}`; each script appends its
paragraph to `results/scenario_composer/summary_v4_r3.txt` (new file; originals kept).

## 5. What is reported either way

The final report states, regardless of outcome: the diagnostic's Heavy and NOO mean residuals with their
90% intervals and whether the confirmation rule was met; the clean card's coefficients next to v1's;
coverage, heavy bias and NOO-bias-comparison for C1b/C2b/B1b next to the originals' coverage and bias in one
table; pass/fail per gate; and a plain reading that names anything that weakens the conclusion (in
particular: NAIP reads ~1.2 m/yr low against field plots and most heavily oiled shoreline was cleaned, both
already noted against C1/C2/B1 and unaffected by this fix; the clean-edge training set is about 15% of the
original and has far fewer Heavy-adjacent blocks, so its own interval is likely wider; and the small
leave-one-basin-out leak stated in the originals is unchanged here).

## 6. Scope

Only `scenario_composer.py`, the new model card/script, the new validation `_b` scripts, and focused tests in
`tests/test_scenario_composer.py` change behaviour. `site_evidence.py` defaults, `site_view.py`,
`decision_framework.py`, data/knowledge, and the CHANGELOG/ROADMAP/HANDOFF/REVIEW_NOTES/FINDINGS docs are not
touched (handled by a separate step). No git commit.
