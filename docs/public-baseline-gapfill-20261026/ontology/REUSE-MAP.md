# 现有阀门本体复用核查（只读，2026-10-26）

## 结论

已有，不应重建第二份标准库。复用 `standards-kb` 的知识对象、全局量ID、映射及证据纪律；公开手册/教材作为独立来源补缺，不能伪装标准正文。已读远端固定 commit `2937b5901b26d02456b95545ab2c1a059676e82a`；阀门仓库当前为 `a8ada4ed61b15e408979b8025ff8a58ceac0ae31`。未修改任何上游或 builder。本包 `source-records.json` 仅保存本次复核的6条公式及其6个映射对象、来源文件blob与记录指纹；不包含全库93条或完整连接器响应，不能据此单独重做全库计数。全库计数是本次固定版本只读检查的观察记录；完整响应不随包交付，也不作为包内测试依赖。本包不是可用于适配器的原始字节快照，不分发付费标准正文。

## 已有资产与边界

- 实际逐文件计数：23公式（10 VERIFIED_CLAUSE、3 PENDING_VERIFICATION、10 UNVERIFIED_CLAUSE）；13表（6 VERIFIED、7 UNVERIFIED）；57参数（49 VERIFIED、8 PENDING）。合计93条=65/11/17。状态是库中声明，不是本次重新逐条核验标准全文；另2推导未计入93。
- `kb/ontology/ontology.yaml` 七类：Quantity、Context、Occurrence、Criterion、VariableBinding、EquivalenceSet、TableColumn。Formula是底层知识对象，并非该文件新增的第八类本体。
- Quantity必需 `qid/name_zh/dimension/canonical_unit`；Context必需 `xid/kind/name_zh`。Context.kind只有既有受控枚举，不能将任意手册适用范围直接塞成新kind。
- 参数映射：`mappings[entry_id].quantity/role/relation/unit_system/contexts`；值/单位/来源仍在参数原记录。`onto_model.py`派生 `O:<entry_id>` VALUE 和 `C:<entry_id>`判据，避免复制阈值。
- 公式映射：`mappings[formula_id].result_quantity/variables/uses_parameters`；派生RESULT occurrence及 `B:<formula_id>:<symbol>`，后者字段为 `bid/formula_id/local_symbol/quantity`。
- 表格不产生Occurrence；列走 `TC:<entry_id>:<column_key>`，`quantity_or_text`区分量与文字。
- 现有适配器固定旧commit `7eda528a8795b8fbd850d6d35ac67e198de5810a`，保留原record/evidence/source/applicability，加repo/commit/path/file与record SHA256。已存在20项测试记录（19合成+1真实条目）。它只是检索，不执行公式，也不验证正文/单位/适用性，永远 `engineering_release=false`。不能将旧manifest直接当当前库全量快照。

## 公开设计参考如何挂接（建议映射，不是已经导入）

| 参考内容 | 复用落点 | 必守边界 |
|---|---|---|
| 标量/摩擦系数/材料值 | 先核物理意义与单位，再候选对齐Quantity；现有参数形状有 `param_kind/value/unit/source/applicability/usage/evidence` | 手册页码、版本、适用材料对、温度/润滑未知时保留缺口；不冒填标准ID或VERIFIED_CLAUSE |
| 公式 | 比对 `expression.canonical/rearranged_forms/solved_for` + `variables[].symbol/unit/source_of_value`，再连已有F-ID和变量qid | 同名不等价；公开基础式不自动替代规范计算式，不自动升级实现状态 |
| 工况/有效范围 | 保留来源原始 `valid_when/not_valid_when`，审查后使用已有Context | 工作压力≠压差≠设计压力；同一单位也不自动同量 |
| 限值 | 只有已核来源明确给限值及方向，才候选映射参数→VALUE→Criterion | 教学例数、研究诊断阈值、材料推荐值不能变标准验收阈值 |
| 尺寸/性能多行表 | 数据表→TableColumn | 不压成单个Occurrence；不从DN自动推有效受压面积 |
| 教材计算/诊断流程 | 复用CFD sidecar Method/Evidence/DiagnosticTest | 不伪装标准Occurrence或等价集；未知公式链接保持空 |

