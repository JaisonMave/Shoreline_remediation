# Foundation architecture (design only; 12 November 2026)

Status: **every decision here (D14 to D20) is Proposed.** Nothing in this document is built. It says what
to build, in what order, and what must be true before each part is worth building. Written after the
proof of concept (P1 to P6) and the Stage 2 inventory, so it is shaped by what the data can support.

## 1. Why change anything

The proof of concept is one spill, one habitat, one outcome (marsh-edge loss), with file layouts invented
per analysis. Three things now force a common foundation:

1. **New data do not fit the current tables.** DIVER chemistry is long-format with censoring flags; the
   Zengel meta-analysis is site-year-zone vegetation; Turner is islands. Each would need its own loader and
   its own conventions unless a shared schema exists.
2. **The dashboard calls one model directly.** A second model (vegetation recovery, chemical recovery) would
   need its own wiring, flags and interval logic.
3. **Rules, evidence and assumed constants live in Python code** (`fast_engine.py`, `treatment_effects.py`,
   `shoreline_transport.py`). A scientist cannot review or edit them without reading code.

What does not change: validated results, the P5 model artefact, the rule that evidence sits beside rules and
is never blended into one score (D13), hold-out by whole units (D5), and D1 (oil and salt marsh first).

## 2. Layers

```
 offshore fate models (PyGNOME, OpenOil)      [upstream, optional, D19]
                 | arrival record: where, when, how much, what state
                 v
 +-------------------------------------------------------------+
 | 1 DATA      common schema: site, event, observation,         |  D14
 |             intervention, source                             |
 +-------------------------------------------------------------+
 | 2 KNOWLEDGE editable tables: technologies, screening rules,  |  D16
 |             evidence effects, parameter priors               |
 +-------------------------------------------------------------+
 | 3 MODELS    each behind one interface: site in; prediction,  |  D15, D20
 |             interval, scope flags, explanation out           |
 |             a) empirical (edge loss v1, later veg, chemistry)|
 |             b) process-informed (priors, Monte Carlo, ...)   |  D18
 +-------------------------------------------------------------+
 | 4 ORCHESTRATION  fixed pipeline: characterise -> screen ->   |  D17
 |             predict -> attach evidence -> compare -> report  |
 +-------------------------------------------------------------+
 | 5 INTERFACE dashboard, reports (reads layer 4 only)          |
 +-------------------------------------------------------------+
```

## 3. Decisions

### D14 Common multi-site data schema (Module 1)

Five tables, stored as Parquet or CSV, one row meaning one thing:

| Table | One row is | Key fields |
| --- | --- | --- |
| `source` | a dataset or paper | source_id, citation, DOI, licence, acquired, method read, checksum |
| `site` | a fixed place | site_id, source_id, lat, lon, datum, coordinate_quality, region, spill_id, habitat (ESI code), zone (supratidal, intertidal, subtidal), geometry type (point, 100 m cell, plot, segment, island) |
| `event` | a visit or image date at a site | event_id, site_id, date, date_precision, method, campaign |
| `observation` | one measured value | event_id, variable (from the variable dictionary), value, unit, matrix (soil, sediment, water, tissue, vegetation, shoreline), depth_top, depth_bottom, basis (dry, wet), **censor_flag** (measured, below detection, between limits, no limit available), detection_limit (number or empty), qualifier, lab_method, value_type (measured, derived, modelled, **assumed**) |
| `intervention` | a treatment applied to a site | site_id, treatment (knowledge-base code), start, end, intensity, assigned (randomized, chosen, unknown), source_id |

Rules: units are converted on load and the original value and unit are kept; a variable not in the
dictionary is rejected, not silently added; a site without coordinates is allowed (`coordinate_quality =
none`) but is barred from any spatial join; censored values are never stored as zero or as the limit.
Derived per-analysis tables (edge cells, plot rates) are built from these and keep their own files.

Alternatives considered: one wide table per dataset (current; cannot hold DIVER or censoring); a relational
database (more than one person working alone needs; the tables above can be moved into one later unchanged).

Limits: mapping each source to the schema is manual work per source; DIVER's lack of numeric limits is
carried through, not solved. First loaders, in order: DIVER wetland chemistry, Zengel meta-analysis, the
existing edge cells, Turner islands.

### D15 Standard model interface (Modules 4, 5, 7)

Every model, simple or complex, is called the same way:

```
predict(site: SiteRecord, scenario: Scenario) -> Prediction
SiteRecord : site fields + the predictors the model declares it needs
Scenario   : treatment code (or none), horizon in years
Prediction : value, unit, interval (low, high, level), interval_method,
             scope ("in range", "new region", "outside training range") with reasons,
             explanation (per-predictor contribution, in the target's units),
             evidence_grade, model_id, model_version
```

A model that cannot give an interval, or cannot say when it is extrapolating, does not satisfy the interface
and cannot be shown. `site_evidence.predict_edge_loss` and `site_flags` already do most of this for one
model; the work is to make it a contract, with a test that every registered model honours it.
Explanation is a description of the model's arithmetic, not a causal claim, and is labelled so.

### D16 Knowledge base as editable tables (Module 3)

Three CSV tables replace constants in code, each row carrying source, evidence type (field trial,
observational, mesocosm, laboratory, expert rule, assumed) and status (proposed, approved):

- `technology`: code, name, mechanism, target contaminants, habitats, secondary impacts.
- `screening_rule`: technology, condition (habitat, oil type, exposure, access ...), verdict (unsuitable,
  conditional, suitable), reason, source. The FAST-like rules move here unchanged; a test proves the engine
  gives the same answers before and after the move.
