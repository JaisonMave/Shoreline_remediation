"""Scenario-projection programme, Session 1: capture the production reference cases before any projection code exists.

Drives the real dashboard (Streamlit AppTest) for four reference cases, records the exact run spec each one sends to the decision
pipeline, replays that spec through decision_pipeline.run_decision outside Streamlit, and writes normalized reports and a summary of
visible controls. Session 6 reruns this script and diffs the output against the committed baseline.

Read-only with respect to production code: it imports the dashboard and pipeline, it never modifies them.

Run from the repository root (the output directory must be new or empty; the Session 1 baseline in
results/projection_baseline is read-only):
    python -W ignore scripts/capture_projection_baseline.py --out results/projection_baseline_session6

Normalization: only genuinely volatile fields are replaced (the code commit recorded in report.version). Everything else, including
Monte Carlo summaries, is compared exactly because the pipeline uses a fixed seed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "src" / "shoreline_remediation" / "dashboard.py")
VOLATILE_VERSION_KEYS = ("git_commit", "generated_at", "timestamp", "run_at")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def _bay_jimmy() -> AppTest:
    at = _app()
    at.button(key="home_use_bay_jimmy").click().run()
    at.button(key="home_run").click().run()
    return at


def _habitat(key: str, setup=None) -> AppTest:
    at = _app()
    at.segmented_control(key="page").set_value("site").run()
    at.segmented_control(key="site_habitat").set_value(key).run()
    if setup:
        setup(at)
    at.button(key=f"run_{key}").click().run()
    return at


def _typed_heavy(at: AppTest) -> None:
    """Site page, salt marsh, 'New site (enter values)' with the default coordinates (29.40, -89.90) and Heavy oiling."""
    at.radio(key="site_mode").set_value("New site (enter values)").run()
    at.selectbox(key="new_oil").set_value("Heavy").run()


# The four reference cases named in docs/CLAUDE_SCENARIO_PREDICTION_PLAN.md Session 1. Other inputs are the dashboard defaults.
CASES = {
    "bay_jimmy_mapped": _bay_jimmy,          # Home > worked example: mapped cell 8018_32612, heavy oiling from the SCAT record
    "typed_marsh": lambda: _habitat("marsh", _typed_heavy),  # typed site with no site-table record (status no_site_record)
    "rocky_esi_1A": lambda: _habitat("esi_1A"),
    "mangrove": lambda: _habitat("mangrove"),
}


def _controls(at: AppTest) -> dict:
    """Visible controls and section labels after the run (keys and labels only; values that the user did not set are excluded)."""
    def labels(elems):
        return sorted({f"{getattr(e, 'key', None) or ''}|{getattr(e, 'label', '')}" for e in elems})
    out = {
        "buttons": labels(at.button),
        "selectboxes": labels(at.selectbox),
        "toggles": labels(at.toggle),
        "segmented_controls": labels(at.get("segmented_control")) if at.get("segmented_control") else [],
        "expanders": sorted({e.label for e in at.expander}),
        "radios": labels(at.radio),
        "text_inputs": labels(at.text_input),
        "tabs": sorted({t.label for t in at.tabs}),
        "n_expander_elements": len(at.expander),
        "n_charts": len(at.get("vega_lite_chart")),
        "n_maps": len(at.get("deck_gl_json_chart")),
        "n_metrics": len(at.metric),
        "n_dataframes": len(at.dataframe),
    }
    downloads = at.get("download_button")
    out["download_buttons"] = sorted({getattr(d.proto, "label", "") for d in downloads})
    return out


def _normalize(report_dict: dict) -> dict:
    v = report_dict.get("version") or {}
    for k in VOLATILE_VERSION_KEYS:
        if k in v:
            v[k] = "<volatile>"
    return report_dict


def capture(out: Path) -> dict:
    from src.shoreline_remediation import site_view as SV
    from src.shoreline_remediation.decision_pipeline import run_decision
    from src.shoreline_remediation.data_model import Scenario
    from src.shoreline_remediation.ui_pipeline import UI_DRAWS

    out.mkdir(parents=True, exist_ok=True)
    summary = {"python": platform.python_version(), "cases": {}}
    for name, drive in CASES.items():
        at = drive()
        exc = [str(e.value) for e in at.exception]
        rec = at.session_state[SV.BOARD_RUN_KEY]
        spec = rec["spec"]
        kind, *args = spec
        # Replay outside Streamlit with the same arguments the cached wrappers in ui_pipeline.py pass.
        if kind == "site":
            items, oil, season, *rest = args
            n_draws = rest[0] if rest else UI_DRAWS
            site = {k: v for k, v in items if v is not None}
            report = run_decision(site, habitat="salt_marsh", oil=oil, season=season, n_draws=n_draws)
        else:
            fields, oiling_class, oil, season, *rest = args
            habitat = rest[0] if rest else None
            n_draws = rest[1] if len(rest) > 1 else UI_DRAWS
            report = run_decision(Scenario(**dict(fields)), habitat=habitat, oiling_class=oiling_class, oil=oil, season=season,
                                  n_draws=n_draws)
        rd = _normalize(report.to_dict())
        text = json.dumps(rd, indent=2, sort_keys=True, allow_nan=False)
        (out / f"{name}.report.json").write_text(text, encoding="utf-8")
        summary["cases"][name] = {
            "spec_kind": kind,
            "spec": json.loads(json.dumps(spec, default=str)),
            "app_exceptions": exc,
            "scope_tier": report.scope_tier,
            "decision_outcome": report.decision_outcome,
            "evidence_state": report.evidence_state,
            "headline": report.headline,
            "classes": {k: v for k, v in report.classes().items() if v},
            "recommendation_summary": report.recommendation_summary,
            "abstentions": [a if isinstance(a, str) else a.get("item", a) for a in report.abstentions],
            "report_top_level_fields": sorted(rd),
            "report_sha256_normalized": hashlib.sha256(text.encode()).hexdigest(),
            "controls": _controls(at),
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True,
                    help="New or empty directory. The Session 1 baseline is results/projection_baseline and is never overwritten; "
                         "write comparison runs elsewhere (for example results/projection_baseline_session6).")
    out_dir = Path(ap.parse_args().out)
    if out_dir.exists() and any(out_dir.iterdir()):
        sys.exit(f"Refusing to write into non-empty {out_dir}: choose a fresh directory so earlier captures are preserved.")
    s = capture(out_dir)
    for k, c in s["cases"].items():
        print(f"{k}: outcome={c['decision_outcome']} scope={c['scope_tier']} classes={c['classes']} sha={c['report_sha256_normalized'][:12]}"
              f" exceptions={len(c['app_exceptions'])}")
