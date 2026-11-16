"""Figures for the NCAR (GDEX d010111) inquiry: RCP4.5 historical VIC run vs. RCP4.5 met forcing.

Uses only the PUBLISHED release downloaded from GDEX (monthly files; daily files MD5-verified
against the Feb 2023 NCAR wget checksums).

Figure 1  <model>, 1950-2099, as differences between files (mean over land cells of the per-cell
          |difference| in annual totals; zero = identical files):
            a. met pcp RCP4.5 vs RCP8.5, and VIC RUNOFF RCP4.5 vs RCP8.5
            b. VIC RCP4.5 PRCP vs met pcp RCP4.5, and vs met pcp RCP8.5
Figure 2  <model>, one year: per-cell annual totals - VIC RCP4.5 PRCP vs met RCP4.5 pcp, vs met
          RCP8.5 pcp, and VIC RCP4.5 RUNOFF vs VIC RCP8.5 RUNOFF.
Figure 3  all models: which met scenario VIC RCP4.5 PRCP matches, per year (from the alignment CSV
          written by check_forcing_year_alignment.py).

Usage: python fig_ncar_historical_forcing.py <gdex_root> <alignment_csv> <out_dir> [model] [year]
"""

import calendar
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

ROOT, ALIGN, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
MODEL = sys.argv[4] if len(sys.argv) > 4 else "ACCESS1-3"
YEAR = int(sys.argv[5]) if len(sys.argv) > 5 else 1985
OUT.mkdir(parents=True, exist_ok=True)
YEARS = range(1950, 2100)

# reference palette (dataviz skill, light mode)
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
C = {"vic45": "#2a78d6", "vic85": "#eb6834", "met45": "#1baf7a", "met85": "#eda100"}
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "axes.edgecolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})


def wf(m, s, y, var):
    with xr.open_dataset(ROOT / f"vic/monthly/BCSD/{m}/{s}/{m}_{s}_BCSD_wf_{y}.nc", decode_times=False) as ds:
        return ds[var].values.sum(axis=0)  # mm/yr


def met_pcp(m, s, y):
    with xr.open_dataset(ROOT / f"met/monthly/BCSD/{m}/{s}/{m}_{s}_BCSD_met_{y}.nc", decode_times=False) as ds:
        v = ds.pcp.values.astype("float64")
        units = ds.pcp.attrs.get("units", "")
    if not units or "day" in units.lower():  # monthly mean daily rate -> monthly total
        v = v * np.array([calendar.monthrange(y, k)[1] for k in range(1, v.shape[0] + 1)])[:, None, None]
    return v.sum(axis=0)  # note: HadGEM2-ES 2005 has 11 months (not used for ACCESS1-3)


land = np.isfinite(wf(MODEL, "rcp85", 2050, "RUNOFF"))

# ---------------- Figure 1: differences, not overlapping levels
# Every line is a per-cell absolute difference between two files, averaged over land cells
# (mm/yr of annual totals). Zero means the two files are identical cell for cell, so "same data"
# shows up as a line on the zero axis instead of one line hidden under another.
rows = []
for y in YEARS:
    v45 = wf(MODEL, "rcp45", y, "PRCP")
    r45, r85 = wf(MODEL, "rcp45", y, "RUNOFF"), wf(MODEL, "rcp85", y, "RUNOFF")
    m45, m85 = met_pcp(MODEL, "rcp45", y), met_pcp(MODEL, "rcp85", y)
    ok = land & np.isfinite(v45) & np.isfinite(r45) & np.isfinite(r85) & np.isfinite(m45) & np.isfinite(m85)
    rows.append({"year": y,
                 "d_met45_met85": np.mean(np.abs(m45 - m85)[ok]),      # forcing: RCP4.5 vs RCP8.5
                 "d_runoff45_runoff85": np.mean(np.abs(r45 - r85)[ok]),  # VIC output: RCP4.5 vs RCP8.5
                 "d_vic45_met45": np.mean(np.abs(v45 - m45)[ok]),      # RCP4.5 VIC PRCP vs RCP4.5 forcing
                 "d_vic45_met85": np.mean(np.abs(v45 - m85)[ok]),      # RCP4.5 VIC PRCP vs RCP8.5 forcing
                 "agree_met45": np.mean(np.abs(v45 - m45)[ok] < 0.5),
                 "agree_met85": np.mean(np.abs(v45 - m85)[ok] < 0.5),
                 "n_cells": int(ok.sum())})
