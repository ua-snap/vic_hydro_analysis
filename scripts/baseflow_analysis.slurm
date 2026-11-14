#!/bin/bash
#SBATCH --job-name=vic-baseflow
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/baseflow/slurm-%j.log

# Baseflow vs surface runoff from NCAR monthly wf files (read-only). See baseflow_analysis.py.
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo   # before `set -u`: conda's gdal activate hook references unset vars
set -euo pipefail
export MPLCONFIGDIR=/import/home/jdpaul3/tmp/mplconfig
export HDF5_USE_FILE_LOCKING=FALSE   # read-only access to another user's files

REPO=/import/home/jdpaul3/vic_hydro_analysis
WORK=/import/home/jdpaul3/tmp/vic_hydro_analysis
python -u "$REPO/scripts/baseflow_analysis.py" \
    /beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/monthly \
    "$WORK/boundaries/huc8.gpkg" \
    "$WORK/precip_cmp/cache/vic_Fairbanks.json" \
    "$WORK/baseflow" \
    20
