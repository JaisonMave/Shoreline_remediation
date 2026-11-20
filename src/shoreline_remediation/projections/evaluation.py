"""Protocol P-RET-1 (docs/PROJECTION_RETREAT_PROTOCOL.md sections 5 to 7): pseudo-prospective scoring of retreat rate rules.

Implements the protocol as written; nothing here was chosen after seeing results.

- Data: heavily oiled untreated Bay Jimmy plots (n = 9) with the 4 Dec 2010 origin, from recovery_trajectories.field_positions().
- Cutoffs c: 2012-09-17, 2013-09-08, 2014-09-26, 2015-09-30. Targets: every later survey (10 pairs, lead 0.97 to 4.05 yr).
- Forecast of the group-mean increment R(t) - R(c) = rate x (t - c). Every rate uses only surveys on or before c.
    B0 last-observation persistence (rate 0)                                       baseline
    B1 least-squares slope through the origin of plot increments, surveys <= c      baseline (primary comparator)
    C1 recent-interval rate of the group means: (R(c) - R(c_prev)) / (c - c_prev)   candidate
    C2 M1 long-run rate b fitted to surveys <= c; eligible only for c >= 2013-09-08; a cutoff where tau sits at a bound is
       'not identified' and its pairs are not scored                                candidate
- Each candidate is compared with B0 and B1 on exactly the pairs that candidate scores.
- Criteria (Delta = 0.5 m, owner-confirmed before scoring): (1) MAE(C) <= MAE(B1) - Delta; (2) MAE(C) <= MAE(B1) in every lead bin
  with >= 2 pairs; (3) |bias(C)| <= |bias(B1)| + 0.25 m; (4) MAE(B1) < MAE(B0). A candidate passes only if all four pass.
- Intervals: whole-plot cluster bootstrap, seed 20261120, 2000 draws (descriptive; not part of the criteria).

Pairs share plots and overlapping periods; they are not independent tests. A pass would cover these plots and the tested lead
times only.
"""
from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd

PROTOCOL = "P-RET-1"
DELTA_M = 0.5
BIAS_MARGIN_M = 0.25
CUTOFFS = ("2012-09-17", "2013-09-08", "2014-09-26", "2015-09-30")
C2_FIRST_CUTOFF = "2013-09-08"
BINS = ((0.0, 1.5, "<1.5 yr"), (1.5, 2.5, "1.5-2.5 yr"), (2.5, 3.5, "2.5-3.5 yr"), (3.5, math.inf, ">3.5 yr"))
SEED, N_BOOT = 20261120, 2000
RULES = ("B0", "B1", "C1", "C2")
CANDIDATES = ("C1", "C2")
RULE_TEXT = {
    "B0": "last-observation persistence (rate 0)",
    "B1": "constant rate: LS slope through the origin of plot increments, surveys <= cutoff",
    "C1": "recent-interval rate of the group means, last two surveys <= cutoff",
    "C2": "M1 (fading-excess) long-run rate b, fitted to surveys <= cutoff",
}
JUMP_TARGET = "2016-10-05"     # the 2015-2016 interval contains a jump shared with the reference plots (protocol section 5)


def untreated_plots() -> pd.DataFrame:
    from src.shoreline_remediation import recovery_trajectories as T
    d = T.field_positions()
    g = d[(d.key == "untreated") & np.isclose(d.t0, 0.0)].copy()
    g["d"] = g.date.dt.date.map(dt.date.isoformat)
    return g[["pid", "d", "t", "t0", "inc"]].reset_index(drop=True)


def lead_bin(lead: float) -> str:
    return next(name for lo, hi, name in BINS if lo <= lead < hi)


