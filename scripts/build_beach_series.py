"""Build the sand-beach persistence table from DWH SCAT layer 18613 (NCEI 0163818, "SCAT All zones, Mobile").

Plain-language summary
----------------------
SCAT teams walked beach segments (about 500 m long) many times between May 2010 and June 2013. On each visit
they split the segment into "zones" with similar oiling and gave each zone an oiling category, including
"NOO" (no oil observed). The NCEI metadata say that zone letters are re-assigned on every visit and "have no
relationship to the IDs assigned to zones from previous survey dates", so a zone letter cannot be followed
through time. The unit we follow is therefore the SEGMENT (see docs/V5_BEACH_SAND_PLAN.md, section 2).

For every segment and survey date ("visit") we record whether any oil was seen (oiled visit) or every zone was
NOO (clear visit). For each sand-beach segment that was ever oiled we then record:
  * the predictors seen at the FIRST oiled visit (only information known at that moment);
  * L_days, R_days: the clearing time (first NOO visit) is only known to lie between the last oiled visit
    (L) and the first clear visit (R), counted in days from the first oiled visit;
  * if no clear visit was ever recorded, the series is right-censored at its last visit (R = empty);
  * re-oiling after the first clear visit (secondary, descriptive).

Inputs : data/raw/scat_mobile/18613/data/SCAT_AllZones_Mobile_2014_0927Sorted.shp (+ .dbf etc.), fetched by
         scripts/download_scat_mobile.sh. Raw files are not in git.
Outputs: data/external/scat_dwh_mobile/beach_series.csv   one row per segment (all ESI classes, oiled or not;
                                                          the analysis filters to ESI 3A oiled series)
         data/external/scat_dwh_mobile/beach_visits.csv   one row per segment-visit (status only, no names)
         data/external/scat_dwh_mobile/counts_check.json  structural counts, incl. the earlier agent's counts

Run:  python scripts/build_beach_series.py [--raw data/raw/scat_mobile]
No personal data (team member names) are written.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = ROOT / "data" / "raw" / "scat_mobile"
OUT = ROOT / "data" / "external" / "scat_dwh_mobile"
LAYER = "18613/data/SCAT_AllZones_Mobile_2014_0927Sorted.shp"

SPILL_START = pd.Timestamp("2010-04-20")
UTM = 32616  # WGS84 / UTM zone 16N, metres

# Oiling category codes (OilCatCode) in the SCAT order given by the layer's own `oil_order` field.
OIL_ORDER = {"NOO": 1, "Neg_TB": 2, "Light_TB": 3, "Mod_TB": 4, "Heavy_TB": 5,
             "Very_Light": 6, "Light": 7, "Moderate": 8, "Heavy": 9}
# Category groups fixed in the plan (section 3) before outcomes were looked at.
# Negligible tarballs (16 series) are merged with light tarballs because no state has 20 of them.
CAT_GROUP = {"Neg_TB": "tb_neg_light", "Light_TB": "tb_neg_light", "Mod_TB": "tb_mod_heavy",
             "Heavy_TB": "tb_mod_heavy", "Very_Light": "surface_light", "Light": "surface_light",
             "Moderate": "surface_mod_heavy", "Heavy": "surface_mod_heavy"}
# Surface oil thickness (SOThicknes). PO pooled >1 cm, CV cover 0.1-1 cm, CT coat 0.01-0.1 cm, ST stain <0.01 cm.
# 'FL' (10 records) is not in the metadata domain; ASSUMED thin (it is probably 'film').
THICK_GROUP = {"PO": "thick", "CV": "thick", "CT": "thin", "ST": "thin", "FL": "thin"}

ESI_SHARE_MIN = 0.80        # ASSUMED: a segment is "ESI 3A" if >= 80% of its ESI-coded zone length is 3A
NOO_COVER_MIN = 0.50        # ASSUMED: an all-NOO visit counts as "clear" only if NOO zones cover >= 50% of SegLength
RAY_BEARINGS = np.arange(120, 241, 20)  # ASSUMED: 7 rays, ESE through WSW (the open Gulf lies to the south)
RAY_LENGTH_M = 20_000.0     # ASSUMED
RAY_SKIP_M = 200.0          # ASSUMED: ignore crossings within 200 m of the start (adjacent segments)


def load(raw: Path) -> "pd.DataFrame":
    import geopandas as gpd  # noqa: F401  (pyogrio returns a GeoDataFrame)
    import pyogrio
    g = pyogrio.read_dataframe(raw / LAYER)
    g = g.drop(columns=[c for c in g.columns if c.startswith("Team")])  # personal names: never carried on
    g["len_m"] = g.to_crs(UTM).length
    return g


def earlier_agent_counts(g) -> dict:
    """Reproduce the counts reported in /home/claude/review/beach_evidence.md (series = segment + zone letter)."""
    out = {"records": int(len(g)), "records_by_state": g["State"].value_counts().to_dict(),
           "segments": int(g["Segment"].nunique()),
           "date_min": str(g["SurvDate"].min().date()), "date_max": str(g["SurvDate"].max().date())}
    for esi in ("3A", "4", "5", "6A"):
        r = g[g["ESIType"] == esi]
        s = r.groupby(["Segment", "Zone"])["SurvDate"].nunique()
        out[f"esi_{esi}"] = {"records": int(len(r)), "segment_zone_series": int(len(s)),
                             "with_3plus_surveys": int((s >= 3).sum()), "with_5plus_surveys": int((s >= 5).sum())}
    out["esi_missing_records"] = int(g["ESIType"].isna().sum())
    out["esi_missing_records_that_are_NOO"] = int((g["ESIType"].isna() & (g["OilCatCode"] == "NOO")).sum())
    out["oilcatcode_counts"] = g["OilCatCode"].value_counts(dropna=False).to_dict()
    out["duplicate_ZoneSurvID"] = int(g["ZoneSurvID"].duplicated().sum())
    return out


def segment_table(g):
    """Segment-level attributes: ESI class, length, midpoint and exposure proxy (geometry only, no outcomes)."""
    from shapely import STRtree
    from shapely.geometry import LineString
    from shapely.ops import linemerge, unary_union

    gp = g.to_crs(UTM)
    coded = g[g["ESIType"].notna()]
    share = coded.groupby(["Segment", "ESIType"])["len_m"].sum().reset_index()
    share["share"] = share["len_m"] / share["Segment"].map(coded.groupby("Segment")["len_m"].sum())
    share = share.drop(columns="len_m")
    top = share.sort_values(["share", "ESIType"], ascending=[False, True]).drop_duplicates("Segment")
    seg = g.groupby("Segment").agg(state=("State", "first"), county=("County", "first"),
                                   opdiv=("OpDiv", "first"), seg_length_m=("SegLength", "max")).reset_index()
    seg = seg.merge(top.rename(columns={"ESIType": "esi_main", "share": "esi_main_share"}), on="Segment", how="left")
    s3 = share[share["ESIType"] == "3A"].set_index("Segment")["share"]
    s4 = share[share["ESIType"] == "4"].set_index("Segment")["share"]
    seg["esi_3a_share"] = seg["Segment"].map(s3).fillna(0.0)
    seg["esi_4_share"] = seg["Segment"].map(s4).fillna(0.0)
    seg["esi_class"] = np.where(seg["esi_3a_share"] >= ESI_SHARE_MIN, "3A",
                                np.where(seg["esi_4_share"] >= ESI_SHARE_MIN, "4",
                                         np.where(seg["esi_main"].isna(), "unknown", "other")))

    # One shoreline line per segment = union of all its zone lines over all dates.
    geoms = gp.groupby("Segment")["geometry"].apply(lambda s: unary_union(list(s)))
    lines, mids = {}, {}
    for sid, geom in geoms.items():
        merged = linemerge(geom) if geom.geom_type == "MultiLineString" else geom
        if merged.geom_type == "MultiLineString":
            merged = max(merged.geoms, key=lambda x: x.length)
        lines[sid] = geom
        mids[sid] = merged.interpolate(0.5, normalized=True)
    ids = list(lines)
    tree = STRtree([lines[i] for i in ids])
    expo = {}
    for k, sid in enumerate(ids):
        p = mids[sid]
        open_n = 0
        for b in RAY_BEARINGS:
            th = np.deg2rad(b)
            dx, dy = np.sin(th), np.cos(th)  # bearing clockwise from north
            ray = LineString([(p.x + dx * RAY_SKIP_M, p.y + dy * RAY_SKIP_M),
                              (p.x + dx * RAY_LENGTH_M, p.y + dy * RAY_LENGTH_M)])
            hits = [j for j in tree.query(ray) if j != k and ray.intersects(lines[ids[j]])]
            open_n += (len(hits) == 0)
        expo[sid] = open_n / len(RAY_BEARINGS)
    mid_ll = gpd_points_to_lonlat({sid: mids[sid] for sid in ids})
    seg["exposure_open_frac"] = seg["Segment"].map(expo)
    seg["lon"] = seg["Segment"].map({k: v[0] for k, v in mid_ll.items()})
    seg["lat"] = seg["Segment"].map({k: v[1] for k, v in mid_ll.items()})
    return seg


def gpd_points_to_lonlat(points: dict) -> dict:
    import geopandas as gpd
    s = gpd.GeoSeries(list(points.values()), crs=UTM).to_crs(4326)
    return {k: (round(p.x, 6), round(p.y, 6)) for k, p in zip(points, s)}


def visit_table(g):
    """One row per segment x survey date. status: 'oiled', 'clear', 'partial_clear' (all NOO but NOO zones cover
    < 50% of the segment) or 'undefined' (only 'Undefined' category records)."""
    g = g.copy()
    g["oo"] = g["OilCatCode"].map(OIL_ORDER)  # NaN for 'Undefined' / missing
    g["oiled"] = g["oo"] > 1
    rows = []
    for (sid, d), r in g.groupby(["Segment", "SurvDate"], sort=True):
        seglen = float(r["SegLength"].max())
        defined = r[r["oo"].notna()]
        if defined.empty:
            rows.append((sid, d, "undefined", np.nan, None, None, None, np.nan, np.nan, np.nan))
            continue
        oiled = defined[defined["oiled"]]
        if len(oiled):
            top = oiled.sort_values(["oo", "len_m"], ascending=False).iloc[0]
            oiled_frac = min(1.0, float(oiled["len_m"].sum()) / seglen) if seglen > 0 else np.nan
            tb = float(oiled["TBCount"].fillna(0).sum())
            rows.append((sid, d, "oiled", oiled_frac, top["OilCatCode"], top["TidalZone"], top["SOThicknes"],
                         float(top["SODistro"]) if pd.notna(top["SODistro"]) else np.nan, tb,
                         float(defined["len_m"].sum()) / seglen))
        else:
            cover = float(defined["len_m"].sum()) / seglen if seglen > 0 else np.nan
            status = "clear" if cover >= NOO_COVER_MIN else "partial_clear"
            rows.append((sid, d, status, 0.0, "NOO", None, None, 0.0, 0.0, cover))
    v = pd.DataFrame(rows, columns=["segment", "date", "status", "oiled_frac", "top_cat", "top_tidal_zone",
                                    "top_thickness", "top_sodistro", "tb_count", "survey_cover"])
    return v


def series_table(v, seg):
    """One row per segment. Outcome columns are interval bounds in days from the first oiled visit."""
    out = []
    for sid, r in v.groupby("segment", sort=True):
        r = r[r["status"] != "undefined"].sort_values("date")
        n_all = len(r)
        oiled = r[r["status"] == "oiled"]
        base = {"segment": sid, "n_visits": n_all}
        if oiled.empty:
            out.append({**base, "ever_oiled": 0})
            continue
        f = oiled.iloc[0]
        t0 = f["date"]
        after = r[r["date"] > t0]
        days = (after["date"] - t0).dt.days.to_numpy()
        status = after["status"].to_numpy()
        row = {**base, "ever_oiled": 1,
               "first_oiled_date": str(t0.date()),
               "days_spill_to_first_oiled": int((t0 - SPILL_START).days),
               "first_cat": f["top_cat"], "first_cat_group": CAT_GROUP[f["top_cat"]],
               "first_tidal_zone": f["top_tidal_zone"] if f["top_tidal_zone"] in ("SU", "UI", "MI", "LI") else "missing",
               "first_thickness": THICK_GROUP.get(f["top_thickness"], "none"),
               "first_sodistro_pct": f["top_sodistro"], "first_tb_count": f["tb_count"],
               "first_oiled_frac": f["oiled_frac"],
               "n_visits_after_first_oiled": int(len(after)),
               "last_visit_days": int(days.max()) if len(days) else 0}
        row.update(_interval(days, status, partial_is_clear=False, prefix=""))
        row.update(_interval(days, status, partial_is_clear=True, prefix="alt_"))
        # Visit frequency during the at-risk period (first oiled visit to clearing or last visit); used ONLY for
        # the informative-visiting sensitivity check, never as a predictor.
        end = row["R_days"] if pd.notna(row["R_days"]) else row["last_visit_days"]
        times = np.concatenate([[0], days[days <= end]]) if len(days) else np.array([0])
        gaps = np.diff(times)
        row["median_gap_days"] = float(np.median(gaps)) if len(gaps) else np.nan
        row["max_gap_days"] = float(np.max(gaps)) if len(gaps) else np.nan
        # Re-oiling (descriptive): an oiled visit after the first clear visit.
        if pd.notna(row["R_days"]):
            later = after[(after["date"] - t0).dt.days > row["R_days"]]
            row["n_visits_after_clear"] = int(len(later))
            reo = later[later["status"] == "oiled"]
            row["reoiled"] = int(len(reo) > 0) if len(later) else np.nan
            row["days_clear_to_reoil"] = int((reo["date"].iloc[0] - t0).days - row["R_days"]) if len(reo) else np.nan
            row["reoil_cat"] = reo["top_cat"].iloc[0] if len(reo) else None
        out.append(row)
    s = pd.DataFrame(out)
    s = seg.rename(columns={"Segment": "segment"}).merge(s, on="segment", how="left")
    return s


def _interval(days, status, partial_is_clear: bool, prefix: str) -> dict:
    """Clearing interval (L, R] in days after the first oiled visit. R empty = right-censored at L."""
    clear_codes = ("clear", "partial_clear") if partial_is_clear else ("clear",)
    use = np.isin(status, ("oiled",) + clear_codes)
    d, st = days[use], status[use]
    L = 0
    for di, si in zip(d, st):
        if si in clear_codes:
            return {f"{prefix}L_days": int(L), f"{prefix}R_days": int(di), f"{prefix}censor": "interval"}
        L = di
    return {f"{prefix}L_days": int(L), f"{prefix}R_days": np.nan, f"{prefix}censor": "right"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DEFAULT))
    a = ap.parse_args()
    g = load(Path(a.raw))
    OUT.mkdir(parents=True, exist_ok=True)
    counts = earlier_agent_counts(g)
    seg = segment_table(g)
    v = visit_table(g)
    s = series_table(v, seg)
    sand = s[(s["esi_class"] == "3A") & (s["ever_oiled"] == 1)]
    counts["this_build"] = {
        "segments_by_esi_class": s["esi_class"].value_counts().to_dict(),
        "visits": int(len(v)), "visit_status": v["status"].value_counts().to_dict(),
        "esi_3A_segments_ever_oiled": int(len(sand)),
        "esi_3A_oiled_with_a_later_visit": int((sand["n_visits_after_first_oiled"] > 0).sum()),
        "esi_3A_oiled_by_state": sand["state"].value_counts().to_dict(),
        "esi_4_segments_ever_oiled": int(((s["esi_class"] == "4") & (s["ever_oiled"] == 1)).sum()),
        "esi_4_oiled_with_a_later_visit": int(((s["esi_class"] == "4") & (s["ever_oiled"] == 1)
                                               & (s["n_visits_after_first_oiled"] > 0)).sum()),
        "assumed": {"ESI_SHARE_MIN": ESI_SHARE_MIN, "NOO_COVER_MIN": NOO_COVER_MIN,
                    "RAY_BEARINGS": RAY_BEARINGS.tolist(), "RAY_LENGTH_M": RAY_LENGTH_M, "RAY_SKIP_M": RAY_SKIP_M},
    }
    v_out = v.copy()
    v_out["date"] = v_out["date"].dt.strftime("%Y-%m-%d")
    v_out.round(4).to_csv(OUT / "beach_visits.csv", index=False)
    s.round(4).to_csv(OUT / "beach_series.csv", index=False)
    with open(OUT / "counts_check.json", "w") as fh:
        json.dump(counts, fh, indent=2, default=str)
    print(json.dumps(counts["this_build"], indent=2, default=str))


if __name__ == "__main__":
    main()
