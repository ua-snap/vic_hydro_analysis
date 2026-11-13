# 05 — Data-integrity issues in the NCAR source files and SNAP's curated product

Found 2026-11-13 while running the baseflow analysis. Scripts: `scripts/check_api_vs_raw.py`,
`scripts/check_forcing_year_alignment.py`. Results: `results/provenance/`.

## 0. Which NCAR release? (read this first)

- **The beegfs files are NCAR's *preliminary* release, not what SNAP curated.**
  - Files in `/beegfs/CMIP6/cparr4/AK_NCAR_12km/` say Mizukami created them 2020-11-23
    (`txt2nc_vic_wf.py`), and they were converted with `ncks -4` on 2021-04-29.
  - The directories date from July 2022.
- **The curation used `/atlas_scratch/cparr4/ncar_replacement_data`.** It was downloaded from the
  NCAR gateway in Feb 2023 (`download_scripts/wget-*-20230224/20230228`). The EDA notebook says
  "replacement" means "distinct from the preliminary data we already had on disk… basically a
  mirror of what NCAR is serving". Atlas is gone, but that release can be re-downloaded from NCAR.
- **There's no year-relabeling bug in the curation code.** `run_*_vars.ipynb` glob the files
  unsorted, but `compute_summaries.slice_by_decade` selects decades by each file's internal
  `time` coordinate. Nothing in the repo renames, converts or re-times source files.
- **So problem 1 below belongs to the preliminary release.** The API suggests the published
  release fixed it. For CanESM2 RCP4.5 in the 2050s, 2070s and 2080s, the API values match
  neither beegfs scenario, while earlier decades match.
- **RCP8.5 looks unchanged between releases:** the API matches beegfs RCP8.5 in most decades.
  The RCP8.5 baseflow results in notes/04 should therefore hold for the published data.
- **Confirmed for CanESM2 RCP4.5 2060** using the published release from NCAR GDEX (`d010111`,
  anonymous download; MD5 identical to the Feb 2023 wget checksums).
  - Published VIC PRCP equals published met pcp: identical annual totals, r = 1.000.
  - The preliminary file's PRCP differs by a median of 129 mm/yr.
  - The published file was regenerated 2021-05-08 by `txt2nc_vic_wf_CanESM2.py`.
  - The full re-check on published monthly files (~50 GB) is pending.

## 1. RCP4.5 VIC outputs don't line up with the RCP4.5 forcing (all 10 models) — PRELIMINARY RELEASE

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

With section 0 in mind: the published release appears to use **one shared historical VIC run for
both scenarios**, which equals the preliminary RCP8.5 run. Its **met files are still
scenario-specific in the historical period**: the API's RCP4.5 `pcp` matches the preliminary
RCP4.5 met, so met looks unchanged between releases. The curation passes both through as they
are. For RCP4.5 historical decades, then, the served `pcp`/`tmax`/`tmin` (RCP4.5 met) **probably
don't correspond to the served hydrology** (shared run, RCP8.5 forcing). This is inferred from
API values with rounding and grid mismatch; confirm with published files.

Problem 1's year offsets, including CanESM2 RCP4.5 late century, appear to have been fixed in
the published release (section 0).

## 3. Other issues

- **HadGEM2-ES `pcp`/`tmax`/`tmin` are null in the API by design.**
  - `run_met_vars.ipynb` does `models.remove("HadGEM2-ES")`.
  - The EDA notebook found that the published `HadGEM2-ES_rcp{45,85}_BCSD_met_2005.nc` files are
    missing December (334 days) and set the model aside, with "contact NCAR eventually".
  - Likely cause: HadGEM2-ES's CMIP5 historical experiment ends in Nov 2005.
  - It's documented in the EDA notebook but not in the API docs. In a reprocess, the other 149
    years per scenario could be served and the 2000s decade flagged.
- **GLACIER_MELT is implausible as a cell-average flux** (median 19–53 m/yr in glacier cells vs a
  cell ice-loss residual of 0.7–1.7 m/yr). It's served as `glacier_melt`.
- `/beegfs/CMIP6/NCAR_VIC/NCAR_NetCDF/` is a reprojected extract (EPSG:3338, EVAP/RUNOFF/SM1
  only), not source data.
- The met monthly files store `pcp` as a mean daily rate (mm/day), while the wf monthly files
  store monthly totals (mm/month).

## Implications

- **Our analyses use the preliminary release.** RCP8.5 results should carry over; RCP4.5 results
  shouldn't be used. Re-run on the published release before quoting RCP4.5 numbers.
- **The served product has no evidence of a year-shift bug.** The curation code is sound in that
  respect.
- **Remaining served-product issues:**
  - The RCP4.5 historical met probably doesn't match the shared historical hydrology.
  - HadGEM2-ES met is excluded, which isn't documented in the API.
  - `glacier_melt` is questionable (check against the published files).
- **Option C QC list:**
  - Serve the forcing that drove the historical run for both scenarios.
  - Restore HadGEM2-ES met with a flag on the 2000s.
  - Resolve or drop `glacier_melt`.
  - Confirm against the published release.
