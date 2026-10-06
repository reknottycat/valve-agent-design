# C4 verification scope

The user selected the unsuffixed base and authorized analogous-data study input selection.
C4 records 0.63MPa(g), seawater, −2..50°C as explicit research assumptions. It does not
replace an original manufacturer rating, operating envelope, material certification or proof-test procedure.

## Executed

- Existing CadQuery/OCP imported six frozen C2 STEP assets, each checked for millimetres, BREP validity and source hash
- Two closed poses each retained two unambiguous pressure compartments
- Face-face pressure-area extraction matched independently calculated projected areas
- Disc-plus-stem area transfer between poses was checked; both pressure ports remain separate
- 20 pressure cases include four expected-red free-disc/forward-pressure cases under a pressure-only unilateral-contact model
- 12 screw/collar friction scenarios satisfy an independent efficiency/work identity
- Nine gasket-boundary scenarios retain actual bolt force and preload as unknown
- Nine seawater temperature/salinity points match rounded primary tables; −2°C and non-reference-pressure property calls are rejected
- 47 regression tests pass in normal and optimized Python; failure injection invalidates stale success
- Unified verify_study.sh passed; T04/C2/C3's 360 frozen file hashes remained unchanged
- The final technical PNG was visually inspected; SVG is also supplied

## Explicit limits

Gauge values represent increments relative to an assumed common external atmospheric reference.
Contact regions are dry with no fluid-pressure penetration; atmospheric/contact prestress, gravity,
seal preload, friction, elasticity, leakage and dynamics are not solved. Two contact reactions in
closed geometry cannot be inferred uniquely from the net pressure resultant. No negative seat
reaction is treated as a permissible static unilateral contact.

Screw calculations use nominal analogous thread geometry and hypothetical friction. The reported
hydraulic load component excludes missing actuator loads; static self-lock screening is not a
vibration-retention qualification. Bearing/collar and effective joint-pressure diameters remain scenarios.
Reference-pressure seawater properties are not yet pressure-corrected or valid at the −2°C endpoint.

This C4 stage performed no installation, OpenFOAM/CalculiX solve, physical operation, remote write or purchase.
Separately authorized solver-capability benchmarks and repository synchronization are tracked outside C4;
a benchmark pass is not an actual-valve result. Product strength, pressure rating, proof test, leakage and manufacture remain HOLD.
The existing C2/C3 frozen stages and their original archives are unchanged.

Independent review also reproduced the negative-density dataset and empty STEP-provenance attacks
in isolated copies. Both now fail closed, including after refreshing plot-source hashes. Primary
catalog page pixels, nominal thread dimensions and screw-efficiency identity were independently checked.
