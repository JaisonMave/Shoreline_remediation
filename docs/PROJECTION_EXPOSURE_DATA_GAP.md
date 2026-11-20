# Release-and-exposure hindcast: data-gap record (Session 5, 20 Nov 2026)

Outcome: **no transport simulation can be run from this checkout.** The dated shoreline surveys needed to *evaluate* a hindcast are
present; the release and forcing inputs needed to *run* one are not. The runner returns `exposure_inputs_unavailable` for the
replayable request below, records the missing inputs in the manifest and exports the survey observations. No engine was installed,
imported or evaluated, and nothing was downloaded.

## 1. Candidate case

| Item | Value |
| --- | --- |
| Case ID | `dwh_mobile_sector_2010` (`src/shoreline_remediation/projections/catalogue.py`) |
| Release | Deepwater Horizon (MC252), northern Gulf of Mexico |
| Window | 20 April 2010 (release start; scenario start and `as_of`) to 31 August 2010 |
| Shoreline region | SCAT segments of the Mobile Incident Command Post: Mississippi, Alabama, Florida panhandle; segment midpoints lon -89.53 to -84.18, lat 29.59 to 30.52; ESI 3A sand beach dominant, also marsh and armoured shore |
| Why this case | It is the only release in the checkout with visit-level, dated shoreline surveys (3,007 segments, 28,628 segment-visits from 5 May 2010). Louisiana marsh SCAT in the checkout is a CRMS match table, not visit-level. |
| Request | `examples/projections/dwh_mobile_exposure_hindcast.json` (endpoint `shoreline_oil_contact`, model `transport_hindcast/1`) |

## 2. Input inventory (searched: `data/`, `results/`, `docs/`; no NetCDF/GRIB files anywhere in the checkout)

| Input | Essential | Status | What exists (path, provenance) | Variables, units | Dates | Coverage | Overlap with the case |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Release location | yes | **absent** | none as data; the MC252 position appears only in literature text | lon/lat, depth | - | - | cannot be checked |
| Release timing | yes | **partial** | start date 2010-04-20 only, as code constants (`scripts/build_beach_series.py` `SPILL_START`; `recovery_view.SPILL_YEAR`); no dated release or capping record | datetime | start only | - | start matches; duration unknown |
| Release amount or rate | yes | **absent** | none | m3/day or bbl/day, time series | - | - | cannot be checked |
| Oil type | yes | **proxy** | `data/oil_properties.csv` (NOAA ADIOS export): no MC252 record; generic South Louisiana crudes AD01025 (API 37.0, 1996), EC00696 (33.7, 2021), EC00698 (37.1, 2021) disagree | API, density kg/m3, viscosity cSt, pour point C | 1996, 2021 | not location-specific | proxy only; weathering at landfall not represented |
| Wind fields | yes | **absent** | none | u, v (m/s) | - | - | cannot be checked |
| Current fields | yes | **absent** | none | u, v (m/s) | - | - | cannot be checked |
| Shoreline geometry | yes | **partial** | `data/external/scat_dwh_mobile/beach_series.csv`: midpoints and lengths of 3,007 segments; raw SCAT shapefile (`data/raw/scat_mobile`) not in the checkout. `data/external/chandeleur_shoreline` is 2012-2017 and outside the region | midpoint lon/lat (EPSG:4326), length m | 27 Sep 2014 layer | MS, AL, FL | segments overlap; no line geometry for contact tests |
| Dated shoreline surveys | yes (evaluation) | **present** | `data/external/scat_dwh_mobile/beach_visits.csv` (NCEI 0163818 v1.1, DOI 10.7289/v53t9ffx, layer 18613; derived by `scripts/build_beach_series.py`) | status oiled / clear / partial_clear per segment and date; top oiling category | 2010-05-05 to 2013-06-18 | 3,007 segments | overlaps the window from 2010-05-05 |

Not used: `data/external/dwh_treatment` (cleanup archive package listings), `data/external/scat_dwh` (CRMS-SCAT match for marsh
vegetation sites), DIVER chemistry (not in this checkout), Chandeleur shorelines (post-event, different region).

## 3. What the surveys can verify (window 20 Apr to 31 Aug 2010)

Visit status comes from the derived table: a visit is **clear** when all zones are NOO and NOO zones cover at least 50% of the
segment length (ASSUMED in `scripts/build_beach_series.py`); 3 visits in the whole record are `partial_clear` and are treated as
uninformative. A segment **with no oil observed** (at least one clear visit, no oiled visit) is different from a segment **with no
visit** and from one whose window holds only partial_clear visits (**inconclusive**). Shoreline that SCAT never segmented is not in
the files and cannot be counted.

