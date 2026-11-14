# Shoreline Remediation Decision Support

A structured prototype for shoreline oil-spill assessment and treatment screening. It combines NOAA/SCAT-informed field variables, FAST-style feasibility rules, machine-learning suitability benchmarking, a DHI-informed process simulation, and an interactive Streamlit dashboard.

## Start the application

For Windows, double-click:

`run_shoreline_dashboard.bat`

Or run from PowerShell in this folder:

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m streamlit run src\shoreline_remediation\dashboard.py
```

The launcher checks Python and dependencies, installs missing packages, and starts the dashboard. The dashboard lets a user select one preset or build a custom scenario, then displays treatment ranking, scientific plots, NOAA cross-checks, ML benchmark evidence, and a DHI-informed process trajectory.

## Project structure

```text
Model_v3/
|-- data/            inputs; data/external (real datasets with SOURCE.md), data/knowledge (evidence tables),
|                    data/meta (catalogue, variable dictionary), data/demo (site table for the dashboard)
|-- docs/            plans (written before each analysis), FINDINGS, ROADMAP (milestones, decisions),
|                    REVIEW_NOTES, HANDOFF, V4_PROGRAMME_PLAN, DATA_CATALOGUE, VARIABLE_DICTIONARY
|-- models/          model cards (JSON) for deployed and experimental models
|-- results/         one folder per analysis; earlier results are kept beside reruns
|-- reports/         synthetic-data benchmark outputs (method test only)
|-- scripts/         data download and build scripts
|-- src/shoreline_remediation/   package: rules, ranking, process model, site evidence, composer, dashboard
|-- tests/           pytest suite (python -m pytest tests)
|-- validation/      one module per pre-specified check (python -m validation.<name>)
|-- requirements.txt, requirements-analysis.txt, CHANGELOG.md
```

Tested with Python 3.11 (dashboard and full test suite, 14 Nov 2026); several analyses were first run with 3.13.

## Decision workflow

```text
SCAT/Scenario inputs
        |
        v
FAST feasibility gate
        |
        v
Ecological (do-no-harm) order within each feasibility tier, ASSUMED
        |
        v
Field evidence beside each option (site evidence view; D13)
        |
        v
DHI-informed process trajectory
        |
        v
Monitoring-oriented endpoint state
```

FAST remains a safety and applicability gate. Since V4 (D26) the ranking uses no ML suitability score: the only labels available are rule-generated, so the Gaussian Process layer is used only in the method test. The ML model evidence tab compares Linear Regression, SVM/SVR, ANN/MLP, Random Forest, XGBoost, Gaussian Process Regression, and the fuzzy baseline. The benchmark is based on synthetic labels and is not production validation.

## Command-line workflows

Run the selected-scenario batch comparison:

```powershell
py -3.11 -m src.shoreline_remediation.scenario_runner
```

This writes reports to `reports/`.

Run the seven-model benchmark:

```powershell
py -3.11 -m src.shoreline_remediation.run_benchmark
```

This writes datasets to `data/` and benchmark results to `reports/`.

## Process model

`process_model.py` generates a reproducible Latin Hypercube synthetic SCAT dataset and simulates a DHI-informed shoreline process model. It tracks:

- Surface volatile oil
- Surface heavy oil
- Subsurface volatile oil
- Subsurface heavy oil
- Wax
- Asphaltenes
- Residual oil
- Habitat recovery
- Endpoint decision
- Continued monitoring

The process model adapts the state-variable and first-order process structure documented in the supplied DHI manual. It is not the full MIKE model: it does not simulate hydrodynamic advection, particle tracks, emulsification, slick area, vertical dispersion, sedimentation, photooxidation, or re-oiling.

Full equations and assumptions are documented in [docs/PROCESS_MODEL_METHOD.md](docs/PROCESS_MODEL_METHOD.md).

## NOAA/SCAT basis

The NOAA cross-check is documented in [docs/NOAA_ASSUMPTION_AUDIT.md](docs/NOAA_ASSUMPTION_AUDIT.md), and the dashboard's NOAA cross-check tab uses [noaa_crosswalk.py](src/shoreline_remediation/noaa_crosswalk.py). The supplied manual supports treatment applicability, constraints, repeat inspection, and endpoint decision categories; it does not provide universal numeric treatment suitability scores or universal endpoint durations.

## Data and calibration boundary

The current synthetic data are for workflow development only. Replace them with repeat SCAT/SOS/STR observations before operational use. Calibration should use held-out shoreline segments and include residual oil measurements, treatment timing, oil chemistry, weather/tide/wave conditions, habitat observations, and endpoint decisions. Report uncertainty intervals and validate endpoint classification separately from parameter fitting.

## Evidence from real data (November 2026)

The branch `process-model-audit` adds analyses on real Deepwater Horizon data: NOAA SCAT shoreline oiling,
NAIP aerial imagery, Landsat, CRMS marsh stations and Zengel et al. (2015). Each was planned in writing before
it was run and run once.

| Document | What it holds |
| --- | --- |
| [CHANGELOG.md](CHANGELOG.md) | Every improvement on the branch: why, files, how to rerun, result, status |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Proof-of-concept milestones P1-P6, full programme, decision register |
| [docs/FINDINGS_2026-11-11.md](docs/FINDINGS_2026-11-11.md) | Results of every analysis, including nulls and failures |
| [docs/HANDOFF.md](docs/HANDOFF.md) | Current state and next steps for a new session |
| [docs/DATA_CATALOGUE.md](docs/DATA_CATALOGUE.md) | Every dataset: source, licence, date, method, checksums |
| [docs/VARIABLE_DICTIONARY.md](docs/VARIABLE_DICTIONARY.md) | Every variable: definition, unit, valid range, derivation |
| [docs/REVIEW_NOTES.md](docs/REVIEW_NOTES.md) | Open scientific and technical concerns |
| [docs/P6_POC_REPORT.md](docs/P6_POC_REPORT.md) | Proof-of-concept report and slides (links) and where each number comes from |
| [docs/P5_WORKED_EXAMPLE.md](docs/P5_WORKED_EXAMPLE.md) | Worked example from the demo's Site evidence tab (Bay Jimmy, Barataria Bay) |
| [models/p5_edge_loss_v1.json](models/p5_edge_loss_v1.json) | Deployed edge-loss model card: coefficients, 90% interval, training ranges, checksums |

Main result so far: heavily oiled salt-marsh edge in Louisiana lost about 0.6 to 0.85 m/yr more than clean edge
after the spill, once wave exposure and pre-spill erosion are accounted for. A model fitted on some basins
predicts edge loss in a held-out basin better than a no-information guess, with calibrated 90% intervals.

Install the extra packages with `pip install -r requirements-analysis.txt`.
