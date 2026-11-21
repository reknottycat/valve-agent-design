# Final read-only scientific finding

**The limited0.5 pilot is NOT a converged manufactured-Poisson verification.** Its relative solution L2error0.0820% and signed sourcebalance4.10e-10 are insufficient: the savedfield has a significant reconstructed nonlinear local residual, and measured iteratechange exceeds the frozen stabilitygate. Original R1 fullcheck prerequisite remains Failed4 and physicalCFD/engineering acceptance remains blocked.

## Integrated versus volume-normalized residual
For r_i=(sum outwardfaceq)/V_i-S and R_i=V_i*r_i, S=-6s^-1:
- sum|R_i|=0.004539526713m³/s, **1.18770057%** of absolute domainsource0.3822113774m³/s.
- Signed sumR_i=-1.567918e-10m³/s; positive/negative local errors cancel. Independent globalflux-source identity agrees to6.52e-17m³/s.
- Discrete integratedvector L2=5.964794e-4m³/s; Linf=2.812550e-4m³/s.
- Volumeweighted localr L1=0.071262s^-1,L2=106.6734s^-1,Linf=2.789605e6s^-1. The large lasttwo are amplified by smallvolumes and must not be reported without integratedvalues.

Worstlocalr cell532976:V2.427206e-11m³,|R|6.770945e-5m³/s (0.017715%total source),incidentwall_FDG_102,z103.925mm. WorstintegratedR cell477365:V2.363343e-9m³,|R|2.812550e-4m³/s (0.073586%total source),incidentwall_FDG_36/39,z21.9625mm. Alltopcell volumes and bothnorms in residual-weighting.json.

### Contribution to sum|R| by cellvolume
- V<1e-12m³:0.01656%.
- 1e-12<=V<1e-10:14.75236%.
- 1e-10<=V<1e-8:78.67819%.
- 1e-8<=V<1e-6:4.95582%.
- V>=1e-6:1.59707%.
Boundary-adjacent cells account69.6438%,interior30.3562% ofsum|R|. Patchnames are exact incident boundarylabels; CADroles are NOT inferred. The thin21.95–22mm band does not explain allerror (12.6309%ofV*r²); worstlocalcell is elsewhere.

## Evidence quality and remaining limitation
Exact installed1912 scalar limitedSnGrad implementation was inspected, including coefficientparsing, nonOrthDeltaCoeffs, staticuncorrectednormalgradient, lambda/(1-lambda)ratio,1e-15regularizer,minwith1,andfinal correctionmultiplication. Saved exactversionsource covers Gaussgradient/interpolation,boundarydelta,zero noncoupledcorrection,andLaplacian assembly. No newerformula was assumed.

Independent Gaussgradient matches actual solver-written nativegradTx/y/z at relativevolumeL2 **4.62339e-14**. Replacing it with nativegradient changes residualvolumeL2 by only1.04333e-9absolute. Native expressiongrad(T)was tried only onNEWpostprocessingcopy and is unsupported in1912parser; failedlogretained. No claimed output from that expression.

**Still missing:** independent native perface limitedflux or TEqn matrixexport. Thus these are implementation-matched reconstructed residuals, cross-checked at thegradientstage and globalconservationidentity, not a direct nativefaceoperator comparison. Historical laggedsubiteration RHS/matrices were notsaved; PCGnormalizedfinalresiduals~1e-11 cannot be equated to the finalfield nonlinearresidual. No thirdsolve, compile,install,download,or sourcecasechange occurred.

## What the tail suggests, without overstating cause
Outer21–30meaninitialresidual2.10e-5 versus11–20mean2.32e-5; exacterror essentiallyplateaus and changesdirection. Onlylast2fullfields exist, so a periodiccycle is NOT proved. From29→30,286internalfaces switch limited/unlimitedstatus,485faces change limiter by>0.1; maxlimiterchange0.9239. At worstlocalresidualcell itsincident internalfaces reach89.135deg nonorthogonality andmaxlimiterchange0.6024. This supports investigating coupledgeometricconditioning and explicitcorrection fixedpointbehavior, not claiming a universalsoftwarebug or designbug.

## Actionable priority / no execution requested
1. Prioritize independently identified extreme geometricanisotropy; retain control of source,BC,scheme,initialfield,solver andmetrics for a later improvedmeshcomparison only if nativequality materiallyimproves. This is not a fullcheckPASS waiver.
2. Keep linear-tolerancenormalization separate from nonlinear correction: allinner solves meettheir tolerance while finalstate localresidual anddeltaT do not. A tighterlinear tolerance alone is not currently justified as the likelycure; matrix/fluxexport is the remaining nativecrosscheck.
3. Preserve perouterdeltaL2/Linf andsignedtopcell/limiterhistories in any separatelyapproved futurediagnostic; distinguish decay frompersistentvariation instead ofextending blindly.
4. **Do not add ineffective relaxationFactors.** Matching laplacianFoam.C calls neitherTEqn.relax()norT.relax(); dictionaryrelaxation entrieswouldnot implementunder-relaxation. No newsolverframework or simultaneous mesh/scheme/relaxationtuning is proposed.

Currentpriority is geometrydiagnosis, not an additional solvertuningrun. This report supplements, doesnotrewrite,the frozenfailure/limitedarchives.
