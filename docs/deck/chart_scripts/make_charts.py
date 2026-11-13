"""Makes the deck charts from the results CSVs. Run: python3 make_charts.py  (needs matplotlib, pandas, numpy)."""
import json, numpy as np, pandas as pd
from style import *
R = REPO + "results/"

# 1 P1 checks -----------------------------------------------------------------------------------
c = pd.read_csv(R+"p1_prespill/checks.csv"); e = pd.read_csv(R+"p1_prespill/exploratory.csv")
labels = ["0 NAIP 2010-2015\n(as first published)", "1 Landsat 2008-2015\n(second sensor)", "2 Landsat 1999-2008\n(before any oil)",
          "3 After minus before\n(pre-specified headline)", "4 NAIP + finer exposure", "E1 After minus before\n+ finer exposure", "E2 Landsat 2008-2015\n+ finer exposure", "E3 Landsat 1999-2008\n+ finer exposure"]
d = pd.concat([c, e]).reset_index(drop=True)
f, ax = fig(); y = np.arange(len(d))[::-1]
cols = [WATER]*5 + [GREY]*3
for yi, r, col in zip(y, d.itertuples(), cols):
    ax.errorbar(r.heavy_effect, yi, xerr=[[r.heavy_effect-r.lo], [r.hi-r.heavy_effect]], fmt="o", color=col, capsize=6, lw=3, ms=11)
    ax.text(1.62, yi, f"{r.heavy_effect:.2f} ({r.lo:.2f} to {r.hi:.2f})", va="center", fontsize=19)
ax.axvline(0, color=INK, lw=1.5); ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=19); ax.set_xlim(-0.3, 2.6)
ax.set_xlabel("Heavy minus clean edge loss, same 2 km block (m/yr, 90% interval)")
ax.set_title("P1: heavy minus clean edge loss, by check")
save(f, "p1_checks")

# 2 P2 held-out error --------------------------------------------------------------------------
pb = pd.read_csv(R+"p2_basin_holdout/per_basin.csv").dropna(subset=["MAE_M0"]); po = pd.read_csv(R+"p2_basin_holdout/pooled.csv").iloc[0]
groups = ["Barataria", "Western Breton", "Pooled"]
vals = {"M0 no predictor": [pb.MAE_M0.iloc[0], pb.MAE_M0.iloc[1], po.MAE_M0], "M1 exposure + trend": [pb.MAE_M1.iloc[0], pb.MAE_M1.iloc[1], po.MAE_M1],
        "M2 + oiling class": [pb.MAE_M2.iloc[0], pb.MAE_M2.iloc[1], po.MAE_M2], "M3 boosted trees": [pb.MAE_M3.iloc[0], pb.MAE_M3.iloc[1], po.MAE_M3]}
f, ax = fig(); w = 0.2; x = np.arange(3)
for i, ((k, v), col) in enumerate(zip(vals.items(), [GREY, WATER, OIL, "#9AA7AB"])):
    b = ax.bar(x + (i-1.5)*w, v, w, label=k, color=col)
    for xi, vi in zip(x + (i-1.5)*w, v): ax.text(xi, vi+0.02, f"{vi:.2f}", ha="center", fontsize=19)
cov = [pb.coverage_90.iloc[0], pb.coverage_90.iloc[1], po.coverage_90]
ax.set_xticks(x); ax.set_xticklabels([f"{g}\n90% interval coverage {c_*100:.0f}%" for g, c_ in zip(groups, cov)])
ax.set_ylabel("Held-out error, MAE (m/yr)"); ax.set_ylim(0, 1.8); ax.legend(ncol=2, loc="upper right")
ax.set_title("P2: held-out error by basin and model")
save(f, "p2_heldout_error")

