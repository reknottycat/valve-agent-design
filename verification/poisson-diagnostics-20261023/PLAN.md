# Bounded manufactured Poisson diagnostic — PLAN ONLY

2026-10-23. No solver, dry-run, mesh modification, compilation, or installation performed. Only exact-version official source retrieval and `laplacianFoam -help` inspection. This is NOT physical CFD, mesh acceptance, manufacturing authorization, or relaxation of R1. R1's full native checkMesh PASS remains unmet (current mesh Failed 4). Structural explanation for some determinant flags does not dispose of the other warnings.

## Verified mechanism and provenance
Installed Debian OpenFOAM 1912 patch200626, LSB label32 scalar64, serial dummy Pstream. Official matching Debian source files saved under `reference/`, with URL/hash manifest `references.json`. Source root https://sources.debian.org/data/main/o/openfoam/1912.200626-3/ . Binary `applications/solvers/basic/laplacianFoam/laplacianFoam.C` solves `fvm::ddt(T) - fvm::laplacian(DT,T) == fvOptions(T)` inside SIMPLE/nonorthogonal loops. `createFields.H` accepts dimensionless T and DT from transportProperties, assigning diffusivity dimensions. Exact-version flange tutorial supplies PCG/DIC and SIMPLE controls; planarPoiseuille tutorial supplies flat fvOptions syntax; SemiImplicitSource.C confirms source units, sign and volume normalization.

Choose L=1 m, DT=1 m²/s, T_exact=1+(x²+y²+z²)/L², gradT_exact=2(x,y,z)/L². Steady equation -div(DT gradT) = S = -6/s. Do NOT use +6. T dimensions [0 0 0 0 0 0 0]; DT [0 2 -1 0 0 0 0]. Source entries are bare scalar values whose dimensions are assigned by the matrix; specific mode avoids total-domain-volume normalization.

constant/transportProperties: `DT 1;` (supported by actual tutorial/createFields).
constant/fvOptions:
```
manufacturedSource
{
    type scalarSemiImplicitSource;
    selectionMode all;
    volumeMode specific;
    injectionRateSuSp { T (-6 0); }
}
```
No timeStart/duration: always active. No coded BC or compiled library needed.

## Preparation and output safety
Use NEW root `/workspace/shared/valve-poisson-diagnostic-20261023`, fail if it already exists (or choose and record a new unique suffix). Cases `fine-corrected`, `coarse-corrected`, `fine-limited05` must each be brand-new. Copy ONLY points, faces, owner, neighbour, boundary and optional zone definition files, with hashes; never copy fields, times, sets, postProcessing, or old system dictionaries. Never source old env.sh (it mutates B). Use Python subprocess with explicit env, cwd and absolute binary + absolute `-case` path. Assert resolved case path is inside NEW root, is not a source, no symlinks, inputs hash-identical, and writable outputs are confined to new root before every tool launch. Write logs/command/env/exit/RSS/time metadata only there. Hash source mesh, R1 original, and relevant source cases before and after.

Fine source: `/workspace/shared/valve-local-volume-grading-native-20261023/case`, 614334 tets. Optional comparison: `/workspace/shared/valve-boundary-grading-native-quality-20261023/case`, 266705 tets, same surface; not systematic uniform refinement, so cannot infer convergence order or perform Richardson extrapolation.

Generate 0/T with internalField uniform 1 (do NOT seed the exact solution), all 132 named patches `type fixedValue; value nonuniform List<scalar> N (...)`. Each boundary face value is T_exact at its triangle centroid Cf, ordered by patch startFace/nFaces. No inlet/outlet/wall physics; all patches get manufactured Dirichlet data. Specify face-centre sample convention, not exact face-averaged quadratic data. Retain patch types, geometry and topology unchanged. Independently reconstruct tetra centres/volumes and oriented triangle centres/area vectors; verify patch coverage, orientation, positive volume and positive outward normal owner-to-face distances. Compare native `writeCellCentres`/`writeCellVolumes` output against Python reconstruction on NEW case only; installed exact-version templates exist in etc/caseDicts/postProcessing/fields. Native C boundary values are face centres (verify count/ordering).

Proposed system dictionaries:
- ddtSchemes default steadyState; gradSchemes default Gauss linear; divSchemes default none; laplacianSchemes default Gauss linear corrected; interpolationSchemes default linear; snGradSchemes default corrected.
- T solver PCG; preconditioner DIC; tolerance 1e-11; relTol 0; maxIter 2000. SIMPLE nNonOrthogonalCorrectors 2. No relaxation factors or residualControl (avoid premature termination based only on a linear residual).
- startFrom startTime; startTime 0; stopAt endTime; endTime 30; deltaT 1; writeControl timeStep; writeInterval 1; purgeWrite 2; writeFormat ascii; writePrecision 17; runTimeModifiable false. Verify exact-version support of any optional control before use. Preserve residual history in log and postprocessed scalar metrics before output purging; retain final two iterations for stabilization.
- Optional sensitivity is a NEW fine case with laplacian and snGrad `limited 0.5`, all other controls fixed. Validate 1912 limitedSnGrad syntax from source before launching it. This is an explicitly labeled scheme-sensitivity case, NOT a fallback quietly substituted for corrected.

