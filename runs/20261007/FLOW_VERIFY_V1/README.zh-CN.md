# 真实阀域最小流动验证包 V1（R1 之外）

**状态：PREPARED / BLOCKED；没有真实阀流动求解结果。** 本包基于
`aa80b87b6ee9617754101a238f70bec99393ad9a`，仅新增本目录，不改冻结 R1。
运行入口一次只处理仓库已有 `laminar_diagnostic_Re10`。原始工况不是实测额定工况。

当前唯一执行环境阻断点：**缺少已加载、双精度的 OpenCFD OpenFOAM 1912 开发运行环境**，
包括 `simpleFoam`、`checkMesh`、`wmake` 及其库/头文件。当前容器三个命令均不存在。
Python 来源/网格 seal 和算例生成已执行；原生 C++ 尚未编译，阀域 PDE 和流场尚未运行。
这不保证补齐运行环境后所有数值门一定通过；失败应保留原始证据继续诊断，不能跳门。

## 固定输入和来源

`manifest.json` 的固定 SHA256：
`7559f772e025b4d3ec27cc31ec43b0ca02ec92713992a5b71e7dca26f0cc0a9b`。
入口同时核对该摘要、13份来源文件原字节以及所选参数与 current-flow 的逐项一致性。
清单更改必须另立版本，不能临时刷新摘要来接收漂移输入。

| 项目 | 固定值 / 来源 |
|---|---|
| 物性 | 海水20°C、35g/kg、参考绝压101325Pa；C4/current-flow |
| ρ / ν | 1024.9109328963 kg/m³ / 1.0504609627009073e−6 m²/s |
| 入口 | U=(5.252304813504536e−5,0,0) m/s，fixedValue |
| 出口 | U zeroGradient；运动压力p fixedValue 0 |
| 壁面 | U noSlip；p zeroGradient；入口p也是zeroGradient |
| 边界类型来源 | `C0/T23/cfd_pipeline.py` 的 `write_case/blk`；只继承边界类型及初始U/p，不继承旧水物性、速度或湍流模型 |
| 几何 | 固定保持全开，阀瓣升程/阀杆退开各57mm，D=0.2m，x约−0.6至1.2m |
| 网格 | mesh v2 final_candidate：411099 cells、90900 points、865251 faces |

0.63MPa(g)只属于独立结构研究载荷，**没有作为本例压降施加**。
制造工况、−2°C相态和压力修正仍未知。本例不预测阀瓣能否自然保持开启。

## 执行命令

在包含本增量的仓库目录执行，Python需要3.10+和NumPy。输出必须是仓库和网格包之外的**新目录**。
入口不会安装软件、联网、改写R1、改网格源包或续跑旧结果。

1. 使用R1已指定的原网格归档
   `valve-mesh-repair-evidence-binding-v2-20261006.tar.gz`。
   身份为 `libfile_d1fe3abe4124819191187761705c99c6`，归档SHA256：
   `aa2410a92d6aa64dc6e9f0a6253f4a82e1a5cceb9814557b3a84b4190d2f667e`。
   解包后传入其中的 `revalidation_v2` 目录，不能传入旧v1包或Gmsh网格。
2. 在该机器加载已有OpenFOAM 1912环境。当前容器没有可供source的安装路径，故不虚构路径。
   加载后用 `command -v simpleFoam checkMesh wmake` 核对。兼容版本没有自动替换机制。
3. 运行以下入口（环境变量只用于机器上的真实绝对路径）：

```bash
export VALVE_MESH_V2=/absolute/path/to/revalidation_v2
export VALVE_FLOW_RUN=/absolute/path/outside/repository/flow-re10-new-run

# 仅准备并检查来源；缺运行环境时返回3且写入BLOCKED证据。
python3 -B runs/20261007/FLOW_VERIFY_V1/flow_verify.py \
  --mesh-root "$VALVE_MESH_V2" --output "$VALVE_FLOW_RUN"

# 实际执行必须另选一个新输出目录，不能复用上面的准备目录。
export VALVE_FLOW_RUN=/absolute/path/outside/repository/flow-re10-solve
python3 -B runs/20261007/FLOW_VERIFY_V1/flow_verify.py \
  --mesh-root "$VALVE_MESH_V2" --output "$VALVE_FLOW_RUN" --run
```

