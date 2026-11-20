# Protocol: Bay Jimmy cumulative shoreline retreat projections (P-RET-1)

Status: **specified 20 November 2026, before any forecast evaluation was run.** Session 1 of
`docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md`. Nothing in this file was fitted or scored before section 7's criterion was confirmed.

**Owner confirmation, recorded 20 November 2026 at the start of Session 6, before any score was computed:** Delta = 0.5 m is
confirmed as the minimum useful gain, as a research criterion (not a management threshold). Sections 5 to 7 are applied
unchanged. Results are in section 10, added after scoring.

## 1. Purpose and claim boundary

Two separate products, kept separate in every output:

1. **Conditional scenario projection.** Continue cumulative retreat from the last observed group mean at a stated rate to a
   user-chosen end date (for example 2030 or 2050). The end date is a planning horizon, not a validated horizon. Every point after
   the last survey is labelled "conditional projection: holds only IF the stated rate applies". This product needs no gate to run.
2. **Forecast-skill claim** for a historical rate rule. Only the evaluation in sections 5 to 8 can support a statement such as "rule
   X beat the constant-rate baseline at lead times up to L years on these plots". Such a claim never extends beyond the tested
   lead times, these plots or this site.

The existing `scenario_composer.forecast` design refuses horizons beyond 8 years (`docs/SCENARIO_PROGRAMME_PLAN.md`, Phase B1).
The research runner does not change or bypass that; its long-horizon outputs are conditional scenarios, not composer forecasts.

## 2. Endpoint

| Item | Definition |
| --- | --- |
| Quantity | Cumulative landward movement of the marsh edge since the time origin, group mean of plot values |
| Unit and sign | metres; positive = land lost (edge moved landward). Per plot: mean over its two transects of (first distance minus current distance), as in `recovery_trajectories.field_positions()` |
| Population | Heavily oiled **untreated** plots at Bay Jimmy (northern Barataria Bay), Deepwater Horizon: plots 3, 8, 12, 13, 15, 16, 18, 19, 23 (n = 9). Spartina/Juncus salt marsh. |
| Secondary groups (reported, not promotion targets) | Manual removal (11, 17, 20, 21, 22; n = 5) and reference (24 to 28; n = 5). Mechanical removal is **not eligible**: no plot has a December 2010 origin (2 plots from 13 Nov 2011, 4 from 2014). Planted plots have no field positions. |
| Not this endpoint | The mapped worked-example cell `8018_32612` (100 m NAIP cell, `edge_loss_v1` 1.42 m/yr 2010-2015, no oiling term). Plots and cell are different spatial units and must not be pooled, compared as one series or used to calibrate each other. |
| Time origin | 4 December 2010 (decimal 2010.9233), the first survey with every untreated, manual and reference transect. The partial 9 Oct 2010 survey is excluded. Retreat between oiling (mid-2010) and the origin is not observed in this series. |
| Time variable | Elapsed decimal years via `recovery_trajectories.decimal_year`, i.e. actual dates, so output cadence cannot change any value. |
| Observation depth | Not applicable (horizontal position). |

## 3. Data and evidence window (verified 20 Nov 2026 with the existing loader)

Source: `data/external/zengel2022/zengel2022_griidc_erosion.xlsx`, sheets "GIS field erosion points" and "GIS field erosion";
Zengel et al. 2022, Sci. Rep. 12:13802; GRIIDC doi:10.7266/VF524143 (CC0). SHA-256 prefix of the working-tree file
`e1615f1317dc21c0` (Windows checkout; see the handoff note on line endings for text files; this file is binary).

Untreated group means of cumulative retreat (m), all 9 plots present at every date:

| Survey | Elapsed (yr) | Mean | SD (plots) |
| --- | --- | --- | --- |
| 2010-12-04 | 0.000 | 0.000 | 0.000 |
| 2011-11-13 | 0.942 | 2.770 | 1.739 |
| 2012-09-17 | 1.787 | 5.632 | 1.105 |
| 2013-09-08 | 2.762 | 7.223 | 1.487 |
| 2014-09-26 | 3.811 | 8.586 | 1.838 |
| 2015-09-30 | 4.822 | 9.774 | 2.098 |
| 2016-10-05 | 5.836 | 12.126 | 2.454 |

**Final survey: 5 October 2016** (decimal ~2016.76), mean 12.126 m, plot range 9.27 to 15.84 m. Manual: 11.442 m (n = 5).
Reference: 7.691 m (n = 5). Values match `docs/V5_4_RECOVERY_VIEW.md`.

Related cutoffs (not part of this endpoint): total vegetation cover plot-years 2011 to 2016 (2013-2016 survey months assumed
September); manual-plot cover 2011 and 2012 only; Zengel 2015 tPAH July-August 2011 and September 2012; borrowed
`pah_decline_v1` heavy-class rate supported to about 2013.78.

