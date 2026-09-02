# v1.3.0 change log

## Why this is a new model line

v1.2.0 used one fixed rectangular solid and a direct-pressure/electrostatic benchmark. That arrangement was useful for checking the automation plumbing, but it did not represent the PFM drive geometry and could invert the experimentally observed piezoelectric order. v1.3.0 is a separate folder and does not overwrite v1.2.0.

## Main changes

- PFM-converse voltage drive is the primary study; direct pressure is retained only as a separate benchmark.
- The checked tensor bridge is retained only as a provisional automation test; supplied papers are design references, not own-data material constants.
- The PFM target table is kept as apparent validation data, not as constitutive input.
- The expected piezoelectric order is stated explicitly as BiOI > BiOBr > BiOCl and is checked before COMSOL is started.
- SEM/TEM archive metadata are summarized with SHA-256 digests; unmeasured morphology dimensions are never guessed.
- COMSOL selections, mesh limits, electrode mode, dielectric status, and retry diagnostics are recorded in the run outputs.
- Added the DFT-informed apparent-response branch. `BiOX_FEA_DFT.zip` is
  parsed into full tetragonal `C^E` matrices and electronic/ionic dielectric
  tensors; the VASP zero macroscopic piezoelectric tensor is retained as
  provenance. The measured SSPFM `d33_app` is used only through the documented
  response-level `e33_app` closure.
- Verified a real COMSOL 6.3 run in
  `results/pfm_dft_apparent/`; its apparent order is BiOI > BiOBr
  > BiOCl. Publication-ready individual and 2x3 figures are in
  `figures/pfm_dft_apparent_v1/`.

## Not claimed by this release

The current template does not yet provide a validated tip-contact footprint or
an independently measured full bulk piezoelectric tensor. Consequently,
v1.3.0 is a traceable apparent-PFM comparison framework, not an absolute
calibration of intrinsic bulk `d33`. The remaining inputs for an intrinsic
claim are listed in `OWN_DATA_REQUIREMENTS.md`.
