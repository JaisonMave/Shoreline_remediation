# Process Model Audit and Marsh Recovery Model

## Verdict

The process models are not sufficient to predict treatment impacts. The default engine
(`shoreline_transport.py`) had a mass-balance defect, ignores several scenario inputs, and ranks the most
aggressive treatments best on sensitive marsh, which contradicts published marsh case histories. No
open-source model was found that covers oil fate on the shoreline together with treatment effects.

A data-driven recovery model was built from 63 published marsh cases. It does not yet predict held-out
spills better than the overall base rate, so it should not be used to rank treatments. The limiting factor
is outcome data, not the choice of model.

## The two engines

- `process_model.py`: six oil-mass compartments with first-order losses, adapted from the DHI open-water
  model. Used only when `engine` is not `"transport"`.
- `shoreline_transport.py`: a 40-cell cross-shore dispersion and reaction model with first-order and Monod
  terms. This is the default for the dashboard. Its own parameter table marks 11 of 19 entries as ASSUMED,
  including every treatment removal rate.

## Findings (default engine)

| Finding | Evidence |
| --- | --- |
| Mass was not conserved | Heavy oil on a sand beach with no cleanup rose to 117% of its initial mass by day 30. With every sink switched off, dispersion alone added 49% in 30 days. Cause: `d_eff * laplacian(field)` is not conservative where `d_eff` changes between zones. Fixed in this change. |
| Inputs with no effect on oil fate | `oil_thickness`, `penetration_depth_cm`, `subsurface_oil`, `season` and `shoreline_sensitivity` leave residual oil at day 365 unchanged (49.7% in every case tested). |
| Shorelines not distinguished | Sand beach, mixed sediment and cobble give identical results. |
| Treatment effect ignores context | Each treatment is one fixed removal rate, whatever the shoreline or oil. |
| Treatment harm is negligible | On a heavily oiled, very sensitive marsh, mechanical removal gives the best habitat index at day 365 (0.99) and no cleanup the worst (0.71). The disturbance term has a weight of at most 0.3 and fades with a 90-day time constant. |
| Habitat recovery has no dynamics | It is an algebraic function of oil removed, so it cannot lag, stall or reverse. |

The NOAA marsh report states the opposite of the fifth finding: recovery is shortest with less-intensive or
no treatment, and it lists overly aggressive treatment among the conditions with the longest recovery.

## Open-source models reviewed

| Model | Licence | What it covers | Use here |
| --- | --- | --- | --- |
| PyGNOME (NOAA) | Public domain | Transport and weathering at sea. Checked in the source: beached oil only has a refloat half-life, biodegradation is formulated for dispersed droplets, and cleanup covers at-sea options such as skimming and burning. | Good upstream source for how much oil strands, and in what state. Not a shoreline fate model. Could not be installed in the build environment, so it is not wired in. |
| OpenDrift / OpenOil | GPL-2 | Drift and weathering at sea, using NOAA oil data. Biodegradation is defined for droplets and slicks. | Same role as PyGNOME. Copying its code would place this project under the GPL. |
| BIOMARUN / MARUN (Geng and Boufadel) | No public code found | Subsurface flow, oxygen, nutrients and biodegradation in tidal beaches. | The right physics for beaches, from the same family of models that `shoreline_transport.py` cites for its Monod terms. Not available to incorporate. |
| Nixon and Michel (2015), Environ. Sci. Technol. 49(7) | Paper only | Boosted tree models predicting the probability of finding subsurface Exxon Valdez oil. | The closest precedent for machine learning on shoreline oil persistence. Its pit-survey data would be the best training set for a beach persistence model. |
| BSEE project 1165 (2025) | Report | An updated shoreline oil-loading dataset from about 60 documents and 13 spills. | Only the abstract was read. Worth obtaining for holding capacities by shoreline type. |

## What changed

