# P2 plan: does the edge-loss model predict marsh it was not fitted to?

Written and committed on 11 November 2026, before any NAIP, Landsat or exposure value was measured outside
Barataria Bay. The models below are fixed now and run once. Quality-check fixes made before the run are
allowed and will be listed as amendments; anything changed after the run is exploratory.

Milestone P2 (proof-of-concept track, `docs/ROADMAP.md`); Modules 4 and 5. Builds on approved D1, D5, D6
and on D7 (Jaison gave the go-ahead for P2 on 11 Nov 2026, which applies D7's predictors).

## Question

If the tool is fitted on some Louisiana basins, how well does it predict marsh-edge loss in a basin it has
never seen? And does knowing the oiling level improve that prediction over exposure alone?

This is a predictive question for the tool, not the causal question of P1. Within-block comparisons are not
available for a new basin, so the models use only information a user would have for a new site.

## Units and basins

`scripts/build_edge_cells.py --louisiana`: 100 m salt-marsh (ESI 10A) edge cells along the SCAT-surveyed
Louisiana coast, -91.20 to -88.80 E, 28.90 to 30.35 N. `scripts/assign_basins.py` assigns basins from geography
alone (lines in the script). Counts of 10A cells before any outcome filter:

| Basin | Clean (NOO) | Very Light | Light | Moderate | Heavy | 2 km blocks |
| --- | --- | --- | --- | --- | --- | --- |
| Terrebonne | 6,480 | 487 | 235 | 251 | 45 | 190 |
| Barataria | 11,057 | 823 | 1,053 | 981 | 978 | 367 |
| Birdfoot delta | 3,590 | 273 | 163 | 295 | 270 | 127 |
| Breton Sound / St Bernard | 10,083 | 543 | 1,013 | 548 | 152 | 372 |

A basin is used as a test basin only if, after the outcome filters, it has at least 30 Heavy and 100 clean
cells (ASSUMED). Barataria Bay was used to develop the method; its results are reported but read with that
in mind.

## Measurements (same methods as before, run per basin)

- Outcome: NAIP edge-loss rate 2010 to 2015 (m/yr), `scripts/naip_edge_extract.py` with years 2010 and 2015
  only, and the filters of `validation/naip_edge_loss.py` (edge cell 0.1 to 0.9 land in 2010, at least 90%
  valid pixels, block and tile failure filters).
- Exposure from 2010 NAIP (`scripts/exposure_metrics.py`): open water within 1 km and 250 m, log mean fetch.
- Pre-spill trend: Landsat edge-loss rate 1999.6 to 2008.6 (`scripts/landsat_edge_fraction.py`, epochs A and B).
  Cells without a valid pre-spill rate are dropped (ASSUMED; reported by basin).
- Oiling: SCAT maximum oiling class.

All predictors are fixed by 2010; the outcome runs 2010 to 2015.

## Models (fixed)

| Model | Predictors |
| --- | --- |
| M0 no-predictor baseline | mean rate of the training basins |
| M1 exposure only | water 1 km, water 250 m, log fetch, pre-spill rate (linear least squares) |
| M2 primary | M1 + oiling class (5 levels, clean as reference) (linear least squares) |
| M3 boosted trees | same predictors as M2; scikit-learn HistGradientBoostingRegressor, max_iter 300, learning_rate 0.05, max_leaf_nodes 15, min_samples_leaf 50, random_state 0 |

## Validation (fixed)

Leave one basin out: fit on the other basins, predict every cell of the held-out basin, once per test basin.
Per held-out basin and pooled:

- MAE and RMSE (m/yr); skill against M0 = 1 - MAE(model) / MAE(M0).
- Block level: mean observed and predicted rate per 2 km block and oiling class (groups of at least 5 cells);
  MAE at that level, because planning works on stretches of shoreline, not single cells.
- Oil effect transfer: M2's Heavy coefficient from the training basins, against the held-out basin's own
  Heavy estimate from the P1-style model (oiling class + exposure + 2 km block, clustered by block).
- 90% prediction intervals for M2: the 5th and 95th percentiles of residuals from an inner leave-one-basin-out
  among the training basins, added to the prediction. Coverage on the held-out basin should be near 90%.

## How P2 is judged (fixed now)

- **Transfers:** M2 beats M0 on MAE in at least 3 of 4 test basins and pooled; M2 beats M1 pooled (oiling adds
  predictive value); interval coverage between 80% and 95% in each test basin.
- **Partly transfers:** M2 beats M0 pooled but not in 3 of 4 basins, or coverage falls outside 80 to 95% in
  some basins. The tool must then flag those conditions as extrapolation.
- **Does not transfer:** M2 does not beat M0 pooled.
M3 is a comparison: if it beats M2 clearly, that is recorded, but the linear model stays primary for the
proof of concept because it is easier to explain and check.

## Known limits

- One spill. Transfer to unseen marsh within Louisiana is not transfer to a new spill (D6).
- Cell-level edge loss is noisy (2 m pixels, classification), so R squared will be low even for a useful model;
  skill against M0 and the block-level results are the main measures.
- Terrebonne has only 45 Heavy cells before filters and may fall below the test threshold.
- Barataria dominates training when it is not the held-out basin.
- Cleanup after oiling is unknown (P3).

## Amendments after the quality check (11 Nov 2026, before the models were run)

No outcome had been compared between basins or oiling classes when these were made.

1. **Birdfoot delta excluded from P2 (training and testing).** In the active Mississippi River delta the 2010
   land rule fails: bright, sediment-laden river water is classified as land (visual check of NAIP 2010
   blocks), so the 2010 land mask, the edge-loss outcome, the exposure measures and the Landsat calibration
   are all unreliable there. Only 7 of 84 Landsat scenes passed the marsh/water contrast check (interior
   "land" read as dark as water in short-wave infrared). This is recorded as an applicability limit: the tool
   should flag active river-delta shoreline as out of scope until a method that handles plumes exists.
2. With three test basins, the "transfers" rule becomes: M2 beats M0 in all 3 test basins and pooled (was:
   at least 3 of 4).
3. **One validity rule for every area** (class-blind, ASSUMED threshold): Landsat is run per basin, or per
   quadrant of a basin where memory requires it (Breton, Barataria; water and marsh values are then taken per
   quadrant). An area is kept only if at least 50% of its Landsat scenes in each pre-spill epoch pass the
   marsh/water contrast check, i.e. the 2010 NAIP land map agrees with Landsat physics there. Results before
   any outcome comparison: Terrebonne passes (57 of 73 and 36 of 51 scenes); birdfoot fails (consistent with
   amendment 1); Breton west/south-west and north-west quadrants pass (167 of 174, 79 of 81 scene-epochs);
   Breton south-east fails (11 of 166) and north-east fails (0 usable; turbid Breton and Chandeleur Sound
   water read as land in 2010). Failed areas are excluded from training and testing and recorded as
   applicability limits.
   Barataria (run per quadrant): north-west, south-east and north-east pass (85 of 87, 89 of 110, 130 of 135
   scene-epochs); south-west (lower bay, Caminada and Grand Isle side) fails: no scene passes.
   Diagnosis common to all failed areas: on NAIP tiles that are almost all open water, Otsu's method splits
   two kinds of water instead of land from water, so part of the water is labelled land (interior "land"
   reads 0.004 in Landsat short-wave infrared, like water).
4. **Cell agreement filter** (class-blind, ASSUMED 0.4): drop a cell if its 2010 NAIP land fraction and its
   2007-2009 Landsat land fraction differ by more than 0.4, which catches single mis-classified tiles inside
   areas that pass rule 3. (Landsat reads about 0.1 lower than NAIP on average because of mixed pixels.)
5. Backlog, not part of P2: a land/water classifier that does not depend on each tile containing both marsh
   and water (e.g. trained on checked samples across tiles), together with Jaison's P1 note that the Landsat
   land-fraction maps are not very clean.
