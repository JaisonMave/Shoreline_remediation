import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/claude/Shoreline_remediation/"
BG, INK, MUTE, GRID, AC, AC2 = "#F5F3EC", "#14262E", "#5E6B70", "#D9DED9", "#9A531A", "#2B6CB0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "axes.edgecolor": MUTE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTE, "ytick.color": INK})
def fig(w=16, h=8):
    f, a = plt.subplots(figsize=(w, h), facecolor=BG); a.set_facecolor(BG)
    for s in ("top", "right"): a.spines[s].set_visible(False)
    return f, a
# cell values for worked example
l = pd.read_csv(R + "data/external/p2/barataria/cell_land_by_year.csv")
print(l[l.cell == "8018_32612"][["year", "land_fraction", "valid_fraction", "flight_date"]].to_string())
# 1 study area by status
s = pd.read_csv(R + "data/demo/p5_sites.csv")
f, a = fig(14, 10)
grp = {"in_scope": None, "river_delta": "#B9A6A0", "classification_unreliable": "#C9CFC9", "not_salt_marsh": "#E2E4DE"}
other = s[~s.status.isin(grp)]
a.scatter(other.lon, other.lat, s=2, c="#C9CFC9", lw=0, label="Salt marsh, failed an image check")
for st, c in [("not_salt_marsh", "#E2E4DE"), ("classification_unreliable", "#AEB6AF"), ("river_delta", "#B9A6A0")]:
    d = s[s.status == st]; a.scatter(d.lon, d.lat, s=2, c=c, lw=0, label={"not_salt_marsh": "Not salt marsh", "classification_unreliable": "Excluded: imagery unreliable", "river_delta": "Excluded: active river delta"}[st])
cols = {"terrebonne": "#7FA7C9", "barataria": "#2B6CB0", "breton": "#1F4E79"}
for b, c in cols.items():
    d = s[(s.status == "in_scope") & (s.basin == b)]; a.scatter(d.lon, d.lat, s=3, c=c, lw=0, label=f"Used: {b.title()} ({len(d):,} cells)")
a.set_xlabel("Longitude"); a.set_ylabel("Latitude"); a.set_aspect(1 / np.cos(np.radians(29.4)))
lg = a.legend(loc="lower left", markerscale=6, frameon=False, fontsize=14)
plt.tight_layout(); plt.savefig("study_area.png", dpi=110, facecolor=BG); plt.close()
print(s.status.value_counts().to_string()); print(s[s.status=="in_scope"].basin.value_counts().to_string())
# 2 oiling map barataria
f, a = fig(14, 10)
d = s[(s.basin == "barataria") & (s.esi_main == "10A")]
oc = {"NOO": "#5b8fb0", "Very_Light": "#9bb8a8", "Light": "#e8c547", "Moderate": "#db8b3e", "Heavy": "#a32a2a"}
for k in ["NOO", "Very_Light", "Light", "Moderate", "Heavy"]:
    e = d[d.max_oiling == k]; a.scatter(e.lon, e.lat, s=4, c=oc[k], lw=0, label=f"{k.replace('_', ' ').replace('NOO', 'No oil observed')} ({len(e):,})")
a.set_aspect(1 / np.cos(np.radians(29.4))); a.set_xlabel("Longitude"); a.set_ylabel("Latitude")
a.legend(loc="lower left", markerscale=5, frameon=False, fontsize=14, title="SCAT maximum oiling", title_fontsize=14)
plt.tight_layout(); plt.savefig("oiling_map.png", dpi=110, facecolor=BG); plt.close()
# 3 by oiling class
c = pd.read_csv(R + "results/naip_edge_loss/coefficients.csv"); c = c[(c.period == "2010-2015") & (c.term != "water_1km_2010")]
f, a = fig(14, 7)
names = {"Very_Light": "Very light", "Light": "Light", "Moderate": "Moderate", "Heavy": "Heavy"}
x = np.arange(len(c)); cl = [AC if t == "Heavy" else MUTE for t in c.term]
a.bar(x, c.estimate, color=cl, width=0.55)
a.errorbar(x, c.estimate, yerr=[c.estimate - c.lo, c.hi - c.estimate], fmt="none", ecolor=INK, capsize=8, lw=1.6)
for i, r in enumerate(c.itertuples()): a.text(i + 0.32, r.estimate, f"{r.estimate:.2f}", va="center", fontsize=16, color=INK)
a.axhline(0, color=MUTE, lw=1); a.set_xticks(x, [names[t] for t in c.term], fontsize=17)
a.set_ylabel("Extra edge loss vs clean edge, m/yr"); a.set_xlabel("SCAT maximum oiling class")
plt.tight_layout(); plt.savefig("by_class.png", dpi=110, facecolor=BG); plt.close()
print(c.to_string())
# 4 P1 checks forest
p = pd.read_csv(R + "results/p1_prespill/checks.csv"); e = pd.read_csv(R + "results/p1_prespill/exploratory.csv")
rows = [("Aerial photos 2010-2015\n(first estimate)", p.iloc[0]), ("Landsat 2008-2015\n(second sensor)", p.iloc[1]),
        ("Landsat 1999-2008\n(before any oil)", p.iloc[2]), ("After minus before\n(headline)", p.iloc[3]),
        ("Headline + finer exposure\n(exploratory)", e.iloc[0])]
