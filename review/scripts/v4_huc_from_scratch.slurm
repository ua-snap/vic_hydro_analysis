#!/bin/bash
#SBATCH --job-name=verify-v4-huc
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v4-%j.log
# Verification job 4: opposite-sign HUC8s recomputed straight from raw monthly files (read-only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v4_huc_from_scratch.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/boundaries/huc8.gpkg \
    /import/home/jdpaul3/vic_hydro_analysis/review/results/v4_huc8_from_scratch.csv \
    19010304 19020701 19060501 19010204
