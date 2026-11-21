# Read-only assessment after frozen comparison

## History: plateau with fluctuations, not proven periodic cycle
Initial residual mean across each outer's three solves drops quickly early. Outer11–20mean=2.31784e-5;21–30mean=2.10063e-5; late range1.95640e-5–2.23841e-5. The fitted late log-slope is only-0.008469perouter and is not a justified forecast for field-change convergence. Exact-errorL2 last10 spans0.00113804891–0.00113806460 (relative range1.38e-5), with4directionchanges. Error amplitude is essentially plateaued; even stable exact-error magnitude does not mean the solution stops changing.

Only29/30fullT fields remain; history has perouter Tmin/Tmax/L2error, not signed percell trajectories or delta norms. Therefore we cannot distinguish definitively an asymptotically weak decay, quasiperiodic limiter switching, or a fixed-amplitude local cycle. Do NOT call a periodic cycle proved.

Last29→30: relativeL2change6.78086e-7 (678times frozen1e-9gate), maxchange3.54154e-4 at cell601449 centre(0.41847978,-0.00060877,0.02066593)m. Top30largest-change cell data are in history-analysis.json. In z21.95–22mm band:105cells,0.0256224%domainvolume,0.501424%total V*deltaT²,2of top30absolute-changecells,0of top30energy-contributioncells. Largest band change2.24385e-4. This band contains corrected failure's worstcell487529, but it does not dominate the limited run's current iteration-change energy. Entire analysis is the614334mesh; no inference of688424solution behavior.

## Is a checkpoint extension justified?
Not as a likely verification pass: the initial residual tail is weakly improving/fluctuating and strict stability is678times above target. Blindly spending another30outer merely to hope for a pass is poorly supported. A short, explicitly exploratory checkpoint extension could scientifically test decay versus persistent local oscillation ONLY after diagnosing the local limited residual, and should persist everyouter deltaL2/Linf, signed T at fixed topchangingcells and limiter statistics; preserve source, BC, scheme, relaxations and fixedpoint iteration controls. A stopping condition should classify the tail, not silently lower the gate. No third solve or extension has been performed.

## Limited local operator: established exact-version mechanics
`limited-correction-disassembly.txt` is the installed scalar limitedSnGrad::correction implementation. Constructor evidence saved in comparison directory confirms numeric0.5 selects corrected base. Saved exact1912 source already establishes Gausslinear gradients/interpolation, stabilized nonorth delta, and zero correction for noncoupled boundaries.

Inspection of installed binary at0x209b5e0 confirms:
- obtain base corrected correction c_f;
- form denominator (1-lambda)*abs(c_f)+epsilon;
- obtain the UNCORRECTED two-point snGrad through static snGrad(field,nonOrthDeltaCoeffs,...) (call0x209b86f);
- numerator lambda*abs(a_f);
- divide and min with1 (calls0x209b904 and0x209b92e).
Constants read directly from matching ELF.rodata:0x23666b0=1e-15,0x23666c8=1.0. Thus for scalar T, L_f=min(lambda*|a_f|/((1-lambda)*|c_f|+1e-15),1), lambda=0.5. The small value carries snGrad dimensions in the native dimensioned expression. Final correction is L_f*c_f. This is specific evidence from installed1912binary, not a substituted newer API.

Internal-face definitions:
d=Cn-Co; n=Sf/|Sf|; D=1/max(n·d,0.05|d|); a=D*(Tn-To); c=(n-D*d)·[w*gradTo+(1-w)*gradTn], with the exact Gausslinear gradient and native interpolation weights. Diffusive oriented flux q=-DT*|Sf|*(a+L*c). Boundary fixedValue flux remains q=-DT*|Sf|*(Tb-To)/abs(n·(Cf-Co)); noncoupled correction zero. Accumulate owner positive/neighbour negative; r_i=sum(outward q_i)/Vi-S. Final field local residual is the nonlinear fixedpoint residual, distinct from each lagged PCG linear residual.

## What remains before calling that residual verified
1. Implement the above final-field limiter/operator reconstruction using independently verified nativegeometry and fixed BC; do NOT reuse corrected c without limiter, nor stored volume-vector `flux`.
2. Recheck reconstructed Gauss gradients against native gradTx/y/z on field30, including precision/field ordering and geometric coefficient handling.
3. Validate per-face limited flux/limiter against a native operator evaluation or matching source/test harness. Existing setExprFields parser does NOT support snGrad(T); its failed optional probe cannot validate this. Do not claim a native matrix/flux comparison was done. Any newly compiled helper or downloaded source is outside current execution scope and needs separate authorization.
4. Report volume-weighted local residual L1/L2/Linf normalized by|S|=6, worstcells, face limiter distribution and overlap with largest deltaT. Check that sum(V*r) equals reconstructed boundaryflux-source, but this identity alone is necessary, not sufficient: cancellation hides local error.
5. Independently evaluate sampled-exact T on the SAME limited discrete operator as truncation-error reference, separate from numerical iteration residual and solution error.
6. To reproduce the printed PCG residual exactly would require each nonorthogonal solve's lagged correction/RHS and OpenFOAM normalization. Only final outer29/30fields exist; those historical linear matrices cannot be reconstructed exactly from finalfields alone. Do not equate final nonlinear residual with PCGfinal~1e-11.

No local limited residual numbers are reported as verified. Frozen limitedresult remains BOUNDED_LIMITED05_BUT_STABILITY_GATE_UNMET, corrected remains divergent, and R1 physicalCFD/fullcheck gates remain unmet.
