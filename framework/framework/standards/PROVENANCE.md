# Source and integration scope

## Adapted interface

The original research API/CLI came from
[`valve-agent-design@5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/standards`](https://github.com/reknottycat/valve-agent-design/tree/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/standards).
The old `standards_adapter.py` Git blob was
`36765a6bf79f70fe7a679b234ae0c5feff827d36`. Its pinned standard source was
`7eda528a8795b8fbd850d6d35ac67e198de5810a`; it was retrieval-only and did not call
the current upstream guards. That history remains in its original commit and is
not copied here as another executable old-source entry point.

## Current production dependencies

The reviewed upstream is
[`standards-kb@19d586bb53cb452325d815313a895a1dfafa868b`](https://github.com/reknottycat/standards-kb/tree/19d586bb53cb452325d815313a895a1dfafa868b).
Every selected dependency's original bytes were compared with its Git blob in
that commit's tree before creating `upstream.lock.json`. The lock's exact SHA256 is
`ca5e450dcc1fa21b00f1eb75ed513ed29e201190ead439818d69833e8d0c1780`.
It is a runtime input contract, not a process log or a full-repository manifest.

The 20 paths and SHA256 values in that file are the authoritative dependency
inventory. They include all 95 records for reference completeness and the current
baseline acceptance card, but no original data or standards table is vendored.
The seven upstream modules are `kb_entries`, `flw001_contract`,
`valve_completion_contract`, `valve_variant_binding`, `source_closure_contract`,
`formula_input_contract` and `acceptance_card`. The execution path does not call
source-closure migration routines or need `pressure_closure_contract`.

The formula metadata check requires installed PyYAML 6.0.3. It is declared as a
trusted runtime dependency, not asserted to be authenticated by upstream hashes.
No package installation was performed for this integration.

## Meaning of the delivered verification

Exact-current-source API and CLI checks establish that this adapter can read the
corrected records and call the reviewed guards, with separate retrieval, source,
calculation-eligibility, project-applicability and release meanings. The locked
card has canonical SHA256
`d9b67c1faa7770c4c683cba94b6800a87b5252b560f16c5fcf51b3a24b511b91`;
its actual result is nine HOLD and 27 unfilled numeric limits. The canonical
record/card digests and exact-file digests are intentionally distinct.

The selected [research readiness consumer](../tools/README.md) now invokes this
API in its existing metadata/case preflight. This is not integration of a candidate
runner, topology validator or full solver orchestration.
No CAD/CFD/FEA, source-PDF verification, original R1 verification, physical input
validation, standard adoption, product acceptance or engineering release follows
from these software checks. Existing history, R1 and source snapshots are not
modified. Future integration into other callers remains a separately scoped task.
