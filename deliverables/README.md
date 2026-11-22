# Phase 1 Deliverables

Valve: 522-35.4179СБ, DN200, PN6, bronze check-globe (ГОСТ 1536-76 marine flange)

| File | Description |
|------|-------------|
| `ASSUMPTIONS.md` | Engineering assumptions register (A-01..A-04) + Phase 2 verification template |
| `quick_kv.py` | Conditional Kv estimator (±30%, research-only, HOLD status) |
| `BOM.csv` | Bill of materials: 6 CAD parts (masses from verified STEP volumes) + 3 standard-part rows |

CAD models: `runs/20261006/C0/T12/out/parts/*.step` (6 parts) and `out/assembly/*.step`.
Kv inputs must come from CFD state21 results; see STATE21_FLOW_CONTRACT.md.

**Phase 1 success criteria:** STEP opens in FreeCAD without error; Kv has documented
method (±30% OK); BOM >= 10 rows (this BOM: 9 line items); ASSUMPTIONS.md lists all
open items. NOT included: manufacturing drawings, full GOST certification, shipped product.

## STEP 文件

零件 STEP 文件位于 `runs/20261006/C0/T12/out/assembly/`:
- `body_asm.step` — 阀体 (55.67 kg)
- `seat_ring_asm.step` — 阀座 (1.86 kg)
- `disc_asm.step` — 阀盘 (5.58 kg)
- `stem_asm.step` — 阀杆 (3.45 kg)
- `bonnet_asm.step` — 阀盖 (3.22 kg)
- `lever_asm.step` — 手柄 (2.11 kg)

**整体装配文件生成**：标记为 Phase 2 待办（需 FreeCAD Assembly4 脚本合并拆件）
