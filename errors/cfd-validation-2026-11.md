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

**根因**：整批下载在一个大文件传输中断时退出，后续文件未写入本地。可从单次作业的输出清单按文件名读取结果和日志。

**缓解**：`valve_3d_cfd.py` 在 result.json 里记录完整的错误信息（error 字段），以便部分下载也能诊断。同时在 main() 里把每步关键日志也打印到 stdout（kernel log 中可见）。

---

## 错误 9：kernel 源码 1MB 限制

**现象**：直接把 STL（11MB）和 CFD 脚本打包进 kernel 源码，推送时报错超过 1MB 限制。

**修复**：kernel 只放轻量引导脚本（`valve_cfd_release.py` < 2KB），在运行时从 GitHub Release 下载实际文件。

---

## 错误 10　把边界名称差异误报为 v11 退出原因

v11 网格检查通过。网格有入口、出口和壁面，初始场还包含一个多余的壁面条目。未取得 v11 求解报错原文，具体退出原因未确认。v12 仅删了部分字段，多余项已在 v18 从剩余三个场中移除。

## 错误 11　OpenFOAM 11 配置迁移不全

v12 日志显示缺少 `viscosityModel`。v17 选中黏度模型后，在首次迭代前因缺少 `constant/momentumTransport` 停止，并提示旧字典类名错误。v18 按 Foundation 11 官方算例生成 `physicalProperties` 和 `momentumTransport`，两者的文件类均为 `dictionary`。

## 错误 12　计算量纲与验收阈值混用

旧脚本把 0.001 当作运动黏度，计算得到雷诺数约 177。研究工况采用 20 °C、盐度 35 g/kg 海水，运动黏度 1.0504609627009073×10⁻⁶ m²/s。DN200、100 m³/h 时雷诺数约 168344，按名义截面的动压折算，Кз 为 6 对应 2403.82 Pa。140 Pa 单列为比较值。测压位置取两侧延伸管的端面，产品验收的测压约定仍待确认。

## 错误 13　清理输出导致启动报错并可能丢失日志

v16 在安装前因 `main()` 中局部导入 `os` 报 `UnboundLocalError`，故没有求解结果。v17 修复导入。v18 把求解工作目录与可下载结果分开，输出结果、压缩日志和逐步监测数据，取消按大小删除文件。

## 错误 14　启动器与求解程序的字段和判定不一致

旧启动器读取 `pressure_drop_pa` 和 `resistance_coefficient`，而求解程序写 `dp_Pa` 和 `kz`。v18 提交的脚本直接计算、保存和显示同一份结果。用一组稳定的模拟监测数据验证，移除求解器收敛标志后，达标判定为假。

## 错误 15　端口分组包含侧壁三角面

原来按 5 mm 宽的轴向区间分组，入口混入 249 个侧面三角形，出口混入 247 个。逐个检查三顶点是否共面后，入口和出口各有 2964 个端面三角形。v18 固定积分入口体积流量，并核对两端实际流量与设定值的偏差。

## 错误 16　稳态计算运行到上限，压降仍有波动

第 18 版达到 3000 次迭代上限，求解器未报告残差收敛。复算最后 20 次监测记录，平均压降 2527.48 Pa，极差占均值 2.64%，超过 0.5% 的稳定性要求。最大流量不平衡为 0.0088%。该次结果作为未收敛记录保留，不能用来判定合格或不合格。

[计算结果与原始监测数据](../verification/valve-3d-cfd-57mm/v18/)

## 错误 17　将通用网格检查通过误当成几何范围完整

v18 和 v19 采用同一网格。对照 v19 的 `checkMesh` 原始记录和输入三角面，保留流体网格最高 z 为 211.9999975 mm，输入几何最高 z 为 332 mm。`Mesh OK` 和单连通区域只能说明现存单元通过常规检查，不能证明所有原始狭缝均保留。v19 在 7500 次稳态迭代后也未达到残差标准；最后 20 次压降均值 2522.52 Pa，波动 0.945%，上限 0.5%。该值不可作为整阀验收。v20 改为局部加密并检查 CAD 确认的六个流体点是否同属一个网格区域，不计算压降；点位检查也不等于通过完整的网格敏感性验证。

[第 19 版结果、运行脚本与原始监测证据](../verification/valve-3d-cfd-57mm/v19/)

## 错误 18　覆盖到顶部不等于网格质量通过

v20 有 1,997,199 个单元，最高 z 为 331.999991 mm，报告一个连通区域。但存在 1 个非正交错误、1 个方向错误面和 1,180 个严重偏斜面；不同检查可能涉及同一面。三项质量检查失败，未执行随后的六点定位，未求解压降。

v21 改从同一原始 STEP 直接生成四面体，保留端面和壁面，限制导向间隙两侧圆柱的离散误差。生成器测得该两面最大径向内偏分别为 0.0326、0.0336 mm，六个原始流体点均在四面体内。这不是 OpenFOAM 的网格质量、连通性或压力验证结果。

[第 20 版原始网格日志](../verification/valve-3d-cfd-57mm/v20/)；[新网格本地检查](../verification/valve-3d-cfd-57mm/v21/geometry/)。

## 错误 19　采样点连通且四面体体积为正，但网格仍不适合压力求解

v21 原生转换后有 498572 个单元。六个模型内部位置各自在唯一连通区域中找到；原生求解器报告 1097 个高偏斜面、57236 个低行列式单元、27333 个低插值权重面和 1198 个低体积比面，四项检查失败。未启动压力求解。对原始四面体做独立诊断：按形状指标 minSICN < 0.05 筛出的 22169 个单元中，21861 个中心位于 z=70–80 mm。这是另一种定位指标，不能与原生检查的缺陷数量相加，也不能代替原生检查。保留几何、连通性和原生质量三项分别核对的规则。

[第 21 版原生检查、连通性与运行脚本](../verification/valve-3d-cfd-57mm/v21/)。
