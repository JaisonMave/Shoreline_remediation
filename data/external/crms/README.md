# Louisiana coastal marsh vegetation by site and year (CRMS, 2006-2025)

Copied unchanged from https://github.com/anamikadristi/coastal-marsh-vegetation-extreme-events
(commit 76e2143cca1876834aaeced774173fe2b15fc4c5, 2026-10-24), by Anamika Dristi, MIT licence (see LICENSE).

- `crms_marsh_site_year.csv`: one row per monitoring site and year: field vegetation cover, species
  richness, growing-season MODIS NDVI, salinity, flooding and storm exposure.
- `hurricane_site_events.csv`: one row per site and hurricane season: wind-radius exposure class and the
  survey dates before and after the storm.

The underlying observations are public data from Louisiana's Coastwide Reference Monitoring System (CRMS,
CPRA), NOAA HURDAT2 storm tracks and NASA MOD13Q1 NDVI. See the source repository for full methods.

These files hold no oil-spill information. They are used here to test the event-study method on real
events and to measure hurricane effects on marsh vegetation. To study the 2010 spill with them, each site
would first have to be matched to the SCAT shoreline oiling layer (see docs/DATA_ACQUISITION.md).