程序顺序：固定来源 → 完整mesh v2 seal → 拷贝真实阀网格并生成输入 → 软件/动态库指纹 →
本次 `checkMesh -allTopology -allGeometry` → 原生场/面探针及阀域非零源Poisson/格式敏感性 →
一次 `simpleFoam` Re10 → 最终场检查 → 时间序列及结果门。
任何前置失败均不会启动下一步。C++只在输出目录中的副本编译。

网格seal固定清单：`98976d5277a5592284cd20c9dbce095d7c7b845e036417ade65c90e5aff0bd05`。
旧网格原生日志只用于输入身份和告警基线；每次实际执行仍必须新跑原生检查。
旧cavity、立方体Poisson和CalculiX基准均不能替代本入口的阀域前置门。

## 本次数值门槛

以下为本包新设的诊断门槛，不是原制造厂性能限值或工程验收标准。

| 门 | 判据 |
|---|---|
| 网格 | 原生Mesh OK；无Failed/FATAL；单连通域；计数/体积与固定网格一致 |
| 非正交告警 | 恰有54个>70°面，最大角≤77.471485°；完整日志保留，不删告警 |
| 其他网格质量 | max skewness≤1.60；min determinant≥0.001；不放宽checkMesh原生标准 |
| 原生探针和阀域PDE | 见 `native/README.md`、`native_gate.py` 的明确误差/格式敏感性门；失败即停止 |
| 计算预算 | 5000次稳态迭代，不把残差单项提前停止当作稳定 |
| 残差 | 末100次每次最坏初始残差：p≤1e−7，Ux/Uy/Uz≤1e−8 |
| 稳定性 | 末100次Qout和Δp的相对极差均≤1e−3 |
| 守恒 | abs(Qin+Qout)/max(abs(Qin),abs(Qout))≤1e−6；Qin<0、Qout>0 |
| 壁面 | 末100次净壁面通量/abs(Qout)≤1e−10；最终全壁面绝对通量另检查 |
| 场值 | 全场有限；速度分量≤入口速度100倍、abs(p)≤1m²/s²，仅作数值发散保护 |

离散方案采用一阶迎风的层流诊断设置；数值门通过仍不建立网格无关精度。
阀域制造解的边界/源项是数学验证数据，**不会进入物理流动算例**。

## 输出定义与证据链

- `run_record.json`：综合状态、输入/软件/原始结果摘要；只有完整入口通过才为 `DIAGNOSTIC_PASS`。
- `results.json` / `history.csv`：时间序列及流动量。单独运行postprocess仅检查后处理门，不能代表全链通过。
- `case/`：实际0/U、0/p、system、constant、完整求解日志、保留的末两组场和全部monitor历史。
- `native/`：真实阀域探针、制造解场、日志、格式敏感性和源文件摘要。
- `case-inputs.json` / `runtime-fingerprints.json`：启动前的实际输入、二进制与动态库摘要。
- 本目录 `evidence/`：本次已经执行的Python测试和阻断记录；不会把预期命令记为已执行成功。

Q取实际 `phi` 的有向面通量积分；Qactual=Qout，Qnominal仅为参考输入。
ΔPstatic=ρ×(入口面积平均p−出口面积平均p)，因为simpleFoam的p是m²/s²。
ζport,static=ΔPstatic/[0.5ρ(Qout/(πD²/4))²]。使用17位原始写出精度，保留Pa科学计数。
该压差包含两侧各3D延长管；总压系数、直管修正和图纸注24的≤6比较均为UNASSESSED/NOT_COMPUTED。

当前真实通量、ΔP、ζ都是 `null`。未运行、失败或门未通过时不会自动填名义值。
所有结果即使数值通过也仍是研究诊断；接触、接头、整阀结构和制造放行继续独立HOLD。

## 回链R1

固定R1：[aa80b87…/CALCULATIONS/R1](https://github.com/reknottycat/valve-agent-design/tree/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1)。
本包对应其 `current_flow_chapter.py` 的10.10—10.12及FLOW_PLAN_NEW/MESH_V2来源，
不重建39页工作稿，不修改R1的NOT_RUN记录。后续新结果仅追加本包新运行记录。

```bash
cd runs/20261007/FLOW_VERIFY_V1
python3 -B -m unittest test_gate test_postprocess test_native_gate -v
python3 -B -O -m unittest test_gate test_postprocess test_native_gate -v
```

以上测试只验证输入绑定、拒绝逻辑、解析与单位换算，测试夹具不是真实求解结果。
