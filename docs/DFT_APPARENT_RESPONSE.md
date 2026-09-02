# DFT-informed apparent-response model

The supplied `BiOX_FEA_DFT.zip` is now used as a first-principles input package,
not as a literature surrogate. The papers in the reference archive remain
design/layout references only.

## Imported quantities

- `C^E`: the VASP `TOTAL ELASTIC MODULI` matrices, converted from kBar to Pa
  (`1 kBar = 10^8 Pa`), with tetragonal entries retained in COMSOL Voigt order
  `(xx, yy, zz, yz, xz, xy)`.
- Dielectric tensors: the VASP electronic tensor and ionic contribution are
  stored separately. The default PFM run uses their low-frequency sum because
  the instrument drive is 1 Hz. Frequency dispersion is not resolved.
- The VASP total macroscopic piezoelectric tensor is zero in all three supplied
  calculations. This result is preserved as provenance and is not replaced by
  an unverified intrinsic tensor.

The compact numeric summary is stored in
`data/dft/dft_tensor_summary.csv`; the full matrices used by the solver are in
`config/materials_dft_apparent.json`.

## Apparent electromechanical closure

The measured SSPFM normal response is the comparison observable. For the
stress-charge COMSOL material node, a single effective normal coupling is
introduced only to reproduce the response level:

\[
e_{33}^{app}=d_{33}^{app} C_{33}^{E}10^{-12}\;\mathrm{C\,m^{-2}},
\]

where `d33_app` is in pm/V and `C33^E` is in Pa. No claim is made that this
`e33_app` is an intrinsic bulk coefficient, and it must not be compared with a
DFT piezoelectric tensor or reported as one.

The COMSOL result is therefore a calibrated field/displacement map. The
scientific comparison is the measured apparent order and ratio:

| material | measured `d33_app` (pm/V) | `e33_app` closure (C/m²) |
|---|---:|---:|
| BiOCl | 315.71 ± 6.13 | 16.3333 |
| BiOBr | 477.98 ± 6.77 | 13.1605 |
| BiOI | 649.67 ± 9.33 | 19.8596 |

## Verified COMSOL run

The run used `config/model_v13_apparent_dft.json`, a 100 nm × 100 nm × 1 nm
local contact-patch proxy, a 1 V Gaussian surface-potential proxy, and the DFT
low-frequency dielectric sum. The solved apparent displacement values were:

| material | simulated `d_eff` (pm/V) | target ratio |
|---|---:|---:|
| BiOI | 40.8199 | 2.0578 |
| BiOBr | 30.0325 | 1.5139 |
| BiOCl | 19.8367 | 1.0000 |

The common multiplicative factor (`d_eff / d33_app ≈ 0.0628318`) is a property
of the present contact/geometry proxy. It is not an additional material
constant. The ranking agrees with the SSPFM measurements: `BiOI > BiOBr >
BiOCl`.

## Reporting boundary

Use this branch for “apparent piezoelectric response comparison” and for
linking the spatial COMSOL fields to SSPFM. Do not describe it as an intrinsic
bulk piezoelectric prediction. A future intrinsic model would require a
validated non-centrosymmetric structure, a full 3-D `e`/`d` tensor, orientation
statistics and a calibrated tip/contact transfer function.
