#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 / A-04 cloud CFD: extract the results of an OpenFOAM run.

Reads the logs (checkMesh, simpleFoam) and the surfaceFieldValue output of an
OpenFOAM case directory and writes a JSON summary with mesh quality,
convergence information, the pressure drop and the flow coefficient Kv.

Kv definition (as used in deliverables/kv_calculation.json):
    Kv [m3/h] = Q [m3/h] * sqrt( (rho/1000) / dp [bar] )
"""
import argparse
import json
import os
import re
import sys


def read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, errors="replace") as f:
        return f.read()


def parse_check_mesh(path):
    txt = read_text(path)
    out = {"log": os.path.basename(path)}
    if not txt:
        out["error"] = "checkMesh log missing"
        return out
    for key, pat in (("cells", r"(?im)^\s*cells:\s*(\d+)"),
                     ("points", r"(?im)^\s*points:\s*(\d+)"),
                     ("faces", r"(?im)^\s*faces:\s*(\d+)"),
                     ("boundary_faces", r"(?im)^\s*boundary faces:\s*(\d+)")):
        m = re.search(pat, txt, re.M)
        if m:
            out[key] = int(m.group(1))
    m = re.search(r"(?i)max aspect ratio\s*[:=]?\s*([\d.eE+-]+)", txt)
    if m:
        out["max_aspect_ratio"] = float(m.group(1))
    m = re.search(r"Maximum non-orthogonality\s*[:=]?\s*([\d.eE+-]+)", txt)
    if m:
        out["max_non_orthogonality"] = float(m.group(1))
    m = re.search(r"(?i)max skewness\s*[:=]?\s*([\d.eE+-]+)", txt)
    if m:
        out["max_skewness"] = float(m.group(1))
    m = re.search(r"number of severely non-orthogonal[^:]*:\s*(\d+)", txt, re.I)
    if m:
        out["n_severely_non_orthogonal"] = int(m.group(1))
    out["mesh_ok"] = "Mesh OK" in txt
    m = re.search(r"(?i)failed\s+(\d+)\s+checks?", txt)
    if m:
        out["n_failed_checks"] = int(m.group(1))
    m = re.search(r"(\d+)\s+highly skew faces", txt)
    if m:
        out["n_highly_skew_faces"] = int(m.group(1))
    return out


def parse_simple_foam(path):
    txt = read_text(path)
    out = {"log": os.path.basename(path)}
    if not txt:
        out["error"] = "simpleFoam log missing"
        return out, []

    res = {}
    cur = None
    history = []
    cont = []
    for line in txt.splitlines():
        m = re.match(r"\s*Solving for (\w+),", line)
        if m:
            cur = m.group(1)
        m = re.search(r"Final residual = ([-\d.eE+]+)", line)
        if m and cur:
            res[cur] = float(m.group(1))
        m = re.match(r"^Time = (\d+)", line)
        if m:
            history.append([int(m.group(1)), res.get("p"), res.get("U"),
                            res.get("Ux"), res.get("Uy"), res.get("Uz")])
        m = re.search(r"time step continuity errors\s*:\s*sum local = ([-\d.eE+]+),"
                      r"\s*global = ([-\d.eE+]+),\s*cumulative = ([-\d.eE+]+)", line)
        if m:
            cont.append([float(m.group(1)), float(m.group(2)), float(m.group(3))])
        if "SIMPLE solution converged" in line:
            out["converged"] = True
        m = re.search(r"ExecutionTime = ([\d.]+) s", line)
        if m:
            out["execution_time_s"] = float(m.group(1))

    out["residuals_final"] = res
    if cont:
        out["continuity_final"] = {"sum_local": cont[-1][0],
                                   "global": cont[-1][1],
                                   "cumulative": cont[-1][2]}
    m = re.search(r"SIMPLE solution converged in (\d+) iterations", txt)
    if m:
        out["iterations"] = int(m.group(1))
    elif history:
        out["iterations"] = history[-1][0]
    out["converged"] = out.get("converged", False)
    return out, history


def parse_fo(case_dir, name):
    """Last value written by a surfaceFieldValue function object."""
    base = os.path.join(case_dir, "postProcessing", name)
    if not os.path.isdir(base):
        return None, None
    times = []
    for d in os.listdir(base):
        p = os.path.join(base, d, "surfaceFieldValue.dat")
        if os.path.exists(p):
            try:
                times.append((float(d), p))
            except ValueError:
                pass
    if not times:
        return None, None
    times.sort()
    t, path = times[-1]
    last = None
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        try:
            last = float(parts[-1])
        except ValueError:
            continue
    return t, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--velocity", type=float, required=True)
    ap.add_argument("--rho", type=float, default=1024.0)
    ap.add_argument("--mode", default="laminar")
    ap.add_argument("--nu", type=float, default=1.025e-6)
    ap.add_argument("--area", type=float, default=3.14159265358979e-2,
                    help="inlet area [m2]")
    args = ap.parse_args()

    case = args.case_dir
    res = {
        "label": args.label,
        "nu_m2_s": args.nu,
        "mode": args.mode,
        "velocity_inlet_m_s": args.velocity,
        "rho_kg_m3": args.rho,
        "inlet_area_m2": args.area,
        "case_dir": case,
    }
    res["mesh"] = parse_check_mesh(os.path.join(case, "log.checkMesh"))
    solver, history = parse_simple_foam(os.path.join(case, "log.simpleFoam"))
    res["solver"] = solver

    p_in_t, p_in = parse_fo(case, "pInlet")
    p_out_t, p_out = parse_fo(case, "pOutlet")
    q_in_t, q_in = parse_fo(case, "qInlet")
    q_out_t, q_out = parse_fo(case, "qOutlet")
    res["p_inlet_kinematic"] = p_in
    res["p_outlet_kinematic"] = p_out
    res["phi_inlet_sum"] = q_in
    res["phi_outlet_sum"] = q_out
    res["fo_times"] = {"pInlet": p_in_t, "pOutlet": p_out_t,
                       "qInlet": q_in_t, "qOutlet": q_out_t}

    if p_in is not None and p_out is not None:
        dp_kin = p_in - p_out
        dp_pa = dp_kin * args.rho
        res["dp_kinematic_m2_s2"] = dp_kin
        res["dp_Pa"] = dp_pa
        res["dp_bar"] = dp_pa / 1.0e5
        # flow rate: use the computed flux if available, else the prescribed one
        q = abs(q_in) if q_in not in (None, 0) else args.velocity * args.area
        res["Q_m3_s"] = q
        res["Q_m3_h"] = q * 3600.0
        if dp_pa > 0:
            res["kv_m3_h"] = res["Q_m3_h"] * ((args.rho / 1000.0) / res["dp_bar"]) ** 0.5
        else:
            res["kv_m3_h"] = None
        # loss coefficient K = dp / (0.5 rho v^2)
        v = q / args.area
        res["velocity_computed_m_s"] = v
        res["reynolds"] = args.rho * v * 0.2 / (args.rho * args.nu)
        if v > 0:
            res["K_loss"] = dp_pa / (0.5 * args.rho * v * v)

    if history:
        csv_name = os.path.basename(args.out).replace(".json", "") + "_residuals.csv"
        with open(os.path.join(os.path.dirname(args.out) or ".", csv_name),
                  "w") as f:
            f.write("time,p_res,U_res,Ux_res,Uy_res,Uz_res\n")
            for row in history:
                f.write(",".join("" if v is None else repr(v) for v in row) + "\n")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
