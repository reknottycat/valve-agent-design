# Boundary-complete conical transition grading — one 2D comparison

The parent explicitly approved one 2D-only comparison and raised the provisional surface cost screen from 200,000 to **240,000 triangles**, retaining 180 s / 2 GiB RSS / 4 GiB address-space limits. The earlier proposal is archived in `frozen-proposal.zip`; the revised cost authorization does not change geometry or quality criteria.

## Preserved and changed scope

Original CAD, global mesh settings, planar controls, and guide/retainer controls were preserved. No 3D generation, volume-law change, optimization retry, threshold relaxation, or CFD solve occurred. The successful volume law remains a separately frozen artifact for any later reviewed volume experiment.

Only faces 120/124 and their **complete uncombined boundaries** were added to the size callback: curves 283/285/286 and 291/292/293. The straight periodic seam curves 286/293 are included explicitly, not lost through combined-boundary cancellation.

For slant distance s from the lower cone join, the new law is:

`min(existing_lc, pi/24 + 0.8*s, pi/6 + 0.8*(L-s))`, with L = 3.0010320485 mm.

The lower and upper joins are at z = 79.351684160769 and 82.093263356924 mm; slant distance is derived analytically from z. Prelaunch tests verify s in [0,L], both endpoint sizes, complete boundaries, seam adjacency, millimetre units, and exclusion of other entities. `evidence/preflight.json` retains the audit. Existing stricter sizes are preserved by the minimum operation.

## Actual result and resources

- **231,120 surface triangles**, below the revised 240,000 cost screen.
- **16.55 s** elapsed, **181,014,528 bytes (172.63 MiB)** sampled peak RSS.
- All **346,680** unique surface edges have incidence two; no degenerate triangles found by the existing area check.
- Source CAD hash unchanged.
- Guide and retainer radial separation lower bounds remain approximately **0.8814641549 mm** and **0.0928263574 mm**; all four earlier cylindrical facet-error budgets pass.

## Surface quality comparison

Ratios below are longest edge / minimum triangle altitude, not OpenFOAM metrics or acceptance thresholds.

| Face | Triangle count before → after | Median ratio before → after | Maximum ratio before → after |
| --- | --- | --- | --- |
| Cone 120 | 8,037 → 26,577 | 5.88 → 1.62 | 24.37 → 5.87 |
| Cone 124 | 7,633 → 23,321 | 5.90 → 1.68 | 24.12 → 7.69 |

Adjacent toroidal faces 119/121/123/125 retain maximum ratios approximately 2.76–2.94, without a new extreme aspect tail. Full adjacent-triangle edge-size-ratio distributions and slant-distance bands are included in `comparison.json`.

Per-face count changes versus the reviewed boundary-grading surface are limited to: 119 −8; 120 +18,540; 121 −22; 124 +15,688; 125 −4. All other face counts match. Exact non-target connectivity preservation is not claimed.

## Mixed geometry diagnostic and limitations

Cone vertices lie on the analytic CAD radii to approximately 1.3e−11 mm. Samples at vertices, triangle centroids, and edge midpoints give these maximum radial deviations:

- Cone 120: 0.004176 → 0.002860 mm.
- Cone 124: 0.002054 → 0.003334 mm.

These are **sampled values, not full-facet bounds**. Face 124's sampled geometric deviation increased even though triangle aspect improved. No unverified engineering tolerance is introduced to declare this acceptable. Shape quality and geometric approximation are distinct checks.

The result supports a limited conclusion: cone transition triangle shapes improved substantially with complete boundary controls, while checked neighbor shapes and earlier gap guards remain sound. It does not prove native tetrahedral quality, full geometric error acceptance, flow convergence, or engineering release. The existing native Failed 4 status remains open. Stop for review before any 3D experiment.
