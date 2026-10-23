# AGR1 closed-assembly neutral STEP roundtrip

## Actual result, 2026-10-23 UTC

Pinned existing AGR1 closed-assembly STEP was imported with installed CadQuery 2.7.0 / OCP 7.8.1.1, exported as STEP (`STEPControl_AsIs`, pcurves enabled, precision mode 0), and re-imported. Both representations are kernel-valid and contain 12 solids. Each source solid has a unique matched output solid with equal face, shell, edge and vertex counts, and matching volume, centroid and axis-aligned bounding box within the explicit numerical budgets below. The original 1,274,477 bytes were unchanged.

- Maximum centroid/bbox-coordinate absolute delta: 2.3248958314070478e-11 mm.
- Maximum individual-solid volume absolute delta: 6.044283509254456e-7 mm³.
- Maximum individual-solid volume relative delta: 1.8822727364298914e-13.
- Numerical roundtrip result: passed.
- Output STEP: 1,280,764 bytes; SHA256 `3349e803db2f4ab8ac0bd4584df405d9d1ccb1fc5a10d546a87e329dea62fdcc`.
- Original SHA256 `4720192e2fb9d4c26b9a4b2be521d29508667eda67bd9301a9273df11c570fff`.

Source provenance: [existing AGR1 closed assembly](https://drive.google.com/file/d/1p-jIXdsgX9-I2pPdB0KpcXoexSlqiebu/view). Reuses the original bytes and prior read-only CAD evidence; no new external download, installation, healing operation, Boolean operation, meshing or solver run was requested. Standard import/export kernel processing is used as installed; this is not a guarantee that the CAD library performs no internal representation normalization.

## Numerical contract and limits

Coordinates must agree within 1e-5 mm; each volume within max(1e-3 mm³, 1e-8 × source volume). These are explicit serialization regression thresholds, selected to be small relative to the 600 × 360 × 774 mm assembly, not a manufacturing tolerance, drawing requirement or standard. The observed errors are several orders smaller. Topology counts are exact and every solid must be valid. Matching is a bijection independent of file entity order; symmetric components with equal summaries need not retain named component identity.

These checks establish preservation of these invariants, NOT exact pointwise geometric equivalence. They do not establish assembly names/metadata, native feature history, parameter editability, BOM correspondence, interference/fit, material properties, manufacturing release, SOLIDWORKS import or any other commercial-vendor acceptance. The source is closed AGR1, not the P08 open fluid domain. No CFD or R1 modification is involved. Engineering release remains false.

## Reproduction

Use the already installed CadQuery/OCP environment and the exact existing source. The destination directory must not exist; the runner refuses to reuse it. Source hash and explicit millimetre units are checked before output creation.

    python step_roundtrip.py /path/to/AGR1_closed_assembly.step /new/output/directory --expected-sha256 4720192e2fb9d4c26b9a4b2be521d29508667eda67bd9301a9273df11c570fff --expected-solids 12 --scope 'AGR1 closed assembly; neutral STEP representation exchange only, not P08 fluid domain'

Writes `roundtrip.step` and `result.json`. Exit 0 only if the numerical invariants pass. STEP headers may encode export timestamps, so a fresh export can differ bytewise; preserve that run's output hash rather than requiring equality to this run's hash. Actual comparison metrics and input identity remain the primary checks. A nonfatal installed ezdxf cache-directory warning appeared; no permission escalation was attempted.

    PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -v

11 tests pass: 10 comparator/input-contract tests with synthetic data, and 1 consistency test of the saved actual report. These unit tests do not rerun the actual CAD roundtrip. The separate actual runner execution produced the recorded geometry measurements. Do not count these tests as commercial-tool or engineering acceptance.

## Repository delivery

Minimal proposed path: `framework/providers/step-roundtrip/` with runner, tests, README, result.json, test-results.txt and actual-stderr.txt. Keep the generated STEP in the private working artifact directory; it is not part of this code-only proposal. The current result supports a limited STEP exchange check under ZHE-86; the entire CAD-exchange/engineering task must remain open.
