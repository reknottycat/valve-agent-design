# Cone-local grading: native OpenFOAM quality evidence

Official Debian OpenFOAM 1912.200626-3+b1, serial dummy Pstream. ONE new conversion/scale/check; no solver, no threshold edits. Source mm mesh SHA ec42b02e7f907abd5297bfdeeb74afa1917730ed986541eb7113fdfd95d1c3ef remains immutable. Export MSH2.2 changes only dimension-3 physical 1→1001; nodes and triangle/tetra connectivity matched, 132 surface roles/counts preserved. transformPoints scale0.001 once, point-set bijection verified before checkMesh.

## Result
Native **Failed 3**, improved from prior Failed 4. Native exit0 is not PASS. Frozen R1 fullcheckPASS prerequisite remains unmet; no engineering release.

| Check | 614334 baseline | 688424 cone candidate |
|---|---:|---:|
| skew | 15 (0.001130%) | 0 (0.000000%) |
| nonortho | 8363 (0.630156%) | 4235 (0.283770%) |
| det | 11091 (1.805370%) | 2799 (0.406581%) |
| weight | 947 (0.071357%) | 229 (0.015344%) |
| ratio | 114 (0.008590%) | 112 (0.007505%) |

Fractions use all cells for determinant, all faces for face counts; not a claim of exact tested-face subset fractions. Max skew 10.1340537→3.6600089; max nonorthogonality89.7807095 unchanged. Positive volumes, face pyramids, face tets and topology checks pass. Total volume0.0637018963656401m³ (prior0.0637018962272279m³); same bounding box. This surface-refined candidate is intentionally not identical to prior boundary triangulation, but its exported copy is identical to its own source.

Native check elapsed11.539s, peak691142656B; all native processes below180s/2GiB guard. Exact absoluteargv/cwd/environment in evidence/preflight.json and per-step JSON. Oldcases untouched; no environment scripts sourced. Initial source-path string replacement pointed to older2D mesh; SHA assertion stopped preflight before any export/native action. Corrected to authorized cone-grading-volume source; only validated chain executed.

All source/export/readback evidence, logs, native badsets, scripts and case retained. Archive excludes installed libraries/packages/binaries.