def rates_at(g: pd.DataFrame, cutoff: str) -> dict:
    """Rates of every rule from the surveys on or before `cutoff`. Values are floats or (None, reason)."""
    from src.shoreline_remediation import recovery_trajectories as T
    tr = g[g.d <= cutoff]
    means = tr.groupby(["d", "t"]).inc.mean().reset_index().sort_values("t")
    out = {"B0": (0.0, "")}
    b1 = T._retreat_fit(tr, "M0")
    out["B1"] = (float(b1[0]), "") if b1 is not None else (None, "M0 fit did not converge")
    last, prev = means.iloc[-1], means.iloc[-2]
    out["C1"] = (float((last.inc - prev.inc) / (last.t - prev.t)), "")
    if cutoff < C2_FIRST_CUTOFF:
        out["C2"] = (None, "fewer than three post-origin surveys at this cutoff (protocol: C2 eligible from 2013-09-08)")
    else:
        th = T._retreat_fit(tr, "M1")
        lo, hi = T.RETREAT_MODELS["M1"][2][2], T.RETREAT_MODELS["M1"][3][2]
        if th is None:
            out["C2"] = (None, "M1 fit did not converge")
        elif np.isclose(th[2], lo) or np.isclose(th[2], hi):
            out["C2"] = (None, f"not identified: tau = {th[2]:.3g} yr at its bound [{lo}, {hi}] (b = {th[0]:.3f}, A = {th[1]:.3f})")
        else:
            out["C2"] = (float(th[0]), "")
            lb, ub = T.RETREAT_MODELS["M1"][2], T.RETREAT_MODELS["M1"][3]
            at = [n for n, v, a, z in zip(("b", "A", "tau"), th, lb, ub) if np.isclose(v, a, atol=1e-4) or np.isclose(v, z, atol=1e-4)]
            out["C2_params"] = {"b": float(th[0]), "A": float(th[1]), "tau": float(th[2]), "params_at_bound": ",".join(at)}
    return out


def score_pairs(g: pd.DataFrame) -> tuple:
    """Long table (one row per rule x pair) and the rate table (one row per rule x cutoff)."""
    means = g.groupby(["d", "t"]).inc.mean().reset_index().set_index("d")
    plots = g.pivot_table(index="pid", columns="d", values="inc")
    rows, rate_rows = [], []
    for c in CUTOFFS:
        r = rates_at(g, c)
        for rule in RULES:
            v, why = r[rule]
            rate_rows.append({"cutoff": c, "rule": rule, "rate_m_per_yr": v, "omitted_reason": why,
                              **({k: r["C2_params"][k] for k in ("b", "A", "tau", "params_at_bound")}
                                 if rule == "C2" and "C2_params" in r else {})})
        for t_d in [d for d in means.index if d > c]:
            lead = float(means.loc[t_d, "t"] - means.loc[c, "t"])
            obs = float(means.loc[t_d, "inc"] - means.loc[c, "inc"])
            plot_obs = (plots[t_d] - plots[c]).to_numpy()
            for rule in RULES:
                v, why = r[rule]
                base = {"cutoff": c, "target": t_d, "lead_years": lead, "lead_bin": lead_bin(lead), "rule": rule,
                        "observed_increment_m": obs, "target_is_2016": t_d == JUMP_TARGET}
                if v is None:
                    rows.append({**base, "scored": False, "omitted_reason": why, "rate_m_per_yr": None, "forecast_increment_m": None,
                                 "error_m": None, "abs_error_m": None, "plot_mae_m": None})
                else:
                    f = v * lead
                    rows.append({**base, "scored": True, "omitted_reason": "", "rate_m_per_yr": v, "forecast_increment_m": f,
                                 "error_m": f - obs, "abs_error_m": abs(f - obs),
                                 "plot_mae_m": float(np.mean(np.abs(f - plot_obs)))})
    return pd.DataFrame(rows), pd.DataFrame(rate_rows)


def _stats(p: pd.DataFrame, rule: str, keys: list) -> dict:
    s = p[(p.rule == rule)].set_index(["cutoff", "target"]).loc[keys]
    return {"mae_m": float(s.abs_error_m.mean()), "bias_m": float(s.error_m.mean()), "plot_mae_m": float(s.plot_mae_m.mean())}


