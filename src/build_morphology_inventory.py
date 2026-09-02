#!/usr/bin/env python3
"""Create a compact, auditable inventory from the supplied SEM/TEM ZIP.

The script records instrument scale metadata but deliberately does not infer
particle dimensions from contrast.  Major/minor dimensions are left for
manual or validated segmentation and are therefore not silently fabricated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


MATERIAL_MARKERS = {
    "bioxcl": "BiOCl",
    "biocl": "BiOCl",
    "cl-sem": "BiOCl",
    "biobr": "BiOBr",
    "br-sem": "BiOBr",
    "bioi": "BiOI",
    "i-sem": "BiOI",
}


def material_from_name(name: str) -> str | None:
    lowered = name.lower()
    for marker, material in MATERIAL_MARKERS.items():
        if marker in lowered:
            return material
    return None


def decode_metadata(data: bytes) -> str:
    for encoding in ("utf-16", "utf-16-le", "utf-8", "gb18030"):
        try:
            text = data.decode(encoding)
            if "SemImageFile" in text or "DataSize=" in text:
                return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def fields(text: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            output[key.strip()] = value.strip()
    return output


def number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group(0)) if match else None


def material_rows(zippath: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(zippath) as archive:
        # Keep the full metadata suffix in the lookup key.  Using a stem-only
        # key silently misses ``image.tif`` -> ``image.txt`` companions.
        by_name = {Path(info.filename).as_posix(): info for info in archive.infolist()}
        for info in archive.infolist():
            name = info.filename
            lower = name.lower()
            if not lower.endswith((".tif", ".tiff", ".dm3", ".ibw")):
                continue
            material = material_from_name(name)
            if material is None:
                continue
            # ZIP members may start with ``SEM/`` or ``TEM/``; checking only
            # for the slash-prefixed form would discard the entire archive.
            parts = [part for part in lower.split("/") if part]
            kind = "SEM" if "sem" in parts else "TEM" if "tem" in parts else "other"
            if kind == "other":
                continue
            metadata: dict[str, str] = {}
            if lower.endswith(".tif"):
                txt_info = by_name.get(Path(name).with_suffix(".txt").as_posix())
                if txt_info is not None:
                    metadata = fields(decode_metadata(archive.read(txt_info)))
            digest = hashlib.sha256(archive.read(info)).hexdigest()
            fov_um = number(metadata.get("FOV"))
            pixel_size = number(metadata.get("PixelSize"))
            rows.append({
                "material": material,
                "image_type": kind,
                "archive_path": name,
                "sha256": digest,
                "data_size": metadata.get("DataSize", ""),
                "pixel_size_nm_per_pixel": pixel_size if kind == "SEM" else "",
                "fov_um": fov_um if kind == "SEM" else "",
                "magnification": metadata.get("Magnification", "") if kind == "SEM" else "",
                "accelerating_voltage": metadata.get("AcceleratingVoltage", "") if kind == "SEM" else "",
                "condition": metadata.get("Condition", "") if kind == "SEM" else "",
                "scale_bar_um": "",
                "measured_major_um": "",
                "measured_minor_um": "",
                "measured_thickness_nm": "",
                "measurement_status": (
                    "pending_manual_annotation" if kind == "SEM" else "scale_bar_manual"
                ),
            })
    return sorted(rows, key=lambda row: (str(row["material"]), str(row["image_type"]), str(row["archive_path"])))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory SEM/TEM metadata for BiOX v1.3.0.")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/morphology"))
    args = parser.parse_args()
    if not args.archive.is_file():
        raise FileNotFoundError(args.archive)
    rows = material_rows(args.archive)
    if not rows:
        raise RuntimeError("No BiOX SEM/TEM images found in the archive.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0])
    csv_path = args.output_dir / "image_inventory.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, dict[str, object]] = defaultdict(lambda: {"SEM": 0, "TEM": 0, "sem_fov_um": []})
    for row in rows:
        material = str(row["material"])
        image_type = str(row["image_type"])
        summary[material][image_type] = int(summary[material][image_type]) + 1
        fov = row["fov_um"]
        if isinstance(fov, (float, int)):
            summary[material]["sem_fov_um"].append(fov)
    for material, data in summary.items():
        values = data["sem_fov_um"]
        data["sem_fov_range_um"] = [min(values), max(values)] if values else None
        del data["sem_fov_um"]
    json_path = args.output_dir / "image_inventory_summary.json"
    json_path.write_text(json.dumps({
        "archive": str(args.archive),
        "n_images": len(rows),
        "materials": summary,
        "measurement_policy": "scale metadata are recorded; particle dimensions remain manual/validated inputs",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"csv": str(csv_path), "json": str(json_path), "n_images": len(rows), "materials": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
