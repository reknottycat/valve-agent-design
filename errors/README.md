# Agent Work Error Log

每次 agent 工作中出现的失误，按时间倒序记录在这里。
目的：让下一个 agent 看到，不重蹈覆辙。

| 文件 | 时间 | 任务 |
|------|------|------|
| [cfd-validation-2026-11.md](cfd-validation-2026-11.md) | 2026-11 | Kaggle CFD 3D 验证 |

## 规则表（每条规则 → 执行它的机制）

| 规则 | 执行机制 |
|------|---------|
| OpenFOAM STL 必须与求解器单位一致（metre） | `valve_3d_cfd.py` 在 `setup_mesh_case()` 写入 triSurface 时强制除以 1000 |
| blockMeshDict 必须有 `defaultPatch { type patch; }` | snappyHexMesh 前的检查：`valve_3d_cfd.py` blockMeshDict 模板已内置 |
| STL 必须有 named solids（inlet / outlet / walls） | v18 校验 `valve_endplanes.stl.gz` 摘要后使用两个共面端口和壁面 |
| `locationInMesh` 必须在流体域内，不能在固体壁面内 | 固定为 `(-0.5, 0.0, 0.0)`（入口管道中心） |
| Kaggle kernel 不能依赖 apt 包名假设版本 | kernel 脚本让 `valve_3d_cfd.py` 自己调 `install_openfoam()` |
| GitHub Release 资产必须是公开仓库才能从 Kaggle 访问 | 仓库已设为 public；下载后用 SHA-256 验证 |
| `identify_patches()` 不能是 placeholder | 已删除，改用 named-solid STL 直接生成正确 patch |
