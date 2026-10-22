# 参数索引

> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。
> 参数条目本体在 `kb/parameters/`，证据件在 `kb/_evidence/`。

## 概况

| 项 | 值 |
|---|---|
| 参数条目总数 | **57** |
| 覆盖标准 | 2 |
| 视觉核验条目 | 49 |

## 按种类分布

| 种类 | 条目数 | 说明 |
|---|---|---|
| `COEFFICIENT` | 9 | 系数（修正因子、比例系数） |
| `CONSTANT` | 14 | 常数（SI/英制水常数等） |
| `DEFAULT_SUBSTITUTE` | 2 | 缺省替代值 |
| `LIMIT` | 17 | 限值（不得超过/不得低于） |
| `RANGE` | 3 | 区间（允许范围） |
| `THRESHOLD` | 10 | 阈值（判据门槛） |
| `UNIT_FACTOR` | 2 | 单位换算因子 |

## 按域分布

| 域 | 条目数 |
|---|---|
| `MATE` | 27 |
| `TEST` | 30 |

## 按标准浏览

### ASME B31.1-2007 —— 8 条

| ID | 名称 | 种类 | 值 | 判据 | 条款 | 状态 |
|---|---|---|---|---|---|---|
| `P-MAT-011` | 碳当量 CE 上限（免焊后热处理条件，B31.1） | `LIMIT` | < 0.50 | `<` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (b)(1) | PENDING_VERIFICATION |
| `P-MAT-012` | CE 后两项缺分析值时的替代值 0.1%（B31.1） | `DEFAULT_SUBSTITUTE` | 0.1 | `=` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (b)(1), Note | PENDING_VERIFICATION |
| `P-MAT-013` | 免 PWHT 路径 (b) 的公称材料厚度窗口（B31.1） | `RANGE` | 19.0..38 | `range` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (b) | PENDING_VERIFICATION |
| `P-MAT-014` | 免 PWHT 路径 (b)(2) 的最小预热 250 °F (121 °C)（B31.1） | `THRESHOLD` | 250 | `>=` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (b)(2) | PENDING_VERIFICATION |
| `P-MAT-015` | 单道焊缝熔敷厚上限 ¼ in. (6 mm)（B31.1） | `LIMIT` | 6 | `<=` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (b)(3) | PENDING_VERIFICATION |
| `P-MAT-016` | 通用注 (a)(2) 的预热条件 200 °F (95 °C)（B31.1） | `THRESHOLD` | 200 | `>=` | Table 132 (Postweld Heat Treatment) GENERAL NOTES (a)(2) | PENDING_VERIFICATION |
| `P-MAT-017` | P-No.1 材料的最小保温温度 1,100 °F (600 °C)（B31.1） | `THRESHOLD` | 1100 | `>=` | Table 132 (Postweld Heat Treatment), table body, P-No. 1 Gr. Nos. 1, 2, 3, column 'From Appendix A Range, °F (°C)' | PENDING_VERIFICATION |
| `P-MAT-018` | PWHT 保温时间 1 hr/in. (25 mm) 与超厚增量 2 hr + 15 min/每增厚 1 in.（B31.1） | `COEFFICIENT` | 1 hr per 1 in. (25 mm) | `=` | Table 132 (Postweld Heat Treatment), table body, columns 'Minimum Holding Time at Normal Temperature for Weld Thickness (Nominal)' — 'Up to 2 in. (50 mm)' and 'Over 2 in. (50 mm)' | PENDING_VERIFICATION |

### ASME BPVC Section I-2010 —— 49 条

