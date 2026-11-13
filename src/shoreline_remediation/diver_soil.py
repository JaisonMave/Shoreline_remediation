"""DIVER coastal-wetland soil PAH loader (plan: docs/PAH_DECLINE_PLAN.md, "Final choices"; structure notes:
docs/DIVER_SOIL_STRUCTURE.md). Builds the per-sample compound table, the station assignment, SCAT oiling and the
station-campaign table. The DIVER files are untrusted data: they are only read (pandas, latin-1), never executed.

Rules (all values marked ASSUMED are assumptions of the plan or of this implementation, not measurements):
  rows       Collection_Matrix Soil; PAH analytes = Analysis_Type PAH; hopane = Analysis '17a(H),21b(H)-Hopane (Hopane)';
             unit PPB only (drops water-type units); drop Tarball/Oil rows, wet-weight rows, rejected (qualifier R) rows.
  compounds  names present in every one of the four PAH campaigns (list fixed from names alone, before any value is read).
             Individual isomers that are components of a homologue-group row (e.g. 2-methylnaphthalene inside
             C1-naphthalenes) are removed by NAME to avoid double counting (implementation addition, ASSUMED).
  replicates per sample and compound: mean; if two results differ by more than RPD_LIMIT (50 %, ASSUMED) keep the one closer
             to the median of that compound at the same station and campaign; with three or more, drop the one farthest
             from their median. A detect outranks a non-detect replicate (ASSUMED).
  non-detects Detection_Extent == 'At or Below Detection Limit' (ASSUMED). Proxy limit per compound and campaign = 5th
             percentile of detected values (ASSUMED). Modes: 'tobit' (primary), 'zero', 'proxy', 'half' (half proxy limit).
  stations   Fall 2013 (and any unlabelled sample) matched to the nearest station sample point within 30 m (ASSUMED).
  oiling     SCAT maximum-oiling zone nearest to the station within 100 m (ASSUMED), else 'unknown'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import log_ndtr

CAMPAIGN_FILES = {"Spring2011": "cwvp_Spring2011_samples.csv", "Fall2011": "cwvp_Fall2011_samples.csv",
                  "Fall2012": "cwvp_Fall2012_samples.csv", "Fall2013": "cwvp_Fall2013_samples.csv"}
EXTRA_FILE = {"Fall2010": "cwvp_Fall2010_samples.csv"}   # no PAH, but its stations give reference coordinates
USECOLS = ["Date", "Station-Site", "Sample_ID", "Collection_Matrix", "Analysis_Type", "Analysis", "Lab_Replicate",
           "Analysis_Result", "Analysis_Result_Unit", "Measurement_Basis", "QM_Matrix", "Lab-Result_Matrix",
           "Qualifier_Code", "Detection_Extent", "Lab_ID", "Sample_Upper_Depth", "Sample_Lower_Depth",
           "Start_Latitude", "Start_Longitude"]
HOPANE = "17a(H),21b(H)-Hopane (Hopane)"
TOC = "Organic carbon, total"
RPD_LIMIT = 50.0                  # ASSUMED percent
PROXY_Q = 0.05                    # ASSUMED quantile of detected values
MIN_DETECTS = 30                  # plan
STATION_MATCH_M = 30.0            # ASSUMED
SCAT_RADIUS_M = 100.0             # ASSUMED
T0 = pd.Timestamp("2010-04-20")   # ASSUMED: Deepwater Horizon blowout; t in years since this date
FLAG_SHARE = 0.5                  # plan: samples with more than 50 % of the sum estimated are flagged
ND_EXTENT = "At or Below Detection Limit"
UTM = 32615
OIL_CLASS = {"NOO": "none", "Neg_TB": "very_light", "Very_Light": "very_light", "Light": "light", "Light_TB": "light",
             "Moderate": "moderate", "Mod_TB": "moderate", "Heavy": "heavy", "Heavy_TB": "heavy"}  # Neg_TB ASSUMED
OIL_ORDER = ["none", "very_light", "light", "moderate", "heavy", "unknown"]
# Name-based isomer rule: individual alkyl isomers that are included in a homologue-group row (C1-..., C2-..., C3-...).
ISOMER_RE = re.compile(r"^\d[\d,/]*-(Methyl|Dimethyl|Trimethyl)", re.I)


@dataclass
class Log:
    lines: list = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.lines.append(msg)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n")


# ---------------------------------------------------------------- replicate rule
def rpd(a: float, b: float) -> float:
    m = (a + b) / 2.0
    return 0.0 if m == 0 else abs(a - b) / m * 100.0


def pick_value(values, ref_median: float, limit: float = RPD_LIMIT) -> tuple[float, str]:
    """One value per sample and compound from its replicate results. Returns (value, rule label)."""
    v = np.asarray(values, float)
    if len(v) == 1:
        return float(v[0]), "single"
    if len(v) == 2:
        if rpd(v[0], v[1]) <= limit:
            return float(v.mean()), "mean"
        d = np.abs(v - ref_median)
        return float(v[int(np.argmin(d))]), "closer_to_median"
    maxrpd = max(rpd(v[i], v[j]) for i in range(len(v)) for j in range(i + 1, len(v)))
    if maxrpd <= limit:
        return float(v.mean()), "mean"
    keep = np.delete(v, int(np.argmax(np.abs(v - np.median(v)))))
    return float(keep.mean()), "drop_farthest"


# ---------------------------------------------------------------- Tobit imputation
def tobit_fit(X: np.ndarray, y: np.ndarray, cens: np.ndarray, c: np.ndarray):
    """Left-censored normal regression. y: log value (ignored where cens); c: log censoring limit (used where cens).
    Returns (beta, sigma)."""
    X = np.asarray(X, float); y = np.asarray(y, float); c = np.asarray(c, float); cens = np.asarray(cens, bool)
    det = ~cens
    beta0 = np.linalg.lstsq(X[det], y[det], rcond=None)[0]
    s0 = max(float(np.std(y[det] - X[det] @ beta0)), 0.1)
    p0 = np.r_[beta0, np.log(s0)]

    def nll(p):
        b, ls = p[:-1], p[-1]
        s = np.exp(ls)
        mu = X @ b
        z = (y[det] - mu[det]) / s
        ll = np.sum(-0.5 * z ** 2 - ls - 0.5 * np.log(2 * np.pi))
        if cens.any():
            ll += np.sum(log_ndtr((c[cens] - mu[cens]) / s))
        return -ll

    r = minimize(nll, p0, method="L-BFGS-B")
    return r.x[:-1], float(np.exp(r.x[-1]))


def tobit_expected(mu, sigma: float, c) -> np.ndarray:
    """E[exp(Y) | Y < c] for Y ~ N(mu, sigma^2); never above exp(c)."""
    mu = np.asarray(mu, float); c = np.asarray(c, float)
    a = (c - mu) / sigma
    e = np.exp(mu + sigma ** 2 / 2 + log_ndtr(a - sigma) - log_ndtr(a))
    return np.minimum(e, np.exp(c))


# ---------------------------------------------------------------- reading and row filters
def read_soil(csv_dir: Path, log: Log) -> pd.DataFrame:
    parts = []
    for camp, fn in {**EXTRA_FILE, **CAMPAIGN_FILES}.items():
        d = pd.read_csv(Path(csv_dir) / fn, encoding="latin-1", low_memory=False, dtype=str, usecols=USECOLS)
        n_all = len(d)
        d = d[d["Collection_Matrix"] == "Soil"].copy()
        d["campaign"] = camp
        log.add(f"[read] {fn}: rows {n_all}, soil rows {len(d)}, soil samples {d.Sample_ID.nunique()}")
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def filter_rows(soil: pd.DataFrame, log: Log) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (PAH+hopane rows, TOC rows) after the plan's row filters, counted at every step."""
    log.add(f"[rows] soil rows, five files: {len(soil)}; samples {soil.Sample_ID.nunique()}")
    sel = soil[(soil.Analysis_Type == "PAH") | (soil.Analysis == HOPANE)]
    log.add(f"[rows] Analysis_Type PAH or hopane: {len(sel)} rows; PAH samples "
            f"{sel[sel.Analysis_Type == 'PAH'].Sample_ID.nunique()}")
    water = sel.Analysis_Result_Unit.isin(["ug/L", "mg/L"]) | (sel.Analysis_Result_Unit != "PPB")
    log.add(f"[rows] drop non-PPB / water-type units: {int(water.sum())}"); sel = sel[~water]
    tb = (sel.QM_Matrix == "Oil") | (sel["Lab-Result_Matrix"] == "Tarball")
    log.add(f"[rows] drop tarball/oil rows: {int(tb.sum())}"); sel = sel[~tb]
    wet = sel.Measurement_Basis != "Dry Weight"
    log.add(f"[rows] drop wet-weight / not dry-weight rows: {int(wet.sum())}"); sel = sel[~wet]
    rej = sel.Qualifier_Code == "R"
    log.add(f"[rows] drop rejected (qualifier R) rows: {int(rej.sum())}"); sel = sel[~rej]
    sel = sel.assign(value=pd.to_numeric(sel.Analysis_Result, errors="coerce"))
    bad = sel.value.isna()
    log.add(f"[rows] drop non-numeric results: {int(bad.sum())}"); sel = sel[~bad]
    log.add(f"[rows] kept: {len(sel)} rows; PAH samples {sel[sel.Analysis_Type == 'PAH'].Sample_ID.nunique()}; "
            f"hopane samples {sel[sel.Analysis == HOPANE].Sample_ID.nunique()}")
    toc = soil[(soil.Analysis == TOC) & (soil.Analysis_Result_Unit == "PCT")].copy()
    toc["value"] = pd.to_numeric(toc.Analysis_Result, errors="coerce")
    toc = toc.dropna(subset=["value"])
    log.add(f"[rows] total organic carbon rows (same-sample soil property, PCT): {len(toc)}; samples {toc.Sample_ID.nunique()}")
    for a in ("Organic Matter", "Bulk Density", "Salinity"):
        ids = set(soil.loc[soil.Analysis == a, "Sample_ID"])
        log.add(f"[rows] {a}: measured on {len(ids & set(sel.Sample_ID))} of {sel.Sample_ID.nunique()} PAH/hopane samples "
                "(plan covariate; not usable if 0)")
    return sel, toc


