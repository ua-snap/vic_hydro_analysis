#!/bin/bash
#SBATCH --job-name=gdex-vic-dl
#SBATCH --partition=transfer
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=/import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex/download-%j.log

# Download NCAR GDEX d010111 (published Alaska VIC release) monthly wf + met files. Resumable.
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
python -u /import/home/jdpaul3/vic_hydro_analysis/scripts/download_gdex.py \
    /import/beegfs/CMIP6/jdpaul3/vic_hydro_gdex 4
