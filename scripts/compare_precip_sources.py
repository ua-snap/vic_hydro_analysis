"""Compare VIC-Hydro forcing precipitation with SNAP's other precipitation products at a few points.

Question: if a user pairs VIC runoff/ET with precipitation from a *different* SNAP dataset,
how far off is the water balance?

Sources (all via the SNAP data API, earthmaps.io):
  - VIC-Hydro `pcp` (/hydrology/point): BCSD-downscaled CMIP5 forcing used to drive VIC,
    decadal means of monthly totals. Historical = mean of 1980s, 1990s, 2000s decades.
  - ERA5-WRF `rainnc_sum` (/era5wrf/point): 4 km dynamically downscaled reanalysis, daily, 1980-2009.
  - CMIP6 downscaled `pr` (/cmip6_downscaled/point): 4 km, daily; historical 1980-2009 and
    ssp585 2070-2099 (excluding the multi-model averages).

Also reports VIC `evap` and `runoff` (surface only) so the implied water-balance residual
P - ET - R_surface can be shown with each choice of P.

Usage: python compare_precip_sources.py <cache_dir> <out_csv>
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

CACHE, OUT = Path(sys.argv[1]), sys.argv[2]
CACHE.mkdir(parents=True, exist_ok=True)
API = "https://earthmaps.io"

POINTS = {
    "Fairbanks": (64.84, -147.72),
    "Palmer": (61.60, -149.11),
    "Juneau": (58.30, -134.42),
    "Bethel": (60.79, -161.76),
    "Utqiagvik": (71.29, -156.79),
}
HIST_DECADES = ["1980-1989", "1990-1999", "2000-2009"]
FUT_DECADES = ["2070-2079", "2080-2089", "2090-2099"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def get(name, url):
    f = CACHE / f"{name}.json"
    if not f.exists():
        for attempt in range(3):  # large daily responses sometimes arrive truncated
            try:
                with urllib.request.urlopen(url, timeout=600) as r:
                    f.write_bytes(r.read())
                break
            except Exception as e:  # out of domain, 404, truncated read, etc.
                print(f"  {name} (attempt {attempt + 1}): {e}")
                time.sleep(5)
        else:
            return None
        time.sleep(1)
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return None


def vic_annual(d, var, decades, scenario):
    """Per-model annual total (sum of monthly decadal means), averaged over decades.

    Models with null values are skipped (HadGEM2-ES has null pcp/tmax/tmin in the API).
    """
    out = {}
    for model, sc in d.items():
        cells = [sc[scenario][m][dec][var] for dec in decades for m in MONTHS]
        if any(c is None for c in cells):
            continue
        vals = [sum(float(sc[scenario][m][dec][var]) for m in MONTHS) for dec in decades]
        out[model] = np.mean(vals)
    return pd.Series(out)


def daily_annual_mean(series, y0, y1):
    """series: {date: value}; mean annual total over y0..y1 inclusive."""
    s = pd.Series(series, dtype=float)
    s.index = pd.to_datetime(s.index)
    s = s[(s.index.year >= y0) & (s.index.year <= y1)]
    return s.groupby(s.index.year).sum().mean()


rows = []
for name, (lat, lon) in POINTS.items():
    print(name)
    vic = get(f"vic_{name}", f"{API}/hydrology/point/{lat}/{lon}")
    wrf = get(f"wrf_{name}", f"{API}/era5wrf/point/{lat}/{lon}?vars=rainnc_sum")
    c6h = get(f"c6hist_{name}", f"{API}/cmip6_downscaled/point/{lat}/{lon}?vars=pr&scenarios=historical")
    c6f = get(f"c6ssp585_{name}", f"{API}/cmip6_downscaled/point/{lat}/{lon}?vars=pr&scenarios=ssp585")

    r = {"location": name, "lat": lat, "lon": lon}
    if vic:
        p45 = vic_annual(vic, "pcp", HIST_DECADES, "rcp45")
        p85 = vic_annual(vic, "pcp", HIST_DECADES, "rcp85")
        r["vic_hist_rcp45_vs_rcp85_maxdiff"] = float((p45 - p85).abs().max())
        pf = vic_annual(vic, "pcp", FUT_DECADES, "rcp85")
        r["vic_models_with_pcp"] = len(p85)
        r["vic_models_null_pcp"] = ",".join(sorted(set(vic) - set(p85.index)))
        r.update(
            vic_P_hist=p85.mean(), vic_P_hist_min=p85.min(), vic_P_hist_max=p85.max(),
            vic_ET_hist=vic_annual(vic, "evap", HIST_DECADES, "rcp85").mean(),
            vic_Rsurf_hist=vic_annual(vic, "runoff", HIST_DECADES, "rcp85").mean(),
            vic_dP_pct_rcp85=((pf - p85) / p85 * 100).mean(),
            vic_dP_pct_rcp85_min=((pf - p85) / p85 * 100).min(),
            vic_dP_pct_rcp85_max=((pf - p85) / p85 * 100).max(),
        )
    if wrf:
        r["era5wrf_P_1980_2009"] = daily_annual_mean(
            {k: v["rainnc_sum"] for k, v in wrf.items()}, 1980, 2009)
    if c6h:
        models = [m for m in c6h if "ModelAvg" not in m]
        h = pd.Series({m: daily_annual_mean({k: v["pr"] for k, v in c6h[m]["historical"].items()},
                                            1980, 2009) for m in models})
        r.update(cmip6_P_hist=h.mean(), cmip6_P_hist_min=h.min(), cmip6_P_hist_max=h.max(),
                 cmip6_n_models=len(models))
        if c6f:
            fm = [m for m in models if m in c6f and "ssp585" in c6f[m]]
            f = pd.Series({m: daily_annual_mean({k: v["pr"] for k, v in c6f[m]["ssp585"].items()},
                                                2070, 2099) for m in fm})
            d = (f - h[fm]) / h[fm] * 100
            r.update(cmip6_dP_pct_ssp585=d.mean(), cmip6_dP_pct_ssp585_min=d.min(),
                     cmip6_dP_pct_ssp585_max=d.max(), cmip6_ssp585_n_models=len(fm))
    rows.append(r)

df = pd.DataFrame(rows)
for src in ["era5wrf_P_1980_2009", "cmip6_P_hist"]:
    if src in df:
        df[f"{src}_vs_vic_pct"] = (df[src] - df["vic_P_hist"]) / df["vic_P_hist"] * 100
        # implied residual P - ET - Rsurf (≈ baseflow + storage change) with each P
        df[f"resid_with_{src}"] = df[src] - df["vic_ET_hist"] - df["vic_Rsurf_hist"]
df["resid_with_vic_P"] = df["vic_P_hist"] - df["vic_ET_hist"] - df["vic_Rsurf_hist"]
df.round(1).to_csv(OUT, index=False)
pd.set_option("display.width", 250)
print(df.round(0).T.to_string())
