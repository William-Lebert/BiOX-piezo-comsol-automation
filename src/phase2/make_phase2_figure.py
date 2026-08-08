#!/usr/bin/env python3
"""Render a dependency-light PNG summary of the phase-2 COMSOL results."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def get_font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def draw_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
              title: str, ylabel: str, ymax: float, ticks: int = 4):
    x0, y0, x1, y1 = box
    title_font = get_font(30, True)
    label_font = get_font(23)
    tick_font = get_font(20)
    draw.text((x0, y0 - 48), title, fill="#20242a", font=title_font)
    draw.line((x0, y0, x0, y1), fill="#30343a", width=2)
    draw.line((x0, y1, x1, y1), fill="#30343a", width=2)
    for index in range(ticks + 1):
        value = ymax * index / ticks
        y = y1 - (y1 - y0) * index / ticks
        draw.line((x0, y, x1, y), fill="#d8dce1", width=1)
        text = f"{value:.3g}"
        width = draw.textbbox((0, 0), text, font=tick_font)[2]
        draw.text((x0 - width - 12, y - 10), text, fill="#4b5159", font=tick_font)
    if ylabel:
        draw.text((x0 - 112, y0 + (y1 - y0) / 2 - 14), ylabel,
                  fill="#30343a", font=label_font)


def grouped_bars(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                 rows: list[dict[str, float]], metric: str, title: str,
                 ylabel: str):
    materials = ["BiOCl", "BiOBr", "BiOI"]
    modes = ["vasp-electronic", "vasp-total"]
    colors = {"vasp-electronic": "#3f78b5", "vasp-total": "#9aa3ad"}
    lookup = {(row["material"], row["epsilon_mode"]): row for row in rows}
    values = [lookup[(m, mode)][metric] for m in materials for mode in modes]
    ymax = max(values) * 1.2
    draw_axes(draw, box, title, ylabel, ymax)
    x0, y0, x1, y1 = box
    group_width = (x1 - x0) / len(materials)
    bar_width = group_width * 0.25
    tick_font = get_font(22)
    value_font = get_font(18)
    for i, material in enumerate(materials):
        center = x0 + group_width * (i + 0.5)
        for j, mode in enumerate(modes):
            value = lookup[(material, mode)][metric]
            bx0 = center + (j - 0.5) * bar_width - bar_width / 2
            bx1 = bx0 + bar_width
            by0 = y1 - (y1 - y0) * value / ymax
            draw.rectangle((bx0, by0, bx1, y1), fill=colors[mode])
            label = f"{value:.3g}"
            width = draw.textbbox((0, 0), label, font=value_font)[2]
            draw.text(((bx0 + bx1 - width) / 2, by0 - 24), label,
                      fill="#30343a", font=value_font)
        label_width = draw.textbbox((0, 0), material, font=tick_font)[2]
        draw.text((center - label_width / 2, y1 + 10), material,
                  fill="#30343a", font=tick_font)
    legend_font = get_font(19)
    for i, mode in enumerate(modes):
        lx = x1 - 280 + i * 145
        draw.rectangle((lx, y0 + 12, lx + 22, y0 + 34), fill=colors[mode])
        draw.text((lx + 30, y0 + 8), mode.replace("vasp-", ""),
                  fill="#30343a", font=legend_font)


def material_bars(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                  rows: list[dict[str, float]]):
    materials = ["BiOCl", "BiOBr", "BiOI"]
    colors = {"BiOCl": "#2f6f9f", "BiOBr": "#d9772b", "BiOI": "#4d8b57"}
    lookup = {row["material"]: row for row in rows if row["epsilon_mode"] == "vasp-total"}
    values = [lookup[m]["top_avg_abs_pz_uC_per_m2"] for m in materials]
    ymax = max(values) * 1.2
    draw_axes(draw, box, "C  Top-surface |Pz| (microC m^-2)", "", ymax)
    x0, y0, x1, y1 = box
    group_width = (x1 - x0) / len(materials)
    tick_font = get_font(22)
    value_font = get_font(19)
    for i, material in enumerate(materials):
        value = lookup[material]["top_avg_abs_pz_uC_per_m2"]
        center = x0 + group_width * (i + 0.5)
        width = group_width * 0.35
        by0 = y1 - (y1 - y0) * value / ymax
        draw.rectangle((center - width / 2, by0, center + width / 2, y1),
                       fill=colors[material])
        label = f"{value:.3f}"
        label_width = draw.textbbox((0, 0), label, font=value_font)[2]
        draw.text((center - label_width / 2, by0 - 26), label,
                  fill="#30343a", font=value_font)
        label_width = draw.textbbox((0, 0), material, font=tick_font)[2]
        draw.text((center - label_width / 2, y1 + 10), material,
                  fill="#30343a", font=tick_font)


def pressure_lines(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
                   rows: list[dict[str, float]]):
    materials = ["BiOCl", "BiOBr", "BiOI"]
    colors = {"BiOCl": "#2f6f9f", "BiOBr": "#d9772b", "BiOI": "#4d8b57"}
    ymax = max(row["delta_v_mv"] for row in rows) * 1.18
    draw_axes(draw, box, "D  Pressure response: DeltaV (mV)", "", ymax)
    x0, y0, x1, y1 = box
    pressures = [25.0, 50.0, 100.0, 200.0]
    tick_font = get_font(20)
    for pressure in pressures:
        x = x0 + (x1 - x0) * (pressure - pressures[0]) / (pressures[-1] - pressures[0])
        draw.line((x, y1, x, y1 + 7), fill="#30343a", width=2)
        label = str(int(pressure))
        width = draw.textbbox((0, 0), label, font=tick_font)[2]
        draw.text((x - width / 2, y1 + 11), label, fill="#30343a", font=tick_font)
    for material in materials:
        subset = sorted((row for row in rows if row["material"] == material),
                        key=lambda row: row["pressure_mpa"])
        points = []
        for row in subset:
            x = x0 + (x1 - x0) * (row["pressure_mpa"] - pressures[0]) / (
                pressures[-1] - pressures[0])
            y = y1 - (y1 - y0) * row["delta_v_mv"] / ymax
            points.append((x, y))
        draw.line(points, fill=colors[material], width=5)
        for x, y in points:
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colors[material])
    legend_font = get_font(20)
    for i, material in enumerate(materials):
        lx = x0 + 20 + i * 155
        draw.line((lx, y0 + 20, lx + 35, y0 + 20), fill=colors[material], width=5)
        draw.text((lx + 45, y0 + 8), material, fill="#30343a", font=legend_font)
    draw.text((x0 + (x1 - x0) / 2 - 75, y1 + 45), "Pressure (MPa)",
              fill="#30343a", font=get_font(23))


def main() -> int:
    analysis = Path(__file__).resolve().parent
    mechanism_raw = read_csv(analysis / "phase2_mechanism_summary.csv")
    mechanism = [{key: (float(value) if key not in ("material", "epsilon_mode", "model_file") else value)
                  for key, value in row.items()} for row in mechanism_raw]
    pressure_raw = read_csv(analysis / "phase2_pressure_sweep.csv")
    pressure = [{key: (float(value) if key not in ("material", "epsilon_mode", "model_file") else value)
                 for key, value in row.items()} for row in pressure_raw]

    image = Image.new("RGB", (1800, 1250), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 40), "BiOX phase-2 COMSOL mechanism audit",
              fill="#1f252b", font=get_font(44, True))
    draw.text((80, 96), "Static linear model; 100 MPa and 5 nm unless noted",
              fill="#58616b", font=get_font(25))
    boxes = [
        (170, 215, 820, 550),
        (1040, 215, 1690, 550),
        (170, 790, 820, 1125),
        (1040, 790, 1690, 1125),
    ]
    grouped_bars(draw, boxes[0], mechanism, "delta_v_mv",
                 "A  Local piezopotential span (mV)", "")
    grouped_bars(draw, boxes[1], mechanism, "top_avg_abs_ez_kv_per_m",
                 "B  Top-surface |Ez| (kV m^-1)", "")
    material_bars(draw, boxes[2], mechanism)
    pressure_lines(draw, boxes[3], pressure)
    draw.text((80, 1205),
              "Uniform electronic and total dielectric conventions are shown separately; no mixed-dielectric result is used.",
              fill="#58616b", font=get_font(22))
    output = analysis / "phase2_mechanism_summary.png"
    image.save(output, dpi=(200, 200))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
