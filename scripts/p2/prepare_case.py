#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 / A-04 cloud CFD: write the OpenFOAM case files for the cloud run.

The patch names are read from constant/polyMesh/boundary (written by
gmshToFoam) instead of being hard-coded, because gmshToFoam derives the patch
names from the gmsh physical groups and may sanitise or re-order them. Every
patch that is found in the mesh gets an entry in 0/U, 0/p (and 0/k, 0/omega,
0/nut for the turbulent case), so the case can never end up with a missing
boundary condition (which is a hard FATAL in OpenFOAM).

Modes
  laminar : incompressible laminar (the state21 setup), nu from --nu
  ras     : kOmegaSST turbulence model, for the rated-velocity operating point
"""
import argparse
import os
import re
import sys

FOAMFILE = (
    "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
    "    class       %s;\n    object      %s;\n}\n\n"
)


def write(path, cls, obj, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(FOAMFILE % (cls, obj))
        f.write(body)
    print("  wrote %s" % path)


def read_patches(poly_mesh_dir):
    """Patch names from constant/polyMesh/boundary."""
    path = os.path.join(poly_mesh_dir, "boundary")
    if not os.path.exists(path):
        raise SystemExit("ERROR: %s not found (gmshToFoam must run first)" % path)
    with open(path) as f:
        txt = f.read()
    names = re.findall(r"^[ \t]*(\S+)[ \t]*\n[ \t]*\{[ \t]*\n[ \t]*type[ \t]+(\w+)",
                       txt, re.M)
    names = [n for n, _t in names]
    if not names:
        raise SystemExit("ERROR: no patches parsed from %s" % path)
    return names


def pick_patch(names, key):
    cands = [n for n in names if key in n.lower()]
    if not cands:
        raise SystemExit("ERROR: no '%s' patch among %s" % (key, names))
    return cands[0]


def role_of(name, inlet, outlet):
    if name == inlet:
        return "IN"
    if name == outlet:
        return "OUT"
    return "WALL"


def bc_block(patches, inlet, outlet, spec):
    """spec: role -> list of (type, value-or-None)"""
    out = ""
    for name in patches:
        kind, value = spec[role_of(name, inlet, outlet)]
        out += "    %s\n    {\n        type %s;\n" % (name, kind)
        if value is not None:
            out += "        value %s;\n" % value
        out += "    }\n"
    return out


def build(case_dir, mode, velocity, rho, nu, end_time, write_interval):
    poly = os.path.join(case_dir, "constant", "polyMesh")
    patches = read_patches(poly)
    inlet = pick_patch(patches, "inlet")
    outlet = pick_patch(patches, "outlet")
    print("  patches: %s" % patches)
    print("  inlet='%s'  outlet='%s'" % (inlet, outlet))

    # ---- 0/U -------------------------------------------------------------
    spec_u = {
        "IN": ("fixedValue", "uniform (%g 0 0)" % velocity),
        "OUT": ("zeroGradient", None),
        "WALL": ("noSlip", None),
    }
    write(os.path.join(case_dir, "0", "U"), "volVectorField", "U",
          "dimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\n"
          "boundaryField\n{\n" + bc_block(patches, inlet, outlet, spec_u) + "}\n")

    # ---- 0/p (kinematic pressure, m2/s2) --------------------------------
    spec_p = {
        "IN": ("zeroGradient", None),
        "OUT": ("fixedValue", "uniform 0"),
        "WALL": ("zeroGradient", None),
    }
    write(os.path.join(case_dir, "0", "p"), "volScalarField", "p",
          "dimensions [0 2 -2 0 0 0 0];\ninternalField uniform 0;\n"
          "boundaryField\n{\n" + bc_block(patches, inlet, outlet, spec_p) + "}\n")

    # ---- turbulence fields ----------------------------------------------
    if mode == "ras":
        k_in = max(1.0e-6, 0.01 * velocity * velocity)
        om_in = max(1.0e-4, 0.09 ** 0.25 * k_in ** 0.5 / 0.02)
        spec_k = {
            "IN": ("fixedValue", "uniform %g" % k_in),
            "OUT": ("zeroGradient", None),
            "WALL": ("kqRWallFunction", "uniform %g" % k_in),
        }
        spec_om = {
            "IN": ("fixedValue", "uniform %g" % om_in),
            "OUT": ("zeroGradient", None),
            "WALL": ("omegaWallFunction", "uniform %g" % om_in),
        }
        spec_nut = {
            "IN": ("calculated", "uniform 0"),
            "OUT": ("calculated", "uniform 0"),
            "WALL": ("nutkWallFunction", "uniform 0"),
        }
        write(os.path.join(case_dir, "0", "k"), "volScalarField", "k",
              "dimensions [0 2 -2 0 0 0 0];\ninternalField uniform %g;\n"
              "boundaryField\n{\n" % k_in
              + bc_block(patches, inlet, outlet, spec_k) + "}\n")
        write(os.path.join(case_dir, "0", "omega"), "volScalarField", "omega",
              "dimensions [0 0 -1 0 0 0 0];\ninternalField uniform %g;\n"
              "boundaryField\n{\n" % om_in
              + bc_block(patches, inlet, outlet, spec_om) + "}\n")
        write(os.path.join(case_dir, "0", "nut"), "volScalarField", "nut",
              "dimensions [0 2 -1 0 0 0 0];\ninternalField uniform 0;\n"
              "boundaryField\n{\n"
              + bc_block(patches, inlet, outlet, spec_nut) + "}\n")

    # ---- constant --------------------------------------------------------
    write(os.path.join(case_dir, "constant", "transportProperties"),
          "dictionary", "transportProperties", "nu %s;\n" % nu)
    write(os.path.join(case_dir, "constant", "g"), "uniformDimensionedVectorField",
          "g", "dimensions [0 1 -2 0 0 0 0];\nvalue (0 0 0);\n")
    if mode == "ras":
        write(os.path.join(case_dir, "constant", "momentumTransport"),
              "dictionary", "momentumTransport",
              "simulationType RAS;\nRAS\n{\n    model kOmegaSST;\n"
              "    turbulence on;\n    printCoeffs on;\n}\n")
    else:
        write(os.path.join(case_dir, "constant", "momentumTransport"),
              "dictionary", "momentumTransport", "simulationType laminar;\n")

    # ---- system/controlDict ---------------------------------------------
    def fo(name, patch, operation, field):
        return (
            "    %s\n    {\n"
            "        type surfaceFieldValue;\n"
            '        libs ("libfieldFunctionObjects.so");\n'
            "        writeControl timeStep;\n"
            "        writeInterval %d;\n"
            "        regionType patch;\n"
            "        name %s;\n"
            "        operation %s;\n"
            "        fields (%s);\n"
            "    }\n" % (name, write_interval, patch, operation, field)
        )

    functions = (
        fo("pInlet", inlet, "areaAverage", "p")
        + fo("pOutlet", outlet, "areaAverage", "p")
        + fo("qInlet", inlet, "sum", "phi")
        + fo("qOutlet", outlet, "sum", "phi")
    )
    control = (
        "application simpleFoam;\n\n"
        "startFrom startTime;\nstartTime 0;\nstopAt endTime;\n"
        "endTime %d;\ndeltaT 1;\n\n"
        "writeControl timeStep;\nwriteInterval %d;\npurgeWrite 0;\n"
        "writeFormat ascii;\nwriteFormatOptions { precision 15; }\n"
        "timeFormat general;\ntimePrecision 8;\n\n"
        "functions\n{\n%s}\n" % (end_time, end_time, functions)
    )
    write(os.path.join(case_dir, "system", "controlDict"), "dictionary",
          "controlDict", control)

    # ---- system/fvSolution ----------------------------------------------
    if mode == "ras":
        solvers = (
            "solvers\n{\n"
            "    p     { solver GAMG; tolerance 1e-7; relTol 0.01; "
            "smoother GaussSeidel; nCellsInCoarsestLevel 10; }\n"
            "    U     { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-9; relTol 0; }\n"
            "    k     { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-9; relTol 0; }\n"
            "    omega { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-9; relTol 0; }\n"
            "}\n"
        )
        relaxation = (
            "relaxationFactors\n{\n"
            "    fields { p 0.3; }\n"
            "    equations { U 0.7; k 0.7; omega 0.7; }\n"
            "}\n"
        )
        divschemes = (
            "    div(phi,U)     bounded Gauss linearUpwind grad(U);\n"
            "    div(phi,k)     bounded Gauss limitedLinear 1;\n"
            "    div(phi,omega) bounded Gauss limitedLinear 1;\n"
        )
    else:
        solvers = (
            "solvers\n{\n"
            "    p     { solver GAMG; tolerance 1e-7; relTol 0.01; "
            "smoother GaussSeidel; nCellsInCoarsestLevel 10; }\n"
            "    U     { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-9; relTol 0; }\n"
            "}\n"
        )
        relaxation = (
            "relaxationFactors\n{\n"
            "    fields { p 0.3; }\n"
            "    equations { U 0.7; }\n"
            "}\n"
        )
        divschemes = "    div(phi,U)     bounded Gauss linearUpwind grad(U);\n"

    solution = (
        solvers
        + "SIMPLE\n{\n"
        "    nNonOrthogonalCorrectors 0;\n"
        "    consistent no;\n"
        "    residualControl { p 1e-4; U 1e-5; }\n"
        "}\n"
        + relaxation
    )
    write(os.path.join(case_dir, "system", "fvSolution"), "dictionary",
          "fvSolution", solution)

    # ---- system/fvSchemes ------------------------------------------------
    schemes = (
        "ddtSchemes { default steady; }\n\n"
        "gradSchemes { default Gauss linear; }\n\n"
        "divSchemes\n{\n"
        "    default none;\n"
        + divschemes +
        "}\n\n"
        "laplacianSchemes { default Gauss linear corrected; }\n\n"
        "interpolationSchemes { default linear; }\n\n"
        "snGradSchemes { default corrected; }\n"
    )
    write(os.path.join(case_dir, "system", "fvSchemes"), "dictionary",
          "fvSchemes", schemes)

    print("  case written to %s (mode=%s, U_in=%.6g m/s, nu=%s)"
          % (case_dir, mode, velocity, nu))
    return {"patches": patches, "inlet": inlet, "outlet": outlet}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--mode", choices=["laminar", "ras"], default="laminar")
    ap.add_argument("--velocity", type=float, required=True)
    ap.add_argument("--rho", type=float, default=1024.0)
    ap.add_argument("--nu", default="1.025e-6")
    ap.add_argument("--end-time", type=int, default=2000)
    ap.add_argument("--write-interval", type=int, default=50)
    args = ap.parse_args()
    build(args.case_dir, args.mode, args.velocity, args.rho, args.nu,
          args.end_time, args.write_interval)


if __name__ == "__main__":
    main()
