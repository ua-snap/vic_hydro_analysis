"""Verification 5: what the SNAP API serves, traced to the published files (light; cached JSON).

Uses the cached /hydrology/point responses (vic_<point>.json) and the per-year point values
extracted by v1 (points_monthly.csv: VIC wf variables) and v2 (points_met_monthly.csv: met pcp
and VIC PRCP, both scenarios, all years).

  H1  the API has no baseflow/total-runoff field
  M3  API `runoff` == decadal mean of raw monthly RUNOFF, rounded to whole mm, at the nearest
      cell (or one of its 8 neighbours, since the API grid is reprojected to EPSG:3338)
  M4  HadGEM2-ES pcp/tmax/tmin are null at every point and decade; its hydrology is present
  H7  for RCP4.5 historical decades, API `pcp` matches the RCP4.5 met files (not the RCP8.5
      met that drove the shared historical hydrology); API `runoff` rcp45 == rcp85 there
  M6  SNAP's other precipitation products vs VIC forcing at the test points, recomputed from
      the cached ERA5-WRF and CMIP6-downscaled responses

Usage: python v5_api_checks.py <cache_dir> <points_monthly.csv> <points_met_monthly.csv|-> <out_dir>
"""
import calendar
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE, PTS, MET, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
MO = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
API_POINTS = ["Fairbanks", "Palmer", "Juneau", "Bethel", "Utqiagvik"]
DEC = {"hist": ["1980-1989", "1990-1999", "2000-2009"], "late": ["2070-2079", "2080-2089", "2090-2099"]}
api = {p: json.load(open(CACHE / f"vic_{p}.json")) for p in API_POINTS}
models = sorted(api["Fairbanks"])
pts = pd.read_csv(PTS)

# --- H1
fields = sorted(api["Fairbanks"]["CCSM4"]["rcp85"]["jan"]["1980-1989"])
print("H1 API fields:", fields, "| has baseflow:", any("base" in f or "total" in f for f in fields))

# --- M4
nulls = {}
for p in API_POINTS:
    for m in models:
        for s in ("rcp45", "rcp85"):
            for dec in api[p][m][s]["jan"]:
                rec = api[p][m][s]["jan"][dec]
                for v in ("pcp", "tmax", "tmin", "runoff", "evap"):
                    nulls.setdefault((m, v), []).append(rec[v] is None)
m4 = pd.DataFrame([dict(model=m, var=v, frac_null=np.mean(x)) for (m, v), x in nulls.items()])
print("\nM4 null fractions (all points, scenarios, decades):")
print(m4[m4.frac_null > 0].to_string(index=False) if (m4.frac_null > 0).any() else "none")
m4.to_csv(OUT / "v5_api_nulls.csv", index=False)


def api_dec(p, m, s, var, dec):
    return np.array([float(api[p][m][s][mo][dec][var]) if api[p][m][s][mo][dec][var] is not None else np.nan for mo in MO])


def raw_dec(df, var, dec):
    y0, y1 = map(int, dec.split("-"))
    d = df[(df["var"] == var) & (df.year >= y0) & (df.year <= y1)]
    return d[[f"m{i}" for i in range(1, 13)]].mean().values, len(d)


# --- M3: API runoff vs raw RUNOFF at the nearest cell, hist and late decades, both scenarios
rows = []
for p in API_POINTS:
    for m in models:
        for s in ("rcp45", "rcp85"):
            sub = pts[(pts.source == m) & (pts.scenario == s) & (pts.point == p)]
            for per, decs in DEC.items():
                for dec in decs:
                    a = api_dec(p, m, s, "runoff", dec)
                    r, n = raw_dec(sub[sub.period == per], "RUNOFF", dec)
                    d = np.abs(a - r)
                    rows.append(dict(point=p, model=m, scenario=s, decade=dec, n_years=n,
                                     max_abs_diff=float(np.nanmax(d)), n_months_within_0p5=int((d <= 0.5 + 1e-6).sum()),
                                     n_months_within_1=int((d <= 1.0 + 1e-6).sum()), api_annual=float(np.nansum(a)), raw_annual=float(r.sum())))
m3 = pd.DataFrame(rows)
m3.to_csv(OUT / "v5_api_vs_raw_runoff.csv", index=False)
print("\nM3 API runoff vs raw RUNOFF (decadal mean of monthly, nearest cell): share of month-values within 0.5 mm / 1 mm, by point")
print(m3.groupby("point").apply(lambda g: pd.Series(dict(n=len(g) * 12, within_0p5=g.n_months_within_0p5.sum() / (12 * len(g)),
                                                            within_1=g.n_months_within_1.sum() / (12 * len(g)), max_abs=g.max_abs_diff.max(),
                                                            all_decades_within_0p5=int((g.n_months_within_0p5 == 12).sum()), decades=len(g)))).round(3).to_string())
fb = m3[(m3.point == "Fairbanks") & (m3.model == "CCSM4") & (m3.scenario == "rcp85") & (m3.decade == "1980-1989")].iloc[0]
print("Fairbanks CCSM4 rcp85 1980s: API", api_dec("Fairbanks", "CCSM4", "rcp85", "runoff", "1980-1989").tolist(),
      "\n   raw", np.round(raw_dec(pts[(pts.source == "CCSM4") & (pts.scenario == "rcp85") & (pts.point == "Fairbanks") & (pts.period == "hist")], "RUNOFF", "1980-1989")[0], 2).tolist())

