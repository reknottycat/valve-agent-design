# 公开阀门参数反推约束说明

核查日期：2026-10-26。用途：概念设计与候选方案筛选；不构成原厂结构复原、制造图或船级认证结论。

## 方法边界

可以从公开参数反推设计约束和候选方案，通常不能唯一还原原厂结构。建议过程：公开资料 → 参数约束 → 候选几何 → 正向仿真/试验 → 筛选。

本项目为手动轴向船用截止/止回类目标。调节阀手册可提供流量计算方法，但气动调节阀不能直接作为同型结构基准。

## 官方来源与定位

1. Emerson/Fisher, Control Valve Handbook，官方入口：
   https://www.emerson.com/en/final-control/catalog/products-and-software/valves/control-valves/control-valve-handbook
   已核官方入口及公开手册存在；本报告不将未逐页核实的手册版本、页码或公式作精确引用。
2. SAMSON T 8015 EN, Series 240, Type 3241 Globe Valve · DIN version：
   https://france.samsongroup.com/document/t80150en.pdf
   14页PDF封面标 Edition November 2022；末页另见2026-08-27标记，应保留这一版本区分，不把后者自动解释为技术修订日期。印刷第6页Table 4为无流量分配器配置，DN25包含Kvs 4.0、6.3、10等；第6页Table 3提供Kvs、阀座直径与行程对应表；印刷第4页Table 1为技术参数，第5页Table 2为材料，第9页含尺寸表。同一DN对应多档Kvs，不足以唯一确定内件。具体组合须连同表头、脚注、配置读取，不能跨型号拼接。
3. Spirax Sarco, Control Valve Sizing for Water Systems：
   https://www.spiraxsarco.com/learn-about-steam/control-hardware-electric-pneumatic-actuation/control-valve-sizing-for-water-systems
   官方HTML教学页，未显示可明确引用的修订号；定位Equation 6.3.1（液体Kv关系）、Equation 6.3.2（水的简化）、Table 6.3.1（单位转换）。说明Kv以m³/h及1 bar压差定义，须区分Cv US与Cv UK。US Cv约为1.16 Kv；本报告计算不需要该转换。
4. IEC 60534-2-1:2011官方摘要：
   https://webstore.iec.ch/en/publication/2461
   第二版，2011-03-30；官方说明已包含2015年4月勘误。范围为控制阀可压缩/不可压缩流体流量计算，包含非湍流修正。不是内部几何反演标准。本报告只使用官方公开摘要，不声称已取得完整标准正文。

## 参数本体建议

|输入字段|可以约束/推算|不能唯一确定|
|---|---|---|
|Kv/Cv、Q、Δp、ρ、μ、T、开度|指定工况通流能力、压降、等效通流参数|完整流道形状|
|DN、连接标准、结构长度|接口与安装包络|内腔、壁厚分布|
|行程、公开阀座直径、流量特性|运动行程和节流几何候选范围|阀芯精确曲面|
|PN、压温限制、材料牌号|压温与材料约束|完整强度证明、实际热处理状态|
|泄漏等级、密封类型|验收目标及结构类型|制造公差、粗糙度、预紧量、接触压力|

每条数据应记录source_url、document_revision、page_table、unit、configuration、operating_conditions、confidence，并将厂家公开值、计算推导值、设计假设明确分层。

## 小型教学算例（非目标阀性能预测）

假设：固定开度，不可压缩牛顿液体，充分湍流，无汽蚀/闪蒸/阻塞；压差测量边界一致，不另计安装管件影响。

Q = Kv × sqrt(Δp_bar / SG)，SG = ρ/1000。

Q单位m³/h，Δp单位bar，ρ单位kg/m³。以Kv=10、水SG≈1、Δp=0.25 bar为例：Q=10×sqrt(0.25)=5 m³/h。这是独立教学输入，不是对SAMSON某配置或项目目标阀的全工况保证。

若额外采用简化孔口模型 Q = Cd A sqrt(2Δp/ρ)，全部改用SI单位：

Cd A = (5/3600)/sqrt(2×25000/1000) ≈ 1.96×10^-4 m² = 196 mm²。

反推结果只是Cd A的乘积，即该模型与工况下的等效通流参数，不是实际阀座面积。Cd未知且与几何、开度及流态有关，不能据此唯一确定A或真实阀座直径。不同结构可满足同一整体流量点或近似曲线。

## 低雷诺数与验证要求

若项目Re≈10，不能直接套用上述充分湍流平方根关系，也不能把目录Kvs视为该低雷诺数下不变的性能系数。必须记录Re定义、特征长度/速度及黏度；管道Re与阀门Re不能直接混同。应采用适当非湍流修正，或在相应层流CFD/试验中核算压降。

候选设计需要同时满足接口、启闭功能、流阻、承压、密封、材料与制造约束。单一Kv匹配不能证明密封可靠或结构合格。

## 工具职责（建议流程，不是本次软件执行成果）

先用参数化CAD建立候选几何与流体域，进行几何清理、网格和边界条件配置，再用CFD求流量/压降及流场；Fluent结果不能自动补齐未公开的制造结构。承压、接触、密封预紧等需要另行结构/接触分析与适当试验，不能把流场结果当成结构合格证明。本报告未安装软件、未生成可制造几何、未运行Fluent或结构求解。

最终产物应是带假设、适用工况及证据的一族候选参数，而非声称复原原厂的唯一设计。

本包另提供 [教学算例结构化输入与结果](educational-kv-example.json)，`actual_valve_result=false`，可复算仅用于检查单位链和算术。厂家配置与原件工程字段仍以 [工程输入矩阵](engineering-input-matrix.md) 为准。
