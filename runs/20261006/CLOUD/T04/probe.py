#!/usr/bin/env python3
"""T04: real, independent open-source CAD and mesh capability tests.

No benchmark result is transferred from the original Windows/WSL machine.
No solver is called here and no product dimensions are inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from geometry_gate import check_exchange, measure


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(str(message))


def cadquery_probe(out):
    import cadquery as cq
    results = []
    for radius in (10.0, 12.0):
        shape = cq.Workplane("YZ").circle(radius).extrude(30).val()
        path = out / f"smoke_r{radius:g}_mm.step"
        shape.exportStep(str(path))
        imported = cq.importers.importStep(str(path)).val()
        exchange = check_exchange(measure(shape), measure(imported))
        expected = math.pi * radius**2 * 30
        require(exchange["status"] == "PASS", exchange)
        require(math.isclose(shape.Volume(), expected, rel_tol=1e-12), "Cylinder volume differs from analytic value")
        results.append({"radius_mm": radius, "analytic_volume_mm3": expected,
                        "native": measure(shape), "reimported": measure(imported),
                        "exchange": exchange, "artifact": path.name})
    require(results[0]["native"]["volume"] != results[1]["native"]["volume"], "Parameter update did not change geometry")
    return {"status": "VERIFIED", "version": cq.__version__,
            "scope": "parametric rebuild and STEP reimport, independent cylinder, mm",
            "tests": results}


def gmsh_probe(out):
    import gmsh
    import meshio
    import numpy as np
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("independent_pipe_smoke")
        entities = gmsh.model.occ.importShapes(str(out / "smoke_r10_mm.step"))
        gmsh.model.occ.dilate(entities, 0, 0, 0, .001, .001, .001)
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        require(len(volumes) == 1, f"Unexpected mesh volumes: {volumes}")
        groups = {"inlet": [], "outlet": [], "wall": []}
        for dim, tag in gmsh.model.getBoundary(volumes, oriented=False):
            x0, _, _, x1, _, _ = gmsh.model.getBoundingBox(dim, tag)
            if abs(x0) < 1e-6 and abs(x1) < 1e-6:
                groups["inlet"].append(tag)
            elif abs(x0 - .03) < 1e-6 and abs(x1 - .03) < 1e-6:
                groups["outlet"].append(tag)
            else:
                groups["wall"].append(tag)
        for tag, (name, members) in enumerate(groups.items(), 1):
            require(bool(members), f"Missing physical surface {name}: {groups}")
            gmsh.model.addPhysicalGroup(2, members, tag)
            gmsh.model.setPhysicalName(2, tag, name)
        gmsh.model.addPhysicalGroup(3, [v[1] for v in volumes], 4)
        gmsh.model.setPhysicalName(3, 4, "fluid")
        gmsh.option.setNumber("Mesh.MeshSizeMin", .002)
        gmsh.option.setNumber("Mesh.MeshSizeMax", .004)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(out / "smoke_pipe.msh"))
    finally:
        gmsh.finalize()
    mesh = meshio.read(out / "smoke_pipe.msh")
    tet = mesh.get_cells_type("tetra")
    require(len(tet) > 0, "No tetrahedra returned")
    p = mesh.points[tet]
    det = np.linalg.det(np.stack((p[:, 1] - p[:, 0], p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]), axis=1))
    require(bool(np.all(det > 0)), "Non-positive tetrahedron Jacobian")
    require(set(mesh.field_data) == {"inlet", "outlet", "wall", "fluid"}, "Physical group names changed")
    actual_volume = float(np.sum(det) / 6)
    analytic_volume = math.pi * .01**2 * .03
    error = abs(actual_volume - analytic_volume) / analytic_volume
    require(error < .02, f"Mesh volume error exceeds tolerance: {error}")
    tri_tags = mesh.get_cell_data("gmsh:physical", "triangle")
    require(set(tri_tags) == {1, 2, 3}, "Missing inlet, outlet or wall triangles")
    require(set(mesh.get_cell_data("gmsh:physical", "tetra")) == {4}, "Fluid volume tag changed")
    return {"status": "VERIFIED", "version": gmsh.__version__, "meshio_version": meshio.__version__,
            "scope": "independent STEP pipe in SI metres, MSH4.1 mesh and physical tags re-read",
            "nodes": len(mesh.points), "tetrahedra": len(tet), "min_determinant_m3": float(min(det)),
            "mesh_volume_m3": actual_volume, "analytic_volume_m3": analytic_volume,
            "relative_volume_error": error, "discretization_tolerance": .02,
            "physical_groups": {k: v.tolist() for k, v in mesh.field_data.items()},
            "surface_triangle_counts": {name: int(np.count_nonzero(tri_tags == tag))
                                        for tag, name in enumerate(("inlet", "outlet", "wall"), 1)}}


def freecad_probe(out):
    python = os.environ.get("FREECAD_PYTHON", "/usr/bin/python3")
    lib = os.environ.get("FREECAD_LIB", "/usr/lib/freecad-python3/lib")
    script = out / "freecad_smoke.py"
    script.write_text('''import sys, json, math
from pathlib import Path
sys.path.append(sys.argv[2])
import FreeCAD as App, Part
out = Path(sys.argv[1])
doc = App.newDocument("T04Smoke")
box = doc.addObject("Part::Box", "EditableBox")
box.Length=10; box.Width=20; box.Height=30; doc.recompute()
original = box.Shape.Volume
box.Length=12; doc.recompute()
if not (math.isclose(original,6000) and math.isclose(box.Shape.Volume,7200)):
    raise RuntimeError("FreeCAD parameter rebuild failed")
doc.saveAs(str(out/"smoke_editable.FCStd"))
box.Shape.exportStep(str(out/"freecad_smoke.step"))
App.closeDocument(doc.Name)
doc=App.openDocument(str(out/"smoke_editable.FCStd"))
shape=Part.Shape();shape.read(str(out/"freecad_smoke.step"))
if not (shape.isValid() and len(shape.Solids)==1 and math.isclose(shape.Volume,7200,rel_tol=1e-8)):
    raise RuntimeError("FreeCAD STEP exchange failed")
if doc.EditableBox.Length.Value!=12:
    raise RuntimeError("FreeCAD FCStd parameter persistence failed")
(out/"freecad_result.json").write_text(json.dumps({"status":"VERIFIED","version":App.Version(),
 "scope":"editable parametric box rebuild, FCStd reopen and STEP roundtrip; independent smoke only",
 "before_mm3":original,"after_mm3":shape.Volume,"solid_count":len(shape.Solids)},indent=2))
App.closeDocument(doc.Name)
''')
    result = subprocess.run([python, str(script), str(out), lib], capture_output=True, text=True, timeout=120)
    (out / "freecad_smoke.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"FreeCAD subprocess exited {result.returncode}; see freecad_smoke.log")
    return json.loads((out / "freecad_result.json").read_text())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    report = {"schema": "valve.cloud-capability/1.0", "evidence_ceiling": "E1",
              "product_assessment": "NOT_ASSESSED", "python": sys.version,
              "platform": platform.platform(), "cpu_count": os.cpu_count(), "capabilities": {}}
    for name, action in (("cadquery", cadquery_probe), ("gmsh", gmsh_probe), ("freecad", freecad_probe)):
        start = time.monotonic()
        try:
            result = action(out)
        except Exception as exc:
            result = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        result["runtime_s"] = round(time.monotonic() - start, 3)
        report["capabilities"][name] = result
    for name, executables in (("openfoam", ("simpleFoam", "blockMesh", "checkMesh")),
                              ("calculix", ("ccx",))):
        paths = {exe: shutil.which(exe) for exe in executables}
        report["capabilities"][name] = {"status": "UNTESTED" if all(paths.values()) else "UNAVAILABLE",
            "executables": paths, "scope": "PATH probe only; no solver benchmark run in this cloud workspace"}
    report["capabilities"]["assembly_constraints_motion_and_drawing"] = {
        "status": "UNTESTED", "scope": "No complete kinematic or dimensioned drawing adapter tested"}
    report["output_hashes"] = {p.name: sha256(p) for p in out.iterdir()
                                if p.is_file() and p.name not in ("capability_matrix.json", "probe.log")
                                and (p.name.startswith("smoke_") or p.name.startswith("freecad_"))}
    (out / "capability_matrix.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["status"] for k, v in report["capabilities"].items()}, indent=2))
    return 1 if any(v["status"] == "FAILED" for v in report["capabilities"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
