# Verification record

2026-10-06, isolated Debian 13 cloud workspace. Status: T04 cloud PARTIAL, product HOLD.

| Check | Result | Evidence |
|---|---|---|
| Complete isolated Python environment, SHA256-locked install | PASS | `evidence/install.log`; 47 package records in `evidence/dependency_metadata.json` |
| CadQuery parametric changes and STEP exchange | PASS | `evidence/capability_matrix.json`, independent cylinder artifacts |
| FreeCAD editable FCStd rebuild/reopen and STEP exchange | PASS | `evidence/freecad_result.json`, independent box artifacts |
| Gmsh SI pipe mesh, physical tag re-read, Jacobians, volume | PASS | 272 nodes, 894 tetrahedra, positive determinants, 1.821% volume error |
| Standard-library/unit regression suite | 20 PASS | `evidence/tests.log` |
| Optimized Python negative control and suite | 20 PASS | `evidence/tests-optimized.log` |
| Original 43-task DAG static validator | PASS | `evidence/manifest.log`; static validation, no task execution |
| Unmodified C0 CAD replay and all six STEP exchanges | EXECUTED | `evidence/c0-cad-replay.log`, `evidence/c0_audit.json` |
| Original C0 geometry/units/contract gates | EXPECTED FAIL, exit 2 | `evidence/audit.log`, `evidence/observed-red.txt` |
| Boolean diagnostic plus explicit STEP unit conversion | PASS for diagnostic connectivity only | `proposals/diagnostic_geometry.json`; no solver functions in generated module |
| OpenFOAM and CalculiX cloud solve | NOT RUN | Executables absent from PATH; adapter status UNAVAILABLE |
| Kinematic constraints, whole-stroke interference, engineering drawing adapter | NOT RUN | Capability status UNTESTED |
| Original source integrity | PASS | All 27 materialized source files match upstream Git blob hashes |
| Shell syntax and authored-file diff whitespace | PASS | `bash -n bootstrap.sh verify.sh`; `git diff --cached --check` |

Aggregate command: `bash runs/20261006/CLOUD/T04/verify.sh` returned 0,
meaning the tools/tests ran and the known bad input was rejected. The product
gate itself returned 2; no product solver or manufacturing release is authorized.
`verify_evidence.py` checks the concrete failure codes, rather than relying only
on the unfrozen baseline's HOLD state.

An independent read-only review reproduced the audit and normal/optimized tests.
It identified and prompted fixes for a copied solver entry point, disabled asserts
under `-O`, STEP metre/mm mislabeling, nonfinite tolerances, volume-preserving
extent drift and generic-HOLD masking. These were fixed before packaging.

All newly authored files are under this CLOUD/T04 directory. C0 input files,
engineering dimensions, main and the existing C1 branch were not modified.
Remote publication and PR creation were not performed by this task.

No user credentials, license changes, paid services, network configuration,
physical equipment actions, manufacturing approval or product certification
are part of this work. The original repository's private distribution boundary
and the dependencies' own licenses are unchanged.
