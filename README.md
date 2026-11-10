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
model/
|-- data/
|   |-- expert_scoring_template.csv
|   |-- lhs_scat_process_dataset.csv
|   `-- scenario_training_dataset.csv
|-- docs/
|   |-- NOAA_ASSUMPTION_AUDIT.md
|   |-- PROCESS_MODEL_METHOD.md
|   |-- workflow.md
|   `-- reference/
|       |-- DHI_OilSpill_Model.pdf
|       `-- manual_shore_assess_aug2013.pdf
|-- reports/
|   |-- comparison_report.csv
|   |-- scenario_summary.csv
|   |-- scenario_comparison_report.pdf
|   |-- scenario_comparison_report.png
|   `-- scenario_dashboard.html
|-- src/shoreline_remediation/
|   |-- dashboard.py
|   |-- scenario_runner.py
|   |-- process_model.py
|   |-- noaa_crosswalk.py
|   |-- data_model.py
|   |-- fast_engine.py
|   |-- decision_framework.py
|   |-- ml_models.py
|   |-- training_pipeline.py
|   |-- data_dictionary.py
|   |-- train_models.py
|   `-- run_benchmark.py
|-- requirements.txt
|-- run_shoreline_dashboard.bat
`-- README.md
```

## Decision workflow

```text
SCAT/Scenario inputs
        |
        v
FAST feasibility gate
        |
        v
ML suitability and benchmark evidence
        |
        v
Ecological suitability rules
        |
        v
Treatment utility ranking
        |
        v
DHI-informed process trajectory
        |
        v
Monitoring-oriented endpoint state
```

FAST remains a safety and applicability gate. The dashboard currently uses the live Gaussian Process suitability path for supported treatments, while the ML model evidence tab compares Linear Regression, SVM/SVR, ANN/MLP, Random Forest, XGBoost, Gaussian Process Regression, and the fuzzy baseline. The benchmark is based on synthetic labels and is not production validation.

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
