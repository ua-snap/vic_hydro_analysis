#!/bin/bash
#SBATCH --job-name=vic-published
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/published/slurm-%j.log

# Re-run all checks on NCAR's PUBLISHED release (GDEX d010111), i.e. the data SNAP curated:
#   1. forcing-year alignment (all 10 models)  2. baseflow analysis  3. API-vs-raw provenance
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export MPLCONFIGDIR=/import/home/jdpaul3/tmp/mplconfig
export HDF5_USE_FILE_LOCKING=FALSE

REPO=/import/home/jdpaul3/vic_hydro_analysis
SRC=/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex
WORK=/import/home/jdpaul3/tmp/vic_hydro_analysis
OUT=$WORK/published
mkdir -p "$OUT/baseflow"

echo "=== 1. forcing-year alignment"
python -u "$REPO/scripts/check_forcing_year_alignment.py" "$SRC/vic/monthly" "$SRC/met/monthly" \
    "$OUT/forcing_year_alignment_published.csv" \
    ACCESS1-3 CanESM2 CCSM4 CSIRO-Mk3-6-0 GFDL-ESM2M HadGEM2-ES inmcm4 MIROC5 MPI-ESM-MR MRI-CGCM3

echo "=== 2. baseflow analysis"
python -u "$REPO/scripts/baseflow_analysis.py" "$SRC/vic/monthly" "$WORK/boundaries/huc8.gpkg" \
    "$WORK/precip_cmp/cache/vic_Fairbanks.json" "$OUT/baseflow" 20

echo "=== 3. API vs raw provenance"
python -u "$REPO/scripts/check_api_vs_raw.py" "$SRC/vic/monthly" "$WORK/precip_cmp/cache" \
    "$OUT/api_vs_raw_published.csv"
