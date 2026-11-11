# Roadmap and milestones (status on 11 November 2026)

Status words: Not started, In progress, Awaiting data, Under validation, Completed, On hold.
A milestone is Completed only when it is validated and documented, not when code exists.

## Where the project stands, by module

| Module | Built so far | Status |
| --- | --- | --- |
| 1 Data infrastructure | Deepwater Horizon (DWH) SCAT oiling, CRMS marsh sites, Landsat and NAIP series for Barataria Bay, Zengel 2015 treatment table, 1,460 NOAA ADIOS oils, 63 NOAA marsh cases. One spill, oil only. No variable dictionary or schema yet. | In progress |
| 2 Characterisation and risk | Oil category from measured properties; shoreline type and ESI. No sediment or water chemistry, no toxicity or bioavailability. | In progress (thin) |
| 3 Remediation intelligence | Rule-based screening and ranking (FAST-like), five SCAT sanity checks pass; Zengel treatment priors. No ML suitability model: no outcome labels to train on. | In progress |
| 4 Recovery prediction | Marsh-edge loss by oiling class from NAIP; after the pre-spill check, heavy oiling adds 0.85 m/yr (90% CI 0.49 to 1.22), 0.62 to 0.85 depending on exposure adjustment; Zengel vegetation priors. Published-case recovery model did not beat a no-predictor baseline. | Under validation |
| 5 Generalisation and reliability | Uncertainty intervals on every estimate. No test on a second spill or region yet. | Not started |
| 6 Scenarios and decision support | Dashboard compares treatments; oil chosen by name. Comparisons are rule-based, not yet driven by validated predictions. | In progress |
| 7 Software | Modular Python package, Streamlit dashboard, 43 tests, branch `process-model-audit` (not pushed). | In progress |

## Proof-of-concept track (Jaison working alone, with Claude)

Goal: a defensible demonstration for project leads, using only open data and work Jaison and Claude can do.
Claim to be made at the end: "for oiled salt marsh in the northern Gulf of Mexico, the tool screens cleanup
options, predicts marsh-edge loss with honest intervals, and holds up when tested on marsh it was not
fitted to." Not claimed: other contaminants, other ecosystems, other spills.

| # | Milestone | Deliverable | Jaison's part | Done when | Status |
| --- | --- | --- | --- | --- | --- |
| P1 | Lock the core result | Pre-spill erosion check (Landsat 1999-2009 shoreline change; NAIP 2007/2009 if Jaison obtains it) and a finer exposure check | Optional: download pre-spill NAIP for Barataria Bay (USGS EarthExplorer, free login; availability to confirm); review the quality-check images | The 1.0 m/yr estimate survives both checks, or is revised and documented | Under validation: checks run, result revised to 0.85 m/yr (0.49 to 1.22). Jaison (11 Nov): Landsat land-fraction maps not very clean; revisit later. FINDINGS section 7 not yet reviewed (no laptop). |
| P2 | Geographic hold-out within the spill | Edge cells and NAIP edge loss for other oiled Louisiana basins (e.g. Terrebonne, Breton Sound, Mississippi delta); predictive model fitted on some basins, tested on a held-out basin, against a no-predictor baseline | Agree the model and basins before it runs; judge marsh-type and exposure variables | Held-out error and interval coverage reported per basin, including any basin where it fails | In progress (plan: docs/P2_BASIN_HOLDOUT_PLAN.md) |
| P3 | Treatment data check | Search NOAA DIVER for segment-level cleanup records; if usable, edge loss split by cleanup method; if not, Zengel 2015 priors stay and the gap is documented | Decide how cleanup categories map to the tool's treatments | Either a treatment split with intervals, or a documented "not available" | Not started |
| P4 | Light data documentation | Variable dictionary, data catalogue with provenance, decision register, for the datasets the PoC uses only | Check the soil and sediment definitions | Every input in the demo traceable to source, date and method | Not started |
| P5 | Demo dashboard | Map of a site; rule screening of options; predicted edge loss per option against no treatment, with intervals; out-of-scope and extrapolation flags; one worked Barataria example | Test it as a user; flag anything a lead would question | Runs end to end from a clean install; tests pass | Not started |
| P6 | Proof-of-concept report and slides | What works (with validated numbers), what failed and why, limits, and what scaling needs (data, people, other spills, other contaminants) | Scientific review; present to leads | Jaison signs off | Not started |

