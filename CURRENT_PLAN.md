# 阀门工程：当前方案与交付入口

核对日期：2026-11-04，事实快照截至 09:59 UTC。**本文件是当前方案的唯一入口**；README 只保留导航与历史说明。后续沿用此路径更新，不再并列新增“最新方案”。

## 1. 目标、优先级与边界

先把用户选定的无后缀 **522-35.4179，DN200 青铜止回-截止阀** 做成可重复执行、可独立核查的流动性能研究链：参数与假设 → CAD 与湿域 → 边界 → 网格 → 求解 → 守恒、收敛及敏感性 → 流量 Q、压降 ΔP、阻力系数 K 的同版证据。再从真实链中提炼可复用工具，而不是另起一套万能 Agent。

**当前优先事项是修正已讨论公式、确定验收依据并接通两仓规则。** 本批在现行方案基础上，将已有研究预检入口接入只读标准 API/CLI，并更新导航；没有改研究模型、运行 CAD/CFD/FEA 或进行物理试验。以下研究成果是读取既有记录所得，不代表本次重新运行或恢复完整算例。

制造放行、完整生产 BOM、实物装拆和密封合格不是所有有限研究的统一前置条件。研究可以使用明确且可审查的假设，但不能把推导值、假设值、软件测试或数值收敛写成实物验证。C02 是独立候选，不是必须采用的基线。产品设计及制造验收另按九项卡逐项闭合。此区分与 [ZHE-93 的目标及交付记录](https://linear.app/zhenhe-fu/issue/ZHE-93) 一致。

产品范围固定如下：
- base：海水 −2～+50℃；**−02** 才另含 28% 氯化钙、−40～+50℃。base 的 −2℃液相/物性资格仍未闭合。
- СБ/SB 是装配图标记，不是 −02 型号后缀。
- 旧 C0“底铰链摆盘＋配重杠杆”解释已被后继来源否定；R1 采用轴向升降研究解释。真实自由升程、尺寸化内部件和传力链仍需核实。
- Ру6 原标记、条件换算 0.588399 MPa、0.63 MPa(g) 研究载荷，以及产品设计/额定/试验压力不是同一量。产品压力不能由研究选值自动确定。
- 20℃、盐度 35 g/kg、57 mm 研究姿态不是全服役范围或现场实测；57 mm 不能直接认作真实自由最大升程。

来源：[R1 研究依据](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources/C4/T06/research_basis.json)、[型号矩阵与历史纠错](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources/C2/T06/variant_input_matrix.json)。

## 2. 当前版本与跨仓依赖

| 对象 | 固定版本及角色 | 不能据此声称 |
|---|---|---|
| 本仓库 main | 本批接线前为 [4259a86a9147829ed4aac2fb5a433e213f64501e](https://github.com/reknottycat/valve-agent-design/tree/4259a86a9147829ed4aac2fb5a433e213f64501e)；本批仅移植并接通 [只读研究预检](framework/tools/README.md)，复用现有标准 API/CLI，其余研究线未整体迁入 | 整支研究线、CAD/CFD 编排或研究结果已集成；前列 SHA 是本批前版本，不是发布后的 HEAD |
| 标准库当前阅读及只读适配器依赖基线 | [19d586bb53cb452325d815313a895a1dfafa868b](https://github.com/reknottycat/standards-kb/tree/19d586bb53cb452325d815313a895a1dfafa868b)，已核为标准库 main | 自动成为本阀已批准的工程依据，或已被全部计算调用路径采用 |
| 阀门复用研究线 | [5dcc3b8302f566678259bcbeeb36a891a593eba6](https://github.com/reknottycat/valve-agent-design/tree/5dcc3b8302f566678259bcbeeb36a891a593eba6) | 整阀通过、已合 main 或原生 runner 已完整交付 |
| P08 C02 独立候选 | [e008a3939a7730b3aedbbf3c0b54ceac1a58663d](https://github.com/reknottycat/valve-agent-design/tree/e008a3939a7730b3aedbbf3c0b54ceac1a58663d) | 已与复用研究线合并、全行程/装拆/密封已验 |
| R1 冻结来源 | [aa80b87b6ee9617754101a238f70bec99393ad9a](https://github.com/reknottycat/valve-agent-design/tree/aa80b87b6ee9617754101a238f70bec99393ad9a) | 可回改历史消除冲突，或已制造放行 |

标准库 19d586b 比 fc62e1f 仅多同步工具的只读检查修复及测试，公式/验收卡数据未变；`--check` 不应再写文件，错误与差异分开返回。该修复不证明现有镜像已经无差异，也没有自动重新生成资产。

**main 的只读标准 API/CLI 已接通 19d586b，既有研究预检入口已消费它；完整设计/求解调用链尚未接通。** 当前 [适配器](framework/standards/README.md) 用生产锁验真 20 个依赖，在同一入口实际调用公式一致性、三条输入语义元数据、法兰使用隔离及当前验收卡护栏；不是只改版本号。源库数据仍在外部快照，不复制标准表入本仓库。

研究线的 [旧适配器](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/standards/PROVENANCE.md) 仍固定 `7eda528a8795b8fbd850d6d35ac67e198de5810a`，只覆盖单个 ГОСТ 文件的真实测试，现作为历史保留。main 当前入口拒绝旧 pin、变更数据及自行重哈希的 manifest；不在 main 另开可执行旧源入口。当前 main 的 [valve_readiness 研究预检](framework/tools/README.md) 已在同一研究输入检查中消费新适配器。历史 C0 脚本、网格建议及任务拓扑检查仍未调用它，本批不会拦截人直接运行旧脚本。研究分支中的旧 readiness 保留为历史，不因 main 更新而自动变化。

本仓库 main 未设 STATUS.md；当前状态集中于本方案，不新增平行状态页。旧研究分支和旧文档中的“当前”“下一步”均须结合其日期与固定提交阅读。本次不删除、改写或全量合并任何历史分支。

## 3. 成果清单：价值、限制与当前入口

| 成果 | 已有有限证据 | 当前不能证明/待补 |
|---|---|---|
| R1 输入及型号绑定 | 型号、工况、假设与来源散列分离；上述两个 R1 JSON 为固定入口 | 材料牌号、设计温压、实际介质物性和产品试验条件获批 |
| AGR1 中性 STEP 往返 | 历史实际导入、导出、回读为 12 个有效实体，比较体积、包围盒、质心和拓扑计数 | 装配干涉、公差、BOM 身份、商业原生特征树、制造放行 |
| DRS1 / CRM1 | 历史真实阀盘两网格结构研究及自由开闭接触模型可复用 | 峰应力局部收敛、真实连接/预紧/热态公差、胶料和泄漏 |
| NSC1 局部流动 | time960 局部压降稳定有限里程碑已有记录，无需重复算作新成果 | 整阀稳态、网格无关性或真实产品 Q/ΔP/K |
| 整阀连续计算 | ZHE-93 已记录 p 松弛 0.3 主轨迹到状态 21；17→21 原始动量 L2 下降 68.47%、体积 RMS 下降 12.29% | 20→21 端口静压差仍变 19.43%，总研究信号 false，未稳态；本次未重验数值场或真实重启 |
| p=0.15 对照 | 已有两步配对试验结论 NOT_SUPPORTED，失败/退化证据保留 | 不支持替换主轨迹；也不证明 0.15 长期无效或 0.3 最优。不重跑此对照 |
| 离线 continuation 审计 | 11 月 4 日交付 6 个最终工具文件，固定两步协议的日志/身份检查 | 不是求解器启动器，不含原生 runner、日志或完整场；检查通过不授予真实重启资格 |
| P08 C02 台肩 | 单个全开姿态 CAD 有效及零正体积干涉记录 | D40 杆头不能穿 D36.4 肩孔；装拆未验；候选流体体积平衡差 −0.030874 mm³ 待核；原 face80 已改变，不能直接沿用旧边界/流场 |
| 编排与适配工具 | main 的标准 API/CLI 及选取的研究预检已接当前规则；研究线其他契约、CAD 探针和离线审计仍属可复用历史 | 不是完整 CAD/CFD 编排集成、自主 Agent 或 MCP 服务；真实端到端、取消、恢复与幂等链未闭合 |

固定入口：[已有成果矩阵](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/research/reusable-framework-20261022/README.md)、[STEP 往返范围](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/providers/step-roundtrip/README.md)、[离线审计工具](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/tools/continuation_audit/README.md)、[P08 C01/C02](https://github.com/reknottycat/valve-agent-design/blob/e008a3939a7730b3aedbbf3c0b54ceac1a58663d/framework/cad/p08-packing-design/README.md)、[ZHE-93 的 11 月 1 日及 11 月 4 日记录](https://linear.app/zhenhe-fu/issue/ZHE-93)。上述既有记录均需保留原工况与范围，不跨模型拼接。

## 4. 公式与验收：已经修正什么，还差什么

### 已写入标准库 main 的纠错

- 核心公式与元数据：厚壁圆筒内壁环向应力、Kv 多余除数及反式、手力的 N·m→N·mm 换算、Cv_US 与 Kv 的量及绑定已纠正。对应 [当前核心条目](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/kb/formulas/seed_core.json)。公式自洽不等于本阀已重算或工程适用性已批准。
- 驱动输入：螺纹升载需求力矩不再称纯摩擦损失；它不是整机总力矩，支承、填料、密封及启动附加另审。运行摩擦 μk 与静摩擦 μs 分开，不能凭运行扭矩判断静态自锁。安全阀容量公式的 L 绑定试验压力下升程，不能随意替换为额定升程。标准库原检查是需主动调用的三条元数据合同；本仓库当前适配器已在每次构造时调用，但仍不是全局运行时输入守卫，也不认证真实摩擦或升程试验。见 [输入语义与检查范围](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/formula-input-semantics.md)。
- 碳当量和热处理：条件替代、质量百分数尺度、同版来源关系及精确阈值比较已修正；不同版次、不同材料条款不能合并成一个通用规则，更不自动适用青铜阀。见 [碳当量说明](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/carbon-equivalent.md)。
- 验收卡、型号绑定、图面要求、压力来源缺口及有限防误用门已有实现。**13 条 GB/ГОСТ 法兰记录只完成隔离门，完整数据纠错尚未写回**，不得见旧 VERIFIED_CLAUSE 标签便用于工程。见 [法兰隔离边界](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/flange-quarantine.md)。

在 19d586b 的条目数据中，23 公式＋57 参数＋13 表共 93 条，自报状态为 50 VERIFIED_CLAUSE、16 PENDING_VERIFICATION、17 UNVERIFIED_CLAUSE、10 CONFLICT；另有 2 条派生记录均 PENDING_VERIFICATION。95 条均标 E1。**这不是 95 条独立工程批准，也不是“93 条已核”。** 来源状态、模型算术、对本阀的适用性和产品验证必须分别记录。

### 当前适配器实际接线

[使用入口](framework/standards/README.md) 与 [固定来源/范围](framework/standards/PROVENANCE.md) 说明 API、CLI、20 个生产依赖和信任边界。实际运行读取全部 95 条研究记录，上游源级计算资格为 **44 条**；13 条法兰表与 2 条相关派生记录均被隔离。来源资格不等于适用于本青铜阀，项目适用性仍未确认、工程放行始终 false。

同一入口读取当前正确 Kv 条目、核其合成样例与反式，再实际调用当前验收卡评估。只接受生产锁中的固定卡，不接任意外部候选卡；同 ID 换配置或混入 −02 盐水也会被字节绑定拒绝。这不是独立认证配置摘要，更不是新物理计算。

### 当前验收结论

[AC-VALVE-001](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/kb/acceptance/AC-VALVE-001.json) 的设计材料、尺寸、壳体强度、密封、流量止回、操作、制造、综合放行资料、独立试压安全九项，实际观测均 UNKNOWN，批准均 false，评估仍 **9 项 HOLD、工程放行 false**。27 个待批数值限值及对应来源/批准记录仍空。软件测试通过不能消除这些缺口。

原图并非没有要求：液阻≤6、参考 9.5 圈、特定条件辅助扳手≤45 kgf、噪声≤70 dB、寿命与可靠性已有记录；测量定义、完整条件和采用/批准未齐，不能把研究静压 K 或力矩直接与之比较后放行。M14 粗牙指定表行的 115 mm² 也不是实装螺纹、数量、预紧与载荷已经确定。

剩余问题按依赖归类：
1. **来源/采用**：原图引用的 ГОСТ356-80 历史版次、寿命与材料关系、ГОСТ1536-76、ОСТ5.5131-73、Л-ПСП-4035-85、01-1874-62 及产品修订链仍需受控依据；现代 GB/ASME 不能自动替换。ISO5208 等有限预览不能补齐压力、保持时间、泄漏与本复合阀适用性。不默认 1.5PN。
2. **明确冲突/隔离**：法兰完整数据更正尚未入库；量纲或原文有冲突的历史公式继续隔离，不能猜数字、转抄版权全文或变换格式规避限制。
3. **本产品输入/实体证据**：材料牌号与产品状态、温压历程、允许值、公差/实际几何、摩擦润滑、制造/NDT/试验记录尚欠。缺哪一项就限制对应结论，不笼统阻断全部有限研究。

依据：[公式与验收收口](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/valve-formula-criteria-completion.md)、[来源收口](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/valve-source-closure.md)、[压力及产品来源缺口](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/valve-pressure-source-gaps.md)、[31 条图面要求](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/valve-drawing-requirements.md)、[验收框架](https://github.com/reknottycat/standards-kb/blob/19d586bb53cb452325d815313a895a1dfafa868b/docs/valve-acceptance-framework.md)。

## 5. 下一步只按依赖推进

### 第一优先：公式/验收已进入真实研究预检，仍保留证据缺口

沿用 [M02 / ZHE-84](https://linear.app/zhenhe-fu/issue/ZHE-84)。[研究预检入口](framework/tools/README.md) 从固定研究线选取既有 `audit(meta, case)` / CLI，只迁必要代码与测试，没有合并整支研究分支。它在同一次输入检查中读取研究声明的标准引用与用途，调用当前 adapter，并列返回物理预检、源级使用资格和固定验收卡结论。不是仅新增无人调用的自测，也不把任务拓扑校验器改称求解入口。

**已完成的有限范围**：原有作用域、预算、边界/压强角色、网格和算例文件预检继续保留；当前标准引用、旧版本/错式拒绝、隔离、未知引用和型号声明另行检查。`preflight_pass` 仅代表旧有限检查，不代表标准依据齐备；CLI 的整体状态和退出码见模块说明。九项工程 HOLD 与研究检查分列，不作为所有有限研究的统一禁令，亦不能被研究检查成功覆盖。引用可读取不等于获准作为计算或规范依据。

实际回放[原 P08 研究输入](https://github.com/reknottycat/valve-agent-design/blob/5dcc3b8302f566678259bcbeeb36a891a593eba6/framework/evidence/p08_readiness_input.json)时，边界未核、未确认保留流体网格、网格质量未过、未检查完整算例四项原失败全部保留，标准声明另列 INCOMPLETE。添加声明的合成接线检查仍不消除这四项；不是新 P08 配置或求解成功。

**仍欠**：真实几何/材料/边界与来源的完整绑定、标准适用与采用批准、公式实际输入及求解器消费者。型号文字匹配不认证配置、R1 字节或真实物性；原预检不解析完整边界或证明网格拓扑。现有元数据检查也不认证真实 μs、压力 P 下试验 L。没有新 CAD/CFD/FEA、物理试验或工程放行。

**下一步完成标志**：在明确同版研究输入后，将必要公式的具体数值、单位、参考量与使用条件连到真实消费者，而非把源级 44 条资格直接当本阀计算许可。**停止条件**：必需来源/依赖缺失、跨型号误用或语义不兼容时，保留失败并报告影响，不伪造通过或复制隔离数据补洞。公式/验收仍优先，未因此启动新设计或大计算。

### 第二优先：固定一条同版研究基线及可复现输入

沿用 [M01 / ZHE-82](https://linear.app/zhenhe-fu/issue/ZHE-82)、[ZHE-90](https://linear.app/zhenhe-fu/issue/ZHE-90)。先从已有资料恢复必需小文件，逐项区分“已列出、正文已读、字节已验、已恢复、已复现”。选择一个明确的研究几何/湿域/姿态/边界及材料物性假设，不能拼接旧 P08 的流场和 C02 的几何。

**完成标志**：同版 CAD/湿域/patch/输入 manifest 与运行环境可被独立读取；真实输入与研究假设分列。若选择 C02，须先复核其布尔体积差及新边界身份，不能继续沿用 face80。若不选择 C02，其装拆、强度、泄漏欠项不作为旧研究基线的统一阻断门；它们仍禁止相应实物/制造结论。

### 第三优先：只补缺失的有限验证

沿用 [M06 / ZHE-91](https://linear.app/zhenhe-fu/issue/ZHE-91)。只有同版原生输入、场、日志、可核重启点与适用边界具备后，再制定最小新问题、资源预算和预先停止条件。分别核线性残差、守恒、局部尾部、稳态、网格敏感性与 Q/ΔP/K 定义。不重算 NSC1 已达里程碑，不重跑 p=0.15 既有对照，不靠换参数或任意迭代步数制造“绿灯”。

**完成标志**：输入、命令、结果和证据可独立核查，研究判据注明是项目判据，适用限制未被隐藏。有限研究通过仍不是整阀产品通过；没有完整原件时只声明读过记录，不声明已恢复/可重启。

### 最后：同版研究交付与产品验收分开

沿用 [M07 / ZHE-93](https://linear.app/zhenhe-fu/issue/ZHE-93)。先交假设明确、可复现的研究包；产品验收需九项卡的适用条款、批准输入、真实观测及独立审核逐项齐备。M05 的材料、连接、密封、装拆与实体试验分别限制相应产品结论。缺失的专有资料按具体文件列明合法获取路径，不反复要求用户提供其没有的专业图纸。

## 6. 八模块保持同一个看板

不另建平行任务。[Valve Agent Framework 看板](https://linear.app/zhenhe-fu/project/valve-agent-framework-阀门工程复用与交付-066366016831) 的八个父模块目前均未 Done；子任务 Done 只代表该票的有限范围。

| 模块 | 当前应交付的结果 |
|---|---|
| M01 来源资产 | 一个版本清单，逐项说明来源、SHA、模型/工况和可读/恢复/复现状态 |
| M02 公式标准 | 必需公式/标准的输入、单位、假设、来源、适用与批准条件；接通当前规则 |
| M03 编排工具 | 一条真实小流程及取消、恢复、失败、重复执行验证，不只接口草图 |
| M04 CAD | 同版参数/装配/湿域映射及交换检查；研究几何与制造结论分别标注 |
| M05 结构驱动密封 | 真实载荷/材料、局部收敛、连接预紧、热态公差、驱动及密封证据和剩余实测项 |
| M06 网格流动 | 同源边界、质量、原生 case、Q/ΔP/K 及守恒/稳态/敏感性证据 |
| M07 证据交付 | 每个结论回链输入、版本与结果，独立复核，失败/未知不隐藏 |
| M08 复用准备 | 真实链跑通后再提炼安装/接口/脱敏示例/许可清单；保持私有，公开发布另行决定 |

## 7. 历史保留与交付纪律

- [README 中折叠保留的旧说明](README.md#historical-readme) 及原始 C0 文件是历史，不再作为现行型号、机构、材料或验收结论。特别停用旧摆盘解释、base −40℃盐水、As=147 已解和“93 条已核”说法。
- 标准库旧 README/STATUS 计数、旧“5.092 官方漏点定案”、旧低温条件合格说法不覆盖当前条目与冲突记录。历史候选可查，但不等于最新规则或已适用本阀。
- 研究线及候选分支按上面的固定链接读取；包含某分支祖先不等于包含另一独立分支的最新更改。历史报告不复制成多份活跃真源。
- 原始证据、反例和失败保留，不删分支、不改 R1。本批只交付必要的研究预检代码、测试、正式说明与当前入口更新；复用既有生产依赖锁，不上传过程日志、计算场、临时工件或标准全文。
- 每批先明确问题、固定输入、允许范围、交付物、通过/停止条件；结束只报告实际改动、实际验证、仍不能证明的内容和一个当前版本链接。按关闭的工程缺口计进度，不累加测试数、分支数或文档数充当完成率。