| ID | 名称 | 种类 | 值 | 判据 | 条款 | 状态 |
|---|---|---|---|---|---|---|
| `P-TEST-001` | 水试验理论流量常数（英制） | `CONSTANT` | 2407 | `=` | PG-69.2.3 Coefficient of Discharge Method — For tests with water, For 45 deg seat (U.S. Customary Units) | VERIFIED_CLAUSE |
| `P-TEST-002` | 水试验理论流量常数（SI） | `CONSTANT` | 5.092 | `=` | PG-69.2.3 Coefficient of Discharge Method — For tests with water, For 45 deg seat (SI Units) | VERIFIED_CLAUSE |
| `P-TEST-003` | 干饱和蒸汽理论流量常数（英制） | `CONSTANT` | 51.5 | `=` | PG-69.2.3 Coefficient of Discharge Method — For tests with dry saturated steam, For 45 deg seat (U.S. Customary Units) | VERIFIED_CLAUSE |
| `P-TEST-004` | 干饱和蒸汽理论流量常数（SI） | `CONSTANT` | 5.25 | `=` | PG-69.2.3 Coefficient of Discharge Method — For tests with dry saturated steam, For 45 deg seat (SI Units) | VERIFIED_CLAUSE |
| `P-TEST-005` | 45° 阀座面积因子 | `COEFFICIENT` | 0.707 | `=` | PG-69.2.3 Coefficient of Discharge Method — For 45 deg seat | VERIFIED_CLAUSE |
| `P-TEST-006` | 设计排放系数 K 的上限 | `LIMIT` | 0.878 | `<=` | PG-69.2.3 Coefficient of Discharge Method（0.878 上限条款） | VERIFIED_CLAUSE |
| `P-TEST-007` | 单阀排放系数平均值折减系数 | `COEFFICIENT` | 0.90 | `=` | PG-69.2.3 Coefficient of Discharge Method | VERIFIED_CLAUSE |
| `P-TEST-008` | 单阀排放系数相对平均值的允许分散带 | `LIMIT` | 5 | `±` | PG-69.2.3 Coefficient of Discharge Method（±5% 条款） | VERIFIED_CLAUSE |
| `P-TEST-009` | 排放系数适用区间（beta ratio） | `RANGE` | 0.15..0.75 | `range` | PG-69.2.3 Coefficient of Discharge Method（beta ratio 条款） | VERIFIED_CLAUSE |
| `P-TEST-010` | 水流量单位换算因子（lb/hr → gal/min） | `UNIT_FACTOR` | 1/500 | `=` | PG-69.2.3 Coefficient of Discharge Method（单位换算注） | VERIFIED_CLAUSE |
| `P-TEST-011` | 水流量单位换算因子（kg/hr → L/min） | `UNIT_FACTOR` | 1/60 | `=` | PG-69.2.3 Coefficient of Discharge Method（单位换算注） | VERIFIED_CLAUSE |
| `P-TEST-012` | 压力修正因子的适用压力下限 | `LIMIT` | 1500 psig (10.3 MPa) | `>` | PG-69.2.3 Coefficient of Discharge Method（超临界压力修正因子条款） | VERIFIED_CLAUSE |
| `P-TEST-013` | 超临界修正因子的适用压力下限 | `LIMIT` | 3200 psig (22.1 MPa) | `>` | PG-69.2.3 Coefficient of Discharge Method（超临界修正因子条款） | VERIFIED_CLAUSE |
| `P-TEST-014` | K 上限 0.878 的构成因子 0.975 | `COEFFICIENT` | 0.975 | `=` | PG-69.2.3 Coefficient of Discharge Method — K 上限构成 | VERIFIED_CLAUSE |
| `P-TEST-015` | 超临界区容量外推常数 1,135.8 | `CONSTANT` | 1135.8 | `=` | PG-69.3（超临界区容量外推） | VERIFIED_CLAUSE |
| `P-TEST-016` | 超临界外推式 US 比值项 0.90/51.45 | `COEFFICIENT` | 0.90/51.45 | `=` | PG-69.3（超临界区容量外推，U.S. Customary Units） | VERIFIED_CLAUSE |
| `P-TEST-017` | 超临界外推式 SI 比值项 0.95/5.25 | `COEFFICIENT` | 0.95/5.25 | `=` | PG-69.3（超临界区容量外推，SI Units） | VERIFIED_CLAUSE |
| `P-TEST-018` | 1,135.8 常数所依据的 γ 因子 1.30 | `CONSTANT` | 1.30 | `=` | PG-69.3 NOTE（1,135.8 常数的依据） | VERIFIED_CLAUSE |
| `P-TEST-019` | 超临界外推的温度界限 800 °F (430 °C) | `THRESHOLD` | 800 °F (430 °C) | `=` | PG-69.3 NOTE（超临界温度界限） | VERIFIED_CLAUSE |
| `P-TEST-020` | 动力操作式泄压阀标记余量 3% | `THRESHOLD` | 3 | `=` | PG-69.4 Power-actuated pressure relieving valves（标记要求） | VERIFIED_CLAUSE |
| `P-TEST-021` | US 超临界压力修正因子分子系数 0.1906 | `CONSTANT` | 0.1906 | `=` | PG-69.2.3 超临界压力修正因子（U.S. Customary 版） | VERIFIED_CLAUSE |
| `P-TEST-022` | US 超临界压力修正因子分母系数 0.2292 | `CONSTANT` | 0.2292 | `=` | PG-69.2.3 超临界压力修正因子（U.S. Customary 版） | VERIFIED_CLAUSE |
| `P-TEST-023` | SI 超临界压力修正因子分子系数 27.6 | `CONSTANT` | 27.6 | `=` | PG-69.2.3 超临界压力修正因子（SI 版） | VERIFIED_CLAUSE |
| `P-TEST-024` | SI 超临界压力修正因子分母系数 33.2 | `CONSTANT` | 33.2 | `=` | PG-69.2.3 超临界压力修正因子（SI 版） | VERIFIED_CLAUSE |
| `P-TEST-025` | 超临界压力修正因子常数 1,000 | `CONSTANT` | 1000 | `=` | PG-69.2.3 超临界压力修正因子（SI 版） | VERIFIED_CLAUSE |
| `P-TEST-026` | 超临界压力修正因子常数 1,061 | `CONSTANT` | 1061 | `=` | PG-69.2.3 超临界压力修正因子（SI 版） | VERIFIED_CLAUSE |
| `P-TEST-027` | P 定义中的 set pressure 系数 1.03 | `COEFFICIENT` | 1.03 | `=` | PG-69.2.3 where（P 的定义） | VERIFIED_CLAUSE |
| `P-TEST-028` | P 定义中的大气压项 14.7 psia (0.101 MPa) | `CONSTANT` | 14.7 psia (0.101 MPa) | `=` | PG-69.2.3 where（P 的定义） | VERIFIED_CLAUSE |
| `P-TEST-029` | P 定义中的附加项 2 psi (0.014 MPa) —— 与 rated slope 的 0.015 MPa 不一致 | `CONSTANT` | 2 psi (0.014 MPa) | `=` | PG-69.2.3 where（P 的定义）对照 PG-69.2.2（rated slope 定义） | VERIFIED_CLAUSE |
| `P-TEST-030` | K_D 超出 ±5% 时的替换试验数量上限 4 | `LIMIT` | 4 | `=` | PG-69.2.3（K_D 分散带超差时的替换试验规定） | VERIFIED_CLAUSE |
| `P-MAT-001` | 碳当量 CE 上限（免焊后热处理条件） | `LIMIT` | <= 0.45 | `<=` | Table PW-39, GENERAL NOTES (a)(2)(a) | VERIFIED_CLAUSE |
| `P-MAT-002` | CE 后两项缺分析值时的替代值 0.15% | `DEFAULT_SUBSTITUTE` | 0.15 | `=` | Table PW-39, GENERAL NOTES (a)(2)(a), Note | VERIFIED_CLAUSE |
| `P-MAT-003` | 免 PWHT 路径 (a)(2) 的焊缝公称厚度窗口 | `RANGE` | 19..38 | `range` | Table PW-39, GENERAL NOTES (a)(2) | VERIFIED_CLAUSE |
| `P-MAT-004` | 免 PWHT 路径 (a)(2) 的最小预热温度 250 °F (120 °C) | `THRESHOLD` | 250 | `>=` | Table PW-39, GENERAL NOTES (a)(2)(b) | VERIFIED_CLAUSE |
| `P-MAT-005` | 单道焊缝熔敷厚上限 ¼ in. (6 mm) | `LIMIT` | 6 | `<=` | Table PW-39, GENERAL NOTES (a)(2)(c) | VERIFIED_CLAUSE |
| `P-MAT-006` | 免 PWHT 路径 (a)(1) 的预热条件 200 °F (95 °C) | `THRESHOLD` | 200 | `>=` | Table PW-39, GENERAL NOTES (a)(1) | VERIFIED_CLAUSE |
| `P-MAT-007` | P-No.1 材料的最小保温温度 1,100 °F (595 °C) | `THRESHOLD` | 1100 | `>=` | Table PW-39, table body, P-No. 1 Group No. 1,2,3, column 'Minimum Holding Temperature, °F (°C)' | VERIFIED_CLAUSE |
| `P-MAT-008` | PWHT 保温时间速率 1 hr/in.（1 hr/25 mm） | `COEFFICIENT` | 1 hr per 1 in. | `=` | Table PW-39, table body, column 'Minimum Holding Time at Normal Temperature for Weld Thickness (Nominal)', column 'Up to 2 in. (50 mm)' | VERIFIED_CLAUSE |
| `P-MAT-009` | PWHT 保温时间最小值 15 min | `LIMIT` | 15 | `>=` | Table PW-39, table body, column 'Up to 2 in. (50 mm)', cell note '15 min minimum' | VERIFIED_CLAUSE |
| `P-MAT-010` | PWHT 保温时间增量 15 min / 每增厚 1 in. (25 mm) | `COEFFICIENT` | 15 min per additional 1 in. (25 mm) | `=` | Table PW-39, table body, columns 'Over 2 in. (50 mm) to 5 in. (125 mm)' and 'Over 5 in. (125 mm)' | VERIFIED_CLAUSE |
| `P-MAT-019` | P-No.1 Group 2 材料的最大实际碳含量 0.30% | `LIMIT` | 0.30% | `<=` | TABLE PW-39 GENERAL NOTES (c) | VERIFIED_CLAUSE |
| `P-MAT-020` | PWHT 豁免的封头最大口径 NPS 8 (DN 200) | `LIMIT` | NPS 8 (DN 200) | `<=` | TABLE PW-39 GENERAL NOTES (c)(2) | VERIFIED_CLAUSE |
| `P-MAT-021` | PWHT 豁免的管子外径上限 2 in. (50 mm) 与开口上限 50 mm | `LIMIT` | 2 in. (50 mm) | `<=` | TABLE PW-39 GENERAL NOTES (c)(1) 与 (9)(a)/(12)(b) | VERIFIED_CLAUSE |
| `P-MAT-022` | PWHT 豁免的喉部/焊缝厚度上限 3/8 in. (10 mm) | `LIMIT` | 3/8 in. (10 mm) | `<=` | TABLE PW-39 GENERAL NOTES (6)(9)(b)(12)(c) | VERIFIED_CLAUSE |
| `P-MAT-023` | PW39 各项豁免中的 1/2 in. (13 mm) 厚度上限 | `LIMIT` | 1/2 in. (13 mm) | `<=` | TABLE PW-39 GENERAL NOTES (3)(a)(10)(11)(c)(14) | VERIFIED_CLAUSE |
| `P-MAT-024` | 热电偶固定焊缝的最小壁厚 0.200 in. (5.0 mm) | `LIMIT` | 0.200 in. (5.0 mm) | `>=` | TABLE PW-39 GENERAL NOTES (15)(b) | VERIFIED_CLAUSE |
| `P-MAT-025` | PW39 免焊后热处理的焊缝厚度分界 3/4 in. (19 mm) | `THRESHOLD` | 3/4 in. (19 mm) | `<=` | TABLE PW-39 GENERAL NOTES (1)(2) | VERIFIED_CLAUSE |
| `P-MAT-026` | PW39 (a)(1) 的母材厚度分界 1 in. (25 mm) | `THRESHOLD` | 1 in. (25 mm) | `>` | TABLE PW-39 GENERAL NOTES (1) | VERIFIED_CLAUSE |
| `P-MAT-027` | PW39 (a)(2) 焊缝厚度上限 1 1/2 in. (38 mm) | `LIMIT` | 1 1/2 in. (38 mm) | `<=` | TABLE PW-39 GENERAL NOTES (2) | VERIFIED_CLAUSE |

