# CFD 3D 验证失误记录 — 2026-11

任务：在 Kaggle CPU 实例上跑 57mm 开度阀门 3D CFD，验证压降 Кз ≤ 6（100 m³/h）。

---

## 错误 1：STL 单位与 OpenFOAM 求解器不一致

**现象**：snappyHexMesh 运行完毕，但 boundary 文件只有 `defaultFaces` 一个 patch，阀门几何体完全没有被识别。

**根因**：STL 文件（由 Gmsh 导出）坐标范围是 X ∈ [-600, 1200]（毫米），而 blockMesh domain 是 X ∈ [-0.65, 1.25]（米）。阀门几何体完全在网格范围之外，snappyHexMesh 什么都没切到。

**证据**：
```
STL 实际坐标（mm）: X -600~1200, Y -145~145, Z -145~332
blockMesh domain（m）: X -0.65~1.25, Y -0.15~0.15, Z -0.15~0.15
```

**修复**：在 `setup_mesh_case()` 写入 `constant/triSurface/valve.stl` 时，逐行把 vertex 坐标除以 1000：
```python
x, y, z = float(parts[1]) / 1000.0, float(parts[2]) / 1000.0, float(parts[3]) / 1000.0
```

**预防**：`valve_3d_cfd.py` 在 `setup_mesh_case()` 中强制转换，不依赖 STL 文件本身的单位。

---

## 错误 2：blockMeshDict 缺少 `defaultPatch`，生成 2D 网格

**现象**：v9/v10 snappyHexMesh 报错：`Mesh provided is not fully 3D as required for mesh relaxation after snapping. Convert all empty patches to appropriate types`。

**根因**：blockMeshDict 中 `boundary ()` 为空，OpenFOAM 11 把未定义的面标记为 `empty` 类型（2D 求解用），snappyHexMesh 拒绝对 2D 网格执行 snap。

**证据**（v9 result.json error 字段）：
```
--> FOAM FATAL ERROR:
Mesh provided is not fully 3D as required for mesh relaxation after snapping
Convert all empty patches to appropriate types for a 3D mesh, current patch types are
1(empty)
```

**修复**：在 blockMeshDict 末尾加：
```
defaultPatch { type patch; }
```

**预防**：blockMeshDict 模板已内置此行。

---

## 错误 3：STL 只有一个 solid，snappyHexMesh 无法生成 inlet/outlet patch

**现象**：即使 snappyHexMesh 正常运行，boundary 文件只有 `valve`（整体壁面）和 `defaultFaces`，没有独立的 `inlet`/`outlet` patch。solver boundary conditions 写死了 `inlet`/`outlet`，简Foam 启动即报错找不到 patch。

**根因**：原始 STL（`valve_geometry.stl.gz`）只有一个 solid `Created by Gmsh`。snappyHexMesh 只能按 solid 名分 patch，无法自动区分入口/出口平面。

**证据**：
```
$ zcat valve_geometry.stl.gz | head -1
solid Created by Gmsh
```

**修复**：用 Python 按 X 坐标把 facet 分成三组，写出 `valve_split.stl.gz`（含 `solid inlet`、`solid outlet`、`solid walls`）：
- inlet：所有 facet 的 X < -595 mm（≈ -600 mm 截面）
- outlet：所有 facet 的 X > 1195 mm（≈ 1200 mm 截面）
- walls：其余

统计：inlet 3213 facet，outlet 3211 facet，walls 156910 facet。

snappyHexMeshDict 中用 `regions` 块对应：
```
valve.stl
{
    type triSurfaceMesh;
    name valve;
    regions
    {
        inlet  { name inlet;  }
        outlet { name outlet; }
        walls  { name walls;  }
    }
}
```

**预防**：`valve_3d_cfd.py` main() 优先加载 `valve_split.stl.gz`。

---

## 错误 4：`locationInMesh` 在阀门固体内部

**现象**：snappyHexMesh 把流体域当固体删掉，或者只保留外壳，网格 patch 不正确。

**根因**：`locationInMesh (0.0 0.0 0.0)` — 坐标原点可能在阀门壁面内部（阀门几何复杂，有阀芯、阀杆等结构穿过中心）。

**修复**：改为 `(-0.5 0.0 0.0)`，即入口管道中心处（X=-0.5m，远在阀门主体 X≥-0.6m 的入口侧），肯定是纯流体区域。

---

## 错误 5：OpenFOAM 版本/安装路径假设错误

**现象（v6 → v7）**：kernel 脚本用 `apt-get install openfoam` 装的是 v1912（路径 `/usr/share/openfoam/etc/bashrc`），但脚本 source 的是 `/opt/openfoam11/etc/bashrc`，bash 命令退出码 1。

**现象（v5）**：同一命令在另一个 Kaggle 机器上装了 OpenFOAM 11（路径 `/opt/openfoam11/etc/bashrc`），两次行为不一致。

**根因**：Kaggle 环境不稳定，`apt-get install openfoam` 的结果取决于 apt source 配置，不同实例可能不同。

**修复**：让 `valve_3d_cfd.py` 内置的 `install_openfoam()` 自己管理安装逻辑（从 openfoam.org 下载指定版本 deb 并校验 SHA-256），`valve_cfd_release.py` 不再负责安装，直接调 `python3 valve_3d_cfd.py`。

---

## 错误 6：Kaggle kernel 下载 GitHub Release 资产时 404

**现象**：curl 下载 `https://raw.githubusercontent.com/...` 返回 404。

**根因**：仓库是私有（private）的，Kaggle 实例没有认证，访问不了。

**修复**：把仓库改为 public（已确认）。用 GitHub Release URL 而非 raw.githubusercontent.com，Release 对 public 仓库无需认证。

---

## 错误 7：`identify_patches()` 是未完成的 placeholder

**现象**：函数体只有 print 语句，不做任何实际操作，导致后续 solver 找不到 patch 名。

**根因**：代码生成时把这个步骤留作 "TODO"，但调用方没有检查其结果。

**修复**：用 named-solid STL 方案（见错误 3）从根本上消除了对这个函数的需求，函数已废弃。

---

## 错误 8：Kaggle kernel 大文件输出导致下载连接中断

**现象**：`kaggle kernels output` 下载到大网格文件（>100MB）时，HTTP 连接断开（`IncompleteRead`），无法取到 `result.json`、`simpleFoam.log` 等关键文件。

**根因**：Kaggle output 下载是按文件大小排序的，大文件（faces、points、owner 等）把连接耗尽，后面的小文件下不到。

**缓解**：`valve_3d_cfd.py` 在 result.json 里记录完整的错误信息（error 字段），以便部分下载也能诊断。同时在 main() 里把每步关键日志也打印到 stdout（kernel log 中可见）。

---

## 错误 9：kernel 源码 1MB 限制

**现象**：直接把 STL（11MB）和 CFD 脚本打包进 kernel 源码，推送时报错超过 1MB 限制。

**修复**：kernel 只放轻量引导脚本（`valve_cfd_release.py` < 2KB），在运行时从 GitHub Release 下载实际文件。
