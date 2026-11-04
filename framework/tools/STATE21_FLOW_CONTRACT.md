# State21 flow-input operational contract

## Purpose and strict input

This is the sole supported profile: `native-simple-state21/v1`. Add the optional
`formula_input_binding` object to the existing readiness manifest. It has exactly
`profile` (that literal) and `paths` (exact seven role-to-path entries):

- `raw_log`: continuation.log
- `observation`: continuation-observation.json
- `observer_source`: ContinuationObserve.H
- `runner_source`: SimpleContinuation.C
- `transport`: actual transportProperties
- `model`: actual turbulenceProperties
- `numerics`: actual fvSolution

Supply explicit absolute canonical realpaths. No symlink component, traversal,
FIFO/device, directory, oversized (>4 MiB) or changed input is accepted. The
historical case has a symlinked constant directory; supply the realpath to its
actual small inputs, not the symlink path. This does not relax legacy case safety.
The JSON CLI rejects duplicate keys, NaN/Infinity and overflow; the Python API
accepts finite JSON only. No caller values, units, state, status, arbitrary lock,
density, DN, formula text or source-grade overrides are supported.

`state21-input.lock.json` contains reviewed roles, filename schemas, sizes and
SHA256 only. Its own SHA256 is fixed in the module. Paths may locate byte-identical
copies, but a freely rehashed lock cannot bless alternate or synthetic data.
Changing the profile requires a reviewed code/lock release. File identity is
verified on the captured bytes used by the parser, not merely via a path name.

Use the existing `standards` declaration with the exact current external
standards snapshot, configuration identity `522-35.4179`, and explicit references
F-FLW-001 and F-FLW-002. Research-reference use is the appropriate current scope;
source ineligibility is never upgraded. Missing declarations cause flow HOLD.
Malformed/old/tampered standards retain the adapter's INVALID behavior.

## Evidence and semantics

Authentication reads all seven selected files before extracting values. Raw
CONT_PORTS 21 and patch78/inlet, patch33/outlet entries are reconciled with JSON
ports.21 and patches.21, together with endpoint begin/end/checkpoint identity.
Producer source is authenticated and its pressure dimensions, area-weighted
static pressure, signed conservative phi, inlet-area reference and K expression
are checked. The runner source checks kinematic p dimensions [0,2,-2,0,0,0,0]
and phi [0,3,-1,0,0,0,0]. Sources are never executed or imported.

The endpoint uses final conservative phi correction2, followed by p relaxation
and velocity correction before the observer and nonmutating write. It does not
substitute flux(U), unrelaxed pressure, state19 or state20. The native checkpoint
is a SIMPLE iteration endpoint, not evidence of 21 seconds of physical time.
The p=0.3 and U=0.7 values read from fvSolution are dimensionless relaxation,
not pressure or measured velocity. Newtonian viscosity and laminar/Stokes model
are read/cross-checked from the selected numerical model configuration inputs and runner. The viscosity is a
frozen research constant, not a measured actual-fluid property.

Only Q, A, area-mean static kinematic pressure and derived proxy-K arithmetic
are bound. The arithmetic witness uses K=2*(pin_kin-pout_kin)/(|Qin|/Ain)^2.
Outward-positive Qin remains signed; its magnitude is used explicitly in speed.
Area is the recorded inlet face-area reduction, never an inferred DN area.
Finite K_valid is an arithmetic guard, not physical validity. Imposed inlet Q
and derived K are not independent validation. No hydraulic diameter or Reynolds
number is inferred.

Current F-FLW-001/002 expressions, units, source-grade/status, record/file hashes,
and applicability are read through the authenticated current standards adapter.
F-FLW-001's actual research contract is checked and emitted: steady single-phase
Newtonian incompressible, sufficiently turbulent/nonchoked, same reference
area/taps/opening, and excluded installation corrections. The explicit rho_ref
1000 kg/m³ comes from that record, not a measured density or verified exact IEC
value. Actual rho is absent. F-FLW-002 unit conversion cannot repair a missing
or inapplicable Kv. Neither capacity formula is evaluated here.

