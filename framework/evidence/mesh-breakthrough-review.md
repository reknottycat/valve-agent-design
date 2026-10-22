# P08 / R04 readiness and scope correction — 2026-10-22

## Actual new readback
P08 A02 original source supplement was materialized (148700 bytes), SHA256 `5c960d0c93239b6303161f2a513975b031608e61bca0b0203f66ac5095750e5f`, Library `libfile_d85687f1cb7081919dc3214f925b56e9`. No old mesh or solver rerun occurred.

The second P08 attempt was a real useful coarse change: 74 generic face minima changed from L2 to L1 (angle max still L2). At the same surface iteration, cells fell 7,387,114 → 5,430,054 (26.49%). The next split would reach 7,936,523. Allocator failed under 6.5 GiB RLIMIT_AS, before domain retention and before snap. 12 million generation cap was NOT reached. This is not proof of host OOM or CFD divergence. The six L8 wallStep faces exist, but failure happened before all desired levels completed; attributing failure solely to L8 would be unsupported.

**The proposed historical coarse gap sizes already exist in P08 A02**: keySide/keyRoot L6 = 0.1 mm; retainer L7 = 0.05 mm for 6.4 mm background. Recommending those exact values as a new solution would repeat a failed route. wallStep L8 = 0.025 mm resolves a 0.05 mm solid step, not a 0.05 mm flow gap. Neither its resolution nor its removal can be justified from gap-layer arithmetic alone.

`p08_scale_audit.json` gives measured input rule groups, not mesh counts. A/h² is an area proxy, not a volume-cell bound. 4096 belongs to a local metadata/no-CFD comparison, not the whole-valve case. A 12M cap is not a minimum accuracy requirement.

## Which issues genuinely stop progress?
- P08 source setup explicitly emits `solvers {}` and no U/p/physical properties: a mesh setup, not a runnable flow case. Readback cannot establish that no physical specification exists elsewhere. Need source-backed full-valve fluid, temperature/viscosity/density, opening state and flow/pressure boundary conditions. Do not substitute 0.63 MPa design pressure for pressure drop.
- P08 generated result at failure is unretained background, not usable fluid mesh; do not run CFD on it.
- Historical R04 failed determinant/face-weight/volume-ratio checks. These are quality defects requiring localization and repair/verified solver-specific acceptance, not arbitrary cell-count gates. No R04 mesh bytes were downloaded or rechecked this run.
- NSC1 continuation to 960 is already complete for its representative-domain pressure-stability milestone. No repeated calculation required. It is not a full-valve or grid-independence proof.

## Minimal next baseline (not falsely labeled executed)
Preserve whole CAD/flow paths and original case. The next attempt must change the failed route materially, not merely rerun identical dictionaries: inspect retained-domain construction/meshing strategy or available CPU-memory capacity against actual failed allocations, and evaluate feature-specific physical length scales. Do not universally lower L6/L7 or delete regions. An anisotropic/body-fitted alternative is a candidate requiring geometry/path validation, not a demonstrated fix. Select actual whole-valve operating inputs from archived specification before generating flow dictionaries.

Current cloud has Python; `simpleFoam`, `checkMesh`, `gmsh` were not found on PATH. This prevents actual CFD execution here today; no inference about GPU is justified. Missing source-surface and final mesh bytes from this small supplement are separate from missing solver runtime. No large download/build/run was started.

## Reusable implemented tools
`tools/valve_readiness.py`: read-only manifest and case-file preflight. Detects scope-mismatched budget, cap treated as required mesh count, duplicate completed milestone without new objective, unverified physical conditions, design pressure wrongly used as pressure drop, unretained mesh, missing case inputs, empty solvers. Check can inspect without requiring solve readiness. It does not parse included OpenFOAM dictionaries or certify topology/BC correctness.

`tools/valve_candidate.py`: creates a new proposal file exclusively, from original rules + explicit target sizes/rationales. Computes levels from actual background spacing; refuses unknown faces and silent overwrites; leaves original untouched. No automatic coarsening is applied and no real candidate is claimed accepted. Rollback is simply discarding the separate proposal; originals never change.

Run: `python3 -m unittest discover -s tests -v`. 22/22 tests passed. Candidate numerical tests are synthetic; P08 preflight result is against restored actual small source supplement. Its missing mesh file findings describe the supplement, not all Library contents. `evidence/p08_readiness_result.json` records this run.

Example proposal command (after engineering targets are established):
`python3 tools/valve_candidate.py original-rules.json targets.json candidate.json --background-mm 6.4`
Target shape: `{ "wall_FDG_37": {"target_h_mm": 0.05, "rationale": "documented engineering rationale goes here"} }` — example syntax only, not an approved size.

Applicability: readiness v1 is scoped to the archived incompressible `0/U` + `0/p` convention. It must not be applied as a universal gate to compressible, multiphase, restart-time or other OpenFOAM cases without an appropriate adapter. A positive synthetic test proves only metadata/file-presence handling, never OpenFOAM parsing.

Candidate serializer numerical scope: source/proposed refinement levels 0..30 are supported by this small tool; this is an implementation range, not a valve precision requirement or resource authorization. Larger levels require another checked adapter. Nonfinite, boolean, nonpositive and unrepresentable sizes and blank rationales are rejected with ValueError. Source min/max without `level` is accepted.
