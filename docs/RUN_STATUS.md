# Run status

## Completed in this workspace

- The v1.3.0 directory was created independently of v1.2.0.
- JSON configuration and the 2D tensor conversion pass validation.
- The derived literature `d11` order and the supplied apparent PFM target order are both BiOI > BiOBr > BiOCl.
- The supplied SEM/TEM archive was inventoried without copying raw images into the release folder.
- PFM-converse, direct-pressure, and six-point pressure-sweep dry runs completed.
- A real COMSOL 6.3 Gaussian-contact PFM-converse run completed for BiOCl, BiOBr and BiOI. Its compact scalar CSV/JSON table and log are retained in `results/historical_pfm_gaussian/`; solved MPH files are excluded from this release.
- A real COMSOL 6.3 100 MPa direct-pressure benchmark completed for all three materials. The induced potential spans approximately 14.89–16.18 mV (BiOCl, BiOBr, BiOI respectively); its compact scalar CSV/JSON table and log are in `results/direct_pressure_100MPa/`.
- Enlarged English-labelled individual panels and a 2×3 composite were generated in `figures/pfm_converse_gaussian_v5/`. Added labels use Times New Roman and the files carry 300 dpi metadata.
- A matching common-scale stress/piezoelectric-potential 6-panel figure and six individual panels were generated in `figures/direct_pressure_100MPa_common/`.
- The BiOBr/BiOI separation audit was completed. Equal-size `e33` closure and literature-size priors do not create a robust gap; a large generic `e33` multiplier reverses the ranking and is rejected. Details are in `PARAMETER_SENSITIVITY.md`.
- Three dependency-free regression tests passed.
- The supplied `BiOX_FEA_DFT.zip` was parsed and recorded in
  `config/materials_dft_apparent.json`. It provides DFT `C^E`, electronic and
  ionic dielectric tensors, and a zero total macroscopic piezoelectric tensor
  for each material.
- A real COMSOL 6.3 DFT-informed apparent-PFM run completed. Its compact
  scalar CSV/JSON table and log are in `results/pfm_dft_apparent/`. The simulated apparent order is
  BiOI > BiOBr > BiOCl, matching the SSPFM target order. The corresponding
  title-free 2x3 figure and individual panels are in
  `figures/pfm_dft_apparent_v1/`.

## Interpretation boundary

The Gaussian-contact run is an interface-qualified field-distribution diagnostic.
Its simulated order is BiOCl > BiOI > BiOBr, which does not reproduce the
measured apparent PFM order BiOI > BiOBr > BiOCl. This mismatch is retained as a
diagnostic and must not be hidden by material-specific colour limits, amplitude
scaling or post-processing. The absolute simulated converse displacement is
also not an intrinsic `d33` calibration because the template lacks a validated
contact-partitioned electrode and uses sensitivity dielectric entries.

The DFT-informed run removes the provisional dielectric input, but it remains a
measurement-level apparent-response model: the VASP total macroscopic
piezoelectric tensor is zero, and the effective `e33_app` channel is derived
from measured SSPFM `d33_app` and DFT `C33`. The resulting common factor between
simulated and measured response is a property of the present contact/geometry
proxy and must not be promoted to a material constant.

## Next validation steps

1. Add a validated local contact selection and contact-transfer calibration if
   absolute PFM displacement is to be interpreted beyond the apparent branch.
2. Record SEM/TEM lateral dimensions from scale bars and run an ensemble of
   morphology-conditioned geometries.
3. Solve the direct-pressure sweep with fixed common plot limits and report the
   pressure slope separately from the PFM-converse observable.