def fix_compound_list(pah: pd.DataFrame, log: Log) -> list[str]:
    """Compounds reported in every PAH campaign, decided from names alone."""
    per = pah.groupby("campaign").Analysis.agg(lambda s: set(s))
    names = set.intersection(*per.values)
    log.add(f"[compounds] campaigns with PAH rows: {sorted(per.index)}; names per campaign: "
            f"{ {k: len(v) for k, v in per.items()} }; reported in all: {len(names)}")
    iso = sorted(n for n in names if ISOMER_RE.match(n))
    names = sorted(n for n in names if not ISOMER_RE.match(n))
    log.add(f"[compounds] removed by name as isomers contained in homologue-group rows (double counting): {iso}")
    log.add(f"[compounds] final list ({len(names)}): " + "; ".join(names))
    return names


# ---------------------------------------------------------------- stations
def sample_table(rows: pd.DataFrame) -> pd.DataFrame:
    g = rows.drop_duplicates("Sample_ID")
    t = pd.DataFrame({"sample": g.Sample_ID.values, "campaign": g.campaign.values,
                      "station": g["Station-Site"].where(g["Station-Site"] != "Not Defined").values,
                      "date": pd.to_datetime(g.Date.values, errors="coerce"),
                      "lat": pd.to_numeric(g.Start_Latitude.values), "lon": pd.to_numeric(g.Start_Longitude.values),
                      "upper": pd.to_numeric(g.Sample_Upper_Depth.values), "lower": pd.to_numeric(g.Sample_Lower_Depth.values)})
    t["depth_class"] = np.where((t.upper == 0) & (t.lower == 2), "0-2cm", "deeper")
    t["state"] = t["sample"].str[:2]
    return t


