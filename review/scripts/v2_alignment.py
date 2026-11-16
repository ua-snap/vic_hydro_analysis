"""Verification job 2: RCP4.5 vs RCP8.5 files and VIC-precipitation vs met-forcing match.

Written independently of scripts/check_forcing_year_alignment.py. Part A reads, for every model
and every year 1950-2099, the four published monthly files (wf rcp45, wf rcp85, met rcp45, met
rcp85) and records:
  * max |RCP4.5 - RCP8.5| over land cells and months for each wf variable (RUNOFF, BASEFLOW,
    EVAP, PRCP, SNOW_MELT, GLACIER_MELT) and for met pcp, tmax, tmin, and the fraction of
    land cell-months that are bit-identical;
  * VIC PRCP (mm/month) vs met pcp (mm/day x days in month) for the four pairings
    (VIC45-met45, VIC45-met85, VIC85-met85, VIC85-met45): median and max |diff| over land;
  * file time lengths; per-cell max GLACIER_MELT and count of months > 0 over all files.
Also the Daymet run: VIC PRCP vs Daymet met pcp per year, and monthly values at named cells.
Part B (sample-based offset search, 3 models): for each VIC year, which (met scenario, met year)
best matches VIC PRCP at 300 random land cells; run on the published release and on the
preliminary release on beegfs, to test the release-comparison claims.

Outputs in <out>: alignment_published.csv, daymet_alignment.csv, points_met_monthly.csv,
glacier_allyears.nc, offset_search_published.csv, offset_search_preliminary.csv

Usage: python v2_alignment.py <gdex_root> <prelim_root> <out_dir> [n_workers]
"""
import calendar
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT, PRE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
NW = int(sys.argv[4]) if len(sys.argv) > 4 else 8
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
YEARS = list(range(1950, 2100))
WF = ["RUNOFF", "BASEFLOW", "EVAP", "PRCP", "SNOW_MELT", "GLACIER_MELT"]
MET = ["pcp", "tmax", "tmin"]
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79), "Umiat": (69.37, -152.14),
          "Ketchikan": (55.34, -131.65)}
OFFSET_MODELS = ["ACCESS1-3", "CanESM2", "MIROC5"]


def paths(root, model, scen, year):
    return (root / f"vic/monthly/BCSD/{model}/{scen}/{model}_{scen}_BCSD_wf_{year}.nc",
            root / f"met/monthly/BCSD/{model}/{scen}/{model}_{scen}_BCSD_met_{year}.nc")


def pub_paths(model, scen, year):
    return paths(ROOT, model, scen, year)


def prelim_paths(model, scen, year):
    return (PRE / f"vic_hydro/monthly/BCSD/{model}/{scen}/{model}_{scen}_BCSD_wf_{year}.nc",
            PRE / f"met/monthly/BCSD/{model}/{scen}/{model}_{scen}_BCSD_met_{year}.nc")


def dim(year):
    return np.array([calendar.monthrange(year, m)[1] for m in range(1, 13)], dtype=np.float64)


def nearest_land_cell(lat, lon, land, plat, plon):
    la, lo, pa, po = map(np.deg2rad, (lat, lon, plat, plon))
    d = np.arccos(np.clip(np.sin(la) * np.sin(pa) + np.cos(la) * np.cos(pa) * np.cos(lo - po), -1, 1))
    return np.unravel_index(int(np.argmin(np.where(land, d, np.inf))), d.shape)


def load(p, variables):
    with xr.open_dataset(p, decode_times=False) as ds:
        out = {v: ds[v].values.astype(np.float64) for v in variables}
        out["_t"] = ds.time.values
        out["_lat"], out["_lon"] = ds.latitude.values, ds.longitude.values
    return out


def stats(a, b, land):
    """median and max |a-b| over land for the months both have; fraction identical."""
    n = min(a.shape[0], b.shape[0])
    d = np.abs(a[:n][:, land] - b[:n][:, land])
    return float(np.nanmedian(d)), float(np.nanmax(d)), float(np.mean(d == 0)), n


