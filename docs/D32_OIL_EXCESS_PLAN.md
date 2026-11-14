# D32 plan: scale the composer oil excess by field studies weighted by field size (14 November 2026)

Status: committed before the literature extraction for marsh-edge erosion (group E) was returned and before
any pooled value was computed. Run once. Jaison's instruction (14 Nov): "for the oil bias scale it based on
the literature's field size".

## Question
The composer adds the Zengel et al. 2022 untreated-plot oil excess (one site, Bay Jimmy) to heavily oiled
cells: +1.88 m/yr in years 1-2 and +0.21 m/yr in years 3-8, about 0.88 m/yr averaged over years 1-5. Held-out
heavy cells are over-predicted by about 0.5 m/yr (FINDINGS_V4 26). Does a field-size-weighted estimate from all
eligible field studies give a better-calibrated excess?

## Eligible studies
Rows in `data/knowledge/literature_effects/part_E_marsh_erosion.csv` that report oiled (heavy or moderate-to-
heavy) minus reference marsh-edge erosion in m/yr, from field measurements (grade A, B or C), Deepwater Horizon
or other spills, with the number of independent sites, transects or plots. Rules fixed now:
- Zengel 2015 and 2022 count as one study (same site and plots); Zengel 2022 values are used.
- Studies based on our own NAIP/Landsat data are excluded (that is the test data).
- Remote-sensing studies of other imagery are eligible only if their unit count is reported; they are flagged.
- Abstract-only rows are eligible only if the abstract states both the difference and the unit count.
- Where one study reports several periods, the period covering years 1-5 after oiling is used for the primary
  estimate (closest match to the 2010-2015 test outcome).

## Method
1. For each study i: excess_i (oiled minus reference, m/yr) averaged over its period, and field size n_i (number
   of independent units; transects within a site count as units only if the study treats them so).
2. **Primary (field-size weighted):** pooled excess E = sum(n_i * excess_i) / sum(n_i). Spread: weighted
   between-study SD, combined with the mean within-study SE where reported; 90% range = E +/- 1.645 * SD_total
   (ASSUMED normal).
3. **Scaling:** the Zengel time shape is kept (front-loaded effect), and scaled so that its years 1-5 mean equals
   E: s = E / 0.88 (Zengel 5-year mean, from results/p3_treatment/A_prespill_adjusted.csv, computed in code);
   excess(y) = s * Zengel excess(y), with the interval scaled by the same s plus the pooled spread.
4. **Sensitivity (reported, not used):** inverse-variance random-effects (DerSimonian-Laird) if at least 3
   studies report an SE or interval; leave-one-study-out range of E.
5. If fewer than 2 eligible studies: no scaling; the Zengel excess stays and the report says so.

## Checks (run once, same data and gates as C1b and B1b)
- C1c: 2010-2015 heavy cells in held-out basins, clean-edge baseline (D27), scaled excess. Gates: coverage
  80-97%; heavy-cell bias within +/-0.25 m/yr; NOO bias not worse than C1b by more than 0.1 m/yr.
- B1c: 2010-2017 Barataria cells, same gates against B1b.
Originals (C1, C1b, B1, B1b) are kept. Results in `results/scenario_composer/` with suffix c and a summary
`summary_d32.txt`.

## Reading rules fixed now
- Passing the bias gate does not validate the literature value; it shows that the field-size-weighted average
  is consistent with NAIP in these basins.
- If E is close to the NAIP-based residual (+0.43 m/yr, FINDINGS_V4 26), that agreement is reported as
  supporting, not as independent proof (NAIP reads low against field plots, FINDINGS 9).
- If the gates fail, the scaled excess is still adopted only if its heavy bias is smaller than C1b and B1b;
  otherwise the Zengel excess stays and the dashboard keeps the bias note.