Elapsed time from the final survey to 1 Jan 2030 is about 13.2 years, and to 1 Jan 2050 about 33.2 years.

## 4. Provenance: what calibrated what, and what is available for testing

| Quantity | Calibrated on | Shares sources with | Available for an independent test |
| --- | --- | --- | --- |
| Plot retreat fits M0/M1 (`recovery_trajectories`) | All 7 survey dates of the same plots (model choice by leave-one-plot-out, all dates) | Zengel 2022 plots also calibrate composer treatment shifts and oil excess; Zengel 2015 uses the same plots | **No untouched data.** Every survey date has been viewed and fitted. A temporal split (section 5) is a pseudo-prospective test on the same plots, not independent. |
| Composer natural recovery (`composer_natural_recovery_v1`) | NAIP clean-edge cells; oil excess from Zengel 2015/2022 plots scaled by D32; treatment shifts from Zengel 2022 plots | Plot retreat (above) | Held-out basins (done: coverage passed, heavy-cell bias **failed**: R3 +0.55, D32 +0.33 m/yr). Not re-tested here. |
| `edge_loss_v1` | 12,696 NAIP cells, 2010-2015 | None with plots | Held-out basins (P2, passed). Different spatial unit; not a plot forecast. |
| Pre-spill DSAS rates (~1.2-1.3 m/yr, 1956-2004) | Aerial imagery | n/a | Context only; image dates for the "DSAS annual" sheet are unconfirmed. Not used. |
| Cross-site transfer | n/a | n/a | **None.** One eligible site. Cross-site skill remains unevaluated. |

## 5. Evaluation design (pseudo-prospective, within-site)

Forecast target: the **increment** of group-mean retreat from an anchor (cutoff) survey c to each later survey t, i.e.
R(t) - R(c). This is exactly what the scenario runner produces (it anchors at the last observation).

- Cutoffs c: 2012-09-17, 2013-09-08, 2014-09-26, 2015-09-30. Training uses only surveys at or before c.
- Targets: every later survey. Pairs: 4 + 3 + 2 + 1 = 10. Lead times about 0.97 to 4.05 years.
- Pairs share plots and overlapping periods, so they are **not independent**; report per pair and per lead time, never as 10
  independent tests. Unit of resampling for any interval: whole plots (cluster bootstrap, seed 20261120, 2000 draws).
- The 2015 to 2016 interval contains a jump shared with the reference plots (reference +1.81 m, untreated +2.35 m); it is kept, not
  removed, and its influence is reported separately.

## 6. Candidate rules and baselines (fixed now)

All rates are estimated from training surveys only, then applied as R_hat(t) = R(c) + rate x (t - c).

| ID | Rule | Rate estimate |
| --- | --- | --- |
| B0 | Last-observation persistence (baseline) | 0 |
| B1 | Constant rate over the record available at the cutoff (baseline; the M0 form) | Least-squares slope through the origin of plot increments using **only surveys on or before c**. "Whole-record" means the whole record available at the simulated forecast date, never the record through 2016: using later surveys would leak the answer |
| C1 | Recent-interval rate | (R(c) - R(c_prev)) / (c - c_prev), group means |
| C2 | M1 long-run rate b (fading-excess form) | `recovery_trajectories` M1 fitted to surveys <= c, same bounds. Eligible only for c >= 2013-09-08 (at least three post-origin dates); if tau sits at a bound, the cutoff is reported as "not identified" for C2 and not scored |

No other rule is added after results are seen. Any later rule is a new protocol version. Every rule, baseline included, is scored
on exactly the same (cutoff, target) pairs; a pair a rule cannot score (C2 not identified) is reported and the comparison for that
rule is restricted to the pairs both can score, with the pair count stated.

## 7. Error measures and acceptance criteria

Per pair: signed error (forecast minus observed, m) and absolute error of the group-mean increment; also plot-level MAE.
Summaries: MAE and mean signed bias by lead-time bin (<1.5, 1.5-2.5, 2.5-3.5, >3.5 yr) and overall; counts of pairs per bin.

Primary comparator: **B1**. A candidate C passes P-RET-1 only if all hold:

1. Overall MAE(C) <= MAE(B1) - Delta.
2. MAE(C) <= MAE(B1) in every lead-time bin that has at least two pairs.
3. |mean signed bias(C)| <= |mean signed bias(B1)| + 0.25 m.
4. B1 itself beats B0 overall (otherwise the comparison set is uninformative and the result is reported as such).

**Minimum useful gain Delta = 0.5 m: a research criterion, confirmed by the owner on 20 November 2026 before scoring.** In plain terms, a candidate
rate rule must reduce the mean absolute error of the predicted group-mean retreat by at least half a metre compared with B1,
scored on the same pairs.

