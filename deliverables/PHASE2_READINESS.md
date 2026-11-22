# Phase 2 启动准备

## Phase 1 交付物验证 ✅

| 文件 | 状态 | 说明 |
|------|------|------|
| ASSUMPTIONS.md | ✅ | A-01～A-04 四个 HOLD 项已文档化 |
| quick_kv.py | ✅ | CLI 工具，支持 --flow-m3-s / --pressure-drop-pa |
| kv_calculation.json | ✅ | Kv=147.09 m³/h，capacity_status=HOLD（state21 未收敛） |
| BOM.csv | ✅ | 10 rows，71.89 kg 总质量 |
| README.md | ✅ | 交付物索引 + STEP 文件位置说明 |
| STEP 文件 | ✅ | 6 个零件拆件（runs/20261006/C0/T12/out/assembly/） |

## Phase 2 验证任务（按优先级）

### 🔴 P0: A-02 设计压力确认
**问题**：当前假设 0.9 MPa（1.5×PN6），但未验证壁厚
**行动**：
1. 从 `runs/20261006/C0/T12/out/geometry_check.json` 提取：
   - 阀体壁厚（body wall thickness）
   - 公称直径 DN=200
2. 按 ГОСТ 356-80（或 ASME B31.1）计算许用压力：
   ```
   P_allow = (2 * S * E * t) / (D_o - 2*y*t)
   ```
   其中 S=许用应力（БрА10Ж3Мц2 @ 20°C ≈ 100 MPa）
3. 若 P_allow < 0.9 MPa → 降低设计压力或增加壁厚
4. 更新 ASSUMPTIONS.md 解除 A-02 HOLD

**工具**：Python 脚本 `scripts/strength_check.py`  
**预计 token**：Codex 5万

### 🟡 P1: A-03 阀座几何测量
**问题**：假设 60° 阀座角，未从 CAD 验证
**行动**：
1. FreeCAD 脚本打开 `seat_ring_asm.step` + `disc_asm.step`
2. 测量：
   - 阀座锥面角度（seat cone angle）
   - 阀盘升程（disc travel / lift）
   - 接触线直径（sealing diameter）
3. 对比 geometry_check.json 的 `seat_width=8` 是否一致
4. 更新 ASSUMPTIONS.md 解除 A-03 HOLD

**工具**：`scripts/freecad_measure_seat.py`  
**预计 token**：Codex 3万

### 🟢 P2: A-04 CFD 收敛（可选）
**问题**：state21 静压不守恒（inlet/outlet 差 19.43%），Kv 数字不可信
**行动**：
1. 切换求解器：state21（自研）→ OpenFOAM simpleFoam/pimpleFoam
2. 湍流模型：k-ω SST（Re ≈ 2000，过渡区）
3. 网格细化：110k → 300k 单元
4. 收敛标准：残差 < 1e-6，质量守恒误差 < 0.1%
5. 重新计算 Kv，若 Δp > 100 Pa 且收敛 → 移除 HOLD

**工具**：OpenFOAM case setup + solver  
**预计 token**：Codex 20万  
**优先级说明**：可推迟到 A-02/A-03 完成后

### 🔵 P3: A-01 材料低温性能
**问题**：БрА10Ж3Мц2 @ −40°C 冲击韧性数据缺失
**行动**：
1. 查阅 ГОСТ 18175-78（铝青铜技术条件）
2. 若无 −40°C 数据：
   - 选项 A：切换到 БрАЖН10-4-4（有船级社认证）
   - 选项 B：标注使用限制"最低工作温度 −20°C"
3. 更新 ASSUMPTIONS.md + BOM.csv 材料列

**工具**：文献搜索 + 标准查询  
**预计 token**：Claude 5万（非 Codex 任务）

## Phase 2 成功标准

- [ ] A-02 + A-03 解除 HOLD（强制）
- [ ] Kv 不确定性从 ±30% 降到 ±15%
- [ ] 生成至少 1 张制造图纸（阀体 2D drawing，标注尺寸公差）
- [ ] BOM 材料规格从 "TBD Phase 2" 更新为具体牌号/标准

## 启动命令（待用户确认）

```bash
# Task 2.1: 壁厚强度验证
codex exec --sandbox danger-full-access --skip-git-repo-check \
  "从 runs/20261006/C0/T12/out/geometry_check.json 提取阀体壁厚，按 ГОСТ 356-80 计算许用压力，验证是否满足 0.9 MPa"

# Task 2.2: 阀座几何测量
codex exec --sandbox danger-full-access --skip-git-repo-check \
  "用 FreeCAD Python API 打开 seat_ring_asm.step，测量阀座锥面角度和接触线直径，输出到 JSON"
```

---
生成日期：2026-11-23  
前置条件：Phase 1 所有任务完成（15→13 分支，deliverables/ 包含 6 个文件）
