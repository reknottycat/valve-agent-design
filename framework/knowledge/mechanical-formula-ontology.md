# 阀门机械基础公式本体草案（非标准库）

日期：2026-10-22。状态：研究草案，禁止工程放行。用户的公式/标准仓库尚待提供，本文件只建立语义与公开基础关系的映射，不重复导入、不猜测标准条款。未取得具体《机械设计手册》版次，不能声称吸收整书；该手册页码、公式号均留空。公开教学资料/厂商资料不是阀门符合性标准。下述例值全部为合成单元测试，不是材料推荐值或实际工况。

## 本体结构

实体：Component（阀瓣/阀杆/阀体/螺母/密封件）、Interface（接触/密封/螺纹）、Geometry、MaterialState、LoadCase、Quantity、FormulaModel、Applicability、Evidence、VerificationCase、StandardBinding、ReviewDecision。

关系：部件 `hasGeometry/hasMaterialState`；工况 `loadsComponent`；接口 `connectsComponents`；公式 `requiresQuantity/producesQuantity/assumes/isInvalidWhen`；参数 `supportedBy` 证据；计算 `verifiedBy` 样例；规则 `governedBy` 外部标准绑定。标准绑定为空时，合规判断必须为 `not_evaluated`，不能用教学公式填补。

每个 Quantity 包含值、单位、符号、物理定义、正方向、证据ID、来源状态（测得/图纸声明/用户确认/推导/合成测试）、温度及不确定度。缺值为 unknown，不填0。公式是受控表达式/实现引用，不能对资料文字做任意 eval。

## 六类基础条目

### M01 压差载荷

- 模型：均匀压差与已确认有效投影面积下，`F_p = (p_up - p_down) A_eff`。一般表面压力需矢量积分；法向/正方向必须声明。[NASA压力](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/air-pressure/)；[NASA表面力积分](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/aerodynamic-force/)。
- 实体/量：LoadCase、受压部件、有效面积；p[Pa]、A_eff[m²]、F_p[N]。压力必须同一基准；不同受压面积不能直接用同一A相减。
- 前提：静态或准静态、已知压力分布与有效面积。限制：不含流动力矩、动量交换、弹簧/填料/密封摩擦和惯性；DN不是自动等于有效受压直径。
- 合成验证：2e6 Pa × 1e-3 m² = 2000 N；压差0则压力差贡献0，不等于总驱动力0；负压差必须保留方向。
- 待标准覆盖：设计/试验工况、载荷组合、允许应力、安全系数、执行机构裕量。

### M02 理想方形动力螺纹：驱动与自锁

