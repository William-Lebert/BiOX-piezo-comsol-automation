#!/usr/bin/env python3
"""Export title-free COMSOL maps with shared publication color scales."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


POTENTIAL_LIMIT_UV = 177.0
STRESS_MAX_MPA = 175.0


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("biox_publication_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_if_supported(node, key: str, value) -> None:
    try:
        node.set(key, value)
    except Exception:
        pass


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / filename), size)
    except OSError:
        return ImageFont.load_default()


def y_for_value(value: float, low: float, high: float,
                top: int = 106, bottom: int = 1176) -> float:
    return top + (high - value) * (bottom - top) / (high - low)


def annotate_colorbar(output: Path, kind: str) -> None:
    image = Image.open(output).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Preserve the COMSOL colorbar and tick marks; replace only its text.
    draw.rectangle((1740, 0, 1999, 104), fill="white")
    draw.rectangle((1888, 105, 1999, 1176), fill="white")
    draw.rectangle((1740, 1177, 1999, 1249), fill="white")

    endpoint_font = font(42, bold=True)
    tick_font = font(34)
    if kind == "potential":
        low, high = -177.0, 177.0
        ticks = [150, 100, 50, 0, -50, -100, -150]
        draw.text((1868, 61), "+177 μV", fill="#111111",
                  font=endpoint_font, anchor="mm")
        draw.text((1868, 1207), "-177 μV", fill="#111111",
                  font=endpoint_font, anchor="mm")
    else:
        low, high = 0.0, 175.0
        ticks = [160, 140, 120, 100, 80, 60, 40, 20, 0]
        draw.text((1868, 61), "175 MPa", fill="#111111",
                  font=endpoint_font, anchor="mm")

    for value in ticks:
        draw.text((1905, y_for_value(value, low, high)), str(value),
                  fill="#111111", font=tick_font, anchor="lm")

    image.save(output, dpi=(200, 200), optimize=True)


def export_plot(base, jmodel, material: str, figure_dir: Path,
                kind: str) -> Path:
    results = jmodel.result()
    plot_tag = "pub_potential" if kind == "potential" else "pub_stress"
    export_tag = "pub_img_potential" if kind == "potential" else "pub_img_stress"
    base.remove_if_present(results, plot_tag)
    results.create(plot_tag, "PlotGroup3D")
    group = jmodel.result(plot_tag)
    group.label(f"{material} publication {kind}")
    set_if_supported(group, "titletype", "none")
    set_if_supported(group, "showlegendsmaxmin", "off")
    group.create("surf1", "Surface")
    surface = group.feature("surf1")
    surface.set("resolution", "fine")
    surface.set("rangecoloractive", "on")

    if kind == "potential":
        surface.set("expr", "V-(biox_max(V)+biox_min(V))/2")
        surface.set("unit", "uV")
        surface.set("colortable", "Rainbow")
        surface.set("colorscalemode", "linearsymmetric")
        surface.set("rangecolormin", -POTENTIAL_LIMIT_UV)
        surface.set("rangecolormax", POTENTIAL_LIMIT_UV)
        filename = f"{material}_potential_common_-177_177uV_large_labels.png"
    else:
        surface.set("expr", "solid.mises")
        surface.set("unit", "MPa")
        surface.set("colortable", "Thermal")
        surface.set("rangecolormin", 0.0)
        surface.set("rangecolormax", STRESS_MAX_MPA)
        filename = f"{material}_stress_common_0_175MPa_large_labels.png"
    group.run()

    exports = results.export()
    base.remove_if_present(exports, export_tag)
    exports.create(export_tag, plot_tag, "Image")
    export = results.export(export_tag)
    output = figure_dir / filename
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
    annotate_colorbar(output, kind)
    return output


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    base = load_base(root / "src" / "biox_comsol_automation.py")
    source_dir = root / "comsol_run"
    figure_dir = root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    import mph

    mph.option("session", "stand-alone")
    client = mph.start(cores=2, version="6.3")
    outputs: list[str] = []
    try:
        for material in ("BiOCl", "BiOBr", "BiOI"):
            model_path = source_dir / f"{material}_piezo_final.mph"
            model = client.load(str(model_path))
            jmodel = model.java
            outputs.append(str(export_plot(base, jmodel, material, figure_dir,
                                           "potential")))
            outputs.append(str(export_plot(base, jmodel, material, figure_dir,
                                           "stress")))
            client.clear()
    finally:
        try:
            client.clear()
        except Exception:
            pass

    manifest = {
        "status": "exported",
        "source": "comsol_run/*_piezo_final.mph",
        "potential_scale_uV": [-POTENTIAL_LIMIT_UV, POTENTIAL_LIMIT_UV],
        "stress_scale_MPa": [0.0, STRESS_MAX_MPA],
        "titles": "off",
        "outputs": [str(Path(path).relative_to(root)).replace("\\", "/")
                    for path in outputs],
    }
    manifest_path = root / "data" / "common_scale_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
