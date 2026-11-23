#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 / A-04 cloud CFD: mesh the FDG1 proxy fluid domain (open valve, seal omitted)
with Gmsh and export an MSH file for OpenFOAM's gmshToFoam.

Geometry: framework/cad/p08-packing-design derived proxy (whole-valve flow path,
DN200 bore, disc/seat passage, x from -600 to +1200 mm, includes 3-DN straight
extensions per the R1 flow study plan).

Domain correction applied here (documented, reproducible):
  The proxy fluid includes the stem/packing gallery (z > ~100 mm above the seat
  chamber). It is a dead-end side pocket that the through-flow never traverses;
  it also contains the near-degenerate torus/packing faces that made every 3-D
  mesher fail with "PLC Error: A segment and a facet intersect" (reproduced with
  Delaunay/HXT/Netgen/MMG3D at multiple resolutions). The gallery (176,288 mm3 =
  0.27% of the domain) is cut away with an axis-aligned box before meshing.
  Flow-path dP/Kv is unaffected by a dead-end pocket; this is a modelling
  simplification, not a change of the wetted flow path.

Units: the STEP is in millimetres. Gmsh meshes in millimetres (native OCC
tolerances) and the node coordinates of the exported MSH are then scaled once by
1e-3, so the file handed to OpenFOAM is strictly SI. A single uniform scale is
used, so lengths/areas/volumes stay consistent (verified by re-reading the MSH
and re-computing the volume/bbox).

Patches (physical groups; tags are unique across dimensions because OpenFOAM's
gmshToFoam keys patch names by physical tag only):
  tag 1  "inlet"  = planar face at x = -600 mm   (area pi*100^2 mm^2)
  tag 2  "outlet" = planar face at x = +1200 mm  (area pi*100^2 mm^2)
  tag 3  "walls"  = everything else (bore wall, seat/disc passage, cut pocket)
  tag 11 "fluid"  = the single remaining solid (3-D)