# 3 P3 treatment contrasts ---------------------------------------------------------------------
a = pd.read_csv(R+"p3_treatment/A_prespill_adjusted.csv")
names = {"Manual minus Oiled, untreated": "Manual vs untreated", "Mechanical minus Oiled, untreated": "Mechanical vs untreated",
         "Mechanical + planted minus Oiled, untreated": "Mechanical + planting vs untreated", "Oiled, untreated minus Reference (unoiled)": "Oiled untreated vs unoiled reference"}
f, ax = fig(); order = list(names)[::-1]; y0 = np.arange(len(order))
for off, per, col, lab in [(0.17, "A 2010-2012 minus 2005-2010 (primary)", OIL, "2010-2012 (primary)"), (-0.17, "A 2012-2018 minus 2005-2010 (secondary)", WATER, "2012-2018")]:
    s = a[a.analysis == per].set_index("contrast").loc[order]
    ax.errorbar(s["difference"], y0+off, xerr=[s["difference"]-s.lo90, s.hi90-s["difference"]], fmt="o", color=col, capsize=6, lw=3, ms=11, label=lab)
    for yi, (_, r) in zip(y0+off, s.iterrows()): ax.text(2.55, yi, f"{r['difference']:+.2f}", va="center", fontsize=19, color=col)
ax.axvline(0, color=INK, lw=1.5); ax.set_yticks(y0); ax.set_yticklabels([names[o] for o in order], fontsize=19); ax.set_xlim(-2.4, 3.1)
ax.set_xlabel("Change vs own 2005-2010 rate (m/yr, 90% interval)"); ax.legend(loc="center right")
ax.set_title("P3: erosion change by cleanup group")
save(f, "p3_treatment_contrasts")

# 4 edge loss by oiling class ------------------------------------------------------------------
k = pd.read_csv(R+"naip_edge_loss/coefficients.csv"); k = k[k.term.isin(["Very_Light", "Light", "Moderate", "Heavy"])]
f, ax = fig(); x = np.arange(4)
for off, per, col in [(-0.18, "2010-2015", OIL), (0.18, "2010-2017", WATER)]:
    s = k[k.period == per].set_index("term").loc[["Very_Light", "Light", "Moderate", "Heavy"]]
    ax.bar(x+off, s.estimate, 0.34, color=col, label=per, yerr=[s.estimate-s.lo, s.hi-s.estimate], capsize=7, error_kw=dict(lw=2.5, ecolor=INK))
    for xi, v in zip(x+off, s.estimate): ax.text(xi, -0.38, f"{v:.2f}", ha="center", fontsize=19)
ax.set_xticks(x); ax.set_xticklabels(["Very light", "Light", "Moderate", "Heavy"]); ax.axhline(0, color=INK, lw=1.2); ax.set_ylim(-0.5, 1.7)
ax.set_ylabel("Extra edge loss vs clean edge in the same 2 km block (m/yr, 90% interval)"); ax.legend(title="NAIP period")
ax.set_title("First NAIP estimate: extra edge loss by oiling class")
save(f, "edge_loss_by_class")

# 5 coverage C1 / C2 / B1 ----------------------------------------------------------------------
c1 = pd.read_csv(R+"scenario_composer/c1_coverage.csv"); c2 = pd.read_csv(R+"scenario_composer/c2_block_coverage.csv"); b1 = pd.read_csv(R+"scenario_composer/b1_horizon_coverage.csv")
items = [("C1 heavy cells, Barataria", c1.coverage[0]), ("C1 heavy cells, Breton", c1.coverage[1]), ("C2 blocks, Barataria", c2.coverage[0]), ("C2 blocks, Breton", c2.coverage[1])]
items += [("B1 cells (7 y), all", b1.coverage[0]), ("B1 blocks (7 y)", b1.coverage[1]), ("B1 heavy cells", b1.coverage[2]), ("B1 Light", b1.coverage[3]), ("B1 Moderate", b1.coverage[4]), ("B1 No oil observed", b1.coverage[5]), ("B1 Very light", b1.coverage[6])]
n = [c1.n_heavy_cells[0], c1.n_heavy_cells[1], c2.n_blocks[0], c2.n_blocks[1]] + list(b1.n)
f, ax = fig(); y = np.arange(len(items))[::-1]
ax.axvspan(80, 97, color=MARSH, alpha=0.18); ax.barh(y, [v*100 for _, v in items], color=[WATER]*4+[OIL]*7, height=0.65)
for yi, (l, v), nn in zip(y, items, n): ax.text(v*100+0.6, yi, f"{v*100:.0f}%  (n = {int(nn):,})", va="center", fontsize=19)
ax.axvline(90, color=INK, lw=1.5, ls="--"); ax.set_yticks(y); ax.set_yticklabels([l for l, _ in items], fontsize=19); ax.set_xlim(60, 116)
ax.set_xlabel("Share of observed values inside the composed 90% range (%)  [dashed line = nominal 90%]")
ax.set_title("Coverage of the composed 90% ranges")
save(f, "coverage_c1_c2_b1")