ts = pd.DataFrame(rows)
ts.to_csv(OUT / f"timeseries_{MODEL}.csv", index=False)
switch = ts.loc[ts.agree_met45 > 0.9, "year"].min()
last_shared = ts.loc[(ts.year < switch) & (ts.agree_met85 > 0.9), "year"].max()
print(f"{MODEL}: VIC RCP4.5 PRCP matches RCP8.5 met through {last_shared}; matches RCP4.5 met from {switch}")
pre = ts.year < switch
print(ts.loc[pre, ["d_met45_met85", "d_runoff45_runoff85", "d_vic45_met45", "d_vic45_met85"]]
      .agg(["mean", "max"]).round(2).to_string())

fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.5, 5.8), sharex=True)
for ax in (a1, a2):
    ax.axvspan(1949.5, switch - 0.5, color=GRID, alpha=0.6, lw=0)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_xlim(1950, 2099)
    ax.text(1951, 0.97, f"1950–{switch - 1}", transform=ax.get_xaxis_transform(), fontsize=8.5,
            color=INK2, va="top")

# Panel a: the forcing files differ between scenarios, the VIC output does not (until the switch)
a1.plot(ts.year, ts.d_met45_met85, color=INK2, lw=2,
        label="BCSD forcing precipitation (met pcp): RCP4.5 file vs RCP8.5 file")
a1.plot(ts.year, ts.d_runoff45_runoff85, color=C["vic45"], lw=2,
        label="VIC output runoff (wf RUNOFF): RCP4.5 file vs RCP8.5 file")
a1.set_title(f"a. The two scenarios' forcing differs, but their VIC output is identical through {switch - 1}",
             loc="left", fontsize=10)
a1.set_ylim(-0.04 * ts.d_met45_met85.max(), 1.3 * ts.d_met45_met85.max())
a1.legend(frameon=False, fontsize=8, loc="upper right", ncol=1)
a1.set_ylabel("Mean |difference|\n(mm/yr)")

# Panel b: which forcing reproduces the RCP4.5 VIC precipitation
a2.plot(ts.year, ts.d_vic45_met45, color=C["met45"], lw=2, label="VIC PRCP (RCP4.5 wf file) vs RCP4.5 forcing (met pcp, RCP4.5 file)")
a2.plot(ts.year, ts.d_vic45_met85, color=C["met85"], lw=2, label="VIC PRCP (RCP4.5 wf file) vs RCP8.5 forcing (met pcp, RCP8.5 file)")
a2.set_title(f"b. Precipitation inside the RCP4.5 VIC run (wf PRCP) matches the RCP8.5 forcing through {switch - 1}",
             loc="left", fontsize=10)
_top = max(ts.d_vic45_met45.max(), ts.d_vic45_met85.max())
a2.set_ylim(-0.04 * _top, 1.3 * _top)
a2.legend(frameon=False, fontsize=8, loc="upper right")
a2.set_ylabel("Mean |difference|\n(mm/yr)")
a2.set_xlabel("Year")

fig.suptitle(f"{MODEL}, GDEX d010111 (Alaska). Each line: per-cell |difference| in annual totals between two "
             f"files,\naveraged over {int(ts.n_cells.median()):,} land cells. A line at zero means the two files "
             f"are identical.", x=0.01, ha="left", fontsize=9, color=INK2)
fig.tight_layout()
fig.savefig(OUT / f"fig1_timeseries_{MODEL}.png", dpi=200)
plt.close(fig)

# ---------------- Figure 2: one-year scatter
_f = {k: f for k, f in [("v45", wf(MODEL, "rcp45", YEAR, "PRCP")), ("v85", wf(MODEL, "rcp85", YEAR, "PRCP")),
                         ("m45", met_pcp(MODEL, "rcp45", YEAR)), ("m85", met_pcp(MODEL, "rcp85", YEAR)),
                         ("r45", wf(MODEL, "rcp45", YEAR, "RUNOFF")), ("r85", wf(MODEL, "rcp85", YEAR, "RUNOFF"))]}
