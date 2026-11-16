"""Verification job 7: quantify the two exceptions to "RCP4.5 historical hydrology = RCP8.5 run".

v2 found (a) CCSM4: RCP4.5 and RCP8.5 share the same precipitation for 1950-2000 but the
hydrology differs in every year; (b) CanESM2: the RCP4.5 precipitation equals RCP8.5's through
2005 but the hydrology differs from 2001. For each year, this job reports the domain total of
RUNOFF, BASEFLOW and total runoff in the two runs, their % difference, and the share of
non-glacier and glacier cells whose annual RUNOFF differs by more than 1 mm.

Usage: python v7_run_exceptions.py <gdex_root> <glacier_allyears.nc> <out_csv>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT, GLAC, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
g = xr.open_dataset(GLAC)
land = g.land.values > 0
glac = (g.gm_months_gt0.values > 0) & land
nong = land & ~glac
lat = g.latitude.values
k = (1 + np.sin(np.deg2rad(64))) / (1 + np.sin(np.deg2rad(lat)))
area = (12.0 / k) ** 2
rows = []
for model, years in (("CCSM4", range(1950, 2011)), ("CanESM2", range(1995, 2011)), ("ACCESS1-3", range(1995, 2006))):
    for y in years:
        a = {}
        for s in ("rcp45", "rcp85"):
            with xr.open_dataset(ROOT / f"vic/monthly/BCSD/{model}/{s}/{model}_{s}_BCSD_wf_{y}.nc", decode_times=False) as ds:
                a[s] = {v: np.nan_to_num(ds[v].values.astype(float)).sum(axis=0) for v in ("RUNOFF", "BASEFLOW", "PRCP", "EVAP", "GLACIER_MELT")}
        r = dict(model=model, year=y)
        for v in ("RUNOFF", "BASEFLOW", "PRCP", "EVAP", "GLACIER_MELT"):
            t45, t85 = (a["rcp45"][v] * area)[land].sum(), (a["rcp85"][v] * area)[land].sum()
            r[f"{v}_pctdiff_domain"] = 100 * (t45 / t85 - 1) if t85 else np.nan
            d = np.abs(a["rcp45"][v] - a["rcp85"][v])
            r[f"{v}_frac_nonglacier_cells_diff_gt1mm"] = float(np.mean(d[nong] > 1))
            r[f"{v}_frac_glacier_cells_diff_gt1mm"] = float(np.mean(d[glac] > 1))
            r[f"{v}_median_absdiff_nonglacier_mm"] = float(np.median(d[nong]))
            r[f"{v}_p99_absdiff_nonglacier_mm"] = float(np.percentile(d[nong], 99))
        tot45 = ((a["rcp45"]["RUNOFF"] + a["rcp45"]["BASEFLOW"]) * area)[land].sum()
        tot85 = ((a["rcp85"]["RUNOFF"] + a["rcp85"]["BASEFLOW"]) * area)[land].sum()
        r["TOT_pctdiff_domain"] = 100 * (tot45 / tot85 - 1)
        rows.append(r)
    print(model, "done", flush=True)
df = pd.DataFrame(rows)
df.round(4).to_csv(OUT, index=False)
pd.set_option("display.width", 250)
cols = ["model", "year", "RUNOFF_pctdiff_domain", "BASEFLOW_pctdiff_domain", "TOT_pctdiff_domain", "PRCP_pctdiff_domain", "GLACIER_MELT_pctdiff_domain",
        "RUNOFF_frac_nonglacier_cells_diff_gt1mm", "RUNOFF_frac_glacier_cells_diff_gt1mm", "RUNOFF_p99_absdiff_nonglacier_mm"]
print(df[cols].round(3).to_string(index=False))
