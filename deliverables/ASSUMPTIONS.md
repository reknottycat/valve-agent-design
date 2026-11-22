# Phase 1 Engineering Assumptions

These assumptions are provisional inputs for Phase 1 research, not verified
product specifications or approval for manufacture. Record their scope and
actual use in each calculation or model. Resolve the applicable items in
Phase 2 before relying on them for design decisions.

| ID | Topic | Phase 1 assumption | Phase 2 verification |
| --- | --- | --- | --- |
| A-01 | Material | БрА10Ж3Мц2 is the assumed material. Suitability at −40 °C is TBD. | Confirm the specified grade, applicable material standard, properties and suitability for the relevant service temperature and environment. The base variant is not assumed to require −40 °C service; confirm whether the −02 variant is in scope. |
| A-02 | Design pressure | 0.9 MPa is a provisional design-pressure assumption. | Verify the applicable product's design pressure, pressure basis and governing requirements against authoritative specifications. Do not equate this assumption with the existing Ру6 marking, research load, rated pressure or test pressure. |
| A-03 | Geometry | A 60° seat angle is assumed. | Confirm the angle, its measurement convention and applicability against an authoritative drawing or measurement. |
| A-04 | CFD | Laminar flow is assumed for research, with research boundary conditions. | Document and justify inlet, outlet and wall boundaries, fluid properties and operating point; evaluate the flow regime and whether a turbulence model and sensitivity studies are needed. Research results do not establish product performance. |

The current project scope and the distinction between research and product
requirements are described in `CURRENT_PLAN.md`. Where these provisional inputs
conflict with verified project evidence, do not silently substitute them: record
the discrepancy and resolve it before use.

## Phase 2 Verification Action Template

Use one record per assumption or independently verifiable action.

- **Assumption ID:**
- **Variant and operating conditions:**
- **Verification question and acceptance criterion:**
- **Action and method:**
- **Authoritative source or evidence required:**
- **Owner and target date:**
- **Status:** Not started / In progress / Verified / Rejected / Blocked
- **Result and evidence reference:**
- **Impact on Phase 1 models and calculations:**
- **Follow-up or blocker:**

Mark an assumption verified only when its acceptance criterion is met and the
supporting evidence is recorded. Otherwise retain the uncertainty and any
resulting limitations.
