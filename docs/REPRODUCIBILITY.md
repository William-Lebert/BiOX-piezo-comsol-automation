# Reproducibility Checklist

Before a run:

- Confirm COMSOL 6.3 and the required license features are available.
- Confirm the Python interpreter, MPh, JPype1, and Pillow versions.
- Use a writable project-local runtime directory for COMSOL preferences and recovery files.
- Check units, tensor dimensions, symmetry, positive definiteness, dielectric convention, and boundary-condition intent.
- Preserve the input template and configuration snapshot.

During a run:

- Log the COMSOL version, core count, material set, pressure, thickness, dielectric mode, and output directory.
- Regenerate the automatic solver sequence after physics or geometry changes.
- Retry once after solver regeneration and save a diagnostic model if the retry fails.

After a run:

- Require finite Vmax, Vmin, DeltaV, stress, and displacement values.
- Compare the FEM result with the labelled analytic precheck.
- Check that all expected MPH, CSV/JSON, log, and image files exist and are nonempty.
- Check rendered images for blank output, clipped labels, wrong language, hidden titles, and inconsistent colorbar limits.
- Keep the input snapshot, result tables, manifests, and limitations together.

