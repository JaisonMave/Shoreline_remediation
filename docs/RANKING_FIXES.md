# Ranking Fixes

## What was wrong

The historical validation showed passive sorbents as the top choice for all six cases. Running the ranking
showed why, and four further defects.

| Defect | Cause | Fix |
| --- | --- | --- |
| Passive sorbents ranked first everywhere | Only 5 of 15 treatments had a trained model. The other 10 received a fixed suitability of 5.0, which was higher than most modelled scores. | All 9 treatments that have labels are now trained. The 6 without labels get no suitability score (`evidence="none"`) and are listed after the scored treatments. |
| Modelled scores barely varied | The Gaussian process used one length scale on unscaled inputs and had no noise term. Cross-validated R2 on the labels was about -0.07 for manual removal. | Inputs are standardised and the kernel has a noise term. R2 rose to about 0.56 (0.82 for high-pressure washing). |
| Thick oil did not affect the ranking (check E3) | The labels did not depend on oil thickness. | Natural attenuation is scored 2 points lower above 1 cm of oil. The magnitude is assumed. |
| High-pressure washing ranked the same on bedrock and sand (check E5) | The labels and the ecology score ignored the substrate, and an early return made the bedrock eligibility rule unreachable. | Labels and ecology scores now depend on the substrate, and the rule is reachable. Magnitudes are assumed. |
| Heated flushing was eligible on a sensitive marsh | It was missing from the wetland rules and fell through to a generic rule. | It is now ineligible on marsh, mudflat, peat and tundra. |

## Results

| Measure | Before | After |
| --- | --- | --- |
| SCAT sanity checks passed | 3 of 5 | 5 of 5 |
| Distinct top choices across the six historical cases | 1 | 2 |
| Top choice matches a documented method | 1 of 5 | 3 of 5 (95% interval 23% to 88%) |
| Mean best rank of a documented method (random order: 5.4) | 3.4 | 2.9 |
| Active or natural class agreement | 5 of 6 | 5 of 6, still equal to always predicting "active" |

## How to read these results

- These are not independent tests. Checks E3 and E5 pass because the rules were changed to satisfy them,
  and the historical cases come from the same sources that informed the rules.
- Suitability still comes from rule-generated labels, not field outcomes. The model is a smoothed copy of
  hand-written rules. Real labels (expert scores, then SCAT outcomes) remain the main gap.
- The two remaining misses are informative. For lightly treated Deepwater Horizon marsh the model prefers
  sorbents to natural attenuation, and for Exxon Valdez rock it prefers manual removal to pressure washing.
- `reports/comparison_report.csv` and the benchmark figures were produced before these changes and need to
  be regenerated with `python -m src.shoreline_remediation.run_benchmark`.