def task(args):
    model, year = args
    wf45, met45 = paths(ROOT, model, "rcp45", year)
    wf85, met85 = paths(ROOT, model, "rcp85", year)
    w45, w85 = load(wf45, WF), load(wf85, WF)
    m45, m85 = load(met45, MET), load(met85, MET)
    land = np.isfinite(w85["PRCP"][0])
    row = dict(model=model, year=year, n_months_wf45=len(w45["_t"]), n_months_wf85=len(w85["_t"]),
               n_months_met45=len(m45["_t"]), n_months_met85=len(m85["_t"]),
               met_time_ok=bool(np.array_equal(m85["_t"][:12], np.cumsum(np.r_[0, dim(year)[:-1]])[:len(m85["_t"])])))
    for v in WF:
        med, mx, ident, _ = stats(w45[v], w85[v], land)
        row[f"maxabs_45v85_{v}"] = mx
        row[f"frac_identical_45v85_{v}"] = ident
    for v in MET:
        med, mx, ident, n = stats(m45[v], m85[v], land)
        row[f"maxabs_45v85_met_{v}"] = mx
    dm = dim(year)[:, None, None]
    for vs, w in (("45", w45), ("85", w85)):
        for ms, m in (("45", m45), ("85", m85)):
            med, mx, ident, n = stats(w["PRCP"], m["pcp"] * dm[:m["pcp"].shape[0]], land)
            row[f"medabs_vic{vs}_met{ms}"] = med
            row[f"maxabs_vic{vs}_met{ms}"] = mx
    gm = np.fmax(np.nan_to_num(w45["GLACIER_MELT"]), np.nan_to_num(w85["GLACIER_MELT"]))
    gm_max = gm.max(axis=0).astype(np.float32)
    gm_cnt = ((np.nan_to_num(w45["GLACIER_MELT"]) > 0).sum(axis=0) + (np.nan_to_num(w85["GLACIER_MELT"]) > 0).sum(axis=0)).astype(np.int32)
    cells = {n: nearest_land_cell(w85["_lat"], w85["_lon"], land, *ll) for n, ll in POINTS.items()}
    pts = []
    for name, (iy, ix) in cells.items():
        for scen, w, m in (("rcp45", w45, m45), ("rcp85", w85, m85)):
            for v in ("PRCP", "RUNOFF", "BASEFLOW"):
                pts.append([model, scen, year, name, iy, ix, "vic_" + v] + [round(float(x), 4) for x in w[v][:, iy, ix]] + [np.nan] * (12 - w[v].shape[0]))
            for v in MET:
                vals = m[v][:, iy, ix]
                pts.append([model, scen, year, name, iy, ix, "met_" + v] + [round(float(x), 4) for x in vals] + [np.nan] * (12 - len(vals)))
    return row, gm_max, gm_cnt, pts


def daymet_task(year):
    w = load(ROOT / f"vic/monthly/daymet/daymet_wf_{year}.nc", ["PRCP"])
    m = load(ROOT / f"met/monthly/daymet/daymet_met_{year}.nc", ["pcp"])
    land = np.isfinite(w["PRCP"][0])
    med, mx, ident, n = stats(w["PRCP"], m["pcp"] * dim(year)[:, None, None], land)
    return dict(year=year, n_months_wf=len(w["_t"]), n_months_met=len(m["_t"]), medabs_vic_met=med, maxabs_vic_met=mx)


def offset_search(pathfn, model, label, cells, rate_x_days=True):
    """For each VIC year, the (met scenario, met year) whose pcp best matches VIC PRCP at sample cells."""
    iy, ix = cells
    met = {}
    for scen in ("rcp45", "rcp85"):
        arr = np.full((len(YEARS), 12, len(iy)), np.nan)
        for k, y in enumerate(YEARS):
            _, mp = pathfn(model, scen, y)
            with xr.open_dataset(mp, decode_times=False) as ds:
                v = ds.pcp.values[:, iy, ix].astype(np.float64)
                if rate_x_days:
                    v = v * dim(y)[:v.shape[0], None]
                arr[k, :v.shape[0]] = v
        met[scen] = arr
    rows = []
    for scen in ("rcp45", "rcp85"):
        for k, y in enumerate(YEARS):
            wp, _ = pathfn(model, scen, y)
            with xr.open_dataset(wp, decode_times=False) as ds:
                vic = ds.PRCP.values[:, iy, ix].astype(np.float64)  # (12, n)
            best = None
            for ms in ("rcp45", "rcp85"):
                d = np.nanmedian(np.abs(met[ms] - vic[None]), axis=(1, 2))  # per met year
                j = int(np.nanargmin(d))
                if best is None or d[j] < best[2]:
                    best = (ms, YEARS[j], float(d[j]))
            same = float(np.nanmedian(np.abs(met[scen][k] - vic)))
            rows.append(dict(release=label, model=model, vic_scenario=scen, vic_year=y, best_met_scenario=best[0],
                             best_met_year=best[1], best_medabs_mm=round(best[2], 3), offset_years=best[1] - y,
                             same_label_same_year_medabs_mm=round(same, 3)))
    return rows


