# VIC-Hydro (NCAR 12 km Alaska) — Assessment & Action Plan

Context brief for SNAP's `/hydrology` endpoint on earthmaps.io. Written for a follow-up Claude Code session. **Constraint: the source model run cannot be re-run or recalibrated** — all actions below use existing NCAR outputs via our own curation pipeline and API.

## 1. What the dataset is

- **Source:** Mizukami, Newman, Wood, Gutmann & Hamman (2022), *21st Century Hydrologic Projections for Alaska and Hawaiʻi*, UCAR/NCAR/RAL, doi:10.5065/c3kn-2y77. Companion paper: Mizukami et al. (2022), *Climate Services* 27, 100312, doi:10.1016/j.cliser.2022.100312.
- **Forcing:** 10 CMIP5 GCMs (ACCESS1-3, CanESM2, CCSM4, CSIRO-Mk3-6-0, GFDL-ESM2M, HadGEM2-ES, inmcm4, MIROC5, MPI-ESM-MR, MRI-CGCM3), RCP4.5 & RCP8.5, downscaled with **BCSD** to 12 km, trained on Daymet v3 aggregated to 12 km (1980–2017).
- **Model:** VIC 4.2.glacier, 1950–2099, frozen-soil algorithm (2-hr step), organic-soil adjustment, simple glacier model on 1,913 of 14,227 cells (RGI v6 extent). No routing.
- **Parameters:** soil parameters from SoilGrids + ASTER GDEM2 via **transfer functions calibrated on CONUS CAMELS basins** (Mizukami et al. 2017, MPR approach) and transferred to Alaska. Not calibrated against Alaska observations. Vegetation from Gergel (2019) Arctic land cover.
- **What we serve:** decadal means of monthly summaries, per 12 km cell, 12 variables (`evap, glacier_melt, iwe, pcp, runoff, sm1–3, snow_melt, swe, tmax, tmin`). `?summarize=mmm` = min/mean/max **across decades** (not across models).

## 2. The "uncalibrated" critique

Feedback cited Mendoza et al. (2015), *J. Hydrometeor.* 16(2), doi:10.1175/JHM-D-14-0104.1: with default parameters, none of VIC/PRMS/Noah/Noah-MP reproduced seasonal runoff or flow duration curves (3 Colorado headwater basins).

Nuance:
- Our run is **not** Mendoza-style "default parameters": its transfer functions were calibrated, just in CONUS. Accurate description: *"regionally parameterized, not calibrated in Alaska."* The open question is transferability to permafrost/organic-soil/glacier/tundra settings poorly represented in CAMELS.
- Mendoza also found calibration did **not** resolve inter-model disagreement in change signals (esp. ET, snowpack), single-objective calibration can be "right for the wrong reasons," and calibration sometimes flipped the sign of runoff change. Calibration ≠ trustworthy; no calibration ≠ useless.

## 3. Key finding: baseflow was dropped in curation

Repo: `ua-snap/ardac-curation`, `curation/ncar12km_decadal_summaries/`

- NCAR `wf` files contain both `RUNOFF` (surface runoff) and `BASEFLOW`. VIC total runoff = `RUNOFF + BASEFLOW`.
- `config.py` → `variable_di["wf"]` processes only `SNOW_MELT, EVAP, GLACIER_MELT, RUNOFF`. `BASEFLOW` is mentioned once (EDA notebook) and never processed.
- So the API's `runoff` is **surface runoff only**. It understates water yield, misrepresents seasonality (winter flow is mostly baseflow), and its projected change may not track total-runoff change. The paper's runoff results use total runoff.
- The API docs (`ua-snap/data-api`, `templates/documentation/hydrology.html`) correctly say "surface runoff," but users will likely read `runoff` as total.

Second finding: a **Daymet-forced historical VIC run (1980–2017)** was downloaded and explored (`eda_daymet_only.ipynb`, `download_scripts/download_alaska_vic_daymet.sh`) but is not exposed in the API.

## 4. Fitness for use (as-is)

| Confidence | Variables / uses |
|---|---|
| Higher | `tmax`, `tmin`, `pcp`; `swe`, `snow_melt`, `glacier_melt`, `iwe`; direction and rough size of temperature-driven change; snow-season shifts |
| Moderate | `evap` change direction where models agree; spatial patterns; screening/"where to look" |
| Weak | `runoff` **(any use, including relative change, until baseflow is added)**; absolute soil moisture (`sm1–3`, better as anomalies); low flows; daily extremes/floods (BCSD limits these regardless); anything gauge- or design-scale |

Paper headline results (useful framing): runoff increases over most of Alaska; decreases in currently glacierized SE Alaska; 50–100% snowpack loss along Gulf of Alaska and Bering Sea; interior/North Slope snowpack increases. Domain-median late-century RCP8.5 change: ΔT 6.2 °C, ΔP +207 mm/yr, ΔET +43 mm/yr, ΔRO +149 mm/yr (σ 44).

## 5. Action plan (no model re-run needed)

1. **Add `baseflow` and `total_runoff`** — `ardac-curation`
   - In `config.py`, add `"BASEFLOW": np.sum` to `variable_di["wf"]` and entries to `precision_di`, `unit_di`, `summary_di`.
   - Compute `TOTAL_RUNOFF = RUNOFF + BASEFLOW` from **daily** data before monthly/decadal summarizing (don't add rounded outputs; `precision_di` rounds to 0 decimals).
   - Re-run `run_wf_vars.ipynb`, `reproject.ipynb`, `qc.ipynb`, zip; ingest into Rasdaman `hydrology` coverage.
   - `data-api`: update `routes/hydrology.py` encodings if needed, docs table, tests in `tests/routes/hydrology/point/`. Consider renaming `runoff` → `surface_runoff` (or keep with a prominent note).
2. **Expose the Daymet-forced historical run** as a baseline "model" (1980–2017 decades).
3. **Cross-model summaries:** median, range, and count of models agreeing on sign of change.
4. **Change/delta outputs:** future decade minus historical baseline, absolute and percent.
5. **Skill assessment (after step 1):** aggregate Daymet-run total runoff over USGS gauge basins in Alaska and compare (runoff ratio, timing, seasonal shape); compare SWE to SNOTEL and snow extent to MODIS. Publish a skill table/map.
6. **Documentation:** parameter provenance (§1), recommended uses (§4), BCSD caveat on extremes, recommend relative change + model agreement.

## 6. Open items to verify

- Paper's evaluation/limitations sections were only seen as a summary (claims: "essentially uncalibrated," no historical streamflow/SWE evaluation shown). Confirm against full text before citing.
- Whether source data are still on disk (`/atlas_scratch/cparr4/ncar_replacement_data`) or need re-download from NCAR.
- EDA noted negative `EVAP` values (likely condensation; plausible) and a very large daily `GLACIER_MELT` max (~160 in/day) — worth a QC look.
- Fraction of total runoff from baseflow in this dataset — quantify once processed.

## Sources

- ua-snap/data-api: `templates/documentation/hydrology.html`, `routes/hydrology.py`
- ua-snap/ardac-curation: `curation/ncar12km_decadal_summaries/` (`README.md`, `config.py`, `compute_summaries.py`, `eda_daymet_only.ipynb`)
- Mizukami et al. 2022, Climate Services — https://www.sciencedirect.com/science/article/pii/S2405880722000309
- NCAR dataset — https://doi.org/10.5065/c3kn-2y77
- Mendoza et al. 2015, JHM — https://journals.ametsoc.org/view/journals/hydr/16/2/jhm-d-14-0104_1.xml
