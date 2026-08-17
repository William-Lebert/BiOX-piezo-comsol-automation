#!/usr/bin/env python3
"""Plot the 100 MPa dielectric-convention sensitivity analysis."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "dielectric_convention_100MPa.csv"
OUTPUT = ROOT / "figures" / "dielectric_convention_100MPa.png"
MATERIALS = ("BiOCl", "BiOBr", "BiOI")
MODES = ("electronic", "total")
COLORS = {"electronic": "#2B6F9C", "total": "#9A9A9A"}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], value: str,
                  text_font: ImageFont.ImageFont, fill: str = "#202020") -> None:
    box = draw.textbbox((0, 0), value, font=text_font)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1]), value,
              font=text_font, fill=fill)


def load_data() -> dict[tuple[str, str], float]:
    with SOURCE.open(newline="", encoding="utf-8") as stream:
        rows = csv.DictReader(stream)
        return {
            (row["material"], row["dielectric_mode"]): float(row["delta_v_uV"])
            for row in rows
        }


def main() -> None:
    values = load_data()
    width, height = 1600, 1000
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    axis_font = font(42)
    tick_font = font(36)
    value_font = font(31)
    legend_font = font(34)

    left, right, top, bottom = 175, 1510, 90, 825
    y_max = 400.0

    def y(value: float) -> float:
        return bottom - value / y_max * (bottom - top)

    for tick in range(0, 401, 100):
        y_tick = y(float(tick))
        draw.line((left, y_tick, right, y_tick), fill="#D8D8D8", width=2)
        label = str(tick)
        box = draw.textbbox((0, 0), label, font=tick_font)
        draw.text((left - 24 - (box[2] - box[0]), y_tick - (box[3] - box[1]) / 2),
                  label, font=tick_font, fill="#202020")

    draw.line((left, top, left, bottom), fill="#202020", width=4)
    draw.line((left, bottom, right, bottom), fill="#202020", width=4)

    group_centers = [400, 830, 1260]
    bar_width, gap = 130, 24
    for material, center in zip(MATERIALS, group_centers):
        positions = {
            "electronic": center - gap / 2 - bar_width,
            "total": center + gap / 2,
        }
        for mode in MODES:
            value = values[(material, mode)]
            x0 = positions[mode]
            x1 = x0 + bar_width
            y0 = y(value)
            draw.rectangle((x0, y0, x1, bottom), fill=COLORS[mode], outline="#202020", width=2)
            centered_text(draw, ((x0 + x1) / 2, y0 - 48), f"{value:.1f}", value_font)
        centered_text(draw, (center, bottom + 24), material, tick_font)

    axis_label = "Potential difference (\u03bcV)"
    label_layer = Image.new("RGBA", (700, 80), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label_layer)
    label_draw.text((0, 0), axis_label, font=axis_font, fill="#202020")
    label_layer = label_layer.rotate(90, expand=True)
    image.paste(label_layer, (38, 235), label_layer)

    legend_y = 915
    legend_items = (("electronic", "Electronic dielectric tensor"),
                    ("total", "Total dielectric tensor"))
    legend_x = 375
    for mode, label in legend_items:
        draw.rectangle((legend_x, legend_y, legend_x + 48, legend_y + 32),
                       fill=COLORS[mode], outline="#202020", width=2)
        draw.text((legend_x + 66, legend_y - 7), label, font=legend_font, fill="#202020")
        legend_x += 475

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, dpi=(300, 300), optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
