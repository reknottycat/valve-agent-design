# One 2D short-step spatial grading comparison

Original CAD, physical roles and prior guide/retainer/plane/cone rules remain unchanged. The new callback first evaluates prior constraints, then applies the reviewed finite-sector distance law to all dim1/dim2 entities; dim3 is unchanged. This is one fresh 2D mesh, not a CFD solution, not an engineering release, and not a rerun of the preceding failed manufactured solve.

## Actual resources and mesh

259,002 surface triangles, +27,882 from 231,120. Elapsed 27.0255 seconds; sampled RSS 185,159,680 bytes (176.58 MiB). No resource cap hit. The 270,000 triangle count is only a cost-review screen. All 388,503 unique surface edges have incidence two; no degenerate surface triangles. CAD source hash and all 132 physical roles are preserved. No 3D generation or optimization retry was executed.

## Target and neighbor measurements

Each of the six short cylindrical sectors now has 928 triangles instead of ten. Their aspect (longest edge divided by shortest altitude) falls from about 462.423 to 5.192125. The 0.05-mm CAD step height is unchanged and is not interpreted as fluid-gap thickness. Plane 36 changes from 78 to 10,446 triangles; maximum aspect falls from 243.486 to 3.85860. Face 5 maximum falls from 93.7492 to 5.96905. These are descriptive improvements, not an acceptance standard.

Mixed local results remain: face 49 maximum aspect rises from 2.48685 to 3.06449; faces 1,4,9,13,17,21,25,29 also have modest maximum-aspect regressions, itemized in summary.json. No face not directly modified by the new face callback has a maximum-aspect increase above 1% in the full 132-face comparison; this descriptive check is not proof of every quality measure being unchanged.

Guide and retainer whole-linear-facet radial separation guards remain 0.8814641549 and 0.0928263574 mm. Cone 120/124 counts, aspect distributions and sampled radial errors remain respectively 0.0028600626 and 0.0033343040 mm. These cone samples are not complete facet-error bounds or manufacturing tolerances.

## Honest locality result

266,346 farfield callback calls returned the previous constrained size exactly. This proves the size-control implementation is local, not that a fresh full surface mesh retains every remote triangle. Exact fingerprints change on 74 faces; rounding coordinates to 1e-9 mm still leaves 70 changed faces, including 28 faces without direct face-size modifications. Some may be affected through shared curves or fresh triangulation; no unverified causal attribution is made. Their full list and count differences are available. Small distant count changes include face81 -4,118 -2,119 +2,122 +2. Do NOT claim farfield mesh identity. Protected geometric guards and quality comparisons were rerun on the actual saved result.

## Reproduction

The frozen reviewed proposal, source STEP, role rules, candidate law and analytic unit tests are included. `trial.py` performs the single 2D trial; `monitor.py` sets explicit cwd/environment and 180-second / 2-GiB RSS limits; trial address space is capped at 4 GiB. `verify.py`, `compare.py`, `identity.py` and `identity_rounded.py` reopen actual meshes without regeneration. All logs and JSON are in evidence/. The old manufactured-solution outcome and this surface improvement must not be combined into a claim of flow or numerical acceptance. Parent review is required before any 3D stage.
