#!/usr/bin/env python3
"""Assemble shared-scale strain and piezopotential maps into six panels."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
OUTPUT = FIGURES / "BiOX_strain_potential_common_scales.png"
MATERIALS = ("BiOCl", "BiOBr", "BiOI")
PANEL_SIZE = (1200, 750)
GUTTER_X = 18
GUTTER_Y = 22


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / filename), size)
    except OSError:
        return ImageFont.load_default()


def prepare_panel(source: Path, panel_label: str, material: str) -> Image.Image:
    panel = Image.open(source).convert("RGB")
    if panel.size != (2000, 1250):
        raise ValueError(f"Unexpected source size for {source}: {panel.size}")
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 760, 112), fill="white")
    draw.text((46, 38), f"({panel_label}) {material}", fill="#111111",
              font=font(48, bold=True), anchor="lm")
    return panel.resize(PANEL_SIZE, Image.Resampling.LANCZOS)


def main() -> int:
    labels = iter("abcdef")
    strain = [
        prepare_panel(FIGURES / f"{material}_strain_ezz_common.png",
                      next(labels), material)
        for material in MATERIALS
    ]
    potential = [
        prepare_panel(FIGURES / f"{material}_potential_common_-177_177uV_large_labels.png",
                      next(labels), material)
        for material in MATERIALS
    ]
    rows = (strain, potential)

    width = PANEL_SIZE[0] * 3 + GUTTER_X * 2
    height = PANEL_SIZE[1] * 2 + GUTTER_Y
    canvas = Image.new("RGB", (width, height), "white")
    for row_index, row in enumerate(rows):
        for column_index, panel in enumerate(row):
            x = column_index * (PANEL_SIZE[0] + GUTTER_X)
            y = row_index * (PANEL_SIZE[1] + GUTTER_Y)
            canvas.paste(panel, (x, y))

    canvas.save(OUTPUT, dpi=(300, 300), optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
