# Methods

## Constitutive representation

The model uses the stress-charge convention

\[
T=c^E S-e^T E,\qquad D=eS+\varepsilon_0\varepsilon_r^S E.
\]

The COMSOL 3D Voigt order is `(xx, yy, zz, yz, xz, xy)`. The checked baseline
contains a provisional reduced tensor only to qualify the automation. It is not
the own-data model. The own-data implementation must replace it with the full
3D matrices measured or calculated for each sample, including the out-of-plane
and shear terms required by PFM.

For traceability, the provisional reduced bridge is written as

\[
C_{2D}=\begin{bmatrix}C_{11}&C_{12}&0\\C_{12}&C_{11}&0\\0&0&(C_{11}-C_{12})/2\end{bmatrix},
\quad
e_{2D}=\begin{bmatrix}e_{11}&-e_{11}&0\\0&0&-e_{11}/2\\e_{31}&e_{31}&0\end{bmatrix}.
\]

The effective 3D conversion in that qualification case is `C3D=C2D/t_eff` and
`e3D=e2D/t_eff`, with an explicit transversely isotropic extension. The
extension factors and dielectric entries are sensitivity-only. They must be
replaced by your own `C^E`, `e/d` and `epsilon^S` data before any material-
specific 3D claim; see `OWN_DATA_REQUIREMENTS.md`.

## DFT-informed apparent branch

`config/model_v13_apparent_dft.json` selects the supplied VASP `C^E` matrices
and the sum of the VASP electronic and ionic dielectric tensors. The VASP total
macroscopic piezoelectric tensor is zero for the supplied calculations and is
kept as provenance. Because the PFM observable is an apparent surface-normal
response, the active comparison introduces only

\[
e_{33}^{app}=d_{33}^{app}C_{33}^{E}10^{-12},
\]

with the measured SSPFM `d33_app` in pm/V. This is a response-level calibration
for a contact/geometry proxy, not an intrinsic bulk piezoelectric coefficient;
the output must be reported as apparent PFM response.

## PFM-converse study

The primary study applies the instrument drive amplitude (`1 V`) as a prescribed potential on the top electrode and grounds the bottom face. The measured quantity is the average top-face normal displacement divided by the applied voltage:

\[
d_{\mathrm{eff}}^{\mathrm{sim}}=|\langle w\rangle_{top}/V_{AC}|.
\]

The template uses a full-top-face electrode proxy unless a validated contact patch named `biox_pfm_patch` is present. This choice is recorded in every result file.

## Direct-pressure benchmark

The secondary study applies a uniform top pressure over the same resolved geometry and reports `Vmax`, `Vmin`, `DeltaV`, and the maximum von Mises stress. Pressure points are independent quasi-static solutions; they are not converted into PFM voltage amplitudes and are not used to calibrate the PFM targets.

## Geometry and mesh

The reference geometry is a 100 nm × 100 nm rectangular effective local-patch proxy. `t_eff` is swept independently of the lateral reference dimensions. Image mode is available only after manual/validated measurements are entered in the inventory. The top and bottom boundaries are rebuilt by z-coordinate selections and checked to contain exactly one boundary each. The lateral mesh limit is set from the lateral size, while the through-thickness minimum is set from `t_eff`; using the thickness as an isotropic lateral limit is intentionally avoided because it produces an impractically large mesh.
