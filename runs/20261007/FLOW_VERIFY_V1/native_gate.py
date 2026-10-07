#!/usr/bin/env python3
"""Native v1912 geometry/MMS gate on an untouched copy of the real valve mesh.

Usage: python native_gate.py --case ABS_FLOW_CASE --output ABS_NEW_DIR
No solver result is synthesized when OpenFOAM is unavailable. Exit 0 requires
all native evidence. These diagnostic thresholds are not engineering criteria.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np


class GateError(RuntimeError):
    pass


LIMITS = {
    "geometry_C_and_Cf_atol_m": 1e-11,
    "geometry_C_and_Cf_rtol": 5e-10,
    "geometry_Sf_atol_m2": 2e-14,
    "geometry_Sf_rtol": 5e-10,
    "geometry_V_atol_m3": 1e-22,
    "geometry_V_rtol": 1e-9,
    "MMS_volume_weighted_relative_L2": 0.02,
    "MMS_Linf_divided_by_max_exact": 0.10,
    "scheme_difference_volume_weighted_relative_L2": 0.02,
    "scheme_difference_Linf_divided_by_max_exact": 0.05,
    "outer_initial_residual": 1e-8,
    "linear_final_residual": 1e-10,
    "max_scaled_update": 1e-10,
    "max_outer_iterations": 4000,
}


def require(condition, message):
    if not condition:
        raise GateError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_hashes(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def foam_header(name, cls="dictionary"):
    return ("FoamFile\n{\n version 2.0; format ascii; class " + cls
            + "; object " + name + ";\n}\n")


def body(path):
    text = path.read_text()
    require(re.search(r"format\s+ascii\s*;", text) is not None, f"ASCII mesh required: {path}")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"FoamFile\s*\{.*?\}", "", text, count=1, flags=re.S).strip()


def read_list(path, kind):
    match = re.fullmatch(r"(\d+)\s*\((.*)\)\s*", body(path), re.S)
    require(match is not None, f"Invalid OpenFOAM list: {path}")
    if kind == "points":
        values = np.fromstring(match[2].replace("(", " ").replace(")", " "), sep=" ").reshape(-1, 3)
    elif kind == "faces":
        entries = re.findall(r"(\d+)\s*\(([^()]*)\)", match[2])
        values = [tuple(map(int, item.split())) for _, item in entries]
        require(all(int(n) == len(v) for (n, _), v in zip(entries, values)), "Face length mismatch")
    else:
        values = np.fromstring(match[2], dtype=np.int64, sep=" ")
    require(len(values) == int(match[1]), f"List count mismatch: {path}")
    return values


def read_mesh(mesh_path):
    points = read_list(mesh_path / "points", "points")
    faces = read_list(mesh_path / "faces", "faces")
    owner = read_list(mesh_path / "owner", "labels")
    neighbour = read_list(mesh_path / "neighbour", "labels")
    patches = []
    for name, content in re.findall(r"(\w+)\s*\{([^{}]*)\}", body(mesh_path / "boundary")):
        entries = dict(re.findall(r"(\w+)\s+([^;]+);", content))
        require(entries["type"].strip() in ("patch", "wall"), "Uncoupled physical patches required")
        patches.append({"name": name, "nFaces": int(entries["nFaces"]), "startFace": int(entries["startFace"])})
    require(len(owner) == len(faces) and len(neighbour) <= len(faces), "Invalid addressing counts")
    ncell = int(max(owner.max(), neighbour.max())) + 1
    require(np.all(owner >= 0) and np.all(neighbour >= 0), "Negative cell index")
    next_face = len(neighbour)
    for patch in patches:
        require(patch["startFace"] == next_face, "Noncontiguous boundary")
        next_face += patch["nFaces"]
    require(next_face == len(faces), "Boundary coverage mismatch")
    return points, faces, owner, neighbour, patches, ncell


def independent_geometry(mesh):
    """Independent signed-pyramid integration, with oriented polygon face fans.

    This supports the actual triangular/planar merged-quad final candidate.
    No native geometry is used as input to this calculation.
    """
    points, faces, owner, neighbour, _, ncell = mesh
    cf = np.zeros((len(faces), 3))
    sf = np.zeros_like(cf)
    sizes = np.array([len(face) for face in faces])
    require(set(sizes) <= {3, 4}, "Only pinned triangle/merged-quad mesh supported")
    for size in sorted(set(sizes)):
        ids = np.flatnonzero(sizes == size)
        vertex_ids = np.array([faces[i] for i in ids], dtype=np.int64)
        require(np.all(vertex_ids >= 0) and np.all(vertex_ids < len(points)), "Invalid vertex index")
        q = points[vertex_ids]
        fan_origin = q.mean(axis=1)
        next_q = np.roll(q, -1, axis=1)
        fan_area = np.cross(q - fan_origin[:, None, :], next_q - fan_origin[:, None, :]) / 2
        fan_mag = np.linalg.norm(fan_area, axis=2)
        face_area = fan_mag.sum(axis=1)
        require(np.all(face_area > 0), "Zero face area")
        sf[ids] = fan_area.sum(axis=1)
        triangle_centres = (q + next_q + fan_origin[:, None, :]) / 3
        cf[ids] = (triangle_centres * fan_mag[:, :, None]).sum(axis=1) / face_area[:, None]
        norm = np.linalg.norm(sf[ids], axis=1)
        require(np.all(norm > 0), "Degenerate oriented face")
        nonplanarity = np.abs(np.einsum("ijk,ik->ij", q - cf[ids, None, :], sf[ids] / norm[:, None]))
        require(float(nonplanarity.max()) <= 1e-11, "Nonplanar face beyond pinned-mesh tolerance")
    ref = np.zeros((ncell, 3))
    count = np.zeros(ncell)
    np.add.at(ref, owner, cf)
    np.add.at(count, owner, 1)
    np.add.at(ref, neighbour, cf[:len(neighbour)])
    np.add.at(count, neighbour, 1)
    require(np.all(count >= 4), "Invalid cell-face incidence")
    ref /= count[:, None]
    volume = np.zeros(ncell)
    first_moment = np.zeros((ncell, 3))
    for addressing, face_ids, orientation in (
        (owner, np.arange(len(faces)), 1),
        (neighbour, np.arange(len(neighbour)), -1),
    ):
        pyr_v = orientation * np.einsum("ij,ij->i", sf[face_ids], cf[face_ids] - ref[addressing]) / 3
        pyr_centroid = 0.75 * cf[face_ids] + 0.25 * ref[addressing]
        np.add.at(volume, addressing, pyr_v)
        np.add.at(first_moment, addressing, pyr_v[:, None] * pyr_centroid)
    require(np.isfinite(volume).all() and np.all(volume > 0), "Nonpositive/nonfinite independent volume")
    centre = first_moment / volume[:, None]
    return centre, cf, sf, volume


def make_case(target, source_mesh, patches, scheme):
    (target / "system").mkdir(parents=True)
    (target / "0").mkdir()
    shutil.copytree(source_mesh, target / "constant/polyMesh")
    (target / "system/controlDict").write_text(foam_header("controlDict") + """
