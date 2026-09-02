#!/usr/bin/env python3
"""Repair and solve the supplied BiOX COMSOL model through MPh + Java API.

The script loads BiOCl_piezo.mph as the template for each material. It keeps
the existing physics architecture, repairs the selections and constitutive
inputs, solves the stationary model, exports plots/results, and saves three
independent MPH files. Use --dry-run for a dependency-free material precheck.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


EPS0 = 8.8541878128e-12
EXPECTED_PFM_ORDER = ["BiOI", "BiOBr", "BiOCl"]
DEFAULT_INPUT = Path("BiOCl_piezo.mph")
DEFAULT_COMSOL_ROOT = Path("COMSOL63") / "Multiphysics"
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class MaterialState:
    name: str
    c_pa: list[list[float]]
    s_per_pa: list[list[float]]
    e_es: list[list[float]]
    d_et: list[list[float]]
    epsilon_r_s: list[list[float]]
    epsilon_r_t: list[list[float]]
    analytic_delta_v: float
    analytic_d33_c_per_n: float
    pfm_max_amplitude_m: float
    source_note: str


def invert_matrix(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    """Invert a square matrix with pivoted Gauss-Jordan elimination."""
    n = len(matrix)
    work = [list(row) + [1.0 if i == j else 0.0 for j in range(n)]
            for i, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-30:
            raise ValueError("Elasticity matrix is singular.")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [value / scale for value in work[column]]
        for row in range(n):
            if row == column:
                continue
            factor = work[row][column]
            work[row] = [value - factor * pivot_value
                         for value, pivot_value in zip(work[row], work[column])]
    return [row[n:] for row in work]


def matmul(left: Sequence[Sequence[float]],
           right: Sequence[Sequence[float]]) -> list[list[float]]:
    return [
        [sum(left[i][k] * right[k][j] for k in range(len(right)))
         for j in range(len(right[0]))]
        for i in range(len(left))
    ]


def transpose(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def is_positive_definite(matrix: Sequence[Sequence[float]]) -> bool:
    """Cholesky test without third-party dependencies."""
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    try:
        for i in range(n):
            for j in range(i + 1):
                subtotal = sum(lower[i][k] * lower[j][k] for k in range(j))
                if i == j:
                    value = matrix[i][i] - subtotal
                    if value <= 0.0:
                        return False
                    lower[i][j] = math.sqrt(value)
                else:
                    lower[i][j] = (matrix[i][j] - subtotal) / lower[j][j]
    except (ValueError, ZeroDivisionError):
        return False
    return True


def flatten_row_major(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [value for row in matrix for value in row]


def flatten_column_major(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [matrix[row][column]
            for column in range(len(matrix[0]))
            for row in range(len(matrix))]


def format_values(values: Iterable[float]) -> list[str]:
    return [f"{value:.16g}" for value in values]


def dielectric_key(mode: str) -> str:
    return {
        "prompt": "epsilon_prompt",
        "vasp-electronic": "epsilon_vasp_electronic",
        "vasp-total": "epsilon_vasp_total",
    }[mode]


def build_material_state(name: str, raw: dict[str, Any], epsilon_mode: str,
                         pressure_mpa: float, thickness_nm: float) -> MaterialState:
    c_pa = [[float(value) * 1e9 for value in row] for row in raw["c_gpa"]]
    if len(c_pa) != 6 or any(len(row) != 6 for row in c_pa):
        raise ValueError(f"{name}: c_gpa must be 6x6.")
    if any(abs(c_pa[i][j] - c_pa[j][i]) > 1e-5 * max(1.0, abs(c_pa[i][j]))
           for i in range(6) for j in range(6)):
        raise ValueError(f"{name}: elasticity matrix is not symmetric.")
    if not is_positive_definite(c_pa):
        raise ValueError(f"{name}: elasticity matrix is not positive definite.")

    e_values = [float(value) for value in raw["e31_e32_e33_c_per_m2"]]
    if len(e_values) != 3:
        raise ValueError(f"{name}: expected [e31, e32, e33].")
    e_es = [[0.0] * 6 for _ in range(3)]
    e_es[2][0:3] = e_values

    epsilon_diag = [float(value) for value in raw[dielectric_key(epsilon_mode)]]
    if len(epsilon_diag) != 3 or any(value <= 0.0 for value in epsilon_diag):
        raise ValueError(f"{name}: dielectric diagonal must contain 3 positives.")
    epsilon_r_s = [[epsilon_diag[i] if i == j else 0.0 for j in range(3)]
                   for i in range(3)]

    s_per_pa = invert_matrix(c_pa)
    d_et = matmul(e_es, s_per_pa)
    dielectric_increment = matmul(d_et, transpose(e_es))
    epsilon_r_t = [
        [epsilon_r_s[i][j] + dielectric_increment[i][j] / EPS0
         for j in range(3)]
        for i in range(3)
    ]

    pressure_pa = pressure_mpa * 1e6
    thickness_m = thickness_nm * 1e-9
    d33 = d_et[2][2]
    analytic_delta_v = abs(d33 * pressure_pa * thickness_m /
                           (EPS0 * epsilon_r_t[2][2]))

    return MaterialState(
        name=name,
        c_pa=c_pa,
        s_per_pa=s_per_pa,
        e_es=e_es,
        d_et=d_et,
        epsilon_r_s=epsilon_r_s,
        epsilon_r_t=epsilon_r_t,
        analytic_delta_v=analytic_delta_v,
        analytic_d33_c_per_n=d33,
        pfm_max_amplitude_m=float(raw["pfm_max_amplitude_m"]),
        source_note=str(raw.get("source_note", "")),
    )


def write_precheck(states: Sequence[MaterialState], output_dir: Path,
                   epsilon_mode: str, pressure_mpa: float,
                   thickness_nm: float) -> Path:
    output = output_dir / "BiOX_analytic_precheck.csv"
    ranked = sorted(states, key=lambda state: state.analytic_delta_v, reverse=True)
    analytic_order = " > ".join(state.name for state in ranked)
    pfm_order = " > ".join(EXPECTED_PFM_ORDER)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "material", "epsilon_mode", "pressure_mpa", "thickness_nm",
            "derived_d33_C_per_N", "derived_d33_pm_per_V",
            "analytic_deltaV_V", "analytic_deltaV_mV",
            "pfm_max_amplitude_m", "analytic_order", "pfm_order",
            "trend_matches_pfm", "status",
        ])
        writer.writeheader()
        for state in states:
            writer.writerow({
                "material": state.name,
                "epsilon_mode": epsilon_mode,
                "pressure_mpa": pressure_mpa,
                "thickness_nm": thickness_nm,
                "derived_d33_C_per_N": f"{state.analytic_d33_c_per_n:.12g}",
                "derived_d33_pm_per_V": f"{state.analytic_d33_c_per_n * 1e12:.12g}",
                "analytic_deltaV_V": f"{state.analytic_delta_v:.12g}",
                "analytic_deltaV_mV": f"{state.analytic_delta_v * 1e3:.12g}",
                "pfm_max_amplitude_m": f"{state.pfm_max_amplitude_m:.12g}",
                "analytic_order": analytic_order,
                "pfm_order": pfm_order,
                "trend_matches_pfm": analytic_order == pfm_order,
                "status": "analytic_precheck_not_comsol_result",
            })
    return output


def configure_logging(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("biox")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_handler = logging.FileHandler(output_dir / "BiOX_COMSOL_run.log",
                                       mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def prepare_comsol_environment(comsol_root: Path) -> None:
    if not comsol_root.is_dir():
        raise FileNotFoundError(f"COMSOL root not found: {comsol_root}")
    bin_dir = comsol_root / "bin" / "win64"
    java_home = comsol_root / "java" / "win64" / "jre"
    java_exe = java_home / "bin" / "java.exe"
    if not java_exe.is_file():
        raise FileNotFoundError(f"COMSOL Java runtime not found: {java_exe}")
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join([str(bin_dir), str(java_home / "bin"), current_path])
    os.environ["JAVA_HOME"] = str(java_home)
    os.environ["COMSOL_ROOT"] = str(comsol_root)


def java_tags(container: Any) -> list[str]:
    return [str(tag) for tag in container.tags()]


def remove_if_present(container: Any, tag: str) -> None:
    if bool(container.hasTag(tag)):
        container.remove(tag)


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


def set_model_parameters(jmodel: Any, model_cfg: dict[str, float]) -> None:
    parameters = {
        "biox_Lx": f"{model_cfg['length_nm']:.12g}[nm]",
        "biox_Ly": f"{model_cfg['width_nm']:.12g}[nm]",
        "biox_t": f"{model_cfg['thickness_nm']:.12g}[nm]",
        "biox_p": f"{model_cfg['pressure_mpa']:.12g}[MPa]",
        "biox_hmax": f"{model_cfg['mesh_hmax_nm']:.12g}[nm]",
        "biox_hmin": f"{model_cfg['mesh_hmin_nm']:.12g}[nm]",
        "biox_sel_tol": f"{model_cfg['selection_tolerance_nm']:.12g}[nm]",
    }
    for name, value in parameters.items():
        jmodel.param().set(name, value)


def repair_geometry_and_selections(jmodel: Any) -> dict[str, list[int]]:
    component = jmodel.component("comp1")
    geometry = component.geom("geom1")
    if not bool(geometry.feature().hasTag("blk1")):
        raise RuntimeError("Expected geometry feature comp1/geom1/blk1 is missing.")
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
        node_type = feature_type(node)
        if node_type == "ElectricPotential" or tag == "pot1":
            features.remove(tag)
            removed.append(tag)
    return removed


def repair_physics(jmodel: Any, state: MaterialState) -> list[str]:
    component = jmodel.component("comp1")
    solid = component.physics("solid")
    es = component.physics("es")

    if not bool(solid.feature().hasTag("pzm1")):
        raise RuntimeError("Expected Piezoelectric Material node solid/pzm1 is missing.")
    pzm = solid.feature("pzm1")
    pzm.selection().geom("geom1", 3)
    pzm.selection().all()
    pzm.set("SolidModel", "Anisotropic")
    pzm.set("ConstitutiveRelation", "StressCharge")
    pzm.set("cE_mat", "userdef")
    pzm.set("cE", make_java_string_array(format_values(flatten_row_major(state.c_pa))))
    pzm.set("eES_mat", "userdef")
    # COMSOL serializes the 3-by-6 eES table column by column:
    # eES11, eES21, eES31, eES12, ..., eES36.
    pzm.set("eES", make_java_string_array(format_values(flatten_column_major(state.e_es))))
    pzm.set("epsilonrS_mat", "userdef")
    pzm.set("epsilonrS", make_java_string_array(
        format_values(flatten_row_major(state.epsilon_r_s))))
    pzm.set("coordinateSystem", "GlobalSystem")

    remove_if_present(solid.feature(), "fix1")
    solid.create("fix1", "Fixed", 2)
    solid.feature("fix1").label("Fixed bottom z face")
    solid.feature("fix1").selection().named("biox_bottom")

    remove_if_present(solid.feature(), "bndl1")
    solid.create("bndl1", "BoundaryLoad", 2)
    solid.feature("bndl1").label("Top pressure")
    solid.feature("bndl1").selection().named("biox_top")
    solid.feature("bndl1").set("forceType", "FollowerPressure")
    solid.feature("bndl1").set("pressure", "biox_p")

    removed = remove_external_electric_potentials(es)
    if not bool(es.feature().hasTag("ccnp1")):
        es.create("ccnp1", "ChargeConservationPiezo", 3)
    ccnp = es.feature("ccnp1")
    ccnp.label("Piezoelectric charge conservation")
    ccnp.selection().geom("geom1", 3)
    ccnp.selection().all()
    ccnp.set("materialType", "solid")
    ccnp.set("epsilonrS_mat", "userdef")
    ccnp.set("epsilonrS", make_java_string_array(
        format_values(flatten_row_major(state.epsilon_r_s))))
    ccnp.set("coordinateSystem", "GlobalSystem")

    remove_if_present(es.feature(), "gnd1")
    es.create("gnd1", "Ground", 2)
    es.feature("gnd1").label("Ground bottom z face")
    es.feature("gnd1").selection().named("biox_bottom")

    if not bool(component.multiphysics().hasTag("pze1")):
        raise RuntimeError("Expected Piezoelectricity coupling comp1/pze1 is missing.")
    component.multiphysics("pze1").active(True)
    return removed


def configure_mesh(jmodel: Any) -> None:
    mesh = jmodel.component("comp1").mesh("mesh1")
    if not bool(mesh.feature().hasTag("size")):
        raise RuntimeError("Expected default mesh size feature mesh1/size is missing.")
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
    logger.info("Regenerating COMSOL automatic solver sequences")
    jmodel.study("std1").createAutoSequences("all")
    for attempt in (1, 2):
        try:
            logger.info("Stationary solve attempt %d/2", attempt)
            model.solve()
            return
        except Exception as error:
            last_error = error
            logger.exception("Solve attempt %d failed", attempt)
            if attempt == 1:
                logger.info("Regenerating COMSOL automatic solver sequences before retry")
                jmodel.study("std1").createAutoSequences("all")
    raise RuntimeError("COMSOL stationary solve failed twice.") from last_error


def evaluate_scalar(jmodel: Any, tag: str, label: str, expression: str) -> float:
    numericals = jmodel.result().numerical()
    remove_if_present(numericals, tag)
    numericals.create(tag, "EvalGlobal")
    numerical = jmodel.result().numerical(tag)
    numerical.label(label)
    numerical.set("expr", make_java_string_array([expression]))
    values = flatten_java_numbers(numerical.getReal())
    if not values:
        raise RuntimeError(f"COMSOL returned no value for {expression!r}.")
    value = float(values[0])
    if not math.isfinite(value):
        raise RuntimeError(f"COMSOL returned non-finite value for {expression!r}: {value}")
    return value


def extract_results(jmodel: Any, state: MaterialState,
                    model_cfg: dict[str, float]) -> dict[str, Any]:
    vmax = evaluate_scalar(jmodel, "biox_vmax", "Maximum electric potential", "biox_max(V)")
    vmin = evaluate_scalar(jmodel, "biox_vmin", "Minimum electric potential", "biox_min(V)")
    max_mises = evaluate_scalar(jmodel, "biox_smax", "Maximum von Mises stress",
                                "biox_max(solid.mises)")
    max_abs_sz = evaluate_scalar(jmodel, "biox_szmax", "Maximum absolute z stress",
                                 "biox_max(abs(solid.sz))")
    top_w = evaluate_scalar(jmodel, "biox_topw", "Average top z displacement",
                            "biox_topavg(w)")
    delta_v = vmax - vmin
    if delta_v <= 1e-12:
        raise RuntimeError(f"Solved delta V is zero or too small: {delta_v:.6g} V")
    pressure_pa = model_cfg["pressure_mpa"] * 1e6
    thickness_m = model_cfg["thickness_nm"] * 1e-9
    g_eff = delta_v / (pressure_pa * thickness_m)
    d_eff = EPS0 * state.epsilon_r_t[2][2] * g_eff
    return {
        "material": state.name,
        "status": "comsol_solved_and_checked",
        "vmax_v": vmax,
        "vmin_v": vmin,
        "delta_v_v": delta_v,
        "delta_v_mv": delta_v * 1e3,
        "max_mises_pa": max_mises,
        "max_abs_sz_pa": max_abs_sz,
        "top_average_w_m": top_w,
        "effective_g_vm_per_n": g_eff,
        "effective_d_c_per_n": d_eff,
        "effective_d_pm_per_v": d_eff * 1e12,
        "analytic_precheck_delta_v_v": state.analytic_delta_v,
        "comsol_to_analytic_ratio": delta_v / state.analytic_delta_v,
        "pressure_mpa": model_cfg["pressure_mpa"],
        "length_nm": model_cfg["length_nm"],
        "width_nm": model_cfg["width_nm"],
        "thickness_nm": model_cfg["thickness_nm"],
    }


def create_result_plots(jmodel: Any, material: str, delta_v: float,
                        output_dir: Path, logger: logging.Logger) -> list[str]:
    results = jmodel.result()
    for tag in ("biox_pg_stress", "biox_pg_potential"):
        remove_if_present(results, tag)

    results.create("biox_pg_stress", "PlotGroup3D")
    stress_group = jmodel.result("biox_pg_stress")
    stress_group.label(f"{material} - von Mises stress")
    stress_group.set("showlegendsmaxmin", "on")
    stress_group.create("surf1", "Surface")
    stress_surface = stress_group.feature("surf1")
    stress_surface.set("expr", "solid.mises")
    stress_surface.set("unit", "MPa")
    stress_surface.set("colortable", "Thermal")
    stress_surface.set("resolution", "fine")
    stress_group.run()

    results.create("biox_pg_potential", "PlotGroup3D")
    potential_group = jmodel.result("biox_pg_potential")
    potential_group.label(f"{material} - centered piezoelectric potential")
    potential_group.set("showlegendsmaxmin", "on")
    potential_group.create("surf1", "Surface")
    potential_surface = potential_group.feature("surf1")
    potential_surface.set("expr", "V-(biox_max(V)+biox_min(V))/2")
    potential_surface.set("unit", "V")
    potential_surface.set("colortable", "Rainbow")
    potential_surface.set("colorscalemode", "linearsymmetric")
    potential_surface.set("rangecoloractive", "on")
    potential_surface.set("rangecolormin", -delta_v / 2.0)
    potential_surface.set("rangecolormax", delta_v / 2.0)
    potential_surface.set("resolution", "fine")
    potential_group.run()

    exported: list[str] = []
    exports = results.export()
    for tag, plot_tag, suffix in (
        ("biox_img_stress", "biox_pg_stress", "stress"),
        ("biox_img_potential", "biox_pg_potential", "potential_centered"),
    ):
        image_path = output_dir / f"{material}_{suffix}.png"
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
            else:
                logger.warning("COMSOL image export did not create %s", image_path)
        except Exception:
            logger.exception("Image export failed for %s", plot_tag)
    return exported


def process_material(client: Any, input_mph: Path, output_dir: Path,
                     state: MaterialState, model_cfg: dict[str, float],
                     logger: logging.Logger) -> dict[str, Any]:
    logger.info("Loading template for %s: %s", state.name, input_mph)
    model = client.load(str(input_mph))
    jmodel = model.java
    failed_path = output_dir / f"{state.name}_piezo_debug_failed.mph"
    try:
        set_model_parameters(jmodel, model_cfg)
        selections = repair_geometry_and_selections(jmodel)
        removed_potentials = repair_physics(jmodel, state)
        configure_mesh(jmodel)
        configure_coupling_operators(jmodel)
        logger.info("%s selections: %s; removed potentials: %s",
                    state.name, selections, removed_potentials)
        solve_with_retry(model, jmodel, logger)
        result = extract_results(jmodel, state, model_cfg)
        result["top_boundary_ids"] = selections["biox_top"]
        result["bottom_boundary_ids"] = selections["biox_bottom"]
        result["removed_electric_potential_features"] = removed_potentials
        result["exported_images"] = create_result_plots(
            jmodel, state.name, result["delta_v_v"], output_dir, logger)

        final_path = output_dir / f"{state.name}_piezo_final.mph"
        model.save(str(final_path))
        if not final_path.is_file() or final_path.stat().st_size == 0:
            raise RuntimeError(f"Final MPH was not created: {final_path}")
        result["model_file"] = str(final_path)
        result["model_size_bytes"] = final_path.stat().st_size
        logger.info("%s complete: delta V = %.6g V; saved %s",
                    state.name, result["delta_v_v"], final_path)
        return result
    except Exception:
        logger.exception("%s processing failed", state.name)
        try:
            model.save(str(failed_path))
            logger.info("Saved diagnostic model: %s", failed_path)
        except Exception:
            logger.exception("Could not save diagnostic model for %s", state.name)
        raise
    finally:
        client.remove(model)


def write_comsol_results(results: Sequence[dict[str, Any]], output_dir: Path,
                         config: dict[str, Any]) -> tuple[Path, Path]:
    ordered = sorted(results, key=lambda item: item["delta_v_v"], reverse=True)
    comsol_order = [item["material"] for item in ordered]
    comparison = {
        "status": "comsol_solved_and_checked",
        "comsol_order": comsol_order,
        "pfm_order": EXPECTED_PFM_ORDER,
        "trend_matches_pfm": comsol_order == EXPECTED_PFM_ORDER,
        "warning": ("The computed order does not match PFM; material constants were not altered."
                    if comsol_order != EXPECTED_PFM_ORDER else ""),
        "results": list(results),
        "config_snapshot": config,
    }
    json_path = output_dir / "BiOX_COMSOL_results.json"
    json_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = output_dir / "BiOX_COMSOL_results.csv"
    columns = [
        "material", "vmax_v", "vmin_v", "delta_v_v", "delta_v_mv",
        "max_mises_pa", "max_abs_sz_pa", "top_average_w_m",
        "effective_g_vm_per_n", "effective_d_c_per_n", "effective_d_pm_per_v",
        "analytic_precheck_delta_v_v", "comsol_to_analytic_ratio",
        "pressure_mpa", "length_nm", "width_nm", "thickness_nm",
        "model_file", "model_size_bytes", "status",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    return json_path, csv_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair and solve BiOCl/BiOBr/BiOI piezoelectric COMSOL models.")
    parser.add_argument("--input-mph", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--config",
        type=Path,
        default=SCRIPT_DIR.parent / "config" / "biox_materials.json",
    )
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "comsol_run")
    parser.add_argument("--comsol-root", type=Path, default=DEFAULT_COMSOL_ROOT)
    parser.add_argument("--comsol-version", default="6.3")
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--materials", nargs="+", choices=["BiOCl", "BiOBr", "BiOI"],
                        default=["BiOCl", "BiOBr", "BiOI"])
    parser.add_argument("--epsilon-mode",
                        choices=["prompt", "vasp-electronic", "vasp-total"],
                        default="prompt")
    parser.add_argument("--pressure-mpa", type=float)
    parser.add_argument("--length-nm", type=float)
    parser.add_argument("--width-nm", type=float)
    parser.add_argument("--thickness-nm", type=float)
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and transform inputs without starting COMSOL.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger = configure_logging(args.output_dir)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        model_cfg = {key: float(value) for key, value in config["model"].items()}
        for key, override in (
            ("pressure_mpa", args.pressure_mpa),
            ("length_nm", args.length_nm),
            ("width_nm", args.width_nm),
            ("thickness_nm", args.thickness_nm),
        ):
            if override is not None:
                model_cfg[key] = float(override)
        if any(model_cfg[key] <= 0.0 for key in (
                "pressure_mpa", "length_nm", "width_nm", "thickness_nm",
                "mesh_hmax_nm", "mesh_hmin_nm", "selection_tolerance_nm")):
            raise ValueError("Geometry, pressure, mesh sizes, and tolerance must be positive.")
        if model_cfg["mesh_hmin_nm"] >= model_cfg["mesh_hmax_nm"]:
            raise ValueError("mesh_hmin_nm must be smaller than mesh_hmax_nm.")

        states = [build_material_state(
            name, config["materials"][name], args.epsilon_mode,
            model_cfg["pressure_mpa"], model_cfg["thickness_nm"])
            for name in args.materials]
        precheck_path = write_precheck(states, args.output_dir, args.epsilon_mode,
                                       model_cfg["pressure_mpa"],
                                       model_cfg["thickness_nm"])
        analytic_order = [state.name for state in sorted(
            states, key=lambda state: state.analytic_delta_v, reverse=True)]
        logger.info("Analytic precheck written: %s", precheck_path)
        logger.info("Analytic order: %s; PFM order: %s",
                    " > ".join(analytic_order), " > ".join(EXPECTED_PFM_ORDER))
        if analytic_order != [name for name in EXPECTED_PFM_ORDER if name in args.materials]:
            logger.warning("Input-derived trend differs from PFM; constants will not be tuned.")
        if args.dry_run:
            print(json.dumps({
                "status": "dry_run_complete",
                "precheck": str(precheck_path),
                "analytic_order": analytic_order,
                "pfm_order": EXPECTED_PFM_ORDER,
            }, ensure_ascii=False, indent=2))
            return 0

        if not args.input_mph.is_file():
            raise FileNotFoundError(f"Input MPH not found: {args.input_mph}")
        prepare_comsol_environment(args.comsol_root)
        try:
            import mph
        except ImportError as error:
            raise RuntimeError(
                "MPh is not installed in this Python environment. Run: python -m pip install MPh") from error

        # Windows stand-alone mode avoids the mphserver/Tomcat port layer and
        # keeps this local batch run independent of per-user server state.
        mph.option("session", "stand-alone")
        logger.info("Starting COMSOL %s with %d cores", args.comsol_version, args.cores)
        client = mph.start(cores=args.cores, version=args.comsol_version)
        results: list[dict[str, Any]] = []
        try:
            for state in states:
                results.append(process_material(
                    client, args.input_mph, args.output_dir, state, model_cfg, logger))
        finally:
            try:
                client.clear()
            except Exception:
                logger.exception("Could not clear COMSOL client")

        json_path, csv_path = write_comsol_results(results, args.output_dir, config)
        logger.info("All requested materials completed: %s, %s", json_path, csv_path)
        return 0
    except Exception as error:
        logger.error("Fatal error: %s", error)
        logger.debug("%s", traceback.format_exc())
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
