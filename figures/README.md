# Figure sets

The figure directories contain publication-oriented PNG exports. All plates
use English annotations, Times New Roman for added labels, and 300 dpi PNG
metadata. The native COMSOL colour fields are preserved; numerical comparisons
must be made from the CSV/JSON result tables.

## Active apparent-PFM set

`pfm_dft_apparent_v1/` is the primary figure set for the current release. It
contains a title-free 2x3 composite and six individual plates. The upper row
shows von Mises stress and the lower row shows the prescribed Gaussian electric
potential used for the converse-PFM excitation. The associated quantitative
observable is the simulated effective surface-normal response, not the colour
intensity of either map.

## Direct-pressure set

`direct_pressure_100MPa_common/` is a supplementary direct-piezoelectric
benchmark at 100 MPa. The six-panel figure uses common 0–150 MPa stress limits
and −10 to +10 mV potential limits. It describes pressure-induced potential
under the specified grounded-bottom boundary condition and is not a PFM voltage
drive.

## Historical diagnostic set

`pfm_converse_gaussian_v5/` records the earlier reduced 2D-to-3D closure. Its
ranking mismatch with SSPFM is retained for transparency and should not be
used as the active material result.

## Regeneration

After a COMSOL run, compose the active apparent-PFM set with:

```powershell
python src/compose_sci_figures.py `
  --results-dir comsol_run/reproduced/pfm_dft_apparent `
  --output-dir figures/pfm_dft_apparent_v1 `
  --mode pfm-converse
```

The compositor expects the native PNG exports in the selected results
directory. For direct-pressure exports, use the common-scale re-export script
before composing the six-panel figure; see `src/reexport_common_scale.py`.