- `shoreline_transport.py`: dispersion is now in flux form with harmonic-mean face coefficients. Mass is
  conserved. All trajectories change, so earlier outputs of this engine are superseded
  (`MODEL_VERSION = adr_shoreline_transport_v1_1`).
- `data/marsh_recovery_cases.csv`: 71 rows (63 included) transcribed from Appendices A-D of NOAA's
  "Oil Spills in Marshes: Planning and Response Considerations".
- `marsh_recovery_model.py`: interval-censored log-normal regression of recovery time on oil group, oiling
  degree, treatment class and study type.
- `validation/recovery_validation.py`: leave-one-spill-out validation against a no-predictor baseline and a
  random forest. Results are written to `results/recovery/`.
- `tests/test_impact_models.py`: mass-balance, data and estimator tests (`python -m pytest tests`).

## Marsh recovery model: result

Out of sample, the full model is no better than a model with no predictors: the mean gain in held-out log
probability is 0.001 per case (standard error 0.072). The result holds for looser and tighter priors, for
unflagged rows only, and for spills only. A random forest on the same features is slightly closer on point
predictions but needs imputed values for the bounds.

What the data do support:

- A base rate: median recovery of about 2 years, with 80% of cases between about 0.4 and 9.4 years.
- In-sample associations that match the report's narrative: light oiling recovers faster (time ratio 0.34,
  90% interval 0.17 to 0.70) and intensive treatment slower (1.49, interval 0.69 to 2.76, three cases).
- Burn cases recover faster (0.45, interval 0.25 to 0.80). This is not evidence that burning speeds
  recovery: burns were chosen for small spills in conditions that favoured burning.

## Data caveats

- The table was read from the PDF by an automated reader. Recovery values for Appendix D and for 13 rows of
  Appendices A-C were read twice and agreed. Check every row against the report before publishing.
- `oil_group`, `oiling` and `treatment_class` are codings added here. The source wording is kept in the
  `_as_written` columns so the coding can be revised.
- Eight rows are excluded, each with a reason in `flags`, mostly because treatment was unspecified.
- Many bounds were set after the outcome was seen ("<2 yr"), which tends to overstate the spread.
- Thick or buried oil and sheltered settings, which the report names as drivers of long recovery, are not
  in the model: the table states oil thickness for only a few cases and does not record exposure.

## Second round: season, latitude and wetland type

Three drivers the report names were added, each coded from facts fixed before the outcome was known:

- `dormant_season`: the month of the spill or burn printed in the table (October to March in the northern
  hemisphere, reversed in the south).
- `abs_latitude_ge_45`: the site lies at or beyond 45 degrees latitude. Latitudes are approximate and were
  assigned from the place names; check them.
- `habitat_class`: salt or non-salt wetland, taken only from explicit wording in the table.

The report's own lists of "longest recovery" examples were not used. Those examples were chosen because
they recovered slowly, so coding features from them would leak the outcome into the predictors and produce
skill that is not real.

The model and features were fixed before the validation was run, and it was run once. Result: still no
gain over the no-predictor baseline (-0.004 per case, standard error 0.103). In-sample, high-latitude sites
recover more slowly (time ratio 1.83, 90% interval 0.94 to 3.57) and non-salt wetlands faster (0.49,
interval 0.24 to 0.76). Dormant-season oiling shows no clear effect (1.36, interval 0.77 to 2.22), where
the report expects faster recovery.

Conclusion: with about 60 cases, the published case table cannot support a predictive model, whatever
predictors are coded. Further feature work on this table is not worthwhile. The next gain has to come from
more outcome data.

## What would let a data-driven model work

1. Segment-level SCAT and treatment records for Deepwater Horizon, which turn one spill into thousands of
   treated and untreated segments.
2. The Exxon Valdez pit-survey data used by Nixon and Michel, for beaches.
3. Satellite recovery series (NDVI, shoreline position) as a consistent outcome measure across spills.
