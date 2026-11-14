# Review notes (critical comments to keep in view)

Running list of scientific and technical concerns raised during development, so they are not lost between
sessions. Each note says where it bites and what would resolve it. Add new notes at the top of a section;
mark resolved notes rather than deleting them. Decisions referred to are in `docs/ROADMAP.md`.

Last updated 14 November 2026 (v3 review; fixes planned in `docs/V4_PROGRAMME_PLAN.md`).

## R. Findings of the v3 review (14 Nov 2026; open until the V4 item named is done)

1. **Ineligible treatments outrank eligible ones** (V4 R1). Scored-but-ineligible options keep utility
   0.4*E and are sorted before unscored options.
2. **Passive sorbents rank first for thick heavy oil on marsh and sand** (V4 R2). Skewed label noise and a
   fixed ecology score; checks E3 and E5 pass because rules were edited to pass them.
3. **Oil effect probably counted twice in the composer** (V4 R3). Baseline M1 was fitted on data including
   heavy cells; the Zengel excess is added on top. Heavy cells over-predicted by +0.53 (B1) and about +0.6
   m/yr (C1); clean cells +0.06.
4. **Two views give different absolute numbers for the same cell** (V4 R4): 1.42 m/yr vs about 3.4 m/yr.
5. **"Distinguished" restates the Zengel interval** and is the same at every heavy site (V4 R5).
6. **AI-written expert review shown as expert** (V4 R6): D23, D24 approved by the orchestrator.
7. **Smaller:** singular cluster covariance in the edge-loss model (181 parameters, 176 clusters);
   vegetation year-2 spike; vegetation curve used where it is worse than baseline; PAH replicate rule biased
   towards the median; worked-example headline in-sample; stale benchmark reports (V4 R7).
8. **Repository:** tracked `.pyc` files; public remote with DWH-derived tables and AI-written reviews
   (V4 R8, D29).

## A. Claims we can and cannot make to leads

1. **Association, not proof of cause.** P1-P3 estimate the extra edge loss associated with heavy oiling after
   adjusting for exposure and the pre-spill trend. Wording for slides: "associated with", "after adjusting
   for". Only the planting contrast (Zengel 2015/2022) comes from a randomized assignment.
2. **One spill.** Every real-data result is Deepwater Horizon, Louisiana salt marsh. P2 shows transfer to
   unseen marsh within Louisiana, not to another spill, coast or oil (D6). Do not describe the tool as
   geographically generalisable yet.
3. **"Heavy oiling" includes the cleanup that followed.** P1/P2 estimates mix oil and cleanup effects; P3's
   treatment contrasts come from one site with 5-9 plots per group.
4. **[Resolved in P5]** **Existing dashboard "Benchmark evidence" tab.** It shows models trained on `scenario_training_dataset.csv`
   and `lhs_scat_process_dataset.csv`, which are synthetic and rule-generated. A lead could read this as
   real-data evidence. P5 should relabel it ("method test on synthetic data") or move it out of the main view.

## B. Measurement

6. **Rounding in reported numbers.** Several P3 values in docs had been rounded up from the results files
   (1.8849 shown as 1.89). Fixed; reports should round from the CSV values, never from rounded text.

0. **[Resolved in P5: chooser offers spill oils only unless a box is ticked]** **Oil table includes non-oils.** `data/oil_properties.csv` (NOAA ADIOS) holds additives and refinery
   intermediates, e.g. "MOTOR FUEL ANTI-KNOCK COMPOUNDS" (API -37.2, 1,500 kg/m3). The dashboard's oil search
   can offer them, and the API-based category is meaningless for them. P5: filter the chooser to crude oils
   and fuel oils by `product_type`, or flag the rest. (Found by the P4 range check.)
1. **NAIP land/water classification** fails on tiles dominated by open water or bright river plume (P2);
   excluded areas: birdfoot delta, eastern Breton/Chandeleur Sound, south-west Barataria. Backlog D10.
2. **NAIP absolute rates read about 1.2 m/yr below field erosion** (P3 analysis C), and clean-edge rates
   (0.2 m/yr) are below Zengel's reference plots (0.8-1.2). Differences between classes are more trustworthy
   than absolute values. D11: the demo says so.
