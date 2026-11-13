---
title: "VIC-Hydro: what we have and what to do with it"
subtitle: "SNAP internal brief · DRAFT 2026-11-13 · baseflow numbers pending"
geometry: "margin=0.6in"
fontsize: 10pt
mainfont: "Liberation Sans"
monofont: "DejaVu Sans Mono"
---

**Bottom line.** The variable hydrologists care about most, `runoff`, is VIC-Hydro's weakest. It is **surface runoff only** (baseflow was dropped during curation), and it's reported
for **single 12 km grid cells**. For the engineers and hydrologists asking, that's the wrong
variable at the wrong scale. Three of the 12 variables (`tmax`, `tmin`, `pcp`) duplicate newer
SNAP products. Streamflow questions are better answered by our RASM-based `/arctic_hydrology`
service. Even so, VIC-Hydro is SNAP's **only** projection of snow water equivalent (SWE),
evapotranspiration, soil moisture, snowmelt and glacier melt, and our only end-of-century,
multi-model hydrology ensemble for Alaska. **Recommendation: Option C (reprocess)**, scoped
tightly, with a planned sunset once CMIP6-based snow and hydrology products are available.

# 1. What it is (raw NCAR data)

Mizukami et al. (2022, NCAR) ran the **VIC land-surface model** (with a simple glacier model) for
1950–2099 on a 12 km Alaska grid of 14,227 cells. The runs were forced by **10 CMIP5 climate
models × 2 scenarios (RCP4.5, RCP8.5)**, statistically downscaled with BCSD against Daymet. A
separate run forced by Daymet observations covers 1980–2016. Output is **daily** for about 20
water- and energy-balance variables, including surface runoff *and* baseflow (the slow
groundwater contribution that sustains winter and late-summer flow). **There is no river routing,
so there is no streamflow.** Soil parameters come from transfer functions calibrated on CONUS
basins, so the model is *regionally parameterized but not calibrated in Alaska*. That's a real
limitation, but calibration alone doesn't make projected changes trustworthy (Mendoza et al.,
2015), so it doesn't by itself make the data useless. The VIC run can't be redone; every option
below works from the existing outputs.

# 2. What we have (SNAP curated product)

We serve 12 variables (`evap, glacier_melt, iwe, pcp, runoff, sm1–3, snow_melt, swe, tmax, tmin`)
as **decadal averages of monthly totals, means or maxima**, rounded to whole millimeters, for each
model, scenario, month and decade. Access is by **point query only** (one 12 km cell per request)
through the data-api, earthmaps.io and Arctic-EDS. Arctic-EDS shows only `evap` and `runoff`.
**Not served:** baseflow or total runoff, the Daymet historical run, change-from-baseline values,
multi-model summaries, and any watershed or area summaries.

# 3. What it can be used for

| Use | Raw NCAR data | SNAP curated product |
|:--------------------------------------|:-------------------------|:----------------------------|
| Watershed water yield and its projected change | **Yes** (surface runoff + baseflow, summed over a watershed) | **No**: surface runoff only, per cell, no area query |
| Streamflow / hydrographs at a river point | Only after routing (not done) | **No** (use `/arctic_hydrology`) |
| Snowpack (SWE) and snowmelt timing | **Yes**, daily | **Partly**: monthly peak SWE, monthly melt totals |
| Evapotranspiration, soil-moisture anomalies | **Yes**, best as relative change | **Partly**: per cell, no baseline or change values |
| Glacier-melt contribution | **Yes** (1,913 glacier cells) | **Partly**: per cell |
| Range across climate models | **Yes** (10 models × 2 scenarios) | **Partly**: no multi-model summary |
| Temperature and precipitation | Yes | **Redundant** with `/cmip6_downscaled`, `/era5wrf`, `/taspr` |
| Daily extremes, design floods, low flows | **No** (BCSD downscaling handles extremes poorly; model not calibrated) | **No** |

