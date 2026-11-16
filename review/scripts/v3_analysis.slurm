#!/bin/bash
#SBATCH --job-name=verify-v3-analysis
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:40:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v3-%j.log
# Verification job 3: analysis of the v1 climatologies (baseflow share, change, HUC8, sensitivity).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v3_analysis.py \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/verify/clim \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/verify/align/glacier_allyears.nc \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/boundaries/huc8.gpkg \
    /import/home/jdpaul3/vic_hydro_analysis/review/results