# 6 worked block paired differences ------------------------------------------------------------
w = pd.read_csv(R+"scenario_composer/worked_block.csv"); w = w[(w.year == 8) & (w.outcome == "cumulative_area_lost_ha")]
opt = ["manual_removal", "mechanical_removal", "planting (after mechanical cleanup)", "bioremediation", "low_pressure_flushing", "surface_washing_agents", "passive_sorbents", "vacuum_removal", "high_pressure_washing"]
lab = ["Manual removal", "Mechanical removal", "Mechanical + planting", "Nutrient addition (elicited)", "Low-pressure flushing (elicited)", "Shoreline cleaners (elicited)", "Passive sorbents (elicited)", "Vacuum (elicited)", "High-pressure washing (elicited)"]
s = w.set_index("option").loc[opt]; f, ax = fig(); y = np.arange(len(opt))[::-1]
for yi, (_, r), col in zip(y, s.iterrows(), [MARSH]*3+[GREY]*6):
    m, lo, hi = r.paired_diff_area_ha_y8_median, r.paired_diff_area_ha_y8_lo90, r.paired_diff_area_ha_y8_hi90
    ax.errorbar(m, yi, xerr=[[m-lo], [hi-m]], fmt="o", color=OIL if r.area_distinguished_y8 is True or str(r.area_distinguished_y8) == "True" else col, capsize=6, lw=3, ms=11)
    ax.text(1.9, yi, f"{m:+.1f} ({lo:.1f} to {hi:.1f})", va="center", fontsize=19)
ax.axvline(0, color=INK, lw=1.5); ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=19); ax.set_xlim(-5, 4.6)
ax.set_xlabel("Marsh area lost by year 8, difference from natural recovery (ha, 90% interval)")
ax.set_title("Worked block: difference from natural recovery")
ax.text(-4.9, 3.5, "Orange: interval excludes zero.\nElicited options carry no edge-loss\neffect by design (expert ranges,\nnot measurements).", fontsize=19, color=GREY, ha="left", va="center")
save(f, "worked_block_paired")

# 7 vegetation recovery curve ------------------------------------------------------------------
m = json.load(open(REPO+"models/veg_recovery_v1.json")); u = pd.read_csv(R+"veg_recovery/units.csv")
A, tau = m["parameters"]["A"], m["parameters"]["tau"]; bd = m["bootstrap_draws"]; ba, bt = np.array(bd["A"]), np.array(bd["tau"])
t = np.linspace(0, 8, 200); curves = np.exp(-ba[:, None]*np.exp(-t[None, :]/bt[:, None]))
lo, hi = np.percentile(curves, 5, axis=0), np.percentile(curves, 95, axis=0)
f, ax = fig(); ax.fill_between(t, lo*100, hi*100, color=MARSH, alpha=0.22, label="90% band (bootstrap over studies)")
ax.plot(t, np.exp(-A*np.exp(-t/tau))*100, color=MARSH, lw=4, label="M2 curve, all 9 studies")
studies = sorted(u.study.unique()); cmap = plt.get_cmap("tab10")
for i, st in enumerate(studies):
    q = u[u.study == st]; ax.scatter(q.t, np.exp(q.lnRR)*100, s=90, color=cmap(i), edgecolor=INK, lw=0.8, label=st, zorder=3)
