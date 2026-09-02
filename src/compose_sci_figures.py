"""Compose publication-ready panels from COMSOL image exports.

The COMSOL 6.3 image exporter uses the application locale for plot titles and
does not expose a reliable colour-bar font setter through the Java API.  This
post-processing step removes the locale-dependent title strip, upscales the
native export (so colour-bar numbers remain legible in a multi-panel figure),
and adds English panel labels in Times New Roman.  Pixel values are not
rescaled and no material-dependent contrast enhancement is applied.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


MATERIALS = ("BiOCl", "BiOBr", "BiOI")
COLS = ("BiOCl", "BiOBr", "BiOI")


def _font_path(bold: bool = False) -> str | None:
    names = ("timesbd.ttf", "times.ttf") if bold else ("times.ttf", "timesbd.ttf")
    roots = (Path(r"C:\Windows\Fonts"), Path(r"C:\WINNT\Fonts"))
    for root in roots:
        for name in names:
            path = root / name
            if path.is_file():
                return str(path)
    return None


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _font_path(bold)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _load_clean(path: Path, title_height: int = 78, scale: float = 1.0) -> Image.Image:
    """Load a COMSOL PNG, remove its locale-dependent title and upscale."""
    with Image.open(path) as src:
        img = src.convert("RGB")
    # The current 1600x1000 COMSOL export reserves about 70 px for the title.
    # Keep a small white margin so the plot is not clipped on older exports.
    if img.height > title_height + 100:
        img = img.crop((0, title_height, img.width, img.height))
    if scale != 1.0:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    return img


def _find_colorbar(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Find the tall COMSOL colour-bar rectangle in the right-hand margin."""
    rgb = img.convert("RGB")
    pix = rgb.load()
    nonwhite = [[any(channel < 238 for channel in pix[x, y]) for x in range(img.width)]
                for y in range(img.height)]
    x0 = int(img.width * 0.72)
    x1 = int(img.width * 0.97)
    counts = [sum(1 for y in range(img.height) if nonwhite[y][x]) for x in range(x0, x1)]
    if not counts or max(counts) < int(img.height * 0.35):
        return None
    threshold = max(int(img.height * 0.35), int(max(counts) * 0.65))
    cols = [x0 + i for i, value in enumerate(counts) if int(value) >= threshold]
    if not cols:
        return None
    # Use the longest contiguous run; text columns are short, while the bar is tall.
    runs: list[list[int]] = [[cols[0]]]
    for value in cols[1:]:
        if value == runs[-1][-1] + 1:
            runs[-1].append(value)
        else:
            runs.append([value])
    run = max(runs, key=len)
    if len(run) < 8:
        return None
    ys = [y for y in range(img.height)
          if any(nonwhite[y][x] for x in range(run[0], run[-1] + 1))]
    if not ys:
        return None
    return run[0], run[-1], min(ys), max(ys)


def _redraw_colorbar_labels(img: Image.Image, limits: tuple[float, float], unit: str) -> None:
    """Replace native tick glyphs with large Times New Roman labels.

    Only the white margin to the right of the existing colour bar is repainted;
    the COMSOL colour ramp itself is untouched.
    """
    box = _find_colorbar(img)
    if box is None:
        return
    x0, x1, y0, y1 = box
    draw = ImageDraw.Draw(img)
    right = min(img.width - 1, x1 + max(95, round(img.width * 0.095)))
    draw.rectangle((x1 + 2, max(0, y0 - 40), right, min(img.height - 1, y1 + 40)), fill="white")
    lo, hi = limits
    ticks = [lo + (hi - lo) * i / 5 for i in range(6)]
    tick_font = _font(max(24, round(img.width * 0.018)), bold=False)
    unit_font = _font(max(22, round(img.width * 0.016)), bold=False)
    for value in ticks:
        y = y1 - (value - lo) / (hi - lo) * (y1 - y0)
        text_value = f"{value:g}"
        draw.text((x1 + 14, round(y)), text_value, fill=(20, 20, 20), font=tick_font, anchor="lm")
    draw.text((x1 + 14, max(2, y0 - 33)), unit, fill=(20, 20, 20), font=unit_font, anchor="lm")


