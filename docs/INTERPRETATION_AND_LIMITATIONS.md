# Interpretation and limitations

1. **PFM is the ranking anchor.** The target order is BiOI > BiOBr > BiOCl, based on the supplied SSPFM reanalysis. This is an apparent local response order. It should not be described as a directly calibrated intrinsic bulk `d33`.
2. **The catalytic result is separate.** A later BiOBr photocatalytic or interfacial-synergy advantage is not a piezoelectric constitutive constraint and is deliberately absent from the parameter selection.
3. **Two constitutive branches are kept separate.** The legacy 2D-to-3D bridge is retained only to qualify the automation. The active DFT-apparent branch imports the supplied VASP elastic and dielectric data and does not use the literature tensors.
4. **The DFT-apparent branch is not intrinsic.** The supplied VASP total macroscopic piezoelectric tensor is zero. A single `e33_app` channel is therefore derived from measured SSPFM `d33_app` and DFT `C33` to produce a response-level comparison. This parameter must not be reported as an intrinsic coefficient.
5. **Dielectric frequency remains unresolved.** The active 1 Hz case uses the stored electronic-plus-ionic low-frequency sum. Frequency dispersion and loss were not supplied, so absolute voltage predictions should be interpreted cautiously.
6. **Electrode mechanics matter.** The default full-top electrode is a transparent proxy for a local PFM contact. A contact-partitioned model and calibrated tip/contact mechanics are required before claiming absolute agreement with an instrument amplitude.
7. **Morphology measurements are not fabricated.** SEM/TEM scale metadata are inventoried, but particle dimensions stay blank until manual measurement or validated segmentation. The image geometry mode refuses incomplete rows.
8. **No material-specific correction factors are applied outside the stated closure.** Any change to the apparent closure, contact footprint or geometry must be reported as a new sensitivity case.