application valveNativeGate;
startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;
writeControl timeStep; writeInterval 1; purgeWrite 0;
writeFormat ascii; writePrecision 17; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable false;
""")
    (target / "system/fvSchemes").write_text(foam_header("fvSchemes") + f"""
ddtSchemes {{ default steadyState; }}
gradSchemes {{ default Gauss linear; }}
divSchemes {{ default none; }}
laplacianSchemes {{ default Gauss linear {scheme}; }}
interpolationSchemes {{ default linear; }}
snGradSchemes {{ default {scheme}; }}
fluxRequired {{ default no; }}
""")
    (target / "system/fvSolution").write_text(foam_header("fvSolution") + """
solvers
{
    T { solver PCG; preconditioner DIC; tolerance 1e-12; relTol 0; maxIter 5000; }
}
""")
    boundaries = "\n".join(p["name"] + " { type fixedValue; value uniform 0; }" for p in patches)
    (target / "0/T").write_text(foam_header("T", "volScalarField") +
                              "dimensions [0 2 0 0 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n" + boundaries + "\n}\n")


def command(argv, log, env, cwd=None, timeout=7200):
    with log.open("w") as out:
        out.write("COMMAND " + json.dumps(list(map(str, argv))) + "\n")
        out.flush()
        proc = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=out,
                              stderr=subprocess.STDOUT, timeout=timeout, check=False)
        out.write(f"\nEXIT_CODE {proc.returncode}\n")
    require(proc.returncode == 0, f"Command exited {proc.returncode}; raw log: {log}")


def csv(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    require(np.isfinite(data).all(), f"Nonfinite CSV: {path}")
    return data


def compare_geometry(probe_case, mesh, independent):
    c, cf, sf, v = independent
    cells = csv(probe_case / "native_cells.csv")
    faces = csv(probe_case / "native_faces.csv")
    require(cells.shape == (len(c), 5) and faces.shape == (len(cf), 8), "Native geometry count mismatch")
    require(np.array_equal(cells[:, 0], np.arange(len(c))), "Native cell order mismatch")
    require(np.array_equal(faces[:, 0], np.arange(len(cf))), "Native face order mismatch")
    patch_ids = np.full(len(cf), -1)
    for i, p in enumerate(mesh[4]):
        patch_ids[p["startFace"]:p["startFace"] + p["nFaces"]] = i
    require(np.array_equal(faces[:, 7], patch_ids), "Native patch mapping mismatch")
    comparisons = [
        ("C", cells[:, 1:4], c, 1e-11, 5e-10),
        ("Cf", faces[:, 1:4], cf, 1e-11, 5e-10),
        ("Sf", faces[:, 4:7], sf, 2e-14, 5e-10),
        ("V", cells[:, 4], v, 1e-22, 1e-9),
    ]
    result = {"cells": len(c), "faces": len(cf), "boundary_mapping": "PASS"}
    for name, actual, expected, atol, rtol in comparisons:
        difference = np.abs(actual - expected)
        passed = bool(np.all(difference <= atol + rtol * np.abs(expected)))
        result[name] = {"max_absolute_difference": float(difference.max()), "atol": atol, "rtol": rtol, "pass": passed}
        require(passed, f"Native versus independent {name} mismatch: {result[name]}")
    return result


def inspect_mms(case, native_c, volume):
    values = csv(case / "manufactured_field.csv")
    require(values.shape == (len(volume), 4), "MMS field count mismatch")
    require(np.array_equal(values[:, 0], np.arange(len(volume))), "MMS cell order mismatch")
    exact = (native_c * native_c).sum(axis=1)
    require(np.allclose(values[:, 2], exact, rtol=1e-13, atol=1e-18), "MMS exact-field identity mismatch")
    error = values[:, 1] - exact
    require(np.allclose(values[:, 3], error, rtol=1e-12, atol=1e-18), "MMS error-column mismatch")
    l2 = float(np.sqrt(np.sum(volume * error * error) / np.sum(volume * exact * exact)))
    linf = float(np.max(np.abs(error)) / np.max(np.abs(exact)))
    history = csv(case / "iterations.csv")
    require(history.shape[1] == 5 and 3 <= len(history) <= 4000, "Invalid MMS iteration evidence")
    require(np.array_equal(history[:, 0], np.arange(1, len(history) + 1)), "Nonsequential iteration evidence")
    require(np.all(history[:, 1:] >= 0), "Negative residual/update evidence")
    require(history[-1, 1] <= LIMITS["outer_initial_residual"], "MMS outer correction not converged")
    require(history[-1, 2] <= LIMITS["linear_final_residual"], "MMS inner solve not converged")
    require(history[-1, 4] <= LIMITS["max_scaled_update"], "MMS update not converged")
    require(l2 <= LIMITS["MMS_volume_weighted_relative_L2"], f"MMS L2={l2} exceeds diagnostic gate")
    require(linf <= LIMITS["MMS_Linf_divided_by_max_exact"], f"MMS Linf={linf} exceeds diagnostic gate")
    require((case / "1/T").is_file(), "Missing raw final OpenFOAM T field")
    return {"relative_L2": l2, "scaled_Linf": linf, "outer_iterations": len(history),
            "last_initial_residual": float(history[-1, 1]), "last_final_residual": float(history[-1, 2]),
            "last_scaled_update": float(history[-1, 4])}, values[:, 1], exact


def run(case, output, report):
    source_mesh = case / "constant/polyMesh"
    report["source_mesh_path"] = str(source_mesh)
    require(source_mesh.is_dir(), "Missing source constant/polyMesh")
    before = tree_hashes(source_mesh)
    report["source_mesh_sha256_before"] = before
    try:
        version = os.environ.get("WM_PROJECT_VERSION", "")
        precision = os.environ.get("WM_PRECISION_OPTION", "")
        report["environment"] = {"WM_PROJECT_VERSION": version, "WM_PRECISION_OPTION": precision,
                                 "WM_OPTIONS": os.environ.get("WM_OPTIONS", ""),
                                 "wmake": shutil.which("wmake")}
        require(version in ("v1912", "1912") and precision == "DP" and shutil.which("wmake"),
                "BLOCKED_RUNTIME: source OpenCFD/ESI OpenFOAM v1912 double-precision development environment (wmake + headers + libraries)")
        native_source = Path(__file__).resolve().parent / "native"
        report["tool_source_sha256"] = tree_hashes(native_source)
        report["runner_sha256"] = sha(Path(__file__))
        build = output / "build"
        shutil.copytree(native_source, build)
        binary_dir = output / "bin"
        binary_dir.mkdir()
        env = os.environ.copy()
        env["FOAM_USER_APPBIN"] = str(binary_dir)
        command([shutil.which("wmake")], output / "build.log", env, cwd=build, timeout=900)
        binary = binary_dir / "valveNativeGate"
        require(binary.is_file(), "wmake did not produce isolated executable")
        report["compiled"] = True
        report["executable_sha256"] = sha(binary)
        mesh = read_mesh(source_mesh)
        independent = independent_geometry(mesh)
        np.savez_compressed(output / "independent_geometry.npz", C=independent[0], Cf=independent[1], Sf=independent[2], V=independent[3])
        probe = output / "probe"
        make_case(probe, source_mesh, mesh[4], "corrected")
        report["execution_attempted"] = True
        command([binary, "-case", probe, "-probeOnly"], output / "probe.log", env)
        report["executed"] = True
        report["native_probe_completed"] = True
        report["native_geometry"] = compare_geometry(probe, mesh, independent)
        native_cells = csv(probe / "native_cells.csv")
        solutions = []
        report["manufactured_cases"] = {}
        for name, scheme in (("corrected", "corrected"), ("limited05", "limited corrected 0.5")):
            target = output / name
            make_case(target, source_mesh, mesh[4], scheme)
            command([binary, "-case", target], output / (name + ".log"), env)
            compare_geometry(target, mesh, independent)
            metrics, solved, exact = inspect_mms(target, native_cells[:, 1:4], native_cells[:, 4])
            report["manufactured_cases"][name] = {"scheme": scheme, **metrics}
            require(tree_hashes(target / "constant/polyMesh") == before, "MMS mesh mutated")
            solutions.append(solved)
        volume = native_cells[:, 4]
        difference = solutions[0] - solutions[1]
        l2 = float(np.sqrt(np.sum(volume * difference**2) / np.sum(volume * exact**2)))
        linf = float(np.max(np.abs(difference)) / np.max(np.abs(exact)))
        report["single_mesh_scheme_sensitivity"] = {"relative_L2": l2, "scaled_Linf": linf,
                                                    "is_mesh_convergence": False}
        require(l2 <= LIMITS["scheme_difference_volume_weighted_relative_L2"], "Scheme L2 sensitivity exceeds diagnostic gate")
        require(linf <= LIMITS["scheme_difference_Linf_divided_by_max_exact"], "Scheme Linf sensitivity exceeds diagnostic gate")
        require(tree_hashes(probe / "constant/polyMesh") == before, "Probe mesh mutated")
        report["executed"] = True
        report["status"] = "PASS"
    finally:
        report["source_mesh_sha256_after"] = tree_hashes(source_mesh)
        report["source_mesh_unchanged"] = before == report["source_mesh_sha256_after"]
        require(report["source_mesh_unchanged"], "Source mesh changed during native gate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    case, output = args.case.resolve(), args.output.resolve()
    if output.exists():
        print("Refusing existing output: " + str(output), file=sys.stderr)
        return 2
    if output == case or case in output.parents:
        print("Output must be outside source case", file=sys.stderr)
        return 2
    output.mkdir(parents=True)
    report = {"schema_version": 1, "status": "FAIL", "compiled": False, "executed": False,
              "execution_attempted": False, "native_probe_completed": False,
              "validation_scope": "Real valve mesh native geometry and nonzero-source manufactured Poisson equation only",
              "manufactured_equation": "T=x^2+y^2+z^2; Laplacian(T)=6; Dirichlet T on every native face centre",
              "physical_boundary_conditions_used": False,
              "engineering_release": False, "mesh_convergence_claim": False,
              "threshold_basis": "Prospective diagnostic gates for this package, not calibrated engineering acceptance limits",
              "limits": LIMITS}
    code = 0
    try:
        run(case, output, report)
    except (GateError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report["status"] = "BLOCKED" if "BLOCKED_RUNTIME:" in str(exc) else "FAIL"
        report["reason"] = str(exc)
        code = 2 if report["status"] == "BLOCKED" else 1
    report["raw_evidence_sha256"] = tree_hashes(output)
    write_json(output / "report.json", report)
    print(json.dumps({"status": report["status"], "report": str(output / "report.json"),
                      "reason": report.get("reason")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