def summarise(p: pd.DataFrame) -> dict:
    out = {}
    for cand in CANDIDATES:
        cp = p[(p.rule == cand)]
        keys = list(cp[cp.scored].set_index(["cutoff", "target"]).index)
        omitted = [{"cutoff": r.cutoff, "target": r.target, "reason": r.omitted_reason} for r in cp[~cp.scored].itertuples()]
        if not keys:
            out[cand] = {"n_pairs": 0, "omitted_pairs": omitted, "verdict": "unevaluable: no scored pairs"}
            continue
        st = {rule: _stats(p, rule, keys) for rule in ("B0", "B1", cand)}
        sub = p[p.rule.isin(("B0", "B1", cand))].set_index(["cutoff", "target"]).loc[keys].reset_index()
        bins = []
        for _, _, name in BINS:
            b = sub[sub.lead_bin == name]
            n = int(b[b.rule == cand].shape[0])
            if n == 0:
                continue
            row = {"lead_bin": name, "n_pairs": n}
            for rule in ("B0", "B1", cand):
                x = b[b.rule == rule]
                row[f"mae_{rule}_m"], row[f"bias_{rule}_m"] = float(x.abs_error_m.mean()), float(x.error_m.mean())
            bins.append(row)
        eligible_bins = [b for b in bins if b["n_pairs"] >= 2]
        c1 = st[cand]["mae_m"] <= st["B1"]["mae_m"] - DELTA_M
        c2 = None if not eligible_bins else all(b[f"mae_{cand}_m"] <= b["mae_B1_m"] for b in eligible_bins)
        c3 = abs(st[cand]["bias_m"]) <= abs(st["B1"]["bias_m"]) + BIAS_MARGIN_M
        c4 = st["B1"]["mae_m"] < st["B0"]["mae_m"]
        crit = {
            "1_mae_gain_at_least_delta": {"result": "pass" if c1 else "fail",
                                          "detail": f"MAE {cand} {st[cand]['mae_m']:.3f} vs B1 {st['B1']['mae_m']:.3f} - {DELTA_M} = "
                                                    f"{st['B1']['mae_m'] - DELTA_M:.3f} m"},
            "2_no_worse_than_B1_in_bins_with_2plus_pairs": {
                "result": "unevaluable" if c2 is None else ("pass" if c2 else "fail"),
                "detail": ("no lead bin has two or more pairs" if c2 is None else
                           "; ".join(f"{b['lead_bin']} (n {b['n_pairs']}): {cand} {b[f'mae_{cand}_m']:.3f} vs B1 {b['mae_B1_m']:.3f}"
                                     for b in eligible_bins))},
            "3_bias_not_worse_than_B1_plus_0.25": {"result": "pass" if c3 else "fail",
                                                   "detail": f"|bias {cand}| {abs(st[cand]['bias_m']):.3f} vs |bias B1| + 0.25 = "
                                                             f"{abs(st['B1']['bias_m']) + BIAS_MARGIN_M:.3f} m"},
            "4_B1_beats_B0": {"result": "pass" if c4 else "fail",
                              "detail": f"MAE B1 {st['B1']['mae_m']:.3f} vs B0 {st['B0']['mae_m']:.3f} m on the same pairs"},
        }
        results = [v["result"] for v in crit.values()]
        verdict = ("pass" if all(r == "pass" for r in results) else
                   "fail" if "fail" in results else "not established (a criterion is unevaluable)")
        no_jump = [k for k in keys if k[1] != JUMP_TARGET]
        sens = ({rule: _stats(p, rule, no_jump) for rule in ("B0", "B1", cand)} | {"n_pairs": len(no_jump)}) if no_jump else None
        out[cand] = {
            "rule": RULE_TEXT[cand], "n_pairs": len(keys), "omitted_pairs": omitted,
            "longest_lead_scored_years": float(cp[cp.scored].lead_years.max()),
            "mae_m": {r: st[r]["mae_m"] for r in st}, "bias_m": {r: st[r]["bias_m"] for r in st},
            "plot_level_mae_m": {r: st[r]["plot_mae_m"] for r in st},
            "mae_difference_candidate_minus_B1_m": st[cand]["mae_m"] - st["B1"]["mae_m"],
            "mae_difference_candidate_minus_B0_m": st[cand]["mae_m"] - st["B0"]["mae_m"],
            "by_lead_bin": bins, "criteria": crit, "verdict": verdict,
            "sensitivity_without_2016_targets": sens,
        }
    return out


