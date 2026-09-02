#!/usr/bin/env python3
"""COMSOL 6.3 automation for the PFM-anchored BiOX v1.3.0 model.

Two intentionally separate studies are supported:

* ``pfm-converse`` applies a prescribed electrical drive and measures the
  surface-normal converse displacement.  The current template uses the top
  face as a documented uniform-electrode proxy; a future contact-partitioned
  template can provide the optional ``biox_pfm_patch`` selection.
* ``direct-pressure`` retains the old quasi-static pressure benchmark for
  provenance only.  It is never used as a PFM calibration.

The script is safe to run with ``--dry-run`` without MPh or COMSOL installed.
Actual COMSOL runs require an explicit ``--allow-unverified-epsilon`` for the
legacy sensitivity configuration.  The DFT-apparent configuration carries a
documented dielectric provenance but remains an apparent-response model.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from biox_v13_core import EPS0, PFM_ORDER, Material2D, load_materials, order_from


DEFAULT_TEMPLATE = SCRIPT_DIR.parent / "model" / "BiOCl_piezo_template.mph"
DEFAULT_MODEL = SCRIPT_DIR.parent / "config" / "model_v13_apparent_dft.json"
DEFAULT_MATERIALS = SCRIPT_DIR.parent / "config" / "materials_dft_apparent.json"
DEFAULT_COMSOL_ROOT = Path("D:/Puxiaoyu/COMSOL/COMSOL63/Multiphysics")


def format_values(values: Iterable[float]) -> list[str]:
    return [f"{value:.16g}" for value in values]


def flatten_row_major(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [value for row in matrix for value in row]


def flatten_column_major(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [matrix[row][column]
            for column in range(len(matrix[0]))
            for row in range(len(matrix))]


def java_tags(container: Any) -> list[str]:
    return [str(tag) for tag in container.tags()]


def remove_if_present(container: Any, tag: str) -> None:
    try:
        if bool(container.hasTag(tag)):
            container.remove(tag)
    except Exception:
        # Some COMSOL collections expose ``hasTag`` only on their Java node;
        # absence is harmless when a tag is already gone.
        pass


def feature_type(feature: Any) -> str:
    for method in ("getType", "type"):
        try:
            return str(getattr(feature, method)())
        except Exception:
            continue
    return ""


def make_java_string_array(values: Sequence[str]) -> Any:
    from jpype import JArray, JString
    return JArray(JString)(list(values))


def make_java_int(value: int) -> Any:
    from jpype import JInt
    return JInt(value)


def flatten_java_numbers(value: Any) -> list[float]:
    if isinstance(value, (int, float)):
        return [float(value)]
    output: list[float] = []
    try:
        for item in value:
            output.extend(flatten_java_numbers(item))
    except TypeError as error:
        raise TypeError(f"Cannot flatten COMSOL value of type {type(value)!r}") from error
    return output


def configure_logging(output_dir: Path) -> logging.Logger:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("biox_v13")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_handler = logging.FileHandler(output_dir / "BiOX_v13_COMSOL_run.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def prepare_comsol_environment(comsol_root: Path) -> None:
    if not comsol_root.is_dir():
        raise FileNotFoundError(f"COMSOL root not found: {comsol_root}")
    java_home = comsol_root / "java" / "win64" / "jre"
    java_exe = java_home / "bin" / "java.exe"
    if not java_exe.is_file():
        raise FileNotFoundError(f"COMSOL Java runtime not found: {java_exe}")
    bin_dir = comsol_root / "bin" / "win64"
    os.environ["PATH"] = os.pathsep.join([str(bin_dir), str(java_home / "bin"), os.environ.get("PATH", "")])
    os.environ["JAVA_HOME"] = str(java_home)
    os.environ["COMSOL_ROOT"] = str(comsol_root)


def read_model_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.3.0":
        raise ValueError(f"Unexpected model schema in {path}.")
    return payload


def read_image_geometry(path: Path, material: str) -> tuple[float, float]:
    """Return one manually annotated SEM/TEM lateral size in micrometres."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    candidates = []
    for row in rows:
        if row.get("material") != material:
            continue
        try:
            major = float(row.get("measured_major_um", ""))
            minor = float(row.get("measured_minor_um", ""))
        except (TypeError, ValueError):
            continue
        if major > 0.0 and minor > 0.0:
            candidates.append((major, minor))
    if not candidates:
        raise ValueError(
            f"No measured_major_um/measured_minor_um values for {material} in {path}. "
            "The inventory intentionally requires manual/validated annotation before morphology mode.")
    # The first row is deterministic; users can create separate inventory
    # files for bootstrap or percentile realizations.
    return candidates[0]


