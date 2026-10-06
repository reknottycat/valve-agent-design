# 云端开源工具链实测与 C0 设计守卫

日期：2026-10-06。来源：reknottycat/valve-agent-design，提交
`4222b3d4df248b07777315068b9f3c99273d47c4`。

本目录对应既有计划 §16 / T04，附带 T22 前置诊断。独立命名为 CLOUD，
没有修改 C0 原始产物，也没有覆盖已经存在的 C1 分支。
这是可复跑的云端工作区交付，不是已注册的长期托管云环境。

## 结论

- **云端 CAD 与网格工具已经实际运行**：CadQuery 2.7.0、FreeCAD 1.0.0、
  Gmsh 4.13.1 / meshio 5.3.5。采用原方案允许的开源替代路线
- **T04 整体仍为 PARTIAL**：本环境未找到 OpenFOAM / CalculiX 可执行文件；
  没有运行云端 CFD/FEA 求解。没有把原机结果迁移成云端成功证据
- **C0 产品状态为 HOLD**：真实重建发现流体域断开、单位错误、零件多实体、
  局部壁厚记录失真以及设计契约语法错误。不能直接进入 T25 或批量扫描
- 数值诊断至多 E1，不构成材料、承压、泄漏、寿命、法规符合性或制造放行结论

## 已完成的实际工作

1. 新建完全隔离的 Python 3.12 环境 `.venv-cloud`，从带 SHA256 的
   `requirements.lock` 安装依赖；不复用系统 site-packages。
   首次探索使用的 `.venv` 不作为最终验收环境
2. CadQuery：两种半径的独立圆柱参数修改、重建、STEP 导出和重新导入，检查实体、体积与解析值
3. FreeCAD：参数化盒体修改尺寸，保存并重新打开 FCStd，再检查 STEP 往返。
   FreeCAD 使用宿主 Debian 13 的系统 Python 3.13 与库，独立于 Python 3.12 环境
4. Gmsh：从独立 STEP 导入，经一次明确的 mm→m 缩放，生成三维四面体网格，
   将 inlet/outlet/wall/fluid 物理标签写出并用 meshio 读回；检查正 Jacobian 与总体积
5. 保持 C0 原脚本字节不变，在本目录隔离重建全部六零件；六件均做 STEP/BREP 体积往返检查
6. 新增确定性守卫、负向测试与退出码；原 C0 在守卫下实际退出 **2 / HOLD**

独立网格样例为 272 节点、894 四面体，体积相对解析圆柱误差约 1.821%。
2% 是本独立冒烟测试的离散几何容差，不是阀门 CFD 质量阈值。
工具版本与完整结果以 `evidence/capability_matrix.json` 为准。

## C0 实测问题及影响

| 项目 | 测量 / 代码证据 | 后果 |
|---|---|---|
| T12 流体域 | 两个不连通实体；X 总长 301.2 mm；原注释声称 3D+L+3D，应为 1500 mm | 上下游 0.6 m 被按 0.6 mm 使用；不能作为流动域 |
| T23 流体域 | 两实体；源码数值按米设计，但 STEP 显式编码为毫米，导入总长仅 1.5000002 mm，意图为 1500 mm | 同时存在全截面切断与 STEP 单位不一致；Mesh OK 不能代替连通性或单位验证 |
| 座圈与杠杆 | 各自 STEP 包含两实体 | 需要明确拆分件/连接拓扑，不能把零件名称等同于单件 |
| 杠杆 | 生成器声明跨度 320 mm，实测 Y 范围 498 mm | 内部参数与实际模型不一致，需回到布局与连接定义 |
| 阀体局部径向韧带 | x=L/2,z=0 的 +Y 射线与 BREP 相交长度为 1.5 mm；原报告 actual_min=23.5 mm | 原“最小壁厚”只取筒体外内径，漏掉沉孔；这里只报告局部几何，不判定承压能力 |
| 设计契约 | YAML 在 53、110、177 行有语法问题 | 编排器无法可靠读取基线；必须报错并阻断 |

`audit_c0.py` 使用上游 Git blob 哈希校验关键脚本与契约，来源改变会拒绝沿用旧审计。
实际 CAD 内核小数误差按未舍入数值记录；不把四舍五入后的 0 宣称为精确零误差。

## 可复现命令

从仓库根目录运行：

