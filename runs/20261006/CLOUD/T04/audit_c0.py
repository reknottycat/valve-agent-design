#!/usr/bin/env python3
"""Replay the pinned C0 CAD in an isolated output directory and reject unsafe gates.

Exit 0: numerical prerequisites met but human review still required.
Exit 2: HOLD; no product solver may be launched from this result.
Exit 1: audit execution/input-integrity failure, also blocks downstream work.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import cadquery as cq
import yaml

from geometry_gate import check_exchange, check_geometry, measure, product_decision, step_length_unit


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def checked_source(root, path, snapshot):
    expected = next(x["git_blob_sha1"] for x in snapshot["files"] if x["path"] == path)
    file = root / path
    if blob_sha(file.read_bytes()) != expected:
        raise ValueError(f"Source changed: {path}; this audit is pinned to {snapshot['commit']}")
    return file


def run_audit(root, output, snapshot):
    c0 = "runs/20261006/C0/"
    cad_source = checked_source(root, c0 + "T12/build_valve_model.py", snapshot)
    cfd_source = checked_source(root, c0 + "T23/cfd_pipeline.py", snapshot)
    contract_source = checked_source(root, c0 + "T06/design_contract.yaml", snapshot)
    replay = output / "source-replay" / "T12"
    replay.mkdir(parents=True, exist_ok=True)
    copied = replay / cad_source.name
    shutil.copyfile(cad_source, copied)
    result = subprocess.run([sys.executable, str(copied)], capture_output=True, text=True, timeout=240)
    (output / "c0-cad-replay.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"C0 CAD replay exited {result.returncode}; see c0-cad-replay.log")
    old = json.loads((replay / "out/geometry_check.json").read_text())
    part_results = {}
    for name in ("body", "seat_ring", "disc", "stem", "bonnet", "lever"):
        original = cq.Shape.importBrep(str(replay / "out/parts" / (name + ".brep")))
        imported = cq.importers.importStep(str(replay / "out/parts" / (name + ".step"))).val()
        part_results[name] = {"measurement_mm": measure(imported),
                              "single_component_screen": check_geometry(measure(imported)),
                              "step_exchange": check_exchange(measure(original), measure(imported))}
    t12_shape = cq.importers.importStep(str(replay / "out/cfd/fluid_domain.step")).val()
    # Contract here is the C0 generator's own documented 3D+L+3D geometry, not an approved valve dimension.
    intended_span_mm = 6 * old["params"]["DN"] + old["params"]["face_to_face"]
    t12 = {"measurement_mm": measure(t12_shape), "documented_span_mm": intended_span_mm,
           "step_unit": step_length_unit(replay / "out/cfd/fluid_domain.step"),
           "gate": check_geometry(measure(t12_shape), expected_span=intended_span_mm)}
    spec = importlib.util.spec_from_file_location("c0_cfd_replay", cfd_source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # Only portable runtime output location changes; source and all geometric parameters remain untouched.
    module.CASE = str(output / "source-replay" / "T23")
    Path(module.CASE).mkdir(parents=True, exist_ok=True)
    path, _, _ = module.build_geometry()
    t23_shape = cq.importers.importStep(path).val()
    intended_span_m = module.GEO["UP"] + module.GEO["L"] + module.GEO["DNC"]
    t23 = {"measurement_mm": measure(t23_shape), "documented_span_m": intended_span_m,
           "step_unit": step_length_unit(path), "source_numeric_convention": "m",
           "gate": check_geometry(measure(t23_shape), expected_span=1000 * intended_span_m)}
    if t23["step_unit"]["unit"] != "m":
        t23["gate"]["status"] = "FAIL"
        t23["gate"]["failures"].append("STEP_METADATA_DISAGREES_WITH_SOURCE_METRE_CONVENTION")
    contract_error = None
    try:
        contract = yaml.safe_load(contract_source.read_text())
        frozen = contract["t07_freeze_decision"]["can_freeze"]
    except (yaml.YAMLError, KeyError, TypeError) as exc:
        frozen = None
        contract_error = f"{type(exc).__name__}: {exc}"
    decision = product_decision([t12["gate"], t23["gate"]] +
                               [v["single_component_screen"] for v in part_results.values()] +
                               [v["step_exchange"] for v in part_results.values()],
                               basis_frozen=frozen,
                               interfaces_frozen=False)
    if contract_error:
        decision["reasons"].append("DESIGN_CONTRACT_PARSE_FAILED")
    # A local radial ray measures a real ligament; it is not a global minimum-wall or code-compliance check.
    body = cq.importers.importStep(str(replay / "out/parts/body.step")).val()
    ray = cq.Edge.makeLine((old["params"]["face_to_face"] / 2, 0, 0),
                           (old["params"]["face_to_face"] / 2, old["params"]["flange_od"], 0))
    ligaments = [{"length_mm": edge.Length(), "start": edge.startPoint().toTuple(),
                  "end": edge.endPoint().toTuple()} for edge in body.intersect(ray).Edges()]
    return {"schema": "valve.cloud-c0-audit/1.0", "upstream_commit": snapshot["commit"],
            "scope": "Unmodified C0 source replay and numerical diagnostics only; no C1 edits",
            "cadquery_version": cq.__version__, "parts": part_results,
            "fluid_t12": t12, "fluid_t23": t23, "decision": decision,
            "design_contract_parse_error": contract_error,
            "radial_ligament_diagnostic": {"at": "x=L/2, z=0, positive-y ray", "segments": ligaments,
                "c0_reported_actual_min_mm": old["checks"]["wall_thickness"]["actual_min"],
                "note": "Local measured wall segment only; no structural adequacy judgement"},
            "lever_span_diagnostic_mm": {"declared": old["params"]["lever_span"],
                "observed_y_span": part_results["lever"]["measurement_mm"]["y_span"],
                "note": "Comparison against generator's own parameter only; not a frozen design requirement"},
            "source_hashes": {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (cad_source, cfd_source, contract_source)},
            "interface_note": "No frozen I1 artifact found in pinned snapshot; never inferred from build success",
            "original_claims_are_not_gates": {"envelope": old["checks"]["envelope"],
                "interference_verdict": old["checks"]["interference"]["verdict"]},
            "limitations": ["A multi-solid part requires an explicit intended topology; screening is not a redesign decision",
                "No pressure, material, wall-strength, sealing or motion acceptance inferred",
                "Full motion, semantic boundaries, minimum wall and assembly routes remain unverified",
                "No product CFD, FEA, leak performance or physical validation run"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "evidence")
    args = parser.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads((Path(__file__).resolve().parent / "source_snapshot.json").read_text())
    try:
        report = run_audit(args.repo.resolve(), output, snapshot)
    except Exception as exc:
        report = {"schema": "valve.cloud-c0-audit/1.0", "decision": {"decision": "HOLD",
            "product_solver_authorized": False}, "error": f"{type(exc).__name__}: {exc}"}
        (output / "c0_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report, ensure_ascii=False)); return 1
    report["output_hashes"] = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (output / "source-replay").rglob("*") if p.is_file()}
    (output / "c0_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))
    return 2 if report["decision"]["decision"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