ax.axhline(100, color=INK, lw=1.2, ls="--"); ax.axhline(80, color=OIL, lw=1.5, ls=":"); ax.set_ylim(0, 240); ax.set_xlim(0, 8)
ax.text(7.9, 82, "80% of reference", color=OIL, ha="right", va="bottom", fontsize=19)
ax.set_xlabel("Years since oiling"); ax.set_ylabel("Oiled cover as % of reference cover"); ax.legend(ncol=3, fontsize=19, loc="upper right")
ax.set_title("A1: oiled cover relative to reference")
save(f, "veg_recovery_curve")

# 8 PAH half-life --------------------------------------------------------------------------------
p = pd.read_csv(R+"pah_decline/by_oiling_class.csv"); p = p[p.stratum_type == "oiling_class"]
f, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100, sharey=True); cls = ["heavy", "moderate", "light", "very_light", "none"]; nm = ["Heavy", "Moderate", "Light", "Very light", "No oil observed"]
for ax, outc, ttl in [(axs[0], "PAH sum", "Sum of PAH compounds"), (axs[1], "PAH sum / hopane", "PAH / hopane ratio")]:
    s = p[p.outcome == outc].set_index("stratum").loc[cls]; y = np.arange(5)[::-1]
    for yi, (_, r) in zip(y, s.iterrows()):
        hl, lo, hi = r.half_life_years, r.half_life_lo90, r.half_life_hi90
        if np.isfinite(hl):
            top = hi if np.isfinite(hi) else 40
            ax.errorbar(hl, yi, xerr=[[hl-lo], [top-hl]], fmt="o", color=OIL if outc == "PAH sum" else WATER, capsize=6, lw=3, ms=11)
            ax.text(min(top, 40)+0.8, yi, f"{hl:.1f}" + ("" if np.isfinite(hi) else " (upper: no decline)"), va="center", fontsize=19)
        else:
            ax.text(1.0, yi, "no decline", va="center", fontsize=19, color=GREY)
    ax.set_xlim(0, 60); ax.set_ylim(-0.6, 4.6); ax.set_title(ttl, fontsize=24); ax.set_xlabel("Half-life (years, 90% interval)")
axs[0].set_yticks(np.arange(5)[::-1]); axs[0].set_yticklabels(nm)
f.suptitle("Soil PAH half-life by oiling class", x=0.01, ha="left", fontsize=26, fontweight="bold")
save(f, "pah_half_life")

# 9 PAH station medians by campaign -------------------------------------------------------------
sc = pd.read_csv(R+"pah_decline/station_campaign.csv"); order = ["Spring2011", "Fall2011", "Fall2012", "Fall2013"]
sc = sc[sc.campaign.isin(order)]; sc["x"] = sc.campaign.map({c_: i for i, c_ in enumerate(order)})
rng = np.random.default_rng(1)
f, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100)
for ax, col, ttl in [(axs[0], "pah_sum", "PAH sum (ppb dry weight, log scale)"), (axs[1], "ratio", "PAH / hopane ratio (log scale)")]:
    for cl, colr in [("heavy", OIL), ("none", WATER)]:
        q = sc[sc.oil_class == cl].dropna(subset=[col]); q = q[q[col] > 0]
        g = q.groupby("x")[col]; med = g.median(); lo_ = g.quantile(0.05); hi_ = g.quantile(0.95)
        ax.errorbar(med.index + (0.08 if cl == "none" else -0.08), med.values, yerr=[med.values-lo_.values, hi_.values-med.values], fmt="-o", color=colr, capsize=6, lw=3, ms=10, label=("Heavy" if cl == "heavy" else "No oil observed") + f" (n = {q.station.nunique()} stations)")
    ax.set_yscale("log"); ax.set_xticks(range(4)); ax.set_xticklabels(["Spring\n2011", "Fall\n2011", "Fall\n2012", "Fall\n2013"], fontsize=26); ax.set_title(ttl, fontsize=24)
