"""Match CRMS vegetation sites to Deepwater Horizon SCAT shoreline oiling.

Rule fixed BEFORE looking at any vegetation outcome (all thresholds ASSUMED):
  oiled    : a SCAT zone with max oiling Light/Moderate/Heavy (any TB variant) within 1,000 m
  unoiled  : SCAT surveyed shoreline within 1,000 m, and no oiled zone (Very Light or worse) within 5,000 m
  excluded : everything else (not surveyed nearby, or only Very Light / negligible oil nearby)
first_oil_date = earliest SCAT survey recording oil within 1,000 m (all-surveys layer).\nDistances use UTM 15N (EPSG:32615). Distance to nearest SCAT-surveyed shoreline is reported as a
proxy for distance to the marsh edge; SCAT teams surveyed the open-water edge, not interior ponds.
"""
import sys, geopandas as gpd, pandas as pd, numpy as np
allp, maxp, sites_csv, out = sys.argv[1:5]
UTM = 32615
a = gpd.read_file(allp).to_crs(UTM)
m = gpd.read_file(maxp).to_crs(UTM)
s = pd.read_csv(sites_csv)
s = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.lon, s.lat), crs=4326).to_crs(UTM)

OILED = {"Light", "Light_TB", "Moderate", "Mod_TB", "Heavy", "Heavy_TB"}
ANY_OIL = OILED | {"Very_Light"}
def nearest(pts, lines, name):
    j = gpd.sjoin_nearest(pts[["site", "geometry"]], lines[["geometry"]], distance_col=name, how="left")
    return j.groupby("site")[name].min()

s.index = s.site.values
s["d_surveyed_m"] = nearest(s, a, "d")
s["d_oiled_m"] = nearest(s, m[m.OilCatCode.isin(OILED)], "d")
s["d_any_oil_m"] = nearest(s, m[m.OilCatCode.isin(ANY_OIL)], "d")
s["d_heavy_m"] = nearest(s, m[m.OilCatCode.isin({"Heavy", "Heavy_TB", "Moderate", "Mod_TB"})], "d")
# Max oiling category of the nearest oiled zone, and when that maximum was recorded
jn = gpd.sjoin_nearest(s[["site", "geometry"]], m[["OilCatCode", "max_date", "segment", "geometry"]], how="left")
jn = jn.drop_duplicates("site").set_index("site")
s["nearest_max_oiling"] = jn.OilCatCode; s["nearest_max_date"] = jn.max_date; s["nearest_segment"] = jn.segment

# Oil arrival: first SCAT survey date with any oil (Very Light or heavier) within 1,000 m of the site
oiled_obs = a[a.OilCatCode.isin(ANY_OIL)][["SurvDate", "geometry"]]
near = gpd.sjoin(s[["site", "geometry"]].assign(geometry=s.geometry.buffer(1000)), oiled_obs, predicate="intersects")
s["first_oil_date"] = near.groupby("site").SurvDate.min().dt.date.astype(str)

s["group"] = np.where(s.d_oiled_m <= 1000, "oiled",
              np.where((s.d_surveyed_m <= 1000) & (s.d_any_oil_m > 5000), "unoiled", "excluded"))
cols = ["site", "lat", "lon", "group", "d_surveyed_m", "d_oiled_m", "d_heavy_m", "d_any_oil_m",
        "nearest_max_oiling", "nearest_max_date", "nearest_segment", "first_oil_date"]
s[cols].round(1).to_csv(out, index=False)
print(s.group.value_counts().to_string())
for g in ["oiled", "unoiled"]:
    d = s[s.group == g].d_surveyed_m
    print(f"\n{g}: n={len(d)}  distance to surveyed edge (m): median {d.median():.0f}, "
          f"<=50 m: {(d<=50).sum()}, <=100 m: {(d<=100).sum()}, <=250 m: {(d<=250).sum()}")
print("\nAll sites: distance to oiled zone (m) quantiles", s.d_oiled_m.quantile([.05,.25,.5]).round(0).to_dict())
print(s[s.group=="oiled"][["d_surveyed_m","d_oiled_m","nearest_max_oiling"]].sort_values("d_oiled_m").to_string())
