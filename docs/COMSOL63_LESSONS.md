# COMSOL 6.3 Lessons From This Project

## Execution Summary

1. Audited the MPH template, material JSON, PFM workbook, FEA archive, and reference instructions before editing the model.
2. Used MPh and the COMSOL Java API to repair the existing model rather than rebuilding its physics architecture.
3. Rebuilt coordinate-based top and bottom selections, fixed the mechanical and electrical boundary conditions, and activated the piezoelectric charge-conservation feature.
4. Serialized the constitutive matrices with the ordering expected by COMSOL, rebuilt the mesh, regenerated automatic solver sequences, and retried failed stationary solves once.
5. Solved the three materials, extracted finite scalar metrics, wrote CSV/JSON/log outputs, and exported stress and centered-potential maps.
6. Added independent pressure and dielectric sensitivity analyses, then checked the figures against the numerical tables.

## Practical Rules

- Inspect actual component, physics, multiphysics, mesh, study, and result tags through the API. File names are not a reliable model schema.
- Build selections from geometry coordinates and verify entity counts. Boundary IDs can change after geometry edits.
- A piezoelectric solid solve without the electrostatic charge-conservation equation can return a mechanically valid but electrically meaningless zero field.
- Verify matrix serialization explicitly. The COMSOL `eES` table used column-major flattening in this workflow.
- Keep dielectric conventions consistent across compared materials and state the convention in every table and figure manifest.
- Redirect COMSOL home, preferences, recovery, and temporary paths to writable project-local folders. Leave the installation tree untouched.
- Use analytic constitutive calculations only as scale and unit checks. They do not replace the FEM solve.
- Treat a zero-load point in a linear model as an exact baseline unless an independent zero-load solve is actually stored.
- Use one physical color range for comparative maps, a zero-centered range for signed fields, and untruncated quantitative chart axes.
- Validate more than process exit codes: require finite values, nonempty MPH/CSV/PNG files, meaningful logs, and nonblank images.

## Scientific Boundaries

Do not tune material constants, dielectric values, geometry, or plotting ranges to force agreement with an expected ranking. Keep local simulated piezopotential, measured voltage, and photocatalytic performance as separate quantities. Record the source and coordinate convention of every constitutive tensor; unresolved tensor provenance must remain a stated limitation.

