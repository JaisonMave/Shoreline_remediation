# Testing Bay Jimmy remediation scenarios

## R9 protocol, revision 1

The question is whether a rule can predict the **observed manual-minus-untreated group difference at the next survey** for heavily oiled Bay Jimmy plots. This is a descriptive, within-site test. Treatment selection, trampling and shared environmental history limit causal interpretation. A proposed future cleanup, another site and the 2030/2050 horizons each require separate evidence.

### Sources and comparability

| Endpoint | Inputs available for both arms | Limitation for a future treatment model |
| --- | --- | --- |
| Total vegetation cover | GRIIDC compiled vegetation workbook, Bay Jimmy plot groups assigned from the erosion workbook. Use plot-derived means for both years. The rounded S1 Table contrast is a separate result from overlapping plots. | Manual plots have only two surveys. Later untreated surveys cannot supply treated outcomes. The multisource synthesis needs independent treatment histories and a site crosswalk before pooling. |
| Soil tPAH | Zengel 2015 S1 Table, group means in mg/kg, 0–10 cm, two sampling periods. | The reported concentration basis is unspecified. DIVER tracks relative PAH at other sampling depths with a different analyte panel and lacks station cleanup histories. A DIVER decline rate cannot identify a treatment-specific Bay Jimmy concentration change. |
| Cumulative shoreline retreat | Stake positions in the GRIIDC erosion workbook, paired by survey on the common December 2010 origin. | Seven dates follow the same plots. The aerial rates from the DSAS sheet are changes in m/year and cannot serve as held-out cumulative metres. |

The compiled vegetation worksheet contains 1,158 rows across ten source labels and has no treatment-method or intervention-date column. Joining its Bay Jimmy site IDs to the erosion workbook recovers the local plot groups. Other source labels alone cannot establish cleanup allocation. The NOAA CWV inventory in `data/external/dwh_treatment/SOURCE.md` documents the treatment-linkage gap. The literature case table `data/marsh_recovery_cases.csv` records recovery-time ranges and broad treatment classes. Neither currently provides an independent series with the same treatment, endpoint and comparator. Passive sorbents have no measured paired series in the Bay Jimmy inventory. For any other technique, consult its inventory cell and prerequisite before interpreting historical material.

### Temporal benchmark specified before running the R9 calculation

Use actual dated, overlapping group means. At each paired survey predict only the next paired survey. Report each forecast date, target, both group sizes and observed difference. Measure MAE and signed bias (prediction minus observation) in percentage points, mg/kg or metres. Never pool those units. Baselines are zero difference and persistence of the last observed difference. A simple statistical challenger fits a straight line to the prior paired differences against elapsed calendar years, including the cutoff, once at least three distinct paired dates exist. Compare all three rules on the identical eligible transitions. Report baseline-only transitions separately. Fail on duplicate group/date observations. Never fill a missing treated survey using an untreated measurement.

For this descriptive screening experiment, advance a challenger to **external testing only** if it reduces MAE against both baselines and does not increase absolute bias against either on the same test pairs. An empty evaluation yields insufficient data. Site and spill each have one level. Overlapping training windows preclude treating forecast errors as independent replicates. Report counts and individual errors instead of attaching a nominal prediction interval. Decline to fit a treatment-by-time mixed model, process-residual ML or a two-pool decay model until independent treatment groups can identify the parameters. Retain the existing P-RET-1 protocol for untreated shoreline retreat.

### Process model and admission

For the worked case the untreated comparator maps to `no_cleanup` (zero removal and disturbance); the similarly named simulator key `natural_attenuation` carries nonzero coefficients. Manual removal and passive sorbents have explicit parameter keys with assumed coefficients. Reject unknown techniques before any research call to `simulate_transect`, which otherwise substitutes `no_cleanup`. Screening eligibility and the existence of a parameter key establish neither efficacy nor model admission. No endpoint transfer from simulated surface oil mass to soil mg/kg, total cover or cumulative retreat has been validated here.

| Existing evaluation | Metric and comparator | Recorded verdict |
| --- | --- | --- |
| F5, 61 held-out stations, 130 station/campaign cells | Mean absolute error on log relative PAH, prior 0.7946, calibrated process 0.7748, empirical decline 0.7499 | Failed the empirical comparison. See `models/process_model_v2.json`. |
| P-RET-1, same nine untreated plots | C1 2.246 m vs B1 2.742 m on ten pairs; C2 3.696 m vs B1 1.883 m on six | Neither passed. See `docs/PROJECTION_RETREAT_PROTOCOL.md` for lead times and uncertainty. |
| D32 oil-excess scaling | Heavy-class bias improved, but the full set of gates failed. | Keep experimental. See `results/scenario_composer/summary_d32.txt`. |

### What would enable an independent test

Acquire a distinct, documented marsh site with heavily oiled untreated plots and plots receiving the **same technique**. Request spill and site IDs, coordinates, stable plot IDs, treatment start/end, intensity, pre-treatment oiling, season, access, trampling and co-interventions. Request pretreatment and repeated follow-up measurements in both arms with exact survey windows. For cover obtain total plot cover and method. For soil obtain core depth, analyte list, concentration basis, censoring and laboratory QA. For retreat obtain a common datum, transects, baseline positions and storms or shoreline loss. Preserve missing plots and reasons.

Freeze external sites and evaluation horizons before calibration. Split by whole sites or spills for transfer and by time within training data. Fit preprocessing and hyperparameters inside training folds. For a hybrid model train residuals only on out-of-fold process predictions. Evaluate both arm-level errors and paired-difference errors, with uncertainty clustered by independent site when enough sites exist. Agree the minimum useful gain in endpoint units, acceptable bias and interval coverage/width with the intended users before looking at external results. Scientific promotion additionally requires independent evidence for the target population, comparator and lead time.

### R9 results on the current checkout

Run `python -m validation.remediation_benchmark` from the repository root. The JSON includes the input file hashes, each cutoff and target, both sample sizes, predictions, signed errors and verdicts. All target observations come from the same site that supplied the earlier exploratory fits.

| Outcome | Evaluation | Zero-difference MAE | Persistence MAE | Linear trend MAE | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| Cover, percentage points | One transition, Sep 2011 to Sep 2012 | 33.467 | 18.222 | — | Only one training date at the cutoff. |
| Soil tPAH, mg/kg | One transition, Jul–Aug 2011 to Sep 2012 | 11.000 | 29.000 | — | Only one training date at the cutoff. |
| Cumulative retreat, m | Four next-survey predictions at matched cutoffs from Sep 2012 through Sep 2015 | 0.237 | 0.227 | 0.285 | The trend reduced signed bias but increased absolute error against both benchmarks. |

For retreat the signed biases were +0.237, +0.112 and +0.006 m respectively. Two earlier transitions have baseline predictions only and are listed separately in the output. Cover here uses plot-level means. The published rounded year-two contrast of +34 percentage points remains the historical field result. Across all three endpoints, the available evidence supports retaining the assumption-labelled futures.
