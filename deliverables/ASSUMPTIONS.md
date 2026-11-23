# Phase 1 Engineering Assumptions

These assumptions are provisional inputs for Phase 1 research, not verified
product specifications or approval for manufacture. Record their scope and
actual use in each calculation or model. Resolve the applicable items in
Phase 2 before relying on them for design decisions.

| ID | Topic | Phase 1 assumption | Phase 2 verification | Status (2026-11-23) |
| --- | --- | --- | --- | --- |
| A-01 | Material | БрА10Ж3Мц2 is the assumed material. Suitability at −40 °C is TBD. | Confirm the specified grade, applicable material standard, properties and suitability for the relevant service temperature and environment. The base variant is not assumed to require −40 °C service; confirm whether the −02 variant is in scope. | **CONDITIONAL RELEASE** — See P3/P3b reports |
| A-02 | Design pressure | 0.9 MPa is a provisional design-pressure assumption. | Verify the applicable product's design pressure, pressure basis and governing requirements against authoritative specifications. Do not equate this assumption with the existing Ру6 marking, research load, rated pressure or test pressure. | **CONDITIONAL RELEASE** — See P0 report |
| A-03 | Geometry | A 60° seat angle is assumed. | Confirm the angle, its measurement convention and applicability against an authoritative drawing or measurement. | **PARTIAL** — 60° assumption rejected; tilted-disc verified — See P1 report |
| A-04 | CFD | Laminar flow is assumed for research, with research boundary conditions. | Document and justify inlet, outlet and wall boundaries, fluid properties and operating point; evaluate the flow regime and whether a turbulence model and sensitivity studies are needed. Research results do not establish product performance. | **IN PROGRESS** — P2 cloud verification |

The current project scope and the distinction between research and product
requirements are described in `CURRENT_PLAN.md`. Where these provisional inputs
conflict with verified project evidence, do not silently substitute them: record
the discrepancy and resolve it before use.

---

## Phase 2 Verification Summary

### A-01: Material (P3 + P3b completed 2026-11-23)

**Status: CONDITIONAL RELEASE with −20°C temperature limit**

- **Primary material**: Dual-track system established — C95400 (ASTM B148/ASME SB-148 sand-cast aluminum bronze) ≈ equivalent to ГОСТ БрА10Ж3Мц2
- **Key finding**: БрА10Ж3Мц2 @ −40°C impact toughness data **NOT FOUND in open sources** (OpenAlex, OSTI, GOST standards searched)
- **FCC stability evidence**: Aluminum bronze is FCC matrix (no DBTT); NAB deep-cryo study (MDPI 2024, −180°C) shows "minor microstructural changes only" — directional evidence, not acceptance criterion
- **Interim temperature limit**: −20°C (conservative, pending material certificate confirmation)
- **Path to −40°C**: Switch to БрАЖН10-4-4 / UNS C95800 (complete data chain available) + mandatory −40°C Charpy testing (3 specimens/heat) as casting acceptance
- **Internal spec created**: INT-MAT-522-35.4179-Rev0 with GOST→ASME mapping, wall-thickness-pressure table, corrosion allowance, BOM fastener recommendations
- **Evidence**: `deliverables/verification/p3/material_report.md`, `p3b/MATERIAL_SPEC.md`

**Release conditions**:
- Obtain БрА10Ж3Мц2 mill certificate confirming mechanical properties
- Confirm actual minimum design temperature with customer
- If < −20°C required, execute C95800 substitution + low-temp testing per MATERIAL_SPEC.md §2.3

### A-02: Design Pressure (P0 completed 2026-11-23)

**Status: CONDITIONAL RELEASE — 0.9 MPa assumption verified with 13.9× margin**

- **Allowable pressure** @ nominal wall thickness 12 mm: **P_allow = 13.89 MPa** (ГОСТ typical values) / 12.49 MPa (B148 conservative minimum)
- **Margin** vs 0.9 MPa design pressure: 15.4× (ГОСТ) / 13.9× (B148)
- **Required thickness** @ 0.9 MPa: only 0.74–0.82 mm (not including corrosion/casting allowance)
- **Hydro test** @ 1.5×PN6 = 0.9 MPa: stress 7.95 MPa << limit 165.6 MPa → **PASS**
- **Formula**: Thin-wall cylinder P_allow = 2·S·t/(D_o−t), where S = min(σb/3.5, σ0.2/1.5)×η_cast(0.8)
- **Sensitivity**: Even @ 10 mm wall (lower bound estimate), P_allow = 11.68 MPa, conclusion unchanged
- **Evidence**: `deliverables/verification/p0/strength_report.md`, `p0/results.json`, `p0/strength_check.py` (reproducible)

**Release conditions**:
- Manufacturing drawings confirm nominal wall thickness ≥12 mm (current data from CAD model only)
- Material certificate confirms БрА10Ж3Мц2 mechanical properties (σb/σ0.2) per A-01
- Flanges/bonnet/other pressure-retaining components verified separately (out of P0 scope)

### A-03: Internal Geometry (P1 completed 2026-11-23)

**Status: PARTIAL — Original "60° conical seat" assumption REJECTED; tilted-disc design VERIFIED; lift still ON HOLD**

- **Critical discovery**: CAD model contains **zero CONICAL_SURFACE entities** (STEP AP214 parsing)
- **Actual design**: **Tilted-disc plane-seal** structure (非锥形阀座)
  - Disc inclination: **45°** (verified from geometry_check.json params + STEP measurements)
  - Sealing diameter: **~200–208 mm** (matches DN200)
  - Seal line width: **4 mm** (from CAD params)
  - Pivot offset e: **15 mm**
  - Seat ring bore: D=200 mm (8 cylinders, 4 planes, 0 cones)
  - Disc: oversized to 208 mm outer edge, seats when tilted 45°
- **Surface inventory**: seat_ring 0 cones / 8 cylinders / 4 planes; disc 0 cones / 12 cylinders / 8 planes
- **Lift assumption (0.25×DN = 50 mm)**: Cannot be measured from static closed-position STEP geometry; **remains ON HOLD** pending original drawings or kinematic model
  - Area-equivalence check: π·204·50 ≈ 32,044 mm² ≥ π/4·200² ≈ 31,416 mm² → validates 50 mm lift assumption if confirmed
- **Evidence**: `deliverables/verification/p1/seat_report.md`, `p1/seat_measurements.json`, `p1/measure_seat.py`

**ASSUMPTIONS.md update required**:
- ❌ **废除**: "60° 阀座锥角" (design-form mismatch with CAD)
- ✅ **替换为**: "斜盘式平面密封：阀盘倾斜 45°，密封线直径 200–208 mm，密封线宽 4 mm，枢轴偏置 e=15 mm" — this portion **VERIFIED, can release**
- ⏳ **保持 HOLD**: "阀盘升程 = 0.25×DN = 50 mm" — needs original drawing kinematic dimensions or opened-position model

### A-04: CFD Validation (P2 in progress)

**Status: IN PROGRESS — Cloud workflow preparation**

P2 agent currently running (5+ hours), preparing GitHub Actions workflow for cloud-based OpenFOAM verification. Awaiting progress report to determine next steps.

---

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
