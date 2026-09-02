# SEM/TEM inventory

`image_inventory.csv` is a metadata inventory generated from the supplied `SEM-TEM.zip`. It records the archive member, SHA-256 digest, SEM field of view, pixel size, magnification, accelerating voltage, and acquisition condition. The summary currently contains 94 image files: 8 SEM and 18 TEM entries for BiOCl, 8 SEM and 22 TEM entries for BiOBr, and 4 SEM and 34 TEM entries for BiOI.

The columns `scale_bar_um`, `measured_major_um`, `measured_minor_um`, and `measured_thickness_nm` are intentionally empty. Populate them only from a documented scale-bar measurement or a validated segmentation workflow. The COMSOL image-geometry mode rejects a material with no positive major/minor dimensions.