def bootstrap(g: pd.DataFrame, summary: dict, n: int = N_BOOT, seed: int = SEED) -> dict:
    """Whole-plot cluster bootstrap of MAE differences on each candidate's scored pairs (descriptive, not a criterion)."""
    from src.shoreline_remediation import recovery_trajectories as T
    rng = np.random.default_rng(seed)
    draw = T._resampler(g)
    diffs = {c: [] for c in CANDIDATES}
    b1b0, invalid = [], {c: 0 for c in CANDIDATES}
    for _ in range(n):
        b = draw(rng)
        b["pid"] = b.pid.astype(str)
        p, _ = score_pairs(b)
        for c in CANDIDATES:
            if summary[c]["n_pairs"] == 0:
                continue
            want = p[(p.rule == c)]
            # same pairs as the point estimate: pairs omitted there stay omitted; a draw that loses one of them is counted
            scored_keys = set(map(tuple, want[want.scored][["cutoff", "target"]].values))
            ref = set(_scored_keys(summary, c))
            if not ref <= scored_keys:
                invalid[c] += 1
                continue
            sel = lambda r: p[(p.rule == r)].set_index(["cutoff", "target"]).loc[sorted(ref)]  # noqa: E731
            diffs[c].append(float(sel(c).abs_error_m.mean() - sel("B1").abs_error_m.mean()))
        allp = p[p.rule.isin(("B0", "B1"))]
        b1b0.append(float(allp[allp.rule == "B1"].abs_error_m.mean() - allp[allp.rule == "B0"].abs_error_m.mean()))
    pct = lambda a: [float(np.percentile(a, 5)), float(np.percentile(a, 95))] if len(a) else None  # noqa: E731
    return {"method": f"whole-plot cluster bootstrap, {n} draws, seed {seed}; 90% percentile intervals; descriptive only",
            "mae_difference_candidate_minus_B1_m_90": {c: pct(diffs[c]) for c in CANDIDATES},
            "draws_dropped_pair_not_scored": invalid,
            "mae_difference_B1_minus_B0_m_90_all_pairs": pct(b1b0)}


def _scored_keys(summary: dict, cand: str) -> list:
    return summary[cand].get("_keys", [])


def c2_identification(rates: pd.DataFrame) -> dict:
    """Diagnostic reported beside the protocol result: the protocol's identification rule checks tau only; this records any other
    M1 parameter at a bound at the scored cutoffs. It does not change which pairs were scored."""
    r = rates[(rates.rule == "C2") & rates.rate_m_per_yr.notna()]
    rows = [{"cutoff": x.cutoff, "b": x.b, "A": x.A, "tau": x.tau, "params_at_bound": x.params_at_bound} for x in r.itertuples()]
    flagged = [x["cutoff"] for x in rows if x["params_at_bound"]]
    return {"protocol_rule": "tau at a bound -> not identified (protocol section 6)", "fits": rows,
            "cutoffs_with_a_parameter_at_bound": flagged,
            "finding": (f"At {len(flagged)} of {len(rows)} scored cutoffs an M1 parameter sits at its bound "
                        f"({', '.join(sorted({x['params_at_bound'] for x in rows if x['params_at_bound']}))}) and b is "
                        f"{'negative (net advance)' if all(x['b'] < 0 for x in rows) else 'as listed'}: the long-run rate is not "
                        "identified in substance, although tau is inside its bounds. The protocol's rule did not catch this; C2 is "
                        "scored as specified, and under a bound-aware reading C2 would have no scored pairs (unevaluable)."
                        if flagged else "No M1 parameter at a bound at the scored cutoffs.")}


def evaluate(n_boot: int = N_BOOT) -> dict:
    g = untreated_plots()
    pairs, rates = score_pairs(g)
    summary = summarise(pairs)
    summary["C2"]["identification_diagnostic"] = c2_identification(rates)
    for c in CANDIDATES:
        cp = pairs[(pairs.rule == c) & pairs.scored]
        summary[c]["_keys"] = list(map(tuple, cp[["cutoff", "target"]].values))
    boot = bootstrap(g, summary, n_boot) if n_boot else None
    for c in CANDIDATES:
        summary[c].pop("_keys", None)
    return {"pairs": pairs, "rates": rates, "summary": summary, "bootstrap": boot,
            "data": {"n_plots": int(g.pid.nunique()), "survey_dates": sorted(g.d.unique().tolist())}}
