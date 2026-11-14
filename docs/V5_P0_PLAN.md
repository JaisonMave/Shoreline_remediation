# V5 Phase 0.1 and 0.2 plan: out-of-sample oil excess and out-of-sample intervals (14 November 2026)

Modules 4 (ecological recovery prediction: marsh-edge loss) and 5 (generalisation and model reliability).
Decision IDs D37 (out-of-sample oil excess) and D38 (per-class out-of-sample intervals). Findings sections
FINDINGS_V5 44 and 45. Source of the task: `/home/claude/review/science_review.md`, "Five highest-value
improvements" items 1 and 2, approved by the owner as Phase 0 of the V5 plan.

Status: written before any new analysis was run. Every modelling choice is fixed below. Each gated analysis is
run once. If a gate fails, the result is reported as a failure and nothing is tuned.

## Disclosure (read first)

- These gates were set on 14 Nov 2026 after the reviewer had already seen the no-excess baseline's error and bias
  on these same cells, so the test is not blind. Known before this plan: on the 532 held-out heavy cells of
  Barataria and Breton, MAE 1.044 m/yr and bias (pred - obs) -0.475 m/yr for the clean-edge baseline with no
  excess; MAE 1.302 / bias +0.549 with the Zengel excess; 1.185 / +0.33 with the D32-scaled excess. Also already
  in the repository: the P2 within-block Heavy estimate inside held-out Barataria (0.37 m/yr,
  `results/p2_basin_holdout/oil_effect_transfer.csv`) and the reviewer's coverage by basin and oiling class of the
  deployed interval (0.76 to 0.99).
- Only three basins have data (Terrebonne, Barataria, Breton). When Barataria is held out, the training basins hold
  only 51 heavy cells (Terrebonne 20, Breton 31), so its excess is estimated from few cells.
- All cells are from one spill (Deepwater Horizon), one oil, one marsh type (ESI 10A salt marsh), one period
  (NAIP 2010-2015). Nothing here says anything about transfer to another spill or shoreline type.

## Data (committed tables only; nothing downloaded)

