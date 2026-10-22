# 数据表索引

> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。
> 数据表条目本体在 `kb/data/`，机器抽取的原始行在 `kb/data/raw/`。

## 概况

| 项 | 值 |
|---|---|
| 数据表条目总数 | **13** |
| 覆盖标准 | 2 |

## 按标准浏览

### GB/T 15530.1-2008 —— 6 条

| ID | 表名 | 条款 | 类型 | 行数 | 定位 |
|---|---|---|---|---|---|
| `D-GBT15530-PT-PN` | PN 系列法兰压力-温度等级(PN6~PN40) | 表 1 | STRESS_TABLE | 5 | `runs/GB-GB_T_15530.1-2008/pages/p0002.png#table1` |
| `D-GBT15530-PT-CLASS` | Class 系列法兰压力-温度等级(Class150 / Class300,全平面型) | 表 2 | STRESS_TABLE | 2 | `runs/GB-GB_T_15530.1-2008/pages/p0003.png#table2` |
| `D-GBT15530-PN6-RF` | PN6 突面(RF 型)铜合金整体铸造法兰尺寸 | 表 3 | DIMENSION_TABLE | 26 | `runs/GB-GB_T_15530.1-2008/pages/p0004.png#table3` |
| `D-GBT15530-PN10-RF` | PN10 突面(RF 型)铜合金整体铸造法兰尺寸 | 表 4 | DIMENSION_TABLE | 21 | `runs/GB-GB_T_15530.1-2008/pages/p0005.png#table4` |
| `D-GBT15530-PN16-RF` | PN16 突面(RF 型)铜合金整体铸造法兰尺寸 | 表 5 | DIMENSION_TABLE | 21 | `runs/GB-GB_T_15530.1-2008/pages/p0006.png#table5` |
| `D-GBT15530-PN25-RF` | PN25 突面(RF 型)铜合金整体铸造法兰尺寸 | 表 6 | DIMENSION_TABLE | 21 | `runs/GB-GB_T_15530.1-2008/pages/p0007.png#table6` |

### ГОСТ 1536-76 —— 7 条

| ID | 表名 | 条款 | 类型 | 行数 | 定位 |
|---|---|---|---|---|---|
| `D-GOST1536-PN025` | 法兰连接尺寸(公称压力 ≤ 0.25 МПа / 2.5 кгс/см²) | Таблица 1 | DIMENSION_TABLE | 14 | `runs/GOST-LOCAL/gost_1536_76.txt#table1` |
| `D-GOST1536-PN063` | 法兰连接尺寸(公称压力 ≤ 0.63 МПа / 6.3 кгс/см²) | Таблица 2 | DIMENSION_TABLE | 17 | `runs/GOST-LOCAL/gost_1536_76.txt#table2` |
| `D-GOST1536-PN10` | 法兰连接尺寸(公称压力 ≤ 1.0 МПа / 10 кгс/см²) | Таблица 3 | DIMENSION_TABLE | 17 | `runs/GOST-LOCAL/gost_1536_76.txt#table3` |
| `D-GOST1536-PN16` | 法兰连接尺寸(公称压力 ≤ 1.6 МПа / 16 кгс/см²) | Таблица 4 | DIMENSION_TABLE | 17 | `runs/GOST-LOCAL/gost_1536_76.txt#table4` |
| `D-GOST1536-PN25` | 法兰连接尺寸(公称压力 ≤ 2.5 МПа / 25 кгс/см²) | Таблица 5 | DIMENSION_TABLE | 15 | `runs/GOST-LOCAL/gost_1536_76.txt#table5` |
| `D-GOST1536-PN40` | 法兰连接尺寸(公称压力 ≤ 4.0 МПа / 40 кгс/см²) | Таблица 6 | DIMENSION_TABLE | 14 | `runs/GOST-LOCAL/gost_1536_76.txt#table6` |
| `D-GOST1536-PN63` | 法兰连接尺寸(公称压力 ≤ 6.3 МПа / 63 кгс/см²,双头螺柱连接) | Таблица 7 | DIMENSION_TABLE | 13 | `runs/GOST-LOCAL/gost_1536_76.txt#table7` |

## 字段字典

同一列在多个表中语义一致时，合并列出。

| 键 | 中文名 | 原文 | 单位 |
|---|---|---|---|
| `C` | 法兰厚度 | C | mm |
| `D` | 法兰外径 | D | mm |
| `D1` | 密封面外径(对接面外径) | D1 | mm |
| `D2` | 密封面内径(凸面密封直径) | D2 | mm |
| `D3` | 密封台阶外径 | D3 | mm |
| `D4` | 密封台阶内径 | D4 | mm |
| `D5` | 凹面密封外径 | D5 | mm |
| `D6` | 凹面密封内径 | D6 | mm |
| `Dn` | 公称尺寸 | 公称尺寸 DN | mm |
| `K` | 螺栓孔中心圆直径 | K | mm |
| `L` | 螺栓孔径 | L | mm |
| `N` | 法兰颈长度 | N | mm |
| `R` | 法兰颈过渡圆角半径 | R | mm |
| `bolt_count` | 螺栓数量 | Болты — Количество | dimensionless |
| `bolt_thread` | 螺栓螺纹规格 | 螺纹规格 | thread |
| `d` | 密封面直径 | d | mm |
| `dn_ff` | 公称尺寸范围(FF 全平面型) | 公称尺寸 DN(FF 型) | text |
| `dn_range` | 公称尺寸范围 | 公称尺寸 DN | text |
| `dn_rf` | 公称尺寸范围(RF 突面型) | 公称尺寸 DN(RF 型) | text |
| `dn_tg` | 公称尺寸范围(TG 榫槽面型) | 公称尺寸 DN(TG 型) | text |
| `f` | 密封面凸起高度 | f | mm |
| `groove_count` | 密封槽数量 | Уплотнительные канавки — Количество | dimensionless |
| `n` | 螺栓数量 | 数量 n | dimensionless |
| `p_100` | 最大无冲击工作压力(100 ℃) | 最大无冲击工作压力 | MPa |
| `p_120` | 最大工作压力(120 ℃) | 最大工作压力 | MPa |
| `p_150` | 最大无冲击工作压力(150 ℃) | 最大无冲击工作压力 | MPa |
| `p_180` | 最大无冲击工作压力(180 ℃) | 最大无冲击工作压力 | MPa |
| `p_200` | 最大工作压力(200 ℃) | 最大工作压力 | MPa |
| `p_220` | 最大无冲击工作压力(220 ℃) | 最大无冲击工作压力 | MPa |
| `p_250` | 最大工作压力(250 ℃) | 最大工作压力 | MPa |
| `p_260` | 最大无冲击工作压力(260 ℃) | 最大无冲击工作压力 | MPa |
| `p_m10_65` | 最大无冲击工作压力(-10~65 ℃) | 最大无冲击工作压力 | MPa |
| `pn` | 公称压力 | PN | dimensionless |
| `q` | 密封槽深度 | q | mm |
| `type` | 类型 | 类型 | text |

---

**使用提醒**：数据表条目的 `evidence.status` 若为 `UNVERIFIED_CLAUSE`，表示行已抽取但尚未逐行核对原文，不得直接作为尺寸依据。

生成时间：2026-10-22T15:11:37+08:00