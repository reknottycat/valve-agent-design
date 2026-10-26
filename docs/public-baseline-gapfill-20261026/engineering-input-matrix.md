# 工程输入逐字段矩阵

本表的公开值只补入独立候选轨道。所有字段默认未采纳；原 R1 不变。`confirmed-original` 表示记录/图注确实已有，不表示实物或制造资格已验证。机器可读权威副本为 [engineering-input-matrix.json](engineering-input-matrix.json)。

来源定位、版本和限制见 [source-register.json](source-register.json)。`null` 是待补证据，不是零值。

## 材料

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| MAT-O-01 原件逐零件完整材料牌号及状态 | original-R1 | unresolved | 待补 designation | ORIG-C2 | 原图复核未建立完整BOM与材料状态；不能把目录铜合金写回原阀。 |
| MAT-O-02 许用应力及温度依赖弹塑性数据 | original-R1 | unresolved | 待补 MPa | ORIG-C2 | 须确定牌号、工艺、温度、铸造质量与适用规范，公开PN不能反算。 |
| MAT-P-01 DN200体盖座瓣候选牌号 | public-perlwitz-017960-DN200 | published-otherproduct | "CC491K / CuSn5Zn5Pb5-C" designation | PUB-PERLWITZ | 只属于该厂家系列；材证、状态、腐蚀/冲蚀与本项目工况适用性未核。 |
| MAT-P-02 阀杆候选牌号 | public-perlwitz-017960-DN200 | published-otherproduct | "CW710R / CuZn35Ni3Mn2AlPb" designation | PUB-PERLWITZ | 不推定与原件材料等同，不提供本项目许用应力。 |
| MAT-I-01 体盖材质类别 | public-ilshin-F7353-DN200 | published-otherproduct | "cast iron" material class | PUB-ILSHIN | 未给完整牌号，不与Perlwitz青铜体混装为一个基线。 |
| MAT-I-02 瓣座材质类别 | public-ilshin-F7353-DN200 | published-otherproduct | "bronze or stainless steel" material class | PUB-ILSHIN | 选项未确定；不是同时存在于已确定BOM。 |
| MAT-M-01 阀体产品材质标识 | public-meson-410-D2X-DN200 | published-otherproduct | "Rg5" designation | PUB-MESON | 原样保留厂家名称；不做跨标准材料等同。 |

