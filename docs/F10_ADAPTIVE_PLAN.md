# F10 adaptive monitoring plan (M9)

Date: 2026-11-14  
Status: Proposed, run once after this plan is committed.

## Question
Do site monitoring observations update natural-recovery forecasts usefully for unmonitored cells in held-out blocks?

## Data and scope
- Primary check (2010-2015): same held-out basins and block setup as C2b/C1c (`barataria`, `breton`), using `data/demo/p5_sites_clean_lobo.csv` via `scenario_composer._baseline_lobo()`.
- Time-update secondary check (2010-2015 -> 2010-2017): Barataria only, as B1/B1c style, matched to `results/naip_edge_loss/cell_rates.csv` (`period == 2010-2017`).
- Blocks: `cell_2km` with >=5 matched cells.
- Monitoring fractions per block: 10%, 25%, 50%.
- Monitoring assignment: random within block, fixed seed (deterministic).

## Method
For each held-out basin and block:
1. Build residual pools from other basin(s), same as C2b/C1c:
   - block residual pool = empirical block means;
   - within-block residual pool = empirical cell deviations from each block mean.
2. Randomly select monitored cells (fraction f), leaving the rest unmonitored.
3. Prior forecast for unmonitored cells: current compose_block natural-recovery mechanics (clean baseline, D32-scaled oil excess for Heavy, one shared block residual draw per draw + independent within-block draws).
4. Update shared block residual with monitored-cell residuals using normal-normal conjugacy:
   - prior on shared block residual: Normal(mean(block_pool), var(block_pool));
   - monitored residual mean: observed - (baseline prediction + deterministic oil excess mean for horizon);
   - likelihood variance of monitored mean: var(within_pool) / n_monitored.
5. Updated forecast for unmonitored cells: same machinery, but shared block residual sampled from posterior; within-block noise unchanged.
6. Compute per-cell prior/updated median, 90% interval, coverage, and width.

## Gate (pre-specified)
Evaluate at **25% monitoring** for unmonitored cells.
Updated forecast must:
1. reduce MAE of the median vs prior;
2. narrow median 90% interval width vs prior;
3. keep updated 90% coverage within 80-97%.

Report all fractions (10%, 25%, 50%), by basin and pooled, and separately for Heavy and NOO cells.
Apply the same gate for the secondary time-update check.

## Outputs
- `results/f10_adaptive/coverage.csv`
- `results/f10_adaptive/summary.txt`
- `results/f10_adaptive/interval_width_vs_fraction.png`
- Focused tests: `tests/test_f10_adaptive.py`

## Run once command
`python -m validation.f10_adaptive_check`
