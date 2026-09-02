# BiOBr/BiOI separation audit

This document records the archived sensitivity tests used to diagnose the
original reduced 2D-to-3D closure. It is retained for transparency; the active
DFT-informed apparent branch is documented separately in
`DFT_APPARENT_RESPONSE.md`.

The 100 MPa direct-pressure baseline gave ΔV = 14.890, 16.180 and 16.183 mV
for BiOCl, BiOBr and BiOI, respectively. The near equality of BiOBr and BiOI
was therefore a constitutive/geometry issue, not a colour-scale issue.

| Case | BiOCl (mV) | BiOBr (mV) | BiOI (mV) | Interpretation |
|---|---:|---:|---:|---|
| Baseline, `e33/e31 = 0` | 14.890 | 16.180 | 16.183 | Reduced bridge with no out-of-plane closure |
| Sensitivity, `e33/e31 = 1` | 14.893 | 16.177 | 16.185 | Equal-size closure is insufficient |
| Upper-bound test, `e33/e31 = 100` | 38.288 | 34.921 | 33.688 | Generic amplification reverses the ranking and is rejected |
| Literature size priors | — | 16.255 | 16.225 | Geometry alone changes <0.2%; not a separator without measured dimensions |
| Naive `e33_eff = d33_app C33` | 6.155 | 3.994 | 2.718 | Reverses the ranking because apparent PFM includes contact transfer |

The runtime MPH/JSON sensitivity folders are not included in this curated
release. Their parameter definitions remain in `config/` for provenance.

## Interpretation

The archived tests show why a BiOI–BiOBr gap should not be forced by changing a
single scalar. A surface-normal PFM observable depends on out-of-plane coupling,
elastic compliance, orientation, geometry and contact transfer. The active
DFT-informed branch therefore uses DFT `C^E` and dielectric data together with
an explicitly labelled measured-response closure, rather than presenting the
archived reduced closure as an independent intrinsic prediction.