def _annotate(img: Image.Image, label: str, material: str, quantity: str,
              colorbar_limits: tuple[float, float] | None = None,
              colorbar_unit: str = "", show_title: bool = True) -> Image.Image:
    label_font = _font(max(30, round(img.width * 0.022)), bold=True)
    name_font = _font(max(28, round(img.width * 0.018)), bold=True)
    # A white header can replace the locale-dependent COMSOL title. Manuscript
    # panels are title-free unless --show-titles is requested.
    header_h = max(64, round(img.height * 0.07)) if show_title else 0
    canvas = Image.new("RGB", (img.width, img.height + header_h), "white")
    canvas.paste(img, (0, header_h))
    d = ImageDraw.Draw(canvas)
    if show_title:
        d.text((24, 10), label, fill=(20, 20, 20), font=label_font)
        d.text((img.width // 2, 10), f"{material} | {quantity}", fill=(20, 20, 20), font=name_font, anchor="ma")
    if colorbar_limits is not None:
        _redraw_colorbar_labels(canvas, colorbar_limits, colorbar_unit)
    return canvas


def _save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", dpi=(300, 300), optimize=True)


def build_figures(results_dir: Path, output_dir: Path, title_height: int = 78,
                  mode: str = "pfm-converse", source_suffix: str = "",
                  show_titles: bool = False) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    individual = output_dir / "individual"
    made: list[Path] = []
    potential_label = "Piezoelectric potential (mV)" if mode == "direct-pressure" else "Electric potential (V)"
    specs = (("stress", "von Mises stress (MPa)"), ("potential", potential_label))
    common_limits = {"stress": (0.0, 150.0), "potential": (-10.0, 10.0)} if mode == "direct-pressure" else {}

    # Individual plates are intentionally larger than the native COMSOL export;
    # the colour-bar units/ticks therefore remain readable in manuscripts.
    for material in MATERIALS:
        for suffix, quantity in specs:
            source = results_dir / f"{material}_{mode}_{suffix}{source_suffix}.png"
            if not source.is_file():
                continue
            plate = _load_clean(source, title_height=title_height, scale=1.25)
            plate = _annotate(plate, "", material, quantity, common_limits.get(suffix),
                              "MPa" if suffix == "stress" else "mV", show_titles)
            target = individual / f"{material}_{mode}_{suffix}_TNR.png"
            _save(plate, target)
            made.append(target)

    # Six-panel layout: rows = stress / potential; columns = BiOCl / BiOBr / BiOI.
    cells: list[list[Image.Image]] = []
    for suffix, quantity in specs:
        row: list[Image.Image] = []
        for material in COLS:
            source = results_dir / f"{material}_{mode}_{suffix}{source_suffix}.png"
            if source.is_file():
                cell = _load_clean(source, title_height=title_height, scale=1.0)
                cell = _annotate(cell, "", material, quantity, common_limits.get(suffix),
                                 "MPa" if suffix == "stress" else "mV", show_titles)
            else:
                cell = Image.new("RGB", (1600, 1000), "white")
            row.append(cell)
        cells.append(row)
    if cells and all(cells) and all(len(row) == 3 for row in cells):
        w = max(cell.width for row in cells for cell in row)
        h = max(cell.height for row in cells for cell in row)
        gap_x, gap_y = 36, 46
        composite = Image.new("RGB", (3 * w + 2 * gap_x, 2 * h + gap_y), "white")
        labels = (("(a)", "(b)", "(c)"), ("(d)", "(e)", "(f)"))
        for i, row in enumerate(cells):
            for j, cell in enumerate(row):
                x = j * (w + gap_x)
                y = i * (h + gap_y)
                composite.paste(cell, (x, y))
                ImageDraw.Draw(composite).text((x + 24, y + 10), labels[i][j], fill=(15, 15, 15), font=_font(34, bold=True))
        target = output_dir / f"BiOX_{mode}_stress-potential_6panel_TNR.png"
        _save(composite, target)
        made.append(target)
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--title-height", type=int, default=78)
    parser.add_argument("--mode", default="pfm-converse", help="COMSOL filename mode, e.g. direct-pressure")
    parser.add_argument("--source-suffix", default="", help="Suffix before .png, e.g. _common")
    parser.add_argument("--show-titles", action="store_true", help="Retain English material/quantity headers")
    args = parser.parse_args()
    made = build_figures(args.results_dir.resolve(), args.output_dir.resolve(), args.title_height,
                         args.mode, args.source_suffix, args.show_titles)
    for path in made:
        print(path)
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