def _utm(lat, lon):
    import geopandas as gpd
    g = gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs=4326).to_crs(UTM)
    return np.c_[g.x.values, g.y.values]


def assign_stations(samples: pd.DataFrame, ref: pd.DataFrame, log: Log, radius=STATION_MATCH_M) -> pd.DataFrame:
    """Fill missing station labels from the nearest labelled sample point (any campaign) within radius metres."""
    from scipy.spatial import cKDTree
    ref = ref.dropna(subset=["station", "lat", "lon"])
    tree = cKDTree(_utm(ref.lat.values, ref.lon.values))
    s = samples.copy(); s["station_source"] = np.where(s.station.notna(), "label", "none")
    miss = s.station.isna() & s.lat.notna()
    if miss.any():
        d, i = tree.query(_utm(s.loc[miss, "lat"].values, s.loc[miss, "lon"].values), distance_upper_bound=radius)
        ok = np.isfinite(d)
        idx = s.index[miss][ok]
        s.loc[idx, "station"] = ref.station.values[i[ok]]
        s.loc[idx, "station_source"] = "coordinates"
        # ambiguity: how many matched samples have a second, different station within the radius
        pts = _utm(s.loc[idx, "lat"].values, s.loc[idx, "lon"].values)
        amb = 0
        for p, st in zip(pts, s.loc[idx, "station"].values):
            near = tree.query_ball_point(p, radius)
            amb += len(set(ref.station.values[near]) - {st}) > 0
        log.add(f"[stations] samples without label: {int(miss.sum())}; matched by coordinates within {radius:.0f} m: "
                f"{int(ok.sum())}; unmatched: {int((~ok).sum())}; matches with a second station also within the radius: {amb}")
    return s


