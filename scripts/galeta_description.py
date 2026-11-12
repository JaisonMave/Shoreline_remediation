"""Phase C1: descriptive summary of the Galeta (Bahia Las Minas, Panama) mangrove files, NCEI accession 9400033.

DESCRIPTIVE ONLY: site-year means, group means and counts. No model, no test, no recovery-time estimate.
Unit of analysis = SITE. Row-level units (seedling, shoot, trap, root, dowel, bag) are averaged to a site-visit
(date) mean first, then the visit means inside a calendar year are averaged to a site-year mean, then site-year
means are averaged across the sites of a group (oiled, unoiled). Missing data are -1 (numeric) per stri_os.doc.

Usage: python scripts/galeta_description.py RAW_DATA_DIR [OUT_DIR]
  RAW_DATA_DIR = the archive's data/ folder (read only; column names come from mgf.doc / mgr.doc).
  OUT_DIR default results/galeta. Writes inventory, site-year, group-year CSVs and one PNG per outcome.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLS = {  # field order from mgf.doc / mgr.doc ("Structure for database")
    "mgfd_m": "SID SSID CID COLL1 CDATE SITE SITEN PLT TAGN QP ST SP PLANT H_HT T_HT GH LREF FTAG PTAG TOPREF TOPNODE VER RECN",
    "mgfl_m": "SID SSID CID COLL1 CDATE SDATE NUMDAYS TN SITE SITEN HAB COND TLOST TSKIP TDIST SP GML NL GMS NS GMW GMD GMR NBA NBB NBP NI NFA NFB NFX NHA NHB GMHB VER",
    "mgfs_mx": "SID SSID CID COLL1 CDATE SP SITE REP F_L TAGN TAG_L NDYS NS SMISS SBAD ND LV BP BA BB I FA FB HA HB S FEX SHOOT_M DLV NLV NSH NR VER",
    "mgft_m": "SID SSID CID COLL1 SITE SITEN HAB COND SAMPN CDATE SURF_S SURF_T VER",
    "mgrb_m": "SID SSID CID CDATE COLL1 REPL SITE HAB COND ROOT_N DATAABBR PRESABBR GROUP GROUP2 NETGM NUMDAYS LENGTH VER",
    "mgrc_m": "SID SSID CID CDATE COLL1 REPL SITE HAB COND ROOT_N RC DATAABBR PRESABBR GROUP GROUP2 P_COV LCM DMM VER",
    "mgre_m": "SID SSID CID CDATE COLL1 SITE HAB COND REPL DEPTH_CM VER",
    "mgrg_m": "SID SSID CID COLL1 CDATE S_SITE SITE HAB COND REPL BAGN SAMPN LEN SEX VER",
    "mgrp_m": "SID SSID CID COLL1 CDATE SDATE NUMDAYS S_SITE SITE REPL HAB COND BAGN I_OR_F LEN LIVE DEAD VER",
    "mgrq_m": "SID SSID CID COLL1 CDATE REPL SITE HAB COND UCANLX OPENLX CANOPY_PCT VER",
    "mgrr_m": "SID SSID CID CDATE COLL1 REPL SITE HAB COND ROOT_N DATAABBR PRESABBR GROUP GROUP2 P_COV LCM DMM VER",
    "mgrs_m": "SID SSID CID COLL1 MEASBY SITE HAB COND REPL SAMPN CDATE MDATE SURF_S IM_S SURF_T IM_T VER",
    "mgrt_m": "SID SSID CID COLL1 SITE HAB COND REPL SAMPN CDATE SDDISM BOT VER",
    "mgrv_m": "SID SSID CID COLL1 CDATE SDATE SITE HAB COND BAG I_O DATAABBR PRESABBR LENGTH TOTAL VER",
    "mgrw_m": "SID SSID CID COLL1 CDATE SITE HAB COND REPL END START DIS_M SPD_CMSC LOCATION VER",
    "mgrz_m": "SID SSID CID COLL1 CDATE SITE HAB COND REPL CLODN NDAYS PC_LEFT VER",
}
FILE = {"mgfs_mx": "mgfs_mx.txt"}
GROUP = {"o": "oiled", "u": "unoiled"}  # COND codes from the .doc; 'n' (newly oiled, mgr.doc site history) and blank are excluded


def load(raw: Path, key: str) -> pd.DataFrame:
    df = pd.read_csv(raw / FILE.get(key, key + ".txt"), header=None, dtype=str, keep_default_na=False, encoding="latin-1")
    names = COLS[key].split()
    if df.shape[1] != len(names):
        raise ValueError(f"{key}: {df.shape[1]} columns, doc lists {len(names)}")
    df.columns = names
    if "CDATE" in df:
        df["date"] = pd.to_datetime(df["CDATE"], format="%Y%m%d", errors="coerce")
    return df


def num(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    return x.where(x != -1)  # -1 = missing (stri_os.doc)


def dead_live_codes(raw: Path) -> tuple[set, set]:
    """Root-condition codes the table in mgr.doc explicitly labels '(dead)' or '(live)'. Others: not documented."""
    lines = open(raw / "mgr.doc", errors="replace").read().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(" RC   DESCRIPTION"))
    dead, live = set(), set()
    for l in lines[i + 1:]:
        if not l.strip():
            break
        for part in (l[:38], l[38:]):
            m = re.match(r"\s*(\S+)\s+(.*)$", part)
            if m:
                code, desc = m.group(1), m.group(2)
                (dead if "(dead)" in desc else live if "(live)" in desc else set()).add(code)
    return dead, live


def site_cond_map(raw: Path) -> dict:
    """COND per MGF site from mgfl/mgft (documented there); mgfd and mgfs have no COND field."""
    m = {}
    for k in ("mgfl_m", "mgft_m"):
        d = load(raw, k)
        for s, c in d[["SITE", "COND"]].drop_duplicates().itertuples(index=False):
            if c in GROUP:
                m.setdefault(s, set()).add(c)
    return {s: next(iter(c)) for s, c in m.items() if len(c) == 1}


def collect(raw: Path) -> pd.DataFrame:
    """Return row-level frame: outcome, unit, stratum, site, cond, date, value."""
    out = []

    def add(df, outcome, unit, value, stratum="all"):
        t = pd.DataFrame({"outcome": outcome, "unit": unit, "stratum": stratum, "site": df["SITE"].values,
                          "cond": df["COND"].map(GROUP).values, "date": df["date"].values, "value": np.asarray(value, float)})
        out.append(t)

    cm = site_cond_map(raw)
    # --- MGF seedlings (mgfd): COND taken from the same SITE code in mgfl/mgft
    d = load(raw, "mgfd_m"); d["COND"] = d["SITE"].map(cm).fillna("")
    d["dead"] = d["ST"].str.contains("x").astype(float)
    add(d, "seedling_dead_flag_share", "share of seedling records with status x (dead)", d["dead"])
    h = d[~d["ST"].str.contains("x|m")]
    for p, lab in (("n", "natural"), ("r", "planted by refinery")):
        hh = h[h["PLANT"] == p]
        add(hh, "seedling_height", "cm", num(hh["T_HT"]), stratum=lab)
    # --- MGF litterfall (mgfl): dry mass per trap record per day deployed (derived: g / NUMDAYS)
    l = load(raw, "mgfl_m"); days = num(l["NUMDAYS"])
    keep = (l["TLOST"] != "T")
    l = l[keep]; days = days[keep]
    add(l, "litter_leaf_dry_mass_rate", "g per trap per day (GML / NUMDAYS, derived)", num(l["GML"]) / days)
    add(l, "litter_reproductive_dry_mass_rate", "g per trap per day (GMR / NUMDAYS, derived)", num(l["GMR"]) / days)
    # --- MGF shoots (mgfs): leaves per shoot, R. mangle only; COND via site code
    s = load(raw, "mgfs_mx"); s["COND"] = s["SITE"].map(cm).fillna("")
    s = s[(s["SMISS"] != "T") & (s["SBAD"] != "T")]
    add(s, "leaves_per_shoot", "leaves per tagged shoot (LV; R. mangle)", num(s["LV"]))
    # --- MGR root cover: root-level oil cover and documented-dead share (mgrc), dowel oil (mgrr)
    for key, outcome, label in (("mgrc_m", "root_oil_cover", "% cover of root by oil (GROUP2 = OI)"),
                                ("mgrr_m", "dowel_oil_cover", "% cover of recruitment dowel by oil (GROUP2 = OI)")):
        r = load(raw, key)
        r = r[(r["SITE"] != "") & r["date"].notna()]
        ids = ["SITE", "COND", "date", "REPL", "ROOT_N"]
        cov = r.assign(p=num(r["P_COV"])).query("GROUP2 == 'OI'").groupby(ids)["p"].sum()
        root = r.groupby(ids).size().rename("n").reset_index().set_index(ids)
        root["v"] = cov.reindex(root.index).fillna(0.0)  # ASSUMED 0 when a sampled root has rows but none for oil (stri_os.doc convention)
        root = root.reset_index()
        add(root, outcome, label, root["v"])
        if key == "mgrc_m":
            dead, live = dead_live_codes(raw)
            rc = r[r["RC"] != ""].drop_duplicates(ids)
            rc = rc[rc["RC"].isin(dead | live)]
            add(rc, "root_documented_dead_share", "share of roots whose RC code is labelled (dead) among codes labelled (dead) or (live)",
                rc["RC"].isin(dead).astype(float))
    # --- dowel biomass (mgrb): 'total' taxon rows, net weight g
    b = load(raw, "mgrb_m"); b = b[(b["DATAABBR"] == "total") & b["date"].notna()]
    add(b, "dowel_total_biomass", "g (NETGM, 'total' rows; deployment days vary, NUMDAYS)", num(b["NETGM"]))
    # --- light (mgrq)
    q = load(raw, "mgrq_m"); q = q[q["date"].notna()]
    add(q, "canopy_light_ratio", "% (under canopy lux / open lux x 100)", num(q["CANOPY_PCT"]))
    # --- caged mussel survival (mgrp, SSID P final rows): bag-level live / (live + dead)
    p = load(raw, "mgrp_m"); p = p[(p["SSID"] == "P") & (p["I_OR_F"] == "f") & p["date"].notna()]
    g = p.assign(L=num(p["LIVE"]), D=num(p["DEAD"])).groupby(["SITE", "COND", "date", "BAGN"])[["L", "D"]].sum().reset_index()
    g = g[(g["L"] + g["D"]) > 0]
    add(g, "caged_mytilopsis_survival", "share live of live + dead, final count per cage (transplant experiment, not natural)",
        g["L"] / (g["L"] + g["D"]))
    return pd.concat(out, ignore_index=True)


def summarise(rows: pd.DataFrame):
    rows = rows[rows["cond"].notna() & rows["value"].notna() & rows["date"].notna()].copy()
    rows["year"] = rows["date"].dt.year
    keys = ["outcome", "unit", "stratum", "site", "cond"]
    visit = rows.groupby(keys + ["year", "date"])["value"].agg(["mean", "size"]).reset_index()
    site_year = visit.groupby(keys + ["year"]).agg(value=("mean", "mean"), n_visits=("date", "nunique"),
                                                   n_records=("size", "sum")).reset_index()
    gk = ["outcome", "unit", "stratum", "cond", "year"]
    grp = site_year.groupby(gk)["value"].agg(n_sites="size", mean_of_site_means="mean",
                                              sd_between_sites="std", min_site="min", max_site="max").reset_index()
    return site_year, grp


def usable(grp: pd.DataFrame) -> pd.DataFrame:
    w = grp.pivot_table(index=["outcome", "stratum", "year"], columns="cond", values="n_sites").reset_index()
    for c in ("oiled", "unoiled"):
        if c not in w:
            w[c] = np.nan
    w["both_ge3"] = (w["oiled"] >= 3) & (w["unoiled"] >= 3)
    return w


def plot(grp: pd.DataFrame, outdir: Path):
    for outcome, g in grp.groupby("outcome"):
        strata = sorted(g["stratum"].unique())
        fig, axes = plt.subplots(1, len(strata), figsize=(5.2 * len(strata), 3.8), squeeze=False)
        for ax, st in zip(axes[0], strata):
            for cond, col in (("oiled", "#b2182b"), ("unoiled", "#2166ac")):
                t = g[(g["stratum"] == st) & (g["cond"] == cond)].sort_values("year")
                if len(t):
                    ax.plot(t["year"], t["mean_of_site_means"], "-o", color=col, label=f"{cond} (n sites: " +
                            ",".join(str(int(n)) for n in t["n_sites"]) + ")")
            ax.set_xlabel("Calendar year of collection")
            ax.set_ylabel("Mean of site means\n" + g["unit"].iloc[0][:48])
            ax.set_title(f"{outcome}" + ("" if st == "all" else f" [{st}]"), fontsize=9)
            ax.legend(fontsize=7)
            ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        fig.tight_layout()
        fig.savefig(outdir / f"galeta_{outcome}.png", dpi=130)
        plt.close(fig)


def inventory(raw: Path) -> pd.DataFrame:
    rows = []
    cm = site_cond_map(raw)
    for key in COLS:
        if not (raw / FILE.get(key, key + ".txt")).exists():
            rows.append(dict(file=key, rows=np.nan, note="listed in doc, file absent"))
            continue
        d = load(raw, key)
        r = dict(file=FILE.get(key, key + ".txt"), rows=len(d), columns=d.shape[1] - ("date" in d))
        if "date" in d:
            r.update(first_date=d["date"].min().date() if d["date"].notna().any() else "", last_date=d["date"].max().date() if d["date"].notna().any() else "",
                     blank_or_invalid_dates=int(d["date"].isna().sum()))
        if "SITE" in d:
            r["sites"] = d["SITE"].replace("", np.nan).nunique()
            if "COND" in d:
                c = d.groupby("SITE")["COND"].agg(lambda x: "".join(sorted(set(x) - {""})))
                r["sites_oiled_only"] = int((c == "o").sum()); r["sites_unoiled_only"] = int((c == "u").sum())
                r["sites_other_or_mixed"] = int(((c != "o") & (c != "u")).sum())
            else:
                r["sites_oiled_via_mgfl_mgft"] = sum(cm.get(s) == "o" for s in d["SITE"].unique())
                r["sites_unoiled_via_mgfl_mgft"] = sum(cm.get(s) == "u" for s in d["SITE"].unique())
                r["sites_no_cond_available"] = sum(s not in cm for s in d["SITE"].unique())
        rows.append(r)
    return pd.DataFrame(rows)


def site_table(raw: Path) -> pd.DataFrame:
    """One row per site code with COND/HAB as recorded and the files and years where it appears."""
    rows = []
    cm = site_cond_map(raw)
    for key in COLS:
        if not (raw / FILE.get(key, key + ".txt")).exists():
            continue
        d = load(raw, key)
        if "SITE" not in d:
            continue
        d = d[d["SITE"] != ""]
        d = d.assign(COND=d["COND"] if "COND" in d else d["SITE"].map(cm).fillna("(none)"),
                     HAB=d["HAB"] if "HAB" in d else "(none)", year=d["date"].dt.year)
        g = d.groupby(["SITE", "COND", "HAB"]).agg(rows=("SITE", "size"), first_year=("year", "min"), last_year=("year", "max")).reset_index()
        g.insert(0, "file", FILE.get(key, key + ".txt"))
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def main(raw: Path, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    inventory(raw).to_csv(outdir / "galeta_file_inventory.csv", index=False)
    site_table(raw).to_csv(outdir / "galeta_sites_by_file.csv", index=False)
    rows = collect(raw)
    sy, grp = summarise(rows)
    sy.to_csv(outdir / "galeta_site_year.csv", index=False)
    grp.to_csv(outdir / "galeta_group_year.csv", index=False)
    usable(grp).to_csv(outdir / "galeta_usable_years.csv", index=False)
    plot(grp, outdir)
    print(f"{len(sy)} site-year rows, {len(grp)} group-year rows, {grp.outcome.nunique()} outcomes")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else Path("results/galeta"))
