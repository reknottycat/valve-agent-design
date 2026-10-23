# Controlled finite-torus local volume grading

One authorized fresh 3D comparison added a size law only to volume entity `(3,1)`. The original CAD, all reviewed surface/curve controls, global algorithms, and boundary-extension setting were preserved. The complete pre-existing callback body is byte-identical after the new volume-only guard. No additional optimization retry, threshold change, CAD defeaturing, or CFD solver was used.

## Law and prelaunch validation

`h = min(lc, pi/24 + 0.8*d)` in millimetres, where d is the exact distance to the finite meridian arcs of toroidal CAD faces 119/125 revolved through full azimuth. The law is inactive beyond 31.0863754 mm. No sampled Distance field is used.

The archived proposal describes the finite-arc geometry and resource estimate. Prelaunch unit tests verify arc endpoints, interior points, normal offsets, preservation of smaller existing sizes, millimetre units, non-volume scope, and exact far-field inertness. A counterexample shows why a full-torus distance is wrong: it gives zero on a trimmed-away point where the finite-surface distance is 0.353553 mm.

Actual callback statistics: 54,554 volume calls, 52,627 modified calls on entity `3:1` only, and 1,927 far-field calls unchanged. Modified distances span 0.106956–31.059608 mm, inside the derived cutoff. These logs demonstrate application of the new law; they do not alone certify generated edge sizes.

## Cost and saved artifact

The revised 360 s budget was explicitly approved before launch, with 2 GiB RSS / 4 GiB address-space limits unchanged. Actual runtime was **42.13 s**, sampled peak RSS **605,036,544 bytes (577.01 MiB)**. The earlier additive resource estimate was conservative; runtime did not scale linearly with cell count.

`fresh-local-surface.msh` is an inherited filename containing the actual new volume mesh.

SHA-256: `499f9bf0fa53c8946f826fa1530a92b2e1bc5f73a39866b9944f3f71af3ad208`.

- 152,955 nodes and **614,334 tetrahedra**.
- 196,926 surface triangles, unchanged from the reviewed surface configuration.
- No logged meshing errors; **177 ill-shaped tetrahedra remain in Gmsh's warning**. The warning is not erased or equated to a minSICN threshold.

## Actual saved-file readback

- Zero nonpositive signed tetrahedral volumes; minimum 0.0000438832 mm³.
- 1,130,205 internal faces have incidence two; all 196,926 exterior faces match the stored surface, without missing/extra/duplicate triangles.
- All 132 source face/physical-role mappings pass.
- Every surface coordinate/connectivity fingerprint exactly matches the reviewed 2D mesh. Source CAD hash is unchanged.
- The guide and retainer geometry guards remain unchanged, including radial separation lower bounds 0.8814641549 mm and 0.0928263574 mm.
- Total tetrahedral volume remains 63,701,896.2272 mm³, approximately −0.686800% from CAD volume; surface-preserving volume grading does not cure this geometric approximation difference.

These are limited provenance, geometry, and basic topology checks, not complete engineering verification.

## Quality comparison with surface-only grading

| minSICN statistic | Previous volume | Local volume grading |
| --- | ---: | ---: |
| Minimum | 0.00368048 | 0.00368048 |
| P1 | 0.02923094 | 0.15618137 |
| P5 | 0.04509571 | 0.36688293 |
| Median | 0.11703951 | 0.69021432 |
| P95 | 0.82854262 | 0.91133975 |

The distribution improves substantially, but its minimum remains unchanged and the Gmsh warning persists. These metrics cannot substitute for native finite-volume checks.

## Actual edge-size evidence

`gradation-readback.json` bins actual tetrahedral edges by their midpoint distance to the finite toroidal surfaces. Shared edges are counted once per incident tetrahedron; the distributions are explicitly not unique-edge counts.

- Distance 0.5–1 mm: median edge length 1.7803 → 0.6976 mm.
- Distance 1–2 mm: median edge length 2.8811 → 1.2869 mm.
- Distance 5–10 mm: median edge length 10.3135 → 5.6858 mm.
- Beyond 31.0864 mm: median 23.1422 → 23.1211 mm, P95 41.5353 → 41.4345 mm.

Not every bin or percentile decreases. The far field is similar, not claimed connectivity-identical; global tetrahedral insertion can change far-field cells even when the size callback is inert there. A requested size is not an exact edge-length bound.

## Native-check handoff and stopping condition

The exact saved artifact and readback results were submitted to the parent for review before a single isolated native recheck. No native pass is assumed in this archive. The prior Failed 4 result remains unresolved until the separate native comparison reports all metrics and failing-set counts/fractions using unchanged thresholds. No flow solver is authorized by this diagnostic result.