3. **Landsat land-fraction maps are not very clean** (Jaison, P1 review). The P1 pre-spill trend depends on
   them; P1's robustness check (0.80 m/yr after filtering) helps but does not settle it. Revisit with D10.
4. **Landsat 5 to Landsat 8 sensor change** sits between P1's pre- and post-spill epochs. Per-scene unmixing
   and agreement with NAIP argue against a large artefact, but it is not tested directly.
5. **The C validation (NAIP vs field) is thin:** 17 plots in 7 cells; the bootstrap treats plots as
   independent, so its interval is optimistic.

## C. Design and inference

0. **Duration of the oil effect is unresolved, and our headline hides it (Stage 1, 12 Nov).** P1's 0.85 m/yr
   is an average over 2010-2015. Challenger et al. 2021 (131 field sites) find extra loss on heavily oiled
   shore only in Fall 2010 to Fall 2011; Zengel 2022 and our P3 find about 2 years; Turner et al. 2016 find
   double the unoiled rate at 2.5 years. Our NAIP estimates for 2010-2015 and 2010-2017 are equal (1.00, 1.01),
   implying about 1.04 m/yr still in 2015-2017, which looks more like a persistent exposure difference than
   a fading oil effect. Bites: any slide or dashboard text that reads 0.85 (or 0.3-0.8) as a continuing annual
   rate; FINDINGS section 6 "at least seven years" (withdrawn). Resolves with: a pre-specified period-split
   check (FINDINGS section 11). Neither paper's full text was read (abstracts and Zengel 2022 Table 1 only).
   **Update (period-split check run, FINDINGS section 12): inconclusive.** 2010-2015: 0.42 (0.07 to 0.76);
   2015-2017: 0.28 (-0.27 to 0.84). Lightly oiled shore shows +0.78 in 2015-2017 where no effect is expected,
   so unexplained differences of that size exist in this design. Quote the headline with the adjusted range
   0.42 to 0.85 and "duration not resolved". Still open; field data, not more imagery, would close it.

1. **Barataria Bay was used to develop every method**, then reused as a P2 test basin. Its P2 result is the
   least independent; western Breton (31 heavy cells) is the only other test basin, and it is small.
2. **Exposure is the main confounder.** Open water within 1 km / 250 m and fetch are proxies; no wave model.
   Zengel's wave-power covariate changes the mechanical estimate from +0.28 to +0.61 m/yr, a reminder that
   exposure adjustment matters.
3. **Zengel 2015 and 2022 are the same site and largely the same plots.** Treat them as one evidence source,
   not two, when weighing treatment effects.
4. **Mechanical plots were the most heavily oiled**, so mechanical effects are confounded with oiling severity.
5. **Many analyses on overlapping data.** Each was pre-specified and run once, but there have been several
   (NAIP, P1 four checks, P2 four models, P3 A-C). Report all of them, including nulls, so the overall picture
   is not cherry-picked.
6. **Thresholds marked ASSUMED** (cell size 100 m, edge 0.1-0.9, agreement 0.4, filters 0.10/0.15, Otsu,
   valid >= 90%) were fixed before outcomes but not varied. A sensitivity sweep on 2-3 of them would
   strengthen the PoC (candidate task for P6).

7. **Cell-level prediction is weak (P5).** Held out by basin, the deployed model's error is 1.30 m/yr against
   1.42 for the regional average; a single cell's 90% interval spans about 6 m/yr. For planners, a prediction for
   a SCAT segment or 2 km block (averaging many cells) would be far tighter; P2 already reported block-level
   errors. Candidate for P6 or later, with its own plan.
8. **Rules and field evidence disagree on mechanical removal (P5).** Rules say ineligible in marsh; Zengel 2022
   shows no clear extra erosion, but mechanical plots were the most heavily oiled and n = 5. Do not let the
   evidence override the rules on this basis; present the disagreement.
9. **[Resolved: D13 approved by Jaison, 11 Nov]** Treatment mapping D13 was proposed by Claude; P3 had assigned it
   to Jaison.

## D. Reproducibility

1. Imagery is read live from Microsoft Planetary Computer. Scene and tile IDs are saved
   (`tile_classifiers.csv`, `scene_endmembers.csv`), but a collection update could change results; the
   derived per-cell tables are committed so analyses rerun without the imagery.
