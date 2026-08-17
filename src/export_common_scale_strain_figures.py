#!/usr/bin/env python3
"""Export BiOX out-of-plane strain maps with one data-derived color scale."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont


MATERIALS = ("BiOCl", "BiOBr", "BiOI")


def load_base(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("biox_strain_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_if_supported(node: Any, key: str, value: Any) -> None:
    try:
        node.set(key, value)
    except Exception:
        pass


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / filename), size)
    except OSError:
        return ImageFont.load_default()


def nice_step(raw_step: float) -> float:
    exponent = math.floor(math.log10(raw_step))
    magnitude = 10.0 ** exponent
    fraction = raw_step / magnitude
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if fraction <= candidate:
            return candidate * magnitude
    raise AssertionError("Unreachable step selection")


def common_bounds(values: Sequence[tuple[float, float]]) -> tuple[float, float, float]:
    raw_low = min(0.0, *(low * 100.0 for low, _ in values))
    raw_high = max(0.0, *(high * 100.0 for _, high in values))
    span = raw_high - raw_low
    if span <= 0.0:
        raise ValueError(f"Degenerate strain range: {raw_low}, {raw_high}")
    step = nice_step(span / 5.0)
    low = math.floor(raw_low / step) * step
    high = math.ceil(raw_high / step) * step
    return low, high, step


def format_value(value: float) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.4f}".rstrip("0").rstrip(".")


def ticks_between(low: float, high: float, step: float) -> list[float]:
    count = int(round((high - low) / step))
    return [low + index * step for index in range(1, count)]


def annotate_colorbar(output: Path, low: float, high: float, step: float) -> None:
    image = Image.open(output).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((1740, 0, 1999, 104), fill="white")
    draw.rectangle((1888, 105, 1999, 1176), fill="white")
    draw.rectangle((1740, 1177, 1999, 1249), fill="white")

    endpoint_font = font(42, bold=True)
    tick_font = font(34)
    draw.text((1868, 61), f"{format_value(high)}%", fill="#111111",
              font=endpoint_font, anchor="mm")
    draw.text((1868, 1207), f"{format_value(low)}%", fill="#111111",
              font=endpoint_font, anchor="mm")
    for value in ticks_between(low, high, step):
        y = 106 + (high - value) * (1176 - 106) / (high - low)
        draw.text((1905, y), format_value(value), fill="#111111",
                  font=tick_font, anchor="lm")
    image.save(output, dpi=(200, 200), optimize=True)


def export_strain(base: Any, jmodel: Any, material: str, figure_dir: Path,
                  low: float, high: float, step: float) -> Path:
    results = jmodel.result()
    plot_tag = "pub_strain_ezz"
    export_tag = "pub_img_strain_ezz"
    base.remove_if_present(results, plot_tag)
    results.create(plot_tag, "PlotGroup3D")
    group = jmodel.result(plot_tag)
    group.label(f"{material} out-of-plane normal strain")
    set_if_supported(group, "titletype", "none")
    set_if_supported(group, "showlegendsmaxmin", "off")
    group.create("surf1", "Surface")
    surface = group.feature("surf1")
    surface.set("expr", "100*solid.eZZ")
    surface.set("unit", "1")
    surface.set("colortable", "Rainbow")
    surface.set("resolution", "fine")
    surface.set("rangecoloractive", "on")
    surface.set("rangecolormin", low)
    surface.set("rangecolormax", high)
    group.run()

    exports = results.export()
    base.remove_if_present(exports, export_tag)
    exports.create(export_tag, plot_tag, "Image")
    export = results.export(export_tag)
    output = figure_dir / f"{material}_strain_ezz_common.png"
    export.set("target", "file")
    export.set("imagetype", "png")
    export.set("pngfilename", str(output))
    export.set("size", "manualweb")
    export.set("width", base.make_java_int(2000))
    export.set("height", base.make_java_int(1250))
    export.set("resolution", base.make_java_int(200))
    export.set("options3d", "on")
    export.set("grid", "off")
    export.set("logo3d", "off")
    export.run()
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"COMSOL did not create {output}")
    annotate_colorbar(output, low, high, step)
    return output


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=root / "comsol_run")
    parser.add_argument("--comsol-root", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    base = load_base(root / "src" / "biox_comsol_automation.py")
    base.prepare_comsol_environment(args.comsol_root)
    figure_dir = root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    import mph

    mph.option("session", "stand-alone")
    client = mph.start(cores=args.cores, version="6.3")
    models: dict[str, Any] = {}
    extrema: dict[str, tuple[float, float]] = {}
    outputs: list[Path] = []
    try:
        for material in MATERIALS:
            model_path = args.model_dir / f"{material}_piezo_final.mph"
            if not model_path.is_file():
                raise FileNotFoundError(model_path)
            model = client.load(str(model_path))
            models[material] = model
            jmodel = model.java
            extrema[material] = (
                base.evaluate_scalar(jmodel, f"pub_{material}_emin", "Minimum eZZ",
                                     "biox_min(solid.eZZ)"),
                base.evaluate_scalar(jmodel, f"pub_{material}_emax", "Maximum eZZ",
                                     "biox_max(solid.eZZ)"),
            )

        low, high, step = common_bounds(list(extrema.values()))
        for material in MATERIALS:
            outputs.append(export_strain(base, models[material].java, material,
                                         figure_dir, low, high, step))
    finally:
        try:
            client.clear()
        except Exception:
            pass

    manifest = {
        "status": "comsol_exported",
        "quantity": "out-of-plane normal strain, solid.eZZ",
        "display_unit": "%",
        "source_models": "user-supplied calculation directory/*_piezo_final.mph",
        "raw_extrema": {
            material: {"minimum": values[0], "maximum": values[1]}
            for material, values in extrema.items()
        },
        "common_scale_percent": [low, high],
        "tick_step_percent": step,
        "outputs": [str(path.relative_to(root)).replace("\\", "/") for path in outputs],
    }
    manifest_path = root / "data" / "common_scale_strain_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
