# 04 — Baseflow results (raw NCAR monthly wf files)

> **Superseded (2026-11-13):** the analysis was re-run on NCAR's *published* release (GDEX d010111,
> job 744367), and the results are in `results/published/`. RCP8.5 and the non-glacier shares are
> essentially unchanged: non-glacier 48–50% (Nov–Apr 52–56%); RCP8.5 late century surface −17%,
> baseflow +63%, total +9%; 22 of 149 HUC8s with opposite signs. The published RCP4.5 values are
> now valid: late century surface −21% (−28 to −14), baseflow +39%, total −2% (−11 to +6). The
> report uses the published numbers. The text below is the original preliminary-release analysis.

Job 744113, 2026-11-13. Script `scripts/baseflow_analysis.py`, outputs in
`~/tmp/vic_hydro_analysis/baseflow/` (small CSVs copied to `results/baseflow/`).

**Setup**
- Source: `/beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/monthly/` (monthly sums; identical to
  daily-file sums, checked at Fairbanks).
- Periods: hist 1980–2009, mid 2040–2069, late 2070–2099, per scenario. Daymet run: 1980–2009.
- Domain: 14,250 VIC cells (2.04 M km²), including transboundary Canadian basins. 1,912 are
  glacier cells (GLACIER_MELT > 0 in any run). Areas use the polar-stereographic map factor.
- "Total runoff" = RUNOFF (surface) + BASEFLOW.

## 1. Baseflow is about half of total runoff outside glaciers

Historical (1980–2009) shares of total runoff that are baseflow:

| | Non-glacier cells (12,338) | Whole domain, incl. glacier cells |
|---|---|---|
| Annual | **Daymet 50%; 10 GCMs 46–50%** | 28–32% |
| Winter (Nov–Apr) | **52–57%** | 49–55% |
| Freshet (May–Jun) | — | 12–15% |
| Jul–Oct | — | 32–37% |
| Median cell | — | 36–42% |

- HUC8 (Alaska, 149 watersheds with cells; GCM ensemble mean, RCP8.5 historical): median 38%,
  IQR 22–43%, range 4–68%.
- Points (ensemble, nearest cell): Fairbanks 47%, Palmer 30%, Juneau 62%, Bethel 54%,
  Utqiagvik 25%. These agree with the earlier API water-balance estimates (49/32/61/55/28%).

So SNAP's served `runoff` (surface only) leaves out roughly half of the water yield outside
glaciers, and more than half in winter.

## 2. Surface runoff change doesn't track total runoff change

Late century (2070–2099) vs. historical, same scenario; whole domain; range across 10 GCMs:

| | RCP8.5 | RCP4.5 (see caveat) |
|---|---|---|
| Surface runoff (what we serve) | **−17%** (−26 to −13) | −30% (−34 to −26) |
| Baseflow | **+63%** (+38 to +84) | +37% (+20 to +47) |
| Total runoff | **+9%** (−2 to +18) | −10% (−14 to −7) |

- Domain-wide, surface runoff and total runoff change in **opposite directions** under RCP8.5.
  Projected warming shifts water from surface runoff to baseflow, probably through less frozen
  ground and more infiltration (plausible, not diagnosed here).
- Per cell (RCP8.5 late, mean over GCMs):
  - 10% of cells (7–19%) have opposite signs.
  - The median |Δsurface% − Δtotal%| is 18 percentage points (10–29).
  - 36% of cells differ by more than 25 points.
  - Rank correlation is 0.90: spatial patterns are similar, but magnitudes are biased low.
- HUC8 (ensemble mean, RCP8.5 late):
  - Median HUC8 change is **+32% surface vs +51% total**.
  - **22 of 149 HUC8s (15%) have opposite signs.**

## 3. Water balance and data-quality checks

- **Non-glacier cells close the water balance:** P − ET − RO − BF has a mean within ±3.5 mm/yr
  and a median |residual| of 1–4 mm/yr. That makes the API-based residual estimate in
  notes/03 legitimate.
- **Glacier cells look wrong:**
  - The 1,912 glacier cells produce 52–61% of all domain runoff.
  - The served `glacier_melt` (GLACIER_MELT) has median annual values of **19–53 m/yr** in those
    cells, roughly 10–50× the cell's ice-loss residual (P − ET − RO − BF ≈ −0.7 to −1.7 m/yr).
  - GLACIER_MELT is probably expressed per glacier area, or in different units, rather than as a
    cell-average flux. **Don't interpret `glacier_melt` as cell-average melt** until resolved.
  - Domain-wide totals above are dominated by glacier cells. Prefer the non-glacier and HUC8
    numbers.
- **The API matches raw RUNOFF:** at Fairbanks, curated `runoff` = raw RUNOFF rounded to whole mm.

## 4. Caveat: these files are NCAR's preliminary release (see notes/05)

The beegfs files are NCAR's preliminary release (2020/21), not the published release SNAP
curated. In the preliminary release, the RCP4.5 VIC outputs are year-misaligned with their
forcing, so **the RCP4.5 numbers above shouldn't be used**. RCP8.5 is internally consistent and
matches the API (published release) closely, so the RCP8.5 and Daymet-independent conclusions
should hold. Confirm on a few published files before quoting exact values.
