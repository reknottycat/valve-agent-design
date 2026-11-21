# Drawing-to-valve：基于已有资产的框架草案

这不是已经实现的一键制造工具。先把现有工具变成带输入/输出契约的可靠模块；框架与领域知识通用，项目图纸/几何/客户数据独立私有。Google/REA出处由研究线另核，本文件不声称复制其实现。

## 本体：最少且够用的对象
- Requirement：值、单位、原图页/标注、用户决定/规范/研究假设、版本。
- Part / Assembly / Joint：实体hash、姿态、坐标系、材质状态、制造连接和公差。
- LoadCase：方向、表压/绝压、有效面、接触/运动状态、温度、版本。
- Domain：geometry_ref、实体/流体、裁剪/全域、边界映射、保留/省略物。
- Material：牌号、产品形式、温度、数据来源、适用用途、unknown字段。
- Run：输入hash、工具/环境版本、命令、预算、exitcode、产物hash、log。
- Observation：值/单位、测点/积分口径、所属域、误差/敏感性。
- Gate：目的、阈值来源、适用域、满足证据、failed/unknown/pass。
- Artifact / Claim：原件与提取文本分别标识；每条结论链接证据，不以任务完成状态代替。

关系包括 derives_from、uses_geometry、under_load、validates、supersedes、invalidated_by。几何/BC变化沿依赖边标陈旧；不清空不相关已通过成果。

## 三层落实到已有工具
|层|实际职责|已有资产/下一步适配|
|---|---|---|
|认知编排|确定本次观测量、拆任务、优先复用、处理失败原因、合并证据|从图纸需求→运动/载荷图→选择AGR1/CRM1/DRS1或CFD；失败先判单位/姿态/边界/质量/资源，不无限升网格|
|计算执行|确定性Agent Tools执行；模型只选择工具和解释结果|R1 calculate_loads.py/pressure面提取；STEP独审；CRM1 contact_ring.py与独立energy FE；DRS1原生输入和场独审；OpenFOAM日志/守恒读取|
|贯穿治理|身份、范围、可追溯、保密、预算、失败/重试与发版证据|每次工具输入输出hash；已有授权写入任务上下文；私有repo默认；冻结R1只读；仿真与制造放行分离；审批仅新费用/新权限/发布等实质边界|

## 工具接口
统一返回 `{status, input_refs, output_refs, scope, observations, limitations, logs, elapsed_seconds}`。
候选工具：drawing.extract_requirements、cad.build、cad.audit_export、assembly.check_motion、loads.derive、contact.solve、fea.run、cfd.run、evidence.audit、delivery.package。
每个工具支持 dry_run/estimate；执行前只验证该工具所需字段，未知材料可继续geometry检查，不让一个缺项堵死全部工作。资源限制按工具任务局部设定，绝不自动抄成物理要求。

## 推荐目录（私有项目与可开源内核分离）
core/（本体、依赖、运行记录、检查器）；adapters/（CAD/FEA/CFD）；knowledge/（脱敏方法/适用条件/坑）；tests/（合成回归）；projects/private/（图纸/模型/材料/客户信息）；evidence/（原件manifest与运行记录）。
本轮 framework/evidence_contract.py 是无依赖最小检查器；tests 用合成记录验证“局部不能冒充全域、文本读取不能冒充原字节、未知验收不能通过”。它不是完整求解器或制造认证器。

## 下一可实施闭环
先接一条已有R1 load_study输入→hash验证→输出→证据记录，不重写公式；再接AGR1独审和CRM1，最后调度昂贵求解。每个适配器拥有原件fixture+独立反例；回归测试通过仅证明适配器契约，不证明工程合格。发布开源前清理私有图纸/个人链接、核各依赖许可证与再分发权，当前仅私有集成。

## 已核研究来源的工程映射
研究线提供并核对的原文（不是同一篇案例）：
- Google生物药研三层参考架构：https://cloud.google.com/blog/topics/healthcare-life-sciences/architecting-scalable-agentic-biotech-workloads/ （2026-10-16）。本框架映射认知编排、专业执行、贯穿治理；不绑定 Google Cloud。
- Google四条评估经验：https://cloud.google.com/blog/topics/developers-practitioners/four-eval-engineering-lessons/ （2026-10-16）。映射：保存完整工具轨迹；并发调度按依赖轮次而非固定总顺序评估；合成检查不能代真实执行；用工程原例作为goldens。
- REA：https://github.com/morluto/rea ，尤其 docs/mcp-contracts.md。可借鉴工具契约和可观测执行；软件逆向能力不等于CAD/CFD求解能力。

## 已落地的最小真实复用
original/R1/C4/T15/calculate_loads.py 保留原字节；SHA256=4638752c2ef793f139e75ddd7a2d707c2df6b1200269150008e14951ee52051e，与原 load_study.json 自带hash一致。basis_gate.py 来自同一提交的 runs/20261006/C4/T06；保持原件，未将历史权限状态用作当前授权。
tests/test_original_arithmetic.py 实际调用原 screw_model 对历史12行数据回归，核扭矩/效率/自锁阈值；另外校验原字节hash及非有限压力拒绝。11个测试共包含8个合成契约测试和3个原算术测试方法（其中1个遍历12行）。全部通过。不等于完整载荷main重跑，不等于CAD受压面或整阀物理验证。

历史 basis_gate.validate 要求 github_write_allowed、solver_execution_allowed=false，是当时研究快照中的停用状态，不是当前用户权限。不要用复制旧门禁阻挡已授权推送/计算；适配时将运行授权从科学输入分离。原件不得偷偷改写，新增适配层再测试。
