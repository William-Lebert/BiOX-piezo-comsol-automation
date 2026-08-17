#!/usr/bin/env python3
"""Build a publication-ready BiOX potential figure with independent color scales."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "raw_potential_maps"
OUTPUT = ROOT / "figures" / "BiOX_potential_independent_scales.png"

MATERIALS = {
    "BiOCl": {
        "limit": 26.78,
        "ticks": [20, 10, 0, -10, -20],
    },
    "BiOBr": {
        "limit": 176.79,
        "ticks": [150, 100, 50, 0, -50, -100, -150],
    },
    "BiOI": {
        "limit": 123.45,
        "ticks": [100, 50, 0, -50, -100],
    },
}

BAR_TOP = 132
BAR_BOTTOM = 918


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / filename), size)


def y_for_value(value: float, limit: float) -> float:
    return BAR_TOP + (limit - value) * (BAR_BOTTOM - BAR_TOP) / (2 * limit)


def format_limit(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def prepare_panel(material: str, panel_label: str) -> Image.Image:
    config = MATERIALS[material]
    limit = config["limit"]
    source = SOURCE / f"{material}_potential_centered.png"
    panel = Image.open(source).convert("RGB")
    if panel.size != (1600, 1000):
        raise ValueError(f"Unexpected source size for {source}: {panel.size}")

    draw = ImageDraw.Draw(panel)

    # Preserve the COMSOL field and colorbar; replace only title and numeric labels.
    draw.rectangle((0, 0, 1599, 108), fill="white")
    draw.rectangle((1420, 60, 1599, 128), fill="white")
    draw.rectangle((1490, 125, 1599, 925), fill="white")
    draw.rectangle((1420, 920, 1599, 999), fill="white")

    draw.text((42, 32), f"({panel_label}) {material}", fill="#111111",
              font=font(42, bold=True), anchor="lm")
    endpoint = format_limit(limit)
    draw.text((1472, 91), f"+{endpoint} μV", fill="#111111",
              font=font(32, bold=True), anchor="mm")
    draw.text((1472, 956), f"-{endpoint} μV", fill="#111111",
              font=font(32, bold=True), anchor="mm")

    for tick in config["ticks"]:
        draw.text((1505, y_for_value(tick, limit)), str(tick), fill="#111111",
                  font=font(27), anchor="lm")
    return panel


def main() -> int:
    panels = [
        prepare_panel("BiOCl", "a"),
        prepare_panel("BiOBr", "b"),
        prepare_panel("BiOI", "c"),
    ]
    target_width = 1200
    target_height = 750
    panels = [
        panel.resize((target_width, target_height), Image.Resampling.LANCZOS)
        for panel in panels
    ]
    gutter = 18
    canvas = Image.new(
        "RGB",
        (target_width * len(panels) + gutter * (len(panels) - 1), target_height),
        "white",
    )
    for index, panel in enumerate(panels):
        canvas.paste(panel, (index * (target_width + gutter), 0))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, dpi=(300, 300), optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
