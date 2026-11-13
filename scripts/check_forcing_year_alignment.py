"""Which met-forcing year drove each VIC output year?

For each model and scenario, match every year's VIC wf PRCP field (mm/month, 12 x cells) against
the BCSD met pcp field (mm/day x days in month) for every candidate year and scenario. Reports the
best-matching (scenario, year) and its median abs difference. Exact (rounding-level) matches identify
the forcing year.

Motivation: in the RCP4.5 historical period, VIC PRCP does not match the RCP4.5 met pcp that SNAP
curates as `pcp`; the 1980s VIC PRCP equals the 1950s met pcp.

Usage:
  python check_forcing_year_alignment.py <vic_monthly_dir> <met_monthly_dir> <out_csv> [models...]
    preliminary: /beegfs/CMIP6/cparr4/AK_NCAR_12km/{vic_hydro,met}/monthly
    published  : /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/{vic,met}/monthly   (GDEX d010111)
"""

import calendar
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

VIC, MET, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
MODELS = sys.argv[4:] or ["ACCESS1-3", "CCSM4", "MIROC5", "HadGEM2-ES"]
YEARS = range(1950, 2100)
rng = np.random.default_rng(0)

with xr.open_dataset(VIC / "BCSD/CCSM4/rcp85/CCSM4_rcp85_BCSD_wf_2050.nc",
                     decode_times=False) as ds:
    land = ds.RUNOFF.values[0] > -999
iy, ix = np.nonzero(land)
pick = rng.choice(len(iy), 400, replace=False)  # sample of land cells
iy, ix = iy[pick], ix[pick]

# met monthly pcp units: the preliminary files have no units attribute and store a mean daily rate
# (verified: x days-in-month reproduces VIC PRCP for RCP8.5). Honour an explicit attribute if present.
with xr.open_dataset(MET / "BCSD/CCSM4/rcp85/CCSM4_rcp85_BCSD_met_2050.nc", decode_times=False) as ds:
    PCP_UNITS = ds.pcp.attrs.get("units", "")
PCP_IS_RATE = not PCP_UNITS or "day" in PCP_UNITS.lower() or "/d" in PCP_UNITS.lower()
print(f"met pcp units attr: {PCP_UNITS!r} -> treating as {'daily rate' if PCP_IS_RATE else 'monthly total'}",
      flush=True)


def met_field(m, s, y):
    with xr.open_dataset(MET / f"BCSD/{m}/{s}/{m}_{s}_BCSD_met_{y}.nc", decode_times=False) as ds:
        days = np.array([calendar.monthrange(y, k)[1] for k in range(1, 13)])[:, None]
        v = ds.pcp.values[:, iy, ix]
        return v * days if PCP_IS_RATE else v  # (12, cells) mm/month


def wf_field(m, s, y):
    with xr.open_dataset(VIC / f"BCSD/{m}/{s}/{m}_{s}_BCSD_wf_{y}.nc", decode_times=False) as ds:
        return ds.PRCP.values[:, iy, ix]


rows = []
for m in MODELS:
    met = {(s, y): met_field(m, s, y) for s in ["rcp45", "rcp85"] for y in YEARS}
    keys = list(met)
    M = np.stack([met[k] for k in keys])  # (n, 12, cells)
    for s in ["rcp45", "rcp85"]:
        for y in YEARS:
            w = wf_field(m, s, y)
            # compare Feb-agnostic: leap-year day counts can differ between matched years, so
            # use all months except February for the match score
            idx = [0] + list(range(2, 12))
            # median over months x cells: robust to cells where VIC adjusts precip (e.g. elevation bands)
            err = np.nanmedian(np.abs(M[:, idx] - w[None, idx]).reshape(len(keys), -1), axis=1)
            best = int(np.nanargmin(err))
            same = keys.index((s, y))
            rows.append({"model": m, "vic_scenario": s, "vic_year": y,
                         "best_met_scenario": keys[best][0], "best_met_year": keys[best][1],
                         "best_medabs_mm": float(err[best]),
                         "same_label_medabs_mm": float(err[same])})
    print(m, "done", flush=True)

df = pd.DataFrame(rows)
df["offset_years"] = df.vic_year - df.best_met_year
df["aligned"] = (df.best_met_scenario == df.vic_scenario) & (df.offset_years == 0)
df.round(3).to_csv(OUT, index=False)
pd.set_option("display.width", 200)
g = df.groupby(["model", "vic_scenario", "best_met_scenario", "offset_years"]).agg(
    n=("vic_year", "size"), first=("vic_year", "min"), last=("vic_year", "max"),
    worst_match_mm=("best_medabs_mm", "max"))
print(g.to_string())
