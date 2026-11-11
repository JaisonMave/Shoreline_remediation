# Review notes (critical comments to keep in view)

Running list of scientific and technical concerns raised during development, so they are not lost between
sessions. Each note says where it bites and what would resolve it. Add new notes at the top of a section;
mark resolved notes rather than deleting them. Decisions referred to are in `docs/ROADMAP.md`.

Last updated 11 November 2026 (after P3).

## A. Claims we can and cannot make to leads

1. **Association, not proof of cause.** P1-P3 estimate the extra edge loss associated with heavy oiling after
   adjusting for exposure and the pre-spill trend. Wording for slides: "associated with", "after adjusting
   for". Only the planting contrast (Zengel 2015/2022) comes from a randomized assignment.
2. **One spill.** Every real-data result is Deepwater Horizon, Louisiana salt marsh. P2 shows transfer to
   unseen marsh within Louisiana, not to another spill, coast or oil (D6). Do not describe the tool as
   geographically generalisable yet.
3. **"Heavy oiling" includes the cleanup that followed.** P1/P2 estimates mix oil and cleanup effects; P3's
   treatment contrasts come from one site with 5-9 plots per group.
4. **Existing dashboard "Benchmark evidence" tab.** It shows models trained on `scenario_training_dataset.csv`
   and `lhs_scat_process_dataset.csv`, which are synthetic and rule-generated. A lead could read this as
   real-data evidence. P5 should relabel it ("method test on synthetic data") or move it out of the main view.

## B. Measurement

0. **Oil table includes non-oils.** `data/oil_properties.csv` (NOAA ADIOS) holds additives and refinery
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

## D. Reproducibility

1. Imagery is read live from Microsoft Planetary Computer. Scene and tile IDs are saved
   (`tile_classifiers.csv`, `scene_endmembers.csv`), but a collection update could change results; the
   derived per-cell tables are committed so analyses rerun without the imagery.
2. Analyses were run with Python 3.13; the README still says 3.11 for the dashboard. Check the dashboard on
   3.11 before the demo, or update the README.
3. Memory: Landsat over a whole basin needs about 4 GB; the extraction is split into quadrants
   (`work` notes in P2 plan, amendment 3). A user rerunning on a laptop should know this.
4. GRIIDC lists a checksum for the Zengel 2022 file that matches neither the zip nor the xlsx as served
   (`data/external/zengel2022/SOURCE.md`).

## E. Scope gaps against the project brief (for the "what next" slide)

1. Cost, implementation time and waste are not in any data-based estimate yet (Goal 6).
2. No chemical recovery outcome (oil in sediment over time) is modelled; only physical (edge loss) and
   biological (vegetation cover) indicators.
3. Beaches, mangroves, other contaminants: none (D1).
4. Explainability beyond linear coefficients (SHAP etc.) is not warranted until a multi-predictor model beats
   simple baselines on independent data.