axs[0].legend(loc="upper right", fontsize=19)
f.suptitle("PAH station medians by campaign (bars: 5th-95th percentile of stations)", x=0.01, ha="left", fontsize=26, fontweight="bold")
save(f, "pah_station_medians")

# 10 mangrove effect by year -------------------------------------------------------------------
mg = pd.read_csv(R+"mangrove/effect_by_year.csv"); f, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100)
for ax, outc, ttl, col, yl in [(axs[0], "root_documented_dead_share", "Share of prop roots dead", OIL, "Oiled minus unoiled (share)"), (axs[1], "leaves_per_shoot", "Leaves per shoot", MARSH, "Oiled minus unoiled (leaves)")]:
    s = mg[mg.outcome == outc]
    ax.errorbar(s.year_since_spill, s.effect, yerr=[s.effect-s.lo90, s.hi90-s.effect], fmt="-o", color=col, capsize=7, lw=3, ms=11)
    ax.axhline(0, color=INK, lw=1.3); ax.set_xticks(range(1, 6)); ax.set_xlabel("Years since the 1986 spill"); ax.set_ylabel(yl); ax.set_title(ttl, fontsize=24)
fig_ = f; f.suptitle("Galeta mangroves: oiled minus unoiled (90% interval)", x=0.01, ha="left", fontsize=26, fontweight="bold")
save(f, "mangrove_effect_by_year")

# 11 soil layer check ---------------------------------------------------------------------------
sl = pd.read_csv(R+"soil_layer_check/agreement.csv"); sl = sl[(sl.scope == "all_sites") & sl.variable.isin(["bulk_density_g_cm3", "om_pct", "ph"])]
f, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100); vn = {"bulk_density_g_cm3": "Bulk density", "om_pct": "Organic matter", "ph": "pH"}
y = 0; ticks = []; labs = []
for v in vn:
    for prod, col in [("ssurgo", WATER), ("soilgrids", OIL)]:
        r = sl[(sl.variable == v) & (sl["product"] == prod)].iloc[0]
        axs[0].errorbar(r.spearman, y, xerr=[[r.spearman-r.spearman_lo], [r.spearman_hi-r.spearman]], fmt="o", color=col, capsize=6, lw=3, ms=11)
        axs[1].bar(y, r.mae, color=col, width=0.6); axs[1].plot([y-0.3, y+0.3], [r.baseline_mae]*2, color=INK, lw=4)
        ticks.append(y); labs.append(f"{vn[v]}\n{'SSURGO' if prod == 'ssurgo' else 'SoilGrids'}"); y += 1
axs[0].axvline(0, color=INK, lw=1.3); axs[0].set_yticks(ticks); axs[0].set_yticklabels(labs, fontsize=19); axs[0].invert_yaxis(); axs[0].set_xlabel("Spearman rank agreement (90% interval)"); axs[0].set_title("Rank agreement", fontsize=19)
axs[1].set_xticks([0.5, 2.5, 4.5]); axs[1].set_xticklabels(["Bulk density", "Organic matter", "pH"], fontsize=19); axs[1].set_yscale("log")
axs[1].set_title("Map error (MAE, log); black bar = baseline", fontsize=20)
from matplotlib.patches import Patch; axs[1].legend(handles=[Patch(color=WATER, label="SSURGO"), Patch(color=OIL, label="SoilGrids")], loc="upper left", fontsize=19)
f.suptitle("Soil maps against measured CRMS soil (392 sites)", x=0.01, ha="left", fontsize=26, fontweight="bold")
save(f, "soil_layer_check")

