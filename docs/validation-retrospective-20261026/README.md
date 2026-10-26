# 阀门工程交付与错误方向复盘

核查日期：2026-10-26 UTC。对象：`valve-agent-design`，不是其他软件项目。原始目标是从 GA 图到参数、结构方案、CAD、CFD/FEA、计算验证和交接包；[C2原交付清单](https://github.com/reknottycat/valve-agent-design/blob/aa80b87b6ee9617754101a238f70bec99393ad9a/runs/20261006/C2/DELIVERY_PLAN.md)明确要求产物齐备、实测/缺口分开和独立复核后，才可称研究包完整。后续复用框架目标不能替代原工程目标。

## 结论

**可以下的结论：现有成果已形成有价值、部分可复用的研究原型与工程资产；尚不具备作为经验证的阀门工程设计工具进行可靠性能定型或制造放行的条件。**

**不能下的结论：全部不可用、没有结果、所有失败都是 OpenFOAM/Gmsh 的软件 bug，或换商业软件即可自动正确。**

最早、代价很大的方向错误是原图输入理解：C0把轴向升降候选误读为摆盘/配重机构，并混用了变型介质和尺寸含义。C2已回原图纠正，不能将这归因软件能力不足，也不能继续以C0契约作为当前设计事实。详见失败登记F00。

已完成的不仅是写代码：原始资料与哈希、参数化几何和 STEP 回读、研究图/BOM、R1 的可编辑计算书及 PDF、真实结构参考算例、真实代表域流动里程碑、实际整阀代理网格与研究流场、标准适配和诊断工具都有证据。未完成的是把它们闭合为同版、物理边界可信、数值收敛/敏感性充分、标准适用性已核、可工程验收的产品链。

这不是“用户没定义目标”的问题。R1 已冻结；既有研究输入已有来源。后续按假设推进的许可允许研究，但不会把人工封口自动变成实物边界。

## 阅读顺序

1. [完成清单](completion-matrix.md)：12 项原目标对照；“文件存在/单测通过/真实运行/工程验证”分层。
2. [失败与错误方向登记](failure-register.md)：保留失败、修复、混合结果和已撤回说法。
3. [软件能力边界](software-boundaries.md)：哪些是代码问题，哪些是数值/建模/证据问题；商业软件只作为有边界的比较候选。

## 57 mm与机构的精确含义

C0摆盘/配重机构已被C2原图复核纠正；当前C2是轴向升降研究候选。原图57*是阀杆/手轮参考行程，不证明自由阀瓣实际最大升程。冻结R1流动计划另将disc_lift_mm=57和stem_retraction_mm=57设为受约束的固定研究姿态；后续proxy的+Z57 mm几何验证只核名义位移，不预测自然开启、受力平衡或关闭行为。因此应称“固定57 mm位移的研究proxy”，不称“原图已证明真实全开57 mm”。

## 版本与结论边界

- 冻结 R1：`aa80b87b6ee9617754101a238f70bec99393ad9a`，本复盘不修改其内容、历史状态或原门限。
- 不同候选网格（614334、688424、759760）、不同算例（Poisson 制造解、NSC1 裁剪代表域、F80-B0 整阀代理研究）、不同 outer/求解配置不能拼成同一验收序列。
- 研究中间 Q/ΔP/K 与可发布产品性能分开；产品字段 null 表示未放行，不代表从无研究读数。Time 是稳态 SIMPLE 外迭代，不是实物时间演化。
- Linear 读取时为 22 票、5 Done/11 In Progress/6 Todo；8 父模块均未 Done。5 个 Done 是限定子成果，不换算工程完成百分比。
- 本包为精选文本证据归档，不含大场、二进制、凭证或用户原始图纸；未重跑求解器，未宣称所有历史失败已穷尽。未核到后继证据的项目明确保留未闭合。

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
