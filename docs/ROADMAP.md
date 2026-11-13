# Roadmap and milestones (status on 12 November 2026)

Status words: Not started, In progress, Awaiting data, Under validation, Completed, On hold.
A milestone is Completed only when it is validated and documented, not when code exists.

## Where the project stands, by module

| Module | Built so far | Status |
| --- | --- | --- |
| 1 Data infrastructure | DWH SCAT oiling, CRMS marsh sites, NAIP and Landsat series for Louisiana basins, Zengel 2015 and 2022 treatment data, 1,460 NOAA ADIOS oils, 63 NOAA marsh cases. One spill, oil only. Data catalogue and variable dictionary (P4) with tests; no general multi-site schema yet. | In progress |
| 2 Characterisation and risk | Oil category from measured properties (spill oils only); shoreline type and ESI. No sediment or water chemistry, no toxicity or bioavailability: flagged with priorities in `data/meta/planned_variables.csv` and REVIEW_NOTES E0. | In progress (thin) |
| 3 Remediation intelligence | Rule-based screening and ranking (FAST-like), five SCAT sanity checks pass; Zengel 2015 vegetation priors and Zengel 2022 erosion priors (manual -0.6, mechanical +0.3, planting -1.5 m/yr vs natural recovery, first 2 years). No ML suitability model: no outcome labels to train on. | In progress |
| 4 Recovery prediction | Marsh-edge loss by oiling class from NAIP; after the pre-spill check, heavy oiling adds 0.85 m/yr (90% CI 0.49 to 1.22), 0.62 to 0.85 depending on exposure adjustment; Zengel vegetation priors. Published-case recovery model did not beat a no-predictor baseline. | Under validation |
| 5 Generalisation and reliability | Leave-one-basin-out test within Louisiana (P2): beats a no-predictor baseline in 2 held-out basins, 90% intervals cover 88-90%. No second spill yet. Land/water classification fails in river-plume and open-water tiles (backlog). | In progress |
| 6 Scenarios and decision support | Site evidence view (P5): per site, expected edge loss with 90% interval, scope flags, and rule screening beside field evidence per option (Zengel 2015/2022). Old rule-and-synthetic view kept and labelled. No cost or time-to-target from data yet. | Under validation |
| 7 Software | Modular Python package, Streamlit dashboard (runs from a clean install of requirements.txt), versioned model artefact, 108 tests, branch `process-model-audit` (not pushed). | In progress |

## Proof-of-concept track (Jaison working alone, with Claude)

Goal: a defensible demonstration for project leads, using only open data and work Jaison and Claude can do.
Claim to be made at the end: "for oiled salt marsh in the northern Gulf of Mexico, the tool screens cleanup
options, predicts marsh-edge loss with honest intervals, and holds up when tested on marsh it was not
fitted to." Not claimed: other contaminants, other ecosystems, other spills.

