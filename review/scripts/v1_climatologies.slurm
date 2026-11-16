#!/bin/bash
#SBATCH --job-name=verify-v1-clim
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v1-%j.log
# Verification job 1: period climatologies from the published monthly wf files (read-only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v1_climatologies.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/verify/clim 16