![**One grid cell vs. one watershed.** A typical Alaska HUC8 watershed (median 10,100 km²)
covers about 70 VIC grid cells. Flow at its outlet integrates runoff from all of them, so no
single cell value represents it. Watershed polygons come from earthmaps.io
`/boundary`.](../figures/fig1_cell_vs_watershed.pdf){width=86%}

**Pending check: how much runoff is missing.** *[PENDING: baseflow share of total runoff,
statewide and by HUC8, annual and winter (Nov–Apr); and whether projected change in surface
runoff tracks change in total runoff. Waiting on read access to the raw NCAR files.]* In VIC,
baseflow typically carries most cold-season flow, so the served `runoff` very likely understates water yield
and gives a misleading seasonal pattern.

\newpage

# 4. Options

| | **A. Keep as is** | **B. Remove entirely** | **C. Reprocess** (re-curate + aggregate by watershed) |
|:---------|:--------------------|:----------------------|:----------------------------------------|
| **What** | No changes. | Retire the Rasdaman coverage, the `/hydrology` route and the Arctic-EDS section. Point users to the NCAR source and `/arctic_hydrology`. | Add `baseflow` and `total_runoff` (summed daily, before rounding). Add change from a historical baseline (including the Daymet run) and multi-model median, range and sign agreement. Serve **HUC8/HUC10 averages** keyed to existing `/places` IDs. Drop `tmax`, `tmin` and `pcp`. |
| **Pros** | No cost. Nothing breaks. Keeps our only SWE until the CMIP6 and WRF-ERA5 snow products ship. | Removes a product experts say invites misuse. Less to maintain. Sends streamflow users to the better tool. | Fixes the critique (wrong variable, wrong scale). Keeps unique variables and the 10-model, end-of-century range, which complements RASM (one model family, mid-century only). Change plus model agreement is the defensible way to present uncalibrated output. Reuses the existing pipeline and HUC IDs. |
| **Cons** | The critique stands. `runoff` invites misreading as total runoff. Redundant variables stay. No change or uncertainty framing. | Loses SWE, ET, soil-moisture and glacier-melt projections, leaving a gap until CMIP6 snow ships. Breaks existing clients. | Staff time across curation, Rasdaman, API and front ends. Still CMIP5/BCSD and uncalibrated: better presentation, not better skill. Watershed averages are not routed streamflow. |
| **Effort** | None | Low | Moderate |

# 5. Recommendation and next steps

**Go with Option C, scoped to these steps, and plan to retire the product later.**

1. **Now (small):** relabel `runoff` as "surface runoff (excludes baseflow)" everywhere it's
   shown. Add a short fitness-for-use note (not calibrated in Alaska; use relative change and
   model agreement, not absolute values; BCSD is unsuitable for extremes) and a link to
   `/arctic_hydrology` for streamflow.
2. **Reprocess (moderate):** add total runoff, change from baseline, multi-model statistics, and
   HUC8/HUC10 summaries. Drop the redundant temperature and precipitation variables.
3. **Retire later:** once CMIP6 snow and a CMIP6-forced hydrology product cover SWE and runoff,
   deprecate VIC-Hydro in stages.

Option B is reasonable only if we can't fund step 2. If so, do step 1 now and remove the product
when the CMIP6 snow data ships. The pending baseflow numbers will show how big the runoff problem
is. They would change this recommendation only if baseflow turns out to be negligible, which is
not expected.

\vspace{-0.3em}
\footnotesize
**Sources:** Mizukami et al. 2022, doi:10.5065/c3kn-2y77 and *Climate Services* 27:100312.
Mendoza et al. 2015, *J. Hydrometeor.*, doi:10.1175/JHM-D-14-0104.1. Blaskey et al. 2024, doi:10.18739/A25M62870.
Curation code: `ua-snap/ardac-curation` (`ncar12km_decadal_summaries`). API: `ua-snap/data-api`.
Analysis: this repo (`vic_hydro_analysis`).
