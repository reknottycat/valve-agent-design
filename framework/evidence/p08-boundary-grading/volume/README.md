# Bounded 3D comparison after boundary-complete surface grading

One authorized fresh 3D generation used the reviewed boundary-complete surface configuration. No volume grading was added. CAD, global settings, guide/retainer controls, and geometry were unchanged. Gmsh's ordinary optimization within generation ran; no additional optimization or refinement retry was called. No flow solver was run.

## Actual saved mesh and readback

`fresh-local-surface.msh` is the inherited filename but now contains the actual volume mesh.

SHA-256: `29877cecc2d7d3868ab877867240b0089a3c7e5d2c958f2a96a681f57787f295`.

- 101,802 nodes; 266,705 first-order tetrahedra; 196,926 boundary triangles.
- Runtime 112.78 s; sampled peak RSS 588,255,232 bytes (561 MiB), within 180 s / 2 GiB RSS / 4 GiB address-space limits.
- No logged meshing errors. Gmsh still warns of **173 ill-shaped tetrahedra**, versus 172 in the preceding frozen volume. Warning IDs are not supplied; this count must not be equated to a separate minSICN threshold scan.
- Independent saved-file readback finds zero nonpositive signed tetrahedral volumes; minimum is 0.000014277227 mm³.
- 434,947 internal triangular faces have incidence two; 196,926 exterior faces match the saved surface exactly. No missing, extra, or duplicate boundary triangles.
- All 132 physical surface mappings agree with original source face IDs.
- Every surface's exact coordinate/connectivity fingerprint matches the reviewed 2D mesh. No surface difference is hidden by comparing only counts.
- Both corrected-gap facet-error budgets and positive radial separation bounds remain satisfied. Source CAD hash is unchanged.

These are basic generation, topology, geometry, and provenance checks, not complete engineering verification or CFD acceptance.

## Comparison with the preceding frozen volume

| Measure | Previous | This comparison |
| --- | ---: | ---: |
| Tetrahedra | 230,553 | 266,705 |
| Minimum minSICN | 0.00252843 | 0.00368048 |
| P1 minSICN | 0.02352647 | 0.02923094 |
| Median minSICN | 0.10672855 | 0.11703951 |
| Gmsh ill-shaped warning count | 172 | 173 |
| Volume difference from CAD | −0.685874% | −0.686800% |

The minimum/median minSICN improvement is not a native OpenFOAM quality pass. The warning persists. The exact artifact was handed to the separate native-quality agent for one isolated conversion and checkMesh comparison against the earlier Failed 4 result. Original cases remain frozen. Native outcomes are reported in that separate evidence package; they are not assumed here.

`evidence/surface-identity.json` records exact per-face hashes and physical roles. `volume-readback.json` records signed volumes, incidence, and quality distributions. `verification.json` records the existing cylindrical geometry guards. Raw logs and the monitored resource receipt are retained.
