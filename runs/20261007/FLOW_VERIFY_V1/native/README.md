# Native preflight, target OpenCFD/ESI OpenFOAM v1912

This program has **not been compiled or run in the preparation environment**.
The environment has no OpenFOAM runtime or development toolchain. Python
syntax and the blocked-runtime exit path are separate from native validation.

From a terminal with the v1912 **double precision** environment already sourced:

```bash
python /ABS/PACKAGE/native_gate.py --case /ABS/FLOW_CASE --output /ABS/NEW_NATIVE_EVIDENCE
```

The output directory must not exist and must be outside the input case. The
runner copies the native source into its output, builds there using `wmake`,
and places the executable in its own `bin/`. It never installs an executable
into the user's OpenFOAM application directory. It requires Python and NumPy.
The caller must require both exit code 0 and `report.json: status=PASS`.

## What this gate actually checks

1. A serial native probe exports OpenFOAM `C`, `Cf`, `Sf`, and `V`, with cell,
   face and boundary-patch indices, on a copy of the actual valve mesh.
2. Python independently reconstructs the triangular/planar merged-quad
   geometry with oriented polygon fans and signed pyramids. It compares
   all cell/face values and exact index mapping to the native exports.
3. Two further copies of that **same real valve mesh** solve the manufactured
   equation `T=x²+y²+z²`, `Laplacian(T)=6`, from a zero internal field.
   Every patch is Dirichlet; the C++ executable sets its exact value from
   native `Cf`. `T` has dimensions m²; the source is dimensionless 6.
   These are mathematical verification conditions, **not additional physical
   valve operating conditions**. The normal physical flow case is untouched.
4. The two Laplacian/snGrad corrections are `corrected` and
   `limited corrected 0.5`. Each rebuild updates the explicit correction.
   This is **single-mesh scheme sensitivity**, not a refinement study or
   evidence of mesh convergence.

## Diagnostic thresholds fixed before a native run

These are prospective diagnostic gates for this package, not established
engineering acceptance limits. A failure blocks the physical flow runner;
it does not authorize silently loosening a threshold.

| Check | Maximum |
|---|---:|
| Native vs independent C / Cf | abs 1e-11 m + relative 5e-10 |
| Native vs independent Sf components | abs 2e-14 m² + relative 5e-10 |
| Native vs independent V | abs 1e-22 m³ + relative 1e-9 |
| Manufactured volume-weighted relative L2 error | 0.02 |
| Manufactured Linf / maximum exact T | 0.10 |
| Scheme difference, volume-weighted relative L2 | 0.02 |
| Scheme difference, Linf / maximum exact T | 0.05 |
| Updated-matrix initial residual | 1e-8 |
| Linear final residual | 1e-10 |
| Maximum field update / maximum exact T | 1e-10 |
| Correction sweeps | 4000 |

The linear solver is PCG/DIC, tolerance 1e-12, relTol 0, maxIter 5000.
Inner residual alone cannot pass: all last-row correction criteria must pass.
The Python audit independently recalculates field error from the native C.

## Evidence retained

`build.log`, the isolated executable, `probe.log`, all CSV geometry exports,
`independent_geometry.npz`, `corrected.log`, `limited05.log`, per-case
`iterations.csv`, `manufactured_field.csv`, and the raw OpenFOAM final `1/T`
are retained. `report.json` contains their SHA-256 values, source mesh hashes
before and after, executable/source hashes, metrics and thresholds. Every
probe/solve mesh must match the untouched source mesh by byte hash.

Exit 2 / `BLOCKED` identifies missing sourced v1912 development runtime.
Any compile, solve, comparison, evidence or threshold failure exits nonzero.
Absent native results remain absent. Successful execution means only that
this geometry/MMS gate passed. It cannot certify physical valve performance,
contact, joint adequacy, pressure integrity or manufacturing release.

## API/source verification limit

Official v1912 documentation/source retrieval was attempted on 2026-10-07;
those endpoints returned 403 or were inaccessible to the available browsing
tool. Consequently **exact v1912 API compatibility is unverified until the
included source actually compiles with that toolchain**. A successful search
for newer official API references is not treated as a v1912 compile test.
The recorded URLs/status are in `source_api_checks.json`.
