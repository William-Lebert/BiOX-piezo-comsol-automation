# Reference-informed design priorities

This note records how the supplied papers inform the v1.3.0 finite-element
workflow. The references are used to select observables and presentation
formats; they are not treated as evidence for material constants that were not
reported in the present dataset.

## Priority 0 — make the comparison auditable

1. Keep one geometry, mesh policy, drive definition and post-processing rule
   for all three materials within a run.
2. Export stress and electric-potential maps with a common physical range when
   the panels are used for ranking. Independent limits may be retained as a
   diagnostic companion set, but must be labelled as such.
3. Report the raw extrema, the pressure-response slope and the PFM target in a
   table. A colour map is a spatial diagnostic, not a substitute for a scalar
   response metric.
4. Keep the Gaussian contact radius as an explicit sensitivity parameter. A
   local PFM field is a contact model, not a material-specific scaling factor.

## Priority 1 — extend the physically useful observables

### Local contact and pressure transfer

The PFM literature in the supplied archive presents COMSOL stress/potential
maps together in a 2×3 matrix. This layout is adopted by the figure compositor
in `src/compose_sci_figures.py`. The current v1.3.0 Gaussian surface-potential
case should be read as a converse-PFM field-distribution diagnostic. For a
forward comparison with PFM, a second study should apply the measured contact
load (or a bounded load range) and extract the surface-normal displacement at
the contact centre.

### Pressure sweep and linearity

Solve 0, 20, 40, 60, 80 and 100 MPa with the same mesh and plot limits. Fit
`DeltaV = k_p p + b` only over the range that is demonstrably linear. Report
the slope with units and its confidence interval; do not infer linearity from
two points.

### Orientation and anisotropy (future)

The review paper emphasizes that 2D BiOX response is tensorial and strongly
orientation dependent. An orientation sweep (armchair/zigzag or an explicitly
stated surrogate for the tetragonal axes) is therefore a higher-value extension
than adding more colour maps. It requires defensible anisotropic `d`, `c` and
permittivity tensors; values should come from the same experimental or DFT
source rather than being back-calculated to match PFM.

### Morphology-conditioned geometry (future)

SEM/TEM images support a distribution of lateral sizes and aspect ratios, not a
single “representative” particle. Once dimensions are manually recorded from
the supplied scale bars, use a small ensemble of geometries and report the
median and interquartile range. Literature particle sizes are retained only as
context priors in `data/morphology/image_inventory.csv`.

## Priority 2 — mechanism-oriented extensions

- Add a transient acoustic/ultrasound study only after the static pressure and
  contact problems are validated. The supplied BiOI work demonstrates plane-
  resolved stress, potential and displacement as a useful presentation pattern.
- Add defect or vacancy cases only when a defect-dependent piezoelectric or
  elastic tensor is available. A defect label without a changed constitutive
  tensor is not a mechanistic simulation.
- Couple the piezoelectric field to carrier-transport or surface-reaction
  models only after the electrostatic boundary conditions and charge reference
  are experimentally anchored. The present model does not calculate a
  photocatalytic rate or a carrier-separation efficiency.

## Presentation rule used here

The six-panel figure follows the stress-over-potential arrangement used in the
reference COMSOL example, while enforcing English labels, Times New Roman
panel annotations, 300 dpi metadata, and enlarged colour-bar readability. No
material-dependent contrast or numerical rescaling is introduced during image
composition.
