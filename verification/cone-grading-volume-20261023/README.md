# Cone surface grading: bounded 3D comparison

This is one fresh Gmsh 4.15.2 volume generation, not a CFD run or engineering release. Original STEP geometry, physical roles, guide/retainer controls, plane grading and finite trimmed torus volume grading are preserved. The only difference from the last positive volume baseline is the reviewed boundary-complete cone surface/curve law.

## Actual result

- 688,424 tetrahedra; 174,496 nodes; 231,120 surface triangles.
- Monitor elapsed 55.836 seconds; sampled peak RSS 678,932,480 bytes. Limits: 360 seconds, 2 GiB RSS, 4 GiB address space, one thread. The 240,000 surface count is only a cost screen.
- Actual saved MSH was reopened. All signed tetrahedron volumes are positive; minimum 0.0000447803 mm³. All 231,120 boundary triangles exactly match the tetrahedron boundary. Internal faces have incidence two. No duplicate boundary triangles.
- All 132 per-face coordinate/connectivity fingerprints and physical roles exactly match the reviewed cone 2D surface. Source STEP SHA-256 remains unchanged.
- Guide and retainer radial separation guards remain 0.8814641549 mm and 0.0928263574 mm. These are research discretization guards, not manufacturing standards.
- minSICN minimum / P1 / P5 / median / P95: 0.00368048 / 0.312392 / 0.440730 / 0.703711 / 0.915973. The unchanged worst cell and remaining warnings prohibit treating this as a native quality pass.
- Volume is 63,701,896.3656 mm³, 0.686799% below CAD volume. No acceptance tolerance is asserted.

## Preserved limitation

Face 124 sampled radial error increased in the reviewed 2D comparison from 0.0020541316 to 0.0033343040 mm. Exact surface identity carries that observation into this volume. These samples are not a complete facet-error bound, and no tolerance acceptance is implied. Native OpenFOAM quality checking remains a separate next stage subject to parent review. No solver, extra optimization retries, geometry deletion or quality threshold changes were run.

## Reproduction and evidence

`trial.py` combines unchanged `volume_law.py` with reviewed `cone_law.py`. `monitor.py` sets the isolated working directory, explicit vendor path and one-thread environment, and enforces wall/RSS limits. Gmsh address-space limit is set by `trial.py`. `check_volume.py`, `verify.py` and `identity.py` independently reopen the saved actual mesh. `plan.json` records expected surface identity and limitations before launch. `evidence/` contains full logs, raw JSON and copied reviewed 2D preflight/comparison.

The ZIP includes the exact original STEP and role-rule JSON for reproducibility, with hashes; do not publish sensitive engineering source publicly. No vendor binaries or wheels are included.
