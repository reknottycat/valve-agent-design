# Skewness criteria: exact Debian OpenFOAM 1912.200626-3 source comparison

Read-only review, 2026-10-23. No native rerun, edits to thresholds or CFD.

## Default diagnostics
`primitiveMeshCheck.C:42` initializes `skewThreshold_ = 4`. `polyMeshCheck.C:171–264` computes `polyMeshTools::faceSkewness` and flags every face for skew > that single threshold, including ordinary boundary faces. `checkGeometry.C:689–700` counts this as a failed check independently of `-allGeometry`.

The actual modern primitiveMeshTools formula (lines 35–106) is dimensionless. With face centroid F, owner P, neighbor N, area vector S:
- internal/coupled: d=N-P; v=(F-P) - d*(S·(F-P))/(S·d+ROOTVSMALL); denominator=max(0.2|d|+ROOTVSMALL, max_face_vertices |vhat·(vertex-F)|); skew=|v|/denominator.
- noncoupled boundary: n=normalized(S), d=n*(n·(F-P)); same v; denominator uses 0.4|d| rather than 0.2|d|.
Thus boundary skew measures tangential displacement of the face centroid from the owner-centre normal projection, normalized by a directional face extent / normal-distance floor. It is NOT signed cell volume or an invalid-topology test.

## Separate mesh-quality controls
The installed official v1912 `etc/caseDicts/mesh/generation/meshQualityDict.cfg` and `etc/caseDicts/annotated/meshQualityDict` specify maxInternalSkewness 4 and maxBoundarySkewness 20, annotated as allowed maxima. These are mesh-quality configuration controls, commonly associated with mesh generation/motion; they are NOT the default checkMesh global threshold. They can also be applied by `checkMesh -meshQuality` reading `system/meshQualityDict`, so describing them as generation-only would be inaccurate.
`checkMesh.C:255–274` always calls checkGeometry first and then, if requested, adds checkMeshQuality. `checkMeshQuality.C:22` calls motionSmoother::checkMesh and collects meshQualityFaces. Consequently providing those controls would not replace/remove the default skew failure.

The exact downstream motionSmoother/polyMeshGeometry selection/formula chain was NOT fully retrieved in this review: an attempted official Debian directory request was cancelled by the tool with `network approval was cancelled before a decision was returned`, and that action was stopped. Installed libdynamicMesh symbols confirm separate internalSkew/boundarySkew arguments of polyMeshGeometry::checkFaceSkewness. The downloaded primitiveMeshGeometry.C has a DIFFERENT older formula and must not be substituted as proof of the active polyMeshGeometry implementation. Therefore the numerical claim “10.134 < 20 means the actual meshQuality check passes” is NOT made; only the documented distinct criterion values and non-replacement semantics are established.

## Consequence for current 614,334-tet candidate
Existing native result remains Failed 4. Parent's localization says all 15 high-skew faces are ordinary boundary patches 120/124; observed maximum 10.1340537. This does not alone establish invalid tetrahedra or universal CFD prohibition, and it does not establish numerical accuracy/stability either. Boundary condition, near-wall flux reconstruction and requested quantities matter. No new meshQuality run was made.

Separate decisions:
1. Invalid topology / negative volumes: hard geometry defect; e.g. rejected dual-mesh candidate. Not equivalent to a skew diagnostic.
2. Mandatory adopted acceptance: original frozen R1 flow plan requires full check PASS, which remains UNMET. Source interpretation is not permission to amend that gate or resume R1 solver.
3. Diagnostic risk: skew, nonorthogonality, interpolation weight/ratio and low connectivity determinant motivate scheme/BC-specific investigation. An explicitly authorized independent exploratory test may study these risks with NOT ACCEPTED status; it cannot be substituted for R1 acceptance or engineering release.

## Sources
Base exact source: https://sources.debian.org/data/main/o/openfoam/1912.200626-3/
- src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshCheck.C
- src/OpenFOAM/meshes/primitiveMesh/primitiveMeshCheck/primitiveMeshTools.C
- src/OpenFOAM/meshes/polyMesh/polyMeshCheck/polyMeshCheck.C
- src/OpenFOAM/meshes/polyMesh/polyMeshCheck/polyMeshTools.C
- applications/utilities/mesh/manipulation/checkMesh/checkGeometry.C
- applications/utilities/mesh/manipulation/checkMesh/checkMesh.C
- applications/utilities/mesh/manipulation/checkMesh/checkMeshQuality.C
Official installed package version 1912.200626-3+b1; package SHA pins retained in original quality evidence.
