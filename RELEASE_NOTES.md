# Release notes

## Version 1.2.0

This update reorganizes the BiOX finite-element study as a compact, auditable research repository. It preserves the original calculated values and adds the reporting context needed for manuscript use.

### Added

- A consistent dielectric-convention sensitivity dataset at 100 MPa
- A manuscript-ready grouped comparison of electronic and total dielectric results
- Explicit methods, data definitions, interpretation boundaries, and parameter-provenance notes
- A self-contained repository layout with portable relative paths
- Reproduction commands for COMSOL solving and figure generation

### Retained

- Three shared-scale potential maps (-177 to +177 $\mu$V)
- Three shared-scale von Mises stress maps (0-175 MPa)
- Zero-baseline 100 MPa comparison with 1.00, 6.60, and 4.61 relative responses
- The 0-100 MPa pressure sweep and fitted response coefficients
- Independent-scale potential maps for spatial-pattern inspection

### Excluded

- COMSOL installation files and license material
- Large proprietary `.mph` model binaries
- Virtual environments, caches, logs, and temporary render products
- Copyrighted reference PDFs and internal working documents

No numerical result in the retained primary dataset was rescaled or edited for visual separation. Shared color limits and zero-based quantitative axes are used to make the differences directly comparable.