- `evidence_effect`: technology, outcome, habitat, oiling, period, effect, interval, n, design, source.
  Zengel 2015 and 2022 priors move here unchanged.

Why tables: Jaison and future collaborators can review, challenge and extend the science without reading
Python, and adding a contaminant or technology (M7) becomes adding rows. Risk: a table is easier to edit
wrongly than code; so edits go through git, and tests check every row has a source and a status.

### D17 Orchestration layer (Modules 6, 7)

A fixed, ordered pipeline in plain Python: characterise site -> screen technologies by rule -> predict
outcome with and without each surviving treatment -> attach field evidence -> compare -> report, with each
step's inputs and outputs logged so a result can be traced. It reads models from a registry (D20) and rules
from the knowledge base (D16).

Not proposed: an LLM or multi-agent system making or ranking recommendations. Reason: the answer must be
reproducible and traceable to data and rules; a language model adds neither. A language model may later
draft the wording of a report from the pipeline's structured output, clearly separated from the numbers.
Multi-criteria ranking (AHP, TOPSIS) stays out until there are at least two validated outcome predictions
and cost data to rank on; ranking on rule scores alone would only restate the rules.

### D18 Process-informed layer, in four gated steps (Module 4)

The existing process model (`shoreline_transport.py`) has assumed rate constants and ignores oil thickness,
penetration and season. The proposal is to make it honest before making it clever:

| Step | What | Gate to pass before the next step |
| --- | --- | --- |
| 1 Literature priors | A `parameter_prior` table: each rate constant with a distribution, source and evidence type, replacing single assumed numbers | Every parameter has a sourced range or is labelled assumed with a wide range |
| 2 Monte Carlo | Run the model across the priors; output a distribution, not a number; sensitivity analysis shows which parameters matter | Output intervals are reported; the three or four influential parameters are identified |
| 3 Bayesian calibration | Update only the influential parameters against outcome data we actually hold (DIVER soil PAH over 2010-2013 at about 200 stations is the first candidate; edge loss is not, because the process model does not predict erosion) | Calibrated model beats (a) the uncalibrated priors and (b) a simple empirical decline curve on stations held out as whole stations; posterior differs from prior for at least one parameter (otherwise the data taught nothing) |
| 4 ML surrogate | A fast emulator of the process model | Only if the model becomes too slow for the dashboard or calibration. Today it runs in milliseconds, so a surrogate adds error and no benefit. **Not recommended now.** |

Honest limits: calibration can only identify parameters the outcome data respond to. Soil PAH series are
censored, taken at 202 stations whose oiling history is known only through SCAT, and affected by cleanup;
several parameters will stay at their priors. A physics-informed neural network is not proposed: there is
no evidence a simpler calibrated model is insufficient, and the data are too few to constrain one.

### D19 Offshore fate models as an upstream input provider (Modules 1, 2)

PyGNOME (NOAA) and OpenOil (OpenDrift, Norwegian Meteorological Institute) predict where and when floating
oil reaches the coast and in what weathered state. They do not model the shoreline. Proposed contract: an
`arrival` record per shoreline segment (time of first arrival, mass or thickness class, weathering state,
with ensemble spread), written by an adapter and consumed by layers 1 and 3 exactly like an observed SCAT
record, flagged `value_type = modelled`.

Use: forecasting for a new spill, where no SCAT survey exists yet. Not for Deepwater Horizon, where observed
oiling is better than any hindcast. Not built until a second spill or a forecasting use case is in scope;
installing and driving these models (currents, winds) is substantial work and neither has been run here.
Whether a modelled arrival predicts observed SCAT class well enough to stand in for it is an open question
that must be tested on DWH before anyone relies on it.

### D20 Model registry and promotion gate (Module 5)

Each model has a card (as `models/p5_edge_loss_v1.json`) and one of two states: experimental or validated.
To be validated a model must: have a plan committed before it ran; beat a no-predictor baseline on whole
held-out units (basins, stations, studies or spills, never rows); report interval coverage; report
per-region results including failures; record its training-range for extrapolation flags. Only validated
models are reachable from the orchestration layer. Today one model qualifies (edge loss v1); the marsh
recovery model (D4) is the worked example of one that does not.

## 4. Build order (proposed)

| Order | Work | Why first | Needs |
| --- | --- | --- | --- |
| 1 | D14 schema and the DIVER and Zengel loaders | Unlocks the two new outcome types; everything else reads from it | Jaison's check of soil variables and units |
| 2 | D15 interface and D20 registry around the existing edge-loss model | Small; stops the second model needing new wiring | - |
| 3 | D16 knowledge tables (move, do not change) | Makes rules reviewable | - |
| 4 | First new models behind the interface: vegetation recovery hold-out by study (Zengel table); soil PAH decline with censoring (DIVER) | The actual science; each needs its own pre-specified plan | 1, 2 |
| 5 | D18 steps 1 and 2 | Replaces assumed constants with ranges | Literature time |
| 6 | D17 pipeline, then D18 step 3 | Only worth it with two or more validated models | 4, 5 |
| - | D19 adapter; D18 step 4 | Deferred until a use case exists | Second spill |

## 5. What this design does not solve

One spill (D6 still holds). No cleanup records per segment. No cost data. Beaches and mangroves have almost
no outcome data in hand. No sediment toxicity or bioavailability measures: DIVER gives totals, not
bioavailable fractions. Geographic generalisation remains a claim to be earned by a second spill (M4), not
by architecture.
