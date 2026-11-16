# Verification notes: VIC-Hydro assessment

Independent check of `report/vic_hydro_summary.pdf` (draft 2026-11-13), done 2026-11-16 on Chinook.
All code under `review/scripts/`, all computed tables under `review/results/`, intermediate data in
`~/tmp/vic_hydro_analysis/verify/` (climatologies, alignment tables, job logs). The original
`scripts/`, `results/`, `notes/`, `figures/` and `report/` were not modified. Nothing was committed.

## 1. File inventory

| Item | Path | Status |
|---|---|---|
| Report under review | `report/vic_hydro_summary.{md,pdf}` | PDF is **3 pages** (letter), not two; page 3 holds the recommendation |
| Supporting notes | `notes/01`–`05`, `vic_hydro_assessment.md`, `scripts/*.py` headers | read |
| Published NCAR release, monthly (GDEX d010111) | `/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/{vic,met}/monthly/` | 3,037 files each (10 GCMs × 2 RCPs × 150 years + 37 Daymet years 1980–2016); `manifest.csv` 6,074 downloaded, 2 optional 404s (Daymet 2017); no `.part` files |
| Published daily spot files | `.../vic_hydro_gdex/daily_spot/` | 4 files, 45–47 MB each. `CCSM4_rcp85_BCSD_wf_2050.nc` is **46 MB and opens normally** (365 days), not 2 KB as the instructions suggested |
| Published daily CanESM2 RCP4.5 2060 | `~/tmp/vic_hydro_analysis/gdex_dl/daily/` | wf + met; MD5s `ba30feaf…` / `c32d2746…` equal the Feb 2023 wget checksums |
| Preliminary release | `/beegfs/CMIP6/cparr4/AK_NCAR_12km/{vic_hydro,met}/monthly/` | readable; monthly met `pcp` has no units attribute (treated as mm/day, verified by the RCP8.5 match) |
| API cache | `~/tmp/vic_hydro_analysis/precip_cmp/cache/` | `vic_*.json` (5 points), `wrf_*.json` (3), `c6hist_*.json` (3), `c6ssp585_*.json` (3) |
| HUC8 polygons | `~/tmp/vic_hydro_analysis/boundaries/huc8.gpkg` | 157 HUC8, EPSG:4326 |
| Curation grid | `~/tmp/vic_hydro_analysis/grid/alaska_grid_12km_production.nc` | 209×299, mask sum 14,250 |
| Paper and README text | `~/tmp/vic_hydro_analysis/ncar_docs/{paper,readme}.txt` | present |
| Original results and job logs | `results/published/*.csv`, `~/tmp/vic_hydro_analysis/published/*.log` | used for comparison only |

**Grid note.** The monthly files are 166×205 (a window of the 209×299 daily grid, offset 15 rows and
40 columns; verified by summing the daily CCSM4 2050 January RUNOFF, max difference 6e-5 mm). Units
confirmed from attributes: wf monthly = `mm/month`, met monthly `pcp` = `mm/day` (monthly mean),
`tmax`/`tmin` = `deg_C`, daily wf = `mm/day`. Time axes are `days since <year>-01-01`, proleptic
Gregorian; the met time coordinate equals the cumulative month lengths in every file.

## 2. Jobs run (all `--partition=t1small --account=cmip6`, snap-geo)

