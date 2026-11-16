#!/bin/bash
#SBATCH --job-name=verify-v2-align
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --mem=64G
#SBATCH --time=02:30:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/verify/logs/v2-%j.log
# Verification job 2: RCP4.5 vs RCP8.5 files, forcing match, glacier mask over all years (read-only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/review/scripts/v2_alignment.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /beegfs/CMIP6/cparr4/AK_NCAR_12km \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/verify/align 20
