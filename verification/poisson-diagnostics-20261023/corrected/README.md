# Manufactured Poisson: corrected-scheme FAILURE (not physical CFD)

One fine-mesh solver pilot was run after independent geometry/source checks and genuine native probe comparison. The original full native mesh check still Failed4; R1 physical-flow authorization remains blocked. Source mesh and frozen R1 files unchanged.

## Probe repair (not gate waiver)
Original installed postProcess function objects failed on IOstream `sha1`, both -func and explicit dictionary. Static installed binary inspection traces functionObjectList::read -> dictionary::digest -> in-memory OSHA1stream named sha1. The sha1buf overrides block xsputn but inherits streambuf overflow; this is a possible character-write compatibility defect, not a proven exact triggering instruction. It is not evidence of mesh or filesystem damage. No library fix, compilation, download or install was performed.

Installed setExprFields CLI (documented -create/-expression/-dimension, function objects opt-in) successfully parsed pos(), vol(), fpos() in dry-run, then wrote native fields. Disassembled native field_cellCentre and field_cellVolume call fvMesh::C() and fvMesh::V() directly. Independent comparison: centres2.92e-15m maxabs, volumes4.89e-12 maxrelative, all132 boundary face centres2.22e-16m maxabs. fpos internal field was valid; newly created surface boundary output was unpopulated and explicitly NOT used. Native C boundary was checked instead. All geometry/source/native gates passed before solver.

## Pilot failure
Steady dimensionless T=1+r²/(1m)², DT=1m²/s, source=-6s^-1, uniform1 initial internal field; exact face-centre fixedValue on all132 patches. 614334tet mesh unchanged. Gausslinear corrected, PCG/DIC, no relaxation, 30outer max, 3nonorth solves per outer, single thread, 180s/2GiB watchdog.

Strong explicit correction divergence occurred despite linear residuals ~8e-12. Manually interrupted session with exit130; confirmed execution session closed and log stopped changing. Last complete written outer12: field[-2.408e31,3.428e28] versus exact[1.000227,2.440373]; volume L2error1.5478e29; consecutive-field relativeL2change1.0021; conservative boundary-source imbalance1.5574e20. Outer13 partial flux file has no T and is excluded. No rerun or silent scheme/relaxation change.

Last fully logged timing:68.7CPU/69wall seconds at outer12. This is NOT total runtime. Final wrapper metrics were not written because of interrupt: actual peakRSS and total timing unknown, explicitly null. Watchdog was running; do not replace missing data with estimates. Future wrapper must persist telemetry continuously and handle interrupts in finally.

Independent final corrected-flux residual is huge, consistent with divergent lagged correction. Reconstructed Gauss gradient agrees with native output to~2.02e-13 relative volumeL2. This is not direct matrix extraction and cannot be equated with PCG's lagged linear-system residual. Exact sampled-field truncation residual is also nonzero on this poor-quality mesh. Full metrics and limitations:metrics.json; result:result.json; frozen evidence hashes:corrected-failure-freeze.json.