## 关键尺寸

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| DIM-O-01 名义通径标记 | original-R1 | confirmed-original | 200 DN | ORIG-C2 | DN不是实测内径，也不是关阀有效受压直径。 |
| DIM-O-02 面间距600* | original-R1 | confirmed-original | 600 mm | ORIG-C2 | 星号参考尺寸；未转换为制造控制尺寸。 |
| DIM-O-03 手轮直径Ø320* | original-R1 | confirmed-original | 320 mm | ORIG-C2 | 仅参考外形；不能未经受力位置说明换算辅助扳手扭矩。 |
| DIM-O-04 原图法兰外径参考Ø295* | original-R1 | confirmed-original | 295 mm | ORIG-C2 | 原图尺寸注记；法兰标准与压力等级仍需版本核对。 |
| DIM-O-05 原图Ø264*参考注记 | original-R1 | confirmed-original | 264 mm | ORIG-C2 | 尺寸端点/标准定义须在控制图复核，不与厂家PCD295拼接。 |
| DIM-O-06 原图12孔Ø15*参考注记 | original-R1 | confirmed-original | {"count": 12, "diameter": 15} count; mm | ORIG-C2 | 完整接口控制尺寸与孔位公差未冻结。 |
| DIM-O-07 阀杆/手轮参考行程57* | original-R1 | confirmed-original | 57 mm | ORIG-RETRO | 不是自由阀瓣的已验证全开行程。 |
| DIM-O-08 R1固定研究姿态瓣位移 | original-R1 | derived-under-assumptions | 57 mm | ORIG-R1-FLOW | 历史研究姿态记录，不是本次采用或实际自然开启结果。 |
| DIM-O-09 密封有效直径、座宽和座角 | original-R1 | unresolved | 待补 mm / geometry | ORIG-C2, ORIG-C2-GEOM | 需要原零件图、可核验实测或明确新设计选择；目录外形/Cv不能唯一确定。 |
| DIM-O-10 最薄壁、螺杆根径/螺距和导向长度 | original-R1 | unresolved | 待补 mm / geometry | ORIG-C2, ORIG-C2-GEOM | 需要原零件图、可核验实测或明确新设计选择；目录外形/Cv不能唯一确定。 |
| DIM-O-11 阀杆与阀瓣耦合及自由升程 | original-R1 | unresolved | 待补 mm / geometry | ORIG-C2, ORIG-C2-GEOM | 需要原零件图、可核验实测或明确新设计选择；目录外形/Cv不能唯一确定。 |
| DIM-P-01 直通型面间距L | public-perlwitz-017960-DN200 | published-otherproduct | 600 mm | PUB-PERLWITZ | 保留整套同厂家DN200直通候选；未采用为522原阀几何。 |
| DIM-P-02 法兰外径D | public-perlwitz-017960-DN200 | published-otherproduct | 340 mm | PUB-PERLWITZ | 保留整套同厂家DN200直通候选；未采用为522原阀几何。 |
| DIM-P-03 PCD | public-perlwitz-017960-DN200 | published-otherproduct | 295 mm | PUB-PERLWITZ | 保留整套同厂家DN200直通候选；未采用为522原阀几何。 |
| DIM-P-04 目录高度H | public-perlwitz-017960-DN200 | published-otherproduct | 580 mm | PUB-PERLWITZ | 保留整套同厂家DN200直通候选；未采用为522原阀几何。 |
| DIM-P-05 法兰孔表 | public-perlwitz-017960-DN200 | published-otherproduct | {"count": 8, "diameter": 22} count; mm | PUB-PERLWITZ | 不能和原件12孔Ø15*接口混用。 |
| DIM-I-01 目录面间距L | public-ilshin-F7353-DN200 | published-otherproduct | 570 mm | PUB-ILSHIN | JIS5K页面的DN200候选；不能与600 mm求平均或替代。 |
| DIM-I-02 目录法兰外径/PCD/厚度 | public-ilshin-F7353-DN200 | published-otherproduct | {"D": 320, "PCD": 280, "t": 24} mm | PUB-ILSHIN | F7305与F7353共页；需确认具体订货配置。 |
| DIM-I-03 目录孔表 | public-ilshin-F7353-DN200 | published-otherproduct | {"count": 8, "diameter": 23} count; mm | PUB-ILSHIN | 不作为俄罗斯原件接口依据。 |
| DIM-M-01 DN200产品面间距L | public-meson-410-D2X-DN200 | published-otherproduct | 600 mm | PUB-MESON | 同长不证明同内部流道或阀瓣运动方式。 |

## 公差

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| TOL-O-01 原图锁紧细节内螺纹 | original-R1 | confirmed-original | "M6-7H" designation | ORIG-C2 | 仅此原图细节有依据；不能外推主杆螺纹公差或全部制造公差。 |
| TOL-O-02 阀杆/导向配合和全温域间隙 | original-R1 | unresolved | 待补 mm | ORIG-C2, ORIG-C2-GEOM | 本次厂家公开资料未补得控制值；需公差链、热膨胀、变形及加工检验方案。 |
| TOL-O-03 座面同轴度、圆度、平面度与表面粗糙度 | original-R1 | unresolved | 待补 mm / µm | ORIG-C2, ORIG-C2-GEOM | 本次厂家公开资料未补得控制值；需公差链、热膨胀、变形及加工检验方案。 |
| TOL-O-04 密封接触带宽与装配预紧公差 | original-R1 | unresolved | 待补 mm / N | ORIG-C2, ORIG-C2-GEOM | 本次厂家公开资料未补得控制值；需公差链、热膨胀、变形及加工检验方案。 |

