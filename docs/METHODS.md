# Finite-element methods

## Governing equations

The models use the linear piezoelectric stress-charge formulation

$$
\mathbf{T}=\mathbf{c}^{E}\mathbf{S}-\mathbf{e}^{T}\mathbf{E},
\qquad
\mathbf{D}=\mathbf{e}\mathbf{S}+\varepsilon_0\boldsymbol{\varepsilon}^{S}_{r}\mathbf{E},
$$

where $\mathbf{T}$ and $\mathbf{S}$ are the stress and strain vectors, $\mathbf{E}$ is the electric field, $\mathbf{D}$ is the electric displacement, $\mathbf{c}^{E}$ is the stiffness matrix at constant electric field, $\mathbf{e}$ is the piezoelectric stress matrix, and $\boldsymbol{\varepsilon}^{S}_{r}$ is the relative dielectric tensor at constant strain.

The three supplied coefficients are mapped to $e_{31}$, $e_{32}$, and $e_{33}$ in the 3 x 6 COMSOL matrix. Entries not supplied by the source dataset are set to zero. This mapping is an explicit modeling assumption rather than a symmetry-complete tensor reconstruction.

## Geometry and boundary conditions

| Quantity | Value |
|---|---:|
| Domain length | 100 nm |
| Domain width | 100 nm |
| Domain thickness | 5 nm |
| Reference pressure | 100 MPa |
| Pressure sweep | 0, 20, 40, 60, 80, 100 MPa |
| Maximum mesh size | 10 nm |
| Minimum mesh size | 1.25 nm |

A uniform follower pressure acts on the upper $z$ face. The lower $z$ face is fixed in all displacement components and assigned zero electric potential. Other electrostatic boundaries use zero surface charge. The same geometry, mesh controls, selections, solver sequence, and post-processing expressions are applied to BiOCl, BiOBr, and BiOI.

## Solution and verification

Calculations are stationary and use COMSOL Multiphysics 6.3. Before solving, the automation script validates tensor dimensions, stiffness-matrix symmetry and positive definiteness, dielectric positivity, geometry, mesh settings, and expected analytical response order. Each material is loaded from the same base model, rebuilt with its own constitutive data, solved, checked, and saved as a separate model file in the calculation directory.

The primary electrical response is

$$
\Delta V=\max_{\Omega}(V)-\min_{\Omega}(V).
$$

Potential maps display $V-(V_{\max}+V_{\min})/2$ so that the color bar is centered at zero. Mechanical output is reported as the maximum von Mises stress. A simple one-dimensional estimate is retained only as a pre-solve sanity check; it is not substituted for the finite-element solution.

## Dielectric-convention analysis

Three configuration modes are available:

| Mode | Meaning |
|---|---|
| `prompt` | Original reference parameterization; preserves the inputs used for the primary figure set |
| `vasp-electronic` | Electronic dielectric tensors for all three materials |
| `vasp-total` | Total dielectric tensors for all three materials |

The `prompt` mode mixes dielectric conventions across the material series and is retained for provenance. The two consistent modes quantify the sensitivity of the absolute response and test whether the comparative ranking is robust.

## Figure conventions

Shared-scale out-of-plane normal strain maps use -0.8 to 0% and display $100\varepsilon_{zz}$; negative values denote compression along the loading direction. This range was obtained by pooling the extrema from all three 100 MPa solutions, including zero, and rounding outward to 0.2% ticks. Shared-scale potential maps use -177 to +177 $\mu$V, and shared-scale stress maps use 0-175 MPa. These fixed limits permit direct visual comparison without rescaling or clipping the underlying data. The independent-scale potential panel is included only to resolve within-material spatial structure. Quantitative plots begin at zero and use the original calculated values.

## PFM reporting boundary

The available PFM metadata describe SSPFM measurements on pressed pellets using an MFP-3D Origin platform, a 1 V drive, a 1 Hz scan rate, ambient temperature of $25 \pm 1$ degrees C, and relative humidity below 40%. The cantilever contact mechanics and applied force were not sufficiently calibrated to map the drive conditions to the FEM pressure. No direct conversion between 1 V/1 Hz and 100 MPa is made.
