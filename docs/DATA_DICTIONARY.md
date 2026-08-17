# Data dictionary

## Numerical tables

| File | Content | Key units |
|---|---|---|
| `data/benchmark_100MPa.csv` | Primary 100 MPa COMSOL outputs for the original reference parameterization | V, Pa, MPa, nm |
| `data/benchmark_100MPa.json` | Machine-readable result records and configuration snapshot | SI units unless named otherwise |
| `data/pressure_sweep_0_100MPa.csv` | Potential difference at six pressure levels | MPa, $\mu$V |
| `data/pressure_regression.csv` | Linear slope, intercept, and $R^2$ for each compound | $\mu$V MPa$^{-1}$, $\mu$V |
| `data/dielectric_convention_100MPa.csv` | Consistent electronic- and total-dielectric sensitivity results | $\mu$V, kV m$^{-1}$, $\mu$C m$^{-2}$, MPa |

In `benchmark_100MPa.csv`, `delta_v_mv` is expressed in millivolts despite the lowercase field name. The publication figures convert it to microvolts. `top_average_w_m` is a coupling-operator output retained for auditability; it is not used as the principal comparison metric.

## Image data

`data/raw_potential_maps/` contains the three zero-centered potential maps exported from COMSOL before assembly into the independent-scale comparison. These raster exports are retained because the proprietary `.mph` binaries are excluded from the repository.

`figures/` contains the final shared-scale stress and potential maps, the zero-baseline 100 MPa comparison, the pressure-response curves, the independent-scale potential panel, and the dielectric-convention sensitivity plot.

## Configuration

`config/biox_materials.json` is the authoritative repository input for geometry, mesh controls, constitutive tensors, PFM amplitudes, and provenance notes. Values used for a publication should be cited to their original experimental or computational source rather than to the JSON file alone.
