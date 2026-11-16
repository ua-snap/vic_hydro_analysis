# Independent verification of the VIC-Hydro assessment

You are reviewing someone else's analysis. The repo's `CLAUDE.md` (project purpose, sandbox rules,
read-only data, Slurm, conda env) still applies; read it first. This file adds the review task.

## Goal

Decide whether the findings in `report/vic_hydro_summary.pdf` are **defensible**. Check each
factual or quantitative claim on its own: reproduce it from the data we already hold, test the
patterns it implies with spot checks, and dig further wherever something looks wrong. You don't
need to verify every digit, but every claim that drives the recommendation needs a clear verdict.

The output is a **one-page PDF** verification summary. If you find major problems, it can run
longer; give each major problem the space it needs.

## Ground rules

1. **No re-downloading.** Everything you need is already on disk (see "Data" below). Don't fetch
   VIC or met files from NCAR, GDEX or OSDF. Reading GitHub repos with `gh api` and making a few
   point queries to the public SNAP data API (`https://earthmaps.io`) are fine.
2. **Be independent.** For each headline number, write **your own code** from the data files,
   using the method the report describes. Don't import, copy or re-run the original analysis
   scripts in `scripts/` for that first pass: re-running the same code would repeat its bugs.
   Once you have your own number, read the original script to explain any difference. Use the
   original's result CSVs in `results/` only for comparison.
3. **Don't change the original work.** Leave `report/`, `notes/`, `scripts/`, `results/` and
   `figures/` as they are. All of your output goes under `review/` (see "Deliverables").
4. **Data are read-only.** Open NetCDF files read-only; write nothing next to them. Treat
   `/beegfs/CMIP6/cparr4/`, `/beegfs/CMIP6/NCAR_VIC/` and `/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/`
   as source data.
5. **Compute in Slurm.** Opening a few files on the login node to inspect them is fine. Anything
   that loops over many files goes into a Slurm job (`--account=cmip6 --partition=t1small`; see
   `scripts/run_published_checks.slurm` for a working template). Job scripts must activate
   `snap-geo` themselves. Pass the script to sbatch as a file and use full option names only.
6. **Don't commit or push.** Leave your files uncommitted for the user to review.
7. **The repo is public.** Don't put email addresses, correspondence or personal details in
   anything you write.

## Step 1: read and inventory

1. Read `report/vic_hydro_summary.pdf` (its source is `report/vic_hydro_summary.md`). This is
   the document under review.
2. Read the supporting material: `notes/01`–`05`, `vic_hydro_assessment.md`, and the headers of
   each script in `scripts/`.
3. Locate and list every file you'll work with. Confirm the paths below exist and match the
   descriptions, and note any that don't. Put this inventory in your working notes.

### Data

| What | Path | Notes |
|---|---|---|
| **Published NCAR release (GDEX d010111), monthly.** This is the primary dataset. | `/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/{vic,met}/monthly/{BCSD/<model>/<rcp>,daymet}/` | ~3,037 files each for vic and met. `manifest.csv` + `download-744118.log` record MD5s. The report's numbers come from these files. |
| Published release, daily spot files | `/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/daily_spot/` | ACCESS1-3 1985 wf/met (RCP4.5, RCP8.5 met). The CCSM4 2050 file is only 2 KB; check whether it is truncated. |
| Published release, daily CanESM2 RCP4.5 2060 | `~/tmp/vic_hydro_analysis/gdex_dl/daily/` | wf and met |
| Preliminary NCAR release (older, **not** what SNAP served) | `/beegfs/CMIP6/cparr4/AK_NCAR_12km/{vic_hydro,met}/{daily,monthly}/` | For the release-comparison claims only |
| Cached SNAP API responses | `~/tmp/vic_hydro_analysis/precip_cmp/cache/` | `vic_<point>.json` = `/hydrology/point` for Fairbanks, Palmer, Juneau, Bethel (check what else is there) |
| HUC8 polygons | `~/tmp/vic_hydro_analysis/boundaries/huc8.gpkg` | From earthmaps.io `/places/hucs` |
| Curation grid | `~/tmp/vic_hydro_analysis/grid/alaska_grid_12km_production.nc` | |
| NCAR paper and README (text) | `~/tmp/vic_hydro_analysis/ncar_docs/{paper,readme}.{pdf,txt}` | For desk-review claims |
| Original results | `results/published/*.csv` (current), `results/baseflow/`, `results/provenance/` (preliminary release; superseded) | Compare against, don't reuse |
| Original job logs | `~/tmp/vic_hydro_analysis/published/*.log` | |
| Curation and API code | `gh api repos/ua-snap/ardac-curation/...`, `gh api repos/ua-snap/data-api/...` | `curation/ncar12km_decadal_summaries/`, `routes/hydrology.py` |

