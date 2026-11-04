# Standalone saved-continuation audit

This is an **offline, read-only audit tool**, not a solver launcher or an
integration into an existing native runner. It separates iteration identities
from fixed log-protocol constants (for example CONT_PATCH always has17 tokens;
precision17 is not an iteration number). It never starts CFD or changes a case.

Requires Python3.10+ and only the standard library. Do not run with `-O`:
assertions are part of the inherited parser's rejection gates; the CLI refuses
optimization. No logs, simulation fields, historical process artifacts or
credentials are bundled.

```
python tools/continuation_audit/selftest.py
python tools/continuation_audit/audit.py \
  --log /path/to/continuation.log --ids /path/to/selected-ids.json \
  --contract /path/to/window.json --output /path/to/new-observation.json
```

The output must not already exist. Inputs are hashed before/after parsing. A
successful audit checks the supplied evidence's protocol/numerical consistency;
it does not independently authenticate the native run or grant restart authority.
Original fields, input files and repository contents are not modified. Outputs
are user-requested artifacts, not files to commit by default.

## Exact supported contract

The JSON requires exactly these fields, with no duplicates or unknown keys:

```json
{"schema_version":1,"start":19,"end":21,"restart_index":99,
 "delta_t":1,"delta_t0":1,"cumulative_continuity":-0.0000001}
```

This is an illustrative synthetic identity, not a saved real checkpoint. Time
and time-index are distinct: state20 above has index100. Exactly two integer
unit steps are supported, `deltaT=deltaT0=1`; booleans are not integers and all
numbers must be finite. The contract must describe the actual source checkpoint
and native log, not be selected merely to make a parser accept.

The inherited parser is specifically for the serial759760-cell/132-patch
Stokes/Newtonian, empty-MRF/empty-options research protocol with38 fixed sorted
unique selected IDs, two momentum solves and four pressure solves, actual
conservative finalphi, two saved outputs and the existing CONT_* event grammar.
It is **not** a general OpenFOAM log parser or arbitrary mesh/model validator.
Log input is limited to1MiB; contract/IDs to16KiB each. No sampling or ID truncation.

`window_contract.py` owns identity/schema validation. `check_output.py` exposes
`check(log_path, ids_path_or_list, validated_contract)` and returns the existing
research observation. `checkpoint_io.py` separately exposes
`scan_outputs(case, bindings, contract, sha=None, require_complete=False,
expected_stages=None)`; it is not implicitly run by the log CLI.

For a complete checkpoint metadata scan, bindings must map the starting time
and `constant` to the expected resolved source-symlink targets; `system` and the
sibling `tmp` must be real directories. `expected_stages` must come from the
corresponding accepted native-stage records with string time keys, time-index
and cumulative continuity. The scanner checks supported files/headers/time
identity and optional hashes. Its256MiB aggregate limit is scan/polling-based,
not an OS disk quota; it always returns `restart_qualified=false`. Header-only
synthetic data cannot establish valid numerical field contents or restart fitness.

## Evidence and limits

The original three modules were exercised against three saved research logs
before delivery. The standalone CLI layout additionally underwent one local
saved-log integration check; those logs/results are deliberately **not** shipped.
The portable selftest generates tiny temporary metadata and an incomplete log,
checks time/index separation and rejection paths, then cleans its temporary data.
It is not a CFD or physical validation test.

Linear-solver terminal gates, continuity summaries, raw-momentum residuals,
local tails, pressure/velocity updates and port trends are distinct quantities.
The1%,1.10,1e-6 and1.25 checks in the parser are **self-built research criteria**,
not national/industry engineering standards. A small linear residual, low net
flux or accepted two-step log is not nonlinear steady convergence, real seal
validation, product Kv or manufacturing release. Output retains explicit false
engineering/steady-convergence/real-seal flags. Formula/reference-area/source
checks are separately required for any physical interpretation.
