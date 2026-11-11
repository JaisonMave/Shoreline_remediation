"""Export a Landsat NDVI time series for an oiled site and a reference site from Google Earth Engine.

NOT YET RUN: this script was written without access to Earth Engine. Expect to fix small things on the
first run. It needs a Google Earth Engine account and `pip install earthengine-api`, then `earthengine
authenticate` once.

Before running, set OILED and REFERENCE below to polygons you have digitised yourself:
  - OILED: a strip of marsh edge that the shoreline surveys (SCAT) recorded as heavily oiled.
  - REFERENCE: a similar marsh edge nearby, with the same vegetation and exposure, recorded as unoiled.
Keep each polygon narrow (oiling was concentrated within about 15 m of the marsh edge) but large enough
to hold at least 20 Landsat pixels.

Output: ndvi_observations.csv with one row per image and site (date, site, ndvi, pixels). Feed it to
recovery_timeseries.monthly_medians() and then fit_recovery().
"""
import ee
import pandas as pd

OILED = None      # e.g. ee.Geometry.Polygon([[lon1, lat1], [lon2, lat2], ...])
REFERENCE = None  # same form
START, END = "2000-01-01", "2020-12-31"

# Landsat Collection 2, Level 2 (surface reflectance). Tuple: collection id, red band, near-infrared band.
SENSORS = [
    ("LANDSAT/LT05/C02/T1_L2", "SR_B3", "SR_B4"),
    ("LANDSAT/LE07/C02/T1_L2", "SR_B3", "SR_B4"),
    ("LANDSAT/LC08/C02/T1_L2", "SR_B4", "SR_B5"),
]


def ndvi_image(image, red, nir):
    qa = image.select("QA_PIXEL")
    # QA_PIXEL bits: 1 dilated cloud, 3 cloud, 4 cloud shadow, 5 snow.
    clear = (qa.bitwiseAnd(1 << 1).eq(0).And(qa.bitwiseAnd(1 << 3).eq(0))
             .And(qa.bitwiseAnd(1 << 4).eq(0)).And(qa.bitwiseAnd(1 << 5).eq(0)))
    scaled = image.select([red, nir]).multiply(0.0000275).add(-0.2)  # Collection 2 scale and offset
    return scaled.normalizedDifference([nir, red]).rename("ndvi").updateMask(clear).copyProperties(image, ["system:time_start"])


def site_series(geometry, site):
    rows = []
    for collection_id, red, nir in SENSORS:
        collection = ee.ImageCollection(collection_id).filterBounds(geometry).filterDate(START, END)

        def summarise(image, red=red, nir=nir):
            stats = ndvi_image(image, red, nir).reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
                geometry=geometry, scale=30, maxPixels=1e7)
            return ee.Feature(None, {"date": image.date().format("YYYY-MM-dd"), "ndvi": stats.get("ndvi_mean"),
                                     "pixels": stats.get("ndvi_count")})

        features = collection.map(summarise).filter(ee.Filter.notNull(["ndvi"])).getInfo()["features"]
        rows += [{**feature["properties"], "site": site, "sensor": collection_id.split("/")[1]} for feature in features]
    return rows


def main():
    if OILED is None or REFERENCE is None:
        raise SystemExit("Set OILED and REFERENCE to your digitised polygons first (see the notes at the top).")
    ee.Initialize()
    table = pd.DataFrame(site_series(OILED, "oiled") + site_series(REFERENCE, "reference"))
    table.sort_values(["date", "site"]).to_csv("ndvi_observations.csv", index=False)
    print(f"Wrote ndvi_observations.csv with {len(table)} rows.")


if __name__ == "__main__":
    main()
