# 阀门设计恢复检查点

记录日期：2026-10-06。目标“完整制造设计文件”仍未完成；C2几何研究包和C3接口补充包已交付。
本页及 `checkpoint/state.json` 独立于冻结包，**不会改变C2/C3的内容和证据**。

## 1. 从哪里继续

| 阶段 | 冻结本地提交 | 已达到的范围 |
|---|---|---|
| CLOUD/T04 | `705e3574ade324c382552ff5ff46d992697cbf92` | 开源CAD真实探测、C0缺陷复现与失败关闭门 |
| C2 | `2566bdee5b52024036e0bbac559dd78f8a903a34` | 原图纠错、轴向升降研究模型、接触/行程取样、明确SI单位网格、研究图纸/BOM |
| C3 | `31662e66f0a14e426ab60b53c870f958a60f4ce1` | 未选定的紧固/密封/驱动接口、支承/碰撞/拆出取样和制造缺项登记 |

当前工作目录 `/workspace/shared/valve-cloud-20261006`，本地分支 `design/c3-interface-study-20261006`。
这是从上游 `4222b3d4df248b07777315068b9f3c99273d47c4` 物化的部分文本快照加新增成果，
**不是完整上游克隆，不能将本地快照历史直接推到远端覆盖原文件**。

优先阅读：

- `runs/20261006/C2/10_handoff/START_HERE.md` 与 `VERIFICATION.md`
- `runs/20261006/C2/T06/evidence_matrix.md`、`variant_input_matrix.json`、`study_contract.json`
- `runs/20261006/C3/README.zh-CN.md` 与 `10_handoff/VERIFICATION.md`
- `runs/20261006/C3/manufacturing_work_breakdown.json`：M01–M15逐项输入、产物、验收和依赖
- `docs/checkpoint/state.json`：冻结散列、远端观察和暂停状态

## 2. 当前还能否独立推进

本轮可独立验证的来源、几何、接口和可复现检查已完成。继续增加未知载荷下的螺柱尺寸、
材料或驱动包络，不会缩短正式定型缺口，因此停止新增泛泛候选。

M09“导向与防脱”仍开着：原图给出轴向布局，但没有恢复完整的连接、防脱和导向细节。
准确复制需要受控零件图/BOM；新派生设计需要先确定功能和安装约束，再选择机构。
现有七个退出取样不证明连续路径，也不能作为现场拆装操作规程。

最小设计输入分三组，已能从原图或资料确定的内容不再要求重复提供：

1. **产品目标和真实工况。** 原型号哪个变型，还是新派生设计；实际压力—温度、最大关闭/反向压差、
   瞬态、安装方向及管路/空间边界。原图无后缀型号的注4支持海水−2…50°C；
   CaCl2低温注5仅适用于−02。它们不能代替真实项目工况。字面“Ру6”、类比目录PN6.3以及未核实PN10线索
   不能自动组成设计或试验压力。
2. **适用验收依据。** 合同/船级等适用要求和版本，能合法读取的控制条款。
   GOST1536只管相应船用法兰连接/密封面；GOST356是压力系列，不能当垫片材料标准。
   目录/状态页不足以给出允许应力、试验系数或整个产品合格判定。
3. **复制还是允许重新设计的细节边界。** 复制路线需原零件图、BOM和导向/连接细节；
   派生路线应明确哪些接口、外包络和功能必须保持。C3接头外径400/440mm较C2研究阀盖360mm扩大，
   当前驱动支架/保持件尚未设计，不能默认这些变化已纳入正式型号。

