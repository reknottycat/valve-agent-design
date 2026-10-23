# 759760-cell controlled manufactured-Poisson comparison: NOT CONVERGED

One new isolated limited0.5 mathematical diagnostic, NOT physicalCFD or engineeringacceptance. Original R1 fullcheck gate still unmet: native mesh Failed3 (lowdet6988,lowweight57,lowratio1); skewcount0/max2.36008,maxnonorth89.418deg/severe4064. Lowdet deterioration versus immediatepriorcandidate is retained, not dismissed.

Sourcecase:/workspace/shared/valve-step-grading-native-20261023/case. OriginalMSH:/workspace/shared/valve-step-grading-volume-20261023/fresh-local-surface.msh, SHA2564e1b4168c9cfdd8d248a54dbbe2411c6fd7661305e479d77f53e3a0f07568a98. Fullsourcecasefiles/MSH/frozenR1 hashchecked before andafter. No sourceedits oroldcasereruns.

## Controls/preflight
Same dimensionless T=1+r²/(1m)²,DT1m²/s,S=-6s^-1,all132patch exactfacecentre Dirichlet,internaluniform1. Newfield generated from newmesh; nooldmeshfields copied. fvSchemes/fvSolution/controlDict/DT/source byteidentical to614334limitedcase (controlled-comparison.json). Gausslinear limited0.5,PCG/DIC tolerance1e-11/relTol0/maxIter2000,3nonorthsolves/outer,30outer,no relaxation. Logonlylimiteddebugswitchsame.

Allgeometry/sign/orientation gates passed; nativeC maxabs7.77e-16m,Vmaxrelative2.46e-12,internal/boundaryfacecentres2.22e-16m. Sourceanalyticalfluxclosurepassed. Nativeprobes use installedpos()/vol()/fpos(); fposunpopulatedboundariesNOTused,allboundaryfacecentresverified throughnativeC. OriginalpostProcessSHA1problem not bypassed by waivingvalidation.

## Terminal metrics (one solve)
30outer/90linear solves,normalEnd/exit0,113.942s wall. PeaksolverRSS539140096bytes; peakincludingPythonmonitor1032736768bytes. Hard180s/2GiB/singlethread bounds respected; repairedfatalbannerfilter,growth/maxIterguardsactive. Everyouter deltaL2/Linf,changingcell andlimiter summaries retained inhistory.json.

| Metric | 614334 prior limited | 759760 candidate |
|---|---:|---:|
| Relative solution L2error |0.0820105%|0.0859590%|
| Global sourceflux relativeimbalance |4.10223e-10|5.33985e-11|
| Final consecutive relativeL2change |6.78086e-7|1.72825e-7|
| Final consecutiveLinfchange |3.54154e-4|7.40696e-4|
| sumabs(Vr)/abs(total source) |1.1877006%|0.9370892%|

Integrated residual improves21.1006%,but isnot negligible; spatialmaxiteratechange worsens andstrict1e-9relativeL2stabilitygatefails by173times. Accuracyerror is slightlyworse; doNOTclaim allmetrics improved. This is comparison oflocalgeometrycontrol candidates includingcone ANDstepmeshchanges,not isolatedstepcausality,formalgridconvergence,oracceptance.

## Local alternating behavior directly observed
Samecell695824 at(0.292852033,0.021110503,0.10605)m hasouter26–30changes approximately−0.00074081,+0.00074468,−0.00074028,+0.00073725,−0.00074070. T alternatesnear1.09675/1.09750. This isobservedlocalalternation; notproof entirefield hasexactperiodiccycle. Volumemeanchangecontinuesfalling whilelocalLinfdoesnot stabilize.

## Local operator residual / limits
Reconstructs installed1912scalar limitedoperator withlambda0.5 andepsilon1e-15,matching savedsource andELFevidence frompriorreport. Nativegradientagreement relativevolumeL2=4.60269e-14. r=-div(DTgradT)-S; R=Vr. LocalvolumeL1=0.05622535s^-1,L2=86.45528s^-1,Linf=845447.57s^-1. IntegratedsumabsR=0.00358196534m³/s=0.9370892%domainabssource0.38224381456m³/s; signedsumR=-2.04113e-11 illustratescancellation. Fullvolume bins/integratednorms inresidual-weighting.json.

Worstlocalcell696150:V1.16457e-10m³,r=-845447.57s^-1,R=-9.84580e-5m³/s,incidentwall_FDG_128,centrez106.025mm. Worstintegratedcell696002:V3.44016e-9m³,absR2.00943e-4m³/s,incidentwall_FDG_71,z171.906mm. Notallresidualis the21.95–22mmstepband.

StillNO independentnativeperface limitedflux/TEqn matrixexport. Gradientstageandglobalidentitychecked,but reconstructednonlinearresidual isNOTsameas historical laggedPCGresidual. Originalanalytictruncationresidual isreportedseparately. Boundarybalance alone doesnotprove localconvergence. No underrelaxationdictionary placebo: savedlaplacianFoam.C hasneitherTEqn.relax()norT.relax().

One30outercomparison stopped asauthorized. Noextension/newsolvers/compile/install. Result remains NOT_CONVERGED_MANUFACTURED_DIAGNOSTIC; alloriginalR1/physicalgatesunchanged.
