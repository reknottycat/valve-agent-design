# State21 flow-input operational contract

## Purpose and strict input

This is the sole supported profile: `native-simple-state21/v1`. Add the optional
`formula_input_binding` object to the existing readiness manifest. Its base fields
are `profile` (that literal) and `paths` (exact seven role-to-path entries). An
optional `geometry_binding` is described below; no other fields are accepted:

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

In base mode, only Q, A, area-mean static kinematic pressure and derived proxy-K
arithmetic are bound. The arithmetic witness uses K=2*(pin_kin-pout_kin)/(|Qin|/Ain)^2.
Outward-positive Qin remains signed; its magnitude is used explicitly in speed.
The native observer area is the recorded inlet face-area reduction, never an
inferred DN area. The optional binding retains it and adds a separate explicit
nominal research reference.
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

Without `geometry_binding`, the runtime authenticates seven selected source byte
strings only. That base mode does NOT rehash state21 U/p/phi fields or revalidate
mesh geometry/topology. The optional mode below authenticates selected mesh and
p/phi bytes and reconstructs the two ports; neither mode revalidates full mesh
quality or the complete checkpoint. The emitted
physical_hidden_state_hash is a recorded cross-check, not an independently
recomputed field hash. The full checkpoint, historical R1 and product
configuration are NOT authenticated. Area and pressure reduction consistency
is checked against log/producer/JSON in base mode. Optional measured-port mode
adds direct selected-face geometry and saved-pressure reconstruction.
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

## Optional measured port/reference binding

The existing `native-simple-state21/v1` input still accepts exactly `profile` and
`paths`. It additionally accepts one optional `geometry_binding` object with
exactly `profile: native-simple-state21-ports/v1` and `paths`. Its exact path roles
are `boundary`, `points`, `faces`, `owner`, `p`, `phi`, and `plan`. Paths must be
canonical absolute paths without symlinks, including parent components. Supply
explicit realpaths for externally symlinked case files. Values, units, hashes,
status overrides, arbitrary state selection and alternate profiles are rejected.
No existing seven-file behavior or small-file 4 MiB limit is relaxed.

The adjacent `state21-ports.lock.json` is authenticated by a module-pinned SHA-256.
It authenticates selected mesh bytes, saved state21 pressure/flux bytes, and the
frozen research plan. The separate streaming reader reads under 120 MB in total,
with 16 KiB line, 2,000,000 list-count and 4 MiB retained-text bounds. Directory
file-descriptor traversal rejects symlinks and nonregular inputs without opening
FIFOs for blocking reads. Parsing and hashing consume the same file descriptor;
size, digest and before/after descriptor metadata are checked before a result is
returned. Only 272 selected triangles and their selected vertices/owner pressures are
retained from the large lists; p/phi boundary tails are additionally retained
under the 4 MiB text bound. The public output contains compact summaries only. It does not execute evidence source, run
OpenFOAM, remesh, write output files, read U, or recompute the full-case hash.

Missing files yield `HOLD` with no measurement. Invalid paths, nonregular inputs,
modified bytes, changed files, incompatible syntax, or inconsistent arithmetic
yield API errors / CLI `INVALID`. All seven geometry inputs must authenticate
before a measurement is exposed. This optional binding adds separate source,
reconstruction, and eight-value observer-crosscheck statuses. Its overall status
and all flow applicability/capacity statuses remain `HOLD` even when each limited
source/reconstruction check passes. Omitting it preserves the original API.

### What is measured, and what is now closed

The two 136-triangle boundaries reconstruct inlet78 at x=-0.6 m with outward
normal -X and outlet33 at x=1.2 m with outward normal +X. Each has 26 rim vertices
at radius 0.1 m and summed/projected area 0.03111103635738251 m². This is the
polygonal mesh area, not a nominal circle or a valve throat area. Inlet pressure
has `zeroGradient` and no serialized boundary values: each face pressure is
reconstructed from its owner-cell saved internal p. Outlet is `fixedValue uniform
0`. The result is an area-weighted static kinematic pressure difference, not
independent physical wall-tap data. Saved boundary phi supplies both signed fluxes.

The reconstructed state21 values match all eight authenticated observer values
at relative tolerance 1e-12 (actual maximum difference about 7.4e-16): Qin is
-1.634046460129948e-6 m³/s, Qout is 1.634046459592463e-6 m³/s, and dpkin is
1.599501972386503e-7 m²/s². Signed relative flux imbalance is about 3.289e-10.
The native observer's reference explicitly uses abs(Qin). An older observation
contract uses Qout; these conventions are not silently interchanged.

The frozen R1 research plan declares D=0.2 m and A_nominal=pi*D²/4 =
0.031415926535897934 m². With the same actual saved Qin and dpkin, the preserved
mesh-area K is 115.96179557311874 and the separate nominal-area research K is
118.24579895993566. The 1.969617% increase is purely reference-area arithmetic.
`research_input_bindings.RESEARCH_REFERENCE_A` and `RESEARCH_REFERENCE_K` expose
these closed research inputs separately. F-FLW-001 A/zeta/Kv, actual rho, actual Pa,
F-FLW-002 capacity and engineering release remain null/false/HOLD. The reason is
physical ineligibility of this laminar, nonsteady, restrained research case for
product capacity, not that the numerical research reference area is unknown.

The plan describes a restrained 57 mm research pose with 3DN straight extensions
on each side. End-plane positions are checked against the reconstructed mesh.
These port-to-port results include the numerical extensions and developing or
disturbed flow; they are not automatically an isolated-valve loss coefficient.
The plan's assumed fluid properties are not promoted to actual measured fluid
properties. Runtime does not authenticate CAD, a product BOM, full mesh quality,
all of R1, standard taps, steady convergence, or turbulent applicability.

