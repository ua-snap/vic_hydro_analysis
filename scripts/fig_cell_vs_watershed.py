"""Figure: one VIC 12 km grid cell vs. a HUC8 watershed.

Shows why per-cell runoff is the wrong unit for streamflow users: a typical HUC8 spans
dozens of VIC cells, and flow at its outlet integrates all of them.

Usage:
    python fig_cell_vs_watershed.py <huc8.gpkg> <alaska_grid_12km_production.nc> <out_prefix> [huc8_id]

Inputs:
    huc8.gpkg  - from scripts/fetch_huc8.py (earthmaps.io /boundary HUC8 polygons)
    grid .nc   - ua-snap/ardac-curation curation/ncar12km_decadal_summaries/alaska_grid_12km_production.nc
Outputs:
    <out_prefix>.png (300 dpi) and <out_prefix>.pdf
"""

import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from pyproj import Transformer
from shapely.geometry import box

HUC_GPKG, GRID_NC, OUT = sys.argv[1:4]
HUC_ID = sys.argv[4] if len(sys.argv) > 4 else "19020402"  # Matanuska

# NCAR/WRF polar stereographic grid (as in ardac-curation compute_summaries.py); WRF sphere
STERE = "+proj=stere +lat_0=90 +lat_ts=64 +lon_0=-150 +R=6370000 +x_0=0 +y_0=0 +units=m"
DX = 12000.0

# palette: reference dataviz palette (light mode)
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
BASIN, CELL, GRIDLINE, HUCLINE = "#2a78d6", "#eb6834", "#b4b3ad", "#c9c8c2"

# --- grid cell polygons (centers from lat/lon, snapped to the regular 12 km lattice)
ds = xr.open_dataset(GRID_NC)
to_st = Transformer.from_crs(4326, STERE, always_xy=True)
xc, yc = to_st.transform(ds.lon.values, ds.lat.values)
x = np.nanmedian(xc, axis=0)
y = np.nanmedian(yc, axis=1)
X, Y = np.meshgrid(x, y)
cells = gpd.GeoDataFrame(
    geometry=[box(a - DX / 2, b - DX / 2, a + DX / 2, b + DX / 2) for a, b in zip(X.ravel(), Y.ravel())],
    crs=STERE,
)

hucs = gpd.read_file(HUC_GPKG)
basin = hucs[hucs.huc8 == HUC_ID].to_crs(STERE)
name = basin.name.iloc[0]
bgeom = basin.geometry.iloc[0]

hit = cells[cells.intersects(bgeom)].copy()
centers_in = hit[hit.centroid.within(bgeom)]
basin_km2 = bgeom.area / 1e6
print(f"{name} ({HUC_ID}): {basin_km2:,.0f} km2; {len(centers_in)} cell centers inside, "
      f"{len(hit)} cells intersect; area/144 = {basin_km2 / 144:.0f}")

all_km2 = hucs.to_crs(3338).area / 1e6
print(f"All HUC8: n={len(hucs)}, median {all_km2.median():,.0f} km2 "
      f"(~{all_km2.median() / 144:.0f} cells), range {all_km2.min():,.0f}-{all_km2.max():,.0f} km2")

# pick the cell nearest the basin's representative point to highlight
rp = bgeom.representative_point()
one = centers_in.loc[[centers_in.centroid.distance(rp).idxmin()]]

# --- plot
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": INK2})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.45), gridspec_kw={"width_ratios": [1.25, 1]})
fig.patch.set_facecolor(SURFACE)

h3338 = hucs.to_crs(3338)
h3338.plot(ax=a1, facecolor="none", edgecolor=HUCLINE, linewidth=0.4)
h3338[h3338.huc8 == HUC_ID].plot(ax=a1, facecolor=BASIN, edgecolor=BASIN, linewidth=0.6)
a1.set_title(f"Alaska's {len(hucs)} HUC8 watersheds", loc="left", fontsize=9, color=INK)
a1.annotate(name, xy=basin.to_crs(3338).representative_point().iloc[0].coords[0],
            xytext=(25, -28), textcoords="offset points", fontsize=8, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))

hit.plot(ax=a2, facecolor="none", edgecolor=GRIDLINE, linewidth=0.5)
basin.plot(ax=a2, facecolor=BASIN, alpha=0.18, edgecolor="none")
basin.boundary.plot(ax=a2, color=BASIN, linewidth=1.4)
one.plot(ax=a2, facecolor=CELL, edgecolor=SURFACE, linewidth=1.0)
a2.set_title(f"{name} watershed on the VIC 12 km grid", loc="left", fontsize=9, color=INK)
a2.annotate("1 grid cell (144 km²):\nwhat the API returns today",
            xy=one.centroid.iloc[0].coords[0], xytext=(1.02, 0.80), textcoords="axes fraction",
            fontsize=7.5, color=INK, va="top",
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
a2.text(1.02, 0.30, f"Watershed: {basin_km2:,.0f} km²\n≈ {len(centers_in)} grid cells.\n"
        f"Flow at the outlet\nintegrates all of them.",
        transform=a2.transAxes, fontsize=7.5, color=INK, va="top")

for a in (a1, a2):
    a.set_axis_off()
    a.set_aspect("equal")
a1.set_xlim(h3338.total_bounds[[0, 2]])
a1.set_ylim(h3338.total_bounds[[1, 3]])

fig.tight_layout(w_pad=0.5)
fig.subplots_adjust(right=0.80)
for ext in ("png", "pdf"):
    fig.savefig(f"{OUT}.{ext}", dpi=300, facecolor=SURFACE)
print("wrote", OUT + ".png/.pdf")
