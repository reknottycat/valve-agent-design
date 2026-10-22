# 开源优先的阀门工程工具适配矩阵

核实日期：2026-10-22。只读官方资料研究；未安装或运行工具。下列为候选适配设计，不代表插件已实现、工程验证通过或商业许可已取得。

## 结论

先接现有专业工具，不重新造 CAD 内核、CFD 或有限元求解器。首期选择一种建模前端（CadQuery 或 FreeCAD），以受控计算规则形成可测试闭环；按任务增加 CalculiX / OpenFOAM。多学科耦合与优化成熟后再引入 OpenMDAO，而不是首期全部部署。

| 工具 / 定位 | 已核接口与格式 | Agent 适配真实程度与推荐 | 许可与工程边界 |
|---|---|---|---|
| **CadQuery**：脚本参数化几何 | Python API；STEP/DXF 导入，STEP/STL/DXF 等导出。官方明确交换格式不携带其完整参数化数据，完整参数定义保留在 Python 模型 | 适合封装版本固定的参数模板与白名单几何操作；不是已验证的阀门 Agent。禁止让任意模型代码直接在宿主无隔离执行 | Apache-2.0；仍须核 OCP/OCCT 等依赖许可。保存脚本、参数、环境锁与 STEP，不把 STEP 说成原生历史树。[格式](https://cadquery.readthedocs.io/en/latest/importexport.html) / [许可](https://github.com/CadQuery/cadquery/blob/master/LICENSE) |
| **FreeCAD**：人工可审查 CAD 与工作台 | 官方 Python 绑定、宏、工作台扩展；原生 FCStd，STEP/IGES/STL/DXF 等交换 | 适合需要 GUI 审阅、工程图和人工修订的团队；本次仅确认可编程能力，未确认官方生产级 Agent/MCP 适配。与 CadQuery 首期二选一，避免双重模型真源 | LGPL；具体发布版、插件、依赖逐项登记。格式列表不意味着每种格式、所有平台及参数历史均无损。[官方功能](https://www.freecad.org/features.php?lang=en-UNIVERSALITSOLUTIONS) / [官方源码说明](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/The_FreeCAD_source_code.md) |
| **CalculiX**：结构与传热分析 | 官方支持线性/非线性静力、稳态/瞬态传热、热机械耦合；文件驱动求解器，应由 adapter 生成并核验输入 deck、解析输出。输入风格基于 ABAQUS，但不能据此声称完整兼容或结果等同 | 适合受控载荷/边界条件的壳体结构、热分析候选；须先做基准题、网格与收敛检查。没有证据证明开箱即用的官方 Agent | 官网许可 GPL-2.0-or-later；实际选定源码/二进制与链接求解库另核。商业使用与再分发义务不能混为一谈。[能力](https://www.dhondt.de/ov_calcu.htm) / [输入边界](https://www.dhondt.de/) / [许可](https://calculix.de/) |
| **OpenFOAM**：流动/传热数值执行 | CLI、case 文件、网格/后处理工具；官方说明适合自动化与批处理。表面网格（如 STL）到体网格仍需专门步骤，不能拿 STEP 直接当 CFD 完整工况 | 包成 `prepare_case / validate_mesh / submit / status / collect`；由工程师批准物性、湍流/多相模型、边界条件和收敛标准。它不是 LLM Agent | 所核 openfoam.com 分支 GPLv3；锁定发行分支、版本、求解器，不能混用不同分支案例。[CLI](https://doc.openfoam.com/2606/fundamentals/command-line/) / [工具](https://www.openfoam.com/documentation/user-guide/a-reference/a.2-standard-utilities) / [许可](https://www.openfoam.com/documentation/licencing) |
| **OpenMDAO**：跨学科组件与优化编排 | Python 组件；ExternalCodeComp 将外部程序作为子进程，支持输入/输出文件、返回码、超时与轮询；File Wrapping 提供模板生成和结果解析 | 适合复用现有自研计算器及有合法批处理接口的商业程序；不是 CAD/CFD 求解器，也不等于完整持久化任务队列。Agent 只提交受控参数，不能任意更改优化约束 | Apache-2.0；外部程序许可独立，不能因套一层 wrapper 就获得自动化/并发席位。[接口](https://www.openmdao.org/newdocs/versions/latest/features/building_blocks/components/external_code_comp.html) / [文件封装](https://openmdao.org/newdocs/versions/latest/other_useful_docs/file_wrap.html) / [许可](https://github.com/OpenMDAO/OpenMDAO/blob/master/LICENSE.txt) |

## 商业工具兼容与开放交付

- SOLIDWORKS 官方确认 STEP 导入/导出，可导入为零件/装配体并传递几何、拓扑及部分颜色/配置数据。它证明开放交换路线可行，不证明源软件草图约束、特征树、装配配合或仿真研究无损往返。[官方 STEP 文档](https://help.solidworks.com/2026/english/SolidWorks/Sldworks/c_Step_Files.htm)
- 保留商业 CAD/热学/流动工具的 provider 接口，但每个具体产品需另核 API/批处理支持、宿主平台、版本、自动化许可、席位和数据边界；本研究不保证任意商业软件可接，也未采购许可。
- 推荐交付包：原生模型（在授权情况下）＋参数源/建模脚本＋STEP＋二维 DXF/PDF（按用途）＋BOM＋计算输入输出与日志＋适用工况＋标准版本＋文件摘要。每次转换都记录单位、坐标系、装配结构、实体数量、关键尺寸及几何校验，暴露丢失项。
- STL 是离散网格用途，不代替精确几何/参数模型的唯一归档。

## 必须由我们的适配层补齐

工具清单、稳定 schema、版本/能力探测、受控运行目录、作业 ID、状态/取消/资源预算、原始日志引用、normalized_result、coverage、unknowns、limitations、变更后失效规则与人工放行。进程退出码为零不等于计算有效；软件能力不等于阀门规范符合性。

工程手册知识条目至少含：书名/版次/出版年、章节/页码/公式号、授权范围、符号与单位、输入来源、材料/温度/几何/载荷适用域、假设、插值规则、禁用条件、测试样例、审核人、与规范冲突的处置规则。模型不得自行设定或放宽强制标准。

许可提示：开源允许商业用途不等于无条件再分发。分发前固定版本并审核 LICENSE/NOTICE、修改说明、对应源码/重链接等适用义务及依赖；不能仅凭主仓库标签得出整个产品许可结论。私有工程输入不会仅因使用开源工具而自动变成开源资产。
