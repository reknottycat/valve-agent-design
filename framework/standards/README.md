# Current standards research adapter

Read-only Python API and CLI for the reviewed subset of
[`reknottycat/standards-kb@19d586bb53cb452325d815313a895a1dfafa868b`](https://github.com/reknottycat/standards-kb/tree/19d586bb53cb452325d815313a895a1dfafa868b).
This updates the existing research adapter interface, rather than creating a new
engineering framework. The source snapshot stays external. No standards tables,
raw data, source PDFs, process reports or old executable manifest are included.

**This API/CLI is consumed by the selected existing
[research readiness entry](../tools/README.md).** That read-only consumer checks
its declared references and use in the same metadata/case preflight; it does not
run a solver. The valve candidate, topology checks, historical C0 scripts and full
orchestration are not integrated or intercepted. There is no CAD, CFD or FEA run here.

## Run

Use a trusted POSIX Python 3.10+ environment with **PyYAML 6.0.3** already available
(see `requirements.txt`). Tested with Python 3.12.14 and PyYAML 6.0.3. No network,
installation or snapshot generation is performed by the adapter.

From the repository root:

```sh
python -I -B framework/standards/standards_adapter.py \
  --root /path/to/standards-kb-19d586b --id F-FLW-001

python -I -B framework/standards/standards_adapter.py \
  --root /path/to/standards-kb-19d586b --query '阀'

python -I -B framework/standards/standards_adapter.py \
  --root /path/to/standards-kb-19d586b --acceptance
```

The existing `StandardsAdapter(root, manifest_path)` and
`query(text='', record_id=None)` interfaces remain available. `manifest_path`
now defaults to the bundled production lock, and any supplied file must be
byte-identical to that lock. Arbitrary manifests are no longer a trust input.

```python
from framework.standards.standards_adapter import StandardsAdapter
adapter = StandardsAdapter('/path/to/standards-kb-19d586b')
record = adapter.query(record_id='F-FLW-001')
readiness = adapter.assess_acceptance()
```

Run API callers with `python -B` or `PYTHONDONTWRITEBYTECODE=1`. Python controls
bytecode creation when importing the adapter itself; the module cannot prevent
that before its own execution. The recommended CLI and tests use `-I -B`.

Exit codes:

- **0:** research query succeeded, including zero matches. It does not mean
  engineering acceptance. The acceptance path would use 0 only for upstream
  `READY_FOR_REVIEW`, still never release.
- **1:** a valid acceptance assessment is HOLD or FAIL. The locked current card
  returns HOLD. Structured results are on stdout.
- **2:** rejected input/dependency, including a missing or altered lock, data or
  upstream code file. JSON error is on stderr; no partial successful stdout.
  Argument syntax errors use argparse's normal stderr diagnostics.

## What the real call path does

Construction performs the same guard sequence for queries and acceptance:

1. Authenticate the exact production lock, then read and SHA256-check **all 20
   dependencies** before executing upstream code. These comprise ten record files,
   one formula mapping, one vocabulary, the current card, and seven rule modules.
   Inputs must be regular files (no final-component symlinks), at most 4 MiB each.
   Reads are bounded and opened nonblocking, so FIFO/device inputs cannot hang.
   This is a software resource limit, not an engineering criterion.
2. Strictly parse all JSON, including the card and mapping. Reject duplicate
   keys/IDs, non-object records, invalid source/evidence metadata, NaN, Infinity
   and overflow literals such as `1e999`. Load all 95 records across formulas,
   parameters, data and derivations without permissive upstream glob loading.
3. Execute the seven reviewed upstream modules from their already-verified
   bytes, using a private closed import table. No upstream module is selected
   through `sys.path`, `sys.modules`, `PYTHONPATH` or `.pyc`. All module bytes are
   verified before any is executed; script `main` functions are never called.
4. Call `formula_input_contract.validate(root)` against an in-memory read-only
   view of the verified bytes; call `valve_completion_contract.check_entry` on
   records and `flw001_contract.assess` on F-FLW-001.
5. Call `acceptance_card.assess` with the **same strictly loaded records** and
   locked card. This invokes the real variant, documented-requirement and nine
   protocol guards. Calculation/normative references are additionally subject
   to the actual `kb_entries.entry_usable_for_calc` rule, not a copied predicate.
6. Return detached copies of original records, provenance and separate decisions.
   No source file is reread for validation or written; no source cache, temporary
   result or network output is created.

## Separate meanings, never an automatic green light

- `research_retrievable`: a record can be inspected, including conflicting and
  unverified records. Original fields and warnings are retained unchanged.
- `source_status` / `source_grade`: upstream evidence declarations, not a new
  verification of the standard text.
- `upstream_calc_eligibility.usable`: the current upstream source-status and use
  quarantine rule. This is **not** suitability for the selected bronze valve.
- `project_applicability`: NOT_ASSESSED for research hits; the pinned project card
  is UNCONFIRMED. Both always have `approved: false`.
- `engineering_release`: always **false**, including errors, zero hits and a
  successful metadata/consistency check. No release method exists.

The actual current results are:

- 95 research records, of which the upstream source rule permits 44. All 13
  GB/ГОСТ flange table records are blocked even when VERIFIED_CLAUSE. Two related
  DV-THERM derivations also match the upstream flange quarantine, for 15 matching
  records across all layers. Tables have **not** been fully corrected by this work.
- F-FLW-001 uses the corrected reference-density expression without the old
  `/1000`; its recorded synthetic sample is internally consistent
  (Kv ≈ 652.967771 m³/h and inverse ζ ≈ 6). It remains UNVERIFIED_CLAUSE and is
  ineligible under the source rule. This is not an IEC clause verification,
  CFD result, actual flow test or project calculation approval.
- The actual AC-VALVE-001 assessment is **9 HOLD**, with **27 empty pending numeric
  limits** and empty corresponding source/approval fields. No limits are filled.
- `formula_input_metadata_check` checks the recorded semantics of F-DRV-001 and
  F-TEST-001/002. It does **not** authenticate a real static friction coefficient
  μs, measured lift L at pressure P, or any complete formula-input dataset.

## Trust and fixed-card boundary

The lock's SHA256 is embedded in the reviewed adapter code. Changing a record,
rule or card and rehashing a local manifest is rejected. Future upstream updates
require a new reviewed adapter/lock release, not a command-line override. Hashes
bind this selected subset; they do not prove a local Git HEAD, all repository
files, digital signatures, source-PDF contents or product compliance.

The Python interpreter, standard library, this adapter release and installed
PyYAML are trusted runtime components, **not sandboxed hostile code**. The loader
requires PyYAML 6.0.3 from the interpreter's installation and rejects ordinary
cwd/PYTHONPATH or `sys.modules` impersonation. It does not defend an attacker who
has modified that trusted installation, forged in-process runtime internals, or
changed the adapter and its embedded trust anchor. Upstream bytecode is never
used; normal installed-runtime bytecode is inside this declared trust boundary.

`--acceptance` supports **only the exact current baseline card**, not an external
candidate card. Its bytes are locked along with its configuration and source
references. An edited or renamed card, old formula, or -02 brine duty inserted
into the unsuffixed base is rejected by the production identity check. The
original variant guard is also exercised by tests with synthetic contamination.
The adapter does not independently authenticate a `configuration_sha256`, verify
the original frozen R1 files, or claim that `acceptance_card.assess` does so.
Source-bound base seawater −2..50 °C remains distinct from -02 brine −40..50 °C;
materials, product pressure and complete engineering configuration stay unresolved.

## Verification

```sh
STANDARDS_KB_SNAPSHOT=/path/to/standards-kb-19d586b \
STANDARDS_KB_OLD_SNAPSHOT=/path/to/old-7eda528-snapshot \
python -I -B -m unittest discover -s framework/standards/tests -v
```

With both real external snapshots, all tests must run without skips. Without the
current snapshot, only standalone parser/path tests run; that is **not** a current
upstream integration pass. Tests cover actual API/CLI behavior, invocation of
upstream rules, dependency/code drift before execution, old pin/formula/snapshot,
rehashing attacks, fixed-card/variant identity, malformed JSON/IDs, path escape,
module pollution, detached results and byte/file-inventory read-only checks.
Synthetic negative cases are software checks, never engineering evidence.

See [PROVENANCE.md](PROVENANCE.md) for source pins and review scope.