if __name__ == "__main__":
    # --- Part A: published release, all models and years (skipped if already done)
    tasks = [(m, y) for m in MODELS for y in YEARS]
    if (OUT / "glacier_allyears.nc").exists() and (OUT / "alignment_published.csv").exists():
        print("Part A outputs exist; skipping to Part B")
        tasks = []
    rows, pts = [], []
    gm_max = gm_cnt = None
    with ProcessPoolExecutor(NW) as ex:
      if tasks:
        for i, (row, gmx, gmc, p) in enumerate(ex.map(task, tasks, chunksize=5)):
            rows.append(row)
            pts += p
            gm_max = gmx if gm_max is None else np.fmax(gm_max, gmx)
            gm_cnt = gmc if gm_cnt is None else gm_cnt + gmc
            if (i + 1) % 150 == 0:
                print(row["model"], "done", flush=True)
        daymet = pd.DataFrame(list(ex.map(daymet_task, range(1980, 2017))))
    with xr.open_dataset(paths(ROOT, "CCSM4", "rcp85", 2050)[0], decode_times=False) as ds:
        lat, lon = ds.latitude.values, ds.longitude.values
        land = np.isfinite(ds.PRCP.values[0])
    if tasks:
        df = pd.DataFrame(rows)
        df.to_csv(OUT / "alignment_published.csv", index=False)
        daymet.to_csv(OUT / "daymet_alignment.csv", index=False)
        cols = ["model", "scenario", "year", "point", "iy", "ix", "var"] + [f"m{i}" for i in range(1, 13)]
        pd.DataFrame(pts, columns=cols).to_csv(OUT / "points_met_monthly.csv", index=False)
        xr.Dataset({"gm_max": (("y", "x"), gm_max), "gm_months_gt0": (("y", "x"), gm_cnt),
                    "latitude": (("y", "x"), lat), "longitude": (("y", "x"), lon), "land": (("y", "x"), land.astype(np.int8))},
                   attrs={"note": "max monthly GLACIER_MELT (mm/month) and number of months with GLACIER_MELT>0 over 10 GCMs x 2 RCPs x 1950-2099"}
                   ).to_netcdf(OUT / "glacier_allyears.nc")
    df = pd.read_csv(OUT / "alignment_published.csv")
    daymet = pd.read_csv(OUT / "daymet_alignment.csv")
    gm_cnt = xr.open_dataset(OUT / "glacier_allyears.nc").gm_months_gt0.values
    print("glacier cells (GLACIER_MELT>0 in any run/year):", int(((gm_cnt > 0) & land).sum()), "of", int(land.sum()))

    # summary: identical hydrology years, and which met each VIC scenario matches
    df["hydro_identical"] = (df[[f"maxabs_45v85_{v}" for v in WF]].max(axis=1) == 0)
    df["met_identical"] = (df[[f"maxabs_45v85_met_{v}" for v in MET]].max(axis=1) == 0)
    tol = 0.05  # mm/month; exact matches are ~0.01 from float32 rounding
    df["vic45_matches"] = np.select([df.medabs_vic45_met45 < tol, df.medabs_vic45_met85 < tol], ["met45", "met85"], "none")
    df["vic85_matches"] = np.select([df.medabs_vic85_met85 < tol, df.medabs_vic85_met45 < tol], ["met85", "met45"], "none")
    for m in MODELS:
        d = df[df.model == m]
        ident = d[d.hydro_identical].year
        print(f"{m}: hydrology identical rcp45=rcp85 for {len(ident)} years ({ident.min()}-{ident.max()});"
              f" met identical years: {int(d.met_identical.sum())};"
              f" VIC45 matches met85 for {d[d.vic45_matches=='met85'].year.min()}-{d[d.vic45_matches=='met85'].year.max()},"
              f" met45 for {d[d.vic45_matches=='met45'].year.min()}-{d[d.vic45_matches=='met45'].year.max()},"
              f" none: {int((d.vic45_matches=='none').sum())}; VIC85 none: {int((d.vic85_matches=='none').sum())}")
    print("Daymet: years with medabs>0.05:", int((daymet.medabs_vic_met > 0.05).sum()), "of", len(daymet))

    # --- Part B: offset search on published and preliminary releases (3 models)
    rng = np.random.default_rng(1)
    iy, ix = np.nonzero(land)
    pick = rng.choice(len(iy), 300, replace=False)
    cells = (iy[pick], ix[pick])
    res = []
    with ProcessPoolExecutor(min(NW, 6)) as ex:
        futs = [ex.submit(offset_search, pub_paths, m, "published", cells) for m in OFFSET_MODELS]
        futs += [ex.submit(offset_search, prelim_paths, m, "preliminary", cells) for m in OFFSET_MODELS]
        for f in futs:
            res += f.result()
    off = pd.DataFrame(res)
    off[off.release == "published"].to_csv(OUT / "offset_search_published.csv", index=False)
    off[off.release == "preliminary"].to_csv(OUT / "offset_search_preliminary.csv", index=False)
    off["exact"] = off.best_medabs_mm < 0.05
    print(off.groupby(["release", "model", "vic_scenario", "best_met_scenario", "offset_years", "exact"]).vic_year.agg(["count", "min", "max"]).to_string())