| Job | Script | What | Runtime |
|---|---|---|---|
| 745211 | `v1_climatologies.py` | 1980–2009 and 2070–2099 climatologies for 20 runs + Daymet from 1,230 monthly wf files; per-file checks; point extraction | 16 s |
| 745217 (745212, 745215 failed on HadGEM2-ES's 11-month met file and a pickling bug) | `v2_alignment.py` | RCP4.5 vs RCP8.5 fields and VIC-PRCP vs met-pcp match for every model-year (6,000 files); glacier mask over all years; offset search on published and preliminary releases | 62 s + 22 s |
| 745213 | `v4_huc_from_scratch.py` | four opposite-sign HUC8s recomputed from raw files | 19 s |
| 745222 (745218, 745221 had bugs) | `v3_analysis.py` | baseflow share, change, HUC8, sensitivity, spot cells | ~1 min |
| 745219 | `v6_api_cell_match.py` | which native cell the API serves at each point | 12 s |
| 745220 | `v7_run_exceptions.py` | CCSM4 and CanESM2 exceptions to the shared-run claim | 10 s |
| login node | `v5_api_checks.py` | cached API JSON vs point extractions | seconds |

No job is still running; none of the final runs failed.

## 3. Claim table

Verdicts: **R** reproduced (within stated precision), **RD** reproduced with differences, **NR** not
reproduced, **NC** not checked. "Ours" = `review/results/` unless noted.

| # | Claim (report) | Ours | Verdict |
|---|---|---|---|
| H1 | Served `runoff` is surface runoff only; curation dropped `BASEFLOW` | `config.py` `variable_di["wf"]` = SNOW_MELT, EVAP, GLACIER_MELT, RUNOFF; API fields have no baseflow/total (`v5`) | R |
| H2 | Outside glacier cells baseflow is 48–50% of total runoff (1980–2009, per GCM), 52–56% in Nov–Apr | Per GCM: RCP8.5 48.4–49.8% (Nov–Apr 53.7–56.1%), RCP4.5 48.2–49.6% (52.3–55.8%), Daymet 49.8% (52.7%). Fig 2a monthly values reproduced to 0.01 mm (`v3_monthly_nonglacier.csv`) | R |
| H3 | Median baseflow share over 149 Alaska HUC8s 38% (4–68%) | Centroid assignment: 149 HUC8s, median 38.1%, range 3.6–67.5%, IQR 21.9–43.4% | R |
| H4 | RCP8.5 domain-wide: surface −17%, baseflow +63%, total +9% | −16.8% (−25.6 to −12.5), +63.4% (+38.0 to +83.8), +8.6% (−2.3 to +17.6); fig 2b per-model values reproduced | R (see issue 1) |
| H5 | Median HUC8 surface +32% vs total +51%; 22 of 149 opposite directions | +31.9% / +51.3%; 22 of 149 | R (see issue 2) |
| H6 | RCP4.5 hydrology 1950–2000 (CanESM2 to 2005) identical to RCP8.5 run; RCP4.5 met differs; from 2001 (2006) RCP4.5 VIC matches RCP4.5 met; all 10 models | Bit-identical (all six wf variables) for 9 models 1950–2000 and CanESM2 1950–2000. CCSM4: identical PRCP but hydrology differs (separate run). CanESM2 2001–2005: identical PRCP, hydrology differs by ≤0.06% domain-wide. VIC RCP4.5 PRCP = RCP8.5 met for 1950–2000 (CanESM2 2005) and = RCP4.5 met from 2001 (2006), all 10 models; RCP8.5 matches its met every year; met files differ between scenarios in every year | RD (issue 3) |
| H7 | API serves RCP4.5 met alongside the shared historical hydrology | At Fairbanks, Palmer, Bethel, Utqiagvik × 9 models: API rcp45 `pcp` = RCP4.5 met file (max monthly diff ≤1 mm) in every decade 1950s–2050s; API rcp45 `runoff` = rcp85 `runoff` in 93–100% of cases for 1950s–1990s and 0% from the 2000s | R |
| H8 | `glacier_melt` 20–40 m/yr in glacier cells, too large for a cell average | Median annual GLACIER_MELT over the 1,912 glacier cells: 19.4–28.0 m/yr per GCM, 37.8 m/yr Daymet; p90 115–150 m/yr; max 355–469 m/yr; single-month max 197 m. Total runoff in the same cells: median 2.6–2.8 m/yr; ice-loss residual P−ET−RO−BF median −0.66 to −0.91 m/yr (Daymet −1.73). GLACIER_MELT exceeds total runoff in 63–66% of glacier cells. (RO+BF−P+ET)/GLACIER_MELT median 0.035 | R |
| M1 | 14,250 VIC cells, 1,912 glacier cells; notes/01 says 14,227 | 14,250 non-NaN cells in monthly files = 14,227 VIC land cells (paper) + 23 cells outside the VIC domain that hold zeros in RCP8.5 files and NaN in RCP4.5 files (fill in the daily files, lat 54.5–71°N coastal). Glacier: 1,912 cells with GLACIER_MELT>0 in any run and year (paper: 1,913). Area 2,037,919 km² (2,034,732 without the 23) | R, reconciled |
| M2 | Non-glacier cells close the water balance, mean within ±3.5 mm/yr | Mean residual −3.2 to +3.5 mm/yr across runs; median \|residual\| 1.3–3.3 mm/yr | R |
| M3 | API `runoff` = raw RUNOFF rounded to whole mm (Fairbanks); second point | Fairbanks, Palmer, Bethel, Utqiagvik: 100% of 10 models × 2 RCPs × 6 decades × 12 months within 0.5 mm of the nearest native cell. Juneau: 5% at the nearest cell, 100% at the cell one column west (58.319°N, −134.589°E): the API grid is reprojected (`v6`) | R |
| M4 | HadGEM2-ES `pcp`/`tmax`/`tmin` null because 2005 met files lack December | Null at all 5 points, both RCPs, all 15 decades; hydrology present. Both `HadGEM2-ES_rcp*_BCSD_met_2005.nc` have 11 time steps; the wf 2005 files have 12 | R |
| M5 | Median HUC8 ~10,100 km², ~70 cells | 157 HUC8 median 10,124 km²; 149 with cells 10,307 km²; median 70 cells (centroid), 100 (any overlap). Matanuska: 60 cells, 8,722 km² here vs 8,843 km² in the Fig 1 caption (1.4%) | R |
| M6 | Other SNAP precipitation 20–40% wetter than VIC forcing | From the cache: ERA5-WRF +40.3/+34.1/+21.0% (Fairbanks/Palmer/Bethel); CMIP6-downscaled +33.0/+20.2/+19.0% over the 12 models with data (CNRM-CM6-1-HR returns no data; notes/03 says 13). Original CSV arithmetic correct. "20–40%" is a fair rounding of 19–40% | R (wording) |
| M7 | Daymet run 1980–2016 (CLAUDE.md says 2017) | 37 files 1980–2016 in both releases; GDEX has no 2017 | R |
| M8 | Published release fixed the preliminary RCP4.5 offsets; CanESM2 2060 daily MD5s match | Offset search (300 cells, ACCESS1-3/CanESM2/MIROC5): published release all exact at offset 0; preliminary release: 1980–2000 ↔ met year −30, 1950–1979 no exact match, CanESM2 2051–2099 ↔ −25, 2026–2050 no exact match. MD5s equal | R |
| D1 | Paper says "essentially uncalibrated" | Section 4: "the VIC model parameters used here are essentially uncalibrated (Section 2)" | R |
| D2 | VIC 4.2.glacier, 1950–2099, 10 CMIP5 GCMs × RCP4.5/8.5, BCSD vs Daymet, 12 km, no routing, ~20 daily variables | All in the paper/README; routing appears only as a downstream "other impact model"; wf 6 + ws 6 + eb 9 = 21 variables | R |
| D3 | 12 variables, decadal means of monthly summaries, whole mm, point query only, `mmm` across decades, EDS label "Runoff" | `hydrology.html` lists 12; `precision_di` 0 decimals (temperature 1); only `/hydrology/point/<lat>/<lon>`; `mmm` loops over era coordinates; `Hydrology.vue` label `Runoff` | R |
| D4 | `/arctic_hydrology` = RASM streamflow (Blaskey 2024); `/cmip6` serves SWE | docs: RASM, 34,346 MERIT Hydro segments, Blaskey baseline; `/cmip6` variable `snw` "Snow water equivalent, mm" | R |
| D5 | DOIs resolve | 10.5065/c3kn-2y77 → GDEX d010111; 10.1016/j.cliser.2022.100312 → Elsevier pii S2405880722000309; 10.1175/JHM-D-14-0104.1 → AMS; 10.18739/A25M62870 → arcticdata.io | R |
| X1 | Report is a two-page summary (CLAUDE.md) | 3 pages | NR (format) |
| X2 | Report agrees with notes and CSVs | Report numbers equal `results/published/*.csv`. notes/04's "19–53 m/yr" and "46–50%" are the superseded preliminary-release values (its header says so). notes/02 "1,913" vs notes/04 "1,912" glacier cells. notes/03 "13-model mean" is 12 models | minor |

## 4. Spot checks and sensitivity

**Baseflow share by cell** (`v3_spot_cells.csv`, 10-model mean RCP8.5 1980–2009). Surface runoff
peaks at the freshet (Apr–May; Jul–Aug on the North Slope) and baseflow peaks Jul–Oct at every
non-glacier cell. Annual shares: Fairbanks 47%, random Interior cell 45%, Palmer 30%, random
Southcentral 49%, Bethel 54%, random Y-K Delta 37%, Umiat 12%, random North Slope 12%,
Utqiagvik 25%, Ketchikan-area cell 68%, random Southeast 66%. Baseflow dominates Aug–Oct everywhere
(57–69%). In mid-winter (Dec–Feb) both terms are near zero in the Interior and North Slope;
baseflow is the larger term except at Palmer (Jan 2.0 mm surface vs 0.4 mm baseflow). The pattern
is hydrologically sensible; the "winter" statement in the report is a domain aggregate (Nov–Mar
baseflow share 65–78% in Fig 2a) and is driven by the wet Southeast and Southwest.

**Weighting and masks** (`v3_bf_share_by_run.csv`, `v3_change_summary.csv`). Non-glacier annual
share over the 10 RCP8.5 runs: map-factor weights 48.4–49.8%, equal weights 48.7–50.0%, glacier
mask "mean GLACIER_MELT > 100 mm/yr" (1,352 cells) 47.8–49.1%. Including glacier cells drops it
to 31–32% because glacier cells (13% of cells) produce 52–54% of domain total runoff (61% in the
Daymet run). RCP8.5 change, equal weights: −17.2/+62.8/+8.3%. **Non-glacier cells only:
surface +28.7% (+15.8 to +39.7), baseflow +58.7%, total +43.4% (+28.8 to +59.0); surface runoff
rises in all 10 models.** RCP4.5: all cells −20.8/+38.5/−2.1%; non-glacier +19.3/+37.4/+28.1%.

**HUC8 assignment** (`v3_huc8_summary.csv`). Centroid: 149 HUC8s, share 38.1% (3.6–67.5),
median change +31.9/+51.3%, 22 opposite signs. Area-weighted overlap of 12 km cell squares: 150
HUC8s, 38.1% (3.5–68.2), +30.2/+51.8%, 24 opposite (adds Talkeetna, Mulchatna, Stony; drops Lower
Susitna). Mean of per-model changes instead of change of the ensemble mean: +32.7/+52.4%, 22.
Restricting to HUC8s with ≥10 cells changes nothing material. In **all 149 HUC8s** the total-runoff
change exceeds the surface-runoff change (median gap 19.4 points); surface falls in 54, total in 32.

**Opposite-sign HUC8s.** Of the 22: 9 have one change below 5% in magnitude (5 below 2%); 13 have
both ≥5%; 15 have ≥7 of 10 models agreeing on both signs. Recomputed straight from the raw files
(`v4`, yearly HUC means → period means): Taku River −23.2% / +0.9% (total: 5 models up, 5 down;
interannual SD 14%, so +0.9% is noise), Kodiak-Afognak −6.6% / +26.0% (8 and 10 of 10), Canning
−11.1% / +32.3% (8 and 10), Admiralty Island −1.5% / +15.6% (7 and 10). Values equal the original
CSV to 0.1 point.

**Shared historical run** (`v2_alignment_published.csv`, `v7_run_exceptions.csv`). Compared RUNOFF,
BASEFLOW, EVAP, PRCP, SNOW_MELT, GLACIER_MELT for every model-year (SWE/ws files are not in the
published download). 9 models: all six variables bit-identical between RCP4.5 and RCP8.5 for
1950–2000 and different from 2001; CanESM2 identical 1950–2000. **CCSM4**: PRCP identical for
1950–2000 (same forcing) but the hydrology is a different run: domain runoff differs by 10.7% in
1950, 1.0% in 1951, <0.3% from 1957 and <0.05% from 1980; in 1980–2000, 2–5% of non-glacier
cells and ~45% of glacier cells differ by >1 mm/yr (different initial ice; the paper says glacier
initialization used CCSM4). **CanESM2 2001–2005**: PRCP identical to RCP8.5 (and ≠ the RCP4.5 met
file), hydrology differs by ≤0.06% domain-wide, with 1–9% of non-glacier cells differing by >1
mm/yr. Switch-over years confirmed for all 10 (2001; CanESM2 2006). Forcing match tolerance: median
|VIC PRCP − met pcp × days| ≈ 0.01 mm/month for the matching scenario, 11–23 mm for the other.
About 2,700 cells have a few months where VIC PRCP differs from met pcp by 1–8 mm (VIC-internal
adjustment); the 23 non-domain cells hold met precipitation but zero VIC output. Daymet: VIC PRCP
matches Daymet met in all 37 years.

**Time periods** (`v1_file_checks.csv`). 1,230 files read; every file has 12 months, the time-units
year equals the filename year, no NaN on land, 30 unique years per run and period, including
HadGEM2-ES (its 2005 wf file has December). EVAP minimum −91 mm/month (Daymet; condensation).

**API cell** (`v6_api_cell_match.csv`). Fairbanks, Palmer, Bethel, Utqiagvik: the API value equals
the nearest native cell in 99–100% of 120 model-scenario-decade combinations (runoff and evap).
Juneau: 0% at the nearest cell, 100% at the west neighbour. notes/05's "neither rate 20–45%" in
the provenance check comes from this grid offset at Juneau, not from the data. The original
`point_baseflow_share.csv` Juneau value (62%) refers to the nearest native cell (glacier cell),
not the cell the API serves; the report does not use it.

## 5. Where my method differs from the original scripts (read after my runs)

- Glacier mask: the original uses GLACIER_MELT>0 in any of its 61 climatologies; mine uses any
  file of any year (identical result, 1,912 cells) and also a 100 mm/yr threshold.
- The original's statewide sums include the 23 zero cells (no effect on sums or shares); its
  per-cell change statistics use 14,227 cells with RUNOFF and total > 5 mm.
- HUC8: both use centre-in-polygon with map-factor cell areas; I added the overlap method.
- Forcing match: the original scores 11 months (February excluded, leap-year day counts) at 400
  cells; I compared full fields (all 12 months) and ran a 300-cell offset search. Same answers.
- API comparison: the original checked Fairbanks only (CCSM4, 1990s); I checked 5 points, all
  models, 6 decades, and resolved Juneau's cell offset.
- Precipitation sources: identical arithmetic; model count 12, not 13.
- v4 recomputes HUC8 changes from yearly files rather than from 30-year climatologies.

## 6. Assessment of the report's conclusions

Every headline number is reproduced and robust to weighting, glacier mask and HUC8 assignment.
Three statements need more careful wording: the domain-wide RCP8.5 change (issue 1), the count of
opposite-sign HUC8s (issue 2) and "a copy of the RCP8.5 run" (issue 3). None changes the
recommendation. Option C (add baseflow and total runoff, serve each run's actual forcing,
aggregate by watershed) still follows: baseflow is half of the water outside glaciers, the
surface-runoff change understates the total-runoff change in every HUC8, and the RCP4.5 historical
met does not match the served hydrology in any model.

## 7. Not checked

- Skill against gauges or SNOTEL (out of scope by design).
- `ws` and `eb` variables (SWE, IWE, soil moisture, energy terms) in the published release: only
  wf and met were downloaded, so the RCP4.5/RCP8.5 identity test covers the six wf variables.
- The Rasdaman GeoTIFFs and the live Arctic-EDS page (checked through the API cache and the repo
  source instead).
- Mid-century (2040–2069) numbers in `results/published/` (not used in the report).