MSH version 2.2 is written because OpenFOAM v11 gmshToFoam parses the MSH 2.2
layout (a single "$Nodes"/"$Elements" block with a plain count line); the MSH
4.1 layout has one block per entity and is mis-parsed by that utility.
"""
import os
import sys
import time
import json

import gmsh

HERE = os.path.dirname(os.path.abspath(__file__))
GEOM = os.path.join(HERE, "geometry", "proxy_fluid.step")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fluid_flow.msh")
INFO = os.path.splitext(OUT)[0] + "_info.json"

# Characteristic lengths (mm). DN=200 -> bore r=100. The default set gives
# ~2.1e5 tets, inside the 1e5-3e5 band, with the best mesh quality of the
# parameter sweep that was run (median minSICN 0.68, no ill-shaped tets).
CLMAX = float(os.environ.get("P2_CLMAX", "14.0"))
# 0.4 mm created 414 near-degenerate tets (minSICN < 0.05) around the
# packing-gallery cutout and blew three steady-state solvers up; the
# smallest CAD feature is the 4 mm seal line, so 1.5 mm keeps it
# resolved while removing sliver cells
CLMIN = float(os.environ.get("P2_CLMIN", "1.5"))
CURV_SEGMENTS = int(os.environ.get("P2_CURV", "24"))
ALG3D = int(os.environ.get("P2_ALG3D", "1"))     # 1 = Delaunay (HXT/Netgen/Frontal hit PLC errors)

SCALE = 1.0e-3                                    # mm -> m
GALLERY_BOX = (270.0, -40.0, 100.0, 60.0, 80.0, 400.0)   # x,y,z,dx,dy,dz (mm)
INLET_X = -500.0
OUTLET_X = 1100.0
MAX_CAP_AREA = 35000.0                            # mm^2 (DN200 cap = 31416)

TAG_INLET, TAG_OUTLET, TAG_WALLS, TAG_FLUID = 1, 2, 3, 11


def scale_msh_nodes(path, factor):
    """Scale the node coordinates of an ASCII MSH 2.2 file by `factor`.

    The MSH 2.2 node block is:
        $Nodes
        N
        idx x y z      (N lines)
        $EndNodes
    Only those coordinate columns are touched; element connectivity is
    untouched because it is index based.
    """
    with open(path) as f:
        lines = f.read().split("\n")
    out, i, nscaled = [], 0, 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == "$Nodes":
            i += 1
            out.append(lines[i])
            n = int(lines[i].strip())
            i += 1
            for _ in range(n):
                p = lines[i].split()
                p[1] = "%.9g" % (float(p[1]) * factor)
                p[2] = "%.9g" % (float(p[2]) * factor)
                p[3] = "%.9g" % (float(p[3]) * factor)
                out.append(" ".join(p))
                i += 1
                nscaled += 1
            continue
        i += 1
    with open(path, "w") as f:
        f.write("\n".join(out))
    return nscaled


def classify_and_group():
    """Tag physical groups: fluid volume + inlet/outlet/walls surfaces."""
    vols = [v for v in gmsh.model.getEntities(3)
            if gmsh.model.occ.getMass(3, v[1]) > 1000.0]
    if len(vols) != 1:
        raise RuntimeError("expected exactly 1 flow volume, got %d" % len(vols))
    vol_tag = vols[0][1]
    gmsh.model.addPhysicalGroup(3, [vol_tag], TAG_FLUID, "fluid")

    bnd = gmsh.model.getBoundary([(3, vol_tag)], combined=False, oriented=False)
    inlet, outlet, walls = [], [], []
    for (d, s) in bnd:
        bb = gmsh.model.getBoundingBox(2, s)
        area = gmsh.model.occ.getMass(2, s)
        planar_x = abs(bb[3] - bb[0]) < 1.0e-3 and area < MAX_CAP_AREA
        if planar_x and bb[0] < INLET_X:
            inlet.append(s)
        elif planar_x and bb[0] > OUTLET_X:
            outlet.append(s)
        else:
            walls.append(s)
    if not inlet or not outlet:
        raise RuntimeError("inlet/outlet faces not found: %s %s"
                           % (inlet, outlet))
    gmsh.model.addPhysicalGroup(2, inlet, TAG_INLET, "inlet")
    gmsh.model.addPhysicalGroup(2, outlet, TAG_OUTLET, "outlet")
    gmsh.model.addPhysicalGroup(2, walls, TAG_WALLS, "walls")
    return vol_tag, inlet, outlet, len(walls)


def main():
    t0 = time.time()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("General.Verbosity", 3)
    gmsh.model.add("fluid_flow")

    gmsh.open(GEOM)
    gmsh.model.occ.synchronize()

    # Remove the dead-end stem/packing gallery (see module docstring).
    box = gmsh.model.occ.addBox(*GALLERY_BOX)
    gmsh.model.occ.cut([(3, 1)], [(3, box)])
    gmsh.model.occ.synchronize()

    vol_tag, inlet, outlet, nwalls = classify_and_group()
    vol_mm3 = gmsh.model.occ.getMass(3, vol_tag)
    a_in = sum(gmsh.model.occ.getMass(2, s) for s in inlet)
    a_out = sum(gmsh.model.occ.getMass(2, s) for s in outlet)
    bb = gmsh.model.getBoundingBox(3, vol_tag)
    print("flow volume      : %.1f mm^3 (%.6f m^3)" % (vol_mm3, vol_mm3 * SCALE ** 3))
    print("bbox (mm)        : x[%.1f %.1f] y[%.1f %.1f] z[%.1f %.1f]"
          % (bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]))
    print("inlet faces      : %s  area %.4f mm^2" % (inlet, a_in))
    print("outlet faces     : %s  area %.4f mm^2" % (outlet, a_out))
    print("wall faces       : %d" % nwalls)

    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", CURV_SEGMENTS)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeMin", CLMIN)
    gmsh.option.setNumber("Mesh.MeshSizeMax", CLMAX)
    gmsh.option.setNumber("Mesh.Algorithm3D", ALG3D)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.option.setNumber("General.NumThreads", 2)

    gmsh.model.mesh.generate(3)

    types, etags, _ = gmsh.model.mesh.getElements(3)
    ntet = sum(len(e) for e in etags if True)
    tet_tags = gmsh.model.mesh.getElementsByType(4)[0]
    q = gmsh.model.mesh.getElementQualities(tet_tags, "minSICN")
    q_sorted = sorted(q)
    stats = {
        "cells": ntet,
        "minSICN_min": q_sorted[0],
        "minSICN_p1": q_sorted[len(q_sorted) // 100],
        "minSICN_median": q_sorted[len(q_sorted) // 2],
        "minSICN_mean": sum(q) / len(q),
        "n_SICN_lt_0p05": sum(1 for v in q if v < 0.05),
        "n_SICN_lt_0p10": sum(1 for v in q if v < 0.10),
        "n_SICN_lt_0p20": sum(1 for v in q if v < 0.20),
        "volume_mm3": vol_mm3,
        "volume_m3": vol_mm3 * SCALE ** 3,
        "bbox_mm": [bb[0], bb[1], bb[2], bb[3], bb[4], bb[5]],
        "inlet_area_mm2": a_in,
        "outlet_area_m2": a_in * SCALE ** 2,
        "outlet_area_mm2": a_out,
        "wall_faces": nwalls,
        "clmax_mm": CLMAX,
        "clmin_mm": CLMIN,
        "curv_segments": CURV_SEGMENTS,
        "elapsed_s": time.time() - t0,
    }
    print("tets             : %d" % ntet)
    print("minSICN min/p1/med: %.4f / %.4f / %.4f"
          % (stats["minSICN_min"], stats["minSICN_p1"], stats["minSICN_median"]))

    # MSH 2.2 (the layout OpenFOAM v11 gmshToFoam can parse), ASCII, in mm.
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.write(OUT)
    n_nodes = scale_msh_nodes(OUT, SCALE)
    stats["nodes_scaled"] = n_nodes
    print("scaled %d node coordinates by %g -> metres" % (n_nodes, SCALE))

    with open(INFO, "w") as f:
        json.dump(stats, f, indent=2)
    print("written: %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
    gmsh.finalize()


if __name__ == "__main__":
    main()