def scat_oiling(stations: pd.DataFrame, max_zones_shp: Path, log: Log, radius=SCAT_RADIUS_M) -> pd.DataFrame:
    """stations: columns station, lat, lon. Adds oil_class, scat_code, d_scat_m (nearest max-oiling zone within radius)."""
    import geopandas as gpd
    m = gpd.read_file(max_zones_shp).to_crs(UTM)
    p = gpd.GeoDataFrame(stations.reset_index(drop=True), geometry=gpd.points_from_xy(stations.lon, stations.lat), crs=4326).to_crs(UTM)
    j = gpd.sjoin_nearest(p[["station", "geometry"]], m[["OilCatCode", "geometry"]], how="left", max_distance=radius,
                          distance_col="d")
    j = j.sort_values("d").drop_duplicates("station").set_index("station")
    out = stations.copy()
    out["scat_code"] = out.station.map(j.OilCatCode)
    out["d_scat_m"] = out.station.map(j.d)
    out["oil_class"] = out.scat_code.map(OIL_CLASS).fillna("unknown")
    log.add(f"[oiling] stations {len(out)}; SCAT zone within {radius:.0f} m: {int(out.scat_code.notna().sum())}; classes: "
            f"{out.oil_class.value_counts().to_dict()}")
    return out


# ---------------------------------------------------------------- replicates
def resolve_replicates(rows: pd.DataFrame, smp: pd.DataFrame, log: Log) -> pd.DataFrame:
    """rows: filtered rows (PAH + hopane) with value; smp: sample table with station. Returns one row per
    (sample, compound): value, nd (censored), campaign, station."""
    r = rows[["Sample_ID", "Analysis", "value", "Detection_Extent"]].copy()
    r.columns = ["sample", "compound", "value", "extent"]
    r["nd"] = r.extent == ND_EXTENT
    r = r.merge(smp[["sample", "station", "campaign"]], on="sample", how="inner")
    n0 = len(r)
    r = r[r.station.notna()]
    log.add(f"[replicates] rows with an assigned station: {len(r)} of {n0}")
    size = r.groupby(["sample", "compound"]).value.transform("size")
    log.add(f"[replicates] sample-compound keys: {r.groupby(['sample','compound']).ngroups}; keys with >1 row: "
            f"{int(r[size > 1].groupby(['sample','compound']).ngroups)}")
    # a detect outranks a non-detect replicate
    anyd = r.groupby(["sample", "compound"]).nd.transform(lambda x: (~x).any())
    mixed_keys = r[(size > 1) & anyd & r.nd].groupby(["sample", "compound"]).ngroups
    drop = anyd & r.nd
    log.add(f"[replicates] keys mixing detect and non-detect replicates (non-detect rows dropped): {mixed_keys}")
    r = r[~drop]
    pool = {k: g for k, g in r.groupby(["station", "campaign", "compound"])}
    counts = {"single": 0, "mean": 0, "closer_to_median": 0, "drop_farthest": 0}
    out = []
    for (smp_id, comp), g in r.groupby(["sample", "compound"], sort=False):
        st, cp = g.station.iloc[0], g.campaign.iloc[0]
        if len(g) == 1:
            val, rule = float(g.value.iloc[0]), "single"
        else:
            pg = pool[(st, cp, comp)]
            others = pg[pg["sample"] != smp_id]
            ref = float(np.median((others if len(others) else pg).value.values))
            val, rule = pick_value(g.value.values, ref)
        counts[rule] += 1
        out.append((smp_id, comp, val, bool(g.nd.all()), cp, st))
    res = pd.DataFrame(out, columns=["sample", "compound", "value", "nd", "campaign", "station"])
    log.add(f"[replicates] rule outcomes per sample-compound (RPD limit {RPD_LIMIT:.0f} %, ASSUMED): {counts}")
    log.add("[replicates] two-lab case: PAH rows come from one laboratory (Alpha Analytical) only, so the same rule "
            "was applied to replicate and re-extraction rows (1A/2A, several Lab_IDs).")
    return res


