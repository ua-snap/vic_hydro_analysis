# 01 — Inventory: raw vs curated VIC-Hydro, and overlapping SNAP holdings

Working notes (2026-11-13). Sources: `vic_hydro_assessment.md`, `ua-snap/ardac-curation`
(`curation/ncar12km_decadal_summaries/`), `ua-snap/data-api` (main branch, fetched 2026-11-13).

## 1. Raw data (NCAR product)

- Mizukami et al. 2022, doi:10.5065/c3kn-2y77. VIC 4.2.glacier, 1950–2099, **daily**, 12 km grid
  (polar stereographic), 14,227 land cells.
- Forcing: 10 CMIP5 GCMs × RCP4.5/RCP8.5, BCSD-downscaled against Daymet v3 (1980–2017), plus a
  **Daymet-forced historical run** (1980–2016; 37 annual files on Chinook).
- File groups per model/scenario/year:
  - `wf` (fluxes): RUNOFF (surface), BASEFLOW, EVAP, PRCP, SNOW_MELT, GLACIER_MELT
  - `ws` (states): SWE, IWE, SM1–3, WATER_ERROR
  - `eb` (energy): NET_SHORT, NET_LONG, SENSIBLE, LATENT, GRND_FLUX, SOIL_TEMP1–3, ENERGY_ERROR
  - `met` (forcing): tmax, tmin, pcp
- No river routing, so there is **no streamflow**. Values are per-cell runoff depths in mm.
- On Chinook: `/beegfs/CMIP6/cparr4/AK_NCAR_12km/{met,vic_hydro/{daily,monthly}}`. Daily and
  monthly versions both exist. **The files are owner-only (`-rwx------`) and can't be read from
  this account.**

## 2. Curated data (what SNAP serves)

- Pipeline: daily → monthly summary (sum, mean or max) → mean over each decade → GeoTIFF, rounded
  to integers (temperature to 0.1) → reprojected to EPSG:3338 → Rasdaman coverage `hydrology`.
- 12 variables: `evap, glacier_melt, iwe, pcp, runoff, sm1–3, snow_melt, swe, tmax, tmin`.
  - `swe` and `iwe` are the **monthly maximum** of daily values, averaged over the decade.
- Dimensions: 10 models × 2 RCPs × 12 months × 15 decades (1950s–2090s).
- **Not served:** BASEFLOW (so total runoff is missing), the energy-balance group, the Daymet
  historical run, WATER_ERROR, cross-model statistics, and change/delta products.
- API (`routes/hydrology.py`): **point queries only**. Each call returns the full
  model × scenario × month × decade cube for one 12 km cell. There is no area or watershed query.
  - `?summarize=mmm` gives min/mean/max across decades within each model.
  - Arctic-EDS hydrology section (`ua-snap/arctic-eds`, `app/components/reports/Hydrology.vue`):
    - **Charts** monthly `runoff` and `evap`: mean of models with a lowest-to-highest band, by
      era (2010–39, 2040–69, 2070–99) against 1950–2009.
    - **Downloads** the full `/hydrology/point` CSV with all 12 variables.
    - Summary comes from `routes/eds.py` → `eds_hydrology_data`: min/mean/max over 4 eras.
    - Labels the variable plain "Runoff". The headline sentence reports "% change in annual runoff
      by mid-century", which is surface runoff only.
    - The data panel says "9 GCMs" and "Baseline: Daymet, 1950–2009 (modeled)". The API docs
      list 10 models, and 1950–2009 is the BCSD/GCM historical period, not the Daymet run
      (1980–2016). **Check both with the EDS team.**
    - Read from the repo's default branch, not the live page (it's rendered client-side).
  - `runoff` is documented as "surface runoff", but users will likely read it as total.
- Curated GeoTIFFs were not found on Chinook. Rasdaman appears to be the only copy.

## 3. Overlap with other SNAP holdings in the data-api

| VIC-Hydro variable(s) | Other SNAP source | Notes |
|---|---|---|
| `tmax`, `tmin`, `pcp` | `/cmip6_downscaled` (13 CMIP6 GCMs, 4 km, daily, 1965–2100); `/era5wrf` (4 km, 1960–2023); `/taspr` (2 km, CRU/AR5) | Fully redundant. All are newer (CMIP6) or higher resolution. |
| `swe` | **`/cmip6`**: `snw` (SWE, mm), monthly, 1950–2100, pan-Arctic, most models (not KACE-1-0-G). Downscaled CMIP6 snow and WRF-ERA5 snow are in development. (`/snow` is CRU-based *snowfall* equivalent, not SWE.) | Partly redundant. VIC-Hydro is the only **12 km** SWE until the downscaled products ship. `/cmip6` is at global-model resolution (grid spacing not stated in the API docs). |
| `runoff` (as a stand-in for streamflow) | **`/arctic_hydrology`**: RASM-modeled daily streamflow and water temperature on 34,346 MERIT-Hydro stream segments in Alaska and Canada. Blaskey et al. 2024, doi:10.18739/A25M62870. Historical 1990–2021 (ERA5-WRF "Blaskey" baseline) and mid-century 2034–2065, CESM2 under SSP3-7.0, plus PGW runs. ~60 flow statistics and daily hydrograph climatologies. | Already answers "give me streamflow on a river". Limits: mid-century only, one GCM family, one scenario. |
| `evap`, `sm1–3`, `snow_melt`, `glacier_melt`, `iwe` | None | Unique to VIC-Hydro. |
| (CONUS analogue) | `/conus_hydrology`: PRMS streamflow on NHM segments, with USGS gage comparisons | Shows the shape of product hydrologists expect: segment streamflow plus an observed baseline. |

## 4. Why grid-cell runoff is the wrong unit for streamflow users

- Streamflow at a point integrates runoff from every cell upstream. A single 12 km cell's runoff
  depth isn't streamflow, and without routing it can't be turned into flow timing at a gauge.
- A watershed-average runoff depth (e.g. HUC8 mean of total runoff, in mm, or converted to a
  volume) **is** a meaningful water-yield number. It approximates long-term mean annual flow at
  the basin outlet, though not its timing at daily scale. This is how hydrologists use unrouted
  LSM output for water-balance and screening work.
- Monthly basin totals carry some seasonal information, but they arrive earlier than routed flow
  (no channel travel time and no lake or wetland storage). At HUC8 scale and monthly resolution
  this lag is usually small compared with model error. Large basins (e.g. the Yukon) can't be
  treated this way.

## 5. HUC polygons

- Source: `https://earthmaps.io/places/hucs` (157 HUC8, 2,570 HUC10; USGS WBD) and
  `https://earthmaps.io/boundary/area/<id>`.
- Fetched with `scripts/fetch_huc8.py` → `~/tmp/vic_hydro_analysis/boundaries/huc8.gpkg`.
