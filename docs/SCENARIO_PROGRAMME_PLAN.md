# Scenario programme: treatment comparison, long-term forecast, mangroves (plan, 12 Nov 2026)

Direction set by Jaison on 12 Nov 2026: Phase A compares treatment options including untested ones, judged
from scientific literature; Phase B forecasts recovery over months to years at a new place; Phase C extends
to mangroves (not beaches). Nothing in Phase A below had been computed when this file was committed.

## Phase A: compare treatment options at an oiled salt-marsh site

### A1 Vegetation recovery curve (pre-specified analysis, run once)

**Data.** `data/external/zengel2022_meta/` (1,158 rows, 10 source studies, 2010-2017, oiled and reference
sites, two marsh zones). The table has **no treatment variable**, so it gives the recovery curve of oiled
marsh as it was managed, not treatment effects.

**Unit.** One study x year x marsh zone that has both oiled and reference sites. Outcome: log response ratio
`lnRR = ln((mean oiled TotalCover + 1) / (mean reference TotalCover + 1))` (the +1 percentage point is ASSUMED,
to allow zero cover). Time `t = Year - 2010 + 0.5` years (ASSUMED late growing season). 0 means recovered.

**Models.**
- M0 baseline: lnRR is a constant (no recovery trend).
- M1: lnRR = a + b ln(t).
- M2 (primary): lnRR = -A exp(-t / tau), recovery towards the reference; A and tau fitted by least squares.
- M3 (secondary): M2 with a separate A for each marsh zone.
- Secondary run of M0 and M2 on the heavy-oiling subset (`Site type (HO)`, 5 studies).

**Validation.** Leave one whole study out: fit on the other studies, predict every unit of the held-out
study. Error = mean absolute error of lnRR per held-out study, then averaged over studies (so the largest
study does not dominate). 90% prediction interval = 5th and 95th percentiles of leave-one-study-out
residuals; report coverage per study. Uncertainty of every summary by bootstrap over studies (2,000, seed
20261112). Report per-study results, including studies where M2 is worse.

**Pre-specified reading.**
| Result | Verdict |
| --- | --- |
| M2 study-averaged error below M0 and the 90% interval of the difference excludes zero | Validated: use the curve |
| M2 below M0 but the interval includes zero | Suggestive: show the curve with its interval and say so |
| Otherwise | Not usable: show study-year means only |

Also reported (not a gate): years until expected cover reaches 80% of reference, with a 90% interval by
bootstrap over studies; flagged as extrapolation beyond t = 7.5.

**Limits known in advance.** Ten studies, several with one or two years; all one spill; sites without
coordinates; oiling severity differs between studies; cleanup is unrecorded and mixed into "oiled".

### A2 Scenario composer (engineering; no new fitting)

For a site and an option, simulate 5,000 draws (seed fixed) of yearly outcomes to 8 years:
- **Edge loss** = site baseline (deployed model p5-edge-loss-v1 prediction plus a draw from its held-out
  residuals) + oil excess (Zengel 2022: +1.88 m/yr in years 0-2, +0.21 in years 2-8, drawn from their
  intervals as normal) + treatment shift (existing `erosion_prior`, same periods).
- **Vegetation cover relative to reference** = A1 curve (if validated or suggestive) with its interval;
  treatment shift at year 2 from Zengel 2015 where it exists.
- Outputs per option: median and 90% range per year; cumulative edge lost by years 2, 5, 8; probability that
  the option beats natural recovery on each outcome. Options whose 90% ranges overlap natural recovery are
  labelled "cannot be distinguished".
- **Check C1 (pre-specified):** for heavily oiled cells in the two P2 held-out basins, the composed 90% range
  for 2010-2015 mean edge loss (natural recovery option) should contain the observed NAIP value in 80-97% of
  cells. Reported whether or not it passes. NAIP reads about 1.2 m/yr low, which is expected to push
  coverage down; say so.

### A3 Untested treatments (elicited priors from literature)

An evidence table (`data/knowledge/treatment_evidence_untested.csv`) is being compiled from field trials,
monitoring studies and agency guidance, each row with its source and how much of it was read. Priors are
set from the table by this rule, fixed here before the table was seen:

| Best available evidence for marsh | Prior on recovery time relative to natural recovery (multiplier, 90% range) |
| --- | --- |
| Field evidence of benefit, two or more independent studies | 0.6 to 1.0 |
| Field evidence of benefit, one study, or benefit only under stated conditions | 0.7 to 1.2 |
| Mixed or conflicting field evidence, or mesocosm/laboratory only | 0.6 to 1.6 |
| Field evidence of harm, or guidance advising against use in marsh | 1.0 to 2.0 |
| No credible evidence | 0.5 to 2.0, labelled "unknown" |