| Survey class (per segment) | Segments | Meaning |
| --- | --- | --- |
| `oiled_before_window` | 0 | oil observed on or before the scenario start; no first-arrival window; in-window visits still counted |
| `clear_then_oiled` | 944 | possible arrival window (last clear visit in the whole record, first oiled visit in the window]; median 11 days (IQR 4 to 27, max 89) |
| `oiled_at_first_visit` | 255 | never seen clear before the first oil: arrival bounded by (20 Apr 2010, first visit]: 27 to 125 days (median 75); MS 156, AL 60, FL 39 |
| `no_oil_observed` | 1,756 | at least one clear visit and no oiled visit in the window; 29 were oiled after 31 Aug, 1,727 have no oiled visit in the whole 2010-2013 record |
| `inconclusive_partial_clear` | 0 | visits in the window are all partial_clear; counted in n_visits; excluded from clear-segment and false-alarm counts |
| `not_visited_in_window` | 52 | in the SCAT layer, no visit in the window |

Pre-commit review corrections (20 Nov 2026; regression tests in `tests/test_projections_review_fixes.py`) added the
`oiled_before_window` and `inconclusive_partial_clear` classes and made arrival windows use the whole survey record. For this
request (start = release start) every total above is **unchanged**: no oil can precede the release, and no segment has only
partial_clear visits in the window. Later starts do change classes, for example:
- **Start 1 July 2010:** 667 `oiled_before_window` (such as ALBA1-001, first oiled 4 June); 389 `clear_then_oiled`, some with
  windows that begin in June; 143 `oiled_at_first_visit`; 1,710 `no_oil_observed`; 98 not visited. Candidate false-alarm
  denominator 574.
- **Start 12 August 2010:** 1 `inconclusive_partial_clear` (FLGU1-135, one partial_clear visit on 24 August).

First visit in the window 5 May 2010; first oiled visit 17 May 2010 (Mississippi).

**False alarms.** The layer does include never-oiled, surveyed segments, so a false-alarm measure is possible with care. Proposed
denominator: segments with at least two clear visits in the window and no oiled visit anywhere in the record (**731**). A simulated
contact there is a *candidate* false alarm, not a proven one: surveys can miss oil, and oil can arrive and leave between visits.

**Arrival windows** are intervals between visits, not arrival times. Their width depends on survey frequency, which differs between
segments and states. The 255 segments first seen already oiled give only a wide window that starts at the release start (27 to 125 days).

## 4. Exposure outcome vocabulary (catalogue `EXPOSURE_OUTCOMES`)

`contact` and `no_contact` require a **completed** simulation; `no_contact` is never used for missing inputs, a failed run, a domain
problem or a survey with no oil observed. Other outcomes: `exposure_inputs_unavailable` (this case today), `model_failed`,
`outside_domain` (request window outside the case window). The adapter contract (segment ID, arrival window, estimated exposure,
forcing provenance, uncertainty method) is not written yet because no engine can be exercised; it follows once inputs exist.

## 5. What would make the case runnable

1. A release record: MC252 location and depth, a dated discharge-rate time series with its source, and response removals if the
   adapter needs them (dispersant, burning, skimming) or an explicit statement that they are ignored.
2. Archived forcing covering 20 Apr to 31 Aug 2010 over the release and the surveyed coast (a suggested extent, not derived
   from data: lon about -91 to -84, lat 27.5 to 30.7): surface currents (a reanalysis or
   operational ocean model, versioned) and 10 m winds (reanalysis or station network), each with provenance, units and checksums.
3. Segment line geometry: the raw SCAT layer 18613 shapefile (already fetched once, `scripts/download_scat_mobile.sh`; checksums in
   `data/raw/scat_mobile/FETCHED.txt` on the machine that fetched it).
4. An oil record suitable for weathering (an MC252-specific assay), or a stated proxy with its sensitivity.

Then: freeze inputs at the scenario start; reserve every survey after `as_of` for evaluation; compare simulated contact with the
survey classes above against a pre-specified simple baseline (for example a distance-to-release or persistence baseline fixed
before any engine run), reporting hits, misses, candidate false alarms and arrival inside or outside the survey window. Ensemble
agreement remains a scenario frequency until calibrated. Any engine (PyGNOME is a candidate) runs in an optional environment that
the projection tests never import.

## 6. Replay

```
python -m src.shoreline_remediation.projections run --scenario examples/projections/dwh_mobile_exposure_hindcast.json --output runs/dwh_exposure
```
Exit 3; `manifest.json` has `status: unsupported`, `outcome.code: exposure_inputs_unavailable`, `exposure.inputs` (the table above),
`exposure.missing_essential`, `exposure.simulation_attempted: false`, `exposure.survey_summary`; `survey_contact.csv` has one row
per segment with `record_type observed_survey_contact`, `record_class observation` and role `evaluation_observation`.