def set_model_parameters(jmodel: Any, geometry: dict[str, float], mode: str) -> None:
    params = {
        "biox_Lx": f"{geometry['length_um']:.12g}[um]",
        "biox_Ly": f"{geometry['width_um']:.12g}[um]",
        "biox_t": f"{geometry['thickness_nm']:.12g}[nm]",
        "biox_vac": f"{geometry['vac_V']:.12g}[V]",
        "biox_p": f"{geometry['pressure_mpa']:.12g}[MPa]",
        "biox_hmax": f"{geometry['hmax_nm']:.12g}[nm]",
        "biox_hmin": f"{geometry['hmin_nm']:.12g}[nm]",
        "biox_sel_tol": f"{geometry['selection_tolerance_nm']:.12g}[nm]",
        "biox_patch_sigma": f"{geometry['patch_sigma_nm']:.12g}[nm]",
    }
    for name, value in params.items():
        jmodel.param().set(name, value)
    jmodel.label(f"BiOX v1.3.0 | {mode} | PFM-consistent ordering")


def repair_geometry_and_selections(jmodel: Any) -> dict[str, list[int]]:
    component = jmodel.component("comp1")
    geometry = component.geom("geom1")
    if not bool(geometry.feature().hasTag("blk1")):
        raise RuntimeError("Expected geometry feature comp1/geom1/blk1 is missing from template.")
    block = geometry.feature("blk1")
    block.set("base", "center")
    block.set("size", make_java_string_array(["biox_Lx", "biox_Ly", "biox_t"]))
    block.set("pos", make_java_string_array(["0", "0", "0"]))
    geometry.run()

    selections = component.selection()
    limits = {
        "biox_top": ("biox_t/2-biox_sel_tol", "biox_t/2+biox_sel_tol"),
        "biox_bottom": ("-biox_t/2-biox_sel_tol", "-biox_t/2+biox_sel_tol"),
    }
    found: dict[str, list[int]] = {}
    for tag, (zmin, zmax) in limits.items():
        remove_if_present(selections, tag)
        selections.create(tag, "Box")
        selection = component.selection(tag)
        selection.label("BiOX top z face" if tag.endswith("top") else "BiOX bottom z face")
        selection.set("entitydim", make_java_int(2))
        selection.set("condition", "allvertices")
        selection.set("zmin", zmin)
        selection.set("zmax", zmax)
        entities = [int(entity) for entity in selection.entities(2)]
        if len(entities) != 1:
            raise RuntimeError(f"{tag} must select exactly one boundary; got {entities}.")
        found[tag] = entities
    if found["biox_top"] == found["biox_bottom"]:
        raise RuntimeError("Top and bottom selections resolved to the same boundary.")
    return found


def remove_external_electric_potentials(es: Any) -> list[str]:
    removed: list[str] = []
    features = es.feature()
    for tag in java_tags(features):
        node = es.feature(tag)
        if feature_type(node) == "ElectricPotential" or tag == "pot1":
            features.remove(tag)
            removed.append(tag)
    return removed


