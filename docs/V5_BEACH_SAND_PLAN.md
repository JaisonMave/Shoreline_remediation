# V5 sand-beach persistence model: analysis plan (D39)

Written 14 Nov 2026, BEFORE any outcome was tabulated against any predictor. Modules 1 (data), 4 (recovery
prediction) and 5 (generalisation). Owner decision 14 Nov 2026: "sand beach with data". Outcome definition and
gates were set by the orchestrator and are copied verbatim in section 7. This plan is fixed; the gated analysis
(`python -m validation.v5_beach_sand`) is run once.

## 1. Data

- Deepwater Horizon SCAT layer 18613 "SCAT All zones, Mobile" (NCEI Accession 0163818, file
  `SCAT_AllZones_Mobile_2014_0927Sorted`), Alabama, Mississippi and the Florida panhandle, 5 May 2010 to 18 June 2013.
  Download: `bash scripts/download_scat_mobile.sh`. Provenance: `data/external/scat_dwh_mobile/SOURCE.md`.
- Derived, committed table: `python scripts/build_beach_series.py` ->
  `data/external/scat_dwh_mobile/beach_series.csv` (one row per segment), `beach_visits.csv` (one row per
  segment-visit), `counts_check.json`.

## 2. Series definition (deviation from the brief, explained)

The brief assumed a "segment-zone series". The NCEI metadata (layer 18613, Process_Step) say: "The ID assigned to
zones on each survey date has no relationship to the IDs assigned to zones from previous survey dates." A zone
letter therefore cannot be followed through time, and segment-zone "series" would join unrelated pieces of beach.
The unit followed through time is the **SCAT segment** (median about 500 m of shoreline).

- **Visit** = one segment on one survey date (all zones of that date together; records with category
  "Undefined" are ignored; a date with only "Undefined" records is dropped).
- **Oiled visit**: at least one zone has an oiling category other than NOO (field `OilCatCode`).
- **Clear visit**: every zone is NOO ("No oil observed") and the NOO zones cover at least 50% of the segment
  length (ASSUMED threshold, to avoid counting a small partial survey as clear). An all-NOO visit covering less
  is "partial clear" and is ignored in the primary analysis (sensitivity: counted as clear).
- **ESI 3A segment**: at least 80% (ASSUMED) of the segment's ESI-coded zone length is ESI 3A (fine-to-medium
  sand beach). The segment level is needed because 3,858 NOO records have no ESI code, so filtering records by
  ESI would silently delete clear visits.
- **ESI 4 (coarse sand)**: 9 segments meet the 80% rule and none was ever oiled, so ESI 4 is NOT included (the
  data do not allow it).
- **Series** = an ESI 3A segment with at least one oiled visit and at least one later visit. Time zero = its first
  oiled visit.

## 3. Outcome: persistence of visible oil

T = days from the first oiled visit to the first clear visit (the first survey recorded as No Oil Observed).
Persistence at horizon h = P(T > h), for h = 90, 180, 365 and 730 days.

- **Interval-censored**: we never see the day the oil disappeared, only that it was there at one visit and gone at
  the next, so T is known to lie between the last oiled visit (L) and the first clear visit (R).
- **Right-censored**: a segment never recorded clear is known only to have stayed oiled at least until its last
  visit (L), with no upper limit.
- Re-oiling (an oiled visit after the first clear visit) is secondary and descriptive only.

## 4. Eligible predictors (all from the first oiled visit; state and number of visits are NOT predictors)

Taken from the most heavily oiled zone of the first oiled visit (highest SCAT `oil_order`, then longest), except
the tarball count, which is summed over oiled zones.

| Term | Definition | Coding |
|---|---|---|
| first oiling category group | `OilCatCode` grouped: surface_light (Very_Light, Light; reference), surface_mod_heavy (Moderate, Heavy), tb_neg_light (Neg_TB, Light_TB), tb_mod_heavy (Mod_TB, Heavy_TB) | 3 dummies |
| tidal zone | `TidalZone` of top zone: UI (reference; also the 6 missing), SU, MI+LI | 2 dummies |
| surface oil thickness | `SOThicknes`: thick (PO, CV), thin (CT, ST, FL), none (reference) | 2 dummies |
| surface oil distribution | `SODistro` (%) / 100 | standardised |
| tarballs | log(1 + summed `TBCount`) | standardised |
| timing | log(days from 20 April 2010 to first oiled visit) | standardised |
| exposure proxy | share of 7 rays (bearings 120-240 deg, 200 m to 20 km, ASSUMED) from the segment midpoint that cross no other SCAT shoreline; derived from geometry only | standardised |

Dropped before any outcome analysis: alongshore oiled fraction (at least 75% of series equal 1, little
information); tarball area (`TBArea` has mixed units: m2, m, "Segment", "Zone"); tarball type (mostly missing);
ESI (constant within the 3A scope).

## 5. Models

**Primary model (one only): piecewise-exponential proportional-hazards model with interval censoring.** The
hazard of clearing is constant within pieces 0-30, 30-90, 90-180, 180-365, 365-730 and >730 days (6 baseline
parameters) and is multiplied by exp(x·beta) for the terms in section 4 (11 coefficients, log hazard ratios).
Persistence S(t|x) = exp(-exp(x·beta) * sum_k exp(alpha_k) * time spent in piece k up to t). Likelihood:
S(L) - S(R) for interval-censored series, S(L) for right-censored series. Fitted by maximum likelihood (scipy
L-BFGS, analytic gradient) with a small ridge penalty 0.01*|beta|^2 on standardised terms (ASSUMED, for numerical
stability only). Standardisation constants come from the training data of each fold.

