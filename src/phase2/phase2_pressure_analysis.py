#!/usr/bin/env python3
"""Merge the total-dielectric pressure sweep and calculate linear regressions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def regression(x: list[float], y: list[float]) -> dict[str, float]:
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    ss_xx = sum((value - x_mean) ** 2 for value in x)
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / ss_xx
    intercept = y_mean - slope * x_mean
    predicted = [slope * value + intercept for value in x]
    ss_res = sum((actual - fitted) ** 2 for actual, fitted in zip(y, predicted))
    ss_tot = sum((actual - y_mean) ** 2 for actual in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    origin_slope = sum(xi * yi for xi, yi in zip(x, y)) / sum(xi * xi for xi in x)
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r2,
        "origin_slope": origin_slope,
    }


def main() -> int:
    phase2 = Path(__file__).resolve().parent.parent
    analysis = phase2 / "analysis"
    run_dirs = {
        25.0: "sweep_vasp-total_p25_t5",
        50.0: "sweep_vasp-total_p50_t5",
        100.0: "epsilon_vasp-total_p100_t5",
        200.0: "sweep_vasp-total_p200_t5",
    }
    surface_rows = read_csv(analysis / "phase2_surface_metrics.csv")
    surface = {
        (float(row["pressure_mpa"]), row["material"]): row
        for row in surface_rows if row["epsilon_mode"] == "vasp-total"
    }
    rows: list[dict[str, Any]] = []
    for pressure_mpa, directory in run_dirs.items():
        results = read_csv(phase2 / "runs" / directory / "BiOX_COMSOL_results.csv")
        for result in results:
            sm = surface[(pressure_mpa, result["material"])]
            rows.append({
                "material": result["material"],
                "epsilon_mode": "vasp-total",
                "pressure_mpa": pressure_mpa,
                "delta_v_mv": float(result["delta_v_mv"]),
                "top_avg_abs_ez_kv_per_m": float(sm["top_avg_abs_ez_v_per_m"]) / 1e3,
                "top_avg_abs_pz_uC_per_m2": float(sm["top_avg_abs_pz_c_per_m2"]) * 1e6,
                "max_mises_mpa": float(result["max_mises_pa"]) / 1e6,
                "top_average_w_pm": float(result["top_average_w_m"]) * 1e12,
                "model_file": result["model_file"],
            })
    rows.sort(key=lambda row: (row["material"], row["pressure_mpa"]))
    data_path = analysis / "phase2_pressure_sweep.csv"
    with data_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metrics = [
        ("delta_v_mv", "mV/MPa"),
        ("top_avg_abs_ez_kv_per_m", "kV m^-1/MPa"),
        ("top_avg_abs_pz_uC_per_m2", "microC m^-2/MPa"),
        ("max_mises_mpa", "MPa/MPa"),
    ]
    regressions: list[dict[str, Any]] = []
    for material in ("BiOCl", "BiOBr", "BiOI"):
        subset = [row for row in rows if row["material"] == material]
        x = [float(row["pressure_mpa"]) for row in subset]
        for metric, slope_unit in metrics:
            fit = regression(x, [float(row[metric]) for row in subset])
            regressions.append({
                "material": material,
                "metric": metric,
                "slope_unit": slope_unit,
                **fit,
            })
    regression_path = analysis / "phase2_pressure_regression.csv"
    with regression_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(regressions[0]))
        writer.writeheader()
        writer.writerows(regressions)

    summary = {
        "status": "comsol_pressure_sweep_complete",
        "epsilon_mode": "vasp-total",
        "pressures_mpa": sorted(run_dirs),
        "data_csv": str(data_path),
        "regression_csv": str(regression_path),
        "regressions": regressions,
        "acceptance_note": (
            "Linearity is a property of the present small-deformation, linear constitutive model; "
            "it does not validate 200 MPa as an experimental load."
        ),
    }
    json_path = analysis / "phase2_pressure_analysis.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "data_csv": str(data_path),
                      "regression_csv": str(regression_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
