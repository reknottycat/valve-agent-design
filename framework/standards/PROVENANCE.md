# Provenance and verification

Adapter implementation references the read-only upstream audit snapshot at
`/workspace/shared/standards-kb-readonly-audit`, specifically the formula schema,
`tools/kb_entries.py`, `tools/evidence_rules.py`, and `tools/kb_fixture.py`.

Expected upstream: `reknottycat/standards-kb`, commit
`7eda528a8795b8fbd850d6d35ac67e198de5810a`.

Synthetic fixture tests are independent of upstream data availability. They test
adapter behavior, not correctness of any standard or actual engineering design.
No upstream file has been modified and no GitHub writes have been performed.

## Actual-record smoke (2026-10-22 UTC)

Auditor materialized exact bytes via read-only GitHub file retrieval with
`encoding=base64` at the pinned commit (not branch HEAD):

- Path: `kb/data/ГОСТ_1536-76.json`
- Length: 72,396 bytes (original CRLF retained)
- SHA256: `a0daf1637344003b2ac3517f19207740116bcb852a6011f845c5b6092f21e8c8`
- Git blob: `9757c84d4fda5360207de363683605159616342a` (auditor independently checked Git blob hash)
- Local snapshot: `/workspace/shared/standards-kb-readonly-audit`
- Retrieval detail: adjacent `kb/data/ГОСТ_1536-76.provenance.json` in that snapshot.

`pinned-gost1536.manifest.json` selects only that file; it is not a manifest of all
93 upstream records. No upstream data is vendored in this adapter directory.

Verification command:

```sh
STANDARDS_KB_SNAPSHOT=/workspace/shared/standards-kb-readonly-audit \
  python -m unittest discover -s tests -v
```

**20 tests passed**, including 19 synthetic boundary tests and one exact-byte
actual-record regression (full original-record equality and evidence retained).
Actual CLI query `--id D-GOST1536-PN063` returned exactly one hit,
UNVERIFIED_CLAUSE / E1, `engineering_release: false`. `py_compile` also passed.
Without the snapshot environment variable the actual-record test is explicitly
skipped, not represented as a successful integration test.

These checks do not independently verify any source clause or release a product.
