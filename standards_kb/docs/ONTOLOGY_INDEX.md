# 本体索引

> 本文件由 `tools/build_ontology_index.py` 自动生成，请勿手工编辑。
> 本体层本体在 `kb/ontology/`，规范版本 `1.0.0+20261022`。

## 概况

| 项 | 值 |
|---|---|
| 物理量 Quantity | **140** |
| 上下文 Context | 18 |
| 等价集 EquivalenceSet | 14 |
| └ `COLUMN_CORRESPONDENCE` | 1 |
| └ `CONFUSABLE` | 9 |
| └ `UNIT_CONVERSION` | 4 |
| 出现 Occurrence | **80** |
| └ `RESULT` | 23 |
| └ `VALUE` | 57 |
| 判据 Criterion（派生） | 57 |
| 变量绑定 VariableBinding | 127 |
| 表列投影 TableColumn | 126 |
| 跨标准物理量 | **7** |
| 符号碰撞组 | 13 |
| 未决问题登记 | 2 |

## 跨标准对齐对照

同一个物理量在多个标准下出现时的取值对照。这是本体层最核心的一张表 ——
公式层和参数层各自都能查到数，但只有把两边落到同一个 qid 上，
才能一眼看出「这个数在两个标准里不一样」。

| 物理量 | 名称 | 标准数 | 各标准取值 | 判定 |
|---|---|---|---|---|
| `Q:MAT:CARBON_EQUIVALENT` | 碳当量 CE | 2 | ASME B31.1-2007: `F-MAT-003` CE = C + (Mn + Si)/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15<br>ASME B31.1-2007: `P-MAT-011` < 0.50<br>ASME BPVC Section I-2010: `F-MAT-002` CE = C + (Mn + Si)/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15<br>ASME BPVC Section I-2010: `P-MAT-001` <= 0.45 | `S:MAT:CE_THRESHOLD` 不可互换 |
| `Q:MAT:CE_TAIL_SUBSTITUTE` | CE 式中后两项的合并替代值 | 2 | ASME B31.1-2007: `P-MAT-012` = 0.1<br>ASME BPVC Section I-2010: `P-MAT-002` = 0.15 | `S:MAT:CE_TAIL_SUBSTITUTE` 不可互换 |
| `Q:MAT:DEPOSITION_THICKNESS_MAX` | 单道焊缝熔敷厚上限 | 2 | ASME B31.1-2007: `P-MAT-015` <= 6<br>ASME BPVC Section I-2010: `P-MAT-005` <= 6 | `S:MAT:DEPOSITION_THICKNESS_MAX` 等价（数值相同） |
| `Q:MAT:HOLD_TEMP` | 保温温度 | 2 | ASME B31.1-2007: `P-MAT-017` >= 1100<br>ASME BPVC Section I-2010: `P-MAT-007` >= 1100 | `S:MAT:HOLD_TEMP` 不可互换 |
| `Q:MAT:HOLD_TIME_RATE` | 保温时间速率 | 2 | ASME B31.1-2007: `P-MAT-018` = 1 hr per 1 in. (25 mm)<br>ASME BPVC Section I-2010: `P-MAT-008` = 1 hr per 1 in. | `S:MAT:HOLD_TIME_RATE` 等价（量相同，仅排印不同） |
| `Q:MAT:PREHEAT_TEMP` | 预热温度 | 2 | ASME B31.1-2007: `P-MAT-014` >= 250<br>ASME B31.1-2007: `P-MAT-016` >= 200<br>ASME BPVC Section I-2010: `P-MAT-004` >= 250<br>ASME BPVC Section I-2010: `P-MAT-006` >= 200 | `S:MAT:PREHEAT_TEMP` 不可互换<br>`S:MAT:PREHEAT_TEMP_200F` 等价（数值相同），但条款路径不同，引用须带标准 |
| `Q:MAT:WELD_THICKNESS` | 焊缝公称厚度 | 2 | ASME B31.1-2007: `P-MAT-013` range 19.0..38<br>ASME BPVC Section I-2010: `P-MAT-003` range 19..38<br>ASME BPVC Section I-2010: `P-MAT-027` <= 1 1/2 in. (38 mm) | `S:MAT:WELD_THICKNESS_WINDOW` 疑似等价（待 B31.1 正文可得后定案） |

## 物理量清单

按域分组。`条目数` 指该物理量在三层里出现的次数（公式结果 / 参数取值 / 表列投影各算一次）。

| 域 | 物理量数 |
|---|---|
| `BOLT` | 2 |
| `DRIVE` | 10 |
| `FLOW` | 5 |
| `GEOM` | 21 |
| `MATE` | 28 |
| `SEAL` | 7 |
| `STRUCT` | 31 |
| `TEST` | 35 |
| `THERM` | 1 |

### 域 `BOLT`（2 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:BOLT:BOLT_STRESS` | 螺栓轴向应力 | STRESS | MPa | `sigma_bolt` | 1 | GB/T 3098.1 (紧固件机械性能) / ASME B16.5 (法兰) |
| `Q:BOLT:STRESS_AREA` | 单个螺栓应力截面积 | AREA | mm^2 | `As` | 0 | — |

