#!/usr/bin/env python3
"""Analytic audit for the BiOX phase-2 sensitivity study.

This does not start COMSOL. It reuses the validated constitutive conversion
from the phase-1 script and evaluates the linear-model scaling over dielectric
conventions, pressure, and thickness. The output is an audit table, not a
replacement for finite-element results.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_base(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("biox_phase2_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import base script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    script_dir = Path(__file__).resolve().parent.parent
    parser.add_argument("--base-script", type=Path,
                        default=script_dir / "inputs" /
                                "biox_comsol_automation_phase2_base.py")
    parser.add_argument("--config", type=Path,
                        default=script_dir / "inputs" /
                                "biox_materials_phase2_snapshot.json")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--pressures-mpa", nargs="+", type=float,
                        default=[10.0, 25.0, 50.0, 100.0, 200.0])
    parser.add_argument("--thicknesses-nm", nargs="+", type=float,
                        default=[5.0, 10.0, 20.0])
    parser.add_argument("--epsilon-modes", nargs="+",
                        choices=["prompt", "vasp-electronic", "vasp-total"],
                        default=["prompt", "vasp-electronic", "vasp-total"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    base = load_base(args.base_script)
    materials = list(config["materials"])
    rows: list[dict[str, Any]] = []
    for epsilon_mode in args.epsilon_modes:
        for pressure_mpa in args.pressures_mpa:
            for thickness_nm in args.thicknesses_nm:
                states = [base.build_material_state(
                    name, config["materials"][name], epsilon_mode,
                    pressure_mpa, thickness_nm)
                    for name in materials]
                ranked = sorted(states, key=lambda state: state.analytic_delta_v,
                                reverse=True)
                order = ">".join(state.name for state in ranked)
                for state in states:
                    pressure_pa = pressure_mpa * 1e6
                    thickness_m = thickness_nm * 1e-9
                    delta_v = state.analytic_delta_v
                    rows.append({
                        "material": state.name,
                        "epsilon_mode": epsilon_mode,
                        "pressure_mpa": pressure_mpa,
                        "thickness_nm": thickness_nm,
                        "epsilon_r_t_zz": state.epsilon_r_t[2][2],
                        "e33_c_per_m2": state.e_es[2][2],
                        "d33_c_per_n": state.analytic_d33_c_per_n,
                        "d33_pm_per_v": state.analytic_d33_c_per_n * 1e12,
                        "delta_v_v": delta_v,
                        "delta_v_mv": delta_v * 1e3,
                        "g_eff_vm_per_n": delta_v / (pressure_pa * thickness_m),
                        "analytic_order": order,
                    })

    csv_path = args.output_dir / "phase2_analytic_sensitivity.csv"
    columns = list(rows[0]) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, Any] = {
        "status": "analytic_only",
        "materials": materials,
        "epsilon_modes": args.epsilon_modes,
        "pressures_mpa": args.pressures_mpa,
        "thicknesses_nm": args.thicknesses_nm,
        "rows": len(rows),
        "data_quality_flags": [
            "e31/e32/e33 in the snapshot are user-supplied and require a traceable source.",
            "The dielectric convention is intentionally varied because the snapshot mixes conventions.",
            "Analytic scaling assumes linear elasticity and small deformation; it is not a COMSOL solve.",
        ],
        "csv": str(csv_path),
    }
    json_path = args.output_dir / "phase2_analytic_sensitivity.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
