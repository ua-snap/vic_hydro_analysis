# 02 — Uses and options (draft; quantitative checks pending)

## Uses of the raw NCAR data (daily, all variables, 1950–2099)

Things a hydrologist or engineer could reasonably do with the raw files:

- **Basin water balance and water yield:** sum `RUNOFF + BASEFLOW` over a watershed to get mean
  annual and seasonal water yield and its projected change.
- **Routed streamflow:** feed daily runoff and baseflow into a routing model (mizuRoute, RAPID,
  etc.) for hydrographs at points of interest. This is how the product was designed to be used.
  Treat it as a relative-change or delta method, because the model isn't calibrated in Alaska.
- **Snow and glacier:** SWE timing and magnitude, snowmelt timing, glacier melt contribution
  (1,913 glacier cells).
- **Drought and soil-moisture anomalies:** use as anomalies, not absolute values.
- **Energy balance and soil temperature** (`eb`): ground heat flux and soil temperatures for
  permafrost-adjacent screening. Low confidence.
- **Ensemble spread:** 10 GCMs × 2 RCPs gives a usable estimate of GCM uncertainty, though only
  for CMIP5 and BCSD.
- **Not suitable for:** daily extremes or design floods (BCSD does a poor job of daily extremes),
  low flows, anything gauge- or design-scale without local evaluation.

## Uses of the curated data (decadal means of monthly summaries, per cell, point API)

- Point "what's the climate and hydrology trajectory here" screening in earthmaps.io and Arctic-EDS.
- Seasonal shifts in snow (`swe`, `snow_melt`). Currently the only SWE in the API.
- Coarse ET change and seasonal water-balance context for a location.
- **Weak:** `runoff` is surface-only, rounded to whole mm, and per cell. It can't be summed into
  a basin without bulk-downloading GeoTIFFs. `pcp`, `tmax` and `tmin` are redundant.
- Not possible with the curated product: streamflow, basin totals, daily statistics, cross-model
  uncertainty (no ensemble summaries), or change relative to a baseline.

## Options

### A. Keep as is

- **Pros:** zero cost. No broken links or clients (earthmaps.io, Arctic-EDS hydrology tab, CSV
  users). Only SWE source until the CMIP6/WRF-ERA5 snow products ship. Correctly labeled as
  surface runoff in the API docs.
- **Cons:** the feedback stands. The flagship variable (`runoff`) is the least defensible one
  (missing baseflow → understates yield and misrepresents winter flow; per-cell values invite
  misuse). Three of 12 variables are redundant with better products. No uncertainty or change
  framing. Reputational risk if a user designs with surface runoff as if it were total runoff.

### B. Remove entirely

- **Pros:** removes a product that experts call not useful and that invites misuse. Less
  maintenance (Rasdaman coverage, API route, EDS tab, tests). Pushes streamflow users to
  `/arctic_hydrology`, which is the better product for that question.
- **Cons:** loses the only SWE, ET, soil-moisture, snowmelt and glacier-melt projections in the
  API, and the only 10-GCM, 2-scenario, end-of-century hydrology for Alaska (RASM covers
  mid-century, CESM2 and SSP3-7.0 only). Breaks existing clients and any downstream users.
  Statewide coverage includes SE Alaska glaciers. Throws away work when a modest fix addresses
  the main critique.
- **Mitigation:** deprecate in stages. Keep the raw-data link and citation, and point users to
  RASM and the CMIP6 products.

### C. Reprocess: re-curate the NCAR outputs and aggregate by watershed

Uses the existing NCAR outputs and SNAP's existing curation and API patterns. The VIC run is not
redone.

1. **Fix runoff:** add `baseflow` and `total_runoff` (summed daily before monthly totals and
   before rounding). Rename the served variable to `surface_runoff`, or drop it.
2. **Drop redundant met variables** (`tmax`, `tmin`, `pcp`), or keep `pcp` only for
   water-balance closure (P − ET − R − ΔS).
3. **Add a change/uncertainty framing:** baseline (Daymet run and/or BCSD 1980–2009) and deltas
   (absolute and %), multi-model median, range, and number of models agreeing on the sign of
   change.
4. **Aggregate by watershed:** HUC8 (157) and HUC10 (2,570) area-weighted means of total runoff,
   ET, P, SWE and snowmelt (monthly, by era). Serve them through the existing `/places` and
   `/boundary` HUC IDs, the same way other SNAP area queries work.
5. **Document fitness for use:** "regionally parameterized, not calibrated in Alaska". Recommend
   relative change and model agreement. Caveat on BCSD extremes. Point to `/arctic_hydrology`
   for streamflow.

- **Pros:** addresses the specific critique: the scale moves from cell to watershed, and the
  variable becomes total runoff instead of surface only. Keeps the unique variables and the
  10-GCM, end-of-century ensemble. Complements RASM (different models, scenarios and period).
  Change plus agreement framing is the defensible way to use uncalibrated model output.
  Reuses existing pipeline code (`config.py` edits) and existing HUC infrastructure.
- **Cons:** costs staff time (curation, Rasdaman ingest, API route changes, front-end changes,
  QC). It's still CMIP5/BCSD and uncalibrated: reprocessing improves presentation, not model
  skill. Watershed means still aren't routed streamflow, so they may not satisfy engineers who
  want hydrographs. It's a new product that needs to be maintained.

## Future directions (mention only)

- Route NCAR runoff with mizuRoute on MERIT or NHD to get streamflow comparable to RASM.
- Skill assessment of the Daymet run against USGS gauges, SNOTEL and MODIS snow.
- Long term: replace with a CMIP6-forced hydrology product, which could be built on the
  CMIP6 downscaled and WRF-ERA5 datasets.

## Checks still needed to support the report (need raw-data access)

- [ ] Baseflow share of total runoff: domain-wide, by region/HUC8, and by month (winter vs freshet).
- [ ] Change in surface runoff vs change in total runoff, late century vs historical. Look for
      sign disagreement and magnitude differences.
- [ ] Spread within HUC8 (cell-to-cell) vs across models, to show why aggregating helps.
- [ ] Sanity check: our monthly sum of raw RUNOFF should match the API value at one point.
