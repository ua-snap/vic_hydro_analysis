#!/bin/bash
#SBATCH --job-name=ncar-figs
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/published/figs-%j.log

# Figures for the NCAR GDEX d010111 inquiry (published release only).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export MPLCONFIGDIR=/import/home/jdpaul3/tmp/mplconfig
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/scripts/fig_ncar_historical_forcing.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/published/forcing_year_alignment_published.csv \
    /import/home/jdpaul3/vic_hydro_analysis/correspondence/ncar_gdex_d010111 \
    ACCESS1-3 1985