def configure_electric_drive(jmodel: Any, es: Any, mode: str,
                             model_cfg: dict[str, Any], geometry: dict[str, float],
                             logger: logging.Logger) -> str:
    remove_external_electric_potentials(es)
    if not bool(es.feature().hasTag("gnd1")):
        es.create("gnd1", "Ground", 2)
    ground = es.feature("gnd1")
    ground.label("Ground bottom face")
    ground.selection().named("biox_bottom")
    if mode == "direct-pressure":
        return "bottom_ground_only"

    es.create("pot1", "ElectricPotential", 2)
    potential = es.feature("pot1")
    potential.label("PFM top electrode (uniform-face proxy)")
    potential.selection().named("biox_top")
    set_ok = False
    drive_expression = "biox_vac"
    for key in ("V0", "V"):
        try:
            potential.set(key, drive_expression)
            set_ok = True
            break
        except Exception:
            continue
    if not set_ok:
        raise RuntimeError("Could not set the ElectricPotential boundary value (tried V0 and V).")
    has_patch = False
    try:
        # ``Electrostatics`` is a physics node; the selection collection lives
        # on the component, not on the physics wrapper itself.
        has_patch = bool(jmodel.component("comp1").selection().hasTag("biox_pfm_patch"))
    except Exception:
        pass
    if has_patch:
        potential.selection().named("biox_pfm_patch")
        logger.info("Using template-provided biox_pfm_patch selection.")
        return "local_electrode_patch"
    if model_cfg["pfm"].get("surface_drive_model") == "gaussian_potential_proxy":
        drive_expression = "biox_vac*exp(-(x^2+y^2)/(2*biox_patch_sigma^2))"
        set_ok = False
        for key in ("V0", "V"):
            try:
                potential.set(key, drive_expression)
                set_ok = True
                break
            except Exception:
                continue
        if not set_ok:
            raise RuntimeError("Could not set the Gaussian ElectricPotential expression.")
        logger.warning("Template has no biox_pfm_patch; using a Gaussian top-potential contact proxy with sigma=%.6g nm.", geometry["patch_sigma_nm"])
        return "gaussian_surface_potential_proxy"
    logger.warning("Template has no biox_pfm_patch; using the full top face as a uniform-electrode proxy.")
    return "uniform_top_electrode_proxy"


