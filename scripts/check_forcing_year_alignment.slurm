#!/bin/bash
#SBATCH --job-name=vic-forcing-align
#SBATCH --partition=debug
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/forcing_align/slurm-%j.log
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
python -u /import/home/jdpaul3/vic_hydro_analysis/scripts/check_forcing_year_alignment.py \
    /beegfs/CMIP6/cparr4/AK_NCAR_12km/vic_hydro/monthly \
    /beegfs/CMIP6/cparr4/AK_NCAR_12km/met/monthly \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/forcing_align/forcing_year_alignment.csv \
    ACCESS1-3 CCSM4 MIROC5 HadGEM2-ES
