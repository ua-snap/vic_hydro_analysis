#!/bin/bash
#SBATCH --job-name=summary-figs
#SBATCH --partition=t1small
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/import/home/jdpaul3/tmp/vic_hydro_analysis/published/summary-figs-%j.log

# Section 3 figures for the two-page summary (published GDEX d010111 results).
source /home/jdpaul3/miniconda3/etc/profile.d/conda.sh
conda activate snap-geo
set -euo pipefail
export MPLCONFIGDIR=/import/home/jdpaul3/tmp/mplconfig
export HDF5_USE_FILE_LOCKING=FALSE
REPO=/import/home/jdpaul3/vic_hydro_analysis
python -u "$REPO/scripts/fig_summary_issues.py" \
    /import/home/jdpaul3/tmp/vic_hydro_analysis/published/baseflow/wf_monthly_climatologies.nc \
    "$REPO/results/published/runoff_change_surface_vs_total.csv" \
    "$REPO/correspondence/ncar_gdex_d010111/timeseries_ACCESS1-3.csv" \
    "$REPO/figures" "$REPO/results/published"