# ---------------------------------------------------------------- imputation and sums
def proxy_limits(res: pd.DataFrame, compounds: list[str], log: Log) -> pd.DataFrame:
    p = res[res.compound.isin(compounds)]
    det = p[~p.nd]
    lim = det.groupby(["compound", "campaign"]).value.quantile(PROXY_Q).rename("proxy")
    pooled = det.groupby("compound").value.quantile(PROXY_Q)
    full = pd.MultiIndex.from_product([compounds, sorted(p.campaign.unique())], names=["compound", "campaign"])
    lim = lim.reindex(full)
    miss = lim.isna()
    if miss.any():
        lim[miss] = [pooled.get(c, np.nan) for c, _ in lim.index[miss]]
    log.add(f"[proxy] proxy limit (5th percentile of detects, ASSUMED) per compound x campaign: {len(lim)} cells; "
            f"{int(miss.sum())} cells with no detect in that campaign took the compound's pooled value; "
            f"{int(lim.isna().sum())} cells without any detect (non-detects set to 0)")
    return lim.fillna(0.0).reset_index()


def impute(res: pd.DataFrame, compounds: list[str], smp: pd.DataFrame, toc: pd.DataFrame, mode: str, log: Log | None) -> pd.DataFrame:
    """Add column 'filled' (value used in the sum) and 'imputed' (bool) for the compounds. mode in tobit/zero/proxy/half."""
    p = res[res.compound.isin(compounds)].copy()
    lim = proxy_limits(res, compounds, log if log else Log())
    p = p.merge(lim, on=["compound", "campaign"], how="left").merge(smp[["sample", "depth_class"]], on="sample", how="left")
    p = p.merge(toc, on="sample", how="left")
    p["filled"] = p.value
    nd = p.nd
    fill = {"zero": 0.0 * p.proxy, "proxy": p.proxy, "half": p.proxy / 2.0, "tobit": p.proxy / 2.0}[mode]  # tobit: fallback value
    p.loc[nd, "filled"] = fill[nd]
    p["method"] = np.where(nd, {"zero": "zero", "proxy": "proxy", "half": "half_proxy", "tobit": "half_proxy"}[mode], "detected")
    if mode == "tobit":
        camps = sorted(p.campaign.unique())
        n_fit = n_fallback = 0
        for comp, g in p.groupby("compound"):
            gg = g[(g.toc > 0) & (g.proxy > 0) & (g.value > 0)]
            ndet = int((~gg.nd).sum())
            if ndet < MIN_DETECTS or not g.nd.any():
                n_fallback += 1 if g.nd.any() else 0
                continue
            use_deep = int((gg.depth_class == "deeper").sum()) >= 10   # ASSUMED threshold; deep samples are few
            def design(d):
                cols = [np.ones(len(d)), np.log(d.toc.values)]
                cols += [(d.campaign.values == c).astype(float) for c in camps[1:]]
                if use_deep:
                    cols.append((d.depth_class.values == "deeper").astype(float))
                return np.column_stack(cols)
            X = design(gg)
            y = np.log(gg.value.values)
            c = np.log(gg.proxy.values)
            try:
                beta, sig = tobit_fit(X, y, gg.nd.values, c)
            except Exception:
                n_fallback += 1
                continue
            tgt = g[g.nd & (g.toc > 0) & (g.proxy > 0)]
            if len(tgt):
                e = tobit_expected(design(tgt) @ beta, sig, np.log(tgt.proxy.values))
                p.loc[tgt.index, "filled"] = e
                p.loc[tgt.index, "method"] = "tobit"
                n_fit += 1
        if log:
            log.add(f"[tobit] compounds with a fitted Tobit model: {n_fit}; compounds with non-detects that fell back to half the "
                    f"proxy limit (fewer than {MIN_DETECTS} detects or fit failure): {n_fallback}")
            log.add(f"[tobit] non-detect values by method: {p[p.nd].method.value_counts().to_dict()}")
    p["imputed"] = p.nd
    return p