| # | Milestone | Deliverable | Jaison's part | Done when | Status |
| --- | --- | --- | --- | --- | --- |
| P1 | Lock the core result | Pre-spill erosion check (Landsat 1999-2009 shoreline change; NAIP 2007/2009 if Jaison obtains it) and a finer exposure check | Optional: download pre-spill NAIP for Barataria Bay (USGS EarthExplorer, free login; availability to confirm); review the quality-check images | The 1.0 m/yr estimate survives both checks, or is revised and documented | Under validation: checks run, result revised to 0.85 m/yr (0.49 to 1.22). Jaison (11 Nov): Landsat land-fraction maps not very clean; revisit later. FINDINGS section 7 not yet reviewed (no laptop). |
| P2 | Geographic hold-out within the spill | Edge cells and NAIP edge loss for other oiled Louisiana basins (e.g. Terrebonne, Breton Sound, Mississippi delta); predictive model fitted on some basins, tested on a held-out basin, against a no-predictor baseline | Agree the model and basins before it runs; judge marsh-type and exposure variables | Held-out error and interval coverage reported per basin, including any basin where it fails | Under validation: run once; verdict "partly transfers" (beats baseline in both tested basins, 89% interval coverage; oiling class adds no cell-level accuracy over exposure). FINDINGS section 8; awaiting Jaison's review |
| P3 | Treatment data check | Search NOAA DIVER for segment-level cleanup records; if usable, edge loss split by cleanup method; if not, Zengel 2015 priors stay and the gap is documented | Decide how cleanup categories map to the tool's treatments | Either a treatment split with intervals, or a documented "not available" | Under validation: segment-level records not available (documented); plot-level treatment effects on erosion from Zengel et al. 2022 with intervals, added to the tool as priors; NAIP checked against field erosion (rank correlation 0.68, reads 1.2 m/yr low). FINDINGS section 9; awaiting Jaison's review |
| P4 | Light data documentation | Variable dictionary, data catalogue with provenance, decision register, for the datasets the PoC uses only | Check the soil and sediment definitions | Every input in the demo traceable to source, date and method | Under validation: data catalogue (19 datasets, 51 files, checksums), variable dictionary (45 entries with units, ranges, derivation), both checked by tests; awaiting Jaison's check of definitions. Soil and sediment chemistry absent from the PoC and flagged (15 planned variables with comments). |
| P5 | Demo dashboard | Map of a site; rule screening of options; predicted edge loss per option against no treatment, with intervals; out-of-scope and extrapolation flags; one worked Barataria example | Test it as a user; flag anything a lead would question | Runs end to end from a clean install; tests pass | Under validation: built (plan `docs/P5_DEMO_PLAN.md`, FINDINGS section 10); runs from a clean install; 108 tests pass; worked example `docs/P5_WORKED_EXAMPLE.md`. Awaiting Jaison's test as a user. |
| P6 | Proof-of-concept report and slides | What works (with validated numbers), what failed and why, limits, and what scaling needs (data, people, other spills, other contaminants) | Scientific review; present to leads | Jaison signs off | Under validation: report (Docs) and 12-slide deck delivered 11 Nov, every number checked against results files (`docs/P6_POC_REPORT.md`). Awaiting Jaison's review and sign-off (parked). |

## Work after the proof of concept (12 Nov 2026)

| # | Item | Status |
| --- | --- | --- |
| S1 | Reconcile P1 with Challenger 2021 and Turner 2016 | Under validation: note, not revision (FINDINGS 11); full texts not read (`docs/LITERATURE_TO_DOWNLOAD.md`) |
| S1b | Period-split check | Under validation: inconclusive (FINDINGS 12) |
| S2 | Dataset inventory | Under validation: ten sources checked, seven datasets catalogued (`docs/STAGE2_INVENTORY.md`); plant-oiling layers and beach treatment data not obtained |
| S3a | Soil layer check | Under validation: null result (FINDINGS 13) |
| SA | Treatment comparison (A1-A4) | Under validation (FINDINGS 14-18, 24) |
| SB | Long-horizon forecast (B1) | Under validation (FINDINGS 19) |
| SC | Mangroves (C1, C2) | Under validation (FINDINGS 20, 23) |
| SD | Soil PAH decline | Under validation (FINDINGS 22) |
| S3b | Foundation architecture | Not started: design written, D14-D20 Proposed |