### 域 `DRIVE`（10 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:DRIVE:RAISING_TORQUE` | 旋紧（关闭）力矩 | TORQUE | N*m | `T_raise` | 1 | 通用机械设计（螺旋传动摩擦理论） |
| `Q:DRIVE:AXIAL_LOAD` | 轴向载荷 | FORCE | N | `F` | 0 | — |
| `Q:DRIVE:THREAD_MAJOR_DIAMETER` | 螺纹外径 | LENGTH | mm | `d` | 0 | — |
| `Q:DRIVE:EQUIV_FRICTION_COEFF` | 当量摩擦系数 | DIMENSIONLESS | dimensionless | `mu_prime` | 0 | — |
| `Q:DRIVE:LEAD_ANGLE` | 导程角 | ANGLE | deg | `lambda` | 0 | — |
| `Q:DRIVE:PITCH` | 螺距 | LENGTH | mm | `pitch` | 0 | — |
| `Q:DRIVE:HAND_FORCE` | 手轮操作力 | FORCE | N | `F_hand` | 0 | — |
| `Q:DRIVE:DRIVE_TORQUE` | 驱动轴力矩 | TORQUE | N*m | `T_drive` | 0 | — |
| `Q:DRIVE:LEVER_ARM` | 有效力臂 | LENGTH | mm | `L_arm` | 0 | — |
| `Q:DRIVE:LEVER_RATIO` | 杠杆比 | DIMENSIONLESS | dimensionless | `lever_ratio` | 1 | 通用机械（杠杆原理） |

### 域 `FLOW`（5 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:FLOW:FLOW_COEFFICIENT_KV` | 流量系数（公制 Kv） | VOLUME_FLOW | m^3/h | `Kv` | 2 | IEC 60534-2-1:2011 |
| `Q:FLOW:FLOW_COEFFICIENT_CV` | 流量系数（美制 Cv） | VOLUME_FLOW | US gpm | `Cv_US` | 0 | — |
| `Q:FLOW:FLOW_AREA` | 通流截面积 | AREA | m^2 | `A` `A_bore` | 0 | — |
| `Q:FLOW:RESISTANCE_COEFF` | 阻力系数 | DIMENSIONLESS | dimensionless | `zeta` | 0 | — |
| `Q:FLOW:DENSITY` | 介质密度 | DENSITY | kg/m^3 | `rho` | 0 | — |

### 域 `GEOM`（21 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:GEOM:NOMINAL_SIZE` | 公称尺寸 | LENGTH | mm | `Dn` `PN` | 0 | — |
| `Q:GEOM:FLANGE_OUTER_DIA` | 法兰外径 | LENGTH | mm | `D` | 0 | — |
| `Q:GEOM:SEALING_FACE_OUTER_DIA` | 密封面外径 | LENGTH | mm | `D1` | 0 | — |
| `Q:GEOM:SEALING_FACE_INNER_DIA` | 密封面内径 | LENGTH | mm | `D2` | 0 | — |
| `Q:GEOM:GROOVE_DEPTH` | 密封槽深度 | LENGTH | mm | `q` | 0 | — |
| `Q:GEOM:GROOVE_COUNT` | 密封槽数量 | COUNT | count | `groove_count` | 0 | — |
| `Q:GEOM:BOLT_COUNT` | 螺栓数量 | COUNT | count | `n` `bolt_count` | 0 | — |
| `Q:GEOM:BOLT_THREAD` | 螺栓螺纹规格 | TEXT | text | `bolt_thread` | 0 | — |
| `Q:GEOM:BOLT_CIRCLE_DIA` | 螺栓孔中心圆直径 | LENGTH | mm | `K` | 0 | — |
| `Q:GEOM:BOLT_HOLE_DIA` | 螺栓孔径 | LENGTH | mm | `L` | 0 | — |
| `Q:GEOM:SEAL_FACE_DIA` | 密封面直径 | LENGTH | mm | `d` | 0 | — |
| `Q:GEOM:SEAL_FACE_HEIGHT` | 密封面凸起高度 | LENGTH | mm | `f` | 0 | — |
| `Q:GEOM:FLANGE_THICKNESS` | 法兰厚度 | LENGTH | mm | `C` | 0 | — |
| `Q:GEOM:NECK_LENGTH` | 法兰颈长度 | LENGTH | mm | `N` | 0 | — |
| `Q:GEOM:NECK_FILLET_RADIUS` | 法兰颈过渡圆角半径 | LENGTH | mm | `R` | 0 | — |
| `Q:GEOM:SEAL_STEP_OUTER_DIA` | 密封台阶外径 | LENGTH | mm | `D3` | 0 | — |
| `Q:GEOM:SEAL_STEP_INNER_DIA` | 密封台阶内径 | LENGTH | mm | `D4` | 0 | — |
| `Q:GEOM:CONCAVE_SEAL_OUTER_DIA` | 凹面密封外径 | LENGTH | mm | `D5` | 0 | — |
| `Q:GEOM:CONCAVE_SEAL_INNER_DIA` | 凹面密封内径 | LENGTH | mm | `D6` | 0 | — |
| `Q:GEOM:SEAL_STEP_HEIGHT` | 密封台阶高度 | LENGTH | mm | `f` | 0 | — |
| `Q:GEOM:NOMINAL_PRESSURE_RATING` | 公称压力等级代号（PN 数值） | DIMENSIONLESS | dimensionless | `PN` `pn` | 0 | — |

