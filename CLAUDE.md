# CLAUDE.md — VIC-Hydro assessment

## Purpose

Decide what SNAP should do with its curated **VIC-Hydro** dataset: the NCAR 12 km Alaska VIC
hydrologic projections, served as decadal means of monthly summaries per grid cell through the
data-api `/hydrology` endpoint, earthmaps.io and arcticeds.org.

Why now: engineers and hydrologists have told us the data as served is not very useful. Runoff
values summarized per 12 km grid cell are the wrong scale for streamflow work, and the model is
not calibrated in Alaska. Temperature, precipitation and SWE are mostly duplicated by other SNAP
holdings.

## Deliverable

A **two-page summary for internal SNAP leads**, shared on Slack as a **PDF** with figures where
they help. Draft it in Markdown (`report/`) and build the PDF with pandoc + xelatex. Keep it to
two pages: tight prose, one table, one or two figures at most.

The summary must cover, in this order:

1. **What it is (raw data):** the NCAR source product.
2. **What we have (curated data):** what SNAP processed and serves.
3. **What the raw data could be used for.**
4. **What the curated data could be used for.**
5. **Options, with pros and cons for each:**
   - **A. Keep as is**
   - **B. Remove entirely**
   - **C. Reprocess.** This combines two things:
     - **Re-curate the NCAR outputs:** add `BASEFLOW` and `TOTAL_RUNOFF` (summed from daily data
       before summarizing), add change/delta products, cross-model median, range and sign
       agreement, and expose the Daymet-forced historical baseline.
     - **Aggregate by basin:** serve runoff and water-balance terms summarized over watersheds
       (e.g. HUC8/10/12) rather than per grid cell.
     - Out of scope: routing/streamflow (e.g. mizuRoute) and replacing the dataset with a
       different product. Mention them only briefly, as future directions.
6. **Recommendation.**

## Hard constraints

- **The NCAR VIC run cannot be re-run or recalibrated.** Every option has to work from existing
  NCAR outputs.
- **Analysis depth is "light checks":** a desk review plus a few cheap quantitative checks to
  support the claims. Examples: the baseflow share of total runoff, and how big the gap is
  between surface runoff and total runoff in magnitude, seasonality and projected change. **No**
  gauge or SNOTEL skill assessment. That belongs in the recommendations as future work.

## Key context (verify before citing)

`vic_hydro_assessment.md` is a context brief from an earlier session. Main points:

- Source: Mizukami et al. (2022), doi:10.5065/c3kn-2y77; *Climate Services* 27, 100312. VIC
  4.2.glacier, 1950–2099, forced by 10 CMIP5 GCMs × RCP4.5/8.5, BCSD-downscaled to 12 km against
  Daymet. No routing. Parameters come from transfer functions calibrated on CONUS (CAMELS)
  basins, so the accurate wording is "regionally parameterized, not calibrated in Alaska."
- **Curation dropped `BASEFLOW`.** The served `runoff` is surface runoff only
  (`ardac-curation/curation/ncar12km_decadal_summaries/config.py`, `variable_di["wf"]`).
- The Daymet-forced historical VIC run (1980–2017) was downloaded but is not served.
- The `?summarize=mmm` option gives min/mean/max **across decades**, not across models.
- Open items to check: whether the paper's limitations section really says "essentially
  uncalibrated"; negative `EVAP` values; a very large daily `GLACIER_MELT` maximum.

## Overlap with other SNAP holdings

The data-api already serves temperature, precipitation and SWE from other datasets. Two more
products are still in development:

- **CMIP6 downscaled snow variables**
- **WRF-downscaled ERA5** (4 km and 12 km), which includes snow variables

The write-up should name these as alternatives for `tmax`, `tmin`, `pcp` and `swe`. Look up exact
dataset and endpoint names in `ua-snap/data-api`.

## Data locations (Chinook)

| What | Path | Notes |
|---|---|---|
| Raw NCAR VIC, daily | `/beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/daily/{BCSD/<model>/<rcp>,daymet}/` | `*_BCSD_{wf,ws,eb}_<year>.nc4`; `daymet_{wf,ws,eb}_<year>.nc` |
| Raw NCAR VIC, monthly | `/beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/monthly/...` | Same layout. Use these for cheap checks where monthly data is enough. |
| Raw NCAR met | `/beegfs/CMIP6/cparr4/AK_NCAR_12km/met/` | tmax, tmin, pcp |
| Curated outputs | Rasdaman `hydrology` coverage via data-api | Curated GeoTIFFs not found on Chinook |