### Frozen-plan provenance

The pinned upstream file is [flow_study_plan.json at aa80b87](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources_new/FLOW_PLAN_NEW/flow_study_plan.json),
Git blob `0ca3766e0fffb50ab46b999f894b4a7fc481754e`. Its 6453 remote bytes hash to
`0a83f513c91bb1703f6b00ed6fe59db63940e9ab9530779047b815d02d36bac6`.
The reviewed local `flow_study_plan_R1_original.json` contains those bytes plus
one appended newline: 6454 bytes, SHA-256
`f0659ec9bc0a0d560e36ea5df1e1e3354555477ba85996514deeb5ab83d00304`.
They are not byte-identical. Runtime pins the local newline representation.
Neither representation is changed by this binding.

### External regression inputs

Set `VALVE_STATE21_INPUT` to the original seven-file readiness manifest for the
unchanged v1 regressions. Set `VALVE_STATE21_PORT_INPUT` to a readiness manifest
with the optional declaration above for measured-port regressions. Each manifest
uses local external evidence paths and the existing standards root. Run:

```
python -B -m unittest discover -s framework/tests -v
python -B -m unittest discover -s framework/standards/tests -v
python -I -B framework/tools/valve_readiness.py "$VALVE_STATE21_PORT_INPUT"
```

Real-entry tests skip explicitly when their environment variable is absent.
Synthetic tests cover parser arithmetic, finite values, resource bounds,
canonical/nonregular/symlink paths, immutable locks, mutation and strict input
shape. Real tests cover direct reconstruction, eight observer comparisons,
modified and missing input rejection, unchanged source metadata, retained nulls,
and the isolated CLI's exit 2 HOLD response. Do not upload field fixtures, mesh
files, process logs, local manifests or their generated runtime output.

## Conditional research fluid and pressure binding

The same authenticated plan now exposes `selected_study_property_state` in the
geometry measurement. Its exact state and flags are checked: 20 °C,
reference-composition salinity 35 g/kg, P0=0.101325 MPa absolute,
rho=1024.9109328963 kg/m³, mu=0.0010766289252529323 Pa·s and
nu=1.0504609627009073e-6 m²/s. These are declared research assumptions, not
measured temperature, actual density, a temperature field or actual duty.
The original property-code/data SHA256 references are checked against the plan;
no new profile, lock, external-code execution or property source fixture is used.

The [original property implementation](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources/C4/T06/seawater_study.py)
and [frozen cases](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources/C4/T06/seawater_study_cases.json)
are independently implemented rounded-paper arithmetic, not MIT library code.
An independent Decimal audit reproduced all nine frozen rows within relative
1e-14; this is arithmetic agreement, not physical accuracy. The pinned plan
references code SHA256 `2767f043bd35ce52305192495003f9f639d0913e4bdf299f55c2a285b6bc214c`
and data SHA256 `dd39b778058673c846109a4e5bc409147a8820a06efd4891e83b9b1938b5a0fa`.
Runtime authenticates the plan, not a newly fetched copy of those sources.

[Sharqawy, Lienhard and Zubair (2010)](https://web.mit.edu/lienhard/www/papers/journal/Thermophysical_properties_of_seawater-DWT-16-354-2010.pdf),
Eq.8 and Eqs.22–23 support density and viscosity at this selected state, using
Celsius and salinity converted from g/kg to kg/kg. Eq.8 states 0.1% accuracy.
The [MIT property tables](https://web.mit.edu/seawater/2017_MIT_Seawater_Property_Tables_r2b_2023c.pdf)
list viscosity on printed p2 (PDF p5) and density on printed p21 (PDF p24),
with 1.5% and 0.14% labels respectively. These are not numbered tables or
interchangeable accuracy claims. Retained digits preserve provenance, not
physical precision. The [MIT documentation](https://web.mit.edu/seawater/)
has a 0 °C lower domain boundary; −2 °C phase/property eligibility remains
unresolved. No pressure correction is implemented, and no elevated-pressure or
full −2…50 °C validity is claimed.

Only authenticated seven-file observation plus authenticated geometry,
reconstruction and observer-crosscheck PASS produces `research_fluid_binding`.
It reconciles mu/rho with selected nu and actual configured run nu in m²/s,
checks kinematic pressure dimensions, and multiplies the reconstructed static
inlet-minus-outlet area-mean difference by assumed rho:

`conditional_research_pressure_difference_Pa = rho_assumed * reconstructed_dpkin`

For state21 this is 0.00016393470586881226 Pa. The estimator retains inlet
zeroGradient owner-cell reconstruction, outlet fixedValue 0 and the numerical
extensions. It is not a wall-tap, total-pressure, hydrostatic, actual operating
pressure or demonstrated steady result. F-FLW-001 rho_ref=1000 is never used
as actual or assumed fluid density. Conditional scaling is independent of
capacity-source eligibility; all existing source statuses are retained.

Missing observer or geometry produces no conditional numerical pressure.
Changed plan bytes fail the existing pin; caller density/temperature/units are
not accepted. Original seven-file mode stays unchanged. Actual top-level
rho_actual_kg_m3/delta_p_Pa/Kv_m3_h/Cv and applicable product A/zeta remain null;
all nine readiness HOLD conditions, acceptance limits and release status remain
unchanged. New `test_state21_research_fluid.py` tests exercise formula arithmetic,
real API/isolated CLI conversion, missing evidence and mutated state/model/units.
