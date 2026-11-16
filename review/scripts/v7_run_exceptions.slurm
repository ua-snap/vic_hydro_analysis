#!/bin/bash
#SBATCH --job-name=verify-v7-exceptions
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v7-%j.log
# Verification job 7: CCSM4 and CanESM2 exceptions to the shared-historical-run claim (read-only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v7_run_exceptions.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/verify/align/glacier_allyears.nc \
    /import/home/jdpaul3/vic_hydro_analysis/review/results/v7_run_exceptions.csv
