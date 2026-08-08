#!/usr/bin/env python3
"""Extract surface-relevant electric and piezoelectric metrics from phase-2 MPH files."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_base(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("biox_surface_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    phase2 = Path(__file__).resolve().parent.parent
    base = load_base(phase2 / "inputs" / "biox_comsol_automation_phase2_base.py")
    config = json.loads((phase2 / "inputs" /
                         "biox_materials_phase2_snapshot.json").read_text(encoding="utf-8"))
    import mph

    runs = [
        ("vasp-electronic", 100.0,
         phase2 / "runs" / "epsilon_vasp-electronic_p100_t5"),
        ("vasp-total", 25.0,
         phase2 / "runs" / "sweep_vasp-total_p25_t5"),
        ("vasp-total", 50.0,
         phase2 / "runs" / "sweep_vasp-total_p50_t5"),
        ("vasp-total", 100.0,
         phase2 / "runs" / "epsilon_vasp-total_p100_t5"),
        ("vasp-total", 200.0,
         phase2 / "runs" / "sweep_vasp-total_p200_t5"),
    ]
    materials = ["BiOCl", "BiOBr", "BiOI"]
    mph.option("session", "stand-alone")
    client = mph.start(cores=2, version="6.3")
    rows: list[dict[str, Any]] = []
    try:
        for epsilon_mode, pressure_mpa, run_dir in runs:
            for material in materials:
                model_path = run_dir / f"{material}_piezo_final.mph"
                if not model_path.is_file():
                    raise FileNotFoundError(model_path)
                model = client.load(str(model_path))
                jmodel = model.java
                e31, e32, e33 = [float(value) for value in
                                  config["materials"][material]["e31_e32_e33_c_per_m2"]]
                pz = (f"({e31:.16g})*solid.eXX+({e32:.16g})*solid.eYY+"
                      f"({e33:.16g})*solid.eZZ")
                norm_e = "sqrt(es.Ex^2+es.Ey^2+es.Ez^2)"

                def value(tag: str, label: str, expression: str) -> float:
                    return base.evaluate_scalar(jmodel, tag, label, expression)

                rows.append({
                    "material": material,
                    "epsilon_mode": epsilon_mode,
                    "pressure_mpa": pressure_mpa,
                    "thickness_nm": 5.0,
                    "max_abs_ez_v_per_m": value("sm_ezmax", "Maximum absolute Ez",
                                                  "biox_max(abs(es.Ez))"),
                    "top_avg_ez_v_per_m": value("sm_ezavg", "Top average Ez",
                                                  "biox_topavg(es.Ez)"),
                    "top_avg_abs_ez_v_per_m": value("sm_ezabs", "Top average absolute Ez",
                                                      "biox_topavg(abs(es.Ez))"),
                    "max_norm_e_v_per_m": value("sm_enormmax", "Maximum electric field norm",
                                                  f"biox_max({norm_e})"),
                    "top_avg_norm_e_v_per_m": value("sm_enormavg", "Top average field norm",
                                                      f"biox_topavg({norm_e})"),
                    "top_avg_dz_c_per_m2": value("sm_dzavg", "Top average Dz",
                                                   "biox_topavg(es.Dz)"),
                    "top_avg_abs_dz_c_per_m2": value("sm_dzabs", "Top average absolute Dz",
                                                       "biox_topavg(abs(es.Dz))"),
                    "max_abs_pz_c_per_m2": value("sm_pzmax", "Maximum absolute piezo polarization",
                                                   f"biox_max(abs({pz}))"),
                    "top_avg_pz_c_per_m2": value("sm_pzavg", "Top average piezo polarization",
                                                   f"biox_topavg({pz})"),
                    "top_avg_abs_pz_c_per_m2": value("sm_pzabs", "Top average absolute piezo polarization",
                                                       f"biox_topavg(abs({pz}))"),
                    "top_avg_exx": value("sm_exx", "Top average strain XX",
                                           "biox_topavg(solid.eXX)"),
                    "top_avg_eyy": value("sm_eyy", "Top average strain YY",
                                           "biox_topavg(solid.eYY)"),
                    "top_avg_ezz": value("sm_ezz", "Top average strain ZZ",
                                           "biox_topavg(solid.eZZ)"),
                    "model_file": str(model_path),
                })
                client.clear()
    finally:
        try:
            client.clear()
        except Exception:
            pass

    csv_path = phase2 / "analysis" / "phase2_surface_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = phase2 / "analysis" / "phase2_surface_metrics.json"
    json_path.write_text(json.dumps({"status": "comsol_extracted", "results": rows},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "comsol_extracted", "rows": len(rows),
                      "csv": str(csv_path), "json": str(json_path)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
