---
title: "VIC-Hydro: what we have and what to do with it"
subtitle: "SNAP internal brief · DRAFT 2026-11-13"
geometry: "margin=0.55in"
fontsize: 10pt
mainfont: "Liberation Sans"
monofont: "DejaVu Sans Mono"
---

**Bottom line.** The variable hydrologists care about most, `runoff`, is VIC-Hydro's weakest. It
is **surface runoff only** (curation dropped baseflow, about **half of total runoff** outside
glaciers), reported for **single 12 km grid cells**, and its projected change can point the
opposite way from total runoff. We also found **data-consistency problems** in what we serve
(section 3). Streamflow questions are better answered by our RASM-based `/arctic_hydrology`, and
temperature, precipitation and SWE exist in newer SNAP products. Still, VIC-Hydro is our **only**
projection of evapotranspiration, soil moisture, snowmelt and glacier melt.

# 1. What it is (raw NCAR data)

Mizukami et al. (2022, NCAR) ran the **VIC land-surface model** (with a simple glacier model) for
1950–2099 on a 12 km Alaska grid, driven by **10 CMIP5 climate models × 2 scenarios (RCP4.5,
RCP8.5)** downscaled with BCSD against Daymet, plus a Daymet-forced run for 1980–2016. Output is
**daily** for about 20 variables, including surface runoff *and* baseflow (slow groundwater flow
that sustains winter and late-summer streamflow). **There is no river routing, so no
streamflow.** The authors call the parameters "essentially uncalibrated" (transferred from CONUS,
not calibrated in Alaska). That's a real limitation, but calibration alone doesn't make projected
changes trustworthy (Mendoza et al., 2015). The run can't be redone; all options in this document
use existing outputs.

# 2. What we have (SNAP curated product)

We serve 12 variables (`evap, glacier_melt, iwe, pcp, runoff, sm1–3, snow_melt, swe, tmax, tmin`)
as **decadal averages of monthly totals, means or maxima**, rounded to whole mm, per model,
scenario, month and decade, by **point query only** (one 12 km cell) through the data-api,
earthmaps.io and Arctic-EDS. Arctic-EDS labels surface runoff simply "Runoff". **Not served:**
baseflow or total runoff, the Daymet run, deltas, multi-model summaries, watershed summaries.

| Use | Raw NCAR data | SNAP curated product |
|:----------------------------------------|:----------------------------|:------------------------------------|
| Watershed water yield and its change | **Yes** (sum runoff + baseflow) | **No**: surface runoff, per cell |
| Streamflow / hydrographs | Only after routing | **No** (use `/arctic_hydrology`) |
| Snowpack (SWE), snowmelt timing | **Yes**, daily | **Partly**: monthly; SWE also in `/cmip6` |
| Evapotranspiration, soil moisture | **Yes**, as relative change | **Partly**: per cell, no deltas |
| Range across climate models | **Yes**, 10 GCMs × 2 RCPs | **Partly**: no multi-model summary |
| Temperature and precipitation (VIC forcing) | **Yes** | **Yes** |
| Daily extremes, design floods, low flows | **No** (BCSD limits) | **No** |

![**One grid cell vs. one watershed.** A typical Alaska HUC8 watershed (median 10,100 km²)
covers about 70 VIC grid cells.](../figures/fig1_cell_vs_watershed.pdf){width=64%}

# 3. What our checks on NCAR's published files show

NCAR GDEX d010111 (checksum-verified); 1980–2009 vs 2070–2099; 10 climate models.

- **We're missing baseflow, about half of runoff** (Fig. 2a). Outside glacier cells it's
  **48–50%** of total runoff (52–56% in Nov–Apr), and it carries most of the late-summer and winter
  flow. The median across 149 Alaska HUC8 watersheds is 38% (range 4–68%).
- **The served variable misstates change** (Fig. 2b). Under RCP8.5, domain-wide surface runoff falls
  **17%**, while baseflow rises 63% and total runoff **rises 9%**. In the median HUC8, surface
  runoff rises 32% but total runoff rises 51%. **22 of 149 HUC8s** change in opposite directions.
- **For RCP4.5 before 2001, the precipitation and temperature we serve didn't drive the hydrology
  we serve** (Fig. 2c). In NCAR's files, the RCP4.5 hydrology for 1950–2000 (CanESM2: 1950–2005) is a copy
  of the RCP8.5 run. The RCP4.5 met files hold different precipitation and temperature for those
  years. We serve both side by side, so for those years `pcp`/`tmax`/`tmin` aren't the inputs
  behind the runoff, ET and snow shown with them. We've drafted an inquiry to NCAR.