def sample_sums(p: pd.DataFrame, rows_ok: pd.DataFrame, hop: pd.DataFrame, smp: pd.DataFrame, compounds: list[str],
                log: Log | None, surface_only=False) -> pd.DataFrame:
    """Per-sample sum, hopane ratio, estimated share. p: output of impute()."""
    cnt = p.groupby("sample").compound.nunique()
    complete = cnt[cnt == len(compounds)].index
    if log:
        log.add(f"[sum] samples with any compound of the list: {len(cnt)}; with all {len(compounds)} compounds: {len(complete)}; "
                f"dropped for missing compounds: {len(cnt) - len(complete)}")
    pc = p[p["sample"].isin(complete)]
    s = pc.groupby("sample").agg(pah_sum=("filled", "sum"), n_nd=("nd", "sum"))
    s["est_sum"] = pc[pc.nd].groupby("sample").filled.sum().reindex(s.index).fillna(0.0)
    s["est_share"] = np.where(s.pah_sum > 0, s.est_sum / s.pah_sum, np.nan)
    s["flag_est_gt50"] = s.est_share > FLAG_SHARE
    h = hop.set_index("sample")
    s["hopane"] = h.value.reindex(s.index); s["hopane_nd"] = h.nd.reindex(s.index)
    s["ratio"] = np.where(s.hopane.notna() & (s.hopane_nd == False) & (s.hopane > 0), s.pah_sum / s.hopane, np.nan)
    s = s.reset_index().merge(smp, on="sample", how="left")
    if surface_only:
        n = len(s); s = s[s.depth_class == "0-2cm"]
        if log:
            log.add(f"[sum] 0-2 cm only: {len(s)} of {n} samples")
    if log:
        log.add(f"[sum] samples with a sum: {len(s)}; with hopane ratio: {int(s.ratio.notna().sum())}; hopane non-detected "
                f"(ratio not computed): {int((s.hopane_nd == True).sum())}; hopane missing: {int(s.hopane.isna().sum())}")
        log.add(f"[sum] share of the sum estimated from non-detects: pooled {s.est_sum.sum() / s.pah_sum.sum():.4f}; "
                f"mean per sample {s.est_share.mean():.4f}; samples above 50 % flagged: {int(s.flag_est_gt50.sum())}")
    return s


