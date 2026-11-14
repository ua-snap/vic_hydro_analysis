# 03 — Should Option C keep `tmax`, `tmin`, `pcp` alongside the VIC outputs?

Question (2026-11-13): the report's Option C drops the met variables because other SNAP products
cover temperature and precipitation. But a user could pair VIC runoff/ET with precipitation from
another dataset and get a water balance that doesn't add up. Should we keep the met variables with
VIC for consistency?

## What these variables are

`tmax`, `tmin` and `pcp` in VIC-Hydro are **not** a separate climate product. They are the exact
BCSD-downscaled CMIP5 forcing that drove VIC, regridded and summarized the same way as the
hydrology outputs. Every VIC output is a function of these inputs:

- **Water balance:** P = ET + R_surface + R_baseflow + ΔS (soil moisture, SWE, glacier ice).
  Over a multi-decade mean, ΔS ≈ 0 except where glaciers are losing mass.
  So P − ET − R_surface ≈ baseflow (+ glacier loss) in the VIC world.
- **Snow and glacier variables** depend on temperature (rain/snow partitioning, melt).

## Why another dataset's P won't match

Any other SNAP precipitation differs from VIC's forcing in almost every respect:

| | VIC forcing | `/cmip6_downscaled` | `/era5wrf` | `/taspr` |
|---|---|---|---|---|
| Climate models | 10 CMIP5 | 13 CMIP6 | none (reanalysis) | 2 CMIP5 + 5-model average |
| Scenarios | RCP4.5/8.5 | SSPs | historical only | RCP4.5/6.0/8.5 |
| Downscaling | BCSD (statistical) | bias-adjusted to ERA5-WRF | WRF (dynamical) | statistical (see API docs) |
| Observational reference | Daymet v3 | ERA5-WRF | ERA5 | CRU TS 4.0 (historical) |
| Grid | 12 km | 4 km | 4 km | 2 km |

The reference climatology sets absolute precipitation, and Alaska's gridded precipitation
products disagree a lot, especially in mountains and on the coast where gauges are sparse and
undercatch snow. The climate models and scenarios set the change signal, and CMIP6 generally runs
warmer and wetter at high latitudes than CMIP5.

## Evidence at five points (`scripts/compare_precip_sources.py` → `results/precip_source_comparison.csv`)

All values come from the SNAP API. Historical = 1980–2009 annual mean (VIC: 9-model mean of the
1980s, 1990s and 2000s decadal sums, RCP8.5 branch). Future = 2070–2099. Units are mm/yr.

| | Fairbanks | Palmer | Bethel | Juneau | Utqiagvik |
|---|---|---|---|---|---|
| VIC `pcp` (forcing), hist | 317 | 473 | 484 | 2,453 | 93 |
| ERA5-WRF P, 1980–2009 | 445 (**+40%**) | 635 (**+34%**) | 585 (**+21%**) | outside domain | outside domain |
| CMIP6-downscaled P, hist (13-model mean) | 422 (**+33%**) | 569 (**+20%**) | 576 (**+19%**) | outside domain | outside domain |
| VIC `evap` | 249 | 352 | 188 | 352 | 49 |
| VIC `runoff` (surface) | 35 | 82 | 134 | 824 | 31 |
| **P − ET − R_surf, using VIC P** | **33** | **39** | **162** | **1,277** | **12** |
| P − ET − R_surf, using ERA5-WRF P | 161 | 201 | 264 | — | — |
| P − ET − R_surf, using CMIP6 P | 138 | 134 | 254 | — | — |
| ΔP late century, VIC RCP8.5 (model range) | +48% (25–73) | +39% (25–55) | +35% (13–63) | +18% (10–29) | +62% (34–99) |
| ΔP late century, CMIP6 SSP5-8.5 (model range) | +42% (22–60) | +35% (15–53) | +36% (21–52) | — | — |

Findings:

1. **Absolute precipitation differs by 20–40%.** Both the ERA5-WRF and CMIP6-downscaled products
   are wetter than VIC's Daymet-based forcing at all three points where they overlap. A user who
   pairs VIC runoff and ET with either product sees 100–170 mm/yr of "missing" water. That's a
   residual 2–5× larger than in VIC's own water balance, so runoff ratios and closure checks come
   out wrong.
2. **Relative change is similar.** Late-century RCP8.5 vs SSP5-8.5 precipitation increases are
   within a few percentage points at all three points, with overlapping model ranges. Mixing
   datasets is much less harmful for percent change than for absolute amounts. But the models
   differ (CMIP5 vs CMIP6), so model-by-model attribution of ΔRunoff to ΔP is impossible without
   VIC's own forcing.
3. **Coverage differs.** Juneau and Utqiagvik are outside the 4 km ERA5-WRF and CMIP6-downscaled
   domains. In SE Alaska and on the North Slope, there's no matching 4 km precipitation to pair
   with VIC at all.
4. **HadGEM2-ES already has null `pcp`, `tmax` and `tmin`** in the API at every point, though its
   hydrology outputs are present. So the met variables are currently available for only 9 of 10
   models. cparr4's tree has a `met/HadGEM2-ES` directory, so the source likely exists and this
   looks like a curation or ingest gap. One hypothesis, unverified: HadGEM2-ES uses a 360-day
   calendar, which might have tripped the met processing.

Side result: an **interim baseflow estimate**. With VIC's own P, the residual P − ET − R_surface
≈ baseflow + storage change. Over 30 years, storage change is near zero except where glaciers are
losing mass. So the implied baseflow share of total runoff (residual / (residual + R_surf)) is:

- Fairbanks ~49%
- Palmer ~32%
- Bethel ~55%
- Juneau ~61%
- Utqiagvik ~28%

Caveats: the inputs are rounded to whole mm per month; HadGEM2-ES is excluded; VIC's
water-balance error and any glacier or permafrost storage trend are folded into the residual; and
this is 5 points, not a statewide number. Still, it points the same way as expected: baseflow is
a large fraction (roughly 30–60%) of total runoff, so surface runoff alone substantially
understates water yield.

## Recommendation: keep the met variables, but serve them as VIC forcing

Keep `pcp`, `tmax` and `tmin` in Option C, reframed as **VIC's input forcing** rather than as a
climate product.

- **Why keep them**
  - VIC's water balance only adds up with its own P (finding 1).
  - Watershed-level water-balance tables (P, ET, total runoff, ΔS), the most useful product in
    Option C, need P.
  - Attributing runoff change to precipitation vs warming needs model-matched forcing
    (finding 2).
  - Temperature is needed to interpret shifts in snow and glacier variables.
  - SE Alaska and the North Slope have no alternative 4 km data (finding 3).
  - It costs almost nothing, since the variables are already curated.
- **Risk of keeping them:** two SNAP precipitation projections disagree by 20–40% at the same
  place, which looks like an error to an unprepared user.
- **Mitigation**
  - Label them as forcing (e.g. `forcing_pcp`, or a "VIC inputs" group).
  - State in the docs and UI that they're the BCSD CMIP5 forcing, provided for consistency with
    the VIC outputs.
  - Don't chart them as standalone climate projections. Point climate questions to
    `/cmip6_downscaled`.
- **Required with this choice:** fix the HadGEM2-ES gap.

Lower priority: if something has to go, drop `tmax`/`tmin` before `pcp`. Temperature isn't part of
the water-balance closure.