def repair_physics(jmodel: Any, material: Material2D, geometry: dict[str, float],
                   mode: str, model_cfg: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    component = jmodel.component("comp1")
    solid = component.physics("solid")
    es = component.physics("es")
    ext = model_cfg["c3d_extension"]
    constitutive_source = str(ext.get("constitutive_source", "legacy_2d_bridge"))
    if constitutive_source == "dft_apparent":
        epsilon_variant = str(ext.get("epsilon_variant", "low_frequency_total"))
        c3d, e3d, eps = material.dft_apparent_3d(epsilon_variant)
        logger.info(
            "%s: using DFT C^E and %s dielectric tensor with apparent e33=%.8g C/m^2; "
            "the DFT total macroscopic piezo tensor is retained as zero provenance.",
            material.name, epsilon_variant, material.apparent_e33_C_per_m2,
        )
    else:
        e33_ratio = float(ext.get("e33_over_e31", 0.0))
        calibration = model_cfg.get("pfm_effective_calibration", {})
        if bool(calibration.get("enabled", False)):
            # Convert a calibrated effective e33 (C/m^2) into the ratio expected by
            # the 2D-to-3D bridge. This is explicitly an apparent-PFM closure, not
            # an intrinsic coefficient from the supplied 2D source.
            e33_values = calibration.get("e33_eff_C_per_m2", {})
            if material.name not in e33_values:
                raise ValueError(f"PFM calibration has no e33_eff_C_per_m2 value for {material.name}.")
            e31_eff = material.e2d_pC_per_m[2][0] * 1e-12 / (geometry["thickness_nm"] * 1e-9)
            if abs(e31_eff) < 1e-30:
                raise ValueError(f"{material.name}: cannot form e33/e31 calibration ratio from zero e31.")
            e33_ratio = float(e33_values[material.name]) / e31_eff
        c3d, e3d, eps = material.effective_3d(
            geometry["thickness_nm"],
            float(ext["c33_over_c11"]), float(ext["c13_over_c12"]),
            float(ext["shear_over_c66"]), e33_ratio,
        )
    if not bool(solid.feature().hasTag("pzm1")):
        raise RuntimeError("Expected solid/pzm1 Piezoelectric Material node is missing from template.")
    pzm = solid.feature("pzm1")
    pzm.selection().geom("geom1", 3)
    pzm.selection().all()
    pzm.set("SolidModel", "Anisotropic")
    pzm.set("ConstitutiveRelation", "StressCharge")
    pzm.set("cE_mat", "userdef")
    pzm.set("cE", make_java_string_array(format_values(flatten_row_major(c3d))))
    pzm.set("eES_mat", "userdef")
    pzm.set("eES", make_java_string_array(format_values(flatten_column_major(e3d))))
    pzm.set("epsilonrS_mat", "userdef")
    pzm.set("epsilonrS", make_java_string_array(format_values(flatten_row_major(eps))))
    pzm.set("coordinateSystem", "GlobalSystem")

    remove_if_present(solid.feature(), "fix1")
    solid.create("fix1", "Fixed", 2)
    solid.feature("fix1").label("Mechanically fixed bottom face")
    solid.feature("fix1").selection().named("biox_bottom")
    remove_if_present(solid.feature(), "bndl1")
    if mode == "direct-pressure":
        solid.create("bndl1", "BoundaryLoad", 2)
        solid.feature("bndl1").label("Direct-pressure top load")
        solid.feature("bndl1").selection().named("biox_top")
        solid.feature("bndl1").set("forceType", "FollowerPressure")
        solid.feature("bndl1").set("pressure", "biox_p")

    if not bool(es.feature().hasTag("ccnp1")):
        es.create("ccnp1", "ChargeConservationPiezo", 3)
    ccnp = es.feature("ccnp1")
    ccnp.label("Piezoelectric charge conservation")
    ccnp.selection().geom("geom1", 3)
    ccnp.selection().all()
    ccnp.set("materialType", "solid")
    ccnp.set("epsilonrS_mat", "userdef")
    ccnp.set("epsilonrS", make_java_string_array(format_values(flatten_row_major(eps))))
    ccnp.set("coordinateSystem", "GlobalSystem")
    electrode_model = configure_electric_drive(jmodel, es, mode, model_cfg, geometry, logger)
    if not bool(component.multiphysics().hasTag("pze1")):
        raise RuntimeError("Expected comp1/pze1 Piezoelectricity coupling is missing from template.")
    component.multiphysics("pze1").active(True)
    return {
        "electrode_model": electrode_model,
        "epsilon_status": material.epsilon_status,
        "constitutive_source": constitutive_source,
        "constitutive_status": material.constitutive_status,
        "effective_3d_assumption": model_cfg["c3d_extension"]["warning"],
    }


def configure_mesh(jmodel: Any) -> None:
    mesh = jmodel.component("comp1").mesh("mesh1")
    if not bool(mesh.feature().hasTag("size")):
        raise RuntimeError("Expected mesh1/size feature is missing from template.")
    size = mesh.feature("size")
    size.set("custom", "on")
    size.set("hmax", "biox_hmax")
    size.set("hmin", "biox_hmin")
    size.set("hgrad", 1.35)
    mesh.run()


def configure_coupling_operators(jmodel: Any) -> None:
    component = jmodel.component("comp1")
    couplings = component.cpl()
    for tag in ("biox_max", "biox_min", "biox_topavg"):
        remove_if_present(couplings, tag)
    couplings.create("biox_max", "Maximum", "geom1")
    component.cpl("biox_max").label("BiOX domain maximum")
    component.cpl("biox_max").selection().geom("geom1", 3)
    component.cpl("biox_max").selection().all()
    couplings.create("biox_min", "Minimum", "geom1")
    component.cpl("biox_min").label("BiOX domain minimum")
    component.cpl("biox_min").selection().geom("geom1", 3)
    component.cpl("biox_min").selection().all()
    couplings.create("biox_topavg", "Average", "geom1")
    component.cpl("biox_topavg").label("BiOX top-face average")
    component.cpl("biox_topavg").selection().named("biox_top")


def solve_with_retry(model: Any, jmodel: Any, logger: logging.Logger) -> None:
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            logger.info("COMSOL solve attempt %d/2", attempt)
            jmodel.study("std1").createAutoSequences("all")
            model.solve()
            return
        except Exception as error:
            last_error = error
            logger.exception("COMSOL solve attempt %d failed", attempt)
    raise RuntimeError("COMSOL solve failed twice; diagnostic model will be saved if possible.") from last_error


def evaluate_scalar(jmodel: Any, tag: str, label: str, expression: str) -> float:
    numericals = jmodel.result().numerical()
    remove_if_present(numericals, tag)
    numericals.create(tag, "EvalGlobal")
    numerical = jmodel.result().numerical(tag)
    numerical.label(label)
    numerical.set("expr", make_java_string_array([expression]))
    values = flatten_java_numbers(numerical.getReal())
    if not values or not math.isfinite(float(values[0])):
        raise RuntimeError(f"COMSOL returned no finite value for {expression!r}.")
    return float(values[0])


def extract_results(jmodel: Any, material: Material2D, geometry: dict[str, float],
                    mode: str, electrode_model: str) -> dict[str, Any]:
    vmax = evaluate_scalar(jmodel, "biox_vmax", "Maximum potential", "biox_max(V)")
    vmin = evaluate_scalar(jmodel, "biox_vmin", "Minimum potential", "biox_min(V)")
    max_mises = evaluate_scalar(jmodel, "biox_smax", "Maximum von Mises stress", "biox_max(solid.mises)")
    top_w = evaluate_scalar(jmodel, "biox_topw", "Average top normal displacement", "biox_topavg(w)")
    result: dict[str, Any] = {
        "material": material.name,
        "mode": mode,
        "electrode_model": electrode_model,
        "status": "comsol_solved_and_checked",
        "pfm_target_d33_app_pm_per_V": material.pfm_target.d33_app_pm_per_v,
        "pfm_target_sd_pm_per_V": material.pfm_target.sd_pm_per_v,
        "pfm_target_n_cycles": material.pfm_target.n_cycles,
        "top_average_w_m": top_w,
        "max_mises_pa": max_mises,
        "vmax_v": vmax,
        "vmin_v": vmin,
        "delta_v_v": vmax - vmin,
        **geometry,
    }
    if mode == "pfm-converse":
        result["simulated_d_eff_pm_per_V"] = abs(top_w / geometry["vac_V"]) * 1e12
        result["simulated_to_pfm_target_ratio"] = result["simulated_d_eff_pm_per_V"] / material.pfm_target.d33_app_pm_per_v
    else:
        result["delta_v_mV"] = result["delta_v_v"] * 1e3
        result["electric_field_proxy_V_per_m"] = result["delta_v_v"] / (geometry["thickness_nm"] * 1e-9)
    return result


def create_result_plots(jmodel: Any, material: str, mode: str, output_dir: Path, logger: logging.Logger) -> list[str]:
    results = jmodel.result()
    for tag in ("v13_pg_stress", "v13_pg_potential", "v13_pg_displacement"):
        remove_if_present(results, tag)
    exported: list[str] = []
    results.create("v13_pg_stress", "PlotGroup3D")
    stress = jmodel.result("v13_pg_stress")
    stress.label(f"{material} - von Mises stress")
    stress.create("surf1", "Surface")
    stress.feature("surf1").set("expr", "solid.mises")
    stress.feature("surf1").set("unit", "MPa")
    stress.feature("surf1").set("colortable", "Thermal")
    stress.run()
    results.create("v13_pg_potential", "PlotGroup3D")
    potential = jmodel.result("v13_pg_potential")
    potential.label(f"{material} - electric potential")
    potential.create("surf1", "Surface")
    potential.feature("surf1").set("expr", "V")
    potential.feature("surf1").set("unit", "V")
    potential.feature("surf1").set("colortable", "Rainbow")
    potential.run()
    if mode == "pfm-converse":
        results.create("v13_pg_displacement", "PlotGroup3D")
        disp = jmodel.result("v13_pg_displacement")
        disp.label(f"{material} - converse normal displacement")
        disp.create("surf1", "Surface")
        disp.feature("surf1").set("expr", "w")
        disp.feature("surf1").set("unit", "nm")
        disp.feature("surf1").set("colortable", "Thermal")
        disp.run()

    exports = results.export()
    plot_specs = [("v13_img_stress", "v13_pg_stress", "stress")]
    plot_specs.append(("v13_img_potential", "v13_pg_potential", "potential"))
    if mode == "pfm-converse":
        plot_specs.append(("v13_img_displacement", "v13_pg_displacement", "displacement"))
    for tag, plot_tag, suffix in plot_specs:
        image_path = output_dir / f"{material}_{mode}_{suffix}.png"
        try:
            remove_if_present(exports, tag)
            exports.create(tag, plot_tag, "Image")
            export = results.export(tag)
            export.set("target", "file")
            export.set("imagetype", "png")
            export.set("pngfilename", str(image_path))
            export.set("size", "manualweb")
            export.set("width", make_java_int(1600))
            export.set("height", make_java_int(1000))
            export.set("resolution", make_java_int(150))
            export.set("options3d", "on")
            export.set("grid", "off")
            export.set("logo3d", "off")
            export.run()
            if image_path.is_file() and image_path.stat().st_size > 0:
                exported.append(str(image_path))
        except Exception:
            logger.exception("Could not export %s plot for %s", suffix, material)
    return exported


def process_material(client: Any, template: Path, output_dir: Path, material: Material2D,
                     geometry: dict[str, float], mode: str, model_cfg: dict[str, Any],
                     logger: logging.Logger) -> dict[str, Any]:
    model = client.load(str(template))
    jmodel = model.java
    failed = output_dir / f"{material.name}_{mode}_debug_failed.mph"
    try:
        set_model_parameters(jmodel, geometry, mode)
        selections = repair_geometry_and_selections(jmodel)
        physics_info = repair_physics(jmodel, material, geometry, mode, model_cfg, logger)
        configure_mesh(jmodel)
        configure_coupling_operators(jmodel)
        solve_with_retry(model, jmodel, logger)
        result = extract_results(jmodel, material, geometry, mode, physics_info["electrode_model"])
        result["top_boundary_ids"] = selections["biox_top"]
        result["bottom_boundary_ids"] = selections["biox_bottom"]
        result.update(physics_info)
        result["exported_images"] = create_result_plots(jmodel, material.name, mode, output_dir, logger)
        final_path = output_dir / f"{material.name}_piezo_{mode}_final.mph"
        model.save(str(final_path))
        if not final_path.is_file() or final_path.stat().st_size == 0:
            raise RuntimeError(f"Final MPH was not created: {final_path}")
        result["model_file"] = str(final_path)
        result["model_size_bytes"] = final_path.stat().st_size
        return result
    except Exception:
        logger.exception("Processing failed for %s", material.name)
        try:
            model.save(str(failed))
            logger.info("Saved diagnostic model: %s", failed)
        except Exception:
            logger.exception("Could not save diagnostic model for %s", material.name)
        raise
    finally:
        client.remove(model)


def write_results(results: list[dict[str, Any]], output_dir: Path, mode: str,
                  model_cfg: dict[str, Any]) -> tuple[Path, Path]:
    values = ({r["material"]: r["simulated_d_eff_pm_per_V"] for r in results}
              if mode == "pfm-converse" else {r["material"]: r["delta_v_v"] for r in results})
    order = order_from(values)
    comparison = {
        "status": "comsol_solved_and_checked",
        "mode": mode,
        "comsol_order": order,
        "pfm_target_order": list(PFM_ORDER),
        "trend_matches_pfm": order == list(PFM_ORDER),
        "warning": "Ranking mismatch is reported, never corrected by material-specific tuning." if order != list(PFM_ORDER) else "",
        "results": results,
        "model_config": model_cfg,
    }
    json_path = output_dir / f"BiOX_v13_{mode}_results.json"
    json_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = output_dir / f"BiOX_v13_{mode}_results.csv"
    columns = sorted({key for row in results for key in row})
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    return json_path, csv_path


def geometry_from_args(args: argparse.Namespace, model_cfg: dict[str, Any], material: str,
                       pressure_override: float | None = None) -> dict[str, float]:
    geometry_cfg = model_cfg["geometry"]
    if args.geometry_mode == "reference":
        length_um = args.length_um if args.length_um is not None else float(geometry_cfg["reference_length_um"])
        width_um = args.width_um if args.width_um is not None else float(geometry_cfg["reference_width_um"])
    else:
        if not args.morphology_inventory:
            raise ValueError("--morphology-inventory is required for --geometry-mode image.")
        length_um, width_um = read_image_geometry(args.morphology_inventory, material)
    thickness_nm = args.thickness_nm if args.thickness_nm is not None else float(geometry_cfg["effective_thickness_nm"])
    pressure = (pressure_override if pressure_override is not None else
                (args.pressure_mpa if args.pressure_mpa is not None else 100.0))
    vac = args.vac_V if args.vac_V is not None else float(model_cfg["pfm"]["drive_amplitude_V"])
    # Resolve lateral and through-thickness mesh scales separately.  Applying
    # a 1-nm thickness-based hmax to a 1-um sheet creates an unnecessary
    # multi-million-element isotropic tetrahedral mesh.
    hmax = (args.hmax_nm if args.hmax_nm is not None else
            min(length_um, width_um) * 1000.0 * float(model_cfg["mesh"]["hmax_fraction_of_lateral"]))
    hmin = args.hmin_nm if args.hmin_nm is not None else thickness_nm * float(model_cfg["mesh"]["hmin_fraction_of_thickness"])
    patch_sigma = (args.patch_sigma_nm if args.patch_sigma_nm is not None else
                   float(model_cfg["pfm"].get("contact_sigma_nm", 10.0)))
    if min(length_um, width_um, thickness_nm, hmax, hmin, patch_sigma) <= 0.0 or hmin >= hmax:
        raise ValueError("Geometry and mesh values must be positive and hmin < hmax.")
    return {
        "length_um": float(length_um),
        "width_um": float(width_um),
        "thickness_nm": float(thickness_nm),
        "pressure_mpa": float(pressure),
        "vac_V": float(vac),
        "hmax_nm": float(hmax),
        "hmin_nm": float(hmin),
        "patch_sigma_nm": float(patch_sigma),
        "selection_tolerance_nm": max(float(thickness_nm) * 0.01, 1e-6),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PFM-anchored BiOX COMSOL 6.3 automation.")
    parser.add_argument("--template-mph", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--materials-json", type=Path, default=DEFAULT_MATERIALS)
    parser.add_argument("--model-json", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--morphology-inventory", type=Path)
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR.parent / "comsol_run")
    parser.add_argument("--comsol-root", type=Path, default=DEFAULT_COMSOL_ROOT)
    parser.add_argument("--comsol-version", default="6.3")
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--mode", choices=["pfm-converse", "direct-pressure"], default="pfm-converse")
    parser.add_argument("--geometry-mode", choices=["reference", "image"], default="reference")
    parser.add_argument("--materials", nargs="+", choices=["BiOCl", "BiOBr", "BiOI"], default=list(PFM_ORDER))
    parser.add_argument("--length-um", type=float)
    parser.add_argument("--width-um", type=float)
    parser.add_argument("--thickness-nm", type=float)
    parser.add_argument("--pressure-mpa", type=float)
    parser.add_argument(
        "--pressure-sweep", action="store_true",
        help="For direct-pressure mode, solve the configured 0/20/40/60/80/100 MPa series.",
    )
    parser.add_argument("--vac-V", dest="vac_V", type=float)
    parser.add_argument("--hmax-nm", type=float)
    parser.add_argument("--hmin-nm", type=float)
    parser.add_argument("--patch-sigma-nm", type=float)
    parser.add_argument("--allow-unverified-epsilon", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Run parameter/morphology checks without starting COMSOL.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    logger = configure_logging(args.output_dir)
    try:
        materials = load_materials(args.materials_json)
        model_cfg = read_model_config(args.model_json)
        constitutive_source = str(model_cfg.get("c3d_extension", {}).get("constitutive_source", "legacy_2d_bridge"))
        if (constitutive_source != "dft_apparent"
                and not args.allow_unverified_epsilon and not args.dry_run):
            raise ValueError(
                "The dielectric entries are sensitivity-only values. Add --allow-unverified-epsilon "
                "only when you accept this documented uncertainty.")
        if args.pressure_sweep and args.mode != "direct-pressure":
            raise ValueError("--pressure-sweep is only valid with --mode direct-pressure.")
        configured_pressures = [float(value) for value in model_cfg["direct_pressure"]["pressure_mpa"]]
        if args.pressure_mpa is not None:
            pressure_values = [float(args.pressure_mpa)]
        elif args.pressure_sweep:
            pressure_values = configured_pressures
        else:
            pressure_values = [100.0]
        geometries = {name: geometry_from_args(args, model_cfg, name, pressure_values[0])
                      for name in args.materials}
        logger.info("Mode=%s; geometry_mode=%s; target PFM order=%s", args.mode, args.geometry_mode, " > ".join(PFM_ORDER))
        if args.dry_run:
            payload = {
                "status": "dry_run_complete",
                "mode": args.mode,
                "geometry_mode": args.geometry_mode,
                "target_order": list(PFM_ORDER),
                "materials": args.materials,
                "geometries": geometries,
                "pressure_values_mpa": pressure_values,
                "epsilon_warning": {name: materials[name].epsilon_status for name in args.materials},
                "constitutive_source": constitutive_source,
            }
            path = args.output_dir / f"BiOX_v13_{args.mode}_dry_run.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if not args.template_mph.is_file():
            raise FileNotFoundError(f"Template MPH not found: {args.template_mph}")
        prepare_comsol_environment(args.comsol_root)
        try:
            import mph
        except ImportError as error:
            raise RuntimeError("MPh is not installed. Install the pinned requirements in this v1.3.0 directory.") from error
        mph.option("session", "stand-alone")
        client = mph.start(cores=args.cores, version=args.comsol_version)
        results: list[dict[str, Any]] = []
        try:
            for name in args.materials:
                for pressure in pressure_values:
                    geometry = geometry_from_args(args, model_cfg, name, pressure)
                    run_dir = args.output_dir
                    if args.mode == "direct-pressure" and args.pressure_sweep:
                        run_dir = args.output_dir / f"pressure_{pressure:g}MPa"
                    run_dir.mkdir(parents=True, exist_ok=True)
                    results.append(process_material(client, args.template_mph, run_dir, materials[name], geometry, args.mode, model_cfg, logger))
        finally:
            try:
                client.clear()
            except Exception:
                logger.exception("Could not clear COMSOL client.")
        json_path, csv_path = write_results(results, args.output_dir, args.mode, model_cfg)
        logger.info("Results written: %s and %s", json_path, csv_path)
        print(json.dumps({"status": "complete", "json": str(json_path), "csv": str(csv_path)}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        logger.error("Fatal error: %s", error)
        logger.debug(traceback.format_exc())
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