def station_campaign_table(s: pd.DataFrame) -> pd.DataFrame:
    """One row per station x campaign x depth class: medians of the samples (the station is the unit)."""
    s = s.copy()
    s["t"] = (s.date - T0).dt.days / 365.25
    g = s.groupby(["station", "campaign", "depth_class"])
    t = g.agg(n_samples=("sample", "size"), n_ratio=("ratio", lambda x: int(x.notna().sum())), pah_sum=("pah_sum", "median"),
              ratio=("ratio", "median"), t=("t", "mean"), lat=("lat", "median"), lon=("lon", "median"),
              est_share_median=("est_share", "median"), n_flagged=("flag_est_gt50", "sum"), state=("state", lambda x: x.mode().iloc[0]),
              oil_class=("oil_class", "first"), scat_code=("scat_code", "first"), d_scat_m=("d_scat_m", "first")).reset_index()
    return t


# ---------------------------------------------------------------- driver
@dataclass
class Resolved:
    smp: pd.DataFrame
    res: pd.DataFrame
    compounds: list
    toc: pd.DataFrame
    hop: pd.DataFrame
    stations: pd.DataFrame


def prepare(csv_dir: Path, max_zones_shp: Path, log: Log) -> Resolved:
    soil = read_soil(csv_dir, log)
    rows, toc_rows = filter_rows(soil, log)
    pah = rows[rows.Analysis_Type == "PAH"]
    compounds = fix_compound_list(pah, log)
    # reference station coordinates: every labelled soil sample, all five campaigns
    ref = sample_table(soil)
    smp = assign_stations(sample_table(rows), ref, log)
    log.add(f"[stations] PAH/hopane samples {len(smp)}; with station {int(smp.station.notna().sum())}; stations "
            f"{smp.station.nunique()}")
    res = resolve_replicates(rows[rows.Analysis.isin(compounds + [HOPANE])], smp, log)
    hop = res[res.compound == HOPANE]
    res = res[res.compound != HOPANE]
    # TOC (mean of replicate rows, ASSUMED)
    toc = toc_rows.groupby("Sample_ID").value.mean().rename("toc").reset_index().rename(columns={"Sample_ID": "sample"})
    smp = smp[smp.station.notna()]
    st = smp.groupby("station").agg(lat=("lat", "median"), lon=("lon", "median"),
                                    state=("state", lambda x: x.mode().iloc[0])).reset_index()
    st = scat_oiling(st, max_zones_shp, log)
    smp = smp.merge(st[["station", "oil_class", "scat_code", "d_scat_m"]], on="station", how="left")
    return Resolved(smp, res, compounds, toc, hop, st)


def build(prep: Resolved, mode: str = "tobit", surface_only: bool = False, log: Log | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = prep.smp[prep.smp.depth_class == "0-2cm"] if surface_only else prep.smp
    res = prep.res[prep.res["sample"].isin(keep["sample"])]
    p = impute(res, prep.compounds, keep, prep.toc, mode, log)
    s = sample_sums(p, None, prep.hop, keep, prep.compounds, log)
    return s, station_campaign_table(s)


def main(root: Path | None = None) -> None:
    root = root or Path(__file__).resolve().parents[2]
    csv_dir = Path("/home/claude/work/stage2/coastal_wetland_veg/extracted_csv")
    shp = root / "data/raw/scat/18611/SCAT_Max_OilZones_Louisiana_2014_09_30Sorted.shp"
    log = Log()
    prep = prepare(csv_dir, shp, log)
    s, sc = build(prep, "tobit", False, log)
    log.add(f"[table] station-campaign-depth rows {len(sc)}; stations {sc.station.nunique()}; stations by number of campaigns: "
            f"{sc.groupby('station').campaign.nunique().value_counts().sort_index().to_dict()}")
    out = root / "results" / "pah_decline"
    out.mkdir(parents=True, exist_ok=True)
    sc.to_csv(out / "station_campaign.csv", index=False)
    log.write(out / "processing_log.txt")


if __name__ == "__main__":
    main()
