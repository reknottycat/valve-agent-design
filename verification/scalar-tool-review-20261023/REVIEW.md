> Historical preliminary review. Source gaps below are resolved by POISSON-EQUIVALENCE.md and reference/retrieval.json; retained for audit, not the final status.

# Installed scalarTransportFoam: read-only feasibility review

## Evidence boundary
No scalarTransportFoam matching .C/createFields.H source is present in bounded local search. No network was requested (including the previously cancelled source read), no package download, compile or solver execution. Exact installed official binary disassembly is stronger than generic experience for actual relaxation call existence, but is NOT claimed to replace a complete source-level proof of equation/field initialization equivalence.

## Confirmed installed-binary control chain
Debian OpenFOAM1912.200626-3+b1 scalarTransportFoam, SHA in identity.json. Actual main code calls:
- 0x18b01: fv::optionList::source<double>
- 0x18c34: fvm::div<double>
- 0x18c51: fvm::ddt<double>
- 0x19063: fvMatrix<double>::relax()
- 0x19072: fv::optionList::constrain<double>
- after matrix solve machinery, 0x192bb: fv::optionList::correct<double>
The relax() implementation calls solution::relaxEquation and equationRelaxationFactor, then relax(double); a finalIteration branch selects a field name with Final suffix. Hence this is real equation relaxation support, not a claim that merely adding a dictionary to laplacianFoam changes its behavior. Field-only relaxationFactors is not established as called by this solver. Both T and applicable TFinal equation settings need controlled verification to avoid accidental final-step differences.

Binary strings identify reading T, U, transportProperties/DT, reading/calculating phi and SIMPLE control. Dynamic dependencies: libfiniteVolume, libfvOptions, libmeshTools, libsampling, libOpenFOAM, libPstream and standard C/C++ runtime; all are existing installed package artifacts. No turbulence/model library is listed as a direct dependency. This does not prove arbitrary option types require no additional library.

Existing exact-version laplacianFoam.C at /workspace/shared/valve-poisson-plan-20261023/reference/applications/solvers/basic/laplacianFoam/laplacianFoam.C has ddt(T)-laplacian(DT,T)==fvOptions(T), then constrain, solve, correct; no equation/field relaxation call. Existing SemiImplicitSource.C/H is available under the same reference/src/fvOptions tree. Binary confirms scalarTransportFoam's source/constrain/correct integration. Nonzero scalarSemiImplicitSource is therefore a supported candidate, not numerically tested here.

## Conditional same-equation reduction, not yet proven executable configuration
IF the exact solver assembles ddt(T)+div(phi,T)-laplacian(DT,T)==fvOptions(T), with steadyState ddt and identically zero phi on internal AND every boundary face, then transport term and time derivative vanish and the equation is the same Poisson equation. Main binary calls support this candidate but full operator signs, initialization/read precedence of phi/U, required boundary field construction and exact scheme selection are not fully source-verified. Therefore strict equivalence is UNVERIFIED, not promised.
An extra div(phi,T) scheme is required even with zero phi (selection can occur before zero coefficients). Choose an explicit linear scheme only after checking compatible syntax; do not change laplacian, snGrad, grad, interpolation, DT, source sign or scalar boundary values. U=0 alone must NOT be taken as proof phi=0 because an existing read phi may take precedence; all phi entries/dimensions must be verified. No pressure/velocity flow solve is implied.

## What relaxation changes
Equation under-relaxation changes the iterative matrix/diagonal and RHS, hence convergence trajectory and the interpretation of inner linear residuals. For a consistent fixed point, the added diagonal term must be compensated by previous-iterate RHS; exact implementation and finalIteration settings must be checked. It must not change scalar BCs, physical source, diffusion, or solve a transient/artificial equation instead. A small relaxed-system PCG residual is NOT the residual of the unrelaxed original Poisson operator. The independent local residual computation remains mandatory.

## Proposed bounded controlled sequence — NOT executed or authorized by this report
1. First close missing exact-version scalarTransportFoam/createFields.H and fvMatrix relax source evidence through an allowed future source provision; do not bypass cancelled network reading. Verify steadyState implementation and phi construction. Until then do not call the candidate strict-equivalent.
2. Freeze one existing reviewed mesh/case; copy to a fresh diagnostic directory with explicit cwd/env and immutable input manifest. Preserve T initial state/Dirichlet values, DT=1, Su=-6 and Sp=0, exact same nonorthogonal correction scheme (limited0.5 if comparing that run), linear tolerances, iteration schedule and output precision. No remesh or threshold changes.
3. A future authorized A/B comparison must separate solver substitution from relaxation: first scalarTransportFoam with equation relaxation absent, compare original operator coefficients or independently reconstructed unrelaxed residual against laplacianFoam; only then a separately authorized identical copy with one predeclared equation alpha (e.g.0.5). Neither is executed now; do not start a third/fourth case based on this plan.
4. Resource ceiling proposed180s/2GiB per process, single thread, bounded iteration count chosen before execution; no automatic alpha sweep. Stop on nonzero phi, changed BC/source, nonfinite field, unexpected output time or resource guard. Measure original-equation cellwise L2/Linf residual, global source/flux balance, manufactured-solution error, and iterate-change; report plateau/regressions, not inner PCG residual alone.
5. Same fixed-point PDE is necessary but not sufficient: passing manufacturedPoisson remains a diagnostic of a numerical operator, not R1 flow validation, mesh acceptance, real valve CFD, or permission to amend fullcheckPASS.

Recommendation: scalarTransportFoam is a credible already-installed relaxation-capable candidate based on actual binary calls. The strict same-Poisson configuration needs the identified source closure; do not invent a solver framework or claim solved from generic OpenFOAM knowledge.