Order: P1 -> P2 -> P3 (can run alongside P2) -> P4 -> P5 -> P6.
Parked by Jaison (11 Nov, no laptop): his reviews of P1-P5, his check of the variable definitions and his
test of the dashboard. P1-P5 stay "Under validation" until he does them; P6 proceeds meanwhile and says so.
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
| D9 | 2026-11-11 | 4, 6 | Demo (P5) shows the exposure-based edge-loss prediction with its 90% interval, plus the heavy-oiling uplift as a range (about 0.3 to 0.8 m/yr), and flags active river delta and open-water plume areas as out of scope. Reason: P2 found the uplift real but unstable between basins. | Approved by Jaison 2026-11-11 |
| D10 | 2026-11-11 | 1 | Backlog: replace the per-tile Otsu land/water rule with a classifier that works on tiles dominated by water or plume; revisit P1 Landsat maps (Jaison's note). | Proposed |
| D11 | 2026-11-11 | 3, 6 | Demo (P5) uses Zengel et al. 2022 erosion priors by treatment against natural recovery, with intervals, for heavily oiled salt marsh in years 0-2, and shows that differences are not clear after year 2. NAIP-based absolute rates carry a note that they read about 1.2 m/yr low. | Approved by Jaison 2026-11-11 |
| D12 | 2026-11-11 | 1 | Data documentation is generated from data: `scripts/build_catalogue.py` writes the catalogue (with SHA-256 per file) and the dictionary docs; tests fail if data change without a rebuild or a variable leaves its valid range. Git history of `data/meta/catalogue.csv` is the dataset version history. | Implemented (P4) |
| D13 | 2026-11-11 | 3, 6 | Map tool treatments to field-evidence groups: natural_attenuation = untreated (natural recovery, baseline); manual_removal = Zengel manual treatment; mechanical_removal = Zengel mechanical treatment; planting shown as a restoration add-on; every other treatment shows "no outcome evidence". Evidence is shown beside the rule screening, never combined into one score. | Approved by Jaison 2026-11-11; implemented in P5 |
| D9a | 2026-11-12 | 4, 6 | Wording: the heavy-oiling excess is quoted as "average over 2010-2015", with the adjusted range 0.42 to 0.85 and "duration not resolved by our data"; "for at least seven years" withdrawn. Reason: Challenger 2021, Turner 2016, period-split check (FINDINGS sections 11, 12). | Implemented in the dashboard caption and docs (Jaison delegated the call, 12 Nov); P6 report and decks not yet edited |
| D14 | 2026-11-12 | 1 | Common multi-site schema: source, site, event, observation (with censoring fields), intervention. | Proposed (`docs/ARCHITECTURE_FOUNDATION.md`) |
| D15 | 2026-11-12 | 4, 5, 7 | Standard model interface: site and scenario in; value, interval, scope flags and explanation out. | Proposed |
| D16 | 2026-11-12 | 3 | Knowledge base as editable tables (technologies, screening rules, evidence effects) with source and status per row. | Proposed |
| D17 | 2026-11-12 | 6, 7 | Orchestration as a fixed, logged pipeline; no language-model agents in the decision path; multi-criteria ranking deferred until two validated outcomes and cost data exist. | Proposed |
| D18 | 2026-11-12 | 4 | Process-informed layer in gated steps: literature priors, Monte Carlo, Bayesian calibration against DIVER soil PAH, ML surrogate only if speed requires it (not now). | Proposed |
| D19 | 2026-11-12 | 1, 2 | Offshore fate models (PyGNOME, OpenOil) as an upstream provider of an arrival record; deferred until a forecasting use or second spill. | Proposed |
| D20 | 2026-11-12 | 5 | Model registry with experimental and validated states and a promotion gate. | Proposed |
| D21 | 2026-11-12 | 1, 2 | Do not use SSURGO or SoilGrids values as soil predictors in marsh; measured data only. Evidence: FINDINGS section 13. | Proposed |
| D22 | 2026-11-13 | 2, 4 | Soil PAH: sum of individual compounds and hopane ratio; replicates averaged with a 50% RPD rule; non-detects estimated below a proxy limit by censored regression; all surface depths with depth as covariate. Chemical recovery is judged on the hopane ratio, not the sum. | Approved by Jaison (choices 1-5) and orchestrator (6); implemented |
| D23 | 2026-11-13 | 3 | Expert-revised ranges and verdicts for untested treatments; conditions advisory only. | Approved by orchestrator under Jaison's delegation; implemented |
| D24 | 2026-11-13 | 3, 4, 6 | Mangrove mode: Galeta damage model plus mangrove screening (work from water or fringe only); no marsh model applied to mangroves. | Approved by orchestrator under Jaison's delegation; implemented (experimental) |
