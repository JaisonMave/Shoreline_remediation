# Draft plan: soil PAH decline in oiled marsh (DIVER) - PROPOSED, NOT APPROVED, NOT RUN

Written 12 Nov 2026 after a structure-only inspection of the files (`docs/DIVER_SOIL_STRUCTURE.md`): counts,
names and codes only; no concentration was summarised by time or by oiling. Each choice marked **[Jaison]**
is a soil-chemistry judgement that needs his confirmation before anything is run.

## What the files allow
- PAH results exist for 1,703 of 14,926 soil samples: spring 2011, fall 2011, fall 2012, fall 2013 (none in
  fall 2010). About 200 stations, most visited in 3 or 4 campaigns. Surface samples (0-2 cm grabs, some 0-10
  cm cores).
- Fall 2013 samples carry no station label: they must be matched to stations by coordinates.
- No oiling descriptor in the files: oiling must come from SCAT by distance, as for CRMS.
- Ready-made totals are text, not numbers: totals must be summed from compounds.
- No numeric detection limits; non-detects are flagged by category only.
- Hopane was measured on about 1,800 samples.

## Proposed choices
| # | Choice | Proposal | Why | Status |
| --- | --- | --- | --- | --- |
| 1 | Rows used | Collection matrix soil, analysis type PAH, dry-weight, ppb; exclude water-type analytes filed under soil, tarball/oil rows and wet-weight rows | Same quantity throughout | **[Jaison]** |
| 2 | Outcome | Sum of the parent and alkylated PAH compounds that are reported in every campaign (list fixed from the files before any value is read) | Totals must be comparable between campaigns | **[Jaison]**: which sum (a 50-compound total, the 16 priority PAHs, or both) |
| 3 | Second outcome | The same sum divided by hopane (C30 17a(H),21b(H)-hopane) | Hopane is conserved, so the ratio falls only by degradation or dissolution, not by dilution or burial | **[Jaison]** |
| 4 | Replicates | Lab replicates averaged; where two labs report the same sample, keep the lab that analysed the most samples in that campaign and report the other as a sensitivity run | 21,071 duplicate sample-compound keys, most with differing values | **[Jaison]** |
| 5 | Non-detects | Bounds, not substitution: lower bound sums non-detect compounds as 0; upper bound cannot be computed without limits, so samples with more than 20% of compounds non-detected are reported separately and the analysis is repeated without them | No numeric limits exist; half-the-limit substitution is impossible and would be arbitrary | **[Jaison]** |
| 6 | Depth | 0-2 cm grabs only in the primary analysis; 0-10 cm cores as a separate stratum | Different depth intervals are not comparable | **[Jaison]** |
| 7 | Unit | The station (matched by coordinates within 30 m, ASSUMED, where the label is missing); station value per campaign = median of its samples | Never the sample | - |
| 8 | Oiling | SCAT maximum oiling class of the nearest surveyed shoreline within 100 m (ASSUMED); stations beyond that are "unknown" | Only public oiling source | - |

## Analysis (to be run once after approval)
- Outcome on the log scale. Baseline M0: each station keeps its first measured value (no decline).
- M1: first-order decline, log value = station level - k x years since April 2010, with k by oiling class;
  mixed model with station as a random effect.
- Validation: leave whole stations out (grouped 5-fold, seed 20261112); error of M1 against M0; 90%
  prediction intervals and their coverage; half-life with interval. Report by oiling class and by state.
- Verdict rule as elsewhere: validated if M1 beats M0 and the interval of the difference excludes zero;
  suggestive if it only leans; otherwise not usable.

## Limits known in advance
No pre-spill or fall-2010 PAH. Stations were chosen by the damage assessment, not at random. Cleanup is
unrecorded. Total PAH is not exposure: the freely dissolved fraction depends on soil organic carbon
(REVIEW_NOTES E0). Sums from different compound lists are not comparable with published totals.
