"""Figures for the NCAR (GDEX d010111) inquiry: RCP4.5 historical VIC run vs. RCP4.5 met forcing.

Uses only the PUBLISHED release downloaded from GDEX (monthly files; daily files MD5-verified
against the Feb 2023 NCAR wget checksums).

Figure 1  <model>: domain-mean annual precipitation 1950-2099 from VIC wf PRCP (RCP4.5, RCP8.5) and
          BCSD met pcp (RCP4.5, RCP8.5), plus the per-year share of land cells where VIC RCP4.5
          PRCP equals each met scenario's pcp (annual totals within 0.5 mm).
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

# ---------------- Figure 1: time series + agreement
rows = []
for y in YEARS:
    v45, v85 = wf(MODEL, "rcp45", y, "PRCP"), wf(MODEL, "rcp85", y, "PRCP")
    m45, m85 = met_pcp(MODEL, "rcp45", y), met_pcp(MODEL, "rcp85", y)
    rows.append({"year": y, "vic45": np.nanmean(v45[land]), "vic85": np.nanmean(v85[land]),
                 "met45": np.nanmean(m45[land]), "met85": np.nanmean(m85[land]),
                 "agree_met45": np.mean(np.abs(v45 - m45)[land] < 0.5),
                 "agree_met85": np.mean(np.abs(v45 - m85)[land] < 0.5)})
ts = pd.DataFrame(rows)
ts.to_csv(OUT / f"timeseries_{MODEL}.csv", index=False)
switch = ts.loc[ts.agree_met45 > 0.9, "year"].min()
last_shared = ts.loc[(ts.year < switch) & (ts.agree_met85 > 0.9), "year"].max()
print(f"{MODEL}: VIC RCP4.5 PRCP matches RCP8.5 met through {last_shared}; matches RCP4.5 met from {switch}")

fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.5, 6.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
lab = {"vic45": "VIC output PRCP, RCP4.5 files", "vic85": "VIC output PRCP, RCP8.5 files",
       "met45": "BCSD met pcp, RCP4.5 files", "met85": "BCSD met pcp, RCP8.5 files (hidden: identical to orange)"}
for k, lw, ls in [("met45", 2, "-"), ("met85", 2, "-"), ("vic85", 2, "-"), ("vic45", 2, (0, (3, 2)))]:
    a1.plot(ts.year, ts[k], color=C[k], lw=lw, ls=ls, label=lab[k])
a1.axvspan(1950, switch - 0.5, color=GRID, alpha=0.6, lw=0)
a1.text(1951, a1.get_ylim()[1], f"1950–{switch - 1}: VIC RCP4.5 output = VIC RCP8.5 output,\n"
        f"forced by RCP8.5 met, not RCP4.5 met", va="top", fontsize=8.5, color=INK)
a1.set_ylabel("Domain-mean annual precipitation (mm)")
a1.set_title(f"{MODEL}: precipitation in VIC output vs. BCSD forcing files (GDEX d010111)",
             loc="left", fontsize=10.5)
a1.legend(frameon=False, fontsize=8, loc="lower right", ncol=2)
a1.grid(axis="y", color=GRID, lw=0.6)

a2.plot(ts.year, ts.agree_met85 * 100, color=C["met85"], lw=2, label="matches RCP8.5 met")
a2.plot(ts.year, ts.agree_met45 * 100, color=C["met45"], lw=2, label="matches RCP4.5 met")
a2.axvspan(1950, switch - 0.5, color=GRID, alpha=0.6, lw=0)
a2.set_ylabel("% of land cells where\nVIC RCP4.5 PRCP equals\nmet pcp (±0.5 mm/yr)")
a2.set_ylim(-5, 105)
a2.set_xlim(1950, 2099)
a2.legend(frameon=False, fontsize=8, loc="center right")
a2.grid(axis="y", color=GRID, lw=0.6)
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
