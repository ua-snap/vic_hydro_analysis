"""Which raw NCAR run does each curated /hydrology value come from?

For each point (cached /hydrology/point JSON), model, scenario and decade, compare the API's
decadal annual totals of `runoff` and `pcp` with the raw monthly wf RUNOFF and PRCP from the
RCP4.5 and RCP8.5 runs at the nearest VIC cell. Flags which raw scenario each API value matches.

Background: NCAR's raw RCP4.5 and RCP8.5 runs differ even in historical years (separate BCSD per
scenario), but the API's historical hydrology looked identical across scenarios.

Usage: python check_api_vs_raw.py <monthly_dir> <api_cache_dir> <out_csv>
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

MONTHLY, CACHE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79)}
MO = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DECADES = list(range(1950, 2100, 10))

ref = MONTHLY / "BCSD/CCSM4/rcp85/CCSM4_rcp85_BCSD_wf_2050.nc"
with xr.open_dataset(ref, decode_times=False) as ds:
    lat, lon = ds.latitude.values, ds.longitude.values
    land = ds.RUNOFF.values[0] > -999
cells = {}
for name, (plat, plon) in POINTS.items():
    d = np.where(land, (lat - plat) ** 2 + ((lon - plon) * np.cos(np.deg2rad(plat))) ** 2, np.inf)
    cells[name] = np.unravel_index(np.argmin(d), d.shape)
iys = np.array([c[0] for c in cells.values()])
ixs = np.array([c[1] for c in cells.values()])

api = {n: json.loads((CACHE / f"vic_{n}.json").read_text()) for n in POINTS}
models = list(api["Fairbanks"])

rows = []
for m in models:
    raw = {}  # (scenario, decade) -> {var: array over points}
    for s in ["rcp45", "rcp85"]:
        for dec in DECADES:
            acc = {"RUNOFF": [], "PRCP": []}
            for y in range(dec, dec + 10):
                with xr.open_dataset(MONTHLY / f"BCSD/{m}/{s}/{m}_{s}_BCSD_wf_{y}.nc",
                                     decode_times=False) as ds:
                    for v in acc:
                        acc[v].append(ds[v].values[:, iys, ixs].sum(axis=0))
            raw[(s, dec)] = {v: np.mean(acc[v], axis=0) for v in acc}
    for pi, name in enumerate(POINTS):
        for s in ["rcp45", "rcp85"]:
            for dec in DECADES:
                k = f"{dec}-{dec + 9}"
                rec = api[name][m][s]
                r = {"model": m, "point": name, "scenario": s, "decade": k}
                for apiv, rawv in [("runoff", "RUNOFF"), ("pcp", "PRCP")]:
                    vals = [rec[x][k][apiv] for x in MO]
                    a = np.nan if any(v is None for v in vals) else sum(float(v) for v in vals)
                    r[f"api_{apiv}"] = a
                    r[f"raw45_{rawv}"] = raw[("rcp45", dec)][rawv][pi]
                    r[f"raw85_{rawv}"] = raw[("rcp85", dec)][rawv][pi]
                    # tolerance: API = decadal mean of monthly totals, each rounded to whole mm
                    tol = 6.0 + 0.01 * abs(a) if np.isfinite(a) else np.nan
                    d45 = abs(a - r[f"raw45_{rawv}"])
                    d85 = abs(a - r[f"raw85_{rawv}"])
                    r[f"{apiv}_matches"] = ("neither" if not np.isfinite(a) or min(d45, d85) > tol
                                            else "both" if max(d45, d85) <= tol
                                            else "rcp45" if d45 < d85 else "rcp85")
                rows.append(r)
    print(m, "done", flush=True)

df = pd.DataFrame(rows)
df.round(1).to_csv(OUT, index=False)
df["era"] = np.where(df.decade.str[:4].astype(int) < 2010, "1950-2009", "2010-2099")
pd.set_option("display.width", 200)
for v in ["runoff", "pcp"]:
    print(f"\n== API `{v}`: which raw scenario does it match? (counts over models x points x decades)")
    print(pd.crosstab([df.era, df.scenario], df[f"{v}_matches"]).to_string())