## 载荷

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| LOAD-O-01 原图压力字面标记 | original-R1 | confirmed-original | "Ру6" literal designation | ORIG-C2 | 保留原文，不在本包擅自换成0.6、0.63 MPa或PN10。 |
| LOAD-O-02 基础型号海水工作温度范围 | original-R1 | confirmed-original | [-2, 50] °C | ORIG-C2 | 含义来自适用注4；28%氯化钙低温工况是-02变型，不移植到基型。 |
| LOAD-O-03 辅助扳手作用力上限原注 | original-R1 | confirmed-original | 45 kgf | ORIG-C2 | 仅基型/-01适用；不是已证实的手轮轮缘力，力臂及扭矩未给。 |
| LOAD-O-04 R1结构研究表压 | original-R1 | derived-under-assumptions | 0.63 MPa(g) | ORIG-R1-FLOW | 已有研究假设，不是新确认额定压力，也不是CFD压降。 |
| LOAD-O-05 最大关阀/反向压差与瞬变包络 | original-R1 | unresolved | 待补 MPa | ORIG-C2 | 需真实工况；工作额定压力、试验压力和关阀压差分开。 |
| LOAD-O-06 手轮输入扭矩及填料/螺纹摩擦 | original-R1 | unresolved | 待补 N·m / 1 | ORIG-C2 | 无法由PN、手轮外径或Kv唯一反推。 |
| LOAD-P-01 DN200目录允许压力不高于120°C | public-perlwitz-017960-DN200 | published-otherproduct | 10 bar | PUB-PERLWITZ | 该产品温压表，不是522原阀载荷；页面高温段另限6 bar。 |
| LOAD-P-02 DN200目录高于120°C允许压力 | public-perlwitz-017960-DN200 | published-otherproduct | 6 bar | PUB-PERLWITZ | 只在厂家给定介质/最高温度范围内解释，不泛化为所有海水或蒸汽工况。 |
| LOAD-M-01 DN200压力/连接标识 | public-meson-410-D2X-DN200 | published-otherproduct | "PN10" designation | PUB-MESON | 铭牌级别不是本项目关阀压差或实测承压结果。 |

## 强度与接触

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| STR-O-01 阀杆压扭、屈曲、螺纹承载合格结果 | original-R1 | unresolved | 待补 pass/fail | ORIG-C2-GEOM | 需要材料、根径、有效长度、端部约束、载荷和适用计算式；旧公式矛盾先解决。 |
| STR-O-02 阀体阀盖螺栓强度合格结果 | original-R1 | unresolved | 待补 pass/fail | ORIG-C2-GEOM | 需要完整壁厚、开孔、铸造系数、腐蚀裕量、接头和载荷；目录PN不是替代证据。 |
| STR-O-03 阀座接触压力分布和变形合格结果 | original-R1 | unresolved | 待补 MPa / mm | ORIG-C2-GEOM | 必须用结构/接触模型；Fluent流动计算不能单独判定。 |
| STR-O-04 静压合力关系作为待接入计算路线 | original-R1 | derived-under-assumptions | "F_pressure = Δp × A_effective" N = Pa × m² | ORIG-C2 | 只给均匀压力投影简式；不包含摩擦、预紧、非均匀压强、导向及动载；本次不生成原阀数值。 |

## 密封依据

| 字段 | 轨道 | 分类 | 值与单位 | 来源 | 适用限制 |
|---|---|---|---|---|---|
| SEAL-O-01 原阀泄漏等级与方向/持续时间 | original-R1 | unresolved | 待补 acceptance specification | ORIG-C2 | 需合同/产品标准和完整条款；不能由金属密封或PN推出。 |
| SEAL-O-02 原阀壳体试验/阀座试验压力 | original-R1 | unresolved | 待补 MPa | ORIG-C2 | 不采用别家JIS产品试压；需原压力基准和适用验收规则。 |
| SEAL-I-01 JIS5K ≤300A目录壳体水压试验 | public-ilshin-F7353-DN200 | published-otherproduct | 1.03 MPa | PUB-ILSHIN | 只作为分项试验架构实例；未给本项目持续时间/泄漏判据。 |
| SEAL-I-02 JIS5K ≤300A目录阀座水压试验 | public-ilshin-F7353-DN200 | published-otherproduct | 0.76 MPa | PUB-ILSHIN | 不是原阀已通过此试验，非原阀验收值。 |
| SEAL-O-03 填料与阀盖垫片材料、压紧及泄漏 | original-R1 | unresolved | 待补 specification | ORIG-C2-GEOM | 需独立建立；主密封面接触并不覆盖外漏边界。 |
