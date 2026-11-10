# Expert Workflow for FAST + SCAT Shoreline Treatment Scoring

## 1. Prepare the scenario dataset

Use the generated file:

- `scenario_training_dataset.csv`

This file contains realistic FAST/SCAT-style inputs including shoreline, oil, oiling, environmental, ecological, and operational conditions.

## 2. Score each scenario

Open the template file:

- `expert_scoring_template.csv`

Fill in the expert scores for the treatment columns:

- `natural_attenuation`
- `manual_removal`
- `passive_sorbents`
- `vacuum_removal`
- `low_pressure_flushing`
- `mechanical_removal`
- `high_pressure_washing`
- `surface_washing_agents`
- `bioremediation`

Requirements:

- Score each treatment from 0 to 10
- 0 = not suitable
- 10 = strongly suitable
- Use expert judgment only after FAST feasibility screening is applied
- If a treatment is clearly infeasible, still use a low score and record notes

## 3. Combine expert opinions

For multiple experts, keep each response in a separate row or separate sheet and aggregate by:

- mean score
- standard deviation
- confidence band

This captures both central tendency and expert disagreement.

## 4. Benchmark model performance

Run:

```powershell
Set-Location "C:\Users\Jaison.M\OneDrive - Shell\Desktop\New_oppurtunity\Shoreline remediation\model"
& "C:/Program Files/Python311/python.exe" .\train_models.py
```

The script will:

- export the scenario dataset
- run GPR, RF, and FDT benchmarks
- export a comparison CSV report
- print a summary of mean performance

## 5. Use the comparison report

Open:

- `comparison_report.csv`

This report contains one row per model-treatment evaluation with:

- `model`
- `treatment`
- `mae`
- `r2`

## 6. Decision logic

The final model should not simply select one method automatically. Instead, system outputs should include:

- FAST feasibility status
- ML suitability score
- ecological suitability
- uncertainty / confidence interval
- ranked alternatives
- decision drivers

This keeps the output explainable and defensible.