These ranges are ASSUMED and deliberately wide. Every such option is labelled **ELICITED, not measured**, shown
with its sources and conditions, and never ranked above an option with measured evidence on the strength of
its prior alone. The multiplier acts on tau in the A1 curve; it has no effect on edge loss (no evidence).

## Phase B: long-term forecast at a new place (design; not started)

Jaison's choice of horizon (months to years) changes the inputs: by then a shoreline oiling survey exists, so
the forecast starts from observed oiling class, not from a drift model. Drift models (PyGNOME, OpenOil, D19)
are therefore not needed for Phase B and stay deferred.

- Inputs at a new place: oiling class from survey; exposure and pre-event shoreline trend from imagery (the
  P1/P2 pipeline); habitat; treatment applied; measured soil if any (maps are not usable, D21).
- Engine: the Phase A composer, with horizons 1, 3, 5 and 8 years; anything beyond 8 years is extrapolation
  (our longest outcome series end in 2017-2018) and is shown as such.
- Long-term question it can address: cumulative marsh lost, and years to vegetation recovery, under each option.
- Gate: all inputs must be producible for a place outside the fitted basins without using its outcomes;
  rerun the basin hold-out end to end with the composer and report coverage per basin. A second spill is
  still needed before claiming transfer between spills (D5).

## Phase C: mangroves (feasibility first; not a model yet)

Mangroves differ from marsh in the ways that matter here: outcomes are tree mortality, defoliation and
seedling recruitment over decades; oil persists in anoxic sediment; cleanup options and their harms differ.
The marsh model must not be reused. Step 1 is an inventory of open mangrove outcome data
(`docs` entry to follow); a model is proposed only if at least two independent sites with outcome series
and a reference exist.

## Phase A4: option differences, block-level totals, conditions (plan added 12 Nov 2026, before any of it was run)

Reason: FINDINGS 15. At single-cell scale every option's range overlaps natural recovery, because the range
is dominated by cell-level noise that is the same whichever option is chosen.

### A4.1 Amendment to the A2 labelling rule
The "cannot be distinguished" label was defined on overlap of each option's own range. That ignores the
fact that the baseline and its noise are shared between options. **New rule:** an option is "distinguished
from natural recovery" on an outcome when the 90% interval of the **paired difference** (option minus
natural recovery, same simulated baseline in each draw) excludes zero. The old overlap flag is kept in the
output for transparency. Consequence to state wherever shown: the paired difference does not depend on the
site; it is the field evidence (one site, Zengel 2015/2022) accumulated over time, so "distinguished" means
"the evidence distinguishes the options", not "this site was measured". Elicited options have no edge-loss
difference and remain undistinguished unless their range excludes 1.

### A4.2 Block-level composer
`compose_block(cells, options, ...)`: for a set of edge cells (a 2 km block, or any user selection), total
outcome = mean edge loss rate over cells and cumulative marsh area lost (sum over cells of cumulative
retreat x 100 m cell length, in m2 and ha; one cell is ASSUMED to hold 100 m of edge, known to be an
underestimate). Noise model: held-out residuals of the deployed model (P2 predictions) split into a block
component (block mean residual) and a within-block component (cell minus block mean); each draw takes one
block residual for the whole block and independent within-block residuals per cell, both resampled from the
empirical held-out sets. Oil excess and treatment shifts are drawn once per draw and shared by all cells.

**Check C2 (pre-specified, run once):** for 2 km blocks with at least 5 valid cells in the two P2 held-out
basins, natural-recovery option, cells given their own oiling class effect only if Heavy (as in A2): the
composed 90% range for the block mean edge loss 2010-2015 should contain the observed block mean in 80-97%
of blocks. Report per basin, with the median width of the block range against the median width of the
cell range. Blocks are the unit; nothing is tuned after seeing coverage.

### A4.3 Conditions in the screening view
`data/knowledge/treatment_conditions.csv` (written by the orchestrator from the evidence notes, each row
with its source and evidence class) lists, per treatment, the conditions under which the literature reports
benefit or harm. The Site evidence view shows them as "conditions to check" beside each option. **The rule
engine's verdicts are not changed** (they need Jaison's review first); conditions the site data cannot
verify (season, water over the soil, days since oiling) are shown as questions for the user.

### A4.4 Dashboard
A "Compare options" section in the Site evidence view: for the selected cell, and for its 2 km block, a
table per option of evidence label (MEASURED / ELICITED), paired difference from natural recovery with 90%
interval at years 2, 5 and 8 (edge loss; vegetation where available), the distinguished flag, and the
conditions to check. Always shows ranges, the vegetation curve's "suggestive" status, and the note in A4.1.
