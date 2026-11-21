"""Command line for research projections. From the repository root:

    python -m src.shoreline_remediation.projections validate --scenario examples/projections/bay_jimmy_observed.json
    python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_observed.json --output runs/bay_jimmy_observed
    python -m src.shoreline_remediation.projections run --scenario examples/projections/bay_jimmy_retreat_2030.json --output runs/bj_2030
    python -m src.shoreline_remediation.projections compare --runs runs/bj_2030 runs/bj_2050 --output runs/bj_sensitivity
    python -m src.shoreline_remediation.projections evaluate --output runs/p_ret_1     (protocol P-RET-1 scoring)

A what-if JSON downloaded from Bay Jimmy -> Assessment -> Explore future scenarios (spec version 2) is accepted as it is:

    python -m src.shoreline_remediation.projections validate --scenario bay_jimmy_retreat_whatif.json
    python -m src.shoreline_remediation.projections run --scenario bay_jimmy_retreat_whatif.json --output runs/bj_whatif

For version 2 the recorded assessment is re-run (assessment_screening.reproduce, loaded only for version-2 files; it never
imports Streamlit) and the technique is re-screened through the inventory. Outputs saved in the download are compared with the
replay, never used.

Exit codes: 0 completed; 3 unsupported (a run record with the reason is written); 2 invalid input (nothing written);
4 output path already exists (left untouched); 1 run failed (manifest records the error).
"""
from __future__ import annotations

import argparse
import json
import sys

from src.shoreline_remediation.projections import catalogue as C
from src.shoreline_remediation.projections.runner import OutputExistsError, run
from src.shoreline_remediation.projections.spec import SpecError, check_scope, load


def _screening_for(spec):
    """The screening resolver for a version-2 what-if; None for version 1 (which never loads the decision engine)."""
    if spec.model_version not in C.WHATIF_MODELS:
        return None
    from src.shoreline_remediation import assessment_screening
    return assessment_screening.reproduce

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
            screening = _screening_for(spec)
            if screening is not None:
                from src.shoreline_remediation.projections.whatif import screen
                sc = screen(screening(spec), spec.technique, spec.endpoint)
                effect = spec.treatment_effect
                print(f"SCREENING [assessment {sc.assessment_status}]: {spec.technique}: "
                      + ("what-if allowed" if getattr(sc.row, "what_if_allowed", False) else "what-if NOT allowed")
                      + f". {sc.reason}")
                if effect is None:
                    print("TREATMENT EFFECT: none (natural-recovery arm only)")
                elif not getattr(sc.row, "what_if_allowed", False):
                    print("TREATMENT EFFECT: present but blocked by screening; run writes the natural-recovery arm only")
                    return EXIT_UNSUPPORTED
            return EXIT_OK
        spec = load(args.scenario)
        res = run(args.scenario, args.output, screening=_screening_for(spec))
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
    w = res.manifest.get("whatif")
    if w:
        print(f"WHAT-IF: {w['summary']['text']}")
        check = w["exported_outputs_check"]
        if check["status"] == "differs":
            print(f"WARNING: the outputs saved in the scenario file differ from the replay ({len(check['differences'])} rows"
                  f"{', summary' if check.get('summary_differences') else ''}); the replay recomputes from the inputs. "
                  f"See manifest.json -> whatif.exported_outputs_check.", file=sys.stderr)
    print(f"COMPLETED run {res.manifest['run_id']} -> {res.output_dir}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