Put your intermediate data in `~/tmp/vic_hydro_analysis/verify/`.

## Step 2: build the claim list

List every checkable claim in the report as a numbered table (claim, report section, how you'll
check it, priority). Start from the list below and **add whatever it misses**. Also check that
the report agrees with its own notes and result CSVs: a number that differs between
`report/vic_hydro_summary.md`, `notes/04`/`05` and `results/published/*.csv` is itself a finding.

**High priority (they drive the recommendation):**

- H1. The served `runoff` is surface runoff only; curation dropped `BASEFLOW` (check the
  ardac-curation `config.py` and confirm with the API cache against the raw files).
- H2. Outside glacier cells, baseflow is **48–50%** of total runoff (1980–2009, per GCM), and
  **52–56%** in Nov–Apr. Baseflow carries most of the late-summer and winter flow (Fig. 2a).
- H3. Median baseflow share over **149** Alaska HUC8s is **38%** (range **4–68%**).
- H4. RCP8.5, 1980–2009 → 2070–2099, domain-wide: surface runoff **−17%**, baseflow **+63%**,
  total **+9%** (10-model mean; Fig. 2b).
- H5. Median HUC8: surface **+32%** vs total **+51%**. **22 of 149** HUC8s change in opposite
  directions.
- H6. For RCP4.5, the VIC hydrology for 1950–2000 (CanESM2: 1950–2005) is identical to the RCP8.5
  run, while the RCP4.5 met files hold different `pcp`/`tmax`/`tmin` for those years. From 2001
  (CanESM2: 2006), RCP4.5 VIC matches RCP4.5 met. All 10 models show this (Fig. 2c).
- H7. The SNAP API serves the RCP4.5 met (not the forcing that drove the hydrology) alongside the
  shared historical hydrology.
- H8. `glacier_melt` is implausibly large as a cell average. The report says **20–40 m/yr** in
  glacier cells; `notes/04` says 19–53 m/yr against an ice-loss residual of about 0.7–1.7 m/yr.

**Medium priority:**

- M1. Domain: 14,250 VIC cells, 1,912 glacier cells (`GLACIER_MELT > 0` in any run). `notes/01`
  says 14,227 land cells. Reconcile.
- M2. Non-glacier cells close the water balance: P − ET − RO − BF ≈ 0 (mean within ±3.5 mm/yr).
- M3. API `runoff` equals raw RUNOFF rounded to whole mm (Fairbanks), and API values come from
  the published release. Spot-check a second point.
- M4. HadGEM2-ES `pcp`/`tmax`/`tmin` are null in the API because NCAR's 2005 met files lack
  December. Check the published files directly.
- M5. Median Alaska HUC8 is ~**10,100 km²** and covers ~**70** VIC cells (Fig. 1).
- M6. SNAP's other precipitation products are **20–40% wetter** than VIC forcing at the test
  points (`results/precip_source_comparison.csv`; check the arithmetic and whether "20–40%"
  fairly summarizes it).
- M7. The Daymet-forced run covers 1980–2016 (`CLAUDE.md` says 1980–2017). Count the files.
- M8. The published release fixed the preliminary release's RCP4.5 year offsets, and its CanESM2
  RCP4.5 2060 daily file matches the Feb 2023 checksums.

**Desk-review claims:**

- D1. The paper calls the parameters "essentially uncalibrated" (search `paper.txt`).
- D2. Paper facts: VIC 4.2.glacier, 1950–2099, 10 CMIP5 GCMs × RCP4.5/8.5, BCSD against Daymet,
  12 km, no routing.
- D3. Section 2 API facts: 12 variables, decadal means of monthly summaries, rounded to whole mm,
  point query only, `?summarize=mmm` is across decades, Arctic-EDS labels surface runoff "Runoff".
- D4. `/arctic_hydrology` is RASM-based streamflow (Blaskey et al. 2024); `/cmip6` serves SWE.
  Check the endpoint names in `ua-snap/data-api`.