f, a = fig(15, 7.5)
for i, (lab, r) in enumerate(rows):
    y = len(rows) - 1 - i; colr = AC if "headline)" in lab else MUTE
    a.plot([r.lo, r.hi], [y, y], color=colr, lw=4); a.plot(r.heavy_effect, y, "o", ms=13, color=colr)
    a.text(r.hi + 0.04, y, f"{r.heavy_effect:.2f}  ({r.lo:.2f} to {r.hi:.2f})", va="center", fontsize=15, color=INK)
a.axvline(0, color=MUTE, lw=1); a.set_yticks(range(len(rows))[::-1], [r[0] for r in rows], fontsize=15)
a.set_xlim(-0.3, 2.0); a.set_xlabel("Extra edge loss, heavily oiled vs clean edge nearby, m/yr (90% interval)")
plt.tight_layout(); plt.savefig("p1_checks.png", dpi=110, facecolor=BG); plt.close()
# 5 P2 errors
b = pd.read_csv(R + "results/p2_basin_holdout/per_basin.csv"); b = b[b.tested == True]; po = pd.read_csv(R + "results/p2_basin_holdout/pooled.csv").iloc[0]
labs = ["Barataria", "Breton (west)", "Pooled"]; m0 = list(b.MAE_M0) + [po.MAE_M0]; m1 = list(b.MAE_M1) + [po.MAE_M1]
f, a = fig(14, 7); x = np.arange(3)
a.bar(x - 0.18, m0, 0.34, color="#BFC7C3", label="Guess the average (baseline)"); a.bar(x + 0.18, m1, 0.34, color=AC2, label="Model: exposure + pre-spill trend")
for i in range(3):
    a.text(x[i] - 0.18, m0[i] + 0.02, f"{m0[i]:.2f}", ha="center", fontsize=16); a.text(x[i] + 0.18, m1[i] + 0.02, f"{m1[i]:.2f}", ha="center", fontsize=16)
a.set_xticks(x, labs, fontsize=17); a.set_ylabel("Average prediction error, m/yr (lower is better)"); a.set_ylim(0, 1.8)
a.legend(frameon=False, fontsize=15, loc="upper right"); plt.tight_layout(); plt.savefig("p2_errors.png", dpi=110, facecolor=BG); plt.close()
# 6 P3 forest
t = pd.read_csv(R + "results/p3_treatment/A_prespill_adjusted.csv")
order = ["Manual minus Oiled, untreated", "Mechanical minus Oiled, untreated", "Mechanical + planted minus Oiled, untreated"]
nice = ["Manual cleanup", "Mechanical cleanup", "Mechanical + planting"]
f, a = fig(15, 7)
for i, (o, n) in enumerate(zip(order, nice)):
    y = 2 - i
    for k, (per, off, al) in enumerate([("primary", 0.15, 1.0), ("secondary", -0.15, 0.4)]):
        r = t[(t.contrast == o) & t.analysis.str.contains(per)].iloc[0]
        a.plot([r.lo90, r.hi90], [y + off, y + off], color=AC2, lw=4, alpha=al); a.plot(r.difference, y + off, "o", ms=12, color=AC2, alpha=al)
        if per == "primary": a.text(r.hi90 + 0.05, y + off, f"{r.difference:+.2f}", va="center", fontsize=16)
a.axvline(0, color=MUTE, lw=1); a.set_yticks([2, 1, 0], nice, fontsize=17)
a.plot([], [], "o-", color=AC2, lw=4, label="Years 0-2 (2010-2012)"); a.plot([], [], "o-", color=AC2, alpha=0.4, lw=4, label="Years 2-8 (2012-2018)")
a.legend(frameon=False, fontsize=15, loc="upper right"); a.set_xlabel("Change in edge erosion vs leaving oiled marsh untreated, m/yr (left = less erosion)")
a.set_xlim(-2.4, 1.6); plt.tight_layout(); plt.savefig("p3_methods.png", dpi=110, facecolor=BG); plt.close()
