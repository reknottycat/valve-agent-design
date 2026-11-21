# Controlled limited0.5 scheme comparison — bounded, NOT fully verified

Same 614334tet P08 mesh, dimensionless manufactured T=1+r²/(1m)², DT=1m²/s, source=-6s^-1, uniform1 internal start, exact fixedValue on132patches. This is a mathematical diagnostic, NOT physical flow or engineering acceptance. Original R1 full native mesh PASS remains unmet.

Only numerical scheme change versus the corrected failure: laplacian Gauss linear limited0.5 and snGrad limited0.5. fvSolution/controlDict/source/T0 identical; no relaxation/mesh change. `control-comparison.json`, input hashes, native probe binding and dictionary SHA prove identity. `-debug-switch limited=1` is log-only. Installed constructor disassembly proves numeric0.5 accepts the corrected base scheme and bounds coefficient in[0,1]. No current-version API was substituted and no compilation/install/download performed.

Optional setExprFields snGrad(T) preflight was unsupported in this1912 parser; failed log retained, no solver ran then. Required native C/V/allpatch-centre probe had already genuinely passed on byte-identical mesh via supported pos()/vol() fields. A first limited solver startup was stopped before any equation due to watchdog matching its normal FPE-trapping banner. This monitor error was fixed/unit-tested; aborted startup and unchanged case identity retained. Exactly one actual limited mathematical solve followed; no additional solve or parameter tuning.

## Result
Completed30outer/90linear solves, exit0, normalEnd,89.957s wall,448507904bytes peak solver-process-tree RSS. Guard180s/2GiB and sustained field-growth guard active with continuously saved telemetry/history. Geometry volume/source-sign/orientation checks pass; original source files and R1 hashes unchanged.

Volume weighted error L1=8.09094e-4, L2=1.13806e-3, Linf=9.05417e-3. RelativeL2=0.0820105%; amplitude-normalizedL2=0.0790239%, Linf=0.628698%. These are diagnostic measurements, not an engineering acceptance threshold.

T range[1.0009016451,2.4393911114], exact sampled range[1.0002270427,2.4403725433]. Conservative boundary flux=-0.3822113775201535 versus source=-0.38221137736336175; relativeimbalance4.10223e-10, below1e-8 target. FixedValue/noncoupled boundary flux uses the same verified native formula as corrected; solver's volume-vector `flux` is not used for balance.

**Strict stability gate FAIL:** consecutive29→30relativeL2change6.78086e-7 exceeds frozen1e-9; Linfchange3.54154e-4. Initial linear residuals remain~2e-5 though final residuals<1e-10. Worst-changing cell601449 centre(0.41847978,-0.00060877,0.02066593)m; worst exact-error cell42152 centre(1.13394900,-0.08136067,-0.02155865)m.

Local limited-operator residual is UNKNOWN: no independent reconstruction or native matrix export. Do not apply corrected-scheme residual to this limited nonlinear operator. Boundary conservation and low PCG residual do not establish local convergence. Overall numerical verification NOT PASSED. No third numerical run and no extension beyond30outer performed.

Evidence: result.json, metrics.json, pilot.json/log, history.json, native-probe-comparison.json (copied hash-bound proof), source-hashes-before/after.json, startup-abort-*, watchdog-tests.txt, limitedSnGrad-installed-constructor.txt.
