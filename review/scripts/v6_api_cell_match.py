"""Verification job 6: which raw VIC cell does the API serve at each test point?

The curated product is reprojected to EPSG:3338 before it is served, so the API's value at a
point need not come from the nearest cell on NCAR's native grid. For each test point, model,
scenario and decade (1980s-2000s, 2070s-2090s), compute the decadal mean of monthly RUNOFF and
EVAP for the 3x3 neighbourhood of the nearest native cell and compare each neighbour with the
API's `runoff` and `evap` (whole-mm). Reports the best-matching neighbour per point.

Usage: python v6_api_cell_match.py <gdex_root> <cache_dir> <out_csv> [n_workers]
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT, CACHE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
NW = int(sys.argv[4]) if len(sys.argv) > 4 else 8
MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79)}
DECADES = ["1980-1989", "1990-1999", "2000-2009", "2070-2079", "2080-2089", "2090-2099"]
MO = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
VARS = {"RUNOFF": "runoff", "EVAP": "evap", "BASEFLOW": None}

ref = ROOT / "vic/monthly/BCSD/CCSM4/rcp85/CCSM4_rcp85_BCSD_wf_2050.nc"
with xr.open_dataset(ref, decode_times=False) as ds:
    lat, lon = ds.latitude.values, ds.longitude.values
    land = np.isfinite(ds.PRCP.values[0])
cells = {}
for n, (pla, plo) in POINTS.items():
    la, lo, pa, po = map(np.deg2rad, (lat, lon, pla, plo))
    d = np.arccos(np.clip(np.sin(la) * np.sin(pa) + np.cos(la) * np.cos(pa) * np.cos(lo - po), -1, 1))
    cells[n] = np.unravel_index(int(np.argmin(np.where(land, d, np.inf))), d.shape)


def task(args):
    model, scen, dec = args
    y0, y1 = map(int, dec.split("-"))
    acc = {v: [] for v in VARS}
    for y in range(y0, y1 + 1):
        p = ROOT / f"vic/monthly/BCSD/{model}/{scen}/{model}_{scen}_BCSD_wf_{y}.nc"
        with xr.open_dataset(p, decode_times=False) as ds:
            for v in VARS:
                a = ds[v].values
                acc[v].append({n: a[:, iy - 1:iy + 2, ix - 1:ix + 2] for n, (iy, ix) in cells.items()})
    out = []
    for n in POINTS:
        for v in VARS:
            dm = np.mean([a[n] for a in acc[v]], axis=0)  # (12, 3, 3)
            for dy in range(3):
                for dx in range(3):
                    out.append(dict(point=n, model=model, scenario=scen, decade=dec, var=v, dy=dy - 1, dx=dx - 1,
                                    **{f"m{i+1}": float(dm[i, dy, dx]) for i in range(12)}))
    return out


if __name__ == "__main__":
    api = {p: json.load(open(CACHE / f"vic_{p}.json")) for p in POINTS}
    tasks = [(m, s, d) for m in MODELS for s in ("rcp45", "rcp85") for d in DECADES]
    rows = []
    with ProcessPoolExecutor(NW) as ex:
        for r in ex.map(task, tasks):
            rows += r
    raw = pd.DataFrame(rows)
    mcols = [f"m{i}" for i in range(1, 13)]
    res = []
    for _, r in raw[raw["var"].isin(["RUNOFF", "EVAP"])].iterrows():
        a = np.array([float(api[r.point][r.model][r.scenario][mo][r.decade][VARS[r["var"]]]) for mo in MO])
        d = np.abs(a - r[mcols].values.astype(float))
        res.append(dict(point=r.point, model=r.model, scenario=r.scenario, decade=r.decade, var=r["var"], dy=r.dy, dx=r.dx,
                        max_abs_diff=float(d.max()), n_within_0p5=int((d <= 0.5 + 1e-6).sum()), raw_annual=float(r[mcols].sum()), api_annual=float(a.sum())))
    res = pd.DataFrame(res)
    res.to_csv(OUT, index=False)
    raw.to_csv(OUT.replace(".csv", "_raw_neighbourhood.csv"), index=False)
    print("Per point: share of (model, scenario, decade, var) combos with all 12 months within 0.5 mm, by neighbour offset (dy, dx):")
    tab = res.assign(ok=res.n_within_0p5 == 12).groupby(["point", "dy", "dx"]).ok.mean().unstack(["dy", "dx"]).round(3)
    print(tab.to_string())
    best = res.assign(ok=res.n_within_0p5 == 12).groupby(["point", "dy", "dx"]).ok.mean().reset_index().sort_values("ok", ascending=False).groupby("point").head(1)
    print("\nBest neighbour per point:"); print(best.to_string(index=False))
    for n, (iy, ix) in cells.items():
        b = best[best.point == n].iloc[0]
        print(f"{n}: nearest native cell (iy,ix)=({iy},{ix}) lat/lon=({lat[iy,ix]:.3f},{lon[iy,ix]:.3f}); API matches offset ({int(b.dy)},{int(b.dx)}) -> ({lat[iy+int(b.dy),ix+int(b.dx)]:.3f},{lon[iy+int(b.dy),ix+int(b.dx)]:.3f}) in {b.ok:.0%} of combos")
