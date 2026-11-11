import numpy as np, pandas as pd, rasterio, pystac_client, planetary_computer as pc
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from pyproj import Transformer
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
cx, cy, half = 801850, 3261250, 300
xmin,xmax,ymin,ymax = cx-half, cx+half, cy-half, cy+half
tr = Transformer.from_crs(32615, 4326, always_xy=True)
bbox = [*tr.transform(xmin, ymin), *tr.transform(xmax, ymax)]
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
W = 600; T = from_bounds(xmin, ymin, xmax, ymax, W, W)
out = {}
for yr in (2010, 2015):
    items = list(cat.search(collections=["naip"], bbox=bbox, datetime=f"{yr}-01-01/{yr}-12-31").items())
    acc = np.zeros((4, W, W)); dates = set()
    for it in items:
        with rasterio.open(it.assets["image"].href) as src:
            with WarpedVRT(src, crs="EPSG:32615", transform=T, width=W, height=W, resampling=Resampling.bilinear, nodata=0) as v:
                a = v.read([1,2,3,4]).astype(float)
        m = (acc.sum(0) == 0) & (a.sum(0) > 0)
        acc[:, m] = a[:, m]; dates.add(str(it.datetime.date()))
    print(yr, [i.id for i in items], (acc.sum(0)==0).mean())
    out[yr] = (acc, sorted(dates))
g = pd.read_excel("/home/claude/Shoreline_remediation/data/external/zengel2022/zengel2022_griidc_erosion.xlsx", "GIS field erosion points")
px, py = Transformer.from_crs(4326, 32615, always_xy=True).transform(g.LON_DD.values, g.LAT_DD.values)
def stretch(x):
    v = x[x.sum(-1) > 0]; lo, hi = np.percentile(v, 1, axis=0), np.percentile(v, 99, axis=0)
    return np.clip((x - lo) / (hi - lo), 0, 1)
def draw(kind, fname):
    fig, axs = plt.subplots(1, 2, figsize=(16, 8.6), facecolor="#F5F3EC")
    for ax, yr in zip(axs, (2010, 2015)):
        a, d = out[yr]
        img = a[[0,1,2]] if kind == "rgb" else a[[3,0,1]]
        ax.imshow(stretch(img.transpose(1,2,0)), extent=[xmin, xmax, ymin, ymax])
        for gx in range(xmin - xmin % 100 + 100, xmax, 100): ax.axvline(gx, color="white", lw=0.7, alpha=0.55)
        for gy in range(ymin - ymin % 100 + 100, ymax, 100): ax.axhline(gy, color="white", lw=0.7, alpha=0.55)
        ax.add_patch(Rectangle((801800, 3261200), 100, 100, fill=False, ec="#F2B05E", lw=4))
        if kind == "rgb":
            ax.scatter(px, py, s=9, c="#ffffff", edgecolors="#14262E", linewidths=0.5, zorder=3)
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(("Aerial photo" if kind == "rgb" else "Near-infrared view") + f", {d[0]}", fontsize=22, color="#14262E", pad=14)
        for s in ax.spines.values(): s.set_visible(False)
    plt.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.92, wspace=0.03)
    plt.savefig(fname, dpi=110, facecolor="#F5F3EC")
draw("rgb", "naip_pair.png"); draw("nir", "naip_nir_pair.png")