```bash
# Python 3.12 已安装时，建立新的 venv 并用完整哈希锁安装
PYTHON=python3.12 bash runs/20261006/CLOUD/T04/bootstrap.sh

# 包括静态任务图校验、单元测试、真实工具测试、C0 预期拒绝、诊断补丁测试
bash runs/20261006/CLOUD/T04/verify.sh

# 单独检查产品；当前输入应返回 2，不应被当成成功
.venv-cloud/bin/python runs/20261006/CLOUD/T04/audit_c0.py
```

`verify.sh` 的 0 表示测试过程和“正确拒绝坏输入”的回归通过，**产品仍为 HOLD**。
任何意外的审计 0 或执行错误 1 都会使验证脚本失败。

FreeCAD 默认路径 `/usr/bin/python3` 与 `/usr/lib/freecad-python3/lib` 可通过
`FREECAD_PYTHON` / `FREECAD_LIB` 指定；宿主需已有可用 FreeCAD 库。
bootstrap 不会安装宿主系统包、提升权限、修改网络/安全设置或配置许可。
本次系统包查询因受限 apt 配置读取失败；没有绕过该限制。
Gmsh 还需要宿主图形/几何动态库；导入失败会写入 FAILED，不能假装可用。

## 独立修复建议，不覆盖原模型

- `proposals/design_contract.syntax-only.patch`：补冒号空格、把标准说明移到根级、
  将误写的 Python `% 0` 表达式保留为字面文本。全部原有未知项和
  `can_freeze: false` 保留；仍需人工确认启闭负载阈值，不把模板解释为 0 kgf
- `proposals/cfd_boolean_only.patch`：只删除导致全截面堵断的 Boolean 切除。
  `propose_flow_geometry.py` 已实际验证改动后产生一条连通域，尺寸常量不变。
  为纠正源码米制数值与 STEP 毫米编码冲突，另显式放大坐标 1000 倍后导出
  `diagnostic_geometry_mm.step`，回读总长 1500 mm。`legacy_numeric_mm.step` 保留旧错误单位证据
- 生成的 `cfd_boolean_only.py` 只含几何函数与常量，移除了网格/求解器函数和入口；
  直接运行会拒绝退出。诊断 JSON 的标志不被当作足够的执行保护
- 该试验只是定位断开原因。保留的旧旋转轴、未从受控装配派生的流体域、
  壁厚、运动及密封缺口尚未修复；诊断 STEP 明确 **不允许产品求解**

所有通过条件使用显式异常，不会被 Python `-O` 关闭；测试包含优化模式负控制。
`verify_evidence.py` 核对断开实体、两个单位/长度失败、STEP 元数据冲突和契约错误的
具体证据，不能仅靠始终未冻结的基线制造“测试通过”。

## 继续原计划的顺序

1. T03/T05/T06：补设计/试验压力、材料牌号及 −40°C 性能/许用应力，
   处理 Ру6 与 ГОСТ 1536-76 Ру6.3 的冲突；冻结受控接口之前不冻结 T07
2. 与 C1 工作合并时先审核本目录诊断，统一主模型、单位、真实铰轴、阀座密封、
   杠杆连接和局部壁厚；完成 T21/T22 的全行程、装配与语义边界验证
3. 按官方路线安装并分别跑通 OpenFOAM 与 CalculiX 独立已知解基准。
   OpenCFD v2506 与 OpenFOAM Foundation 的版本/命令不能当作同一个适配器
4. 输入、几何、物性、边界与预算都就绪后，再跑 T25 单点 → T27 核验 → T28/T29 扫描；
   T26 实际阀体 FEA 单独验收，既有厚壁圆筒基准不能替代本阀结果

## 来源、许可与保存

- 原始设计来源与 blob 哈希：`source_snapshot.json`。这是文本开发快照，
  不含所有原始二进制图纸；没有把未下载图纸写成“已复核”
- 当前云端证据：`evidence/`；依赖版本与其原始许可字段：`evidence/dependency_metadata.json`
- [CadQuery 官方安装](https://cadquery.readthedocs.io/en/latest/installation.html)
- [FreeCAD 官方仓库](https://github.com/FreeCAD/FreeCAD)
- [Gmsh 官方手册](https://gmsh.info/doc/texinfo/gmsh.html)
- [OpenCFD 官方 Linux 安装入口](https://www.openfoam.com/download/openfoam-installation-on-linux)
- [CalculiX 官方项目及许可](https://www.calculix.de/)

原图资料仍按 private 仓库要求处理。此交付不添加公开授权，不改变上游或依赖许可，
不包含第三方软件二进制；锁文件通过标准包仓库安装，依赖保留各自许可。
