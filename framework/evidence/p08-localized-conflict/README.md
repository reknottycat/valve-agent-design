# P08 localized segment–facet conflict diagnostic

Status: **FAILED mesh, diagnostic localization succeeded. No CFD or engineering acceptance.**

One bounded repeat with unchanged CAD and meshing parameters/algorithms. Only General.AbortOnError was changed from API default 2 to 0, to preserve the diagnostic context hidden by the first thrown error. Logger capture added; Mesh.SaveAll=1 set only after failure for output. No design edit, refinement, installation, or solver execution. Source SHA-256 unchanged: a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787.

Official option/API source: https://gmsh.info/doc/texinfo/gmsh.html#index-General_002eAbortOnError and https://gmsh.info/doc/texinfo/gmsh.html#Namespace-gmsh
Version 4.15.2.

## Results
- Gmsh reports PLC segment–facet intersection; surface 108; segment nodes 29162/29134; facet nodes 30518/30569/30581.
- Error tags independently returned by getLastEntityError and getLastNodeError.
- Exact current failed surface saved: failed-current.msh; SHA-256 273224f13f9f59c158395bb2816678842c17bc3f27f336a9ec4eb3e8142c3556.
- Current regenerated surface has 157084 triangles, not the originally imported 157086. Therefore older surface.msh is NOT the failing mesh; this run captures the actual candidate.
- Volume elements: zero. Three meshing errors. Process return 0 merely reflects AbortOnError=0 and completion of diagnostic capture, NOT meshing success.
- Wall 14.55 s; sampled RSS 388972544 bytes. Caps 180 s / 2 GiB RSS / 4 GiB address; no cap was hit.

## Localization and first-principles explanation
Readback establishes segment in Gmsh/source face64, family guide (elements5254,5255). Intersecting triangle is element8877, Gmsh/source face108, family guide.

Unchanged CAD reports both surfaces as cylinders. Their local radii are32mm and31mm, common axis x=300,y=0, so local radial separation1mm. The surface64 straight mesh edge spans 30.001722 degrees, projected chord 16.565348mm, with maximum inward sag 1.090498mm. Straight chords approximate a curved boundary and here the inward error exceeds the available gap.

An independent 3x3 line/triangle intersection calculation gives (321.960384357,21.856025193,136.859083224)mm, segment parameter0.628724801, triangle barycentric weights(0.008688513,0.960704904,0.030606583), all strictly internal. CAD projection gives intersection distance1.017031802mm from face64,0.017031802mm from face108. This quantitatively explains crossing of the discrete surfaces despite separation of these underlying local cylindrical surfaces.

Supported conclusion: this identified blocker is local geometric approximation incompatible with the1mm gap. It is NOT evidence of an inherently invalid valve design, insufficient GPU, or a proven Gmsh software defect. It does NOT certify other CAD regions, mesh independence, or engineering release.

## Next action (not executed)
Use the captured local patch to set gap-aware/chord-error-based sizing for faces64/108 and shared boundaries; evaluate local error relative to gap, rather than globally increasing all mesh counts. Freeze source design. Compare localized surfaces before another bounded3D attempt. All additional computation requires parent review of these findings.

## Reproduction
trial.py+monitor.py reproduce the single diagnostic using existing vendor and original source paths. read_conflict.py is mesh readback only. check_cad.py imports unchanged CAD and projects the captured point; no meshing. evidence contains raw logs, caps receipt, node/entity mapping and analytic checks.
