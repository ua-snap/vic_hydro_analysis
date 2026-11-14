"""Fetch all Alaska HUC8 polygons from the SNAP data API (earthmaps.io) into one GeoPackage.

Usage: python fetch_huc8.py <hucs.json from https://earthmaps.io/places/hucs> <out.gpkg>
"""

import json
import sys
import time
import urllib.request

import geopandas as gpd
import pandas as pd

hucs_json, out = sys.argv[1], sys.argv[2]
hucs = [h for h in json.load(open(hucs_json)) if h["area_type"] == "HUC8"]

frames = []
for h in hucs:
    url = f"https://earthmaps.io/boundary/area/{h['id']}"
    with urllib.request.urlopen(url, timeout=60) as r:
        gj = json.load(r)
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    g = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
    g = g.dissolve().reset_index(drop=True)[["geometry"]]
    g["huc8"], g["name"] = h["id"], h["name"]
    frames.append(g)
    time.sleep(0.2)  # be polite to our own API

gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
gdf.to_file(out, driver="GPKG")
print(len(gdf), "HUC8 polygons written to", out)