- **Other quality issues.** HadGEM2-ES `pcp`/`tmax`/`tmin` are missing from the API without
  explanation: curation excluded them because NCAR's 2005 files lack December. And `glacier_melt`
  values (20–40 m/yr in glacier cells) are too large to be grid-cell averages.

![**What we serve leaves out half the water, misstates its change, and mixes runs.**
(a) Monthly surface runoff and baseflow, non-glacier land cells, 1980–2009, 10-model mean.
(b) RCP8.5 change, 1980–2009 to 2070–2099, domain-wide; bars are the 10-model mean, dots are
single models. (c) Difference between the RCP4.5 and RCP8.5 files for one model (ACCESS1-3),
averaged over land cells; zero means identical. All 10 models show the same
pattern.](../figures/fig2_section3_issues.pdf){width=100%}

# 4. Options

| | **A. Keep as is** | **B. Remove entirely** | **C. Reprocess** (re-curate + aggregate by watershed) |
|:---------|:--------------------|:----------------------|:-------------------------------------------|
| **What** | No changes. | Retire the coverage, `/hydrology` route and Arctic-EDS section. Point users to NCAR and `/arctic_hydrology`. | Add `baseflow` and `total_runoff` (from daily data), change from baseline (incl. the Daymet run), and multi-model median, range and sign agreement. Serve **HUC8/HUC10 summaries** via existing `/places` IDs: runoff terms as area-weighted depth (mm) *and* volume/mean flow (local water, not routed outlet flow), other variables as area-weighted means. Keep `tmax`/`tmin`/`pcp` as labeled **VIC forcing**, paired with the run that drove each scenario. Our other precipitation products are 20–40% wetter at test points, so pairing them with VIC breaks the water balance. Fix the section 3 issues. |
| **Pros** | No cost. Nothing breaks. Keeps our only 12 km SWE until downscaled CMIP6 snow ships. | Removes a product experts say invites misuse, along with its data issues. Less to maintain. | Fixes the critique (wrong variable, wrong scale) and the data issues. Keeps unique variables and the 10-model end-of-century range, which complements RASM (one model family, mid-century). Change plus model agreement is the defensible use of uncalibrated output. |
| **Cons** | The critique stands. `runoff` omits half the water and can show the wrong direction of change. Data issues stay undocumented. | Loses ET, soil-moisture, snowmelt and glacier-melt projections and 12 km SWE. | Staff time (curation, Rasdaman, API, front ends). Still CMIP5/BCSD and uncalibrated: better presentation, not better skill. Not routed streamflow. |
| **Effort** | None | Low | Moderate |

\newpage

# 5. Recommendation and next steps

**Go with Option C, scoped to these steps, and plan to retire the product later.**

1. **Now (small):** relabel `runoff` as "surface runoff (excludes baseflow)". Add a fitness-for-use
   note: uncalibrated; use relative change and model agreement; not for extremes; RCP4.5 met
   before 2001 didn't drive the RCP4.5 hydrology; HadGEM2-ES met excluded; `glacier_melt` under
   review. Link `/arctic_hydrology` for streamflow. Send the NCAR inquiry.
2. **Reprocess (moderate):** add total runoff, deltas, multi-model statistics and HUC8/HUC10
   summaries. Serve each run's actual forcing. Resolve or drop `glacier_melt`.
3. **Retire later,** in stages, once downscaled CMIP6 snow and CMIP6-forced hydrology cover SWE
   and runoff.

If step 2 can't be funded, do step 1 now and choose Option B when downscaled CMIP6 snow ships.
Future work: check the Daymet run against USGS gauges and SNOTEL; route runoff (e.g. mizuRoute)
if streamflow is needed.

\vspace{-0.3em}
\footnotesize
**Sources:** Mizukami et al. 2022, doi:10.5065/c3kn-2y77 and *Climate Services* 27:100312.
Mendoza et al. 2015, doi:10.1175/JHM-D-14-0104.1. Blaskey et al. 2024, doi:10.18739/A25M62870.
Code: `ua-snap/ardac-curation`, `ua-snap/data-api`. Analysis: `vic_hydro_analysis` repo.
