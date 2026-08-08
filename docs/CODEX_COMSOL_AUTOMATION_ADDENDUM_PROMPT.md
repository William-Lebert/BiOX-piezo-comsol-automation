# Generic Addendum Prompt for Another Codex

```text
Treat this COMSOL Multiphysics automation task as a reproducible scientific-computing workflow, not as a figure-generation task.

Before writing code, inspect every supplied file and report the task interpretation, input inventory, existing model structure, material-data sources, missing information, and a proposed execution plan. Do not redesign an existing model unless explicitly instructed.

Preserve originals. Create a project-local output directory with separate folders for immutable input snapshots, runtime files, each solve case, logs, analysis tables, and publication figures. Never overwrite a supplied MPH or a prior result set.

Audit units, coordinate systems, constitutive form, tensor dimensions, matrix ordering, dielectric convention, boundary conditions, geometry, mesh assumptions, and the source of every nontrivial material value. Reject or clearly flag unlabeled, inconsistent, nonphysical, or non-traceable inputs instead of silently guessing.

Inspect the real COMSOL model tree and tags through the API before modifying it. Build selections from geometry and verify entity counts. Do not assume inherited boundary IDs, variable names, feature tags, or array serialization order.

When using MPh and the Java API, confirm Python/MPh/JPype compatibility and use COMSOL's bundled Java runtime. Redirect COMSOL user-home, preferences, recovery, and temporary paths to writable project-local directories. Do not modify the COMSOL installation.

Repair only what is necessary. Remove conflicting physics features, set explicit boundary conditions, activate every required coupling and conservation equation, rebuild the mesh, and regenerate the automatic solver sequence. Verify that every coupled field equation is present before interpreting a zero result.

Run a small analytic or unit-level precheck first. For each FEM case, log the full configuration, retry a failed solve once after regenerating the solver sequence, and save a diagnostic model on failure. Do not report success until the final model, numerical data, and log files exist and values are finite and physically plausible.

Validate scientifically. Compare FEM results with a clearly labelled analytical scale check, perform requested sensitivity or parameter sweeps in independent output folders, and distinguish exact theoretical baselines from independently solved cases. Never alter parameters merely to obtain an expected ranking or agreement with experiment.

Make comparison graphics quantitatively honest: use identical views, explicit units, common physical color limits across comparable maps, a zero-centered symmetric colorbar for signed fields, and untruncated chart axes unless a justified alternative is requested. Check final rendered images for blank output, text overlap, incorrect language, missing glyphs, wrong colorbar limits, and data clipping.

Deliver a concise manifest listing original inputs, modified copies, final MPH files, exact run settings, result tables, figure paths, validation checks, limitations, and unresolved data needs. Clearly separate actual COMSOL results from derived, analytical, or presentation-only values.

If a key scientific assumption is missing, identify it early, explain its consequence, and ask for the minimum data needed. Continue only with clearly labelled, conservative sensitivity cases that do not fabricate evidence.
```
