"""Figures for section 3 of the two-page summary (published GDEX d010111 release).

Figure 2  (one row, panels a-c = section 3 bullets 1-3)
  a. Missing baseflow: monthly surface runoff (served) and baseflow (not served), area-weighted
     over non-glacier land cells, 1980-2009, mean of the 10 GCMs (RCP8.5 historical run).
  b. Misstated change: RCP8.5 change 1980-2009 -> 2070-2099 in domain-wide surface runoff,
     baseflow and total runoff (bar = 10-model mean, dots = individual models).
  c. ACCESS1-3, 1950-2099: mean per-cell |RCP4.5 - RCP8.5| for BCSD forcing precipitation and for
  VIC surface runoff. Zero = identical files.

Inputs (all written by earlier scripts):
  <clim_nc>     wf_monthly_climatologies.nc     (baseflow_analysis.py)
  <change_csv>  runoff_change_surface_vs_total.csv (baseflow_analysis.py)
  <ts_csv>      timeseries_ACCESS1-3.csv        (fig_ncar_historical_forcing.py)

Usage: python fig_summary_issues.py <clim_nc> <change_csv> <ts_csv> <fig_dir> <table_dir>
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

CLIM, CHANGE, TS = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
FIG, TAB = Path(sys.argv[4]), Path(sys.argv[5])
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

# reference palette (dataviz skill, light mode); fixed categorical order
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
C_RO, C_BF, C_TOT = "#2a78d6", "#eb6834", "#1baf7a"  # slots 1-3: surface runoff, baseflow, total
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "axes.edgecolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white",
                     "savefig.facecolor": "white", "hatch.color": "white", "hatch.linewidth": 1.0})

# ---------------- panel a data: non-glacier monthly climatology
ds = xr.open_dataset(CLIM)
runs = [r for r in ds.run.values if r.endswith("|rcp85|hist") and not r.startswith("daymet")]
clim = ds.climatology
area = ds.area_km2.values
ro_all = clim.sel(var="RUNOFF").values  # (run, month, y, x)
land = np.isfinite(ro_all).all(axis=(0, 1))
# glacier cells as in baseflow_analysis.py: any run with annual GLACIER_MELT > 0
glac = (np.nan_to_num(clim.sel(var="GLACIER_MELT").values).sum(axis=1) > 0).any(axis=0)
nong = land & ~glac
w = np.where(nong, area, 0.0)
sel = clim.sel(run=runs)


def wmean(var):  # (run, month) area-weighted mean over non-glacier land, mm/month
    v = np.nan_to_num(sel.sel(var=var).values)
    return (v * w).sum(axis=(2, 3)) / w.sum()


ro_m, bf_m = wmean("RUNOFF").mean(axis=0), wmean("BASEFLOW").mean(axis=0)
share = bf_m.sum() / (ro_m.sum() + bf_m.sum())
print(f"runs: {len(runs)}; non-glacier land cells: {int(nong.sum())}; glacier cells: {int((glac & land).sum())}")
print(f"non-glacier baseflow share (10-GCM mean climatology): {share:.3f}")
pd.DataFrame({"month": range(1, 13), "surface_runoff_mm": ro_m, "baseflow_mm": bf_m}).round(2).to_csv(
    TAB / "fig2a_nonglacier_monthly_RO_BF.csv", index=False)

# ---------------- panel b data: RCP8.5 late-century change
ch = pd.read_csv(CHANGE)
ch = ch[(ch.scenario == "rcp85") & (ch.period == "late")]
terms = [("Surface runoff\n(served)", "statewide_dRO_pct", C_RO, ""),
         ("Baseflow\n(not served)", "statewide_dBF_pct", C_BF, "////"),
         ("Total runoff\n(not served)", "statewide_dTOT_pct", C_TOT, "////")]
print(ch[[t[1] for t in terms]].agg(["mean", "min", "max"]).round(1).to_string())
ch[["model"] + [t[1] for t in terms]].round(1).to_csv(TAB / "fig2b_rcp85_late_change.csv", index=False)

# ---------------- Figure 2 (panels a-c)
ts = pd.read_csv(TS)
switch = int(ts.loc[ts.agree_met45 > 0.9, "year"].min())

fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.4, 2.15), gridspec_kw={"width_ratios": [1.05, 1.0, 1.15]})
TFS = 8.2  # panel title size

# a. missing baseflow
mon = np.arange(1, 13)
a.bar(mon, ro_m, width=0.8, color=C_RO, label="Surface runoff (served)")
a.bar(mon, bf_m, width=0.8, bottom=ro_m, color=C_BF, hatch="////", edgecolor="white", lw=0,
      label="Baseflow (not served)")
a.set_xticks(mon, list("JFMAMJJASOND"), fontsize=7)
a.set_ylabel("mm per month")
a.set_title(f"a. Baseflow, {share * 100:.0f}% of runoff, is missing", loc="left", fontsize=TFS)
a.set_ylim(0, 1.45 * (ro_m + bf_m).max())
a.legend(frameon=False, fontsize=6.8, loc="upper right", handlelength=1.2)
a.grid(axis="y", color=GRID, lw=0.6)
a.set_axisbelow(True)
a.tick_params(axis="x", length=0)

# b. misstated change
y = np.arange(len(terms))[::-1]
for yi, (lab, col, cc, h) in zip(y, terms):
    vals = ch[col].values
    b.barh(yi, vals.mean(), height=0.6, color=cc, hatch=h, edgecolor="white", lw=0)
    b.scatter(vals, np.full_like(vals, yi), s=7, color=INK, zorder=3, lw=0)
    b.text(max(vals.max(), 0) + 4, yi, f"{vals.mean():+.0f}%", va="center", fontsize=7.5, color=INK,
           fontweight="bold")
b.axvline(0, color=INK2, lw=0.8)
b.set_yticks(y, [t[0] for t in terms], fontsize=6.8)
b.tick_params(axis="y", length=0)
b.set_xlabel("RCP8.5 change by 2070–2099 (%)")
b.set_title("b. Served runoff falls; total rises", loc="left", fontsize=TFS)
b.grid(axis="x", color=GRID, lw=0.6)
b.set_axisbelow(True)
b.spines["left"].set_visible(False)
allv = ch[[t[1] for t in terms]].values
b.set_xlim(min(-35, allv.min() - 5), allv.max() + 32)

# c. RCP4.5 shares the RCP8.5 historical run
c.axvspan(1949.5, switch - 0.5, color=GRID, alpha=0.6, lw=0)
c.axhline(0, color=INK2, lw=0.8)
c.plot(ts.year, ts.d_met45_met85, color=INK2, lw=1.1, label="Precipitation (pcp)")
c.plot(ts.year, ts.d_runoff45_runoff85, color=C_RO, lw=1.3, label="Runoff")
c.text(1953, 0.96, f"1950–\n{switch - 1}", transform=c.get_xaxis_transform(), va="top", fontsize=6.8,
       color=INK2)
c.set_xlim(1950, 2099)
c.set_xticks([1950, 2000, 2050, 2099], ["1950", "2000", "2050", "2099"], fontsize=7)
c.set_ylim(-15, 1.75 * ts.d_met45_met85.max())
c.set_ylabel("|RCP4.5 − RCP8.5|\n(mm/yr)", fontsize=7.5)
c.set_title(f"c. RCP4.5 runoff copies RCP8.5", loc="left", fontsize=TFS)
c.legend(frameon=False, fontsize=6.8, loc="upper right", handlelength=1.2)
c.grid(axis="y", color=GRID, lw=0.6)
c.set_axisbelow(True)

fig.tight_layout(w_pad=1.2)
fig.savefig(FIG / "fig2_section3_issues.pdf")
fig.savefig(FIG / "fig2_section3_issues.png", dpi=200)
plt.close(fig)
print("done")