ok = land.copy()
for f in _f.values():
    ok &= np.isfinite(f)
v45, v85, m45, m85, r45, r85 = (_f[k][ok] for k in ["v45", "v85", "m45", "m85", "r45", "r85"])
stats2 = {}
fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.7))
panels = [
    (m45, v45, f"BCSD met pcp, RCP4.5 file, {YEAR} (mm)", f"VIC PRCP, RCP4.5 file, {YEAR} (mm)", C["met45"]),
    (m85, v45, f"BCSD met pcp, RCP8.5 file, {YEAR} (mm)", f"VIC PRCP, RCP4.5 file, {YEAR} (mm)", C["met85"]),
    (r85, r45, f"VIC RUNOFF, RCP8.5 file, {YEAR} (mm)", f"VIC RUNOFF, RCP4.5 file, {YEAR} (mm)", C["vic85"]),
]
for ax, (x, y, xl, yl, col) in zip(axs, panels):
    lim = np.nanpercentile(np.r_[x, y], 99.5)
    ax.plot([0, lim], [0, lim], color=INK2, lw=0.8, zorder=1)
    ax.scatter(x, y, s=3, color=col, alpha=0.5, lw=0, zorder=2)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.set_aspect("equal")
    ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)
    d = np.abs(x - y)
    stats2[yl + " vs " + xl] = (np.mean(d < 0.5) * 100, np.median(d))
    ax.set_title(f"{np.mean(d < 0.5) * 100:.0f}% of cells equal (±0.5 mm)\nmedian |diff| {np.median(d):.1f} mm",
                 fontsize=8.5, loc="left")
for k, (pct, med) in stats2.items():
    print(f"fig2 {k}: {pct:.1f}% equal, median |diff| {med:.2f} mm")
fig.suptitle(f"{MODEL}, {YEAR}: each point is one land grid cell ({ok.sum():,} cells); line is 1:1",
             x=0.01, ha="left", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / f"fig2_scatter_{MODEL}_{YEAR}.png", dpi=200)
plt.close(fig)

# ---------------- Figure 3: all models, which forcing VIC RCP4.5 matches each year
al = pd.read_csv(ALIGN)
al = al[al.vic_scenario == "rcp45"].copy()
code = np.where((al.best_medabs_mm < 0.1) & (al.offset_years == 0) & (al.best_met_scenario == "rcp85"), 0,
       np.where((al.best_medabs_mm < 0.1) & (al.offset_years == 0) & (al.best_met_scenario == "rcp45"), 1, 2))
al["code"] = code
models = sorted(al.model.unique(), key=str.lower)
mat = np.full((len(models), len(YEARS)), np.nan)
for i, m in enumerate(models):
    s = al[al.model == m].set_index("vic_year").code
    mat[i] = [s.get(y, np.nan) for y in YEARS]
from matplotlib.colors import ListedColormap
cmap = ListedColormap([C["met85"], C["met45"], "#c9c8c2"])
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.imshow(mat, aspect="auto", cmap=cmap, vmin=-0.5, vmax=2.5, interpolation="nearest",
          extent=[1949.5, 2099.5, len(models) - 0.5, -0.5])
ax.set_yticks(range(len(models)), models, fontsize=8)
ax.set_xlabel("Year")
ax.set_title("Which BCSD forcing reproduces VIC PRCP in the RCP4.5 files? (all 10 GCMs)", loc="left", fontsize=10.5)
from matplotlib.patches import Patch
handles = [Patch(color=C["met85"], label="RCP8.5 met, same year (exact)"),
           Patch(color=C["met45"], label="RCP4.5 met, same year (exact)")]
if np.nanmax(mat) == 2:
    handles.append(Patch(color="#c9c8c2", label="no exact same-year match"))
ax.legend(handles=handles,
          frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3)
for sp in ax.spines.values():
    sp.set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig3_all_models_rcp45_forcing.png", dpi=200)
plt.close(fig)

summ = (al.assign(match=np.select([al.code == 0, al.code == 1], ["rcp85_met", "rcp45_met"], "none"))
        .groupby(["model", "match"]).vic_year.agg(["min", "max", "size"]))
summ.to_csv(OUT / "rcp45_forcing_match_summary.csv")
print(summ.to_string())