- D5. The citations' DOIs resolve to the papers named.

## Step 3: reproduce, then spot-check

For each claim, record your number, the report's number and a verdict:

- **Reproduced:** matches to the report's stated precision (e.g. ±1 percentage point, exact
  counts).
- **Reproduced with differences:** close, or the conclusion holds but a figure is off. Say how
  much and why.
- **Not reproduced:** your result contradicts the claim. Investigate before finalizing (see below).
- **Not checked:** say why.

Then test the **patterns** behind the headline numbers, not only the numbers. Suggested spot
checks, which you can change or add to:

- **Baseflow share.** Pick a few random non-glacier cells in different regions (Interior, North
  Slope, Southcentral, Southeast, Y-K Delta). Is the monthly surface/baseflow split
  hydrologically sensible (baseflow dominant in winter, surface dominant at freshet)?
- **Sensitivity.** Do H2–H5 survive (a) equal-area vs map-factor weighting, (b) a different
  glacier-cell mask (e.g. a threshold on mean GLACIER_MELT, or glacier cells included), and
  (c) assigning cells to HUC8s by centroid vs area-weighted overlap? A finding that flips under
  a reasonable alternative isn't defensible as stated.
- **Opposite-sign HUC8s.** Pick 2–3 of the 22, recompute them from scratch, and check that the
  sign split isn't an artifact of near-zero changes. How many of the 22 have |Δ| < 5%?
- **Shared historical run (H6).** Use models and years **other than** ACCESS1-3 1985 (the
  original showcase): e.g. MIROC5 1965, GFDL-ESM2M 1999 vs 2001, CanESM2 2005 vs 2006. Compare
  RCP4.5 vs RCP8.5 VIC fields for several variables (not only PRCP and RUNOFF: also SWE, EVAP,
  BASEFLOW) and confirm the switch-over years.
- **glacier_melt (H8).** Read the variable's units and attributes in the files and the NCAR
  README/paper. Is there a documented reason (e.g. per glacier area, not per cell)? Compare
  GLACIER_MELT with the cell's water balance in a few glacier cells. Check that the report's
  "20–40 m/yr" is a fair statement of what you find.
- **Units.** Monthly wf files hold mm/month totals and met `pcp` holds mm/day means (per
  `notes/05`). Confirm from the file metadata. A units slip here would undermine H6 and M2.
- **Time periods.** Make sure "1980–2009" and "2070–2099" select exactly 30 years in every run,
  with no missing or duplicate years (check HadGEM2-ES, which ends its historical run in Nov 2005).

**If something looks wrong, investigate before reporting it.** Find the cause (your code, the
original code, the data or the wording), decide whether it changes a conclusion, and, if it's
cheap, say what the corrected number is. Separate "the number is slightly off" from "the
conclusion is wrong".

## Deliverables (all under `review/`)

- `review/scripts/`: your verification scripts and Slurm files. Every number in your summary
  must trace to one of them, to an original result CSV you compared against, or to a cited source.
- `review/results/`: small CSVs of your computed values (well under 100 MB in total).
- `review/notes.md`: working notes: the file inventory, the full claim table with your numbers
  and the report's, spot-check results and investigation details. This can be as long as it
  needs to be.
- `review/verification_summary.md` and `review/verification_summary.pdf`: the summary for the
  user. Build it the same way as the report:

  ```sh
  cd review
  pandoc verification_summary.md --template=../report/brief-template.tex --pdf-engine=xelatex \
    --resource-path=.:.. -o verification_summary.pdf
  ```

  Check the page count with `pdfinfo` and look at the rendered PDF before you finish.

### Summary format (one page unless there are major issues)

1. **Verdict** (2–3 sentences): are the findings defensible as written, defensible with
   corrections, or not defensible? Does the recommendation (Option C) still follow?
2. **Claim table**: one row per claim (merge minor ones): report value · our value · verdict.
3. **Issues found**, most serious first, each with severity (major / minor / wording), evidence
   and the suggested fix to the report's text.
4. **What wasn't checked**, and why (one or two lines).

Write for the same readers as the report: technical, but not hydrologists. Keep it tight. A
figure is optional and only worth including if it shows a problem more clearly than a sentence.

## Finishing

When you're done, tell the user: the overall verdict, the major issues (if any), where the PDF is
and any Slurm jobs that are still running or failed. Don't edit the original report. The user
decides what to change.
