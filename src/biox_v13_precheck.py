#!/usr/bin/env python3
"""Dependency-free precheck for the PFM-anchored v1.3.0 parameter set."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from biox_v13_core import PFM_ORDER, load_materials, order_from, relative_targets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check v1.3.0 DFT/apparent PFM inputs and targets.")
    parser.add_argument(
        "--materials-json", type=Path,
        default=SCRIPT_DIR.parent / "config" / "materials_dft_apparent.json",
    )
    parser.add_argument(
        "--model-json", type=Path,
        default=SCRIPT_DIR.parent / "config" / "model_v13_apparent_dft.json",
    )
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR.parent / "data" / "precheck")
    parser.add_argument("--thickness-nm", type=float, default=1.0)
    parser.add_argument("--materials", nargs="+", choices=["BiOCl", "BiOBr", "BiOI"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.thickness_nm <= 0.0:
        raise ValueError("--thickness-nm must be positive.")
    materials = load_materials(args.materials_json)
    selected = args.materials or list(materials)
    selected_materials = {name: materials[name] for name in selected}
    intrinsic_values = {
        name: selected_materials[name].d11_derived_pm_per_v
        for name in selected
        if selected_materials[name].c2d_N_per_m is not None
        and selected_materials[name].e2d_pC_per_m is not None
    }
    pfm_values = {name: selected_materials[name].pfm_target.d33_app_pm_per_v for name in selected}
    intrinsic_order = order_from(intrinsic_values)
    pfm_order = order_from(pfm_values)
    expected = [name for name in PFM_ORDER if name in selected]

    rows = []
    for name in selected:
        material = selected_materials[name]
        if material.constitutive_status.startswith("DFT_"):
            c3d, e3d, eps = material.dft_apparent_3d()
            d11_reported = d11_derived = d31_reported = d31_derived = "not_applicable"
        else:
            c3d, e3d, eps = material.effective_3d(args.thickness_nm)
            d11_reported = f"{material.d11_reported_pm_per_v:.10g}"
            d11_derived = f"{material.d11_derived_pm_per_v:.10g}"
            d31_reported = f"{material.d31_reported_pm_per_v:.10g}"
            d31_derived = f"{material.d31_derived_pm_per_v:.10g}"
        rows.append({
            "material": name,
            "d11_reported_pm_per_V": d11_reported,
            "d11_derived_pm_per_V": d11_derived,
            "d31_reported_pm_per_V": d31_reported,
            "d31_derived_pm_per_V": d31_derived,
            "pfm_d33_app_pm_per_V": f"{material.pfm_target.d33_app_pm_per_v:.10g}",
            "pfm_sd_pm_per_V": f"{material.pfm_target.sd_pm_per_v:.10g}",
            "pfm_relative_to_BiOCl": f"{pfm_values[name] / pfm_values.get('BiOCl', pfm_values[name]):.10g}",
            "effective_thickness_nm": f"{args.thickness_nm:.10g}",
            "epsilon_status": material.epsilon_status,
            "effective_c11_Pa": f"{c3d[0][0]:.10g}",
            "effective_e31_C_per_m2": f"{e3d[2][0]:.10g}",
            "epsilon_r_zz": f"{eps[2][2]:.10g}",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "v13_parameter_precheck.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "status": "precheck_complete",
        "source": str(args.materials_json),
        "model_config": str(args.model_json),
        "effective_thickness_nm": args.thickness_nm,
        "intrinsic_d11_order": intrinsic_order,
        "pfm_target_order": pfm_order,
        "expected_pfm_order": expected,
        "intrinsic_order_matches_pfm": bool(intrinsic_order) and intrinsic_order == expected,
        "pfm_order_matches_target": pfm_order == expected,
        "pfm_relative_targets": relative_targets(selected_materials),
        "rows": rows,
        "interpretation": (
            "For the legacy branch, d11 is a 2D consistency check. For the DFT-apparent "
            "branch, C^E and dielectric data are first-principles inputs and d33_app is "
            "a response-level closure; neither branch should be reported as an intrinsic "
            "bulk d33 calibration."
        ),
    }
    json_path = args.output_dir / "v13_parameter_precheck.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "csv": str(csv_path),
        "json": str(json_path),
        "intrinsic_d11_order": intrinsic_order,
        "pfm_target_order": pfm_order,
        "target_order": expected,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
