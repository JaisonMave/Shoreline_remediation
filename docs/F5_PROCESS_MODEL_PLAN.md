# F5 plan: process model priors, sensitivity and calibration (D18 steps 1-3)

Written 14 November 2026, before any Sobol index, Monte Carlo interval or calibration error was computed.
Screening trajectories of the current engine (optional arguments omitted) were recorded only so tests can
check that the default path is unchanged. They are not a gated result.

Question: after the 19 transport parameters have explicit priors, which of them actually move residual
surface oil on a heavily oiled marsh with no cleanup, and does updating only those parameters against
DIVER soil PAH improve held-out log relative PAH enough to leave the illustrative label?

Engine: `shoreline_transport.simulate_transect` (`MODEL_VERSION` stays `adr_shoreline_transport_v1_1`).
No other model is edited except a keyword forward on `simulate_selected_scenario`.

## Step 1 — Priors and the three ignored inputs

Table: `data/knowledge/process_parameter_priors.csv`. One row for every name in `PARAMETER_TABLE`
(biodegradation base rate has two rows, labile and recalcitrant). Two ODE coefficients that are hardcoded
and absent from that table (`edge_export_scale`, `k_up_per_day`) are extra rows, labelled as such. Two
scenario inputs (`penetration_depth_cm`, `season_temperature_c`) are extra rows used only in the
sensitivity sample.

Each row has a distribution (`lognormal`, `uniform`, `normal` or `fixed`), bounds, and either a citation
with a DOI or the words `ASSUMED, wide`. No DIVER half-life is used as a prior. That series is the
calibration data.

Literature brackets, magnitudes only (the Venosa table stores a negative slope):

- C003 control, hopane-normalised aromatics, sand beach: 0.021 /day (Venosa et al. 1996, DOI 10.1021/es950754r).
- D005, beach sediment-oil agglomerate PAH: 0.0029 /day (Bociu et al. 2019, DOI 10.1038/s41598-019-46301-w).

Labile biodegradation median = geometric mean of those two magnitudes, 0.00780 /day. That is a beach
bracket, not a marsh measurement. The lognormal is wide (`sigma_ln` 1.0) and is labelled so.

Sourced ranges used as stated, not widened:

- K_N uniform 0.1 to 1.0 mg/L (Geng et al. 2021, DOI 10.1016/j.coche.2021.100751).
- Marsh spreading uniform 10 to 15 m, heavy-oil thickness uniform 20 to 30 mm, endpoint fixed at 10 mm
  (Michel et al. 2013, DOI 10.1371/journal.pone.0065087).
- Surface-oil depth fixed at 5 cm (NOAA Shoreline Assessment Manual, Appendix I, supplied; no DOI).

Optional arguments on `simulate_transect` and `simulate_selected_scenario`, all default `None`:

| Argument | When `None` | When set |
| --- | --- | --- |
| `oil_thickness` (mm) | Mass from `scenario.oil_thickness`. No rate scaling. | Same mass rule, plus surface evaporation and surface labile biodegradation scaled by `clip(10 / thickness_mm, 0.2, 5)`. The 10 mm reference is ASSUMED so a thin film keeps the screening rates and thicker oil loses a smaller fraction per day. |
| `penetration_depth_cm` | Subsurface starts at zero. | If depth is at most 5 cm (the NOAA surface definition), no split. If deeper, the fraction `(depth - 5) / depth` starts in the subsurface. Mass is conserved. |
| `season` | Q10 uses `scenario.temperature_c`. `scenario.season` stays ignored. | Temperature set-point, ASSUMED: winter 12, spring 20, summer 28, fall 22 °C. Biodegradation scales with the existing Q10. |
| `parameter_overrides` | Every coefficient stays at the screening literal. | Named replacements or multipliers. This is how the Monte Carlo reaches the priors. |

`parameter_overrides` is not a new physical input. It is the switch that keeps the screening numbers byte-for-byte unless a prior draw is supplied.

## Step 2 — Monte Carlo and Sobol (run once)

Scenario, fixed before the run: marsh, heavy oil, `no_cleanup`, coverage 80% (ASSUMED), thickness 25 mm
(midpoint of the Michel 2-3 cm range) with thickness scaling on, penetration 2 cm (within the 5 cm surface
definition, so the split is zero), wave `low`, tide `low`, permeability `low`, temperature 22 °C.
`low` / `low` is an ASSUMED reading of a sheltered marsh platform (Michel: tidal range about 0.5 m).
Accessibility does not enter `no_cleanup`.

Outputs: residual surface oil as a fraction of initial total oil, at 365 and 730 days
(`surface_oil_mass_kg / residual_oil_kg` at day 0).

