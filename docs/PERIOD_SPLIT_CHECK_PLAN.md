# Plan: did the heavy-oiling excess fade? (period-split check)

Status: **Proposed, not run.** Written 12 Nov 2026, before any 2015-2017 or sub-period rate was computed.
Run once, after Jaison approves. Motivation: FINDINGS section 11, REVIEW_NOTES C0.

## Question
Is the extra marsh-edge loss on heavily oiled shore concentrated in the first years after 2010 (oil effect,
as in Challenger 2021, Zengel 2022, Turner 2016), or roughly constant through 2017 (which would point to
a lasting exposure difference between oiled and clean shore)?

## Data (already in the repository; nothing new is downloaded for part A)
`results/naip_edge_loss/cell_rates.csv`: land fraction per cell in 2010, 2015 and 2017 (NAIP), oiling class,
2 km block, exposure. Exposure and pre-spill trend from `results/p1_prespill/landsat_cell_rates.csv`.
Unit: 100 m edge cell; inference clustered by 2 km block, as in P1.

## Analyses
- **A1 (primary).** Cells present in both periods. Outcome: edge loss 2015-2017 (m/yr) from the 2015 and 2017
  land fractions, same conversion as NAIP_EDGE_LOSS_PLAN. Model: P1 check 4 (Heavy vs clean, 2 km block
  effects, water within 1 km and 250 m, fetch) plus the pre-spill Landsat trend. Report Heavy minus clean
  with 90% interval, and the same model for 2010-2015 on the same cells.
- **A2.** Difference between the two periods' Heavy coefficients, with a block bootstrap interval (2,000
  resamples, seed 20261112).
- **A3 (null baseline).** Same contrasts for Very Light and Light oiling, where no oil effect on erosion is
  expected: an excess there in 2015-2017 measures residual exposure confounding.
- **B (optional, needs new Landsat reads).** Landsat epochs 2011-2013 and 2014-2016 with the P1 method, to
  split 2010-2015 at about 2012. Only if A is inconclusive.

## Pre-specified reading
| A1 result for 2015-2017 (Heavy minus clean) | Reading | Consequence |
| --- | --- | --- |
| Interval includes zero and point estimate below half the 2010-2015 estimate | Fade: consistent with an oil effect of limited duration | Headline stays 0.85 as a 2010-2015 average; demo shows the excess as front-loaded |
| Interval excludes zero and estimate at least as large as 2010-2015 | No fade: exposure confounding likely | Headline moves to the exposure-adjusted range (0.47 to 0.62) and is labelled an upper bound on the oil effect |
| Anything else | Inconclusive | Report as such; run B |

## Limits known in advance
Two-year interval, so noisier than 2010-2015 (ASSUMED adequate; power not computed). Cells that eroded away
by 2015 drop out, which biases 2015-2017 loss downward on the fastest-eroding (Heavy) shore. NAIP 2017
classification quality was checked for 2010-2017 only. Hurricane Isaac (2012) lies in the first period.
