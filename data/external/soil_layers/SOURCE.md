# SSURGO and SoilGrids values at the CRMS site positions

Retrieved 2026-11-12 by `scripts/fetch_soil_layers.py` for `validation/soil_layer_check.py`
(plan: `docs/SOIL_LAYER_CHECK_PLAN.md`). Site list and positions: the 392 CRMS sites (first 8 characters of Station ID)
of `data/external/crms_soil/CRMS_Soil_Properties.csv`, position = mean of the site's cores' coordinates. Values are
as returned by the services (untouched), so the comparison can be rerun offline.

- `ssurgo_sites.csv` (392 rows): site, lon, lat, mukey of the SSURGO map unit at the point. Source: USDA NRCS Soil Data
  Access, POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest (format JSON+COLUMNNAME), function
  SDA_Get_Mukey_from_intersection_with_WktWgs84, 20 points per call. SHA-256 6c6375bc0b26cbff81d4604a84d1524ca7a6726ed78720ee80841caf204fbc3f.
- `ssurgo_horizons.csv` (760 rows, 107 map units): mukey, cokey, compname, comppct_r, chkey, hzdept_r, hzdepb_r, om_r,
  dbthirdbar_r, ec_r, ph1to1h2o_r for every component and horizon of those map units. Units (NRCS SSURGO metadata, 2.3.2):
  om_r %, dbthirdbar_r g/cm3, ec_r dS/m, depths cm; the unit of ph1to1h2o_r is not listed there and is ASSUMED to be pH
  units. SHA-256 509e54f1ef1f2d4e8ee0660bb5d662cca02fe9ac057a921165b7039dff468835.
- `soilgrids_raw.csv` (7,056 rows = 392 sites x 3 properties x 2 depths x 3 statistics): site, lon, lat, prop, depth,
  stat, raw (integer as mapped; blank = nodata in the raster, 1,614 rows). Source: ISRIC SoilGrids v2.0 cloud
  rasters https://files.isric.org/soilgrids/latest/data/<prop>/<prop>_<depth>_<stat>.vrt (bdod, phh2o, soc; 0-5cm and
  5-15cm; mean, Q0.05, Q0.95), read with rasterio over /vsicurl/, coordinates transformed to Interrupted Goode Homolosine
  with pyproj. Conversions from the service's d_factors (REST example response): bdod cg/cm3 /100 = g/cm3; phh2o pH x10 /10;
  soc dg/kg /10 = g/kg. SHA-256 e0fa729a77d75eb0dd2691506dffcc06afdef278e03a8a5d0ac286cc42fb91cc.
- Raw SDA responses (JSON) were cached outside the repository and are not committed.
- Licence: not checked for SSURGO or SoilGrids (the earlier reachability note recorded none).
- Caveats: these are map-unit and grid-cell values (model predictions for SoilGrids), not measurements. SoilGrids has
  no raster value at 90 of the 392 site positions (bdod; water or masked pixels). SSURGO has a map unit at all 392 points but
  some map units have no value in 0 to 15 cm (e.g. water, miscellaneous). The REST fallback was not needed.
