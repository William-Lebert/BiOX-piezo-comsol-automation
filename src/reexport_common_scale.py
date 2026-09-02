"""Re-export solved COMSOL 6.3 plots with common physical colour limits.

This utility only loads solved MPH files and creates PNG exports; it does not
re-solve or modify the saved MPH files. The fixed ranges make material-to-
material colour comparisons auditable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import mph
import jpype


MATERIALS = ("BiOCl", "BiOBr", "BiOI")


def _remove(collection, tag: str) -> None:
    try:
        if bool(collection.hasTag(tag)):
            collection.remove(tag)
    except Exception:
        try:
            collection.remove(tag)
        except Exception:
            pass


def _export_one(model, material: str, source_tag: str, suffix: str, output_dir: Path,
                vmin: float, vmax: float, unit: str, title: str, colortable: str) -> Path:
    jmodel = model.java
    results = jmodel.result()
    pg_tag = f"v13_common_{suffix}"
    _remove(results, pg_tag)
    results.create(pg_tag, "PlotGroup3D")
    pg = jmodel.result(pg_tag)
    # Keep a unique label because the solved MPH already contains the native
    # result node with the same material/quantity label.
    pg.label(f"{material} - {title} (common scale)")
    pg.create("surf1", "Surface")
    surf = pg.feature("surf1")
    surf.set("expr", source_tag)
    surf.set("unit", unit)
    surf.set("colortable", colortable)
    surf.set("rangecoloractive", "on")
    surf.set("rangecolormin", str(vmin))
    surf.set("rangecolormax", str(vmax))
    surf.set("rangeunit", unit)
    surf.set("colorlegend", "on")
    try:
        surf.set("showlegendtitle", "on")
        surf.set("legendtitle", title)
        surf.set("legendunit", unit)
    except Exception:
        pass
    pg.run()
    exports = results.export()
    export_tag = f"v13_export_{suffix}"
    _remove(exports, export_tag)
    exports.create(export_tag, pg_tag, "Image")
    export = results.export(export_tag)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{material}_direct-pressure_{suffix}_common.png"
    export.set("target", "file")
    export.set("imagetype", "png")
    export.set("pngfilename", str(path))
    export.set("size", "manualweb")
    export.set("width", jpype.JInt(1600))
    export.set("height", jpype.JInt(1000))
    export.set("resolution", jpype.JInt(300))
    export.set("options3d", "on")
    export.set("grid", "off")
    export.set("logo3d", "off")
    export.run()
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"COMSOL did not create {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stress-max-mpa", type=float, default=150.0)
    parser.add_argument("--potential-max-mv", type=float, default=10.0)
    parser.add_argument("--comsol-version", default="6.3")
    parser.add_argument("--cores", type=int, default=4)
    args = parser.parse_args()
    client = mph.start(cores=args.cores, version=args.comsol_version)
    made: list[Path] = []
    try:
        for material in MATERIALS:
            mph_path = args.models_dir / f"{material}_piezo_direct-pressure_final.mph"
            model = client.load(str(mph_path))
            made.append(_export_one(model, material, "solid.mises", "stress", args.output_dir,
                                    0.0, args.stress_max_mpa, "MPa", "von Mises stress", "Thermal"))
            # The direct-pressure map is the induced potential and is naturally
            # centred around zero because the bottom face is grounded. Export it
            # directly in mV so the colour bar does not hide the scale behind a
            # 10^-3 multiplier.
            made.append(_export_one(model, material, "1000*V", "potential", args.output_dir,
                                    -args.potential_max_mv, args.potential_max_mv,
                                    "mV", "Piezoelectric potential", "Rainbow"))
    finally:
        try:
            client.clear()
        except Exception:
            pass
    for path in made:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
