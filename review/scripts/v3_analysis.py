"""Verification job 3: baseflow share, projected change, HUC8 aggregation and sensitivity tests.

Uses the period climatologies written by v1_climatologies.py and the all-years glacier mask
from v2_alignment.py. Written independently of scripts/baseflow_analysis.py.

Outputs (CSV) in <res_dir>:
  v3_cell_counts.csv         M1: land cells, active cells, glacier cells under three definitions
  v3_bf_share_by_run.csv     H2/M2/H8: per run x glacier-mask x weighting: baseflow share of
                             total runoff (annual, Nov-Apr, May-Jun, Jul-Oct), water-balance
                             residual, glacier-cell GLACIER_MELT statistics
  v3_monthly_nonglacier.csv  Fig 2a: 10-model-mean monthly surface runoff and baseflow
  v3_change_by_run.csv       H4: per run x mask x weighting: % change late vs hist (RO, BF, TOT)
  v3_change_summary.csv      H4: 10-model mean / min / max per scenario and variant
  v3_huc8.csv                H3/H5/M5: per HUC8 and assignment method
  v3_huc8_summary.csv        H3/H5/M5: medians and counts per assignment method
  v3_spot_cells.csv          monthly surface runoff / baseflow at named and random cells

Usage: python v3_analysis.py <clim_dir> <glacier_allyears.nc> <huc8.gpkg> <res_dir>
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer
from shapely.geometry import Point, box

CLIM, GLAC, GPKG, RES = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
RES.mkdir(parents=True, exist_ok=True)
MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
STERE = "+proj=stere +lat_0=90 +lat_ts=64 +lon_0=-150 +R=6370000 +x_0=0 +y_0=0 +units=m"
POINTS = {"Fairbanks": (64.84, -147.72), "Palmer": (61.60, -149.11), "Juneau": (58.30, -134.42),
          "Bethel": (60.79, -161.76), "Utqiagvik": (71.29, -156.79), "Umiat": (69.37, -152.14),
          "Ketchikan": (55.34, -131.65)}
REGIONS = {"Interior": (63, 66, -150, -143), "NorthSlope": (68.5, 70.5, -158, -148),
           "Southcentral": (60.5, 62.5, -151, -146), "Southeast": (55, 58, -135, -130),
           "YKDelta": (60, 62.5, -165, -160)}
WINTER, FRESHET, SUMFALL = [11, 12, 1, 2, 3, 4], [5, 6], [7, 8, 9, 10]


def load(src, scen, per):
    return xr.open_dataset(CLIM / f"clim_{src}_{scen}_{per}.nc").load()


runs = {(m, s, p): load(m, s, p) for m in MODELS for s in ("rcp45", "rcp85") for p in ("hist", "late")}
runs[("daymet", "obs", "hist")] = load("daymet", "obs", "hist")
ref = runs[("CCSM4", "rcp85", "hist")]
lat, lon = ref.latitude.values, ref.longitude.values
land = ref.land.values.astype(bool)
active = land & (sum(runs[(m, "rcp85", "hist")].PRCP_ann.values for m in MODELS) > 0)  # excludes all-zero cells
k = (1 + np.sin(np.deg2rad(64))) / (1 + np.sin(np.deg2rad(lat)))
area = (12.0 / k) ** 2  # km2, polar-stereographic map factor (true at 64N)
WEIGHTS = {"map": area, "equal": np.ones_like(area)}

# --- glacier masks
gm_any_clim = np.zeros_like(land)
for ds in runs.values():
    gm_any_clim |= np.nan_to_num(ds.GLACIER_MELT_ann.values) > 0
ga = xr.open_dataset(GLAC)
gm_any_year = (ga.gm_months_gt0.values > 0) & land
gm_ens = np.mean([runs[(m, "rcp85", "hist")].GLACIER_MELT_ann.values for m in MODELS], axis=0)
gm_thr = np.nan_to_num(gm_ens) > 100  # mean > 100 mm/yr in 1980-2009
MASKS = {"nonglacier_anyyear": active & ~gm_any_year, "nonglacier_anyclim": active & ~gm_any_clim,
         "nonglacier_mean100": active & ~gm_thr, "all_active": active}
pd.DataFrame([dict(land_nonnan=int(land.sum()), active_nonzero=int(active.sum()),
                   allzero_cells=int((land & ~active).sum()),
                   glacier_anyyear=int(gm_any_year.sum()), glacier_anyclim=int((gm_any_clim & land).sum()),
                   glacier_mean_gt100=int((gm_thr & land).sum()),
                   nonglacier_anyyear=int(MASKS["nonglacier_anyyear"].sum()),
                   total_area_km2=round(float(area[land].sum())), active_area_km2=round(float(area[active].sum())))]
             ).to_csv(RES / "v3_cell_counts.csv", index=False)


def share(ds, mask, w, months=None):
    ro, bf = ds.RUNOFF_mon.values, ds.BASEFLOW_mon.values
    if months is not None:
        idx = [m - 1 for m in months]
        ro, bf = ro[idx], bf[idx]
    ro, bf = ro.sum(axis=0), bf.sum(axis=0)
    return float((bf * w)[mask].sum() / ((ro + bf) * w)[mask].sum())


# --- H2 / M2 / H8: baseflow share and water balance per run
rows = []
for (src, scen, per), ds in runs.items():
    if per != "hist":
        continue
    P, ET, RO, BF, GM = (np.nan_to_num(ds[f"{v}_ann"].values) for v in ("PRCP", "EVAP", "RUNOFF", "BASEFLOW", "GLACIER_MELT"))
    resid = P - ET - RO - BF
    for mname, mask in MASKS.items():
        for wname, w in WEIGHTS.items():
            r = dict(source=src, scenario=scen, mask=mname, weight=wname, n_cells=int(mask.sum()),
                     bf_share_annual=share(ds, mask, w), bf_share_NovApr=share(ds, mask, w, WINTER),
                     bf_share_MayJun=share(ds, mask, w, FRESHET), bf_share_JulOct=share(ds, mask, w, SUMFALL),
                     resid_mean_mm=float((resid * w)[mask].sum() / w[mask].sum()),
                     resid_abs_median_mm=float(np.median(np.abs(resid[mask]))),
                     mean_P=float((P * w)[mask].sum() / w[mask].sum()), mean_RO=float((RO * w)[mask].sum() / w[mask].sum()),
                     mean_BF=float((BF * w)[mask].sum() / w[mask].sum()))
            if mname == "nonglacier_anyyear" and wname == "map":
                g = gm_any_year
                tot = RO + BF
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = (tot - P + ET) / GM
                r.update(glacier_n=int(g.sum()), glacier_GM_median_m=float(np.median(GM[g])) / 1000,
                         glacier_GM_p10_m=float(np.percentile(GM[g], 10)) / 1000, glacier_GM_p90_m=float(np.percentile(GM[g], 90)) / 1000,
                         glacier_GM_max_m=float(GM[g].max()) / 1000,
                         glacier_resid_median_m=float(np.median(resid[g])) / 1000,
                         glacier_TOT_median_m=float(np.median(tot[g])) / 1000,
                         glacier_frac_GM_gt_TOT=float(np.mean(GM[g] > tot[g])),
                         glacier_ratio_runoff_excess_over_GM_median=float(np.nanmedian(ratio[g & (GM > 100)])),
                         glacier_share_of_domain_total_runoff=float((tot * area)[g].sum() / (tot * area)[active].sum()))
            rows.append(r)
bf = pd.DataFrame(rows)
bf.to_csv(RES / "v3_bf_share_by_run.csv", index=False)

# --- Fig 2a: 10-model mean monthly RO and BF over non-glacier cells (RCP8.5 hist, map weights)
mask, w = MASKS["nonglacier_anyyear"], WEIGHTS["map"]
ro_m = np.mean([runs[(m, "rcp85", "hist")].RUNOFF_mon.values for m in MODELS], axis=0)
bf_m = np.mean([runs[(m, "rcp85", "hist")].BASEFLOW_mon.values for m in MODELS], axis=0)
mon = pd.DataFrame({"month": range(1, 13),
                    "surface_runoff_mm": [(ro_m[i] * w)[mask].sum() / w[mask].sum() for i in range(12)],
                    "baseflow_mm": [(bf_m[i] * w)[mask].sum() / w[mask].sum() for i in range(12)]})
mon["bf_share"] = mon.baseflow_mm / (mon.surface_runoff_mm + mon.baseflow_mm)
mon.round(3).to_csv(RES / "v3_monthly_nonglacier.csv", index=False)

# --- H4: domain-wide change, per run, masks and weights; per-cell sign disagreement
rows = []
cell_sign = {}
for m in MODELS:
    for s in ("rcp45", "rcp85"):
        h, l = runs[(m, s, "hist")], runs[(m, s, "late")]
        Rh, Bh = np.nan_to_num(h.RUNOFF_ann.values), np.nan_to_num(h.BASEFLOW_ann.values)
        Rl, Bl = np.nan_to_num(l.RUNOFF_ann.values), np.nan_to_num(l.BASEFLOW_ann.values)
        for mname in ("all_active", "nonglacier_anyyear"):
            mask = MASKS[mname]
            for wname, w in WEIGHTS.items():
                def pct(a, b):
                    return 100 * ((b * w)[mask].sum() / (a * w)[mask].sum() - 1)
                rows.append(dict(model=m, scenario=s, mask=mname, weight=wname, dRO_pct=pct(Rh, Rl),
                                 dBF_pct=pct(Bh, Bl), dTOT_pct=pct(Rh + Bh, Rl + Bl)))
        with np.errstate(divide="ignore", invalid="ignore"):
            dro, dtot = Rl / Rh - 1, (Rl + Bl) / (Rh + Bh) - 1
        cell_sign[(m, s)] = (dro, dtot)
ch = pd.DataFrame(rows)
ch.to_csv(RES / "v3_change_by_run.csv", index=False)
summ = ch.groupby(["scenario", "mask", "weight"])[["dRO_pct", "dBF_pct", "dTOT_pct"]].agg(["mean", "min", "max"]).round(1)
summ.columns = ["_".join(c) for c in summ.columns]
# per-cell sign disagreement, ensemble mean of per-model changes (RCP8.5) and per model
for s in ("rcp45", "rcp85"):
    dro = np.mean([cell_sign[(m, s)][0] for m in MODELS], axis=0)
    dtot = np.mean([cell_sign[(m, s)][1] for m in MODELS], axis=0)
    ok = active & np.isfinite(dro) & np.isfinite(dtot)
    summ.loc[(s, "all_active", "map"), "cells_sign_disagree_frac_ensmean"] = round(float(np.mean(np.sign(dro[ok]) != np.sign(dtot[ok]))), 3)
    fr = [float(np.mean(np.sign(cell_sign[(m, s)][0][ok]) != np.sign(cell_sign[(m, s)][1][ok]))) for m in MODELS]
    summ.loc[(s, "all_active", "map"), "cells_sign_disagree_frac_permodel_min"] = round(min(fr), 3)
    summ.loc[(s, "all_active", "map"), "cells_sign_disagree_frac_permodel_max"] = round(max(fr), 3)
    summ.loc[(s, "all_active", "map"), "cells_median_abs_dRO_minus_dTOT_pctpts"] = round(float(np.median(np.abs(dro[ok] - dtot[ok])) * 100), 1)
summ.reset_index().to_csv(RES / "v3_change_summary.csv", index=False)

# --- H3 / H5 / M5: HUC8 aggregation by cell-centre and by area-weighted overlap
to_st = Transformer.from_crs("EPSG:4326", STERE, always_xy=True)
iy, ix = np.nonzero(land)
x, y = to_st.transform(lon[iy, ix], lat[iy, ix])
cells = gpd.GeoDataFrame({"cid": np.arange(len(iy)), "iy": iy, "ix": ix, "area": area[iy, ix], "active": active[iy, ix]},
                         geometry=[Point(a, b) for a, b in zip(x, y)], crs=STERE)
boxes = cells.copy()
boxes["geometry"] = [box(a - 6000, b - 6000, a + 6000, b + 6000) for a, b in zip(x, y)]
hucs = gpd.read_file(GPKG)
hucs["huc_area_km2"] = hucs.to_crs("EPSG:3338").geometry.area / 1e6
hucs_st = hucs.to_crs(STERE)
# (a) centre inside polygon
cen = gpd.sjoin(cells, hucs_st[["huc8", "name", "geometry"]], predicate="within", how="inner")
cen = cen[~cen.index.duplicated()]
cen["w"] = cen["area"].values  # true cell area (km2); note GeoDataFrame.area would be the point geometry's area
# (b) overlap area, corrected by the map factor to true area
ov = gpd.sjoin(boxes, hucs_st[["huc8", "name", "geometry"]], predicate="intersects", how="inner")
import shapely
inter = shapely.intersection(np.asarray(ov.geometry.values), np.asarray(hucs_st.geometry.loc[ov.index_right].values))
ov["w"] = shapely.area(inter) / 1e6 / (k[ov.iy, ov.ix] ** 2)  # km2 true area of the overlap
ov = ov[ov.w > 1e-3]

RO_h = np.mean([np.nan_to_num(runs[(m, "rcp85", "hist")].RUNOFF_ann.values) for m in MODELS], axis=0)
BF_h = np.mean([np.nan_to_num(runs[(m, "rcp85", "hist")].BASEFLOW_ann.values) for m in MODELS], axis=0)
RO_l = np.mean([np.nan_to_num(runs[(m, "rcp85", "late")].RUNOFF_ann.values) for m in MODELS], axis=0)
BF_l = np.mean([np.nan_to_num(runs[(m, "rcp85", "late")].BASEFLOW_ann.values) for m in MODELS], axis=0)
permodel = {m: (np.nan_to_num(runs[(m, "rcp85", "hist")].RUNOFF_ann.values), np.nan_to_num(runs[(m, "rcp85", "hist")].BASEFLOW_ann.values),
               np.nan_to_num(runs[(m, "rcp85", "late")].RUNOFF_ann.values), np.nan_to_num(runs[(m, "rcp85", "late")].BASEFLOW_ann.values)) for m in MODELS}

hrows = []
for method, j in (("centroid", cen), ("overlap", ov)):
    for h, g in j.groupby("huc8"):
        g = g[g.active]  # all-zero ocean cells carry no water; drop them
        if len(g) == 0:
            continue
        w, yy, xx = g.w.values, g.iy.values, g.ix.values
        def agg(a):
            return float((a[yy, xx] * w).sum() / w.sum())
        roh, bfh, rol, bfl = agg(RO_h), agg(BF_h), agg(RO_l), agg(BF_l)
        pm_ro = [100 * (agg(permodel[m][2]) / agg(permodel[m][0]) - 1) for m in MODELS]
        pm_tot = [100 * (agg(permodel[m][2] + permodel[m][3]) / agg(permodel[m][0] + permodel[m][1]) - 1) for m in MODELS]
        hrows.append(dict(method=method, huc8=h, name=g.name.iloc[0], n_cells=len(g), weight_sum_km2=float(w.sum()),
                          huc_area_km2=float(hucs.loc[hucs.huc8 == h, "huc_area_km2"].iloc[0]),
                          bf_share_hist=bfh / (roh + bfh), RO_hist_mm=roh, BF_hist_mm=bfh,
                          dRO_pct=100 * (rol / roh - 1), dTOT_pct=100 * ((rol + bfl) / (roh + bfh) - 1),
                          dRO_pct_meanmodels=float(np.mean(pm_ro)), dTOT_pct_meanmodels=float(np.mean(pm_tot)),
                          n_models_RO_down=int(sum(v < 0 for v in pm_ro)), n_models_TOT_up=int(sum(v > 0 for v in pm_tot))))
huc = pd.DataFrame(hrows)
huc["sign_disagree"] = np.sign(huc.dRO_pct) != np.sign(huc.dTOT_pct)
huc["sign_disagree_meanmodels"] = np.sign(huc.dRO_pct_meanmodels) != np.sign(huc.dTOT_pct_meanmodels)
huc["min_abs_change"] = np.minimum(huc.dRO_pct.abs(), huc.dTOT_pct.abs())
huc.round(4).to_csv(RES / "v3_huc8.csv", index=False)
srows = []
for method, g in huc.groupby("method"):
    for label, gg in (("all", g), ("ge10cells", g[g.n_cells >= 10])):
        d = gg[gg.sign_disagree]
        srows.append(dict(method=method, subset=label, n_huc8=len(gg), n_huc8_total=len(hucs),
                          median_n_cells=float(gg.n_cells.median()), median_huc_area_km2=float(gg.huc_area_km2.median()),
                          median_all157_area_km2=float(hucs.huc_area_km2.median()),
                          bf_share_median=float(gg.bf_share_hist.median()), bf_share_min=float(gg.bf_share_hist.min()),
                          bf_share_max=float(gg.bf_share_hist.max()), bf_share_q25=float(gg.bf_share_hist.quantile(.25)),
                          bf_share_q75=float(gg.bf_share_hist.quantile(.75)),
                          dRO_median=float(gg.dRO_pct.median()), dTOT_median=float(gg.dTOT_pct.median()),
                          dRO_median_meanmodels=float(gg.dRO_pct_meanmodels.median()), dTOT_median_meanmodels=float(gg.dTOT_pct_meanmodels.median()),
                          n_sign_disagree=int(gg.sign_disagree.sum()), n_sign_disagree_meanmodels=int(gg.sign_disagree_meanmodels.sum()),
                          n_disagree_minabs_lt5=int((d.min_abs_change < 5).sum()), n_disagree_minabs_lt2=int((d.min_abs_change < 2).sum()),
                          n_disagree_both_gt5=int((d.min_abs_change >= 5).sum()),
                          n_RO_up=int((gg.dRO_pct > 0).sum()), n_TOT_up=int((gg.dTOT_pct > 0).sum())))
pd.DataFrame(srows).round(3).to_csv(RES / "v3_huc8_summary.csv", index=False)

# --- spot cells: named points and one random non-glacier cell per region
rng = np.random.default_rng(1)
spots = []
for n, (pla, plo) in POINTS.items():
    la, lo, pa, po = map(np.deg2rad, (lat, lon, pla, plo))
    d = np.arccos(np.clip(np.sin(la) * np.sin(pa) + np.cos(la) * np.cos(pa) * np.cos(lo - po), -1, 1))
    spots.append((n, *np.unravel_index(int(np.argmin(np.where(land, d, np.inf))), d.shape)))
for n, (la0, la1, lo0, lo1) in REGIONS.items():
    cand = np.nonzero(MASKS["nonglacier_anyyear"] & (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1))
    j = rng.integers(len(cand[0]))
    spots.append((f"random_{n}", cand[0][j], cand[1][j]))
srows = []
for n, yy, xx in spots:
    ro = ro_m[:, yy, xx]
    b = bf_m[:, yy, xx]
    srows.append(dict(cell=n, iy=int(yy), ix=int(xx), lat=round(float(lat[yy, xx]), 2), lon=round(float(lon[yy, xx]), 2),
                      glacier=bool(gm_any_year[yy, xx]), bf_share_annual=round(float(b.sum() / (ro.sum() + b.sum())), 3),
                      bf_share_NovApr=round(float(b[[10, 11, 0, 1, 2, 3]].sum() / (ro[[10, 11, 0, 1, 2, 3]].sum() + b[[10, 11, 0, 1, 2, 3]].sum())), 3),
                      bf_share_MayJun=round(float(b[[4, 5]].sum() / (ro[[4, 5]].sum() + b[[4, 5]].sum())), 3),
                      bf_share_AugOct=round(float(b[[7, 8, 9]].sum() / (ro[[7, 8, 9]].sum() + b[[7, 8, 9]].sum())), 3),
                      RO_peak_month=int(np.argmax(ro) + 1), BF_peak_month=int(np.argmax(b) + 1),
                      **{f"RO_m{i+1}": round(float(ro[i]), 1) for i in range(12)}, **{f"BF_m{i+1}": round(float(b[i]), 1) for i in range(12)}))
pd.DataFrame(srows).to_csv(RES / "v3_spot_cells.csv", index=False)

# --- console summary
pd.set_option("display.width", 250)
print("== cell counts"); print(pd.read_csv(RES / "v3_cell_counts.csv").to_string(index=False))
print("\n== H2 non-glacier baseflow share (anyyear mask, map weights), hist")
sel = bf[(bf["mask"] == "nonglacier_anyyear") & (bf.weight == "map")]
print(sel[["source", "scenario", "bf_share_annual", "bf_share_NovApr", "bf_share_MayJun", "bf_share_JulOct", "resid_mean_mm", "resid_abs_median_mm", "glacier_GM_median_m", "glacier_resid_median_m", "glacier_ratio_runoff_excess_over_GM_median"]].round(3).to_string(index=False))
print("\n== H2 sensitivity: range over 10 GCMs (RCP8.5) of annual share by mask x weight")
g = bf[(bf.scenario == "rcp85")].groupby(["mask", "weight"])[["bf_share_annual", "bf_share_NovApr"]].agg(["min", "max"]).round(3)
print(g.to_string())
print("\n== Fig 2a monthly"); print(mon.round(2).to_string(index=False))
print("\n== H4 change summary"); print(summ.to_string())
print("\n== H3/H5/M5 HUC8 summary"); print(pd.DataFrame(srows := pd.read_csv(RES / "v3_huc8_summary.csv")).to_string(index=False))
print("\n== opposite-sign HUC8s (centroid)")
print(huc[(huc.method == "centroid") & huc.sign_disagree][["huc8", "name", "n_cells", "dRO_pct", "dTOT_pct", "dRO_pct_meanmodels", "dTOT_pct_meanmodels", "n_models_RO_down", "n_models_TOT_up"]].round(1).to_string(index=False))
print("\n== spot cells"); print(pd.read_csv(RES / "v3_spot_cells.csv").iloc[:, :13].to_string(index=False))
