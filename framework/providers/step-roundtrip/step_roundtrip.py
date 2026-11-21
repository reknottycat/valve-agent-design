#!/usr/bin/env python3
"""STEP representation roundtrip audit; NOT engineering or vendor CAD acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time

TOLERANCES = {"coordinate_abs_mm": 1e-5, "volume_abs_mm3": 1e-3, "volume_rel": 1e-8}
TOPOLOGY = ("faces", "shells", "edges", "vertices")

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def units(path):
    return sorted(set(re.findall(r"LENGTH_UNIT\(\)[^;]*?SI_UNIT\(([^)]*)\)", Path(path).read_text(errors="strict"), re.S)))

def measure(shape):
    b = shape.BoundingBox()
    c = shape.Center()
    return {"valid": shape.isValid(), "faces": len(shape.Faces()),
            "shells": len(shape.Shells()), "edges": len(shape.Edges()),
            "vertices": len(shape.Vertices()), "volume_mm3": shape.Volume(),
            "centroid_mm": [c.x, c.y, c.z],
            "bbox_mm": [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]}

def compatible(a, b):
    if not a["valid"] or not b["valid"] or any(a[k] != b[k] for k in TOPOLOGY):
        return False
    av, bv = a["volume_mm3"], b["volume_mm3"]
    if not all(math.isfinite(v) and v > 0 for v in (av, bv)):
        return False
    if abs(av-bv) > max(TOLERANCES["volume_abs_mm3"], TOLERANCES["volume_rel"]*abs(av)):
        return False
    for key, size in (("centroid_mm", 3), ("bbox_mm", 6)):
        if len(a[key]) != size or len(b[key]) != size:
            return False
        if any(not math.isfinite(x) or not math.isfinite(y) or abs(x-y) > TOLERANCES["coordinate_abs_mm"] for x, y in zip(a[key], b[key])):
            return False
    return True

def match_solids(before, after):
    """Find a bijection; index order and symmetric component identity are not assumed."""
    if not before or len(before) != len(after):
        return None
    choices = [[j for j,b in enumerate(after) if compatible(a,b)] for a in before]
    owners = {}
    def assign(i, visited):
        for j in choices[i]:
            if j in visited:
                continue
            visited.add(j)
            if j not in owners or assign(owners[j], visited):
                owners[j] = i
                return True
        return False
    if not all(assign(i,set()) for i in range(len(before))):
        return None
    return sorted(({"source_index": i, "roundtrip_index": j} for j,i in owners.items()), key=lambda x:x["source_index"])

def run(source, output_dir, expected_sha256, expected_solids, scope):
    source, output_dir = Path(source).resolve(), Path(output_dir).resolve()
    if sha256(source) != expected_sha256:
        raise ValueError("source SHA256 does not match the pinned input")
    input_units = units(source)
    if input_units != [".MILLI.,.METRE."]:
        raise ValueError("only an explicit, unambiguous millimetre STEP input is supported")
    if expected_solids < 1 or not scope.strip():
        raise ValueError("explicit scope and positive solid count required")
    import cadquery as cq
    import OCP
    from OCP.IFSelect import IFSelect_RetDone
    t = time.monotonic()
    original = cq.importers.importStep(str(source)).val()
    original_metrics = [measure(s) for s in original.Solids()]
    if not original.isValid() or len(original_metrics) != expected_solids:
        raise ValueError("input topology or expected solid count failed")
    output_dir.mkdir(parents=True, exist_ok=False)
    output = output_dir / "roundtrip.step"
    status = original.exportStep(str(output), write_pcurves=True, precision_mode=0)
    if status != IFSelect_RetDone:
        raise RuntimeError("STEP export did not return IFSelect_RetDone")
    rebuilt = cq.importers.importStep(str(output)).val()
    after_metrics = [measure(s) for s in rebuilt.Solids()]
    matches = match_solids(original_metrics, after_metrics)
    max_coordinate_delta = max_volume_delta = max_relative_volume_delta = None
    if matches:
        max_coordinate_delta = max(abs(x-y) for pair in matches for key in ("centroid_mm", "bbox_mm") for x,y in zip(original_metrics[pair["source_index"]][key], after_metrics[pair["roundtrip_index"]][key]))
        volume_deltas = [(abs(original_metrics[p["source_index"]]["volume_mm3"]-after_metrics[p["roundtrip_index"]]["volume_mm3"]), original_metrics[p["source_index"]]["volume_mm3"]) for p in matches]
        max_volume_delta = max(d for d,_ in volume_deltas)
        max_relative_volume_delta = max(d/v for d,v in volume_deltas)
    output_units = units(output)
    unchanged = sha256(source) == expected_sha256
    passed = unchanged and rebuilt.isValid() and matches is not None and output_units == input_units
    result = {
        "schema": "valve.step_roundtrip/v1", "scope": scope,
        "source": {"name": source.name, "sha256": expected_sha256, "bytes": source.stat().st_size, "length_units": input_units},
        "output": {"name": output.name, "sha256": sha256(output), "bytes": output.stat().st_size, "length_units": output_units},
        "cadquery_version": cq.__version__, "OCP_version": getattr(OCP,"__version__",None),
        "export_options": {"write_pcurves": True, "precision_mode": 0, "transfer": "STEPControl_AsIs"},
        "tolerances": TOLERANCES,
        "tolerance_basis": "Numerical serialization regression thresholds only: 1e-5 mm coordinate, max(1e-3 mm3, 1e-8 relative) volume. Not manufacturing tolerances or a standard-based acceptance criterion.",
        "source_shape_valid": original.isValid(), "output_shape_valid": rebuilt.isValid(),
        "source_solids": original_metrics, "output_solids": after_metrics, "bijective_matches": matches,
        "max_coordinate_delta_mm": max_coordinate_delta, "max_volume_delta_mm3": max_volume_delta,
        "max_relative_volume_delta": max_relative_volume_delta,
        "original_file_unchanged": unchanged, "numerical_roundtrip_passed": passed,
        "elapsed_seconds": time.monotonic()-t,
        "explicit_healing_or_boolean_requested": False, "meshing_or_solver_started": False,
        "engineering_release": False,
        "unverified": ["Exact pointwise geometric identity", "Names and assembly metadata", "Native parametric features", "BOM correspondence", "SOLIDWORKS import", "Manufacturing and fit", "P08 fluid domain and CFD"]
    }
    (output_dir/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    return result

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source"); p.add_argument("output_dir")
    p.add_argument("--expected-sha256",required=True);p.add_argument("--expected-solids",required=True,type=int)
    p.add_argument("--scope",required=True)
    a=p.parse_args()
    result=run(a.source,a.output_dir,a.expected_sha256,a.expected_solids,a.scope)
    print(json.dumps({k:result[k] for k in ("numerical_roundtrip_passed","max_coordinate_delta_mm","max_volume_delta_mm3","original_file_unchanged","engineering_release")},indent=2))
    raise SystemExit(0 if result["numerical_roundtrip_passed"] else 2)
