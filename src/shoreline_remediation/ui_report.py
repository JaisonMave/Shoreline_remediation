"""Self-contained HTML site report built from a decision-pipeline report (decision D40). No Streamlit, no network, no scripts.

Contents: headline with evidence chip, option table (class, evidence grade, source, ranges), interval bars on a shared zero line
(inline SVG), scope and limits, version block. Every value is HTML-escaped.
"""
from __future__ import annotations

from datetime import date
from html import escape

from . import ui_evidence as E
from . import ui_theme as T


def _svg_bars(rows: list, title: str) -> str:
    if not rows:
        return ""
    lo = min(0.0, min(r["lo"] for r in rows))
    hi = max(0.0, max(r["hi"] for r in rows))
    span = (hi - lo) or 1.0
    w, left, h = 640, 230, 28
    x = lambda v: left + (v - lo) / span * (w - left - 20)  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h * len(rows) + 50}" role="img" aria-label="{escape(title)}">',
           f'<text x="0" y="14" font-size="13" font-weight="600">{escape(title)}</text>',
           f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="22" y2="{h * len(rows) + 28}" stroke="#6B7280" stroke-width="2" stroke-dasharray="5 4"/>',
           f'<text x="{x(0) + 4:.1f}" y="34" font-size="11" fill="#6B7280">0 = same as natural recovery</text>']
    for i, r in enumerate(rows):
        y = 50 + i * h
        c = T.class_style(r["cls"])["colour"]
        out.append(f'<text x="0" y="{y + 4}" font-size="12">{escape(r["option"][:34])}</text>')
        out.append(f'<line x1="{x(r["lo"]):.1f}" x2="{x(r["hi"]):.1f}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="5" opacity="0.8"/>')
        out.append(f'<circle cx="{x(r["median"]):.1f}" cy="{y}" r="5" fill="{c}" stroke="#fff"/>')
    out.append("</svg>")
    return "".join(out)


def _comparison_html(comparisons) -> str:
    """Field comparisons with natural recovery, from the same comparison.table_records() the dashboard draws. Text only."""
    from . import comparison as K
    blocks = []
    for comp in comparisons or []:
        if not comp.applicable or not any(r.est.has_value for r in comp.rows):
            continue
        cols = ("Method", "Outcome", "Time", "Comparator", "Estimate", "Evidence basis", "Screening status", "In the order", "Why not ranked")
        body = "".join("<tr>" + "".join(f"<td>{escape(str(rec[c]))}</td>" for c in cols) + "</tr>" for rec in K.table_records(comp))
        blocks.append(f"<h3>{escape(comp.title)}</h3><p>{escape(K.finding(comp))} {escape(K.design_limit(comp))}</p>"
                      f"<table><thead><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr></thead><tbody>{body}</tbody></table>"
                      f"<p class=\"sr-muted\">{escape(K.source_caption(comp))} {escape(comp.order_note)}</p>")
    if not blocks:
        return ""
    return ("<h2>Field comparisons with untreated oiled plots</h2><p>Screening status and the performance order are separate: a large "
            "estimate does not change a status. Excluded methods are listed with their historical value and are never ranked. "
            "No model estimate is admitted to the order.</p>" + "".join(blocks))


def build_html(view, title: str = "Shoreline Remediation Decision Support", habitat: str = "marsh", comparisons=None) -> str:
    rows = []
    for o in view.options:
        nums = "; ".join(f"{x.label}, year {x.year}: {E.fmt_interval(x.median, x.lo, x.hi, 2)}" for x in o.decision_outcomes())
        rows.append(f"<tr><td>{T.class_html(o.cls, with_name=False)}</td><td>{escape(o.category_label)}</td><td>{escape(o.name)}</td><td>{T.grade_html(o.grade)}</td>"
                    f"<td>{escape(o.verdict_text)}</td><td>{escape(nums) or '-'}</td><td>{escape(o.source_text)}</td></tr>")
    charts = ""
    for outcome, years in E.available_outcomes(view.options).items():
        label, _ = E.OUTCOME_LABELS.get(outcome, (E.plain_name(outcome), ""))
        charts += _svg_bars(E.interval_rows(view.options, outcome, years[-1]), f"{label}, year {years[-1]} (90% range, right of zero is better)")
    limits = "".join(f"<li>{escape(x)}</li>" for x in T.SCOPE_LIMITS.get(habitat if habitat in T.SCOPE_LIMITS else "beach", []))
    legend = "".join(f"<p>{T.grade_html(k)} {escape(T.GRADES[k]['legend'])}</p>" for k in T.GRADE_ORDER)
    outcome = (f"<p><b>Decision outcome:</b> {escape(view.decision_outcome_label)}</p>" if view.decision_outcome_label else "")
    abstain = ""
    if view.abstentions:
        items = "".join(f"<li>{escape(str(E.field(a, 'text', a)))}</li>" for a in view.abstentions)
        abstain = f"<h2>What this report does not state</h2><ul>{items}</ul>"
    version = E.field(view.extra, "version", {}) or {}
    ver = ", ".join(f"{k}: {version[k]}" for k in ("pipeline_version", "git_commit", "seed", "n_draws") if k in version)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{T.COMPONENT_CSS}
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1B2A30}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{border-bottom:1px solid #ccc;padding:.35rem .5rem;text-align:left;vertical-align:top}}</style></head>
<body><h1>{escape(title)}</h1><p class="sr-muted">Report date {date.today().isoformat()}. {escape(ver)}</p>
<h2>Recommendation</h2><p class="sr-answer">{escape(view.headline)}</p>
<p>Evidence behind this recommendation: {T.grade_html(view.headline_grade, view.headline_grade_text)}
 Scope for this input: {T.grade_html(view.tier_grade, view.tier_text)}</p><p>{escape(view.scope_message)}</p>
{outcome}{abstain}
<h2>Options</h2><table><thead><tr><th>Class</th><th>Category</th><th>Option</th><th>Evidence</th><th>Verdict</th><th>Numbers</th><th>Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
{_comparison_html(comparisons)}
<h2>Scenario-composer differences from natural recovery (experimental)</h2>{charts or '<p>No option has a numerical forecast for this input.</p>'}
<p class="sr-muted">{escape(T.LABELS['interval_note'])}</p>
<h2>Scope and limits</h2><ul>{limits}</ul><h2>Evidence grades</h2>{legend}
</body></html>"""
