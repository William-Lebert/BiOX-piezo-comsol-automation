# BiOX Piezoelectric COMSOL 6.3 Automation

Reproducible COMSOL 6.3 automation and publication-ready result package for a comparative BiOX piezoelectric model. The workflow uses a supplied BiOCl MPH model as a template, applies traceable material data for BiOCl, BiOBr, and BiOI, solves the coupled solid-electrostatic problem, and exports quantitative comparisons.

## What Is Included

- `src/`: COMSOL/MPh automation, shared-scale figure export, quantitative plotting, and phase-2 analysis scripts.
- `model/`: one reusable BiOCl template MPH. Generated material-specific MPH files are intentionally omitted because they are reproducible duplicates.
- `data/baseline/`: verified 100 MPa COMSOL result tables and run log.
- `data/publication/`: pressure-sweep tables and figure manifests.
- `data/phase2/`: dielectric, pressure, thickness, surface-field, and mechanism analysis tables.
- `data/raw/`: supplied PFM workbook and FEA archive. Check redistribution rights before public release.
- `figures/`: common-scale potential maps, stress maps, DeltaV comparison plots, and the phase-2 mechanism summary.
- `docs/`: project scope, COMSOL 6.3 lessons, reproducibility notes, and a generic Codex automation prompt.

## Main Results

At the verified 100 MPa, 5 nm baseline using the total-dielectric convention, the solved DeltaV values are approximately:

| Material | DeltaV (microvolt) |
| --- | ---: |
| BiOCl | 53.57 |
| BiOBr | 177.65 |
| BiOI | 152.10 |

The pressure-response data include 0, 20, 40, 60, 80, and 100 MPa. The 0 MPa point is an exact unloaded baseline, not a separately solved MPH case. All comparative maps use shared physical color limits; no material-dependent scaling is applied.

## Requirements

- COMSOL Multiphysics 6.3 with a license exposing the required solid mechanics and electrostatics features.
- Python 3.10-3.12, MPh 1.3.1, JPype1, and Pillow. See `requirements.txt`.
- COMSOL's bundled Java runtime. Do not copy COMSOL installation files into this repository.

Install the non-COMSOL Python packages:

```powershell
python -m pip install -r requirements.txt
```

Run the dependency-free material precheck:

```powershell
python src/biox_comsol_automation.py `
  --dry-run `
  --input-mph model/BiOCl_piezo_template.mph `
  --config data/biox_materials.json `
  --output-dir outputs/precheck
```

Run the actual COMSOL solve from PowerShell. Replace the COMSOL path for another installation:

```powershell
python src/biox_comsol_automation.py `
  --input-mph model/BiOCl_piezo_template.mph `
  --comsol-root "D:\Puxiaoyu\COMSOL\COMSOL63\Multiphysics" `
  --config data/biox_materials.json `
  --output-dir outputs/comsol_run `
  --cores 4
```

The solver writes material-specific MPH files, result CSV/JSON files, plots, and a run log under the selected output directory. The curated repository keeps the verified tables and publication figures while excluding repeated solve folders and runtime caches.

## Scientific and Reproducibility Notes

- The piezoelectric vector in the supplied configuration is interpreted as `[e31, e32, e33]` in C/m^2. Confirm this mapping against the original DFT or experimental source before publication.
- Dielectric conventions are kept explicit. Mixed conventions are not suitable for a final material ranking; use the uniform electronic and total modes as sensitivity bounds.
- The static local piezopotential span is a model descriptor. It is not automatically an open-circuit voltage, a carrier-separation efficiency, or a photocatalytic rate.
- Analytical prechecks are labelled as analytical and are never presented as finite-element results.
- COMSOL is proprietary software. This repository contains no COMSOL installer, license, user profile, or runtime cache.

"The Python scripts in this repository are provided under the [MIT/Apache] License. The COMSOL model files are intended for academic reproduction purposes and require a valid COMSOL license to run."

