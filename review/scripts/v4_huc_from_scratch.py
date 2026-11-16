"""Verification job 4: recompute a few opposite-sign HUC8s straight from the raw monthly files.

Independent of the climatology pipeline: for each HUC8 given, find its member VIC cells (cell
centre inside the polygon), then for each GCM (RCP8.5) and each year of 1980-2009 and
2070-2099 read the monthly wf file and take the area-weighted HUC mean of annual RUNOFF and
BASEFLOW. Reports period means, % change per model, two ensemble definitions, and the
interannual standard deviation, so near-zero changes can be judged against noise.

Usage: python v4_huc_from_scratch.py <gdex_root> <huc8.gpkg> <out_csv> [huc8_id ...]
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer
from shapely.geometry import Point

ROOT, GPKG, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
HUCS = sys.argv[4:] or ["19010304", "19020701", "19060501", "19010204"]
MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
PERIODS = {"hist": range(1980, 2010), "late": range(2070, 2100)}

ref = ROOT / "vic/monthly/BCSD/CCSM4/rcp85/CCSM4_rcp85_BCSD_wf_2050.nc"
with xr.open_dataset(ref, decode_times=False) as ds:
    lat, lon = ds.latitude.values, ds.longitude.values
    land = np.isfinite(ds.PRCP.values[0])
# true cell area from the polar-stereographic map factor (true at 64N)
k = (1 + np.sin(np.deg2rad(64))) / (1 + np.sin(np.deg2rad(lat)))
area = (12.0 / k) ** 2  # km2

hucs = gpd.read_file(GPKG)
hucs = hucs[hucs.huc8.isin(HUCS)].to_crs("EPSG:4326")
iy, ix = np.nonzero(land)
pts = gpd.GeoSeries([Point(float(lon[i, j]), float(lat[i, j])) for i, j in zip(iy, ix)], crs="EPSG:4326")
members = {}
for _, h in hucs.iterrows():
    inside = pts.within(h.geometry).values
    members[h.huc8] = (h["name"], iy[inside], ix[inside])
    print(h.huc8, h["name"], "cells:", int(inside.sum()))

rows = []
for m in MODELS:
    for per, years in PERIODS.items():
        for y in years:
            p = ROOT / f"vic/monthly/BCSD/{m}/rcp85/{m}_rcp85_BCSD_wf_{y}.nc"
            with xr.open_dataset(p, decode_times=False) as ds:
                ro = ds.RUNOFF.values.sum(axis=0)
                bf = ds.BASEFLOW.values.sum(axis=0)
            for h, (name, hy, hx) in members.items():
                w = area[hy, hx]
                rows.append(dict(huc8=h, name=name, model=m, period=per, year=y,
                                 RO=float(np.average(ro[hy, hx], weights=w)), BF=float(np.average(bf[hy, hx], weights=w))))
    print(m, "done", flush=True)
df = pd.DataFrame(rows)
df["TOT"] = df.RO + df.BF
out = []
for (h, name), g in df.groupby(["huc8", "name"]):
    pm = g.groupby(["model", "period"])[["RO", "BF", "TOT"]].mean().unstack("period")
    sd = g[g.period == "hist"].groupby("model")[["RO", "TOT"]].std()
    dRO = 100 * (pm[("RO", "late")] / pm[("RO", "hist")] - 1)
    dTOT = 100 * (pm[("TOT", "late")] / pm[("TOT", "hist")] - 1)
    ens_ro = 100 * (pm[("RO", "late")].mean() / pm[("RO", "hist")].mean() - 1)
    ens_tot = 100 * (pm[("TOT", "late")].mean() / pm[("TOT", "hist")].mean() - 1)
    out.append(dict(huc8=h, name=name, n_cells=len(members[h][1]),
                    RO_hist_mm=round(pm[("RO", "hist")].mean(), 1), BF_hist_mm=round(pm[("BF", "hist")].mean(), 1),
                    dRO_pct_of_ens_mean=round(ens_ro, 1), dTOT_pct_of_ens_mean=round(ens_tot, 1),
                    dRO_pct_mean_of_models=round(dRO.mean(), 1), dTOT_pct_mean_of_models=round(dTOT.mean(), 1),
                    dRO_pct_min=round(dRO.min(), 1), dRO_pct_max=round(dRO.max(), 1),
                    dTOT_pct_min=round(dTOT.min(), 1), dTOT_pct_max=round(dTOT.max(), 1),
                    n_models_RO_down=int((dRO < 0).sum()), n_models_TOT_up=int((dTOT > 0).sum()),
                    interannual_sd_RO_pct=round(100 * (sd.RO / pm[("RO", "hist")]).mean(), 1),
                    interannual_sd_TOT_pct=round(100 * (sd.TOT / pm[("TOT", "hist")]).mean(), 1)))
res = pd.DataFrame(out)
res.to_csv(OUT, index=False)
df.to_csv(str(OUT).replace(".csv", "_annual.csv"), index=False)
print(res.to_string())