**Access status (2026-11-13):**
- `/beegfs/CMIP6/cparr4/AK_NCAR_12km/` (vic_hydro and met) is now readable. **It holds NCAR's
  PRELIMINARY release** (files created 2020-11, ncks 2021-04). SNAP's curation used the later
  published "replacement" release (Atlas, Feb 2023, now gone). The preliminary RCP4.5 runs have
  year misalignments; RCP8.5 appears unchanged between releases. See notes/05.
- **The published release is on NCAR GDEX as dataset `d010111`**, anonymous download, no token:
  - URL pattern:
    `https://osdf-director.osg-htc.org/ncar/gdex/d010111/alaska/{vic,met}/{daily,monthly}/BCSD/<model>/<rcp>/<model>_<rcp>_BCSD_{wf,ws,eb,met}_<year>.nc`
  - Daymet is under `.../{vic,met}/{daily,monthly}/daymet/` (check the exact path).
  - Verified: the daily `CanESM2_rcp45_BCSD_{wf,met}_2060.nc` MD5s equal the Feb 2023 wget
    checksums in ardac-curation `download_scripts/`, so GDEX = the curated release.
  - In that file, VIC PRCP equals the met pcp (the preliminary file doesn't), so NCAR fixed the
    CanESM2 offset.
  - File discovery: GDEX MCP server `https://gdex-mcp.k8s.ucar.edu/mcp` (public tools:
    list_datasets, find_dataset_files, get_data_access). Helper:
    `~/tmp/vic_hydro_analysis/gdex_call.sh <tool> '<json>'`.
- `/beegfs/CMIP6/NCAR_VIC/NCAR_NetCDF/` is readable but is **not** NCAR source data. It's a
  derived set made in Feb 2025: daily 1950–2099 stacks, one file per model/scenario (15.6 GB
  each), **reprojected to EPSG:3338** (~11.94 km, 318×224, a transform attribute but no coordinate
  variables). It holds only `EVAP/` (20 files), `RUNOFF/` (20) and `SM1/` (7). There's **no
  BASEFLOW**, so it can't support the baseflow check. A `.Rhistory` there shows a point extraction
  for "kennecott_mines".
- The NCAR gateway (`ucar.ral.hydro.predictions.alaska.vic.daily`) serves daily per-year files
  only. Re-downloading `wf` for selected models/years is the fallback and needs a personal NCAR
  token. Don't use the token embedded in ardac-curation's download scripts.
- HadGEM2-ES returns **null `pcp`, `tmax` and `tmin`** from `/hydrology/point`, though its
  hydrology variables are present.

**Treat everything under `/beegfs/CMIP6/cparr4/` and `/beegfs/CMIP6/NCAR_VIC/` as read-only source data.** It belongs to another
user. Open files read-only and write all outputs elsewhere. Ignore stray `*.ncks.tmp` files.

## Related repos (read through `gh api`, don't clone into source dirs)

- `ua-snap/ardac-curation`, `curation/ncar12km_decadal_summaries/`: the curation pipeline
  (`config.py`, `compute_summaries.py`, EDA and QC notebooks)
- `ua-snap/data-api`: `routes/hydrology.py`, `templates/documentation/hydrology.html`

## Environment and execution

- Use the conda env **`snap-geo`** (`/home/jdpaul3/miniconda3/envs/snap-geo`). It has xarray,
  rioxarray, geopandas, dask, matplotlib and pandoc. xelatex is at `/usr/bin/xelatex`.
- Run heavy computation as a Slurm job, never on the login node. Job scripts must activate
  `snap-geo` themselves. Pass the script to sbatch as a file and use only full option names (see
  the global CLAUDE.md). Slurm's own messages are in `~/.cache/tclaude/slurm-logs/`.
- Writable: this repo and `~/tmp`. Put small derived data (CSV/NetCDF summaries under ~100 MB)
  in `~/tmp/vic_hydro_analysis/`. Commit only scripts, small tables, figures and the report.

## Repo layout

```
vic_hydro_assessment.md   context brief from the earlier session (input)
notes/                    working notes: raw vs curated inventory, uses, options analysis
scripts/                  analysis scripts + Slurm job files
figures/                  figures for the report (PNG/PDF)
report/                   two-page summary (Markdown source + built PDF)
```

## Writing guidance

- The readers are SNAP leads: technical, but not hydrologists. Define terms like baseflow and
  BCSD in a few words.
- Be fair to all three options. "Uncalibrated" does not mean useless, and calibration does not
  make results trustworthy (Mendoza et al. 2015).
- Any number in the report must trace to a script in `scripts/` or a cited source.