## 跨层引用

参数条目会指向它依赖的公式条目（`F-` 前缀），公式条目也会反向指向参数。

| 参数 ID | 引用公式 | 引用参数 |
|---|---|---|
| `P-MAT-011` | `F-MAT-003` | `P-MAT-012` `P-MAT-013` `P-MAT-001` |
| `P-MAT-012` | `F-MAT-003` | `P-MAT-011` `P-MAT-002` |
| `P-MAT-013` | — | `P-MAT-011` `P-MAT-014` `P-MAT-015` `P-MAT-003` |
| `P-MAT-014` | — | `P-MAT-013` `P-MAT-015` `P-MAT-004` `P-MAT-016` |
| `P-MAT-015` | — | `P-MAT-013` `P-MAT-014` `P-MAT-005` |
| `P-MAT-016` | — | `P-MAT-013` `P-MAT-006` `P-MAT-014` |
| `P-MAT-017` | — | `P-MAT-018` `P-MAT-007` |
| `P-MAT-018` | — | `P-MAT-017` `P-MAT-008` `P-MAT-009` `P-MAT-010` |
| `P-TEST-001` | `F-TEST-001` | `P-TEST-002` `P-TEST-005` |
| `P-TEST-002` | `F-TEST-001` | `P-TEST-001` `P-TEST-005` |
| `P-TEST-003` | `F-TEST-002` | `P-TEST-004` `P-TEST-005` |
| `P-TEST-004` | `F-TEST-002` | `P-TEST-003` `P-TEST-005` |
| `P-TEST-005` | `F-TEST-001` `F-TEST-002` | `P-TEST-001` `P-TEST-003` |
| `P-TEST-006` | `F-TEST-003` | `P-TEST-007` `P-TEST-009` |
| `P-TEST-007` | `F-TEST-003` | `P-TEST-006` `P-TEST-008` |
| `P-TEST-008` | `F-TEST-003` | `P-TEST-007` |
| `P-TEST-009` | `F-TEST-003` | `P-TEST-006` `P-TEST-008` |
| `P-TEST-010` | `F-TEST-001` | `P-TEST-011` |
| `P-TEST-011` | `F-TEST-001` | `P-TEST-010` |
| `P-TEST-012` | `F-TEST-002` | `P-TEST-013` |
| `P-TEST-013` | `F-TEST-002` | `P-TEST-012` |
| `P-TEST-014` | `F-TEST-003` | `P-TEST-006` `P-TEST-007` |
| `P-TEST-015` | `F-TEST-005` | `P-TEST-016` `P-TEST-017` `P-TEST-018` |
| `P-TEST-016` | `F-TEST-005` | `P-TEST-015` `P-TEST-017` |
| `P-TEST-017` | `F-TEST-005` | `P-TEST-015` `P-TEST-016` |
| `P-TEST-018` | `F-TEST-005` | `P-TEST-015` `P-TEST-019` |
| `P-TEST-019` | — | `P-TEST-015` `P-TEST-018` |
| `P-TEST-020` | `F-TEST-005` | `P-TEST-012` |
| `P-TEST-021` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-022` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-023` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-024` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-025` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-026` | `F-TEST-004` | `P-TEST-012` `P-TEST-013` |
| `P-TEST-027` | `F-TEST-001` `F-TEST-002` | `P-TEST-028` `P-TEST-029` |
| `P-TEST-028` | `F-TEST-001` | `P-TEST-027` `P-TEST-029` |
| `P-TEST-029` | `F-TEST-001` | `P-TEST-027` `P-TEST-028` |
| `P-TEST-030` | `F-TEST-003` | `P-TEST-008` |
| `P-MAT-001` | `F-MAT-003` | `P-MAT-002` `P-MAT-003` `P-MAT-011` |
| `P-MAT-002` | `F-MAT-003` | `P-MAT-001` `P-MAT-012` |
| `P-MAT-003` | — | `P-MAT-001` `P-MAT-004` `P-MAT-005` `P-MAT-013` |
| `P-MAT-004` | — | `P-MAT-003` `P-MAT-006` `P-MAT-014` |
| `P-MAT-005` | — | `P-MAT-003` `P-MAT-015` |
| `P-MAT-006` | — | `P-MAT-004` `P-MAT-016` |
| `P-MAT-007` | — | `P-MAT-008` `P-MAT-009` `P-MAT-010` `P-MAT-017` |
| `P-MAT-008` | — | `P-MAT-007` `P-MAT-009` `P-MAT-010` `P-MAT-018` |
| `P-MAT-009` | — | `P-MAT-008` `P-MAT-010` |
| `P-MAT-010` | — | `P-MAT-007` `P-MAT-008` `P-MAT-009` `P-MAT-018` |
| `P-MAT-019` | — | `P-MAT-020` `P-MAT-021` `P-MAT-016` `P-MAT-001` |
| `P-MAT-020` | — | `P-MAT-019` `P-MAT-021` |
| `P-MAT-021` | — | `P-MAT-019` `P-MAT-020` `P-MAT-022` |
| `P-MAT-022` | — | `P-MAT-021` `P-MAT-023` |
| `P-MAT-023` | — | `P-MAT-022` `P-MAT-024` |
| `P-MAT-024` | — | `P-MAT-023` |
| `P-MAT-025` | — | `P-MAT-003` `P-MAT-026` `P-MAT-027` `P-MAT-006` `P-MAT-001` |
| `P-MAT-026` | — | `P-MAT-006` `P-MAT-025` |
| `P-MAT-027` | — | `P-MAT-001` `P-MAT-003` `P-MAT-004` `P-MAT-005` `P-MAT-025` |

---

**使用提醒**：

1. `evidence.status` 为 `VERIFIED_CLAUSE` 的条目，其数值已在 PDF **纯位图**（剥离 OCR 文本层）上逐字肉眼核过，可直接引用。
2. `PENDING_VERIFICATION` 表示数值已抽取但尚未逐字核过，**不得直接作为计算依据**。
3. `value.relation` 表达该数在判据里的角色：`<=` 上限 / `>=` 下限 / `=` 精确值 / `range` 区间 / `approx` 近似值。不要用 `=` 掩盖原文的「不超过 / 不得低于 / 超过」。
4. 同一物理量在不同标准里数值不同（如 CE 阈值、预热温度），本库**按标准分条记录**，不合并、不取平均。

生成时间：2026-10-23T00:25:12+08:00