来源和适用性证据见C2的证据矩阵及原图像素；官方元数据入口：
[GOST1536-76](https://protect.gost.ru/gost/details/23b3dd83-c416-4ccf-ae9c-77f26bdaffdb)、
[GOST356-80](https://protect.gost.ru/gost/details/8ffe7e89-ad99-4d7d-86b0-b48f85461d3a)。
部分官方全文需授权登录，已停在该访问边界，不据未读条款作结论。

工况和规则明确后，可以继续研究并推荐材料，不要求使用者先自行做完材料设计。
但不能把厂商同族产品的青铜牌号直接变成本阀已批准材料，也不能从抗拉强度猜许用应力。
压力、材料、预紧、扭矩、密封性能和最终制造公差目前都未选定。

## 3. 冻结成果的快速只读验证

标准库检查不安装、不建模、不调用求解器、不访问网络，也不修改冻结文件：

```sh
cd /workspace/shared/valve-cloud-20261006
python docs/checkpoint/verify_frozen_artifacts.py --archive-dir /workspace/shared
```

它验证T04的64项、C2的93项、C3的203项文件散列和大小，同时验证四个指定归档的SHA256，
并检查ZIP CRC。若只保留仓库而没有交付归档，可省略 `--archive-dir`；输出会明确未检查归档。
成功仅表示冻结文件完整性，不表示工程设计合格。检查器的10个回归测试在普通和 `-O` 模式均通过；
另从本地冻结提交物化了全新副本，360项文件散列仍一致。没有为此重建CAD或调用求解器。

归档名及散列：

| 文件 | SHA256 |
|---|---|
| `valve-cloud-T04-20261006.zip` | `32dcd79b035434752eb152dd7fd6074fae06489554ed221c2182c0a94704fbb0` |
| `valve-C2-research-package-20261006.zip` | `d716892fadf965eee7947c1184c4712daac2f2d2d7277b2eb6e3e3dfc90270c7` |
| `valve-C3-interface-supplement-20261006.zip` | `2ff71f2b98fd378a4a47e034e045cc98fb9743dd9849d80ed9dc16ec5216e142` |
| `valve-solvers-20261006-evidence.tar.gz` | `60da7f2b882fcba5bc543befdf0d6107a531fa5702b1c00633d6da334cbf7296` |

C3为增量补充包，依赖同级C2和CLOUD/T04，不能脱离它们单独复跑。
交付包没有虚拟环境、缓存或FreeCAD备份文件；也没有再分发完整第三方标准/厂家目录PDF。

## 4. CAD复现应使用隔离副本

已有 `.venv-cloud` 提供CadQuery2.7.0、OCP7.8.1.1.post1、Gmsh4.13.1和相关锁定依赖；
宿主FreeCAD1.0.0使用 `/usr/bin/python3`。图示脚本使用宿主Python中的matplotlib/reportlab/ezdxf。
运行环境明细和依赖来源见T04，不把另一台机器的安装状态视为已验证。

**全量验证脚本会重写模型、日志和时间戳，不能直接对冻结目录运行。**
C2重建与C3重建应各用一个干净副本；不要先重建C2再在同一副本验证依赖冻结散列的C3。
以下只物化本地提交，不接触远端：

```sh
SOURCE=/workspace/shared/valve-cloud-20261006
C2_REPLAY=$(mktemp -d /tmp/valve-c2-replay-XXXXXX)
C3_REPLAY=$(mktemp -d /tmp/valve-c3-replay-XXXXXX)
git -C "$SOURCE" archive 31662e66f0a14e426ab60b53c870f958a60f4ce1 | tar -x -C "$C2_REPLAY"
git -C "$SOURCE" archive 31662e66f0a14e426ab60b53c870f958a60f4ce1 | tar -x -C "$C3_REPLAY"
export VALVE_PYTHON="$SOURCE/.venv-cloud/bin/python"
export VALVE_DRAWING_PYTHON=/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python
export FREECAD_PYTHON=/usr/bin/python3
export XDG_CACHE_HOME=/tmp/valve-cache MPLCONFIGDIR=/tmp/valve-mpl
bash "$C2_REPLAY/runs/20261006/C2/verify_available.sh"
bash "$C3_REPLAY/runs/20261006/C3/verify_interfaces.sh"
```

这两条脚本只做研究几何/图纸检查，没有CFD/FEA求解器调用。
若环境缺失，先重新核查安装授权和锁定依赖，不能用未验证的替代运行时冒充复现通过。
CAD重建后的输出应作为新证据比较，不能改写冻结manifest以掩盖差异。

## 5. GitHub尚未同步

2026-10-06约16:50UTC只读核查：`main`、`design/c1-geometry-verification-20261006`、
`design/cloud-validation-20261006` 均仍指向上游 `4222b3d4df248b07777315068b9f3c99273d47c4`，没有打开的PR。
这是有时间界限的观察，恢复操作前必须重新读取。

此前已创建cloud-validation分支并确认写入28个独立blob；随后一批中的上传被取消，
其他并行返回未完全确定。没有创建新远端tree/commit、推进分支或创建PR，因此**成果尚未同步**。
取消的路径记录于 `checkpoint/state.json`。现有C1分支从未修改。

只有取消操作被明确恢复后才能重试：读取最新main/C1/目标分支与PR，比较实际差异；
在真实远端基树上加入需要的T04/C2/C3和文档，保留上游全部原始文件；
用预期SHA和 `force=false` 更新隔离分支，核实远端提交，再开draft PR。
不能直接推本地部分快照历史、强推、替换活跃C1或自动合并。

## 6. 求解器仍暂停

工作区 `/workspace/shared/valve-solvers-20261006` 内的 `evidence/approval-paused.flag` 仍保留。
OpenFOAM v1912已从签名核验的Debian包用户级解包，静态依赖可解析；运行基准没有执行。
CalculiX2.23尚缺 `libgfortran.so.4`。下载/解包官方Debian兼容库并探测 `ccx -v` 的操作被取消，
因此没有重试或另换途径。四个解析器单测通过只证明解析逻辑，不证明求解器能运行。

取消操作明确恢复后，先完成可追溯环境和标准已知解基准验收；只有真实输入受控后，
才准备本阀CFD/FEA，分别检查单位、边界、载荷、守恒、收敛和网格敏感性。
圆筒Lamé示例和网格生成不能替代实际阀体强度/流阻结论。

## 7. 下一次工作起点

保留C2/C3，在新研究目录C4先建立 `controlled_design_basis.json`，把上述输入、
来源、适用规则和仍未知项显式登记。按M01–M15依赖顺序推进材料、承压件、紧固/密封、
导向/驱动及完整图纸BOM。每步留下负向门和新证据，不把“程序通过”升级为“工程放行”。
最终制造放行仍需要适用的计算/实物试验证据及合资格工程审签。
