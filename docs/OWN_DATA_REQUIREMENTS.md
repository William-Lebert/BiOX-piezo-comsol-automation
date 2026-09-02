# Own-data requirements for a BiOX 3D PFM model

The supplied papers are design references only. They are not used as material
constants, calibration values or ranking constraints in the own-data model.

## Data already available

- SSPFM raw files for BiOCl, BiOBr and BiOI, together with the MFP-3D Origin
  settings: 1 V drive, 1 Hz scan, 10 μm² scan area, 1 mm pressed pellet and
  controlled laboratory conditions.
- SEM/TEM images with scale bars. These support manual measurement of lateral
  size, thickness and aspect-ratio distributions; the images alone do not give
  a unique 3D geometry until those measurements are recorded.
- Phase/structure characterization files available in the project repository
  (for example XRD/SAED). These can constrain phase identity, lattice
  parameters and preferred orientation, but do not by themselves determine a
  piezoelectric tensor.

## DFT data now available for the apparent branch

`BiOX_FEA_DFT.zip` supplies a full tetragonal `C^E` matrix and separate
electronic/ionic dielectric tensors for BiOCl, BiOBr and BiOI. These values are
now used by `config/materials_dft_apparent.json`. The VASP total macroscopic
piezoelectric tensor is zero in the supplied calculations, so it is retained as
provenance rather than used to generate an intrinsic PFM response. The active
branch therefore uses the measured SSPFM `d33_app` as a response-level closure.

This is sufficient for a defensible apparent-response comparison, but not for
an intrinsic bulk piezoelectric claim. The remaining contact and orientation
data below control the interpretation of absolute PFM amplitude.

## P0: required before claiming a material-specific 3D prediction

### 1. Complete constitutive tensors for each halide

For a static stress–charge COMSOL model, provide one internally consistent set
for each material:

- elastic stiffness (C^E), preferably the full 6×6 matrix (for tetragonal
  symmetry at least (C_{11}, C_{12}, C_{13}, C_{33}, C_{44}, C_{66}));
- piezoelectric tensor in either (e) (3×6) or (d) form, including the
  out-of-plane and shear terms relevant to a surface-normal PFM response
  (typically (e_{31}, e_{33}, e_{15}) or the equivalent (d) entries);
- dielectric permittivity at constant strain (arepsilon^S), including
  (arepsilon_{11}), (arepsilon_{33}), and frequency/loss information if
  the PFM drive is treated as AC;
- sign convention, crystallographic axis definition, units and uncertainty for
  every entry.

These quantities should come from your own measurements (or a clearly
documented calculation performed for your samples). A PFM (d_{33}^{app}) value
alone cannot recover all of (C^E), (e) and (arepsilon^S).

### 2. Crystal orientation and texture

Record the relation between the crystallographic axes and the flake/pellet
surface. Useful evidence includes XRD pole figures, texture analysis, SAED
orientation statistics or a documented random-orientation assumption. Without
this information, a surface-normal PFM value cannot be mapped uniquely onto a
tensor component.

### 3. PFM contact calibration

The current instrument settings do not specify the electromechanical transfer
function. For each measurement series, record:

- probe radius, spring constant and deflection sensitivity;
- contact force/setpoint, indentation or contact stiffness;
- AC voltage actually applied at the tip–sample junction, DC offset and phase
  convention;
- resonance/measurement bandwidth, lock-in time constant and the z-sensitivity
  calibration factor;
- substrate/electrode stack, grounding condition, leakage and sample roughness.

These data are needed to convert apparent SSPFM displacement into a model
boundary condition and to distinguish intrinsic response from contact transfer.

## P1: geometry and mechanical boundary data

- Manually measured lateral length/width and thickness distributions from
  SEM/TEM scale bars for every material; report median and spread rather than a
  single image-selected value.
- Flake orientation, stacking/aggregation and pressed-pellet porosity or solid
  fraction.
- Pellet thickness, density and elastic support/substrate properties. Density
  is required for dynamic studies; for static pressure it is still useful for
  checking the plausibility of the effective modulus.
- Tip contact footprint or a bounded contact-radius range. If unavailable,
  report the contact radius as a sensitivity parameter rather than a measured
  quantity.

## P2: optional data for stronger mechanistic claims

- Frequency-dependent dielectric constant and loss (LCR/impedance data).
- Mechanical modulus from nanoindentation, ultrasonic measurement or a
  compression test on the pressed pellet.
- Spatially resolved PFM amplitude/phase distributions and replicate statistics
  for single flakes, not only the pellet average.
- Conductivity/leakage and surface-charge data if the model is extended to
  carrier transport or piezo-photocatalytic reaction rates.

## What remains unresolved for an intrinsic interpretation

The DFT-informed branch now separates BiOI and BiOBr at the apparent-response
level because their measured SSPFM targets are used explicitly and the DFT
elastic/dielectric data are no longer placeholders. It still does not identify
an intrinsic bulk `e/d` tensor. The highest-priority additions for that stronger
claim are:

1. a validated non-centrosymmetric structural/polarization model and full 3-D
   `e/d` tensor for each sample;
2. crystallographic orientation/texture relative to the measured surface; and
3. probe radius, contact force/stiffness, actual AC voltage and z-sensitivity
   calibration.

Until these are available, report the SSPFM order and the COMSOL maps as
apparent, measurement-level observables, without relabelling `e33_app` as an
intrinsic coefficient.
