# P08 direct-OCC/Gmsh bounded trial, 2026-10-23

## Outcome
This is a **failed coarse volume-mesh trial with a retained surface mesh**, not final P08 mesh or CFD acceptance. It establishes a new, inexpensive alternative-path failure mode without repeating the historical multi-million-cell snappyHexMesh attempts.

- Official Gmsh 4.15.2 was installed into `vendor/`, not system-wide; published Linux-wheel SHA256 was checked. No account, credential, license purchase, system/network setting or external engineering-data upload was used.
- The unchanged pinned 507,364-byte P08 seal-omitted proxy STEP imported as one volume / 132 surfaces; CAD volume 64,142,426.1438 mm³. Healing/sewing/fixing switches remained off.
- Direct surface meshing completed in 9.70 s, 176,428 KiB process peak RSS. Retained `surface.msh`: 7,598,266 bytes, SHA256 `396f7a7ff1387a18bbcca0df01812a0cab2791274d26ec7a4658d2aa66c19e9c`.
- Fresh MSH readback found 78,547 nodes, 157,086 linear triangles, all 132 named physical face groups, 235,629 edges each incident to two triangles, and two connected surface components. Their oriented volumes are +63,700,354.5742 and −759.5809 mm³. This supports opposite shell orientation, not proof against self-intersection or resolved micro-passages.
- Surface volume is **0.6904% below CAD volume**. This is measured error, not an accepted accuracy tolerance.
- One 3D continuation imported the stored surface, but the log proves `generate(3)` ran 1D/2D meshing again. Exact saved-surface reuse therefore failed and the in-memory surface at failure was not saved. It completed initial tetrahedralization and failed during boundary recovery: **`PLC Error: A segment and a facet intersect at point`**. Elapsed 12.84 s, sampled peak RSS 376,946,688 bytes; exit 1. No resource/time limit triggered and **no final volume MSH was produced**. Exact conflicting segment/facet IDs or coordinates are not present in this log; no `.pos`/intersection diagnostic was found in the trial directory or task cwd (depth 2). The failure cannot be mapped to a specific saved-MSH face or classified as invalid CAD versus discretization intersection.

## What changed from the old approach
Direct OCC-conforming tetrahedral generation avoids snappyHexMesh's large external background and pre-retention refinement. It did **not** remove CAD faces or repeat A02's generic-wall downgrade. It did not rerun the accepted NSC1 representative flow.

The first surface count gate (50,000 triangles) declined continuation. It was explicitly reconsidered using the actual low RSS and retained surface, not treated as a user or engineering requirement. Exactly one bounded 3D continuation was then authorized; no 3D retry occurred. Resource controls remained one thread, 180 s wall time per monitored stage, 2 GiB sampled RSS and 4 GiB address space. Polling is 0.1 s, so sampled RSS is not a mathematically hard instantaneous cap; RLIMIT_AS is the hard address limit. File sizes were small, but the proposed 200 MB artifact planning allowance is not enforced by this monitor.

## Face mapping and geometry cautions
The original finite-face manifest supplies area/bounds/family pins. Default Gmsh OCC boxes overbound some trimmed surfaces. `Geometry.OCCBoundsUseStl=1` reduces that but bounds remain approximate. Two pre-mesh assertion failures are preserved. The final identity matcher requires unique area plus bounding-box correspondence, with a **0.2 mm search tolerance**; measured maximum bbox difference is 0.072205 mm. This tolerance is not geometry approximation or manufacturing acceptance. Original source hashes, one-to-one mappings and all per-face observations remain in `evidence/geometry.json`.

Surface concentration: generic faces 155,125 triangles, neck 964, guide 476, retainer 176, key side 126, vent 83, key root 76, wall step 60. Source faces 119 and 125 alone contain 48,154 and 45,539 triangles. A low aggregate count is not evidence of adequate critical-gap resolution, and all original engineering mesh gates remain open.

## Reproduction
The scripts are fixed-input research runners, not a portable product installer. They currently reference the original recovered STEP and source-rule paths. Resolve those same bytes in the consuming executor and adjust those two path constants only; preserve full hashes. `trial.py` uses this directory for outputs and `monitor.py` adds isolated `vendor/` to PYTHONPATH. Do not run an unreviewed automatic retry; reproduce only when explicitly useful.

1. Install the pinned official wheel locally with no dependency additions.
2. `python monitor.py surface` performs original STEP import, unique face mapping, surface generation and saved artifact.
3. `PYTHONPATH=vendor python readback_surface.py` reads the saved MSH, without remeshing, to check group/topological measurements.
4. `python monitor.py volume` is the single historical continuation configuration. It is expected to reproduce the recorded PLC failure, not a known-success solver case.
5. `python -m unittest -v test_saved_evidence.py` checks saved receipts and pins only. It is not a fresh meshing run.

No healing, geometry simplification, fluid boundary-condition change, mesh repair or solver run is included. Next useful action is **localized conflict diagnosis**, then a specifically changed surface candidate if justified. Raising memory limits would not address the observed PLC failure.

## Official package and documentation
- https://gmsh.info/ links the official `gmsh` PyPI package and describes GPL version 2 or later with a linking exception. Closed-source redistribution/integration has separate licensing considerations; this private research execution does not decide the eventual framework's licensing.
- https://pypi.org/project/gmsh/4.15.2/ published Linux-wheel SHA256: `4076a948ce22625330d1413d4982e22b5c69fc2f0f7951f5df64c778cf54108c`.
- https://gmsh.info/doc/texinfo/gmsh.html documents size-field controls, OCC bounding boxes and signed quality measures.

The input remains a seal-omitted research proxy. No manufacturing, actual valve leakage, final native checkMesh, whole-domain flow, ΔP, resistance coefficient or engineering release is established here.
