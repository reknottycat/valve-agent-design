# C3 interface-stage verification

Status: unselected research interfaces. The C2 geometry baseline remains frozen;
no pressure-bearing part selection or manufacturing release is made.

## Evidence

- 21 regression tests pass in normal and optimized Python
- 6 source IDs, 10 dimension groups and 10 drawing structures pass the source/register checks
- 93 C2 archive file hashes remain unchanged
- Three joint coupons contain 43/63/43 parts; packing/gland coupon contains 13 parts
- 172 STEP files, including seven assemblies, were exported and reimported with volume/extents and explicit mm checks
- All 56 joint washer faces and both faces of each annular gasket are fully supported in the modeled coupons
- Packing end coverage is explicitly partial: approximately 95.475% at the housing and 92.731% at the follower; extrusion, compression and leakage acceptance remain unassessed
- At proposed z=388 mm mounting, D40 cylinder has 10 mm nominal hub gap and no measured overlap;
  D54/D70 cylinders overlap the frozen C2 handwheel by 7722.903356/39361.427590mm³
- The D70 vendor flange and all final drive-support/retention geometry remain unmodeled;
  full drive fit is UNASSESSED for every candidate
- Seven disc-withdrawal samples clear the C2 body/seat only under the stated removal assumptions;
  leaving the bonnet or fixed stem yields measured negative-control collisions
- The final technical SVG/PNG was visually inspected after plotting all section-visible fasteners

## Negative controls and corrections

Tests reject assignment of unknown pressure, material or torque; missing unresolved
fields; implicit hardware selection; unit and inherited-datum drift; nonfinite values;
unsafe/duplicate candidate identifiers; washer ring inversion, outer overhang, crossing
the pressure opening and neighbor overlap; overlong packing and oversize gland studs;
and drive envelopes that cannot surround the stem.

The 20 mm stud candidate initially used a 420 mm flange that did not fully support its 45 mm
washer. Its unselected geometric candidate was enlarged to 440 mm; no stress criterion
or acceptance limit was relaxed. No such change was applied to C2.

An independent review confirmed current default support areas, actual drive collisions,
source limits and the lack of pressure/material/preload selection. It identified missing
parameter-negative controls and misleading load/stack labels, which were corrected.
Reported opening area is now only a geometric area, not a determined joint separating load.
The 385 mm gland-nut top and 390 mm stud tip are recorded separately.

## What this does not finish

Material and thread strength, real pressure-temperature/transient loads, effective
sealing diameter, gasket stress, bolt preload/torque, pressure-joint compliance,
packing performance, continuous motion, fatigue, standards compliance and physical
testing are not validated. Smooth thread cylinders are only geometric proxies.
The withdrawal illustration is not a physical maintenance procedure.

GitHub synchronization and solver execution remain paused after the canceled approval.
This stage used already available CAD/drawing tools and performed no new installation,
network write, solver run, purchase or equipment action.
