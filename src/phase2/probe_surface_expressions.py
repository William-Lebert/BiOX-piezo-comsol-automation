#!/usr/bin/env python3
"""Probe COMSOL variable names on one solved phase-2 model."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("biox_probe_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    phase2 = Path(__file__).resolve().parent.parent
    base = load_base(phase2 / "inputs" / "biox_comsol_automation_phase2_base.py")
    os.environ.setdefault("PYTHONPATH", str(phase2.parent / "Codex_BiOX" / ".python_deps"))
    import mph

    mph.option("session", "stand-alone")
    client = mph.start(cores=2, version="6.3")
    model_path = phase2 / "runs" / "epsilon_vasp-electronic_p100_t5" / "BiOBr_piezo_final.mph"
    model = client.load(str(model_path))
    jmodel = model.java
    candidates = [
        "d(V,x)", "d(V,y)", "d(V,z)",
        "es.Ex", "es.Ey", "es.Ez", "ccnp1.Ex", "ccnp1.Ey", "ccnp1.Ez",
        "solid.eXX", "solid.eYY", "solid.eZZ", "solid.eXY", "solid.eYZ", "solid.eXZ",
        "solid.exx", "solid.eyy", "solid.ezz",
        "pze1.Ex", "pze1.Ez", "pze1.Px", "pze1.Pz", "ccnp1.Dz", "es.Dz",
    ]
    rows = []
    for expression in candidates:
        row = {
            "expression": expression,
            "domain_max_abs": None,
            "top_avg_abs": None,
            "domain_error": None,
            "top_error": None,
        }
        try:
            row["domain_max_abs"] = base.evaluate_scalar(
                jmodel, "probe_global", expression + " domain max", f"biox_max(abs({expression}))")
        except Exception as error:
            row["domain_error"] = str(error)
        try:
            row["top_avg_abs"] = base.evaluate_scalar(
                jmodel, "probe_top", expression + " top abs", f"biox_topavg(abs({expression}))")
        except Exception as error:  # COMSOL rejects unknown variables; keep the probe complete.
            row["top_error"] = str(error)
        rows.append(row)
    out = phase2 / "analysis" / "surface_expression_probe.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        client.clear()
    except Exception:
        pass
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