## 机械六类与既有ID的具体关系

1. M01 压差载荷：本地JSON唯一机器化示例，`F_p=delta_p*A_eff`，Pa/m²/N，`executable=false`、`implementation_ref=null`。现有F-SEAL-001输入F_flow绑定 `Q:SEAL:FLOW_THRUST`、F-DRV-001输入F绑定 `Q:DRIVE:AXIAL_LOAD`；二者只有工况/方向/有效面积核准后才可候选连接，不默认等价。未确认存在独立F-ID承载完整M01。
2. M02 理想方牙驱动/自锁：文字草案。既有F-DRV-001是梯形螺纹条目，变量 `d→Q:DRIVE:THREAD_MAJOR_DIAMETER`、`mu_prime→Q:DRIVE:EQUIV_FRICTION_COEFF`、`lambda→Q:DRIVE:LEAD_ANGLE`、`pitch→Q:DRIVE:PITCH`。不是方牙模型的已核替代；工作中径/导程/牙型角和单位转换需复核。
3. M03 摩擦接触：文字草案；未确认独立静/动摩擦通用条目。`EQUIV_FRICTION_COEFF`不是静、动摩擦系数的无条件同义词。
4. M04 热膨胀/配合间隙：文字草案；未确认alpha(T)、自由膨胀、冷热间隙的直接公式/量绑定。本地合成算术不是材料证据。
5. M05 薄/厚壁：文字草案可对照F-STR-001/002及F-MAT-001。已有 `Q:STRUCT:HOOP_STRESS/INNER_HOOP_STRESS/INTERNAL_PRESSURE/INNER_DIAMETER/NET_WALL_THICKNESS/INNER_RADIUS/OUTER_RADIUS`；不是不规则阀体的自动验收方法。F-STR-002内部冲突见缺口台账。
6. M06 密封：决策/验证文字，不是通用密封公式。F-SEAL-001/002可供倾斜座面力及接触压强研究，均UNVERIFIED_CLAUSE/E1；不能从q_contact推出泄漏等级。泄漏试验制度/阈值仍缺。

四项现有机械单测只覆盖压差力、方牙力矩、自由热伸长、薄筒应力的合成算术。不是六类全实现；不代表标准符合性。

## CFD sidecar已有什么

既有独立资产 `cfd-method-ontology-20261026`（不随本包交付）：8教材候选方法+2项目诊断方法；Method/DiagnosticTest/Evidence/AcceptanceCriterion等并列结构；来源只核目录/摘要，`fullTextReviewed=false`。`externalLinks=[]`，没有已核F-ID/标准条款连接。`formulaExecution=false`、`acceptanceEvaluation=DISABLED`、`engineering_release=false`；DT-CFD-001为NOT_EXECUTED，验收threshold=null。28项软件测试不等于教材正文验证或CFD物理通过。

## 可核源

- https://github.com/reknottycat/standards-kb/blob/2937b5901b26d02456b95545ab2c1a059676e82a/kb/ontology/ontology.yaml
- https://github.com/reknottycat/standards-kb/blob/2937b5901b26d02456b95545ab2c1a059676e82a/kb/ontology/mappings/formulas.json
- https://github.com/reknottycat/standards-kb/blob/2937b5901b26d02456b95545ab2c1a059676e82a/kb/formulas/seed_core.json
- https://github.com/reknottycat/standards-kb/blob/2937b5901b26d02456b95545ab2c1a059676e82a/kb/formulas/seed_engineering.json
- 既有独立资产 `valve-standards-adapter` 的 README.md、PROVENANCE.md、standards_adapter.py（来源说明，不随包交付、不作为包内测试依赖）
- 既有独立资产 `valve-research` 的 mechanical-formula-ontology.md、mechanical-ontology.example.json、mechanical-arithmetic-test-results.txt（来源说明，不随包交付、不作为包内测试依赖）