### 域 `MATE`（28 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:MAT:CARBON_EQUIVALENT` | 碳当量 CE | DIMENSIONLESS | dimensionless | `CE` | 4 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:CE_TAIL_SUBSTITUTE` | CE 式中后两项的合并替代值 | MASS_FRACTION | mass-% | — | 2 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:WELD_THICKNESS` | 焊缝公称厚度 | LENGTH | mm | — | 3 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:PREHEAT_TEMP` | 预热温度 | TEMPERATURE | degC | — | 4 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:HOLD_TEMP` | 保温温度 | TEMPERATURE | degC | — | 2 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:HOLD_TIME_RATE` | 保温时间速率 | DIMENSIONLESS | hr per 25 mm | — | 2 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:HOLD_TIME_MIN` | 保温时间最小值 | TIME | min | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:HOLD_TIME_INCREMENT` | 保温时间增量 | DIMENSIONLESS | min per 25 mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:MAX_CARBON_CONTENT` | 最大实际碳含量 | MASS_FRACTION | mass-% | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:HEAD_SIZE_MAX` | 封头最大口径 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:PIPE_OD_MAX` | 管子外径上限 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:NOZZLE_THROAT_MAX` | 喉部/焊缝厚度上限 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:THICKNESS_LIMIT_HALF_IN` | 1/2 in. 厚度上限 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:MIN_WALL_THICKNESS` | 最小壁厚 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:WELD_THICKNESS_BREAKPOINT` | 焊缝厚度分界值 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:BASE_METAL_THICKNESS_BREAKPOINT` | 母材厚度分界值 | LENGTH | mm | — | 1 | ASME BPVC Section I-2010 |
| `Q:MAT:DEPOSITION_THICKNESS_MAX` | 单道焊缝熔敷厚上限 | LENGTH | mm | — | 2 | ASME B31.1-2007<br>ASME BPVC Section I-2010 |
| `Q:MAT:CHEM_CARBON` | 碳含量 | MASS_FRACTION | mass-% | `C` | 0 | — |
| `Q:MAT:CHEM_MANGANESE` | 锰含量 | MASS_FRACTION | mass-% | `Mn` | 0 | — |
| `Q:MAT:CHEM_SILICON` | 硅含量 | MASS_FRACTION | mass-% | `Si` | 0 | — |
| `Q:MAT:CHEM_CHROMIUM` | 铬含量 | MASS_FRACTION | mass-% | `Cr` | 0 | — |
| `Q:MAT:CHEM_MOLYBDENUM` | 钼含量 | MASS_FRACTION | mass-% | `Mo` | 0 | — |
| `Q:MAT:CHEM_VANADIUM` | 钒含量 | MASS_FRACTION | mass-% | `V` | 0 | — |
| `Q:MAT:CHEM_NICKEL` | 镍含量 | MASS_FRACTION | mass-% | `Ni` | 0 | — |
| `Q:MAT:CHEM_COPPER` | 铜含量 | MASS_FRACTION | mass-% | `Cu` | 0 | — |
| `Q:MAT:STRENGTH_UTILIZATION` | 强度利用率 | DIMENSIONLESS | dimensionless | `utilization` | 1 | ASME BPVC Section II Part D (材料许用应力表) |
| `Q:MAT:MAX_WORKING_STRESS` | 最大工作应力 | STRESS | MPa | `sigma_max` | 0 | — |
| `Q:MAT:ALLOWABLE_STRESS` | 许用应力 | STRESS | MPa | `sigma_allow` | 0 | — |

### 域 `SEAL`（7 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:SEAL:NORMAL_CONTACT_FORCE` | 座面法向接触力 | FORCE | N | `N_seat` | 1 | 通用工程力学（座面几何分解） |
| `Q:SEAL:FLOW_THRUST` | 流动推力 | FORCE | N | `F_flow` | 0 | — |
| `Q:SEAL:SEAT_INCLINATION` | 阀座面倾角 | ANGLE | deg | `phi` | 0 | — |
| `Q:SEAL:CONTACT_PRESSURE` | 接触压强 | STRESS | MPa | `q_contact` | 1 | ISO 5208:2015 (密封等级) / 通用密封力学 |
| `Q:SEAL:CONTACT_LINE_AREA` | 密封接触线面积 | AREA | mm^2 | `A_line` | 0 | — |
| `Q:SEAL:SEAL_DIAMETER` | 阀座密封直径 | LENGTH | mm | `D_seat` | 0 | — |
| `Q:SEAL:CONTACT_LINE_WIDTH` | 密封接触线宽 | LENGTH | mm | `w_seat` | 0 | — |

