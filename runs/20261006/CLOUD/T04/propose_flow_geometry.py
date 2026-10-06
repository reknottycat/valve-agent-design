#!/usr/bin/env python3
"""Diagnostic Boolean repair, NOT a candidate valve design or CFD-ready domain.

Uses unchanged C0/T23 parameters. Removes only the subtraction of a full cross-
sectional cylinder, which cuts the inlet off from the outlet. Other unverified
geometry (including the original rotation axis and missing wetted assembly
derivation) is intentionally retained, so no solver may use this artifact.
"""
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

import cadquery as cq

from geometry_gate import check_geometry, measure, step_length_unit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args(); here = Path(__file__).resolve().parent
    source = args.repo / "runs/20261006/C0/T23/cfd_pipeline.py"
    original = source.read_text()
    removal = '''    dom = dom.cut(cq.Workplane("YZ", origin=(g["L"]/2 - 0.013, 0, 0))
                  .circle(g["seat_od"]).extrude(g["seat_h"]))
'''
    if original.count(removal) != 1:
        raise ValueError("Expected C0 Boolean expression changed; proposal requires review")
    proposed = original.replace(removal, "    # Diagnostic proposal: do not subtract a solid full-bore cylinder.\n", 1)
    out = here / "proposals"; out.mkdir(exist_ok=True)
    staged = out / "cfd_boolean_only.py"
    tree = ast.parse(proposed)
    selected = [node for node in tree.body if
                (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GEO" for t in node.targets))
                or (isinstance(node, ast.FunctionDef) and node.name == "build_geometry")]
    if len(selected) != 2:
        raise ValueError("Expected one GEO assignment and one geometry function")
    geometry_only = ('"""DIAGNOSTIC ONLY: no solver code; not a validated valve geometry."""\n'
                     'import os\nCASE = None\n' +
                     ast.unparse(ast.Module(body=selected, type_ignores=[])) +
                     '\n\nif __name__ == "__main__":\n'
                     '    raise SystemExit("Geometry-only diagnostic module. Use propose_flow_geometry.py; product solvers are disabled.")\n')
    staged.write_text(geometry_only)
    spec = importlib.util.spec_from_file_location("diagnostic_cfd_proposal", staged)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    artifact_dir = out / "diagnostic_geometry"; artifact_dir.mkdir(exist_ok=True)
    module.CASE = str(artifact_dir)
    path, _, _ = module.build_geometry()
    imported = cq.importers.importStep(path).val()
    legacy_path = artifact_dir / "legacy_numeric_mm.step"
    Path(path).replace(legacy_path)
    legacy_unit = step_length_unit(legacy_path)
    if legacy_unit["unit"] != "mm":
        raise ValueError("Legacy STEP units changed; refuse implicit rescaling")
    corrected_path = artifact_dir / "diagnostic_geometry_mm.step"
    # Source constants are metre-convention numbers, but default CadQuery STEP encodes millimetres.
    imported.scale(1000).exportStep(str(corrected_path))
    reimported = cq.importers.importStep(str(corrected_path)).val()
    measurement = measure(reimported)
    gate = check_geometry(measurement, expected_span=1000*(module.GEO["UP"]+module.GEO["L"]+module.GEO["DNC"]))
    report = {"schema": "valve.diagnostic-proposal/1.0", "status": "DIAGNOSTIC_ONLY",
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "parameters_source_metre_convention": module.GEO, "measurement_mm": measurement,
              "numeric_gate": gate, "step_unit": step_length_unit(corrected_path),
              "conversion": {"coordinate_scale": 1000, "legacy_step_unit": legacy_unit,
                             "reason": "Correct source metre-convention numbers to explicit STEP millimetres"},
              "product_solver_authorized": False, "engineering_approval": False,
              "unchanged_problems": ["Fluid domain not derived from validated assembly",
                "Original rotation axis retained, not a demonstrated valve hinge",
                "No motion, seal, wall, material, pressure or flow acceptance established"],
              "purpose": "Prove cause of disconnected flow path, not a replacement design"}
    (out / "diagnostic_geometry.json").write_text(json.dumps(report, indent=2))
    (out / "cfd_boolean_only.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(True), proposed.splitlines(True),
        fromfile="a/runs/20261006/C0/T23/cfd_pipeline.py",
        tofile="b/runs/20261006/C0/T23/cfd_pipeline.py")))
    print(json.dumps({"status": "DIAGNOSTIC_ONLY", "solid_count": measurement["solid_count"],
                      "numeric_gate": gate, "product_solver_authorized": False}, indent=2))
    return 0 if gate["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
