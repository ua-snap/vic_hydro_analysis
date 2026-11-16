---
title: "Verification of the VIC-Hydro assessment"
subtitle: "Independent check of report/vic_hydro_summary.pdf (draft 2026-11-13) · 2026-11-16"
geometry: "margin=0.5in"
fontsize: 10pt
mainfont: "Liberation Sans"
monofont: "DejaVu Sans Mono"
header-includes:
  - \AtBeginDocument{\small}
---

**Verdict: defensible with minor corrections; the recommendation (Option C) still follows.**
Every number that drives the recommendation was reproduced from NCAR's published files with new
code (`review/scripts/`, details in `review/notes.md`), and holds under equal-area weighting, a
stricter glacier mask and area-weighted HUC8 assignment. Four things should be reworded: the
domain-wide change headline is driven by glacier cells, 9 of the 22 opposite-sign watersheds involve
a near-zero change, "a copy of the RCP8.5 run" is exact for 9 of 10 models, and the PDF runs to
three pages.

| Claim (report) | Our value | Verdict |
|:--------------------------------|:-----------------------------------------------------|:------|
| Served `runoff` is surface only; baseflow dropped | Curation config processes RUNOFF, not BASEFLOW; API has no baseflow field | Reproduced |
| Baseflow 48–50% of total runoff outside glaciers, 52–56% Nov–Apr | 48.2–49.8% per GCM (Daymet 49.8%); Nov–Apr 52.3–56.1%. Equal weights or a 100 mm/yr glacier threshold move it under 1 point. Fig. 2a values match to 0.01 mm | Reproduced |
| Median of 149 HUC8s 38% (4–68%) | 38.1% (3.6–67.5%); area-weighted overlap: 150 HUC8s, 38.1% (3.5–68.2%) | Reproduced |
| RCP8.5 domain-wide: surface −17%, baseflow +63%, total +9% | −16.8 / +63.4 / +8.6% (equal weights −17.2 / +62.8 / +8.3%). Outside glacier cells: **+28.7 / +58.7 / +43.4%**, surface up in all 10 models | Reproduced; see 1 |
| Median HUC8 surface +32% vs total +51%; 22 of 149 opposite | +31.9 / +51.3%; 22 (overlap method 24 of 150). Total change exceeds surface change in all 149 (median gap 19 points) | Reproduced; see 2 |
| RCP4.5 hydrology 1950–2000 (CanESM2 to 2005) is a copy of RCP8.5; RCP4.5 met differs; all 10 models | Six wf variables bit-identical for 9 models (CanESM2 to 2000). CCSM4: same precipitation, separate run. RCP4.5 VIC precipitation equals the RCP8.5 met file until 2001 (CanESM2 2006) in all 10; met files differ by scenario every year | With differences; see 3 |
| API serves RCP4.5 met beside the shared hydrology | At 4 points × 9 models, API rcp45 `pcp` equals the RCP4.5 met file in every decade; rcp45 `runoff` equals rcp85 through the 1990s, not after | Reproduced |
| `glacier_melt` 20–40 m/yr in glacier cells | Medians 19.4–28.0 m/yr per GCM, 37.8 Daymet; 90th percentile over 110 m/yr; total runoff in those cells 2.7 m/yr; ice-loss residual 0.7–0.9 m/yr | Reproduced |
| 14,250 cells / 1,912 glacier; water balance within ±3.5 mm/yr | 14,227 VIC cells plus 23 all-zero cells outside the domain; 1,912 (paper 1,913); residual −3.2 to +3.5 mm/yr | Reconciled |
| API `runoff` = raw RUNOFF rounded; HadGEM2-ES met null (no December 2005) | 100% of 120 model-scenario-decades at 5 points (Juneau: API uses the cell one column west); null at all points, both 2005 met files have 11 months | Reproduced |
| Median HUC8 10,100 km², ~70 cells; other precipitation 20–40% wetter | 10,124 km², 70 cells; ERA5-WRF +21 to +40%, CMIP6 +19 to +33% (12 models with data, not 13) | Reproduced |
| Daymet 1980–2016; published release has no year offsets; MD5s match; paper says "essentially uncalibrated"; API/EDS facts; DOIs | 37 files; no offsets (preliminary offsets of −30 and −25 years confirmed); MD5s equal; quote in Section 4; 12 variables, point only, `mmm` across decades, EDS label "Runoff", RASM 34,346 segments, `/cmip6` `snw`; all DOIs resolve | Reproduced |

**Issues**

1. **Minor: the domain-wide change headline is a glacier-cell effect.** Glacier cells are 13% of
   cells but 52–54% of domain runoff, and the report itself distrusts them. Outside glacier cells
   surface runoff *rises* 29% and total runoff 43% under RCP8.5 in every model; the sign flip exists
   only in the glacier-dominated domain total. notes/04 already advises preferring non-glacier and
   HUC8 numbers. Fix: lead with "surface runoff understates the total-runoff change in every HUC8
   (median +32% vs +51%)" and present −17% vs +9% as the domain total, dominated by glacier cells.
2. **Wording: 22 opposite-sign HUC8s.** Nine have a change under 5% in one term (five under 2%);
   13 have both above 5%; 15 have at least 7 of 10 models agreeing on both signs. Taku River's
   +0.9% total change is noise (models split 5–5, interannual spread 14%). Recomputed from raw
   files, the values match. Fix: "22 of 149 (13 with both changes above 5%)".
3. **Wording: "a copy of the RCP8.5 run".** Exact for 9 models. CCSM4's RCP4.5 historical run used
   the RCP8.5 precipitation but is a separate run: domain runoff differs by 10.7% in 1950, under
   0.3% after 1957 and under 0.05% from 1980, with about half the glacier cells differing
   throughout (glacier initialization used CCSM4). CanESM2 is identical to 2000 and within 0.06%
   for 2001–2005. The conclusion holds for all 10. Fix: "identical to the RCP8.5 run (CCSM4:
   equivalent within 0.1% after 1960)"; in Fig. 2c, say the precipitation pattern holds for all 10.
4. **Format and small items.** The PDF is three pages (recommendation on page 3) against a two-page
   brief. notes/03 "13-model mean" is 12 models (CNRM-CM6-1-HR returns no data). notes/04's
   "19–53 m/yr" is the superseded preliminary release. Fig. 1 gives Matanuska as 8,843 km²; the
   polygon measures 8,722 km² here (60 cells confirmed). The provenance check's "neither" rate at
   Juneau is a grid offset, not a data problem.

**Not checked.** Skill against gauges or SNOTEL (out of scope). SWE and other `ws`/`eb` variables
are not in the published download, so the RCP4.5/RCP8.5 identity test covers the six `wf`
variables. The Rasdaman GeoTIFFs and the live Arctic-EDS page were checked only through the API
cache and repo source.