# 12 elicited ranges ---------------------------------------------------------------------------
ep = pd.read_csv(REPO+"data/knowledge/elicited_priors.csv"); ep = ep.iloc[::-1].reset_index(drop=True)
f, ax = fig(); y = np.arange(len(ep))
for yi, r in zip(y, ep.itertuples()):
    ax.plot([r.rule_lo, r.rule_hi], [yi+0.17]*2, color=GREY, lw=7, solid_capstyle="butt", alpha=0.6)
    ax.plot([r.tau_multiplier_lo, r.tau_multiplier_hi], [yi-0.17]*2, color=OIL, lw=7, solid_capstyle="butt")
ax.axvline(1, color=INK, lw=1.5, ls="--"); ax.set_yticks(y); ax.set_yticklabels([o.split(" (")[0] for o in ep.option], fontsize=19)
ax.plot([], [], color=GREY, lw=7, label="Rule-based range (first pass)"); ax.plot([], [], color=OIL, lw=7, label="Expert-revised range (used by the composer)"); ax.legend(loc="lower right")
ax.set_xlabel("Multiplier on recovery time (below 1 = faster)"); ax.set_title("Elicited ranges per treatment (not measurements)"); ax.set_xlim(0.4, 2.8)
save(f, "elicited_ranges")

# 13 period split ------------------------------------------------------------------------------
a1 = pd.read_csv(R+"period_split/A1.csv"); a2 = pd.read_csv(R+"period_split/A2.csv"); a3 = pd.read_csv(R+"period_split/A3.csv")
rows = [("Heavy, 2010-2015", a1.iloc[0]), ("Heavy, 2015-2017", a1.iloc[1]), ("Heavy: later minus earlier", a2.iloc[0]),
        ("Very light, 2010-2015 (null check)", a3.iloc[0]), ("Very light, 2015-2017 (null check)", a3.iloc[1]), ("Light, 2010-2015 (null check)", a3.iloc[3]), ("Light, 2015-2017 (null check)", a3.iloc[4])]
f, ax = fig(); y = np.arange(len(rows))[::-1]
for yi, (l, r) in zip(y, rows):
    col = OIL if l.startswith("Heavy") else GREY
    ax.errorbar(r.estimate, yi, xerr=[[r.estimate-r.lo90], [r.hi90-r.estimate]], fmt="o", color=col, capsize=6, lw=3, ms=11)
    ax.text(1.9, yi, f"{r.estimate:+.2f} ({r.lo90:.2f} to {r.hi90:.2f})", va="center", fontsize=19)
ax.axvline(0, color=INK, lw=1.5); ax.set_yticks(y); ax.set_yticklabels([l for l, _ in rows], fontsize=19); ax.set_xlim(-1.2, 3.3)
ax.set_xlabel("Oiled minus clean edge loss, fully adjusted (m/yr, 90% interval)"); ax.set_title("Period split: heavy and null-check classes")
save(f, "period_split")

# 14 event study ---------------------------------------------------------------------------------
es = pd.read_csv(R+"oil_event_study/effects.csv"); f, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100)
for ax, outc, ttl, col, yl in [(axs[0], "cover_total", "Vegetation cover (points)", OIL, "Oiled minus unoiled, relative to survey -1"), (axs[1], "ndvi_gs_mean", "Growing-season NDVI", WATER, "Oiled minus unoiled, relative to survey -1")]:
    s = es[es.outcome == outc]; ax.errorbar(s.event_time, s.estimate, yerr=[s.estimate-s.ci_low, s.ci_high-s.estimate], fmt="o", color=col, capsize=7, lw=3, ms=11)
    ax.axhline(0, color=INK, lw=1.3); ax.axvline(-0.5, color=GREY, ls="--"); ax.set_xlabel("Surveys since the 2010 spill (event time)"); ax.set_title(ttl, fontsize=24); ax.set_ylabel(yl, fontsize=26)
f.suptitle("CRMS event study: oiled minus unoiled", x=0.01, ha="left", fontsize=26, fontweight="bold")
save(f, "oil_event_study")