- `data/demo/p5_sites_clean_lobo.csv`: 12,696 in-scope 100 m edge cells (basin, 2 km block `cell_2km`, SCAT
  `max_oiling`, observed NAIP 2010-2015 edge-loss rate in m/yr, and `lobo_pred_clean` = prediction of the clean-edge
  baseline model (P2 model M1 refitted on NOO and Very_Light cells only) fitted WITHOUT that cell's basin). Built by
  `scripts/build_clean_baseline.py`.
- `data/demo/p5_sites.csv`: same 12,696 in-scope cells with the four inputs (`water_1km_2010`, `water_250m_2010`,
  `fetch_mean_m`, `pre_rate`) and `lobo_pred` = deployed model p5-edge-loss-v1 (M1 fitted on all classes) fitted
  WITHOUT that cell's basin. Built by `scripts/build_p5_demo.py`.
- Cell counts (basin x class; Heavy / Moderate / Light / Very_Light / NOO): Barataria 501 / 509 / 427 / 339 / 3,610;
  Breton 31 / 55 / 125 / 103 / 2,892; Terrebonne 20 / 124 / 132 / 168 / 3,660.
- Blocks: a block is the pair (basin, `cell_2km`). Two 2 km cells straddle a basin border; each half is treated as a
  separate block so that no block is split between training and test.
- `max_oiling` is the worst SCAT class ever recorded on the segment, applied to the whole cell (known dilution).

## Words used

- **Held-out basin**: the basin being predicted; nothing from it is used to fit or calibrate anything.
- **Conformal interval**: a prediction interval whose width is read off the sorted errors a model made on data it
  was not fitted to, with a small rank correction so that, if new cells behaved like the calibration cells, at least
  90% would fall inside.
- **Winkler score** (interval score): the interval's width plus a penalty of 20 times (2 / 0.10) the distance by which
  the observed value falls outside it, averaged over cells; lower is better, so a narrow interval that still covers
  scores well and a wide or often-missed interval scores badly.

## Part 0.1: oil excess estimated out of sample

### Question
Does an oil excess estimated only from the other basins, added to the clean-edge baseline, predict held-out
heavy-cell edge loss better than the same baseline with no excess, without introducing a heavy-specific bias?

### Method (fixed by the brief)
The excess for oiling class c in a held-out basin is the mean within-2-km-block difference in edge-loss rate between
class-c cells and no-oil-observed cells, estimated only from the OTHER basins, with no Zengel term; it is added to the
clean-edge baseline prediction fitted without the held-out basin. Report Heavy (gated) and Moderate/Light
(descriptive, not gated). Give a bootstrap interval for the excess, resampling blocks.

### Choices fixed here (the brief leaves them open)
1. Held-out basins: each of Terrebonne, Barataria and Breton in turn. The gate applies only to basins with 30 or more
   heavy cells (Barataria 501, Breton 31). Terrebonne (20 heavy cells) is reported, not gated.
2. "Edge-loss rate" is the observed NAIP rate (`observed_rate`), not a model residual.
3. A block contributes to the class-c excess if it holds at least one class-c cell and at least one NOO cell. Its
   difference is mean(class-c rate) - mean(NOO rate) within the block.
4. "Mean" over blocks is weighted by w = n_c * n_NOO / (n_c + n_NOO) (the weight that makes the estimate identical to
   a regression of rate on a class-c indicator with block fixed effects, using class-c and NOO cells only). All
   contributing blocks of all training basins are pooled with these weights. If no block contributes, the excess is
   0 and this is reported.
5. Classes given an excess: Heavy, Moderate, Light. NOO and Very_Light get none (Very_Light is in the clean
   baseline's own training set). Cells in the held-out basin are given the excess of their own class.
6. Prediction for a cell = `lobo_pred_clean` + excess of its class (a point prediction; no Monte Carlo composer).
   The no-excess baseline is `lobo_pred_clean` alone.
7. Bias = mean(prediction - observed). Heavy-cell bias minus unoiled-cell bias uses NOO cells of the same held-out
   basin as "unoiled" (their prediction is the baseline alone, since they get no excess).
8. Bootstrap for the excess: 2,000 replicates, seed 20261114; contributing blocks are resampled with replacement
   within each training basin (stratified by basin); the excess is recomputed with the same weights; 90% interval =
   5th and 95th percentiles of the replicates.
9. Descriptive only (not gated, fixed now): (a) block-bootstrap 90% interval of the heavy-cell MAE difference
   (out-of-sample excess minus no excess) in each held-out basin, resampling held-out blocks that hold heavy cells,
   2,000 replicates, same seed; (b) reference rows with a constant point excess equal to the Zengel 2010-2015 mean
   (years 1-5 mean of the Zengel periods, computed in code from `results/p3_treatment/A_prespill_adjusted.csv`) and to
   the D32 value (`models/oil_excess_d32.json`, E_field_size_weighted), so the point comparison is like for like;
   (c) a deployable excess per class estimated from all three basins, with the same bootstrap.
10. Check before the gate: the script recomputes MAE and bias of `pred_clean` on the 532 Barataria+Breton heavy cells
    and stops if they differ from 1.044 and -0.475 by more than 0.001.

### Baseline
Clean-edge baseline with no excess (`lobo_pred_clean`).

### Gate 0.1 (verbatim)
"In each held-out basin with 30 or more heavy cells, the heavy-cell mean absolute error with the out-of-sample excess
is strictly below that of the no-excess baseline, AND (heavy-cell bias minus unoiled-cell bias) is within plus or
minus 0.25 m/yr."

Both conditions must hold in both gated basins for a pass.

### Outputs
`validation/v5_p0_oil_excess.py` (run: `python -m validation.v5_p0_oil_excess`) writes to `results/v5_p0/`:
`oil_excess_cells.csv` (every held-out cell: basin, block, class, observed, baseline, excess, prediction),
`oil_excess_estimates.csv` (excess per held-out basin and class, with bootstrap interval, blocks and cells used),
`oil_excess_by_basin_class.csv` (MAE and bias per basin x class for the baseline, the out-of-sample excess and the
reference excesses), `oil_excess_summary.txt` (gate verdict). Card: `models/oil_excess_oos_v1.json`.

## Part 0.2: intervals calibrated without the target basin, per oiling class

### Question
Do 90% intervals whose offsets come only from other basins, computed separately per oiling class, cover 80-97% of
held-out cells in every well-populated basin x class group, and are they better (lower Winkler score) than an interval
with no predictor?

### Method (fixed by the brief)
For each held-out basin, interval offsets are the 5th and 95th percentiles of out-of-sample residuals from the other
basins only, computed separately per oiling class (classes with fewer than 100 calibration cells fall back to the
all-class offsets; say when that happens), with the standard finite-sample conformal correction. The no-predictor
baseline interval is the training-basin mean plus the 5th/95th percentiles of training-basin deviations from that
mean.

### Choices fixed here
1. Point predictor (gated): the deployed model p5-edge-loss-v1 (P2 model M1, exposure + pre-spill trend, all classes),
   as it is the model whose interval the review faulted. Held-out prediction = its committed leave-one-basin-out
   prediction `lobo_pred` in `data/demo/p5_sites.csv`.
2. "Out-of-sample residuals from the other basins only" is read strictly (nested): for held-out basin B with training
   basins A and C, the calibration residuals of A's cells come from M1 fitted on C alone, and those of C's cells from
   M1 fitted on A alone. So no model used for calibration has seen basin B. (The plain leave-one-basin-out residuals of
   A would come from a model fitted on B and C, which uses B.) The inner models are refitted by ordinary least squares
   from the four inputs in `data/demo/p5_sites.csv` (log fetch = ln(fetch + 16 m), as in the model card). As a check,
   the same code refits the outer leave-one-basin-out models and must reproduce `lobo_pred` within 0.01 m/yr, or the
   script stops.
3. Residual = observed - predicted. Finite-sample conformal correction, alpha = 0.10, each tail 5%: with n sorted
   calibration residuals, the lower offset is the k_lo-th smallest with k_lo = floor(0.05 (n + 1)) and the upper is the
   k_hi-th smallest with k_hi = ceil(0.95 (n + 1)) (minus or plus infinity if k_lo < 1 or k_hi > n). Interval =
   [prediction + lower offset, prediction + upper offset]. A cell is covered if lower <= observed <= upper.
4. Classes: NOO, Very_Light, Light, Moderate, Heavy (the `max_oiling` values). Calibration cells per class are the
   cells of that class in the two training basins. Known before running (counts only): held-out Barataria has 51
   Heavy calibration cells, so its Heavy cells use the all-class offsets.
5. No-predictor baseline (M0): training-basin mean of observed rate (all classes, both training basins pooled) plus
   the 5th and 95th percentiles (numpy default linear quantile, as the brief states) of training-cell deviations from
   that mean. Not class-conditional.
6. Coverage gate groups: held-out basin x class groups with 100 or more held-out cells (by the counts above: Barataria
   all five classes; Breton NOO, Very_Light, Light; Terrebonne NOO, Very_Light, Light, Moderate; 12 groups). Smaller
   groups are reported, not gated.
7. Winkler score: mean over all held-out cells of the basin (all classes), alpha = 0.10. Gate compares it with M0's in
   each of the three held-out basins.
8. Descriptive only (not gated, fixed now): (a) the same nested conformal interval without class conditioning
   (all-class offsets for every cell), to show what conditioning on class adds; (b) the deployed v1 offsets
   (-3.159, +2.882, calibrated on the pooled residuals they are scored on) applied to `lobo_pred`, for reference;
   (c) the same per-class nested conformal procedure around the composer's natural-recovery point prediction from
   Part 0.1 (clean-edge baseline + out-of-sample class excess); inner folds refit the clean-edge model on the single
   remaining training basin's NOO and Very_Light cells and estimate the excess from that basin's blocks alone (excess
   0 if that basin has no contributing block; reported). Its held-out predictions are those of Part 0.1.
9. Deployable offsets (for the card and the code option, not part of the test): per class, conformal offsets from
   the plain leave-one-basin-out residuals of all three basins (same 100-cell fallback). This is the same procedure
   one level up: offsets come from models that did not see the cells they are scored on.

### Baseline
M0 interval (training-basin mean with its own spread), as above.

### Gate 0.2 (verbatim)
"Coverage of the 90% interval is between 80% and 97% in every basin-by-oiling-class group with 100 or more cells, AND
the interval (Winkler) score is lower than that of the no-predictor baseline interval in each held-out basin."

Both conditions must hold for a pass. Coverage limits are inclusive (0.80 and 0.97 pass).

### Outputs
`validation/v5_p0_intervals.py` (run: `python -m validation.v5_p0_intervals`, after the Part 0.1 script) writes to
`results/v5_p0/`: `interval_cells.csv` (every held-out cell with each interval), `interval_offsets.csv` (offsets used
per held-out basin and class, calibration n, fallback flag), `interval_by_basin_class.csv` and
`interval_by_basin.csv` (coverage, mean width, Winkler score, MAE, bias), `interval_summary.txt` (gate verdict) and
`summary.txt` (both verdicts). Card: `models/p5_edge_loss_v2.json`.

## What happens after the run

- Cards declare "experimental (gate passed, awaiting owner review)" or "experimental (gate failed)", never "validated".
- `scenario_composer.py` and `site_evidence.py` get the new excess and the per-class offsets as options only; defaults
  are unchanged. If a gate fails the option stays, its docstring says it failed, and the default is not changed.
- Composer option time profile (ASSUMED): the out-of-sample excess estimates the 2010-2015 mean (years 1-5). In the
  composer it keeps the Zengel time shape (front-loaded), scaled so its years 1-5 mean equals the out-of-sample
  excess, as D32 did; its spread is a normal from the bootstrap 90% interval. Years 6-8 are not tested by any data.
- `models/p5_edge_loss_v1.json` gets a note: its "90% intervals covered 89%" refers to P2 model M2's inner interval,
  and its deployed offsets were calibrated on the same residuals they were scored on.

## Limits known in advance

- Within-block differencing removes exposure differences between blocks, not within them; heavy cells can still be
  more exposed than NOO cells in the same block.
- Hidden manual treatment of heavy segments and oiling misclassification are not addressed.
- Conformal coverage guarantees assume exchangeable cells; basins are not exchangeable, which is why coverage is
  tested per basin and class rather than assumed.
- NAIP rates read about 1.2 m/yr below field measurements (P3 analysis C); all comparisons are NAIP against NAIP.
