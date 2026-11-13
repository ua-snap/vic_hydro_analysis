"""Download NCAR's published Alaska VIC release (GDEX d010111) monthly wf + met files.

This is the release SNAP curated (verified by MD5 against ardac-curation's Feb 2023 wget
checksums). Anonymous HTTPS via OSDF; no token.

Writes <out_root>/{vic,met}/monthly/{BCSD/<model>/<rcp>,daymet}/<file>.nc, mirroring GDEX paths.
Each file is downloaded to <file>.part and renamed only when complete, so reruns resume safely.
A manifest (path, bytes, md5, status) is written to <out_root>/manifest.csv.

Usage: python download_gdex.py <out_root> [n_parallel]
"""

import csv
import hashlib
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(sys.argv[1])
NPAR = int(sys.argv[2]) if len(sys.argv) > 2 else 4
BASE = "https://osdf-director.osg-htc.org/ncar/gdex/d010111/alaska"
MODELS = ["ACCESS1-3", "CanESM2", "CCSM4", "CSIRO-Mk3-6-0", "GFDL-ESM2M",
          "HadGEM2-ES", "inmcm4", "MIROC5", "MPI-ESM-MR", "MRI-CGCM3"]
SCENARIOS = ["rcp45", "rcp85"]


def targets():
    for grp, tag in [("vic", "wf"), ("met", "met")]:
        for m in MODELS:
            for s in SCENARIOS:
                for y in range(1950, 2100):
                    rel = f"{grp}/monthly/BCSD/{m}/{s}/{m}_{s}_BCSD_{tag}_{y}.nc"
                    yield rel, True
        for y in range(1980, 2018):  # Daymet run; 2017 may not exist (preliminary had 1980-2016)
            yield f"{grp}/monthly/daymet/daymet_{tag}_{y}.nc", y <= 2016


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(rel, required):
    dst = OUT / rel
    if dst.exists():
        return rel, dst.stat().st_size, None, "exists"
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(dst.suffix + ".part")
    req = urllib.request.Request(f"{BASE}/{rel}", headers={"User-Agent": "research-download/1.0"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
                expected = int(r.headers.get("Content-Length", -1))
                n = 0
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    n += len(chunk)
            if expected >= 0 and n != expected:
                raise IOError(f"short read {n}/{expected}")
            part.rename(dst)
            return rel, n, md5(dst), "downloaded"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                part.unlink(missing_ok=True)
                return rel, 0, None, "404-required" if required else "404-optional"
            err = e
        except Exception as e:  # network hiccup, truncated read
            err = e
        part.unlink(missing_ok=True)
        time.sleep(5 * (attempt + 1))
    return rel, 0, None, f"failed: {err}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    todo = list(targets())
    print(f"{len(todo)} targets -> {OUT}", flush=True)
    rows, t0 = [], time.time()
    with ThreadPoolExecutor(NPAR) as ex:
        futs = [ex.submit(fetch, rel, req) for rel, req in todo]
        for i, fu in enumerate(as_completed(futs), 1):
            rows.append(fu.result())
            if i % 250 == 0 or not rows[-1][3] in ("downloaded", "exists"):
                gb = sum(r[1] for r in rows) / 1e9
                print(f"{i}/{len(todo)}  {gb:.1f} GB  {time.time() - t0:.0f}s  last: {rows[-1][0]} "
                      f"{rows[-1][3]}", flush=True)
    with open(OUT / "manifest.csv", "a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["path", "bytes", "md5", "status"])
        w.writerows(sorted(rows))
    bad = [r for r in rows if r[3].startswith(("failed", "404-required"))]
    print(f"done: {sum(r[3] == 'downloaded' for r in rows)} downloaded, "
          f"{sum(r[3] == 'exists' for r in rows)} existed, "
          f"{sum(r[3] == '404-optional' for r in rows)} optional missing, {len(bad)} problems", flush=True)
    for r in bad[:50]:
        print("PROBLEM", r, flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
