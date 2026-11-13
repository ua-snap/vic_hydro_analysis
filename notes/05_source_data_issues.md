# 05 — Data-integrity issues in the NCAR source files and SNAP's curated product

Found 2026-11-13 while running the baseflow analysis. Scripts: `scripts/check_api_vs_raw.py`,
`scripts/check_forcing_year_alignment.py`. Results: `results/provenance/`.

The source files are cparr4's copy of the NCAR files (downloaded Feb 2023),
`/beegfs/CMIP6/cparr4/AK_NCAR_12km/{vic_hydro,met}/monthly/`. NCAR's current published version
hasn't been checked; it may differ.

## 1. RCP4.5 VIC outputs don't line up with the RCP4.5 forcing (all 10 models)

The test: match each year's VIC `PRCP` field (the precipitation VIC actually used) against the
BCSD met `pcp` for every candidate year. Score is the median |difference| over 400 random land
cells × 11 months. An exact match is about 0.01 mm.

| VIC output years | RCP8.5 (all 10 models) | RCP4.5 (all 10 models) |
|---|---|---|
| 1950–1978 | same year, exact | **no matching forcing year** (best ~10 mm/month) |
| 1979 | same year, exact | no match |
| 1980–2000 | same year, exact | **met year − 30, exact** (VIC 1980 ↔ forcing 1950) |
| 2001–2099 | same year, exact | same year, exact (except CanESM2, below) |

**CanESM2 RCP4.5 has an extra problem:**
- 2026–2049: no exact match (4–8 mm/month).
- 2050: no match.
- **2051–2099: met year − 25, exact.** The late-century RCP4.5 hydrology for CanESM2 was driven by
  2026–2074 forcing.

From these files alone we can't tell whether the VIC outputs or the met files are mislabeled. The
VIC outputs have break years (1979, 2050) that match nothing, which suggests a problem with how
the VIC output segments were assembled. **Raise with NCAR (Mizukami/Newman) and check against
NCAR's current published files.**

Also: NCAR's raw RCP4.5 and RCP8.5 *met* forcing differ in historical years (e.g. Fairbanks
ACCESS1-3 1950s: 313 vs 382 mm/yr). The GCM historical period is the same for both RCPs, so this
suggests BCSD was run separately per scenario. That's not necessarily an error, but it means
"historical" differs by scenario.

## 2. What SNAP serves (/hydrology), traced to the raw runs

Comparison: API decadal sums vs raw sums at 5 points × 10 models × 15 decades. Tolerance
covers whole-mm rounding. The "neither" rate is 20–45% throughout, from rounding and grid
mismatch (the API grid is reprojected to EPSG:3338).

| Served | Historical decades (1950–2009) | Future decades (2010–2099) |
|---|---|---|
| `runoff` labelled RCP8.5 | RCP8.5 run | RCP8.5 run |
| `runoff` labelled **RCP4.5** | **RCP8.5 run** (145 rcp85 vs 25 rcp45 matches) | RCP4.5 run |
| `pcp` labelled RCP8.5 | RCP8.5 met | RCP8.5 met |
| `pcp` labelled **RCP4.5** | **RCP4.5 met**, which drove neither served hydrology series | RCP4.5 met |

So for RCP4.5 historical decades, SNAP serves RCP8.5-run hydrology alongside RCP4.5 met forcing.
Using the RCP8.5 historical hydrology may have been a deliberate workaround for problem 1; it's
undocumented either way. The served `pcp`/`tmax`/`tmin` therefore **don't correspond to the
served hydrology** for RCP4.5 1950–2009. For CanESM2 RCP4.5 2050s–2090s, the served hydrology
comes from mid-century forcing.

## 3. Other issues

- **HadGEM2-ES `pcp`/`tmax`/`tmin` are null in the API.** Its met files exist on disk (150 per
  scenario, standard calendar, valid values), so this is a curation or ingest gap.
- **GLACIER_MELT is implausible as a cell-average flux** (median 19–53 m/yr in glacier cells vs a
  cell ice-loss residual of 0.7–1.7 m/yr). It's served as `glacier_melt`.
- `/beegfs/CMIP6/NCAR_VIC/NCAR_NetCDF/` is a reprojected extract (EPSG:3338, EVAP/RUNOFF/SM1
  only), not source data.
- The met monthly files store `pcp` as a mean daily rate (mm/day), while the wf monthly files
  store monthly totals (mm/month).

## Implications

- **Analyses here use RCP8.5** for change statistics. The RCP4.5 baselines are unreliable.
- **Option A (keep as is) is weaker than the first draft said:** the served product has
  undocumented scenario mixing, a model with missing forcing, and a questionable glacier-melt
  variable.
- **Option C must include QC:**
  - Use one consistent historical run for both scenarios, and serve the matching forcing with it.
  - Exclude or flag CanESM2 RCP4.5 after 2025 until NCAR confirms.
  - Fix the HadGEM2-ES met gap.
  - Resolve or drop `glacier_melt`.
- **Option B gains weight** if NCAR can't confirm or correct the RCP4.5 runs.
