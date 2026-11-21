# Valve standards research adapter

Small, standard-library-only, **read-only** adapter for selected records from
[`reknottycat/standards-kb`](https://github.com/reknottycat/standards-kb/tree/7eda528a8795b8fbd850d6d35ac67e198de5810a),
pinned to `7eda528a8795b8fbd850d6d35ac67e198de5810a`. No network, writes, formula
execution, ontology dependency, new standards database, or engineering rules.

## Contract

- Reads every manifest-listed file before returning any record. Missing files,
  malformed JSON, duplicate JSON keys, invalid/missing IDs or evidence fields,
  duplicate IDs across files, empty record files, wrong repository/commit,
  checksum mismatch, and escaped paths fail closed. CLI exits **2**, writes an
  error to stderr and emits no successful/partial stdout response.
- Formula/parameter files are arrays; data files are `{"entries": [...]}`.
- Every hit contains the **entire original record**, including
  `evidence.status`, `evidence.grade`, `source`, `applicability` when present,
  usage limitations and any additional fields. No status is upgraded and missing
  applicability is not invented. Returned copies cannot mutate the loaded data.
- Every hit includes repository, commit, path, ID, exact-file SHA256 and canonical
  record SHA256 (UTF-8, sorted keys, compact JSON, non-ASCII retained). Response
  also includes manifest SHA256. File hashes are over original bytes, not pretty
  printed/re-serialized content.
- All E0–E3 grades and original clause states remain **research retrievable**.
  This means inspectable, not reliable for use. `CONFLICT` / `SUPERSEDED` records
  remain visible for research with their original warnings/status.
- `engineering_release` is **always false**, and `engineering_acceptance` is
  **NOT_ASSESSED**, including zero hits and failures. A source's nested fields are
  untrusted upstream content, not adapter decisions. Even source declarations of
  release, VERIFIED_CLAUSE, E3, query success, or validator exit 0 cannot override
  the adapter's decision. No engineering release method exists.

## Usage

Python 3.9+ (tested using Python 3.12), no dependencies:

```sh
python -m unittest discover -s tests -v
python standards_adapter.py --root /path/to/reviewed/snapshot \
  --manifest /path/to/reviewed/manifest.json --id D-GOST1536-PN063
python standards_adapter.py --root /path/to/reviewed/snapshot \
  --manifest /path/to/reviewed/manifest.json --query '阀'
```

Manifest shape (replace the placeholder with the exact file digest):

```json
{
  "repository": "reknottycat/standards-kb",
  "commit": "7eda528a8795b8fbd850d6d35ac67e198de5810a",
  "scope": "selected_files",
  "files": {"kb/data/ГОСТ_1536-76.json": "<64 lowercase SHA256 hex characters>"}
}
```

Manifest is a **trust input**: materialize bytes from the explicit commit using an
approved read-only connector and independently review the resulting manifest.
Merely writing the commit into a manifest cannot authenticate arbitrary local
bytes as coming from that commit. The adapter verifies integrity relative to the
manifest, not Git signatures or remote origin. Keep the reviewed manifest separate
from mutable source snapshots. This explicitly scoped subset never claims full
repository coverage; unlisted files are not consumed or validated.

## Safety boundaries and known open evidence

This is structural **ingestion**, not full upstream schema/evidence validation.
It does not verify source PDFs, locator contents, original-language extraction,
standard revisions, jurisdiction, applicability, units, solver convergence,
physical evidence, or product acceptance. It does not interpret pressure rules
or calculate bolt stress area. Evidence binaries need not be downloaded for
research retrieval; their absence must not be mistaken for verified evidence.

The audited upstream `D-GOST1536-PN063` is UNVERIFIED_CLAUSE / E1. Its DN200 row
has no `As` field and cannot substantiate `As=147`. Its `usage.how` pressure
comparison direction remains **pending independent review**. Neither is repaired
or converted to a selection rule here. No changes to upstream standards, frozen
R1, or valve engineering parameters are made.

Engineering acceptance is a separate project-controlled decision requiring
explicit applicability and independently checked evidence. This adapter is
intentionally incapable of making it. Integrators must consume `result.record`,
not stripped ontology-query projections that omit evidence/status.

Tests synthesize records only; such fixtures are not standards evidence. See
`PROVENANCE.md` for any separately materialized actual-record smoke coverage.

The included `pinned-gost1536.manifest.json` can be used with the independently
retrieved audit snapshot. To include the optional exact-byte integration test:

```sh
STANDARDS_KB_SNAPSHOT=/path/to/pinned/snapshot python -m unittest discover -s tests -v
```
