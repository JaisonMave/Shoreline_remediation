"""Choose oiled and reference marsh-edge sites in northern Barataria Bay from SCAT only (no NDVI used).
ASSUMED rules: box -90.05..-89.80 E, 29.38..29.55 N; oiled = SCAT segment whose maximum oiling was Heavy
and recorded in 2010; reference = segment whose zones are all 'NOO' and lie > 1,000 m from any zone
with Very Light or heavier oil; site polygon = 45 m buffer either side of the segment's shoreline lines.
Pairs: each oiled segment is paired with the nearest reference segment (references may repeat)."""
import sys, geopandas as gpd, pandas as pd
maxp, allp, out = sys.argv[1:4]
BOX = (-90.05, 29.38, -89.80, 29.55); UTM = 32615
m = gpd.read_file(maxp).to_crs(4326).cx[BOX[0]:BOX[2], BOX[1]:BOX[3]].to_crs(UTM)
oil = m[m.OilCatCode.isin(["Very_Light","Light","Light_TB","Moderate","Mod_TB","Heavy","Heavy_TB"])]
heavy = m[m.OilCatCode.isin(["Heavy","Heavy_TB"]) & m.max_date.str.startswith("2010")]
segs = m.dissolve(by="segment", aggfunc={"OilCatCode": lambda s: ",".join(sorted(set(s)))}).reset_index()
oiled = heavy.dissolve(by="segment").reset_index()[["segment","geometry"]]
noo = segs[segs.OilCatCode == "NOO"].copy()
noo["d_oil"] = noo.geometry.apply(lambda g: oil.distance(g).min())
ref = noo[noo.d_oil > 1000][["segment","geometry"]]
pairs = gpd.sjoin_nearest(oiled, ref.rename(columns={"segment":"ref_segment"}), distance_col="pair_dist_m")
pairs = pairs.drop_duplicates("segment")
rows = []
for i, r in enumerate(pairs.itertuples(), 1):
    rows.append({"pair": i, "group": "oiled", "segment": r.segment, "geometry": r.geometry.buffer(45)})
    rows.append({"pair": i, "group": "reference", "segment": r.ref_segment,
                 "geometry": ref.set_index("segment").geometry[r.ref_segment].buffer(45)})
g = gpd.GeoDataFrame(rows, crs=UTM)
g["pair_dist_m"] = g.pair.map(pairs.set_index(pd.RangeIndex(1, len(pairs)+1)).pair_dist_m.round(0))
g.to_crs(4326).to_file(out, driver="GeoJSON")
print(f"oiled segments: {len(oiled)}, reference candidates: {len(ref)}, unique refs used: {pairs.ref_segment.nunique()}")
print("pair distance m:", pairs.pair_dist_m.describe().round(0).to_dict())