### 域 `STRUCT`（31 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:STRUCT:MIN_WALL_THICKNESS` | 壳板最小厚度 | LENGTH | mm | `t` | 1 | ASME BPVC Section I-2010 |
| `Q:STRUCT:NET_WALL_THICKNESS` | 净壁厚 | LENGTH | mm | `t_net` | 0 | — |
| `Q:STRUCT:GEOM_FACTOR_Z1` | 厚壁几何系数 Z1 | DIMENSIONLESS | dimensionless | `Z_1` | 0 | — |
| `Q:STRUCT:GEOM_FACTOR_Z2` | 厚壁几何系数 Z2 | DIMENSIONLESS | dimensionless | `Z_2` | 0 | — |
| `Q:STRUCT:INNER_RADIUS` | 最弱圈节内半径 | LENGTH | mm | `R` `a` | 0 | — |
| `Q:STRUCT:OUTER_RADIUS` | 最弱圈节外半径 | LENGTH | mm | `R_0` `b` | 0 | — |
| `Q:STRUCT:ALLOWABLE_STRESS` | 最大许用工作应力 | STRESS | MPa | `S` | 0 | — |
| `Q:STRUCT:JOINT_EFFICIENCY` | 接头效率 | DIMENSIONLESS | dimensionless | `E` | 0 | — |
| `Q:STRUCT:MAX_WORKING_PRESSURE` | 最大许用工作压力 | PRESSURE | MPa | `P` | 1 | ASME BPVC Section I-2010 |
| `Q:STRUCT:WELD_STRENGTH_REDUCTION` | 焊缝强度折减系数 | DIMENSIONLESS | dimensionless | `w` | 0 | — |
| `Q:STRUCT:NET_AREA_REQUIRED` | 两开孔间所需净截面积 | AREA | mm^2 | `nar` | 1 | ASME BPVC Section I-2010 |
| `Q:STRUCT:NET_AREA_VESSEL` | 壳体壁提供净截面积 | AREA | mm^2 | `nav` | 0 | — |
| `Q:STRUCT:NET_AREA_NOZZLE` | 接管壁提供净截面积 | AREA | mm^2 | `nan` | 0 | — |
| `Q:STRUCT:PLANE_COEFF` | 平面方向系数 | DIMENSIONLESS | dimensionless | `F` | 0 | — |
| `Q:STRUCT:OPENING_CENTER_DISTANCE` | 开孔中心距 | LENGTH | mm | `D` | 0 | — |
| `Q:STRUCT:OPENING_DIAMETER` | 开孔直径 | LENGTH | mm | `dl_1` `dl_2` | 0 | — |
| `Q:STRUCT:NOZZLE_WALL_THICKNESS` | 接管壁厚 | LENGTH | mm | `t_n1` `t_n2` `t_n` | 0 | — |
| `Q:STRUCT:WELD_SIZE` | 焊缝尺寸 | LENGTH | mm | `W_d1` `W_d2` `W_d3` `W_d4` | 0 | — |
| `Q:STRUCT:LOAD_PATH_STRENGTH` | 载荷路径所需最小强度 | FORCE | N | `W` | 1 | ASME BPVC Section I-2010 |
| `Q:STRUCT:GROSS_AREA` | 总截面积 | AREA | mm^2 | `A` | 0 | — |
| `Q:STRUCT:NET_AREA` | 扣除开孔削弱后的净截面积 | AREA | mm^2 | `A_l` | 0 | — |
| `Q:STRUCT:YIELD_STRENGTH` | 屈服强度 | STRESS | MPa | `S_y` | 0 | — |
| `Q:STRUCT:HOOP_STRESS` | 环向应力 | STRESS | MPa | `sigma_h` | 1 | ASME BPVC Section VIII-1 (UG-27) |
| `Q:STRUCT:INTERNAL_PRESSURE` | 内压 | PRESSURE | MPa | `p` | 0 | — |
| `Q:STRUCT:INNER_DIAMETER` | 内径 | LENGTH | mm | `D` | 0 | — |
| `Q:STRUCT:INNER_HOOP_STRESS` | 内壁环向应力 | STRESS | MPa | `sigma_theta_inner` | 1 | ASME BPVC Section VIII-1 (UG-27(b)) |
| `Q:STRUCT:REINFORCEMENT_AREA` | 所需补强面积 | AREA | mm^2 | `WM` | 1 | ASME BPVC Section I (PG-27) |
| `Q:STRUCT:OPENING_DEDUCTION_AREA` | 开孔削弱面积 | AREA | mm^2 | `A` | 0 | — |
| `Q:STRUCT:NOZZLE_DIAMETER` | 接管直径 | LENGTH | mm | `d` | 0 | — |
| `Q:STRUCT:REINFORCEMENT_THICKNESS` | 需补强厚度 | LENGTH | mm | `t_r` | 0 | — |
| `Q:STRUCT:CAST_QUALITY_FACTOR` | 铸造质量系数 | DIMENSIONLESS | dimensionless | `F` | 0 | — |

