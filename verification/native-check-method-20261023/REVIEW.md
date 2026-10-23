# Native1912 diagnostic interpretation — read-only

## Exact implementation
Debian OpenFOAM1912.200626-3 sources retrieved from https://sources.debian.org/data/main/o/openfoam/1912.200626-3/ . Files retained locally.

primitiveMeshTools.C lines456–558: for each3D cell, use only internalOrCoupledFace. aBar = sum(|Sf|)/N; A = sum[(Sf/aBar) outer (Sf/aBar)]; D=abs(det(A))/8. No eligiblefaces gives0. 2Daddsunit in missingdirection;1Dreturns1. polyMeshCheck.C406–480 obtainseligiblefaces via syncTools::getInternalOrCoupledFaces; warnDet=1e−3. This is area-vector connectivity metric, NOT signedcellvolume, tetrahedralJacobian, nor the determinant of a PDEmatrix assembled with actual BCs.

3Dtet with≥2noncoupled boundaryfaces has≤2eligiblefaces,rank(A)≤2,so D≈0 by construction. Physicalwall/inlet/outletBC contributions are not included; changing genericpatch towall does not make itcoupled. Thus avalidpositiveboundarytet may failthisdiagnostic even though its eventualdiscretization is not proven singular. Conversely BCs do not magically guarantee suitability.

Actual614334tet mesh: all cells byboundaryfacecount0/1/2 =417886/195970/478. BadD11091 split715/9898/478. Every2boundaryface tetflagged, as predicted. Only478/11091(4.31%) explained by thisnecessaryrankargument;715pureinterior and9898singleboundaryflagged still need anisotropy/connectivity/stencilanalysis. Do notdismiss all11091.

## Default vs expanded check
checkGeometry.C623,645,690 default includes volumes/nonorthogonality/skewness; -allGeometry adds face-tetdecomposition, lengths/angles/flatness, determinant(line862), concavecells, weights(line902,.05), volratio(line923,.01). Someinformationalextras deliberately do not incrementnoFailedChecks. In current tetra results, Failed4 =skew(default)+D/weight/ratio(expanded). Staticcallpath implies defaultgeometry wouldretain skewfailure; no defaultnative rerun performed and no pass claim. All historicalFailed4 logs stay intact.

polyMeshTools.C175–229: w=min(dOwn,dNei)/(dOwn+dNei+VSMALL), d=abs(Sf dot (Cf−Cc)). Coupledneighbors handled; noncoupled boundarydefaults1. Lines233–279: r=min(Vo,Vn)/(max(Vo,Vn)+VSMALL); noncoupledboundarydefaults1. Therefore lowweight/ratio here are internalface interpolation/size-transition indicators, not boundarymissing-contribution artifacts. Actualeffect depends on finitevolumegradient/interpolation/limiting/nonorthogonalcorrection, PDE,flow andstencil. Skewness is actualgeometricinterpolationoffset; BC andschemes affectconsequences, not whetheroffset exists. Near90degree nonorthogonality is astrongrisk even when reportedundererrorcutoff.

## Governance correction
No officialsource establishes zero-allGeometryfailures as auniversalengineeringlaw for alltetraCFD. Treating that as anabsoluteproductrequirement without solver/BC/accuracyrequirements was anagent-selectedconservativegate, not user/standard requirement. Correctinterpretation does NOT lowerthresholds, erasefailures, authorizeunvalidatedsolveror excuseactualnegativevolume dualcandidate. Preserve native numbers and distinguish hard invalidity from riskindicators.

## Next verification, no execution here
1 Freeze current614334mesh,retainAllGeometrylogsandnegative-dualrejection.
2 Separate478structuralboundaryrankcells fromremaining10613lowDcells. Overlayactual15skew947weight114ratiodefects withthroats/BC/monitorplanes; report overlaps,not sums.
3 Define intendedphysicalproblem/BC/fluid/Reynoldsrange/turbulenceandwallresolution/targetQoI(pressureloss,flow,K) and numericalscheme beforedecidingacceptance. Currentgenericpatchqualitycase has no physicalBCs.
4 Inspectlocalstencilrank including intendedboundaryconstraints and applicablegradientreconstruction. Use manufacturedboundedlinearfield/gradientaccuracy test or representativeknownsolution only after scopeapproval; do not require globalrefinement toremove everyDzero by construction.
5 Addressactualextremeskew andinadequatephysicalresolution locally. Alternatecontrolvolumetopology must pass positivevolume/geometrychecks; priorpolyDual0 failedthis, so notapprovedroute.
6 Onlyafterexplicitnumericalreview authorizeboundedsolververification: conservation,residual+QoIstability,sensitivitytowall/BC/scheme andmeshuncertainty/referencevalidation. A solver that runs is not engineeringrelease; neither defaultcheck norallGeometry alone establishes accuracy.
