"""Command line for research projections. From the repository root:

    python -m src.shoreline_remediation.projections validate --scenario examples/projections/bay_jimmy_observed.json
    python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_observed.json --output runs/bay_jimmy_observed
    python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2030.json --output runs/bj_2030
    python -m src.shoreline_remediation.projections compare --runs runs/bj_2030 runs/bj_2050 --output runs/bj_sensitivity
    python -m src.shoreline_remediation.projections evaluate --output runs/p_ret_1     (protocol P-RET-1 scoring)

Exit codes: 0 completed; 3 unsupported (a run record with the reason is written); 2 invalid input (nothing written);
4 output path already exists (left untouched); 1 run failed (manifest records the error).
"""
from __future__ import annotations

import argparse
import json
import sys

from src.shoreline_remediation.projections.runner import OutputExistsError, run
from src.shoreline_remediation.projections.spec import SpecError, check_scope, load

EXIT_OK, EXIT_FAILED, EXIT_INVALID, EXIT_UNSUPPORTED, EXIT_EXISTS = 0, 1, 2, 3, 4


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.shoreline_remediation.projections",
                                 description="Research projections (not validated forecasts, not recommendations).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check a scenario file and its scope without writing anything")
    v.add_argument("--scenario", required=True)
    r = sub.add_parser("run", help="run a scenario into a new output directory")
    r.add_argument("--scenario", required=True)
    r.add_argument("--output", required=True, help="new directory; an existing path is refused")
    c = sub.add_parser("compare", help="overlay two completed projection runs (sensitivity figure, no band)")
    c.add_argument("--runs", nargs="+", required=True)
    c.add_argument("--output", required=True, help="figure path stem; .png and .svg are written, existing files refused")
    e = sub.add_parser("evaluate", help="score protocol P-RET-1 (retreat rate rules) into a new output directory")
    e.add_argument("--output", required=True, help="new directory; an existing path is refused")
    e.add_argument("--n-boot", type=int, default=2000, help="cluster bootstrap draws (protocol: 2000)")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "evaluate":
            from src.shoreline_remediation.projections.runner import write_evaluation
            out = write_evaluation(args.output, n_boot=args.n_boot)
            s = json.loads((out / "evaluation.json").read_text(encoding="utf-8"))
            for c, v in s["candidates"].items():
                print(f"{c}: verdict {v['verdict']}; {v['n_pairs']} pairs; MAE {v['mae_m'].get(c, float('nan')):.3f} vs B1 "
                      f"{v['mae_m'].get('B1', float('nan')):.3f} m")
            print(f"WROTE {out}")
            return EXIT_OK
        if args.cmd == "compare":
            from src.shoreline_remediation.projections.runner import compare
            for p in compare(args.runs, args.output):
                print(f"WROTE {p}")
            return EXIT_OK
        if args.cmd == "validate":
            spec = load(args.scenario)
            u = check_scope(spec)
            if u:
                print(f"UNSUPPORTED [{u.code}] ({u.field}): {u.reason}")
                return EXIT_UNSUPPORTED
            print(f"VALID: {spec.scenario_id} ({spec.endpoint}, {spec.site_id}/{spec.plot_group_id}, model {spec.model_version})")
            return EXIT_OK
        res = run(args.scenario, args.output)
    except SpecError as exc:
        print(exc, file=sys.stderr)
        return EXIT_INVALID
    except OutputExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_EXISTS
    except Exception as exc:  # the manifest already records status 'failed'
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED
    if res.status == "unsupported":
        print(f"UNSUPPORTED [{res.unsupported.code}]: {res.unsupported.reason}\nRecord: {res.output_dir / 'manifest.json'}")
        return EXIT_UNSUPPORTED
    print(f"COMPLETED run {res.manifest['run_id']} -> {res.output_dir}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
