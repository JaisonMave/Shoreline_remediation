from src.shoreline_remediation.training_pipeline import (
    benchmark_models,
    export_comparison_report,
    export_dataset,
    summarize_benchmark,
)


if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    report_dir = project_root / "reports"
    data_dir.mkdir(exist_ok=True)
    report_dir.mkdir(exist_ok=True)
    dataset_path = data_dir / "scenario_training_dataset.csv"
    report_path = report_dir / "comparison_report.csv"

    export_dataset(path=dataset_path, n_rows=600)
    results = benchmark_models()
    export_comparison_report(path=report_path, results=results)
    summary = summarize_benchmark(results)

    print("Scenario dataset exported to:", dataset_path)
    print("Comparison report exported to:", report_path)
    print("Model benchmark summary")
    print("=" * 80)
    for model_name, metrics in results.items():
        print(f"\nModel: {model_name}")
        for item in metrics:
            print(
                f"{item['treatment']:30s} | MAE={item['mae']:.3f} | R2={item['r2']:.3f}"
            )

    print("\nMean performance by model")
    print("-" * 80)
    for model_name, stats in summary.items():
        print(
            f"{model_name:6s} | mean_MAE={stats['mean_mae']:.3f} | mean_R2={stats['mean_r2']:.3f} | best={stats['best_treatment']}"
        )