Environment values:
```
WM_PROJECT_DIR=/workspace/shared/valve-openfoam-quality-20261023/root/usr/share/openfoam
FOAM_ETC=/workspace/shared/valve-openfoam-quality-20261023/root/usr/share/openfoam/etc
LD_LIBRARY_PATH=/workspace/shared/valve-openfoam-quality-20261023/root/usr/lib/dummy:/workspace/shared/valve-openfoam-quality-20261023/root/usr/lib
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
```
Record executable/library fingerprints and use absolute binary path under root/usr/bin. No -parallel. No old wrapper whose output root is derived from __file__ unless copied/adapted and audited inside NEW root.

## Independent quantities, balance and acceptance labels
Compute e_i=T_i-T_exact(C_i). Report volume-weighted L1=sum(V|e|)/sumV, L2=sqrt(sum(Ve²)/sumV), Linf=max|e|, relative L2 using sqrt(sum(V*T_exact²)/sumV), and amplitude-normalized errors using max(T_exact)-min(T_exact). Report worst cell ID/location, native quality-flag overlap where available without importing sets into case, and near-boundary vs interior error. Report min/max/finite values, source activation over all cells, linear residual/iteration histories and final two-field L2/Linf change. Optionally grad error using written gradTx/y/z; do not confuse this with the conservative balance.

Critical: solver's `flux` output is a VOL VECTOR DT*grad(T), NOT a conservative face flux, and has opposite sign to diffusion flux q=-DT gradT. Do not use it naively for the source balance.

For the all-noncoupled fixedValue boundary, exact-version fixedValue gradient coefficients use patch.deltaCoeffs. fvPatch::delta() projects Cf-Co onto the outward normal; surfaceInterpolation::makeDeltaCoeffs uses reciprocal magnitude, so boundary flux q_f = -DT |Sf| (Tb-To)/abs(n dot(Cf-Co)). Reject nonpositive signed distances; with validated positive distance this equals denominator n dot(Cf-Co). Nonorthogonal boundary correction vectors are ZERO for noncoupled patches, confirmed in source. Sum all 132 patch fluxes. Balance = abs(sum_boundary q - S sumV)/abs(S sumV). Report individual patch and total flux, signed source integral, and analytical flux q_exact,f=-2 DT Cf dot Sf/L². For flat triangular faces this analytical linear-gradient face integral is exact. Check sum q_exact against -6 DT sumV/L² to ~1e-11 relative (subject to serialization precision); failure means geometry/orientation/unit bug, not solver behavior.

Independently reconstruct final finite-volume residual using matching internal linear interpolation weights, nonOrthDeltaCoeffs=1/max(n dot d,0.05|d|), correction vector n-d*nonOrthDeltaCoeffs, and Gauss linear cell gradients from T/BCs; accumulate oriented corrected flux into owner/neighbour cells. Compare gradient reconstruction to native written grad components first. Report r_i=(sum outward q_i)/V_i - S, volume-weighted normalized L1/L2 and max, and the residual evaluated on the exact sampled field (truncation error). Source and boundary-only balance alone cannot prove local convergence. Source-specific scalar-gauss specialization and gradient boundary implementation must be checked when implementing this independent residual, before claiming exact algebraic agreement.

Prospective numerical completion gates, explicitly diagnostic not engineering: no NaN/Inf/FPE, all linear solves converge without maxIter, final linear residual <=1e-10; consecutive-field relative L2 change <=1e-9; conservative balance <=1e-8; independently reconstructed residual agrees with solver discretization and is much smaller than truncation/error scales. Report accuracy magnitudes without inventing an R1 acceptance threshold. If an internal screening criterion is desired, freeze it BEFORE results (e.g. amplitude-normalized L2 <=1%, Linf <=5%); it is only an explicitly proposed diagnostic target, not a sourced engineering criterion. A coarse/fine improvement is useful evidence but absence of improvement is an adverse result, not grounds to hide a mesh. A single mesh run does not close R1's mesh/scheme-sensitivity requirement.

## Cost, bounds and stopping
No cost measurement exists for this solver. Native fine checkMesh previously took 9.23 s and 619 MB RSS; that is only a geometry-processing baseline, not a solver timing forecast. Fine mesh ASCII input ~61 MB. Estimate 0.7–1.5 GiB runtime, allow hard 2 GiB peak process-tree RSS, one serial CPU thread, hard 180 s initial fine pilot. Limit 30 outer iterations *3 nonorth solves and 2000 linear iterations each; abort on FPE, nonfinite field, nonpositive distance, any source/input mismatch or sustained residual growth. Keep only two write times plus metric history; reserve <500 MB per fine case including gradients/flux and independently measured arrays, monitor disk (2 GiB suite cap). If 180 s reached, label INCONCLUSIVE_RESOURCE_BOUND and preserve results; do not claim pass or silently increase budget/change schemes. Request an explicit bounded continuation decision from coordinator.

Only if fine corrected is stable and informative: run one coarse corrected and one fine limited0.5, each separate new dir with same hard 180 s /2 GiB bounds; worst authorized prospective suite compute cap 540 s, excluding preparation. No reruns of already passed representative-domain tests. No additional native full check required merely to re-establish known failed quality, but bind this diagnostic to existing mesh-hashed check evidence. A later physical flow launch still needs original fresh full-check PASS and all other R1 prerequisites.

## Outstanding implementation checks (not blockers to planning)
Validate independent native centre/volume probe output, exact scalar Gauss flux/residual implementation, and optional limitedSnGrad 1912 syntax before any proposed execution. Required current blocker for physical CFD remains full-check FAIL. There is no need for compilation/install to perform this manufactured-source diagnostic.
