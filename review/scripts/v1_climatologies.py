"""Verification job 1: period climatologies from NCAR's published monthly wf files (GDEX d010111).

Written independently of scripts/baseflow_analysis.py. For every run (10 GCMs x RCP4.5/RCP8.5,
plus the Daymet-forced run) and period (hist = 1980-2009, late = 2070-2099) it reads the 30
annual monthly files read-only, checks each file (12 months; the year in the time units equals
the filename year; no NaN on land) and writes:

  <out>/clim_<source>_<scenario>_<period>.nc  monthly climatology (12,y,x) of RUNOFF and
                                              BASEFLOW, and mean annual totals (y,x) of all six
                                              wf variables, plus latitude/longitude/land
  <out>/points_monthly.csv                    monthly values of all six variables, each year, at
                                              named cells (for the API comparison)
  <out>/file_checks.csv                       one row per file read

Usage: python v1_climatologies.py <gdex_root> <out_dir> [n_workers]
"""
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
NW = int(sys.argv[3]) if len(sys.argv) > 3 else 8
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
SCEN = ["rcp45", "rcp85"]
PERIODS = {"hist": list(range(1980, 2010)), "late": list(range(2070, 2100))}
VARS = ["RUNOFF", "BASEFLOW", "EVAP", "PRCP", "SNOW_MELT", "GLACIER_MELT"]
# named cells: the five API test points plus two regional spot-check sites
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79), "Umiat": (69.37, -152.14),
          "Ketchikan": (55.34, -131.65)}


def wf_path(src, scen, year):
    if src == "daymet":
        return ROOT / "vic/monthly/daymet" / f"daymet_wf_{year}.nc"
    return ROOT / f"vic/monthly/BCSD/{src}/{scen}" / f"{src}_{scen}_BCSD_wf_{year}.nc"


def nearest_land_cell(lat, lon, land, plat, plon):
    """Nearest land cell by great-circle distance (sphere)."""
    la, lo, pa, po = map(np.deg2rad, (lat, lon, plat, plon))
    d = np.arccos(np.clip(np.sin(la) * np.sin(pa) + np.cos(la) * np.cos(pa) * np.cos(lo - po), -1, 1))
    d = np.where(land, d, np.inf)
    return np.unravel_index(int(np.argmin(d)), d.shape)


def task(args):
    src, scen, period = args
    years = PERIODS[period]
    acc = cnt = None
    checks, pts = [], []
    for y in years:
        p = wf_path(src, scen, y)
        with xr.open_dataset(p, decode_times=False) as ds:
            t = ds.time.values
            m = re.search(r"since (\d{4})-", ds.time.attrs.get("units", ""))
            uy = int(m.group(1)) if m else -1
            data = np.stack([ds[v].values for v in VARS]).astype(np.float64)  # (6,12,y,x)
            if acc is None:
                land = np.isfinite(data[3, 0])
                lat, lon = ds.latitude.values, ds.longitude.values
                acc = np.zeros_like(data)
                cnt = np.zeros_like(data)
                cells = {n: nearest_land_cell(lat, lon, land, *ll) for n, ll in POINTS.items()}
        if data.shape[1] != 12:
            raise RuntimeError(f"{p}: {data.shape[1]} months")
        onland = data[:, :, land]
        checks.append(dict(source=src, scenario=scen, period=period, year=y, file=p.name,
                           n_months=len(t), units_year=uy, year_matches=(uy == y),
                           nan_on_land=int(np.isnan(onland).sum()), land_cells=int(land.sum()),
                           min_RUNOFF=float(np.nanmin(onland[0])), min_BASEFLOW=float(np.nanmin(onland[1])),
                           min_EVAP=float(np.nanmin(onland[2])), min_PRCP=float(np.nanmin(onland[3])),
                           max_GLACIER_MELT=float(np.nanmax(onland[5]))))
        fin = np.isfinite(data)
        acc += np.where(fin, data, 0.0)
        cnt += fin
        for name, (iy, ix) in cells.items():
            for vi, v in enumerate(VARS):
                pts.append([src, scen, period, y, name, int(iy), int(ix), float(lat[iy, ix]),
                            float(lon[iy, ix]), v] + [round(float(x), 4) for x in data[vi, :, iy, ix]])
    with np.errstate(invalid="ignore", divide="ignore"):
        clim = acc / cnt  # NaN where never finite (off land)
    ds_out = xr.Dataset(
        {"RUNOFF_mon": (("month", "y", "x"), clim[0].astype(np.float32)),
         "BASEFLOW_mon": (("month", "y", "x"), clim[1].astype(np.float32)),
         **{f"{v}_ann": (("y", "x"), clim[i].sum(axis=0).astype(np.float32)) for i, v in enumerate(VARS)},
         "latitude": (("y", "x"), lat), "longitude": (("y", "x"), lon),
         "land": (("y", "x"), land.astype(np.int8))},
        coords={"month": np.arange(1, 13)},
        attrs={"source": src, "scenario": scen, "period": period, "years": f"{years[0]}-{years[-1]}",
               "n_years": len(years), "note": "mean over years of monthly totals (mm/month); *_ann = sum of the 12 monthly means (mm/yr)"})
    ds_out.to_netcdf(OUT / f"clim_{src}_{scen}_{period}.nc", encoding={k: {"zlib": True, "complevel": 4} for k in ds_out.data_vars})
    return checks, pts


if __name__ == "__main__":
    tasks = [(m, s, p) for m in MODELS for s in SCEN for p in PERIODS] + [("daymet", "obs", "hist")]
    checks, pts = [], []
    with ProcessPoolExecutor(NW) as ex:
        for c, p in ex.map(task, tasks):
            checks += c
            pts += p
            print(c[0]["source"], c[0]["scenario"], c[0]["period"], "done", flush=True)
    chk = pd.DataFrame(checks)
    chk.to_csv(OUT / "file_checks.csv", index=False)
    cols = ["source", "scenario", "period", "year", "point", "iy", "ix", "cell_lat", "cell_lon", "var"] + [f"m{i}" for i in range(1, 13)]
    pd.DataFrame(pts, columns=cols).to_csv(OUT / "points_monthly.csv", index=False)
    print("files read:", len(chk), "| months!=12:", int((chk.n_months != 12).sum()),
          "| units year != filename year:", int((~chk.year_matches).sum()),
          "| files with NaN on land:", int((chk.nan_on_land > 0).sum()),
          "| land cells:", chk.land_cells.unique())
    print("min EVAP over all files:", chk.min_EVAP.min(), "| min RUNOFF:", chk.min_RUNOFF.min(),
          "| max monthly GLACIER_MELT (mm):", chk.max_GLACIER_MELT.max())
    print(chk.groupby(["source", "scenario", "period"]).year.agg(["count", "min", "max", "nunique"]).to_string())
