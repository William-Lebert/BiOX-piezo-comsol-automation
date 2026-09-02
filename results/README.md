# Verified result summaries

This directory contains compact CSV/JSON tables and run logs from the
validated v1.3.0 calculations. Solved material-specific MPH files and native
COMSOL export folders are intentionally omitted; the reusable template and
the publication figures are retained elsewhere in the repository.

## `pfm_dft_apparent/`

The active DFT-informed converse-PFM study. DFT `C^E` and dielectric tensors
are combined with the measured SSPFM `d33_app` through an explicitly labelled
apparent-response closure. The simulated order is BiOI > BiOBr > BiOCl.

## `direct_pressure_100MPa/`

The 100 MPa direct-pressure benchmark. It reports the pressure-induced
potential difference under the specified grounded-bottom boundary condition;
it is complementary to, and not interchangeable with, the converse-PFM
observable.

## `historical_pfm_gaussian/`

The earlier reduced 2D-to-3D Gaussian-contact run. Its ranking mismatch is
retained as a diagnostic record and is not used as the active material result.
