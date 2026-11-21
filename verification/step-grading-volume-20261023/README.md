# One combined finite-step / finite-torus 3D comparison

One authorized fresh Gmsh 4.15.2 generation completed. This is not native finite-volume quality acceptance, a CFD result or engineering release. No automatic retries, CAD changes, physical-role changes or additional optimization runs were performed. The prior corrected manufactured-solution failure remains separate evidence, not a causal proof or a result on this mesh.

## Actual mesh and independent readback

759,760 tetrahedra; 193,875 unique node tags, all coordinates finite; 259,002 surface triangles. Monitor elapsed 63.7079 seconds and sampled peak RSS 740,536,320 bytes (706.23 MiB). Hard limits were 360 seconds / 2 GiB RSS / 4 GiB address space, one thread. The simple 807,785-cell estimate overpredicted actual count by about 5.95%; actual time and RSS were also below the planning range. Planning counts were not mesh quality requirements.

The saved MSH was reopened. All signed tetrahedron volumes are positive; minimum 0.0000447803 mm³. There are 1,390,019 interior triangle faces with incidence two and 259,002 boundary faces with incidence one. Surface triangles exactly match the tetrahedral boundary; no duplicate surface triangles. All132 physical roles are unchanged. All132 per-face exact coordinate/connectivity fingerprints match the reviewed step2D surface. Node and CAD hashes are recorded; original STEP remains unchanged.

The current tetrahedral volume is 63,707,302.4274 mm³, 0.678371% below CAD volume. This is a comparison, not an accepted volume tolerance. Guide and retainer whole-facet separation guards remain 0.8814641549 and 0.0928263574 mm. Exact surface identity carries forward the verified cone120/124 sampled radial errors 0.0028600626 / 0.0033343040 mm; they remain samples, not complete facet bounds or manufacturing tolerances.

## Mixed quality result and retained warnings

Gmsh reports 166 ill-shaped tetrahedra (no full cell-ID list in that warning), zero meshing errors. No warning was suppressed. minSICN minimum / P1 / P5 / median / P95 / maximum:
0.00417649 / 0.277042 / 0.422886 / 0.701245 / 0.914797 / 0.999992.
The minimum improves from 0.00368048, but P1 drops from 0.312392 and median drops slightly from 0.703711 on the previous cone volume. Do not claim all metrics improved or infer native quality from Gmsh completion.

## Controlled change

The new dimension-3/tag1 law takes the smaller of the previous finite trimmed torus field and the finite short-step field. It was invoked64,388 times; the step term further reduced size5,394 times, exclusively entity3:1. There were58,976 step-farfield calls that returned the previous value exactly. The torus term reduced size57,102 times. Existing curve/surface rules are byte-for-byte the reviewed logic and produced identical current2D geometry. This exact match is to the step2D reference, not a claim that the earlier cone2D farfield triangulation was restored.

## Evidence and next gate

`trial.py`, laws, monitor, original STEP and role rules are included. `check_volume.py`, `verify.py` and `identity.py` independently read the actual saved result; full logs and JSON are in evidence/. The frozen proposal and 2D comparison are included. Root must review this artifact before requesting one independent native check. No native check or CFD was launched by this task.