# --- M6: precipitation sources at the test points, recomputed from the cache
rows = []
for p in API_POINTS:
    vic = {}
    for s in ("rcp45", "rcp85"):
        vals = []
        for m in models:
            ann = [np.nansum(api_dec(p, m, s, "pcp", dec)) for dec in DEC["hist"]]
            if not any(api[p][m][s]["jan"][dec]["pcp"] is None for dec in DEC["hist"]):
                vals.append(np.mean(ann))
        vic[s] = (np.mean(vals), len(vals), min(vals), max(vals))
    r = dict(point=p, vic_P_hist_rcp85=round(vic["rcp85"][0], 1), vic_P_hist_rcp45=round(vic["rcp45"][0], 1), vic_n_models=vic["rcp85"][1],
             vic_P_min=round(vic["rcp85"][2], 1), vic_P_max=round(vic["rcp85"][3], 1))
    wrf = CACHE / f"wrf_{p}.json"
    if wrf.exists():
        w = json.load(open(wrf))
        days = {d: v["rainnc_sum"] for d, v in w.items() if "1980-01-01" <= d <= "2009-12-31"}
        r["era5wrf_P_1980_2009"] = round(sum(v for v in days.values() if v is not None) / 30, 1)
        r["era5wrf_n_days"] = len(days)
        r["era5wrf_vs_vic_pct"] = round(100 * (r["era5wrf_P_1980_2009"] / r["vic_P_hist_rcp85"] - 1), 1)
    c6 = CACHE / f"c6hist_{p}.json"
    if c6.exists():
        c = json.load(open(c6))
        per_model = {}
        for m, d in c.items():
            if "Avg" in m:
                continue
            days = {dd: v["pr"] for dd, v in d["historical"].items() if "1980-01-01" <= dd <= "2009-12-31"}
            if sum(v is not None for v in days.values()) < 10000:  # e.g. CNRM-CM6-1-HR has no data at these points
                continue
            per_model[m] = sum(v for v in days.values() if v is not None) / 30
        r["cmip6_P_hist"] = round(np.mean(list(per_model.values())), 1)
        r["cmip6_n_models"] = len(per_model)
        r["cmip6_P_min"], r["cmip6_P_max"] = round(min(per_model.values()), 1), round(max(per_model.values()), 1)
        r["cmip6_vs_vic_pct"] = round(100 * (r["cmip6_P_hist"] / r["vic_P_hist_rcp85"] - 1), 1)
    rows.append(r)
m6 = pd.DataFrame(rows)
m6.to_csv(OUT / "v5_precip_sources.csv", index=False)
print("\nM6 precipitation sources (mm/yr):"); print(m6.to_string(index=False))

# --- H7: which met does the API's RCP4.5 pcp match in historical decades?
if MET != "-" and Path(MET).exists():
    met = pd.read_csv(MET)
    rows = []
    for p in API_POINTS:
        for m in models:
            for dec in ["1950-1959", "1960-1969", "1970-1979", "1980-1989", "1990-1999", "2000-2009", "2010-2019", "2050-2059"]:
                y0, y1 = map(int, dec.split("-"))
                a = api_dec(p, m, "rcp45", "pcp", dec)
                if np.isnan(a).all():
                    continue
                res = dict(point=p, model=m, decade=dec)
                for s in ("rcp45", "rcp85"):
                    sub = met[(met.model == m) & (met.scenario == s) & (met.point == p) & (met["var"] == "met_pcp") & (met.year >= y0) & (met.year <= y1)]
                    mon = sub[[f"m{i}" for i in range(1, 13)]].values * np.array([[calendar.monthrange(y, i)[1] for i in range(1, 13)] for y in sub.year])
                    r = np.nanmean(mon, axis=0)
                    res[f"maxabs_api45_vs_met{s[-2:]}"] = float(np.nanmax(np.abs(a - r)))
                    res[f"api45_annual"] = float(np.nansum(a)); res[f"met{s[-2:]}_annual"] = float(np.nansum(r))
                a45 = api_dec(p, m, "rcp45", "runoff", dec); a85 = api_dec(p, m, "rcp85", "runoff", dec)
                res["api_runoff_45_eq_85"] = bool(np.array_equal(a45, a85, equal_nan=True))
                res["api_pcp_45_eq_85"] = bool(np.array_equal(a, api_dec(p, m, "rcp85", "pcp", dec), equal_nan=True))
                rows.append(res)
    h7 = pd.DataFrame(rows)
    h7.to_csv(OUT / "v5_api_rcp45_met_match.csv", index=False)
    h7["api45_matches"] = np.select([h7.maxabs_api45_vs_met45 <= 1.0, h7.maxabs_api45_vs_met85 <= 1.0], ["met45", "met85"], "neither")
    print("\nH7 API rcp45 pcp vs raw met (max |diff| over 12 monthly means <= 1 mm), counts by decade:")
    print(h7.groupby(["decade", "api45_matches"]).size().unstack(fill_value=0).to_string())
    print("points with 'neither' (API cell is not the nearest native cell; see v6):", sorted(h7[h7.api45_matches == "neither"].point.unique()))
    print("API runoff rcp45 == rcp85 by decade:"); print(h7.groupby("decade").api_runoff_45_eq_85.mean().round(2).to_string())
    print("API pcp rcp45 == rcp85 by decade:"); print(h7.groupby("decade").api_pcp_45_eq_85.mean().round(2).to_string())
