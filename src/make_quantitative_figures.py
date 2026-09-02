#!/usr/bin/env python3
"""Create title-free quantitative BiOX figures from actual COMSOL results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MATERIALS = ["BiOCl", "BiOBr", "BiOI"]
COLORS = {"BiOCl": "#2f6f9f", "BiOBr": "#d9772b", "BiOI": "#4d8b57"}


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default()


def read_results(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return {row["material"]: float(row["delta_v_v"]) * 1e6
                for row in csv.DictReader(stream)}


def draw_y_axis(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                ymax: float, step: float) -> None:
    x0, y0, x1, y1 = box
    draw.line((x0, y0, x0, y1), fill="#30343a", width=3)
    draw.line((x0, y1, x1, y1), fill="#30343a", width=3)
    tick_font = font(26)
    value = 0.0
    while value <= ymax + 1e-9:
        y = y1 - (y1 - y0) * value / ymax
        draw.line((x0, y, x1, y), fill="#d7dce1", width=1)
        label = f"{value:.0f}"
        width = draw.textbbox((0, 0), label, font=tick_font)[2]
        draw.text((x0 - width - 16, y - 14), label, fill="#434a52",
                  font=tick_font)
        value += step


def make_bar_figure(values: dict[str, float], output: Path) -> None:
    image = Image.new("RGB", (1400, 1000), "white")
    draw = ImageDraw.Draw(image)
    box = (155, 90, 1325, 845)
    ymax = 400.0
    draw_y_axis(draw, box, ymax, 100.0)
    x0, y0, x1, y1 = box
    group = (x1 - x0) / len(MATERIALS)
    tick_font = font(31)
    value_font = font(27)
    ratio_font = font(29, True)
    base_value = values["BiOCl"]
    ratios = {material: values[material] / base_value for material in MATERIALS}
    for index, material in enumerate(MATERIALS):
        center = x0 + group * (index + 0.5)
        bar_width = group * 0.43
        value = values[material]
        top = y1 - (y1 - y0) * value / ymax
        draw.rectangle((center - bar_width / 2, top, center + bar_width / 2, y1),
                       fill=COLORS[material])
        value_label = f"{value:.1f} μV"
        ratio_label = f"{ratios[material]:.2f}×"
        width = draw.textbbox((0, 0), value_label, font=value_font)[2]
        draw.text((center - width / 2, top - 70), value_label,
                  fill="#30343a", font=value_font)
        width = draw.textbbox((0, 0), ratio_label, font=ratio_font)[2]
        draw.text((center - width / 2, top - 37), ratio_label,
                  fill=COLORS[material], font=ratio_font)
        width = draw.textbbox((0, 0), material, font=tick_font)[2]
        draw.text((center - width / 2, y1 + 18), material,
                  fill="#30343a", font=tick_font)
    draw.text((18, 28), "ΔV (μV)", fill="#30343a", font=font(34))
    image.save(output, dpi=(200, 200))


def make_pressure_figure(rows: list[dict[str, float]], output: Path) -> None:
    image = Image.new("RGB", (1500, 1000), "white")
    draw = ImageDraw.Draw(image)
    box = (165, 90, 1420, 825)
    ymax = 400.0
    draw_y_axis(draw, box, ymax, 100.0)
    x0, y0, x1, y1 = box
    pressures = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
    tick_font = font(27)
    for pressure in pressures:
        x = x0 + (x1 - x0) * pressure / 100.0
        draw.line((x, y1, x, y1 + 8), fill="#30343a", width=3)
        label = f"{pressure:.0f}"
        width = draw.textbbox((0, 0), label, font=tick_font)[2]
        draw.text((x - width / 2, y1 + 17), label, fill="#30343a",
                  font=tick_font)
    lookup = {(row["material"], row["pressure_mpa"]): row["delta_v_uV"]
              for row in rows}
    for material in MATERIALS:
        points = []
        for pressure in pressures:
            value = lookup[(material, pressure)]
            x = x0 + (x1 - x0) * pressure / 100.0
            y = y1 - (y1 - y0) * value / ymax
            points.append((x, y))
        draw.line(points, fill=COLORS[material], width=6)
        for x, y in points:
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=COLORS[material])
    legend_font = font(23)
    for index, material in enumerate(MATERIALS):
        material_rows = [row for row in rows if row["material"] == material]
        slope, _, _ = linear_regression(
            [float(row["pressure_mpa"]) for row in material_rows],
            [float(row["delta_v_uV"]) for row in material_rows],
        )
        lx = x0 + 25 + index * 400
        draw.line((lx, y0 + 28, lx + 48, y0 + 28),
                  fill=COLORS[material], width=6)
        legend = f"{material}  {slope:.3f} μV/MPa"
        draw.text((lx + 62, y0 + 12), legend, fill="#30343a",
                  font=legend_font)
    draw.text((22, 28), "ΔV (μV)", fill="#30343a", font=font(34))
    xlabel = "Pressure (MPa)"
    width = draw.textbbox((0, 0), xlabel, font=font(32))[2]
    draw.text(((x0 + x1 - width) / 2, y1 + 70), xlabel,
              fill="#30343a", font=font(32))
    image.save(output, dpi=(200, 200))


def linear_regression(x: list[float], y: list[float]) -> tuple[float, float, float]:
    xbar = sum(x) / len(x)
    ybar = sum(y) / len(y)
    slope = sum((a - xbar) * (b - ybar) for a, b in zip(x, y)) / sum(
        (a - xbar) ** 2 for a in x)
    intercept = ybar - slope * xbar
    predicted = [slope * value + intercept for value in x]
    ss_res = sum((actual - fitted) ** 2 for actual, fitted in zip(y, predicted))
    ss_tot = sum((actual - ybar) ** 2 for actual in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    return slope, intercept, r2


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    figure_dir = root / "figures"
    result_dir = root / "data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    source_100 = result_dir / "benchmark_100MPa.csv"
    values_100 = read_results(source_100)
    pressure_data = result_dir / "pressure_sweep_0_100MPa.csv"
    with pressure_data.open(newline="", encoding="utf-8-sig") as stream:
        rows = [
            {
                "material": row["material"],
                "pressure_mpa": float(row["pressure_mpa"]),
                "delta_v_uV": float(row["delta_v_uV"]),
                "source": row["source"],
            }
            for row in csv.DictReader(stream)
        ]
    rows.sort(key=lambda row: (str(row["material"]), float(row["pressure_mpa"])))

    fits = []
    for material in MATERIALS:
        subset = [row for row in rows if row["material"] == material]
        x = [float(row["pressure_mpa"]) for row in subset]
        y = [float(row["delta_v_uV"]) for row in subset]
        slope, intercept, r2 = linear_regression(x, y)
        fits.append({"material": material, "slope_uV_per_MPa": slope,
                     "intercept_uV": intercept, "r2": r2})
    fit_path = result_dir / "pressure_regression.csv"
    with fit_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fits[0]))
        writer.writeheader()
        writer.writerows(fits)

    bar_path = figure_dir / "BiOX_DeltaV_100MPa_zero_baseline.png"
    pressure_path = figure_dir / "BiOX_DeltaV_pressure_0_100MPa.png"
    make_bar_figure(values_100, bar_path)
    make_pressure_figure(rows, pressure_path)
    manifest = {
        "status": "created",
        "units": "microvolt",
        "bar_figure": "figures/BiOX_DeltaV_100MPa_zero_baseline.png",
        "pressure_figure": "figures/BiOX_DeltaV_pressure_0_100MPa.png",
        "data": "data/pressure_sweep_0_100MPa.csv",
        "regression": "data/pressure_regression.csv",
        "fits": fits,
    }
    manifest_path = result_dir / "quantitative_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