Order: P1 -> P2 -> P3 (can run alongside P2) -> P4 -> P5 -> P6.
Deferred to after the PoC, as the "what we need next" ask: expert scoring (M6), more spills (M4), other
contaminants and ecosystems (M7), the full platform (M8-M10).

## Full programme milestones (after the proof of concept)

| # | Milestone | Completion criteria | Depends on | Status |
| --- | --- | --- | --- | --- |
| M1 | Confirm the DWH edge-loss result | Same as P1 | Pre-spill imagery | Under validation (as P1) |
| M2 | Data governance foundation | Variable dictionary, data schema, source inventory with provenance, decision register, dataset version records (P4 is the first part) | None | Not started |
| M3 | Treatment-effect model at scale | DIVER segment-level cleanup records joined to edge cells; edge loss by cleanup method with intervals; compared with Zengel 2015 (P3 is the first part) | M1; DIVER records usable (unverified) | Not started |
| M4 | Second and third spills | At least two further spills with shoreline oiling, cleanup and outcome data, harmonised to the M2 schema. Candidates (data availability unverified): Exxon Valdez 1989 beaches, other NOAA SCAT archives, Hebei Spirit 2007, Prestige 2002, Wakashio 2020 mangroves | M2 | Not started |
| M5 | Recovery prediction v1 (oil, marsh) | Hierarchical model of edge loss and vegetation recovery by oiling and treatment; validated leaving out whole spills; beats a no-predictor baseline; prediction intervals checked for coverage | M3, M4 | Not started |
| M6 | Expert scoring | Three or more experts score the 30 blind scenarios; agreement (ICC) reported; used to check the ranking engine | Experts recruited | On hold (needs other people) |
| M7 | Remediation knowledge base beyond oil | Evidence table per technology for the technologies in the project brief; rule-based screening for each | D1 | Not started |
| M8 | Explainability and uncertainty integration | Interval on every dashboard output; SHAP or sensitivity analysis once a multi-predictor model passes validation; extrapolation flags | M5 | Not started |
| M9 | Scenario comparison and adaptive monitoring | Each intervention compared with a no-intervention baseline using validated predictions; monitoring data update the estimates | M5, M8 | Not started |
| M10 | Integrated platform validation and release | All modules connected; independent-spill validation reported per ecosystem; documentation of assumptions, limits and applicability | All above | Not started |

## Decision register

| ID | Date | Module | Decision | Status |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-11 | All | Build oil spills x salt marsh first, then other oiled shorelines (beaches, mangroves), then other contaminants. The full multi-contaminant scope needs outcome data that open sources do not yet supply. | Approved by Jaison 2026-11-11 |
| D2 | 2026-11-11 | 4 | NAIP 2013 dropped from edge-loss analysis; primary period 2010-2015 (hazy imagery, decided before the model ran). | Approved by Jaison 2026-11-11; implemented |
| D3 | 2026-11-11 | 3 | Zengel 2015 contrasts used as priors only, not as a validated treatment model (one site, not randomized except planting). | Approved by Jaison 2026-11-11; implemented |
| D4 | earlier | 4 | Published-case marsh recovery model not used for ranking (fails baseline). | Approved by Jaison 2026-11-11; implemented |
| D5 | earlier | 5 | Validate by holding out whole spills, never single rows. | Approved |
| D6 | 2026-11-11 | 5 | For the proof of concept, test generalisation by holding out whole Louisiana basins within Deepwater Horizon, because no second spill's data are in hand. This shows transfer to unseen marsh, not to unseen spills; D5 still applies to the full programme. | Approved by Jaison 2026-11-11 |
| D7 | 2026-11-11 | 4, 5 | P2 predictive model includes open water within 250 m, mean fetch and each cell's pre-spill (1999-2008) edge-loss trend, in addition to oiling class and open water within 1 km. Reason: P1 showed exposure explains the pre-spill gap and about half of the original estimate. | Applied: Jaison gave the go-ahead for P2 on 2026-11-11 (section 7 not yet reviewed) |
| D8 | 2026-11-11 | 5 | P2 basins: Terrebonne, Barataria, birdfoot delta, Breton Sound/St Bernard, split by fixed geographic lines (scripts/assign_basins.py) before outcomes outside Barataria were measured. | Implemented |
