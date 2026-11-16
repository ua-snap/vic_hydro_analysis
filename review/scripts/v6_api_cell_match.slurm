#!/bin/bash
#SBATCH --job-name=verify-v6-apicell
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:40:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v6-%j.log
# Verification job 6: which native VIC cell the API serves at each test point (read-only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v6_api_cell_match.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/precip_cmp/cache \
    /import/home/jdpaul3/vic_hydro_analysis/review/results/v6_api_cell_match.csv 8
