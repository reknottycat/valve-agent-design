# C2 geometry-stage verification

Status: **PARTIAL design package, locally verified geometry stage**. No product
qualification, manufacturing release, or verified GitHub publication is claimed.

## Proven artifacts

- Source/variant matrix and nine source/crop SHA256 checks pass
- Seven simplified main parts are valid single solids in closed, check-closed and open states
- All27 delivered STEP files (parts, assemblies and fluid regions in three states) reimported and compared with freshly rebuilt native geometry; exchanges pass with explicit mm metadata
- 28 sampled spindle/disc states pass volume-interference and opposing planar-face contact gates
- Closed disc contacts the continuous seat annulus; it is separated from the body web by the proposed2mm seat protrusion
- Removing that protrusion in an in-memory model produces3928.43mm² of unintended disc/body contact and is rejected
- Seven fluid-position samples distinguish closed isolation (two volumes) and open connectivity (one volume)
- Mesh has11178nodes and47679tetrahedra, positive finite Jacobians, one shared-face component,
  exact exterior boundary coverage, no nonmanifold faces and no duplicated boundary triangles
- SI mesh volume differs from the CAD volume by approximately0.431%; maximum accepted geometric-volume error remains1%
- Ten C2 regression tests pass in ordinary and optimized Python;20 inherited T04 checks also pass
- Injected CAD-build exception replaces any earlier PASS with RUNNING/non-authorized state before reconstruction
- Closed/open FCStd snapshots reopen with seven valid parts each; these are neutral geometry, not full feature history
- A3 study section drawing (PDF/SVG/DXF), five-page Chinese review PDF, and study BOM (CSV/JSON) generated
- All six rendered PDF pages were inspected; no clipping, overlaps or missing glyphs observed

Exact machine results: `../T22/out/geometry_check.json`, `../T22/out/negative_contact_control.json`,
`../T23/out/mesh_report.json`, `../T40/out/freecad_report.json`, and `../T40/out/drawing_report.json`.

## Independent review corrections

The review reproduced source dimensions and mesh topology, identified a body/seat
coplanar-contact defect missed by volume-only checks, and verified the corrective
seat protrusion with a real red/green geometry comparison. It also checked fail-closed
handling of invalid Boolean results, startup failure, missing contact, mixed units,
stale hashes, and the separation of reference spindle travel from assumed free disc lift.

The lofted-body STEP test initially failed when using nonadaptive mass integration.
Adaptive integration at1e-9 reduced integration error; the exchange acceptance
threshold was not loosened. This does not establish pressure strength or minimum wall.

## Remaining gates

OpenFOAM/CalculiX benchmark execution and GitHub writes are paused after explicit
tool cancellation. No retry or alternative execution route was used. Separate solver
preparation is retained by the project owner; it is not counted as a passing runtime.

The overall goal remains open: controlled variant/pressure/material/standards basis,
stem nut/thread and guide detail, bonnet bolting/gasket, packing/gland/locking parts,
manufacturing tolerances, strength/performance simulations, and engineering/physical
validation are incomplete. The seven-main-part BOM is not the original complete BOM.

## Reproduce

Run `bash runs/20261006/C2/verify_available.sh` from the repository after establishing
the CAD venv and host drawing/FreeCAD runtimes. The script runs no CFD/FEA solver and
prints the remaining PARTIAL/HOLD state explicitly. It requires the sibling
`CLOUD/T04/geometry_gate.py`; include that directory when transferring C2 independently.
