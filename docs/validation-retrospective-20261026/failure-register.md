# 失败、错误方向及已纠正说法登记

范围：本次能回链的重大失败和方向性误判，不冒称穷尽全部历史日志。**已修复的失败仍保留；未被证明的因果只标假设。** 原失败不能被新成功覆盖掉，但当前状态应由后继证据更新。

| ID / 案例 | 失败/误判和位置 | 原因可信度 / 分类 | 后继与当前状态 | 教训 / 证据 |
|---|---|---|---|---|
| F00 原图/机构/变型误读 | C0把竖直阀杆/水平阀瓣理解为底铰轴摆盘+配重；600*漏读/取300，Ø320*手轮误作杠杆跨度，57*参考阀杆行程混作自由阀瓣升程；-02氯化钙低温强加基本型；note30防松误作IP、GOST356压力系列误作垫片、旧图像SHA错误；注24阻力与注23振动混淆、全图无受控尺寸概括过宽 | 原图复核已确认输入/推理错误，不是求解器bug | C2改轴向升降研究候选并保留原错误；基本型海水已选；57 mm proxy姿态仍为独立研究选择，不冒充图纸已证明自由最大升程 | [C2纠错原文](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C2/T06/evidence_matrix.md)、[原交付清单](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C2/DELIVERY_PLAN.md)；包内两原文快照。先纠输入再算，不能修错误拓扑使其连通就说合格 |
| F01 C2接触 | 体积干涉检查漏掉阀体/阀座共面意外接触；移除2mm凸起产生3928.43mm²意外接触 | 已独立复现；几何检查覆盖缺口 | 新增面接触负对照，研究几何纠正；非制造认证 | 只测体积重叠不够；C2原文 |
| F02 STEP积分 | 非自适应体积积分导致lofted STEP测试失败 | 实测数值积分路径 | 自适应1e-9积分后通过，未放宽交换阈值 | 不把测量算法误差当CAD损坏；C2原文 |
| F03 Gmsh 3D | PLC segment/facet intersection，0 tetra；源面64/108间1mm间隙被粗弦近似穿入 | 相交位置和弓高已定位；不能推CAD无效/算力不足 | 局部尺寸处理后真实体网格产生；几何近似问题已推进 | [3a8e189](https://github.com/reknottycat/valve-agent-design/commit/3a8e189d87893da5cefbeca9f9274353aa82fcdc)；失败表面ZIP SHA `9ec3e43fb2764aee9b8c5fe0886ecfe87fa718f670b46a8dd61849ff98684400` |
| F04 局部重网格 | MeshOnlyEmpty仍重建非目标；toy MeshOnlyVisible清掉其他网格 | 已观测工具选项行为，不等通用软件bug | 该路线拒绝；新粗2D+局部控制替代 | 不声称旧表面完整保留；F03提交 |
| F05 dual0候选 | Failed10、55非正体积cell、empty zone | 实际劣化候选 | 拒绝，未作为CFD基础；原失败保留 | [2846901](https://github.com/reknottycat/valve-agent-design/commit/2846901facaba00553baedc406265e8fa29cf359)；原包SHA `f7f1fdee1b14ad3d6eb5cad9b28b63695502b03f96381069c4a9623d9bc9256a` |
| F06 网格“改善=通过” | 230553、614334、688424、759760各候选有不同质量失败；平均值改善不消除尾部 | 确定质量观测；尚未全因果解释 | 759760仍Failed3；默认Mesh OK未检查同一扩展项 | exit0、正体积、超阈 skew 面数为0都不是全验收；ZHE-90/审计 |
| F07 制造解 | 614334 corrected发散；limited30轮误差较小但稳定门未达；759760后续联合门未达 | 实际数值失败，非实物流动不稳定证明 | alpha0.5改善场变化至7.385e-11，但平衡1.289e-7>项目1e-8 | 不挑单一好指标；[59cfab9](https://github.com/reknottycat/valve-agent-design/commit/59cfab96f3abf7bab26a28db423d15083b282af9)、研究摘录 |
| F08 松弛/求解器选择 | 匹配laplacianFoam无relax调用，配置relaxationFactors不生效；scalarTransportFoam即使零对流仍非对称存储，PCG不适配 | 已核匹配源码/实际桥接 | 改用匹配PBiCGStab路径，限定A1/A2桥接；不是盲加配置 | 配置存在不等调用发生；ZHE-91、制造解来源 |
| F09 初始化/后处理 | postProcess function-object SHA1问题；setExprFields自引用失败 | 环境/集成已观测，非流动发散 | 真实simpleFoam start=end=0初始化成功；失败保留 | 初始化成功不计稳态成功；pilot证据 |
| F10 首步观察器 | outer1已写场，outer2观察器Missing value导致主动终止；合法noSlip/zeroGradient无显式value被拒 | 已定位解析器缺陷 | 按原生owner/BC语义离线修复32tests；后续独立恢复2–15完成 | 不能写成求解器崩溃；checkpoint manifest SHA `0708e96006e22b54f9a3bda61d95a1bb575482f42e0ddf054a8781f5f72a0906` |
| F11 收紧p.relTol | 0.05→0.005，local变好，但outer3全边界不平衡1.0215%→2.21074%，压力换号未消失 | 同起点单变量限定对照；不是所有原因隔离 | “只收紧压力线性残差即可修复”不被支持 | 不盲扫参数、不只报改善；p对照摘录 |
| F12 压力分母/时相 | 把变化全归小分母，或用松弛后保存p重建final solve、对比不同时相 | 来源/公式审计纠正 | 分母放大存在，但端口ΔP也真实变化；p.relax前后/phi时相已区分 | 小残差≠外层收敛；负表压≠负绝压；压力路径摘录 |
| F13 局部诊断测试 | 两解析器失败；独立测试首次7pass+3 NameError；曾过早标通过 | 软件/报告流程错误已确认 | 修独立runner后10/10；先前通过声明已更正 | 必须等真实终态，不能把测试计划写成完成；局部诊断摘录 |
| F14 阶段采集监控 | monitor MemoryError，0事件、子进程被回收 | 启动监控缺陷；历史失败具体分配不可追认 | 可复用64KiB readinto+预拒绝+固定系统Python，在原32MiB监控预算通过；新恢复成功 | 不归为solver耗尽/流动发散；恢复12普通输出hash同基线；修复摘录 |
| F15 CPU继承 | supervisor固定CPU(2,2)，继承hard<2时消耗锁后失败 | 已复现守卫缺陷 | 新overlay在latch/fork前拒绝，58断言；不改原冻结包 | 合成成功不保证所有继承限额；ZHE-91 |
| F16 正常FPE横幅 | guard以“Floating point exception”子串误杀正常trapFpe banner；0MBP | 已定位监控分类bug，不是实际浮点异常 | 精确正常字节豁免+53反例测试；新隔离恢复13MBP/8summary成功，旧锁/日志留存 | 正常启用FPE trapping≠触发FPE；恢复/分析摘录 |
| F17 收紧U.relTol | 0.05→0，6分量从3次到17–19次均达abs1e-10，外层16/17变化反增1.747%/3.121% | 限定同起点/轨迹依赖对照 | “相对停止足以解释反弹”不被支持；不能说完全无影响 | 不把17当固定矩阵纯因果；U对照摘录 |
| F18 松弛残差误读 | relaxed残差大幅降而raw只降11.208%；ΣDrel/ΣDraw=1.484112不等1/0.7 | 实际观测+源码代数 | 不再用D/α简化全部边界/对角增强，不以relaxed代raw；根因未证明 | 动量分析摘录 |
| F19 held诊断准备 | tmp/Field比较、缺WM_PROJECT_DIR、directionMixed头文件猜测、Info.precision、str/Path helper不匹配 | 确定C++ API/fixture/harness缺陷 | 编译/微型运行前逐项修正；3-cell和2-cell通过，保留旧日志/版本 | 不等759760整阀通过；held两报告摘录 |
| F20 资产/发布 | 运行工作区丢失后旧口头数值不能当证据；分片blob/staging tree不等branch已交付；bulk上传被用户叫停 | 交付可追溯性/流程问题 | R1重建与来源冻结；后续采用精选证据。本包新授权独立发布，不虚报历史全部同步 | R1 README；不再默认大场入Git |
| F21 错误总括 | 曾概括“没有CAD/从未真实流动/680未达门仍为当前/4096整阀硬上限/没有标准库/没有任何QΔPK数字” | 与后继原件矛盾，已撤回 | OCP真实CAD、NSC1 time960、固定标准库及研究读数均已恢复；4096只局部元数据对照预算 | 不把过时摘要变现状，不归责用户；完成清单 |
| F22 验收偷换风险 | 8父模块未完成，却把5小票Done或测试数量换算工程完成；默认MeshOK、库E1、教材方法当放行 | 结论层级错误，明确禁止 | 当前仍研究/未放行；不编造百分比、不事后降门 | 原R1、ZHE-93 |

## 已识别的路线风险（回顾性判断）

在成熟同输入参考基线尚未建立时，较多投入自定义求解器内部诊断和保护性工具链，增加了工程维护/机会成本。此项是基于交付结构的路线复盘，不是外层反弹的已证原因，也不是商业工具一定更好。后续以有界比较决定是否替换后端，详见软件边界。

## 尚未定位为 bug 的问题

F80人工截断与真实填料/泄漏边界缺口；物性/额定载荷适用性；网格尾部质量对误差的具体作用；外层反弹根因；自然开启、接触、低温/密封/制造验证。它们都不能靠“修一个软件错误”自动闭合。图跳数远离cap或热点不在坏元集合，只是空间关联，不能排除全局压力耦合或网格原因。

## 证据入口

- [原工程目标/证据等级](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/README.md)
- [原 C0 设计契约](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C0/T06/design_contract.yaml)：历史探索基线，不将其中历史“无求解器”等状态当作现在。
- [C2 几何阶段独立记录](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C2/10_handoff/VERIFICATION.md)
- [冻结 R1 交付说明](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/README.zh-CN.md)
- [冻结 R1 流动计划与五项前提](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources_new/FLOW_PLAN_NEW/flow_study_plan.json)
- [R1 文件身份清单](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/artifact_manifest.json)
- [当前整阀研究记录 ZHE-91](https://linear.app/zhenhe-fu/issue/ZHE-91)
- [同版交付与验收 ZHE-93](https://linear.app/zhenhe-fu/issue/ZHE-93)
- [工程复用项目](https://linear.app/zhenhe-fu/project/valve-agent-framework-阀门工程复用与交付-066366016831)
- 本包 [原文快照](evidence/original-source-snapshots.json)、[精选研究原文/哈希](evidence/research-excerpts.json)、[证据清单](evidence-manifest.json)。快照证明本次读取内容；不是重跑或新工程批准。
