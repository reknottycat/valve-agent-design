# 原目标—实际完成—验收缺口（2026-10-26）

“已完成”只对应该行明确范围，不自动升级整体。原目标首先取原仓目标、C2 DELIVERY_PLAN 与冻结 R1；C0只作已纠错的历史。后建 Linear 票仅用于追踪后继证据。

| 原目标/交付物 | 实际已经做到 | 验证层次 | 未闭合/不可据此声称 | 主要来源 |
|---|---|---|---|---|
| 1. 图纸识读、来源及参数输入 | 已回原图纠正C0机构、600*/Ø320*、变型及标准用途误读；源/变体矩阵、9 个源/裁剪 SHA 检查；参数分级 | 来源与几何阶段检查 | 历史/派生资产统一总清单仍待补齐；不将内部假设当原图还原 | [C2原图纠错](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C2/T06/evidence_matrix.md)、C2 VERIFICATION；ZHE-82 |
| 2. 参数化 CAD 与可交换几何 | C2 七简化主件三姿态有效；27 STEP 回读；28 姿态干涉/平面接触检查；AGR1 后继 12 实体导入及 STEP 往返 | 真实 CAD 执行、有限几何/交换验证 | 不是完整原 BOM、制造细节或商业原生特征树等价；SOLIDWORKS 读取未实测 | C2；[AGR1 回读提交](https://github.com/reknottycat/valve-agent-design/commit/a374cf65f12a24044dddb59f9243c6fcabb74cb9) |
| 3. 图纸、BOM、交接文档 | A3 研究剖面 PDF/SVG/DXF、研究 BOM、审查 PDF；R1 39 页 PDF+可编辑 DOCX，78 原生公式/48 表 | 文件交付、渲染 QA、文稿生成一致性 | 不是完整受控制造图、公差热态/材料/连接/密封验收 | C2；R1 README/artifact_manifest |
| 4. 计算与结构验证 | R1 保留物性、双侧压力及驱动/接头敏感性；新六例阀瓣弹性参考解、两压力块 | 实际 FEA/原 DAT 绑定及算术核对 | C95800 研究替代+刚性无摩擦双边支承；单边接触 HOLD，峰应力未收敛，无许用比较/整阀耐压/泄漏 | R1 README；[结构原文](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/CALCULATIONS/R1/sources_new/STRUCTURAL_NEW/README.md)；ZHE-87 |
| 5. 工况与姿态恢复 | 20°C、35 g/kg 海水、57 mm 开度、Re10；入口79/出口34；历史名义 proxy +Z57 mm 证据恢复 | 固定研究输入、源哈希/几何姿态证据 | 源图57*是阀杆/手轮参考行程，不能直接证明自由阀瓣最大升程；本proxy将+Z57 mm显式用作研究姿态，并非口径（DN200）；不是实际额定工况、自然开启或 F80 真实密封边界 | R1 flow plan；[姿态证据](https://github.com/reknottycat/valve-agent-design/tree/affcdffac417bc1722e134f787a3580e4195f2a8/framework/cad/p08-pose)；ZHE-89 |
| 6. 网格生成与质量 | 实际从无四面体推进到 759760 个正体积四面体、132 patch；超阈 skew 面数降为0（最大 skewness 2.36008）；默认 Mesh OK | 真网格/原生检查；不是只写生成脚本 | 扩展检查仍 Failed 3：6988 low determinant cells、57 low weight faces、1 low volume ratio face；4064 严重非正交面另列。默认退出0不等全质量通过 | [网格与诊断提交](https://github.com/reknottycat/valve-agent-design/commit/e1b83cd7580cd18d627785baec5ca10b8a84d0d9)；ZHE-90；审计精选 |
| 7. 求解器/离散验证 | 三原生 Poisson 立方体；阀域制造解、格式/松弛比较；部分稳定指标改善 | 原生基准与数值诊断 | 立方体不替代阀域；759760 制造解联合门未达，场变化过门但原方程平衡未过；不把自建阈值称行业标准 | R1；研究摘录、ZHE-91/93 |
| 8. 代表域流动有限里程碑 | NSC1 真实 1147080 胞计算；续算至 time960 连续三段40步 ΔP变化<0.1% | 已核日志/趋势/来源，限定压降稳定门 | 不是全部方程残差门、网格无关性或整阀；960小包有场哈希但不含完整960场体 | [ZHE-88](https://linear.app/zhenhe-fu/issue/ZHE-88) |
| 9. 整阀代理研究流动及性能 | F80-B0 人工封口下真实运行到15及后续16/17，U/p/phi 与研究端口读数存在；诊断采集成功 | 有界真实运行及同版输出核验 | ΔP/ΔU反弹未消除，完整收敛/敏感性和实物边界未闭合；无可发布产品 Q/ΔP/K，不是无任何数字 | ZHE-91；研究摘录 |
| 10. 标准、公式与教材方法 | standards-kb 固定来源适配保留状态；六类机械公式说明/M01示例；新8教材候选+2项目方法、28 tests，独立包交付 | 来源/数据/校验器层，可复用 | 93条源记录状态不是93条独立工程认可；教材候选缺全文处明确待核；新本体尚未上游运行时接入 | [标准适配提交](https://github.com/reknottycat/valve-agent-design/commit/39b027d9f00580618ea8f1f3dede1fb3e3d230d3)；ZHE-84；Library 包SHA见证据 |
| 11. 编排、诊断与回归 | 私有源码保存、33基础测试里程碑；多次解析/守卫修复；同调用 shadow C++编译、3-cell LDU、2-cell真实fvMesh BC两方向检查通过 | 代码+合成/微型原生验证；各批不混加 | 不是通用自动设计插件或整阀求解证明；大case HOP尚缺严格解析/映射/监督器及运行验证 | ZHE-81/85/92；研究摘录 |
| 12. 完整工程验收、复用发布 | R1 manifest/freeze/197文稿算术检查/独审；后续14项验收切片、35来源、27测试；当前复盘 | 文档与有限审查基础存在 | CAD/BOM/计算/标准/真实边界/风险同版总清单未闭合；无制造放行、完整插件发布或实物E3证据 | R1；ZHE-93/94 |

## 可直接复用 / 仅可研究 / 不可发布

- **可直接复用（保持范围）：**来源清单、版本哈希、参数/单位治理、CAD交换回归、数据驱动计算书、研究图/BOM模板、标准适配和拒绝错误证据的测试。
- **仅作研究：**代理几何、参考 FEA、制造解、NSC1有限里程碑、F80-B0研究场、诊断观察器；保留各自假设/版本。
- **尚不能发布为工程结论：**整阀可信阻力系数/性能曲线、额定耐压/材料低温合格、密封泄漏合格、制造批准与通用自主设计成熟度。

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