Sampled parameters: every prior row with `sampled_in_sobol = yes` (rate multipliers, the sourced K_N,
spreading, thickness, and the two scenario inputs). Not sampled, and why:

- Biodegradation form, oxygen-limit statement, endpoint, surface-oil definition: not numbers in the ODE.
- Tidal range in metres: the ODE uses a categorical factor, already set to `low` for this scenario.
- Treatment rate and duration: identically zero for `no_cleanup`.

Method, fixed: Saltelli matrices from one scrambled Sobol sequence of dimension `2k`, N = 128 (a power of
two), seed 20261114. First-order index is the Saltelli et al. (2010) estimator
`mean(f(B) * (f(AB_i) - f(A))) / Var`. Total-order index is the Jansen (1999) estimator
`mean((f(A) - f(AB_i))^2) / (2 Var)`. Variance is the pooled sample variance of f(A) and f(B).
90% intervals on the indices are a bootstrap of the N rows (200 resamples, seed 20261114). Inverse CDFs
are the untruncated lognormal or uniform, then clipped to the prior bounds.

Monte Carlo intervals are a separate draw of 400 vectors, seed 20261115, same inverse CDFs. Report the
5th, 50th and 95th percentiles. This draw is not reused as the Saltelli sample.

Influential parameters: among rows with `calibration_group = rate`, rank by the mean total-order index
across the two outputs. Keep four if the fourth is at least 0.05; otherwise keep three. Scenario inputs
are named if their mean total-order index exceeds every rate coefficient, but they are conditions, not
calibration parameters.

Gate 2: `results/f5_process/mc_intervals.csv` has both horizons, and `summary.txt` names the three or four
rate coefficients. No numeric threshold on the width.

## Step 3 — Calibration (run once, after step 2, no refit)

Data: `results/pah_decline/station_campaign.csv` only. Stations with `oil_class` heavy or moderate, whole
stations, never rows. A target cell is a later campaign at the same station and depth class as an earlier
positive PAH sum. Time is years since 20 April 2010, the same origin as `diver_soil.T0`.

Predictor: log residual oil fraction of the process model, total surface plus subsurface, relative to the
model fraction at the station's first campaign. Heavy and moderate use one shared parameter vector and
differ only by the fixed scenario: heavy as in step 2; moderate is coverage 40% and thickness 10 mm, both
ASSUMED, everything else identical. The model is integrated to 4 years at 30-day steps and linearly
interpolated. Fractions below 1e-4 are clipped before the ratio.

Likelihood: Gaussian on the log relative PAH, sd 0.75 (ASSUMED, near the published M1 mean absolute error
of 0.59 ln units in `results/pah_decline/summary.txt`; not fitted). Each station contributes its mean
squared error, so a station with more campaigns does not weigh more. Importance sample: 1,500 draws from
the priors of the influential parameters only, seed 20261114. Every other coefficient stays at the
screening literal. Weights are recomputed on each training fold from the same draws (the trajectories do
not depend on the fold).

Hold-out: 5-fold by station, stations sorted then permuted, seed 20261114. Prediction is the weighted
median of log relative oil. Station error is the mean absolute error of that prediction. The reported
error is the unweighted mean of station errors.

Baselines, same cells, same station average:

- (a) Uncalibrated priors: the same 1,500 draws with equal weights (prior predictive median).
- (b) Empirical first-order curve already in `results/pah_decline/by_oiling_class.csv`, outcome `PAH sum`,
  `stratum_type = oiling_class`: log relative PAH = `-k * (t - t_first)`, with the published k
  (heavy 0.43016 /yr, moderate 0.37798 /yr). That k was fitted with the test stations in the sample, so
  the baseline is slightly favoured. It is not refit.

Posterior file: one importance sample on all heavy and moderate stations (descriptive; not used for the
held-out error). A parameter differs from its prior if its 90% interval is at most 70% as wide, or its
median lies outside the prior 25th-75th percentile. Effective sample size is reported and is not a gate.

Gate 3, all three required: held-out MAE of the calibrated model is strictly below (a) and strictly below
(b), and at least one posterior differs from its prior. If any part fails, the model card status is
`experimental`, the label is `illustrative`, and `decision_path` is false. It is not wired into the
dashboard either way. A pass sets status `validated` and `decision_path` true on the card only.

## What is written

`results/f5_process/`: `sobol.csv`, `mc_intervals.csv`, `calibration_cv.csv`, `posterior.csv`,
`summary.txt`, and the plots the script saves. Model card: `models/process_model_v2.json`.
Tests: `tests/test_f5_process.py` (priors complete; default arguments match the pre-change series;
Saltelli/Jansen indices on `Y = 2 X1 + 0.5 X2`).

The gated script runs step 2 and then step 3 once. A crash before a result file is a defect, not a failed
gate. A failed gate is not rerun.