- 模型：`tan(lambda)=lead/(pi*d_m)`；`T_raise = W*d_m/2 * (tan(lambda)+mu_k)/(1-mu_k*tan(lambda))`。静止理想自锁条件 `tan(lambda)<mu_s`，等号是临界，不算稳健自锁。[Penn State Power Screws](https://mechanicsmap.psu.edu/websites/7_friction/7-4_screws/screws.html)。
- 实体/量：螺杆—螺母接口；W[N]、d_m[m]、lead[m/rev]、lambda[rad]、mu_s/mu_k[1]、T[N·m]。lead是导程，不可把多头螺纹螺距直接代入；d_m为工作平均直径。
- 前提：理想展开斜面/方形牙、准静态、已确认摩擦。限制：不包含止推轴承/轴环摩擦；梯形/V形牙必须另建经审核的牙型模型。润滑、磨损、振动与温度变化可破坏自锁推断；不能作为唯一防倒驱安全保证。
- 合成验证：W=1000、d_m=0.02、tan(lambda)=0.1、mu_k=0.2 → T=3.0612244898 N·m；mu_s=0.2时理想静止条件成立，mu_s=0.1为临界。分母≤0/输入不明应拒算。
- 待标准覆盖：牙型/公差、螺纹承载与磨损、阀杆稳定性、驱动裕量、独立防倒驱要求。

### M03 摩擦与接触

- 模型：静摩擦 `abs(F_t)<=mu_s*N`；仅临界滑动时取等号。滑动库仑近似 `abs(F_t)=mu_k*N`，方向反抗相对滑动。[Penn State Dry Friction](https://mechanicsmap.psu.edu/websites/7_friction/7-1_dry_friction/dryfriction.html)。
- 量：N、F_t[N]；mu[1]，必须绑定材料对、表面状态、润滑、速度/温度范围及来源。
- 限制：不能把干摩擦简式无条件用于填料、弹性密封、流体润滑或黏滑；摩擦系数不是材料单独属性，也不是永恒常数。
- 合成验证：N=100、mu_s=0.3、切向需求10 → 静摩擦10 N，而非30 N；需求40 → 该静态平衡不可维持。缺mu时阻塞。
- 待标准覆盖：实测/供应商摩擦包络、启闭分离工况、寿命与最坏状态裕量。

### M04 热膨胀与配合间隙

- 模型：自由、小变形、近似恒定alpha时 `delta_L=alpha*L0*delta_T`。[OpenStax University Physics 2 §1.3](https://openstax.org/books/university-physics-volume-2/pages/1-3-thermal-expansion)。
- 派生间隙模型（本草案代数推导）：直径间隙 `c_d(T)=D_b0*(1+alpha_b*delta_T_b)-D_s0*(1+alpha_s*delta_T_s)`；径向间隙为c_d/2。D、L、c[m]，alpha[K^-1]，温差[K]。孔与轴可有不同温度。
- 前提：各部件均匀温度、自由膨胀、同心几何；限制：约束、梯度、接触、弹塑性与温度相关物性需更完整模型。c_d≤0表示可能接触/过盈，不能继续套自由间隙式计算接触应力。
- 合成验证：alpha=1e-5、L0=0.1、delta_T=100 → delta_L=1e-4 m；delta_T=0 → 初始尺寸；同alpha同温差时初始间隙也按同倍率变化，不应误称绝对间隙不变。
- 待标准覆盖：材料真实alpha(T)、公差最坏组合、温度包络、最小运行间隙及密封挤出间隙。

### M05 薄壁与厚壁：模型选择先于计算

- 薄壁闭端圆筒、均匀内压且外压相对可忽略时，膜应力 `sigma_hoop=p*r/t`，`sigma_axial=p*r/(2*t)`；p、sigma[Pa]，r、t[m]。[MIT David Roylance Pressure Vessels](https://ocw.mit.edu/courses/3-11-mechanics-of-materials-fall-1999/082fcd712adffa589a670f9f8dfdd49a_MIT3_11F99_pv.pdf)。
- 前提：t相对r足够小、远离不连续区、薄壁近似适用性已批准；不把经验厚径比自动当作规范限值。轴向应力取决于闭端及约束，不能对任意开口管照搬。
- 厚壁需保留沿厚度径向/环向应力分布及边界条件；Lamé类模型只适用于其轴对称弹性圆筒假设，不能直接把不规则阀体、开孔、阀座过渡替换成圆筒。[MIT厚筒教学](https://ocw.mit.edu/courses/1-033-mechanics-of-material-systems-an-energy-approach-fall-2003/e3cc5c8a5bae3f6d3297dc9fdff70a03_lecture_iii_5.pdf)。本轮不将厚壁公式编码成可执行规则。
- 合成验证：p=1e6、r=0.1、t=0.001 → 环向100e6 Pa、轴向50e6 Pa；只验证代数比例，不判材料安全。外压失稳、塑性、疲劳/蠕变、热应力另立模型。
- 待标准覆盖：适用几何判定、设计壁厚、腐蚀/铸造裕量、应力分类、允许值、外压及疲劳要求。

### M06 密封：决策与验证对象，不是单一公式

- 本轮不提供“接触应力大于压力即可密封”的通用判定。至少关联材料/介质兼容、压力温度、压缩与回弹、沟槽/挤出间隙、表面、磨损、运动类型及泄漏验收。
- 厂商公开证据：Parker O-Ring资料涉及温度、压缩永久变形、挤出与间隙；仅适用相应弹性体O形圈语境，不能泛化为所有金属阀座/填料。[Parker官方手册](https://www.parker.com/content/dam/Parker-com/Literature/O-Ring-Division-Literature/ORD-5700.pdf)。本次PDF全文工具受大小限制，仅用官方索引/检索所见主题核实，不声称逐页验证、不提取尺寸表。
- 验证用例：缺介质/温度/密封型式时输出unknown并阻塞选材；参数全时仍需适用供应商数据与试验，不自动输出零泄漏。
- 待标准覆盖：密封结构专用规范、泄漏等级、试验介质/压力/温度/持续时间及验收。

## 接入现有标准仓库的占位协议

`standard_binding={repository:null,commit:null,rule_id:null,edition:null,clause:null,status:"awaiting_user_repository"}`。后续只做ID映射、冲突审查与测试链接，不复制第二份标准真源。所有公式保持 `engineering_release:false`，直至来源、实现、适用域、输入和独立验证经批准。

阻塞仅限真实工程放行（scope=`engineering_release`），不阻塞研究整理、适配器开发或合成测试。JSON仅机器化展示M01结构，其余五类仍为文字草案，不能称六类全部已可执行。

可重跑算术冒烟测试：`python -m unittest discover -s /workspace/shared/valve-research -p test_mechanical_arithmetic.py -v`。结果见 `mechanical-arithmetic-test-results.txt`。这四项直接检验合成算术，不是对生产求解器、标准符合性或真实阀门的验证。
