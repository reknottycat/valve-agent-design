# Valve research readiness consumer

`valve_readiness.py` is a read-only port of the existing research preflight, with
an explicit call to the current `framework/standards/standards_adapter.py`.
It never starts a solver, changes a case, validates R1, or gives engineering
approval. It is not the task-topology checker, and does not revive old CFD tasks.

## Input and execution

The CLI accepts one JSON manifest and an optional `--case` directory. Standards
root has exactly one source: `standards.root` in that manifest. Relative roots
and case paths resolve from the current working directory. There is no overriding
root/card/lock CLI option. Use absolute paths for reproducibility.

This is a **synthetic wiring example, not a real case or an approved configuration**.
Save it outside source snapshots as `/tmp/synthetic-readiness.json`, replacing
`/absolute/path/to/standards-kb` with an external snapshot matching the production
lock:

```json
{
  "requested_action": "inspect",
  "standards": {
    "root": "/absolute/path/to/standards-kb",
    "configuration_id": "522-35.4179",
    "references": [
      {"id": "F-FLW-001", "use": "RESEARCH_REFERENCE"}
    ]
  }
}
```

From the valve repository root:

```sh
python -I -B framework/tools/valve_readiness.py /tmp/synthetic-readiness.json
```

For the existing API, from repository root:

```sh
python -B -c 'from framework.tools.valve_readiness import audit; print(audit({"requested_action": "inspect"}))'
```

Call `audit(meta, case=None)` with the same manifest object and optional case path.
Use Python `-B` (or `PYTHONDONTWRITEBYTECODE=1`) when importing to suppress normal
Python import-cache writes. The exact sibling adapter/helper loaders themselves
never create bytecode files or search arbitrary `sys.path` plugins.
Malformed input raises `ReadinessError` in the API; the CLI emits `INVALID` JSON
to stderr and exits 2. A complete requested check set exits 0; failed physical or
source checks and incomplete solve intent exit 2. Normal assessment stdout and rejected-input stderr are JSON. Help and argument
syntax errors use standard argparse text diagnostics.

## Contract and separate meanings

- `preflight_pass`, `errors`, `domain_scope`: original physical metadata/file
  diagnostics only. The original 12 tests retain this meaning. Even a positive
  presence check does not validate boundary values, topology or mesh quality.
- `standards.status`: absent declaration on inspect is `NOT_CHECKED`, never a
  standards success. Absent declaration on solve is `INCOMPLETE`. A declaration
  must include exactly `root`, `configuration_id`, and nonempty `references`.
  Null/partial declarations and unknown fields are invalid.
- `configuration_id` is the declared project/variant identity. Only unsuffixed
  `522-35.4179` can call the pinned baseline card. `522-35.4179-02` or another ID
  is incomplete and the card stays `NOT_CHECKED`. No duty, material, temperature,
  medium, geometry, custom card, or alternative variant data is accepted through
  this minimal interface. Unknown such fields are invalid. Matching a string
  proves only declared identity, not actual configuration authentication or
  seawater/brine suitability. Output explicitly says `DECLARED_IDENTITY_ONLY`,
  `configuration_authenticated: false`; project applicability is unconfirmed.
- Every reference has exactly `id` and `use`. The three uses are
  `RESEARCH_REFERENCE`, `CALCULATION_SUPPORT`, and `NORMATIVE_BASIS`. IDs are
  unique and must exist. Ineligible/quarantined records may be inspected only as
  research references, with a warning. Calculation/normative declarations fail
  their source-use check if ineligible. Eligible means upstream source-status
  eligibility only, **not approval to perform that calculation for this valve**.
- `standards.acceptance` is the real adapter assessment of fixed locked
  `AC-VALVE-001`, not a consumer-created substitute. The current result is nine
  HOLD and 27 null numeric limits. HOLD is separate from source inspection and
  limited research, not a blanket prohibition. It is not reduced to a boolean
  that can be mistaken for physical acceptance.
- `requested_checks_pass` combines the legacy checks with declared source-use
  checks and declaration completeness. It does not turn card HOLD into a pass,
  prove project applicability, or authorize solving. `engineering_release` and
  `solver_started` are always false; engineering acceptance is not assessed.

Legacy input fields are `requested_action` (default inspect), `domain_scope`,
`execution_budget` (`scope`, positive integer `cells`, `meaning`),
`milestone_complete`, `new_objective`, `boundary_conditions_verified`,
`pressure_role`, `mesh_stage`, `mesh_quality_pass`, `pressure_stability_pass`,
and descriptive `source_note`. Boolean fields require actual JSON booleans;
strings such as `"false"` fail preflight rather than becoming truthy.

Inputs are finite JSON with string keys, at most 4 MiB and 64 levels deep. At most
95 explicit source references are accepted. Duplicate JSON keys, duplicate IDs,
unknown IDs/fields, nonfinite numbers, nonregular/FIFO/device inputs, file symlinks,
escaping case paths and oversized parsed inputs fail closed. Only `fvSolution`
content is parsed, with a 4 MiB read bound. Other case artifacts, including large
mesh files, receive regular-file existence/type checks without reading their
contents or imposing a size cap. This does not authenticate a complete case
snapshot. Resource bounds are not engineering mesh thresholds. JSON/source files
are read only. No installation, source table, card, PDF or historical run is bundled.

## Reproducible regression checks

The 12 original tests run without a standards snapshot. New integration tests
require external snapshots explicitly; an unset variable means a reported skip,
not verified integration. For a full run from repository root:

```sh
VALVE_STANDARDS_ROOT=/absolute/path/to/current-selected-files \
VALVE_OLD_STANDARDS_ROOT=/absolute/path/to/old-snapshot \
python -B -m unittest discover -s framework/tests -p 'test_valve_readiness*.py' -v
```

Tests cover real adapter API/CLI use, current fixed-card HOLD and missing limits,
15 quarantined data/derived records, declared-reference effects, configuration
mismatch, old snapshots, malformed inputs, safe bounded case reading, no solver,
and unchanged case/source bytes. All fixtures are synthetic and not validation
of a physical valve. The exact 20-dependency lock and dependency installation
requirements remain documented in the [adapter README](../standards/README.md) and
[provenance](../standards/PROVENANCE.md).

## Source provenance

Port source: `reknottycat/valve-agent-design` research commit
[`5dcc3b8302f566678259bcbeeb36a891a593eba6`](https://github.com/reknottycat/valve-agent-design/tree/5dcc3b8302f566678259bcbeeb36a891a593eba6):

- [Original consumer](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/tools/valve_readiness.py), Git blob
  `dd7e6e3e1e1183d7b9460b16bd6b76327109b5be`.
- [Original unchanged 12-test file](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/tests/test_valve_readiness.py), Git blob
  `049d819d123df93d23b9ce2047813ed7a7d81efd`.

Target main baseline: `4259a86a9147829ed4aac2fb5a433e213f64501e`.
The adapter is the existing reviewed current implementation, not a new substitute.
Its external source is `reknottycat/standards-kb` commit
`19d586bb53cb452325d815313a895a1dfafa868b`; production lock SHA256 is
`ca5e450dcc1fa21b00f1eb75ed513ed29e201190ead439818d69833e8d0c1780`.
The adapter authenticates selected dependency bytes before running their guards.
This is selected-file provenance, not verification of snapshot HEAD, a whole
repository, source PDFs, historical R1 or physical evidence. No numerical limit
or formula is invented by this consumer.