`variable_bindings` explicitly maps formula variables to candidates or missing
inputs. F-FLW-001.A has only a candidate inlet area with source locator; its
applicable `value` stays null. zeta.value is null while observed_proxy_K is
separately labeled and cannot substitute for product resistance. rho_ref binds
the current record convention only when current declarations exist. Kv remains
null. F-FLW-002.Kv depends on that HOLD and Cv_US remains null. Missing source
bytes leave candidate A/K and their source locators null. This mapping records
why capacity evaluation is blocked; it does not perform formula substitution.

## Status and failure semantics

- Missing external selected files: flow HOLD, named missing roles, no observation
  or partial arithmetic witness. Missing current formula declarations: HOLD.
- Malformed, forged, changed, unsafe, unit/stage/state-inconsistent evidence:
  INVALID, no partial success; API raises ReadinessError; CLI exit 2 on stderr.
- Authentic current evidence: source binding PASS and arithmetic PASS, but
  applicability HOLD. Kv_m3_h, Cv, delta_p_Pa and rho_actual_kg_m3 remain null.
- Explicitly requested flow HOLD makes requested_checks_pass false and CLI exit 2
  with a structured result on stdout. It must not appear as a full success.
- preflight_pass is the separate legacy metadata/0-field-file check only. Do not
  give this continuation as `--case` and claim state21 was checked as state0.
- Engineering release remains false; the pinned card's nine HOLD conditions,
  source eligibility and flow applicability remain distinct. A K drawing target
  ≤6 or historical 1% triage is not installed as an approved acceptance limit.
- Without this optional object, original readiness behavior remains unchanged.

The selected model is laminar and sustained steady is false. Other missing
inputs include actual density and temperature/phase/absolute pressure, nonchoking
and cavitation evidence, standard taps/installation, opening and product geometry,
physical/grid validation, independent tests and an approved criterion/reviewer.
HOLD is not a blanket prohibition on limited research.

## Limits and integrity boundary

The runtime authenticates seven selected source byte strings only. It does NOT
rehash state21 U/p/phi fields or revalidate mesh geometry/topology. The emitted
physical_hidden_state_hash is a recorded cross-check, not an independently
recomputed field hash. The full checkpoint, historical R1 and product
configuration are NOT authenticated. Area and pressure reduction consistency
is checked against log/producer/JSON; full face geometry is not recomputed.
Historical qualified_execution=true is not a new native execution verification.
No solver, CAD, installation or process-script execution occurs.

The fixed standards baseline is commit
[19d586bb53cb452325d815313a895a1dfafa868b](https://github.com/reknottycat/standards-kb/tree/19d586bb53cb452325d815313a895a1dfafa868b).
The locked F-FLW-001 and F-FLW-002 remain E1/UNVERIFIED_CLAUSE. Local native evidence
is intentionally external; hashes identify it without publishing process data.

## Tests

Run original tests plus `test_state21_flow_binding.py` using unittest discovery.
Set VALVE_STATE21_INPUT to an external local manifest carrying the exact profile,
seven realpaths and current standards declaration. Missing this environment
variable produces explicit external-integration skips, never a claimed real pass.
Set VALVE_STANDARDS_ROOT / VALVE_OLD_STANDARDS_ROOT for existing consumer tests;
STANDARDS_KB_SNAPSHOT / STANDARDS_KB_OLD_SNAPSHOT for adapter tests.
Set VALVE_P08_INPUT to the unchanged external historical P08 manifest for its
regression check. A missing P08 input also reports a skip, not a complete run.
Tests verify API and isolated CLI, unchanged selected-source hashes, HOLD/null
outputs, role/path safety, malformed/old/state/unit/status mutations and existing
readiness regressions. Mutation data are synthetic rejection cases, not physical
evidence. No real native fixture is distributed with tests.
