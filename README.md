# vic_hydro_analysis

An assessment of SNAP's curated **VIC-Hydro** dataset, and options for improving it.

## Background

SNAP curates the NCAR 12 km Alaska VIC hydrologic projections (Mizukami et al. 2022,
doi:10.5065/c3kn-2y77). We serve them as decadal means of monthly summaries per 12 km grid cell
through the SNAP data API, [earthmaps.io](https://earthmaps.io) and
[arcticeds.org](https://arcticeds.org).

Engineers and hydrologists have told us these data are not very useful as served:

- Runoff values could support streamflow modeling, but not at the grid-cell level we report.
- Several variables (temperature, precipitation, SWE) are already available from other SNAP
  datasets.

## Questions

1. **What is it?** The raw NCAR VIC product.
2. **What do we have?** The curated SNAP product.
3. **What could the raw data be used for?**
4. **What could the curated data be used for?**
5. **How could we make our holdings more useful?** We compare three options:
   - **Keep as is**
   - **Remove entirely**
   - **Reprocess**: re-curate the existing NCAR outputs (add baseflow and total runoff, change
     products, model agreement, a historical baseline) and aggregate by watershed rather than by
     grid cell.

The NCAR model run itself cannot be re-run or recalibrated, so every option works from the
existing outputs.

## Deliverable

A two-page summary for internal SNAP leads, distributed as a PDF with figures. Source and built
PDF live in `report/`.

## Repository layout

| Path | Contents |
|---|---|
| `vic_hydro_assessment.md` | Context brief: dataset provenance, the "uncalibrated" critique, and a key finding that baseflow was dropped in curation |
| `notes/` | Working notes and the detailed options analysis |
| `scripts/` | Analysis scripts and Slurm job files for the quantitative checks |
| `figures/` | Figures used in the report |
| `report/` | Two-page summary (Markdown source and PDF) |

## Reproducing

Analyses run on Chinook (UAF RCS) with the `snap-geo` conda environment, submitted through Slurm.
Source data are read from `/beegfs/CMIP6/cparr4/AK_NCAR_12km/` and never modified. To build the
report:

```sh
conda activate snap-geo
python scripts/fig_cell_vs_watershed.py <huc8.gpkg> <alaska_grid_12km_production.nc> figures/fig1_cell_vs_watershed
cd report
pandoc vic_hydro_summary.md --template=brief-template.tex --pdf-engine=xelatex \
  --resource-path=.:.. -o vic_hydro_summary.pdf
```

`brief-template.tex` is a minimal pandoc template. Chinook's system TeX Live is missing
`unicode-math`'s dependencies and `titling`/`titlesec`, so pandoc's default template won't build.
`huc8.gpkg` comes from `scripts/fetch_huc8.py`. The grid file comes from `ua-snap/ardac-curation`.

## References

- Mizukami, N., A. J. Newman, A. W. Wood, E. D. Gutmann, and J. J. Hamman, 2022: 21st century
  hydrologic projections for Alaska and Hawai'i. UCAR/NCAR/RAL. doi:10.5065/c3kn-2y77
- Mizukami et al., 2022: *Climate Services* 27, 100312. doi:10.1016/j.cliser.2022.100312
- Mendoza et al., 2015: *J. Hydrometeor.* 16(2). doi:10.1175/JHM-D-14-0104.1
- Curation code: [ua-snap/ardac-curation](https://github.com/ua-snap/ardac-curation/tree/main/curation/ncar12km_decadal_summaries)
- API: [ua-snap/data-api](https://github.com/ua-snap/data-api)
