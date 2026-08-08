#!/usr/bin/env python3
"""Merge phase-2 COMSOL outputs and make publication-audit plots."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    phase2 = Path(__file__).resolve().parent.parent
    analysis = phase2 / "analysis"
    config = json.loads((phase2 / "inputs" /
                         "biox_materials_phase2_snapshot.json").read_text(encoding="utf-8"))
    surface_rows = read_csv(analysis / "phase2_surface_metrics.csv")
    surface = {(row["epsilon_mode"], float(row["pressure_mpa"]), row["material"]): row
               for row in surface_rows}
    merged: list[dict[str, Any]] = []
    for epsilon_mode, run_name in (
        ("vasp-electronic", "epsilon_vasp-electronic_p100_t5"),
        ("vasp-total", "epsilon_vasp-total_p100_t5"),
    ):
        for row in read_csv(phase2 / "runs" / run_name / "BiOX_COMSOL_results.csv"):
            key = (epsilon_mode, 100.0, row["material"])
            sm = surface[key]
            e31, e32, e33 = [float(value) for value in
                              config["materials"][row["material"]]
                              ["e31_e32_e33_c_per_m2"]]
            exx = float(sm["top_avg_exx"])
            eyy = float(sm["top_avg_eyy"])
            ezz = float(sm["top_avg_ezz"])
            pz_x = e31 * exx
            pz_y = e32 * eyy
            pz_z = e33 * ezz
            merged.append({
                "material": row["material"],
                "epsilon_mode": epsilon_mode,
                "delta_v_mv": float(row["delta_v_mv"]),
                "top_avg_abs_ez_kv_per_m": float(sm["top_avg_abs_ez_v_per_m"]) / 1e3,
                "max_abs_ez_kv_per_m": float(sm["max_abs_ez_v_per_m"]) / 1e3,
                "top_avg_abs_pz_uC_per_m2": float(sm["top_avg_abs_pz_c_per_m2"]) * 1e6,
                "top_avg_pz_uC_per_m2": float(sm["top_avg_pz_c_per_m2"]) * 1e6,
                "pz_x_uC_per_m2": pz_x * 1e6,
                "pz_y_uC_per_m2": pz_y * 1e6,
                "pz_z_uC_per_m2": pz_z * 1e6,
                "max_mises_mpa": float(row["max_mises_pa"]) / 1e6,
                "top_avg_ezz_percent": ezz * 100.0,
                "model_file": row["model_file"],
            })

    csv_path = analysis / "phase2_mechanism_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(merged[0]))
        writer.writeheader()
        writer.writerows(merged)

    summary: dict[str, Any] = {
        "status": "comsol_merged",
        "rows": len(merged),
        "interpretation": [
            "BiOBr remains first in deltaV and top-surface |Ez| for both dielectric conventions.",
            "Top-surface |Pz| is independent of dielectric convention because it is set by e and strain.",
            "Absolute electric field is dielectric-screening sensitive; report the convention explicitly.",
            "Static local piezopotential is a mechanism descriptor, not a direct photocatalytic rate or open-circuit voltage.",
        ],
        "data_quality_flags": [
            "The e tensor source and coordinate convention remain to be confirmed.",
            "The snapshot uses a mixed prompt dielectric convention; the two uniform modes are the defensible sensitivity bounds.",
            "A four-point total-dielectric pressure sweep is complete; experimental load validation and a geometry/thickness study remain pending.",
        ],
        "csv": str(csv_path),
    }
    json_path = analysis / "phase2_mechanism_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        import matplotlib.pyplot as plt
        import numpy as np

        materials = ["BiOCl", "BiOBr", "BiOI"]
        colors = {"BiOCl": "#2f6f9f", "BiOBr": "#d9772b", "BiOI": "#4d8b57"}
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
        x = np.arange(len(materials))
        width = 0.36
        for offset, mode in zip((-width / 2, width / 2),
                                ("vasp-electronic", "vasp-total")):
            subset = {r["material"]: r for r in merged if r["epsilon_mode"] == mode}
            axes[0, 0].bar(x + offset,
                           [subset[m]["delta_v_mv"] for m in materials], width,
                           label=mode.replace("vasp-", ""))
            axes[0, 1].bar(x + offset,
                           [subset[m]["top_avg_abs_ez_kv_per_m"] for m in materials], width,
                           label=mode.replace("vasp-", ""))
        axes[0, 0].set_ylabel("DeltaV (mV)")
        axes[0, 0].set_title("Local piezopotential span")
        axes[0, 1].set_ylabel("Top-surface |Ez| (kV m$^{-1}$)")
        axes[0, 1].set_title("Surface-relevant electric field")
        for ax in axes[0]:
            ax.set_xticks(x, materials)
            ax.legend(frameon=False, fontsize=8)
            ax.grid(axis="y", alpha=0.25)

        subset = {r["material"]: r for r in merged if r["epsilon_mode"] == "vasp-electronic"}
        axes[1, 0].bar(x, [subset[m]["top_avg_abs_pz_uC_per_m2"] for m in materials],
                       color=[colors[m] for m in materials])
        axes[1, 0].set_xticks(x, materials)
        axes[1, 0].set_ylabel("Top-surface |Pz| (microC m$^{-2}$)")
        axes[1, 0].set_title("Piezoelectric polarization (electronic mode)")
        axes[1, 0].grid(axis="y", alpha=0.25)

        normalized = []
        for mode in ("vasp-electronic", "vasp-total"):
            mode_rows = {r["material"]: r for r in merged if r["epsilon_mode"] == mode}
            for metric in ("delta_v_mv", "top_avg_abs_ez_kv_per_m", "top_avg_abs_pz_uC_per_m2"):
                baseline = mode_rows["BiOCl"][metric]
                normalized.append((mode, metric,
                                   [mode_rows[m][metric] / baseline for m in materials]))
        labels = ["DeltaV", "|Ez|", "|Pz|"]
        for i, label in enumerate(labels):
            vals_e = normalized[i][2]
            vals_t = normalized[i + 3][2]
            axes[1, 1].plot(x, vals_e, marker="o", label=f"{label} electronic")
            axes[1, 1].plot(x, vals_t, marker="s", linestyle="--", label=f"{label} total")
        axes[1, 1].axhline(1.0, color="#777777", linewidth=0.8)
        axes[1, 1].set_xticks(x, materials)
        axes[1, 1].set_ylabel("Normalized to BiOCl")
        axes[1, 1].set_title("Robustness of the BiOBr ranking")
        axes[1, 1].legend(frameon=False, fontsize=7, ncol=2)
        axes[1, 1].grid(axis="y", alpha=0.25)

        fig.suptitle("BiOX phase-2 COMSOL mechanism audit (100 MPa, 5 nm)")
        fig_path = analysis / "phase2_mechanism_summary.png"
        fig.savefig(fig_path, dpi=200)
        plt.close(fig)
        summary["figure"] = str(fig_path)
        json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as error:
        fallback_figure = analysis / "phase2_mechanism_summary.png"
        if fallback_figure.is_file():
            summary["figure"] = str(fallback_figure)
            summary["figure_backend"] = "Pillow fallback"
        else:
            summary["figure_error"] = str(error)
        json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