**Baseline (fixed by the orchestrator)**: Kaplan-Meier-type persistence curve by first-observed oiling category
group, estimated from the training states only. Because the data are interval-censored, the Kaplan-Meier
generalisation used is the Turnbull non-parametric estimator (self-consistency EM on the grid of all observed
L and R values; probability mass spread uniformly within each grid interval when reading S(h)). If a category
group has fewer than 20 training series, the pooled training curve is used for it.

**Secondary, not gated**: XGBoost accelerated-failure-time model (`survival:aft`, normal distribution, scale 1.0,
depth 3, learning rate 0.05, 300 rounds; all ASSUMED defaults, not tuned), same predictors and folds.

## 6. Hold-out, metrics, uncertainty

- **Primary hold-out**: leave one state out (Alabama, Mississippi, Florida). Model and baseline are fitted on the
  other two states only.
- **Brier score at horizon h, known-status version**: a series counts at h only if its status at h is known from
  the visits (cleared by h: R <= h; still oiled at h: L >= h). Series with L < h < R are not scored at h; the
  share not scored is reported. Brier = mean of (predicted S(h) - observed 0/1)^2.
- **Integrated Brier score (IBS)** = the simple average of the Brier scores at 90, 180, 365 and 730 days.
  "Pooled over all three" = Brier computed over all held-out predictions together (each series predicted by the
  fold that held its state out), then averaged over horizons.
- **Observed state persistence** at h = Turnbull estimate from the held-out state's own series.
  **Predicted state persistence** = mean of the model's S(h|x) over that state's series.
- **90% interval for state persistence**: 200 bootstrap refits that resample whole training segments (seed 20261114);
  in each, every held-out series draws its 0/1 outcome at h from its predicted S(h), and the state mean of these
  draws is taken; the interval is the 5th to 95th percentile. (This covers parameter uncertainty and the
  finite number of segments in the state.)
- **Calibration** at each horizon: held-out series in 5 bins of predicted S(h); mean predicted vs Turnbull
  observed per bin; for model and baseline.
- **Interval coverage**: whether the 90% interval contains the observed persistence, per state and horizon.
- **Secondary hold-out (descriptive)**: leave one county out (state+county; counties with at least 40 series held
  out in turn; others always train), IBS model vs baseline and 365-day persistence with interval.
- **Sensitivity, informative visiting**: repeat the leave-one-state-out evaluation on series whose largest gap
  between visits (time zero to clearing or censoring) is at most 60 days (ASSUMED). Report IBS model vs
  baseline and observed 365-day persistence by state, beside the full-data results. Also report how many series
  change outcome if "partial clear" visits are counted as clear.
- **Re-oiling (descriptive)**: among series that cleared and had at least one later visit, share later oiled,
  days to re-oiling, by state and first category group.

## 7. Gates (verbatim from the orchestrator; fixed before the run)

Gate B-1: "Holding out each state in turn (Alabama, Mississippi, Florida), the model's integrated Brier score over 90, 180, 365 and 730 days is lower than the baseline's in at least two of the three held-out states and pooled over all three."

Gate B-2: "In each held-out state, predicted and observed persistence at 365 days differ by no more than 10 percentage points, and the 90% interval for state-level persistence at 365 days contains the observed value."

Baseline (fixed): the Kaplan-Meier-type persistence curve by first-observed oiling category, estimated from the training states only (a curve that uses no predictors beyond the starting category).

Consequences fixed now: the declared state is never "validated". Both gates pass -> "experimental (gates passed,
awaiting owner review)". Otherwise "experimental (gate failed: ...)". If B-1 fails (the model does not beat the
baseline), the packaged prediction falls back to the baseline curve (fitted on all three states) and says so.
No tuning after the run.

## 8. Packaging

`models/beach_sand_persistence_v1.json` (card) and `src/shoreline_remediation/beach_model.py`: the final model is
refitted on all three states; 200 bootstrap refits resampling whole segments give the median and 90% interval of
the persistence curve at the four horizons. Scope flags: outside training range, ESI not 3A, state unseen.

## 9. Required caveats

1. Treatment is not recorded per segment and most oiled sand beach was treated (Michel et al. 2017 report roughly
   683 of 965 km with documented treatment), so this is persistence under the response as it was carried out,
   NOT natural recovery, and it cannot rank treatments.
2. Surveys were scheduled by response priority, not at random (informative visiting). The sensitivity check in
   section 6 addresses this partly; it cannot remove it.
3. SCAT oiling is visible surface oil and a cleanup endpoint, not chemical or ecological recovery; buried oil is
   not captured (and was documented at depth on these beaches).
4. One spill, three states. Transfer to other spills, oils or coasts is untested.
5. Disclosure: the orchestrator and an earlier agent had seen record counts, but not outcomes, before the gates
   were set. Before writing this plan, this agent (a) reproduced those counts, (b) saw overall visit status
   counts (14,341 oiled, 14,284 clear, 3 partial-clear visits, all segments together), and (c) looked at the
   distributions of the predictors by state and of number of visits and median visit gap by state (the median
   gap was computed up to clearing, so it carries some outcome information, but it was not tabulated against
   any predictor). No persistence or clearing time was tabulated against any predictor or state.
6. The exposure proxy uses only the SCAT-surveyed shoreline; unsurveyed shorelines (e.g. parts of bays) look
   "open", so it is a rough proxy.
