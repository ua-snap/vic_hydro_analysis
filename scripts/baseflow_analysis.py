"""Baseflow vs surface runoff in the NCAR 12 km Alaska VIC run.

Answers the questions the two-pager leaves pending:
  1. What share of total runoff (surface RUNOFF + BASEFLOW) is baseflow: statewide, by season,
     by HUC8 watershed, and in the Daymet-forced historical run?
  2. Does projected change in surface runoff (what SNAP serves as `runoff`) track change in
     total runoff?
  3. Sanity checks: water-balance residual P - ET - RUNOFF - BASEFLOW, and the curated API
     `runoff` vs. raw RUNOFF at one point.

Reads NCAR monthly `wf` files (mm/month) read-only. Writes only to <out_dir>.

Usage:
    python baseflow_analysis.py <monthly_dir> <huc8.gpkg> <api_vic_point.json> <out_dir> [n_workers]

    monthly_dir : .../AK_NCAR_12km/vic_hydro/monthly   (contains BCSD/<model>/<rcp>/ and daymet/)
    huc8.gpkg   : from scripts/fetch_huc8.py
    api json    : /hydrology/point/64.84/-147.72 response (Fairbanks), for the curated-vs-raw check
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

MONTHLY, HUC_GPKG, API_JSON, OUT = map(Path, sys.argv[1:5])
NWORK = int(sys.argv[5]) if len(sys.argv) > 5 else 8
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
SCENARIOS = ["rcp45", "rcp85"]
PERIODS = {"hist": (1980, 2009), "mid": (2040, 2069), "late": (2070, 2099)}
VARS = ["RUNOFF", "BASEFLOW", "EVAP", "PRCP", "GLACIER_MELT", "SNOW_MELT"]
SEASONS = {"winter_NovApr": [11, 12, 1, 2, 3, 4], "freshet_MayJun": [5, 6],
           "summer_fall_JulOct": [7, 8, 9, 10]}
if __import__("os").environ.get("SMOKE"):  # quick end-to-end test: 3 models, 2 years per period
    MODELS = MODELS[:3]
    PERIODS = {k: (v[0], v[0] + 1) for k, v in PERIODS.items()}
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79)}
STERE = "+proj=stere +lat_0=90 +lat_ts=64 +lon_0=-150 +R=6370000 +x_0=0 +y_0=0 +units=m"


def files_for(source, scenario, y0, y1):
    if source == "daymet":
        return [MONTHLY / "daymet" / f"daymet_wf_{y}.nc" for y in range(y0, y1 + 1)]
    return [MONTHLY / "BCSD" / source / scenario / f"{source}_{scenario}_BCSD_wf_{y}.nc"
            for y in range(y0, y1 + 1)]


def climatology(args):
    """Monthly climatology (mean over years) of VARS for one source/scenario/period."""
    source, scenario, period = args
    y0, y1 = PERIODS[period]
    fs = files_for(source, scenario, y0, y1)
    missing = [f for f in fs if not f.exists()]
    if missing:
        return args, None, f"{len(missing)} missing, e.g. {missing[0].name}"
    stack = []
    for f in fs:  # open each read-only, one at a time
        with xr.open_dataset(f, decode_times=False, mask_and_scale=True) as ds:
            a = np.stack([ds[v].values for v in VARS])  # (var, 12, y, x)
            a = np.where(a <= -999, np.nan, a)
            if a.shape[1] != 12:
                return args, None, f"{f.name} has {a.shape[1]} time steps"
            stack.append(a.astype("float32"))
    return args, np.nanmean(np.stack(stack), axis=0), None  # (var, 12, y, x)


def main():
    # ---- grid, land mask, cell areas (polar stereographic map factor)
    ref = files_for("CCSM4", "rcp85", 2050, 2050)[0]
    with xr.open_dataset(ref) as ds:
        lat, lon = ds.latitude.values, ds.longitude.values
        land = np.isfinite(np.where(ds.RUNOFF.values[0] <= -999, np.nan, ds.RUNOFF.values[0]))
    k = (1 + np.sin(np.deg2rad(64))) / (1 + np.sin(np.deg2rad(lat)))
    area = 144.0 / k**2  # km2
    area = np.where(land, area, np.nan)
    print(f"land cells: {land.sum()}, total area {np.nansum(area):,.0f} km2", flush=True)

    # ---- climatologies
    jobs = [(m, s, p) for m in MODELS for s in SCENARIOS for p in PERIODS]
    jobs += [("daymet", "obs", "hist")]
    clim, problems = {}, []
    with ProcessPoolExecutor(NWORK) as ex:
        for args, arr, err in ex.map(climatology, jobs):
            if err:
                problems.append((*args, err))
                print("PROBLEM", args, err, flush=True)
            else:
                clim[args] = arr
    print(f"climatologies: {len(clim)} ok, {len(problems)} problems", flush=True)

    # save compact NetCDF of RUNOFF/BASEFLOW/EVAP/PRCP monthly climatologies
    keys = sorted(clim)
    da = xr.DataArray(
        np.stack([clim[k] for k in keys]),
        dims=("run", "var", "month", "y", "x"),
        coords={"run": ["|".join(k) for k in keys], "var": VARS, "month": np.arange(1, 13)},
        name="climatology",
        attrs={"units": "mm/month", "description": "Monthly climatology of NCAR VIC wf variables; "
               "run = source|scenario|period; periods " + json.dumps(PERIODS)},
    )
    ds_out = da.to_dataset()
    ds_out["latitude"] = (("y", "x"), lat)
    ds_out["longitude"] = (("y", "x"), lon)
    ds_out["area_km2"] = (("y", "x"), area)
    enc = {"climatology": {"zlib": True, "complevel": 4, "dtype": "float32"}}
    ds_out.to_netcdf(OUT / "wf_monthly_climatologies.nc", encoding=enc)

    vi = {v: i for i, v in enumerate(VARS)}

    def annual(arr, v, months=None):
        sel = arr[vi[v]] if months is None else arr[vi[v]][[m - 1 for m in months]]
        return sel.sum(axis=0)  # mm/yr (or mm per season)

    def statewide(field, mask=None):  # area-weighted total over land (km2*mm; use as relative)
        a = area if mask is None else np.where(mask, area, np.nan)
        return np.nansum(field * a)

    # glacier cells: any run with GLACIER_MELT > 0. GLACIER_MELT values look implausibly large
    # (tens of m/yr), and P - ET - R - B is strongly negative there (ice loss), so statewide
    # water-balance stats are reported for all cells and for non-glacier cells separately.
    glac = np.zeros(land.shape, bool)
    for arr in clim.values():
        glac |= np.nan_to_num(annual(arr, "GLACIER_MELT")) > 0
    nong = land & ~glac
    print(f"glacier cells: {int((glac & land).sum())}, non-glacier land cells: {int(nong.sum())}",
          flush=True)

    # ---- 1. baseflow share, historical
    rows = []
    for key, arr in clim.items():
        src, scen, per = key
        r = {"source": src, "scenario": scen, "period": per}
        ro, bf = annual(arr, "RUNOFF"), annual(arr, "BASEFLOW")
        r["statewide_bf_share_annual"] = statewide(bf) / statewide(ro + bf)
        for sname, mons in SEASONS.items():
            ro_s, bf_s = annual(arr, "RUNOFF", mons), annual(arr, "BASEFLOW", mons)
            r[f"statewide_bf_share_{sname}"] = statewide(bf_s) / statewide(ro_s + bf_s)
            r[f"statewide_frac_of_annual_total_runoff_{sname}"] = (
                statewide(ro_s + bf_s) / statewide(ro + bf))
        with np.errstate(invalid="ignore", divide="ignore"):
            share = np.where(land & ((ro + bf) > 1), bf / (ro + bf), np.nan)
        r["cell_bf_share_p10"], r["cell_bf_share_median"], r["cell_bf_share_p90"] = (
            np.nanpercentile(share, [10, 50, 90]))
        r["statewide_mean_RO_mm"] = statewide(ro) / np.nansum(area)
        r["statewide_mean_BF_mm"] = statewide(bf) / np.nansum(area)
        p, et = annual(arr, "PRCP"), annual(arr, "EVAP")
        resid = p - et - ro - bf
        r["statewide_mean_P_mm"] = statewide(p) / np.nansum(area)
        r["statewide_mean_ET_mm"] = statewide(et) / np.nansum(area)
        r["statewide_mean_resid_mm"] = statewide(resid) / np.nansum(area)
        r["cell_abs_resid_median_mm"] = np.nanmedian(np.abs(np.where(land, resid, np.nan)))
        r["statewide_mean_glacier_melt_mm"] = statewide(annual(arr, "GLACIER_MELT")) / np.nansum(area)
        # non-glacier cells only
        ng_area = np.nansum(np.where(nong, area, np.nan))
        r["nonglacier_bf_share_annual"] = statewide(bf, nong) / statewide(ro + bf, nong)
        for sname, mons in SEASONS.items():
            ro_s, bf_s = annual(arr, "RUNOFF", mons), annual(arr, "BASEFLOW", mons)
            r[f"nonglacier_bf_share_{sname}"] = statewide(bf_s, nong) / statewide(ro_s + bf_s, nong)
        r["nonglacier_mean_resid_mm"] = statewide(resid, nong) / ng_area
        r["nonglacier_cell_abs_resid_median_mm"] = np.nanmedian(np.abs(np.where(nong, resid, np.nan)))
        r["nonglacier_mean_P_mm"] = statewide(p, nong) / ng_area
        r["glacier_cells_share_of_statewide_total_runoff"] = (
            statewide(ro + bf, glac & land) / statewide(ro + bf))
        gm = annual(arr, "GLACIER_MELT")
        r["glacier_cell_median_GLACIER_MELT_mm"] = np.nanmedian(np.where(glac & land, gm, np.nan))
        r["glacier_cell_median_resid_mm"] = np.nanmedian(np.where(glac & land, resid, np.nan))
        rows.append(r)
    share_df = pd.DataFrame(rows).sort_values(["period", "scenario", "source"])
    share_df.to_csv(OUT / "baseflow_share_by_run.csv", index=False)

    # ---- 2. change: surface vs total runoff, late & mid vs hist (same scenario)
    crow = []
    for m in MODELS:
        for s in SCENARIOS:
            h = clim.get((m, s, "hist"))
            for per in ["mid", "late"]:
                f = clim.get((m, s, per))
                if h is None or f is None:
                    continue
                ro_h, bf_h = annual(h, "RUNOFF"), annual(h, "BASEFLOW")
                ro_f, bf_f = annual(f, "RUNOFF"), annual(f, "BASEFLOW")
                tot_h, tot_f = ro_h + bf_h, ro_f + bf_f
                with np.errstate(invalid="ignore", divide="ignore"):
                    ok = land & (ro_h > 5) & (tot_h > 5)  # avoid tiny denominators
                    dro = np.where(ok, (ro_f - ro_h) / ro_h * 100, np.nan)
                    dtot = np.where(ok, (tot_f - tot_h) / tot_h * 100, np.nan)
                    dbf = np.where(ok, (bf_f - bf_h) / np.where(bf_h > 0, bf_h, np.nan) * 100, np.nan)
                n = np.isfinite(dro) & np.isfinite(dtot)
                crow.append({
                    "model": m, "scenario": s, "period": per,
                    "statewide_dRO_pct": (statewide(ro_f) / statewide(ro_h) - 1) * 100,
                    "statewide_dBF_pct": (statewide(bf_f) / statewide(bf_h) - 1) * 100,
                    "statewide_dTOT_pct": (statewide(tot_f) / statewide(tot_h) - 1) * 100,
                    "cells_used": int(n.sum()),
                    "frac_cells_sign_disagree": float(np.mean(np.sign(dro[n]) != np.sign(dtot[n]))),
                    "median_abs_diff_dRO_minus_dTOT_pctpts": float(np.median(np.abs(dro[n] - dtot[n]))),
                    "frac_cells_diff_gt_10pctpts": float(np.mean(np.abs(dro[n] - dtot[n]) > 10)),
                    "frac_cells_diff_gt_25pctpts": float(np.mean(np.abs(dro[n] - dtot[n]) > 25)),
                    "spearman_dRO_dTOT": float(pd.Series(dro[n]).corr(pd.Series(dtot[n]), method="spearman")),
                    "median_cell_dBF_pct": float(np.nanmedian(dbf)),
                })
    change_df = pd.DataFrame(crow)
    change_df.to_csv(OUT / "runoff_change_surface_vs_total.csv", index=False)

    # ---- per-cell ensemble fields for maps / HUC8 aggregation (hist share; late rcp85 changes)
    def ens(per, s, fn):
        vals = [fn(clim[(m, s, per)]) for m in MODELS if (m, s, per) in clim]
        return np.nanmean(np.stack(vals), axis=0)

    ro_h = ens("hist", "rcp85", lambda a: annual(a, "RUNOFF"))
    bf_h = ens("hist", "rcp85", lambda a: annual(a, "BASEFLOW"))
    ro_l = ens("late", "rcp85", lambda a: annual(a, "RUNOFF"))
    bf_l = ens("late", "rcp85", lambda a: annual(a, "BASEFLOW"))

    # ---- HUC8 aggregation (cell centers in polygons)
    hucs = gpd.read_file(HUC_GPKG).to_crs(STERE)
    t = Transformer.from_crs(4326, STERE, always_xy=True)
    X, Y = t.transform(lon, lat)
    pts = gpd.GeoDataFrame({"iy": np.indices(lat.shape)[0].ravel(), "ix": np.indices(lat.shape)[1].ravel()},
                           geometry=gpd.points_from_xy(X.ravel(), Y.ravel()), crs=STERE)
    pts = pts[land.ravel()]
    j = gpd.sjoin(pts, hucs[["huc8", "name", "geometry"]], predicate="within", how="inner")
    hrows = []
    for (huc, name), g in j.groupby(["huc8", "name"]):
        iy, ix = g.iy.values, g.ix.values
        a = area[iy, ix]
        w = lambda f: np.nansum(f[iy, ix] * a)
        cell_tot_h = ro_h[iy, ix] + bf_h[iy, ix]
        hrows.append({
            "huc8": huc, "name": name, "n_cells": len(g),
            "bf_share_hist": w(bf_h) / w(ro_h + bf_h),
            "dRO_pct_late_rcp85": (w(ro_l) / w(ro_h) - 1) * 100,
            "dTOT_pct_late_rcp85": (w(ro_l + bf_l) / w(ro_h + bf_h) - 1) * 100,
            "TOT_hist_mm": w(ro_h + bf_h) / np.nansum(a),
            "cell_TOT_hist_cv": float(np.nanstd(cell_tot_h) / np.nanmean(cell_tot_h)),
        })
    huc_df = pd.DataFrame(hrows)
    huc_df["sign_disagree"] = np.sign(huc_df.dRO_pct_late_rcp85) != np.sign(huc_df.dTOT_pct_late_rcp85)
    huc_df.to_csv(OUT / "huc8_baseflow_and_change.csv", index=False)
    print(f"HUC8s with cells: {len(huc_df)}; cells joined: {len(j)} of {land.sum()}", flush=True)

    # ---- point checks (nearest cell): BF share hist, and curated API vs raw RUNOFF
    prow = []
    for name, (plat, plon) in POINTS.items():
        px, py = t.transform(plon, plat)
        d = np.where(land, (X - px) ** 2 + (Y - py) ** 2, np.inf)
        iy, ix = np.unravel_index(np.argmin(d), d.shape)
        prow.append({"location": name, "iy": iy, "ix": ix,
                     "cell_lat": float(lat[iy, ix]), "cell_lon": float(lon[iy, ix]),
                     "bf_share_hist_ens": float(bf_h[iy, ix] / (ro_h[iy, ix] + bf_h[iy, ix])),
                     "RO_hist_mm": float(ro_h[iy, ix]), "BF_hist_mm": float(bf_h[iy, ix])})
    pd.DataFrame(prow).to_csv(OUT / "point_baseflow_share.csv", index=False)

    # curated API `runoff` (decadal mean of monthly totals) vs raw RUNOFF, Fairbanks, CCSM4 rcp85 1990s
    api = json.loads(API_JSON.read_text())
    iy, ix = prow[0]["iy"], prow[0]["ix"]
    raw = []
    for y in range(1990, 2000):
        with xr.open_dataset(files_for("CCSM4", "rcp85", y, y)[0], decode_times=False) as ds:
            raw.append(ds.RUNOFF.values[:, iy, ix])
    raw = np.mean(raw, axis=0)
    mo = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    apiv = [float(api["CCSM4"]["rcp85"][m]["1990-1999"]["runoff"]) for m in mo]
    pd.DataFrame({"month": mo, "api_runoff": apiv, "raw_RUNOFF_nearest_cell": np.round(raw, 1)}).to_csv(
        OUT / "check_api_vs_raw_runoff_fairbanks.csv", index=False)

    # monthly statewide climatology for the figure (ensemble mean + range; daymet)
    mrows = []
    for key, arr in clim.items():
        for i in range(12):
            mrows.append({"source": key[0], "scenario": key[1], "period": key[2], "month": i + 1,
                          "RO_mm": statewide(arr[vi["RUNOFF"], i]) / np.nansum(area),
                          "BF_mm": statewide(arr[vi["BASEFLOW"], i]) / np.nansum(area)})
    pd.DataFrame(mrows).to_csv(OUT / "statewide_monthly_RO_BF.csv", index=False)

    # ---- summary print
    pd.set_option("display.width", 250)
    hist = share_df[share_df.period == "hist"]
    print("\n== Historical baseflow share (statewide, area-weighted)")
    print(hist[["source", "scenario", "statewide_bf_share_annual", "statewide_bf_share_winter_NovApr",
                "statewide_bf_share_freshet_MayJun", "statewide_bf_share_summer_fall_JulOct",
                "nonglacier_bf_share_annual", "nonglacier_bf_share_winter_NovApr",
                "cell_bf_share_median", "statewide_mean_P_mm", "statewide_mean_ET_mm",
                "statewide_mean_RO_mm", "statewide_mean_BF_mm", "nonglacier_mean_resid_mm",
                "nonglacier_cell_abs_resid_median_mm", "glacier_cells_share_of_statewide_total_runoff",
                "glacier_cell_median_GLACIER_MELT_mm", "glacier_cell_median_resid_mm"]
               ].round(3).T.to_string())
    print("\n== Change, surface vs total runoff")
    print(change_df.drop(columns="model").groupby(["scenario", "period"])
          .agg(["mean", "min", "max"]).round(2).T.to_string())
    print("\n== HUC8 summary")
    print(huc_df.describe().round(2).to_string())
    print("HUC8 sign disagreements (late rcp85):", int(huc_df.sign_disagree.sum()))
    print("\n== Points"); print(pd.DataFrame(prow).round(3).to_string(index=False))
    if problems:
        print("\nPROBLEMS:", problems)


if __name__ == "__main__":
    main()