Context, not justification as a management threshold: position measurement error (tape and DGPS, about 0.1 m) is negligible
against between-plot variation; the standard error of the 9-plot group mean of cumulative retreat is about 0.37 to 0.70 m at the
earlier surveys and 0.82 m at the final survey (SD 2.454 / sqrt 9). Those numbers describe uncertainty in the observed mean at single
surveys; they show that gains well below half a metre would be hard to distinguish from sampling noise. Half a metre is also about
0.35 to 0.4 years of the long-run rate (1.25 to 1.43 m/yr). Whether a 0.5 m difference would change a management decision needs
separate evidence (what difference in projected edge loss alters a response or restoration choice), which this protocol does not
supply. The owner may set a different value **before** the evaluation is run; it must not be changed afterwards.

If no candidate passes, B1 remains the default "historical rate" offered to scenario users, labelled as an untested-beyond-4-years
assumption. Passing promotes nothing to "validated": with one site, the most it supports is "experimental, within-site lead times
up to the tested maximum".

## 8. What remains out of scope regardless of the result

- Any skill claim beyond about 4 years' lead, for any year after the tested targets, including 2030 and 2050.
- Other plots, cells, sites, oiling classes or habitats (rocky and mangrove return structured "unsupported" reasons).
- Storm, sea-level, subsidence or treatment effects on future rates (no versioned forcing or defensible mapping exists in the
  repository). Alternative assumptions are separate curves; a range between two chosen rates is a **sensitivity range**, not an
  uncertainty interval.
- Treatment effects: manual-versus-untreated differences are historical observational contrasts (Session 4), not projected
  annual benefits.

## 9. Historical validation record (unchanged; not evidence for this endpoint)

Legacy replay 5/6 and integrated F11 replay 2/6 against an always-active baseline of 5/6 evaluate different decision rules
(`docs/V5_1_VALIDATION.md` section 1) and supply no validation for these curves. F5 (0.775 against 0.750) and D32 bias gates
remain failed.

## 10. Results (scored 20 November 2026, Session 6, after Delta was confirmed)

Command: `python -m src.shoreline_remediation.projections evaluate --output <new dir>` (protocol code
`src/shoreline_remediation/projections/evaluation.py`; outputs `pairs.csv`, `rates.csv`, `evaluation.json`). Nine untreated
plots, seven surveys, four cutoffs, 10 pairs. Bootstrap: 2000 whole-plot draws, seed 20261120 (descriptive only).

Rates by cutoff (m/yr): B1 3.105, 2.786, 2.491, 2.273; C1 3.388, 1.633, 1.299, 1.176; C2 not eligible at 2012-09-17, then -0.506,
-0.799, -0.717.

| | C1 recent-interval rate | C2 M1 long-run rate b |
| --- | --- | --- |
| Pairs scored / omitted | 10 / 0 | 6 / 4 (cutoff 2012-09-17: fewer than three post-origin surveys) |
| Longest lead scored | 4.05 yr | 3.07 yr |
| MAE candidate / B1 / B0 (m), same pairs | 2.246 / 2.742 / 3.108 | 3.696 / 1.883 / 2.649 |
| Candidate minus B1 (m) | -0.497 (90% bootstrap -1.77 to +0.66) | +1.814 (90% bootstrap -0.59 to +2.57; 153 draws dropped) |
| Signed bias candidate / B1 / B0 (m) | +1.83 / +2.73 / -3.11 | -3.70 / +1.87 / -2.65 |
| 1. MAE gain >= 0.5 m | **fail** (gain 0.497 m; short by 0.003 m) | **fail** |
| 2. No worse than B1 in bins with >= 2 pairs | pass (<1.5, 1.5-2.5, 2.5-3.5 yr) | **fail** (<1.5 and 1.5-2.5 yr) |
| 3. Bias within B1 + 0.25 m | pass | **fail** |
| 4. B1 beats B0 | pass | pass |
| Verdict | **fail** | **fail** |

C2 identification: at all three scored cutoffs A sits at its +20 m bound and b is negative (net advance), while tau is inside its
bounds. The section 6 rule (tau only) did not catch this, so C2 was scored as specified; under a bound-aware reading C2 would have
no scored pairs and be unevaluable. Either way C2 does not pass. The rule is not amended after the fact; a future protocol version
should test every parameter bound.

The 2015-2016 jump: the four pairs with 2016-10-05 targets carry the largest errors (C1 at cutoff 2012-09-17: +7.23 m). Without
them (sensitivity, not a criterion) C1 MAE 2.174 vs B1 2.688 m (6 pairs), a 0.514 m gain; C2 2.494 vs B1 2.027 m (3 pairs). The
C1 result therefore depends on the jump year: it is just below Delta with it and just above without it.

What this supports: no candidate rule earned replacement of B1 as the default historical rate. B1 beat persistence (B0) on the
pairs scored, but overpredicted later retreat by +1.9 to +2.7 m on average because the post-spill excess fades. With one site, nine
plots and overlapping pairs, none of these numbers is evidence of skill beyond about four years or at any other place; 2030 and
2050 outputs keep their conditional-projection labels.
