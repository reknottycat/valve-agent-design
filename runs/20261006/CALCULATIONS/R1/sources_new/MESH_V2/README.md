# Mesh revalidation v2: fail-closed evidence binding

This is an explicit revision of the acceptance machinery, with fresh quality/identity revalidation of unchanged mesh data. It does not rebuild the scientific mesh or claim that these input bindings existed during the historical v1 run.

## Why this revision was necessary

Independent review found that v1 `finalize_evidence.py` could accept a changed owner file using stale passing logs/reports, then write new current hashes into ACCEPTED. The reviewer demonstrated this by changing the first owner to an out-of-range value only in a temporary copy. The same review independently confirmed that the original delivered mesh, geometric unions, boundaries, and numerical determinant results were correct. Two v1 audit command-line entry points also left a previous PASS output behind after an error.

The v1 archive and all 78 v1 manifest payload files are preserved byte-for-byte. The original code and evidence are included under `provenance/v1_code` and `provenance/v1_evidence`. Those are historical records, not the v2 acceptance entry point. The copies of old ACCEPTED/FAILED files inside `data` are likewise historical input records.

## New acceptance contract

Use only `scripts/finalize_v2.py` with the explicitly pinned manifest SHA256:

`98976d5277a5592284cd20c9dbce095d7c7b845e036417ade65c90e5aff0bd05`

The manifest is `revalidation_manifest.json`. Its pinned digest was communicated before adversarial tests and review. The finalizer does not compute a new expected digest, regenerate source fingerprints, or adopt changed inputs as evidence. It compares current bytes and complete inventories against the frozen values, then copies the already-bound values into its output.

The manifest binds complete `data`, `scripts`, `tests`, and `stage_evidence` directory inventories, including every points/faces/owner/neighbour/boundary/zones/set/system/input file and every current native log and report. Each geometry audit records complete before/after input fingerprints and code fingerprints. Each fresh native check records the executable/environment-script fingerprint, exact invocation, complete before/after case inventory, and output log digest. Mesh/system files must remain unchanged during a native check; only diagnostic-set output is allowed to differ, and its final bytes are sealed. Finalization cross-checks each stage's bound inputs against the same frozen role inputs.

Every public v2 audit/finalizer report is replaced with RUNNING before examining inputs, then PASS or explicit FAIL. A prior output is retained separately as superseded evidence. Errors cannot leave the current output marked PASS. Missing files, inventory additions/removals, replaced logs/reports, or edited code invalidate acceptance. Python optimization does not disable gates.

This is integrity and freshness binding for the audited workflow, not a cryptographic defense against an actor authorized to replace the entire codebase and the externally trusted digest. Keep the pinned digest with the durable revision record.

## Fresh results and scope

New full native checks were performed on separate frozen-data copies:

- Baseline reproduced its nine small-determinant cells and one failed mesh check
- Agglomerated intermediate reproduced its two planar/concave-cell flags and one failed mesh check
- Final candidate newly reported Mesh OK without Failed/FATAL
- Source/native identities and both serialized agglomeration/patch-union audits were recomputed and bound

The mesh remains 90,900 points and 411,099 cells, with the same seven two-tetrahedron unions and two same-cell coplanar wall triangle-pair merges. No coordinate movement, geometry change, quality-threshold relaxation, valve-flow solve, hydraulic-performance claim, or manufacturing approval is included.

Warnings remain: 54 faces above 70 degrees non-orthogonality, maximum 77.471484007812791 degrees. Full native logs preserve all other warnings and environment diagnostics.

## Tests and verification

The suite contains 31 tests: the original 20 scientific/identity tests plus 11 evidence-binding and failure-output tests. Negative cases cover an out-of-range owner, reversed face, old native log, substituted report, missing mesh input, modified diagnostic set, edited audit code, changed manifest, and both audit CLIs with pre-existing PASS outputs. A positive frozen-seal case is included.

The first test-fixture attempt could not create hard links across the workspace and `/tmp` filesystems; its error logs are retained as `verification/tests.first-attempt.*.log`. The test fixtures require a temporary directory on the same filesystem as this package, outside the package root. Set `TMPDIR` to such a sibling directory, then run the full suite normally and with `python -O`. The pipeline/production gate itself does not require hard links. Fixtures mutate copies by atomic replacement and do not alter frozen files.

Current test logs and acceptance results are under `verification`. Independent-review results, when available, are retained there as separate evidence. The v2 finalizer command is:

`python -O scripts/finalize_v2.py --manifest revalidation_manifest.json --manifest-sha256 98976d5277a5592284cd20c9dbce095d7c7b845e036417ade65c90e5aff0bd05 --output /new/output/acceptance.json`

An output PASS binds this exact frozen manifest and data only. Do not reuse it after changing mesh, inputs, code, logs, or reports. For a different mesh or revised gate, perform fresh revalidation into a distinct directory and pin the newly produced digest explicitly.

## Source provenance correction

The v1 reference README incorrectly said the existing solver upstream lock contained the OpenFOAM source archive; it did not. `provenance/official_source_provenance.json` corrects that provenance with the official Debian archive URL, complete archive SHA256, member paths, and member hashes. Both source files were newly compared byte-for-byte against the archive and match the preserved v1 references. The Debian `.dsc` signature was not independently verified. This correction is new evidence, not a backdated change to v1.
