#!/bin/bash
#SBATCH --job-name=vic-api-vs-raw
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:30:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/api_vs_raw/slurm-%j.log

# Which raw NCAR scenario does each curated /hydrology value come from? See check_api_vs_raw.py.
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE

python -u /import/home/jdpaul3/vic_hydro_analysis/scripts/check_api_vs_raw.py \
    /beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/monthly \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/precip_cmp/cache \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/api_vs_raw/api_vs_raw.csv
