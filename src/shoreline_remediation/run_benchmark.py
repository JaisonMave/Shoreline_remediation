import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.shoreline_remediation.training_pipeline import (
    benchmark_models,
    export_comparison_report,
    export_dataset,
    summarize_benchmark,
)


if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    data_dir = os.path.join(PROJECT_ROOT, "data")
    report_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    dataset_path = os.path.join(data_dir, "scenario_training_dataset.csv")
    report_path = os.path.join(report_dir, "comparison_report.csv")

    df = export_dataset(path=dataset_path, n_rows=100)
    results = benchmark_models()
    report = export_comparison_report(path=report_path, results=results)
    summary = summarize_benchmark(results)

    print("ROWS", len(df))
    print("REPORT_ROWS", len(report))
    print("MODELS", sorted(summary.keys()))
    for model_name in ["linear", "svm", "ann", "rf", "xgb", "gpr", "fdt"]:
        stats = summary[model_name]
        print(
            model_name.upper(),
            round(stats["mean_mae"], 3),
            round(stats["mean_r2"], 3),
            stats["best_treatment"],
        )
