# P5 plan: demo dashboard (fixed 11 November 2026, before the worked example's outcomes were looked at)

Module 6 (scenarios and decision support) and 7 (software), drawing on modules 3-5. Decisions D9 and D11
(approved by Jaison) set what the demo shows. This plan fixes the deployed model, the interval, the flags and
the worked example before any of them is computed. P5 is engineering, not a new analysis: it packages results
already validated in P1-P3 and adds no new test of them.

## 1. What the demo must show (roadmap P5)

A new "Site evidence (real data)" view, separate from the existing rule-and-synthetic scenario view:

1. A map of Louisiana salt-marsh edge cells (P2 cells) coloured by SCAT maximum oiling, and a site picker
   (basin, oiling class, SCAT segment, cell), plus a "new site" option where exposure values are typed in.
2. The site's inputs: exposure, pre-spill trend, oiling, basin, and where each came from.
3. Rule screening of cleanup options for this site (existing FAST-like rules), with the scenario inputs it
   implies, each mapping marked ASSUMED where it is assumed.
4. Expected marsh-edge loss at this site with a 90% interval (D9), and the heavy-oiling uplift as a range,
   not added in.
5. Per cleanup option, the change in edge erosion against natural recovery with a 90% interval for years 0-2
   and years 2-8 (Zengel et al. 2022, D11), and the change in vegetation cover at year 2 (Zengel et al. 2015).
6. Flags: out of scope (no prediction shown) and extrapolation (prediction shown with a warning).
7. A worked Barataria example selected by the rule in section 5.

## 2. Deployed edge-loss model (p5-edge-loss-v1)

- **Model:** P2's M1, ordinary least squares of NAIP edge-loss rate 2010-2015 (m/yr) on open water within 1 km,
  open water within 250 m, log(mean fetch + 16 m) and the cell's pre-spill Landsat trend (1999-2008). No oiling
  term, because P2 found oiling adds no cell-level accuracy over exposure (D9).
- **Training data:** every cell that passed P2's filters in Terrebonne, Barataria and Breton (same code:
  `validation.p2_basin_holdout.load_basin`). Fitted once on all three.
- **Interval:** the 5th and 95th percentiles of leave-one-basin-out residuals of M1 (each basin predicted by a
  model fitted on the other two), added to the full-data prediction. Same method as P2's intervals, which
  covered 89% of held-out cells. Coverage of this interval is not re-tested here (it would be in-sample).
- **Uplift:** the heavy-oiling coefficient from P2's training folds, 0.34 to 0.83 m/yr (D9), shown beside the
  prediction for cells in the Heavy class, with P1's headline 0.85 (0.49 to 1.22) for context.
- **Measurement note (D11):** NAIP rates read about 1.2 m/yr below field erosion (P3 analysis C); shown with
  every absolute rate.
- **Artefact:** `models/p5_edge_loss_v1.json` holds coefficients, interval offsets, training ranges, training
  file checksums, date and references. The dashboard reads it with numpy only; `scripts/build_p5_demo.py`
  rebuilds it.

## 3. Treatment evidence and the mapping to the tool's treatments (D13, proposed)

| Tool treatment | Evidence group | Source |
| --- | --- | --- |
| natural_attenuation | untreated (natural recovery), the baseline | Zengel 2015, 2022 |
| manual_removal | manual treatment | Zengel 2015, 2022 |
| mechanical_removal | mechanical treatment | Zengel 2015, 2022 |
| (restoration add-on) | mechanical + planting | Zengel 2022 (planting randomized against mechanical) |
| all others | none: "no outcome evidence" | - |

Shown only for Heavy cells in salt marsh; elsewhere the column says "outside evidence scope". The evidence
is not combined with the site prediction into one number, because that would assume the Bay Jimmy contrasts
apply at every site and in every period. The rule screening is not overridden by the evidence; where they
disagree the demo shows both.

## 4. Flags (pure function, tested)

Out of scope, no prediction shown:
- habitat other than ESI 10A salt marsh;
- birdfoot delta (active river delta and plume, excluded in P2);
- cells removed because land/water classification is unreliable there (P2 invalid quadrants), or because the
  cell failed image-quality, NAIP/Landsat agreement or Landsat validity filters;
- new site with any input missing.

Extrapolation, prediction shown with a warning:
- any input outside the 1st-99th percentile of the training cells;
- new site outside the training cells' latitude/longitude box.

Always shown: one spill (Deepwater Horizon) and one oil; associations, not proven causes; NAIP reads low.

## 5. Worked example (selection rule fixed before looking)

The Heavy-class Barataria cell in the training panel nearest to the centroid of the Zengel et al. (2022)
field plots (GRIIDC sheet "GIS field erosion points"), so the site and the treatment evidence come from the
same marsh. Written up in `docs/P5_WORKED_EXAMPLE.md` by `scripts/build_p5_demo.py` with whatever the numbers
are, including the held-out P2 prediction and the observed NAIP rate for that cell.

## 6. Other changes

- The existing "ML model evidence" tab is relabelled as a method test on synthetic data, and a banner says the
  main ranking and recovery curves come from rules and synthetic data (REVIEW_NOTES A4).
- The oil search offers spill oils by default (crude, condensate, tight oil, fuel oils, bitumen and blends);
  other products need a tick box (REVIEW_NOTES B0).

## 7. Done when

- `streamlit run src/shoreline_remediation/dashboard.py` works from a clean install of `requirements.txt`
  (plus `pydeck`, which Streamlit installs), checked with Streamlit's AppTest in tests.
- Tests cover the model artefact (reproduces P2's M1 on its own data), the flags, the treatment table and the
  oil filter; all tests pass.
- Jaison tests it as a user (his part of P5).