2. Analyses were run with Python 3.13; the README still says 3.11 for the dashboard. Check the dashboard on
   3.11 before the demo, or update the README. P5 raised the requirement to streamlit>=1.67 and added openpyxl;
   the clean-install check was on Python 3.13 only.
3. Memory: Landsat over a whole basin needs about 4 GB; the extraction is split into quadrants
   (`work` notes in P2 plan, amendment 3). A user rerunning on a laptop should know this.
4. GRIIDC lists a checksum for the Zengel 2022 file that matches neither the zip nor the xlsx as served
   (`data/external/zengel2022/SOURCE.md`).
5. The map's base tiles come from the internet; offline, the cells still draw on a blank background.

## E. Scope gaps against the project brief (for the "what next" slide)

000. **Gridded soil maps fail in marsh (Stage 3a, FINDINGS section 13).** SSURGO and SoilGrids do not beat the
   regional median for bulk density, organic matter or pH at 392 CRMS sites; SoilGrids overstates bulk density
   about sixfold. Bites: any plan to fill missing soil predictors from maps, here or on other
   coasts. Resolves with: measured data only (CRMS, DIVER); repeat the check before trusting maps elsewhere.

00. **Soil chemistry data now located, but censored (Stage 2, 12 Nov).** NOAA DIVER wetland files: PAH, organic
   matter, bulk density, pH, salinity, nutrients, metals at about 200 marsh stations over five campaigns
   (2010-2013). No numeric detection limits, only a category per result; 30% of rows have no limit available.
   Some soil rows carry mg/L units (unexplained; possibly extracts). Bites: any chemical-recovery model.
   Resolves with: a censored-data method fixed in a plan before running, and Jaison's check of units and
   analytes (his field). Licence wording is NOAA "no warranty", no identifier; 2% of rows are "Trustee and RP".


0. **Soil and sediment chemistry is missing (flagged at Jaison's request, 11 Nov 2026).** The PoC uses no
   soil, sediment or porewater chemistry in any model. The full list, with why each variable matters and open
   candidates, is in `data/meta/planned_variables.csv` (rendered at the end of `docs/VARIABLE_DICTIONARY.md`).
   Comments:
   - What we do hold: sediment total PAH as group means only (Zengel 2015, 2011-2012) and soil shear strength
     per plot (Zengel 2022, not analysed). Neither can enter a cell-level model.
   - Consequence for claims: the tool predicts physical (edge loss) and biological (vegetation cover)
     recovery, not chemical recovery. A slide must not say "recovery" without saying which kind.
   - Total PAH is not exposure. Toxicity follows the freely dissolved fraction, which depends on soil organic
     carbon; organic-rich marsh soils sorb strongly, so total PAH overstates risk there. Hopane-normalised
     PAH is needed to tell degradation from physical removal, otherwise a cleanup that strips surface soil
     looks like faster chemical recovery.
   - Best next additions, in order: (1) soil organic matter and bulk density (CRMS station data exist, and
     they separate organic from mineral marsh, which may explain why the oiling effect differs between basins
     in P2 and how marsh soils respond to trampling under cleanup); (2) porewater salinity (CRMS; basins
     differ in freshwater input); (3) DWH sediment PAH with forensic codes (NCEI 0163796, DIVER), if samples
     fall near our edge cells, which is unverified.
   - Caveat on CRMS: stations sit hundreds of metres inland from the edge (event study), so their soils may
     not represent the eroding edge. Any interpolation to edge cells needs its own check.
   - Redox, sulfide and root biomass would explain mechanisms but no open source covers these sites; treat
     them as field-campaign asks for the "what next" slide.
   - Jaison's own expertise is the right check here: whether these are the right priorities, and whether the
     units and depth conventions above are what a soil scientist would expect.

1. Cost, implementation time and waste are not in any data-based estimate yet (Goal 6).
2. No chemical recovery outcome (oil in sediment over time) is modelled; only physical (edge loss) and
   biological (vegetation cover) indicators.
3. Beaches, mangroves, other contaminants: none (D1).
4. Explainability beyond linear coefficients (SHAP etc.) is not warranted until a multi-predictor model beats
   simple baselines on independent data.