### 域 `TEST`（35 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:TEST:WATER_FLOW_CONSTANT` | 水试验理论流量常数 | MASS_FLOW | kg/hr per (mm^2 * sqrt(MPa * kg/m^3)) | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:STEAM_FLOW_CONSTANT` | 干饱和蒸汽理论流量常数 | MASS_FLOW | kg/hr per (mm^2 * MPa) | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:SEAT_AREA_FACTOR` | 阀座面积因子 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:DISCHARGE_COEFF` | 排放系数 K | DIMENSIONLESS | dimensionless | `K` `K_D` | 3 | ASME BPVC Section I-2010 |
| `Q:TEST:DISCHARGE_COEFF_MEAN_FACTOR` | 单阀排放系数相对平均值的折减系数 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:DISCHARGE_COEFF_CAP_FACTOR` | 排放系数上限的构成因子 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:BETA_RATIO` | 排放系数适用区间（beta ratio） | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:FLOW_UNIT_FACTOR` | 流量单位换算因子 | DIMENSIONLESS | dimensionless | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:PRESSURE_CORRECTION_LIMIT` | 压力修正因子适用压力界限 | PRESSURE | MPa | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:SUPERCRITICAL_CONST` | 超临界区容量外推常数 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:SUPERCRITICAL_RATIO` | 超临界外推式比值项 | DIMENSIONLESS | dimensionless | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:GAMMA_FACTOR` | 比热比 γ 因子 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:SUPERCRITICAL_TEMP_LIMIT` | 超临界外推温度界限 | TEMPERATURE | degC | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:MARK_MARGIN` | 动力操作式泄压阀标记余量 | DIMENSIONLESS | % | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:CORRECTION_FACTOR_COEFF` | 压力修正因子系数项 | DIMENSIONLESS | dimensionless | — | 4 | ASME BPVC Section I-2010 |
| `Q:TEST:CORRECTION_FACTOR_CONST` | 压力修正因子常数项 | DIMENSIONLESS | dimensionless | — | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:SET_PRESSURE_COEF` | 试验压力定义中的 set pressure 系数 | DIMENSIONLESS | dimensionless | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:ATMOSPHERIC_PRESSURE` | 大气压项 | PRESSURE | MPa | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:SET_PRESSURE_OFFSET` | 试验压力定义中的附加项 | PRESSURE | MPa | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:REPLACEMENT_VALVE_COUNT` | 排放系数超差时替换试验的阀门数量上限 | COUNT | count | — | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:THEORETICAL_FLOW` | 理论流量 | MASS_FLOW | kg/hr | `W_T` `Q_theoretical` | 2 | ASME BPVC Section I-2010 |
| `Q:TEST:ACTUAL_FLOW` | 实际流量 | MASS_FLOW | kg/hr | `Q_actual` | 0 | — |
| `Q:TEST:NOZZLE_THROAT_AREA` | 喷嘴喉部面积 | AREA | mm^2 | `A` | 0 | — |
| `Q:TEST:SEAT_DIAMETER` | 阀座直径 | LENGTH | mm | `D` | 0 | — |
| `Q:TEST:LIFT` | 压力下的阀瓣升程 | LENGTH | mm | `L` | 0 | — |
| `Q:TEST:INLET_PRESSURE` | 计算用入口绝对压力 | PRESSURE | MPa | `P` | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:DISCHARGE_PRESSURE` | 排放压力 | PRESSURE | MPa | `P_d` | 0 | — |
| `Q:TEST:WATER_SPECIFIC_WEIGHT` | 入口工况水的重度 | DENSITY | kg/m^3 | `w` | 0 | — |
| `Q:TEST:MEAN_DISCHARGE_COEFF` | 多阀试验排放系数平均值 | DIMENSIONLESS | dimensionless | `avg_K_D` | 0 | — |
| `Q:TEST:CORRECTED_CAPACITY` | 修正后泄放能力 | MASS_FLOW | kg/hr | `W` | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:BASE_CAPACITY` | 未修正泄放能力 | MASS_FLOW | kg/hr | `W_base` | 0 | — |
| `Q:TEST:CORRECTION_FACTOR` | 超临界修正因子 | DIMENSIONLESS | dimensionless | `CF` | 1 | ASME BPVC Section I-2010 |
| `Q:TEST:CAPACITY_PRESSURE_SLOPE` | 容量对绝对压力的变化率 | MASS_FLOW | kg/hr per MPa | `dW_dP` | 0 | — |
| `Q:TEST:INLET_SPECIFIC_VOLUME` | 入口特定比体积 | SPECIFIC_VOLUME | m^3/kg | `v` `nu` | 0 | — |
| `Q:TEST:SET_PRESSURE` | 设定压力 | PRESSURE | MPa | `set_pressure` | 0 | — |

### 域 `THERM`（1 个）

| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |
|---|---|---|---|---|---|---|
| `Q:THERM:MAX_WORKING_PRESSURE_AT_TEMP` | 某温度下的最大工作压力 | PRESSURE | MPa | `p_120` `p_200` `p_250` | 0 | — |

## 符号碰撞与消歧

同一个字母在库里指向 13 组不同物理量。**这是读公式时最容易出错的地方** —— 只看字母不看 qid，就会在两个标准之间串味。

| 符号 | 物理量 | 出现位置 |
|---|---|---|
| `A` | `Q:STRUCT:OPENING_DEDUCTION_AREA`<br>开孔削弱面积 | [formula] F-STR-003 |
| `A` | `Q:STRUCT:GROSS_AREA`<br>总截面积 | [formula] F-STR-007 |
| `A` | `Q:FLOW:FLOW_AREA`<br>通流截面积 | [formula] F-FLW-001 |
| `A` | `Q:TEST:NOZZLE_THROAT_AREA`<br>喷嘴喉部面积 | [formula] F-TEST-001 |
| `A` | `Q:TEST:NOZZLE_THROAT_AREA`<br>喷嘴喉部面积 | [formula] F-TEST-002 |
| `A` | `Q:TEST:NOZZLE_THROAT_AREA`<br>喷嘴喉部面积 | [vocab] Q:TEST:NOZZLE_THROAT_AREA (symbol_candidates) |
| `A` | `Q:STRUCT:GROSS_AREA`<br>总截面积 | [vocab] Q:STRUCT:GROSS_AREA (symbol_candidates) |
| `A` | `Q:STRUCT:OPENING_DEDUCTION_AREA`<br>开孔削弱面积 | [vocab] Q:STRUCT:OPENING_DEDUCTION_AREA (symbol_candidates) |
| `A` | `Q:FLOW:FLOW_AREA`<br>通流截面积 | [vocab] Q:FLOW:FLOW_AREA (symbol_candidates) |
| `P` | `Q:STRUCT:MAX_WORKING_PRESSURE`<br>最大许用工作压力 | [formula] F-STR-004 |
| `P` | `Q:STRUCT:MAX_WORKING_PRESSURE`<br>最大许用工作压力 | [formula] F-STR-005 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [formula] F-TEST-001 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [formula] F-TEST-002 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [formula] F-TEST-004 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [formula] F-TEST-005 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [formula] F-TEST-006 |
| `P` | `Q:TEST:INLET_PRESSURE`<br>计算用入口绝对压力 | [vocab] Q:TEST:INLET_PRESSURE (symbol_candidates) |
| `P` | `Q:STRUCT:MAX_WORKING_PRESSURE`<br>最大许用工作压力 | [vocab] Q:STRUCT:MAX_WORKING_PRESSURE (symbol_candidates) |
| `D` | `Q:STRUCT:INNER_DIAMETER`<br>内径 | [formula] F-STR-001 |
| `D` | `Q:STRUCT:OPENING_CENTER_DISTANCE`<br>开孔中心距 | [formula] F-STR-006 |
| `D` | `Q:TEST:SEAT_DIAMETER`<br>阀座直径 | [formula] F-TEST-001 |
| `D` | `Q:TEST:SEAT_DIAMETER`<br>阀座直径 | [formula] F-TEST-002 |
| `D` | `Q:TEST:SEAT_DIAMETER`<br>阀座直径 | [vocab] Q:TEST:SEAT_DIAMETER (symbol_candidates) |
| `D` | `Q:STRUCT:OPENING_CENTER_DISTANCE`<br>开孔中心距 | [vocab] Q:STRUCT:OPENING_CENTER_DISTANCE (symbol_candidates) |
| `D` | `Q:STRUCT:INNER_DIAMETER`<br>内径 | [vocab] Q:STRUCT:INNER_DIAMETER (symbol_candidates) |
| `D` | `Q:GEOM:FLANGE_OUTER_DIA`<br>法兰外径 | [vocab] Q:GEOM:FLANGE_OUTER_DIA (symbol_candidates) |
| `F` | `Q:STRUCT:CAST_QUALITY_FACTOR`<br>铸造质量系数 | [formula] F-STR-003 |
| `F` | `Q:STRUCT:PLANE_COEFF`<br>平面方向系数 | [formula] F-STR-006 |
| `F` | `Q:DRIVE:AXIAL_LOAD`<br>轴向载荷 | [formula] F-DRV-001 |
| `F` | `Q:STRUCT:PLANE_COEFF`<br>平面方向系数 | [vocab] Q:STRUCT:PLANE_COEFF (symbol_candidates) |
| `F` | `Q:STRUCT:CAST_QUALITY_FACTOR`<br>铸造质量系数 | [vocab] Q:STRUCT:CAST_QUALITY_FACTOR (symbol_candidates) |
| `F` | `Q:DRIVE:AXIAL_LOAD`<br>轴向载荷 | [vocab] Q:DRIVE:AXIAL_LOAD (symbol_candidates) |
| `W` | `Q:STRUCT:LOAD_PATH_STRENGTH`<br>载荷路径所需最小强度 | [formula] F-STR-007 |
| `W` | `Q:TEST:CORRECTED_CAPACITY`<br>修正后泄放能力 | [formula] F-TEST-004 |
| `W` | `Q:TEST:CORRECTED_CAPACITY`<br>修正后泄放能力 | [formula] F-TEST-005 |
| `W` | `Q:TEST:CORRECTED_CAPACITY`<br>修正后泄放能力 | [vocab] Q:TEST:CORRECTED_CAPACITY (symbol_candidates) |
| `W` | `Q:STRUCT:LOAD_PATH_STRENGTH`<br>载荷路径所需最小强度 | [vocab] Q:STRUCT:LOAD_PATH_STRENGTH (symbol_candidates) |
| `d` | `Q:STRUCT:NOZZLE_DIAMETER`<br>接管直径 | [formula] F-STR-003 |
| `d` | `Q:DRIVE:THREAD_MAJOR_DIAMETER`<br>螺纹外径 | [formula] F-DRV-001 |
| `d` | `Q:STRUCT:NOZZLE_DIAMETER`<br>接管直径 | [vocab] Q:STRUCT:NOZZLE_DIAMETER (symbol_candidates) |
| `d` | `Q:DRIVE:THREAD_MAJOR_DIAMETER`<br>螺纹外径 | [vocab] Q:DRIVE:THREAD_MAJOR_DIAMETER (symbol_candidates) |
| `d` | `Q:GEOM:SEAL_FACE_DIA`<br>密封面直径 | [vocab] Q:GEOM:SEAL_FACE_DIA (symbol_candidates) |
| `C` | `Q:MAT:CHEM_CARBON`<br>碳含量 | [formula] F-MAT-002 |
| `C` | `Q:MAT:CHEM_CARBON`<br>碳含量 | [formula] F-MAT-003 |
| `C` | `Q:MAT:CHEM_CARBON`<br>碳含量 | [vocab] Q:MAT:CHEM_CARBON (symbol_candidates) |
| `C` | `Q:GEOM:FLANGE_THICKNESS`<br>法兰厚度 | [vocab] Q:GEOM:FLANGE_THICKNESS (symbol_candidates) |
| `L` | `Q:TEST:LIFT`<br>压力下的阀瓣升程 | [formula] F-TEST-001 |
| `L` | `Q:TEST:LIFT`<br>压力下的阀瓣升程 | [formula] F-TEST-002 |
| `L` | `Q:TEST:LIFT`<br>压力下的阀瓣升程 | [vocab] Q:TEST:LIFT (symbol_candidates) |
| `L` | `Q:GEOM:BOLT_HOLE_DIA`<br>螺栓孔径 | [vocab] Q:GEOM:BOLT_HOLE_DIA (symbol_candidates) |
| `R` | `Q:STRUCT:INNER_RADIUS`<br>最弱圈节内半径 | [formula] F-STR-004 |
| `R` | `Q:STRUCT:INNER_RADIUS`<br>最弱圈节内半径 | [formula] F-STR-005 |
| `R` | `Q:STRUCT:INNER_RADIUS`<br>最弱圈节内半径 | [vocab] Q:STRUCT:INNER_RADIUS (symbol_candidates) |
| `R` | `Q:GEOM:NECK_FILLET_RADIUS`<br>法兰颈过渡圆角半径 | [vocab] Q:GEOM:NECK_FILLET_RADIUS (symbol_candidates) |
| `w` | `Q:STRUCT:WELD_STRENGTH_REDUCTION`<br>焊缝强度折减系数 | [formula] F-STR-004 |
| `w` | `Q:TEST:WATER_SPECIFIC_WEIGHT`<br>入口工况水的重度 | [formula] F-TEST-001 |
| `w` | `Q:TEST:WATER_SPECIFIC_WEIGHT`<br>入口工况水的重度 | [vocab] Q:TEST:WATER_SPECIFIC_WEIGHT (symbol_candidates) |
| `w` | `Q:STRUCT:WELD_STRENGTH_REDUCTION`<br>焊缝强度折减系数 | [vocab] Q:STRUCT:WELD_STRENGTH_REDUCTION (symbol_candidates) |
| `K` | `Q:TEST:DISCHARGE_COEFF`<br>排放系数 K | [formula] F-TEST-003 |
| `K` | `Q:TEST:DISCHARGE_COEFF`<br>排放系数 K | [vocab] Q:TEST:DISCHARGE_COEFF (symbol_candidates) |
| `K` | `Q:GEOM:BOLT_CIRCLE_DIA`<br>螺栓孔中心圆直径 | [vocab] Q:GEOM:BOLT_CIRCLE_DIA (symbol_candidates) |
| `PN` | `Q:GEOM:NOMINAL_SIZE`<br>公称尺寸 | [vocab] Q:GEOM:NOMINAL_SIZE (symbol_candidates) |
| `PN` | `Q:GEOM:NOMINAL_PRESSURE_RATING`<br>公称压力等级代号（PN 数值） | [vocab] Q:GEOM:NOMINAL_PRESSURE_RATING (symbol_candidates) |
| `f` | `Q:GEOM:SEAL_FACE_HEIGHT`<br>密封面凸起高度 | [vocab] Q:GEOM:SEAL_FACE_HEIGHT (symbol_candidates) |
| `f` | `Q:GEOM:SEAL_STEP_HEIGHT`<br>密封台阶高度 | [vocab] Q:GEOM:SEAL_STEP_HEIGHT (symbol_candidates) |

## 易混对清单

跨标准同判据不同取值，必须一起看。`verdict` 是本库给出的判定结论。

| 等价集 | 物理量 | 各标准取值 | 差异 | 判定 |
|---|---|---|---|---|
| `S:MAT:CE_THRESHOLD` | `Q:MAT:CARBON_EQUIVALENT`<br>碳当量 CE | ASME BPVC Section I-2010: `P-MAT-001` <= 0.45<br>ASME B31.1-2007: `P-MAT-011` < 0.5 | 阈值不同（0.45 vs 0.50）**且判据方向不同**（≤ vs <） | 不可互换 |
| `S:MAT:CE_TAIL_SUBSTITUTE` | `Q:MAT:CE_TAIL_SUBSTITUTE`<br>CE 式中后两项的合并替代值 | ASME BPVC Section I-2010: `P-MAT-002` = 0.15<br>ASME B31.1-2007: `P-MAT-012` = 0.1 | 替代值不同（0.15% vs 0.1%） | 不可互换 |
| `S:MAT:PREHEAT_TEMP` | `Q:MAT:PREHEAT_TEMP`<br>预热温度 | ASME BPVC Section I-2010: `P-MAT-004` >= 250<br>ASME B31.1-2007: `P-MAT-014` >= 250 | 英制值相同（250 °F），**公制值不同**（120 °C vs 121 °C） | 不可互换 |
| `S:MAT:HOLD_TEMP` | `Q:MAT:HOLD_TEMP`<br>保温温度 | ASME BPVC Section I-2010: `P-MAT-007` >= 1100<br>ASME B31.1-2007: `P-MAT-017` >= 1100 | 英制值相同（1,100 °F），公制值不同（595 °C vs 600 °C） | 不可互换 |
| `S:MAT:HOLD_TIME_RATE` | `Q:MAT:HOLD_TIME_RATE`<br>保温时间速率 | ASME BPVC Section I-2010: `P-MAT-008` = 1 hr/in. (1 hr/25 mm)<br>ASME B31.1-2007: `P-MAT-018` = 1 hr/in. (25 mm) | **量相同，排印不同** —— BPVC-I 把公制括注写成「1 hr/25 mm」，B31.1 写成「(25 mm)」 | 等价（量相同，仅排印不同） |
| `S:MAT:WELD_THICKNESS_WINDOW` | `Q:MAT:WELD_THICKNESS`<br>焊缝公称厚度 | ASME BPVC Section I-2010: `P-MAT-003` range 19..38<br>ASME BPVC Section I-2010: `P-MAT-027` <= 38<br>ASME B31.1-2007: `P-MAT-013` range 19.0..38 | 区间数值相同；B31.1 文本层保留一位小数 19.0。 三条不是并列的三个判据，而是**两个标准里同一事实的两种粒度**： P-MAT-003 与 P-MAT-013 是"窗口"（区间形式 19..38）， P-MAT-027 是同一 BPVC 条款里单列出来的"上限"（<= 1 1/2 in. (38 mm)）。 引用时按需取区间或上限，但两者同源于 PW-39 (a)(2)。 | 疑似等价（待 B31.1 正文可得后定案） |
| `S:MAT:DEPOSITION_THICKNESS_MAX` | `Q:MAT:DEPOSITION_THICKNESS_MAX`<br>单道焊缝熔敷厚上限 | ASME BPVC Section I-2010: `P-MAT-005` <= 6<br>ASME B31.1-2007: `P-MAT-015` <= 6 | 数值相同（1/4 in. = 6 mm） | 等价（数值相同） |
| `S:MAT:PREHEAT_TEMP_200F` | `Q:MAT:PREHEAT_TEMP`<br>预热温度 | ASME BPVC Section I-2010: `P-MAT-006` >= 200<br>ASME B31.1-2007: `P-MAT-016` >= 200 | 数值完全相同（200 °F / 95 °C），但**判据分支不同** | 等价（数值相同），但条款路径不同，引用须带标准 |
| `S:TEST:SET_PRESSURE_OFFSET_INCONSISTENCY` | `Q:TEST:SET_PRESSURE_OFFSET`<br>试验压力定义中的附加项 | ASME BPVC Section I-2010: `P-TEST-029` = 2 psi (0.014 MPa) | **标准自身不一致**：PG-69.2.3 的 P 定义用 +0.014 MPa， PG-69.2.2 的 rated slope 定义用 +0.015 MPa。两个数都照录，不修正。 | 标准原文不一致，已照录并标注 |

## 其他等价集

### 单位换算（UNIT_CONVERSION）

| 等价集 | US 侧 | SI 侧 | 表达式比值 |
|---|---|---|---|
| `S:TEST:WATER_FLOW_CONSTANT` | `P-TEST-001` | `P-TEST-002` | `0.00211549605` |
| `S:TEST:STEAM_FLOW_CONSTANT` | `P-TEST-003` | `P-TEST-004` | `0.1019417` |
| `S:TEST:FLOW_UNIT_FACTOR` | `P-TEST-010` | `P-TEST-011` | `8.333333` |
| `S:TEST:SUPERCRITICAL_RATIO` | `P-TEST-016` | `P-TEST-017` | `10.3444444` |

### 列对应（COLUMN_CORRESPONDENCE）

| 等价集 | 物理量 | 对应列 |
|---|---|---|
| `S:GEOM:FLANGE_GEOMETRY_CROSS_STANDARD` | `None` |  |

## 上下文清单

| xid | 类别 | 名称 |
|---|---|---|
| `X:UNIT_SYSTEM:US` | `UNIT_SYSTEM` | 英制单位（U.S. Customary Units） |
| `X:UNIT_SYSTEM:SI` | `UNIT_SYSTEM` | 公制单位（SI Units） |
| `X:UNIT_SYSTEM:MIXED` | `UNIT_SYSTEM` | 原文同时给出英制与公制 |
| `X:MATERIAL_GROUP:P_NO_1_GR_1_2_3` | `MATERIAL_GROUP` | ASME P-No.1 组，Group No. 1/2/3（碳钢、低合金钢） |
| `X:MATERIAL_GROUP:P_NO_1_GR_2` | `MATERIAL_GROUP` | ASME P-No.1 组，Group No.2（更高碳钢） |
| `X:MEDIUM:WATER` | `MEDIUM` | 水 |
| `X:MEDIUM:DRY_SATURATED_STEAM` | `MEDIUM` | 干饱和蒸汽 |
| `X:SEAT_TYPE:CONICAL_45` | `SEAT_TYPE` | 45° 锥座 |
| `X:SEAT_TYPE:FLAT` | `SEAT_TYPE` | 平座 |
| `X:NOZZLE_TYPE:SPRAY_NOZZLE` | `NOZZLE_TYPE` | 喷嘴型接口 |
| `X:PWHT_PATH:BPVC_NOTE_A1` | `PWHT_PATH` | BPVC-I TABLE PW-39 通用注 (a)(1) 路径（预热 200 °F，不看 CE） |
| `X:PWHT_PATH:BPVC_NOTE_A2` | `PWHT_PATH` | BPVC-I TABLE PW-39 通用注 (a)(2) 路径（CE ≤ 0.45 + 预热 250 °F） |
| `X:PWHT_PATH:B31_1_NOTE_A` | `PWHT_PATH` | ASME B31.1 Table 132 通用注 (a) 路径（预热 200 °F） |
| `X:PWHT_PATH:B31_1_NOTE_B` | `PWHT_PATH` | ASME B31.1 Table 132 通用注 (b) 路径（CE < 0.50 + 预热 250 °F） |
| `X:STANDARD:ASME_BPVC_I` | `STANDARD` | ASME BPVC Section I-2010 |
| `X:STANDARD:ASME_B31_1` | `STANDARD` | ASME B31.1-2007 |
| `X:TEST_TYPE:CAPACITY_DISCHARGE_COEFF` | `TEST_TYPE` | 排放系数容量试验 |
| `X:REGION:SUPERCRITICAL` | `REGION` | 超临界压力区 |

## 未决问题登记

本体不产生新事实。**疑似同族但无法确认的物理量不合并**，而是登记在这里，等证据到位再定案。

### OQ-01 —— 许用应力族：三个 qid 是否同一物理量

- 涉及物理量：`Q:MAT:MAX_WORKING_STRESS`, `Q:MAT:ALLOWABLE_STRESS`, `Q:STRUCT:ALLOWABLE_STRESS`
- 问题：F-MAT-001 是**无标准来源绑定的通用力学式**（利用率校核）， 它的 σ_allow 指"该零件的许用应力"； F-STR-004/005 的 S 指 BPVC 语境下的"最大许用工作应力"（随材料与温度而变）。 两者概念高度重叠但作用域不同：一个是零件级，一个是受压件级。
- 未合并原因：作用域差异未确认。BPVC 的 S 与零件许用应力在数值上是否总等， 取决于材料分组与温度，本库尚无足够的已核验条目支撑这个判断。 合并需要材料侧的证据，超出本轮本体层的范围。
- 解决路径：待材料性能类条目（许用应力表）进入参数层后，用"同一材料同一温度下 S 的取值" 交叉验证，再决定是否合并。

### OQ-02 —— 最小壁厚族：公式算出的最小壁厚 vs 标准给的限值

- 涉及物理量：`Q:STRUCT:MIN_WALL_THICKNESS`, `Q:MAT:MIN_WALL_THICKNESS`
- 问题：一个是 F-STR-004/005 由应力与许用应力**算出来**的最小壁厚， 一个是 PW-39 通用注 (11) 给的**最小壁厚限值**。 二者是不是同一个物理量，取决于标准是否把公式结果直接当限值用。
- 未合并原因：本库还没有把公式算得值与标准限值逐条比对的证据。 合并会把"计算目标"与"规范限值"混为一谈。
- 解决路径：待能用同一工况同时算出 t 与读出限值时再判定； 在此之前，两者应是两个不同 qid（一个说明怎么算，一个说明不能低于多少）。

---

**使用提醒**：

1. 本体层**不产生新事实**。所有数值、条款、判定方向都来自条目层；本体只声明「这些条目说的是不是同一个东西」。
2. 查数请以条目层为准，本体索引只做**定位与对照**。数值是否可信看条目的 `evidence.status`。
3. 读公式时不要只看字母。符号碰撞是实测出来的（见上表），必须经 qid 确认物理量。
4. `verdict: 不可互换` 的易混对，套错标准即误判，引用时必须带标准号。
5. 交互式查询：`python tools/ontology_query.py qid <QID>`、`symbol <SYM>`、`confusable`、`standard <名>`。

生成时间：2026-10-23T00:25:12+08:00