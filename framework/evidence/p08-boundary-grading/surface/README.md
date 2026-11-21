# Boundary-complete local surface grading: one 2D comparison

This is the single authorized correction to the preceding mixed-result trial. The proposal was frozen before execution and is included as `frozen-proposal.zip`. CAD, global mesh settings, and guide/retainer rules were preserved. No 3D mesh generation, optimization retry, native checkMesh rerun, or CFD solve was performed.

## Change and actual scope

The analytic law h = pi/24 + 0.8*d mm was applied to planar faces 118/126 and **all their uncombined boundary curves**, the full union 280/282/294. The callback takes the minimum with the existing size. Global boundary-size extension remains disabled. Curve 280 has conformal neighbor 117; curves 282/294 meet the original toroidal faces 119/125.

Actual curve counts confirm the intended correction: curve 280 has 101 edges of approximately 7.46397 mm (previously 31 edges of 24.2804 mm); curves 282 and 294 retain 5,316 and 5,052 edges of approximately 0.1309 mm. Callback modification records include all three curves. This does not mean every callback evaluation changed a size.

## Cost and geometric checks

- Total surface triangles: **196,926**, within the 200,000 cost-review screen.
- Elapsed time: **11.43 s**; sampled peak RSS: **176,324,608 bytes (168.16 MiB)**.
- Original source CAD SHA-256 remains `a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787`.
- All **295,389** unique surface edges have incidence two. No degenerate triangles were found by the existing area check.
- Guide radial separation lower bound: **0.8814641549 mm**. Retainer bound: **0.0928263574 mm**. All four previously reviewed cylindrical facet-error budgets remain satisfied.
- Planar target facets have zero z deviation from z = 79 mm. Neighbor 117's vertices remain on radius 120 mm within floating-point precision; this vertex check is not a certificate of full curved-facet approximation error.

## Measured improvement

The ratio below is explicitly longest triangle edge divided by minimum triangle altitude, not an OpenFOAM metric or acceptance standard.

| Face | Triangle count before → after | Median ratio before → after | Maximum ratio before → after |
| --- | --- | --- | --- |
| Neighbor 117 | 124 → 210 | 2.30 → 2.35 | 3.465 → 3.462 |
| Target 118 | 5,565 → 19,697 | 37.77 → 1.77 | 98.81 → 3.71 |
| Target 126 | 5,840 → 23,116 | 9.54 → 1.60 | 106.36 → 3.99 |

Neither target now has a ratio above the descriptive threshold 10. The maximum ratio between adjacent triangles' mean edge lengths changes from 5.32 to 2.05 on face 118 and from 11.72 to 2.14 on face 126. On neighbor 117 it changes from 1.246 to 1.580, without a new extreme aspect tail.

Per-face count changes versus the frozen two-pair baseline are: 117 +86; 118 +14,132; 119 −2; 126 +17,276; 128 +2; 130 +4. These small non-target changes are disclosed; exact frozen connectivity preservation is not claimed. All other face counts match.

The result supports a limited conclusion: **the two targeted planar surface-transition defects improved markedly after boundary-complete size control, while the checked neighbor and earlier gap guards were preserved**. It does not establish good volume tetrahedra, native quality acceptance, flow convergence, or engineering release. The existing failed native volume-quality result remains applicable to the older frozen volume until a separately reviewed volume comparison is made.

## Reusable lesson

A surface size law must be consistent with every uncombined boundary curve, including periodic seams. Curve discretization occurs before surface generation. Applying a law only to the face can leave coarse boundary constraints that the face cannot repair. Audit complete boundary coverage, then inspect conformal neighbor transitions and actual generated geometry. Configuration alone is not verification.

Scripts, raw logs, the cost receipt, source mapping, complete-boundary audits, actual saved surface mesh, `comparison.json`, `verification.json`, and actual curve-edge diagnostics are included. Stop for review before any 3D work or automatic volume-size propagation.
