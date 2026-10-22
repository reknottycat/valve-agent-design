# standards_kb —— 标准 → 公式 + 数据 + 参数 知识库

把**标准正文**变成**可复用的公式条目、数据表条目与参数条目**，供阀门自主设计直接调用，
而不是每次重新翻标准。

覆盖三族：**GB/T（国标）· ASME（美标）· ГОСТ（俄标）**。

**版本**：`v1.1.0+20261022` —— 版本号规则 = **semver + 内容落库日期**（`+YYYYMMDD`）。
语义化版本按**资产内容**递增（新增标准族/新增数据表族/**新增知识对象层** → minor；修正正文数值或证据等级 → patch），
`+` 后是该次落库日期，便于把版本和 `runs/fetch_manifest.json` 的 `updated_at` 对齐。

> v1.1.0 的变化：新增**第三类知识对象 —— 参数条目**（常数/系数/限值/阈值/材料性能等标量），
> 独立 schema、独立目录、独立校验器与查询器。v1.0.0 的两类（公式 + 数据表）结构未变。

---

## 这个库解决什么问题

设计阀门时真正费时间的不是"知道有公式"，而是：

| 真实痛点 | 本库的对应物 |
|---|---|
| 公式记不清适用边界 | 每条公式都带 `valid_when` / `not_valid_when` |
| 不知道这条公式在哪一版标准的哪一条 | `source.clause` + `source.locator`（可回溯到 PDF 行号/页码） |
| 用错公式（薄壁公式套厚壁） | `applicability` 显式写"什么时候不能用" |
| 标准是"看过了但没留下" | 正文带 SHA256 台账 + 目录落盘成 JSON，**不用重下** |
| 尺寸/公差要翻表 | `kb/data/` 结构化数据表 + 字段字典 |
| **常数/限值/系数记不清，或记混是哪本标准的** | `kb/parameters/` 参数条目 + `value.relation` 判据方向 + `source.snippet` 原文 |
| 引用了没核对过的条款 | 证据等级 E0–E3 + `VERIFIED_CLAUSE` / `PENDING_VERIFICATION` / `UNVERIFIED_CLAUSE` |

---

## 三类知识对象

标准里的东西不止公式。三类对象按**形状**分，各有独立 schema、独立目录、独立校验器：

| 层 | 目录 | ID | 形状 | 典型内容 | 条数 |
|---|---|---|---|---|---|
| 公式 | `kb/formulas/` | `F-XXX-NNN` | **表达式** + 变量定义 + 适用条件 | 应力、流量、力矩、碳当量 | 23 |
| 数据表 | `kb/data/` | `D-XXX-NNN` | **多行表** + 列定义 + 行定位键 | 尺寸、公差、压力-温度等级、法兰面 | 13 |
| 参数 | `kb/parameters/` | `P-XXX-NNN` | **一个数** + 它在判据里的角色 | 常数、系数、限值、阈值、材料性能 | 57 |

每条都回答三个问题：**这个数/式是什么、在哪一条、怎么用**：

| 问题 | 承载字段（公式层） | 承载字段（参数层） |
|---|---|---|
| 是什么 | `canonical` / `latex` / `rearranged_forms` / `solved_for` | `value.canonical` / `value.display` / `value.numeric` |
| 在哪一条 | `source.clause` + `source.locator` + `source.snippet` | 同左（外加 `source.visual_verified`） |
| 怎么用 | `applicability.valid_when` + `usage.how` + `usage.pitfalls` | 同左（外加 `applicability.must_pair_with`） |
| 什么条件下不能用 | `applicability.not_valid_when` | `applicability.not_valid_when` |
| 是不是硬约束 | — | `value.relation`（`<=` / `>=` / `=` / `range` / `approx`） |

**参数层与数据表层不重叠**：尺寸表、公差表、压力等级表是**多行表**，留在数据表层；
参数层只收**标量**。判据方向（上限还是下限）写在 `value.relation` 里，
**不用 `=` 掩盖原文的「不超过 / 不得低于 / 超过」**。

---

## 目录结构

```
standards_kb/
├─ kb/
│  ├─ formulas/              公式条目（JSON 数组）
│  │  ├─ seed_core.json          5 条  通用力学/材料/流动
│  │  ├─ seed_engineering.json   6 条  驱动/密封/螺栓/几何
│  │  ├─ seed_bpvci.json         11 条 ASME BPVC Section I
│  │  └─ seed_b31_1.json          1 条 ASME B31.1 碳当量 CE
│  ├─ parameters/            参数条目（JSON 数组，第三类知识对象）
│  │  ├─ seed_bpvc_pg69.json     30 条  BPVC-I PG-69.2.3/69.4 试验常数与限值
│  │  ├─ seed_bpvc_pw39.json     19 条  BPVC-I TABLE PW-39 焊接/保温/豁免参数
│  │  └─ seed_b31_1_table132.json 8 条  B31.1 Table 132 同族参数
│  ├─ data/                  数据表条目（{entries:[...]}）
│  │  ├─ GB_T_15530.1-2008.json   6 条  压力-温度等级 + PN6/10/16/25 突面尺寸
│  │  ├─ ГОСТ_1536-76.json        7 条  船用法兰连接尺寸与密封面
│  │  ├─ raw/                    机器抽取的原始行（未经定名）
│  │  └─ specs/                  人工写的列名与语义（取数与定名分离）
│  ├─ _evidence/             共享证据件（公式层 + 参数层共用）
│  │  ├─ ASME-BPVC-I_p104_raster.png   纯位图（剥离 OCR 文本层）
│  │  ├─ ASME-BPVC-I_p105_raster.png
│  │  ├─ ASME-BPVC-I_p145_raster.png
│  │  ├─ ASME-BPVC-I_p235_raster.png
│  │  ├─ ASME-BPVC-I_p241_raster.png
│  │  └─ ASME-B31.1_table132_snippet.txt
│  ├─ candidates/            待复核候选池（188 条，稳定 hash ID）
│  │  ├─ pool.json                 汇总池
│  │  ├─ reviewed.json             复核结论（已采纳 1 条）
│  │  └─ <标准切片>/               按标准分的原始切片
│  ├─ catalog/               标准目录层（可复用资产）
│  │  ├─ gb_openstd.json           1197 条 GB/T 标准目录
│  │  ├─ gb_body_availability.json  1003 条阀门相关标准的正文可得性（63/940/0）
│  │  ├─ law_resource_ibr.json     120 份 ASME IBR 镜像目录
│  │  └─ archive_asme.json          47 项 archive.org ASME 集合
│  ├─ formula.schema.json    公式条目 schema
│  ├─ data.schema.json       数据表条目 schema
│  └─ parameter.schema.json  参数条目 schema
├─ registry/
│  ├─ sources.yaml           标准源登记表（4 族 24 源，手写，人读）
│  └─ registry.json          由 tools/registry_dump.py 生成（机器读）
├─ tools/                    挖掘管线（fetch → parse → extract → validate → index）
├─ runs/                     已抓取的正文（不进 git，大文件）
│  ├─ ASME-B16.9/ ASME-B31.1/ ASME-B31.4/ ASME-B31.8/ ASME-B31.9/
│  ├─ ASME-BPVC-I/ ASME-BPVC-IV/ ASME-BPVC-VII/ ASME-BPVC-IX/
│  ├─ GB-GB_T_15530.1-2008/  15 页页图 + 4 张精灵图
│  ├─ GOST-LOCAL/            ГОСТ 1536-76
│  └─ probe/                 核读用的渲染图与版面快照（临时，不入库）
└─ docs/
   ├─ INDEX.md               公式使用索引（按"我要算什么"组织）
   ├─ STANDARD_COVERAGE.md   标准覆盖表 + 已知缺口
   ├─ DATA_INDEX.md          数据表索引 + 字段字典
   └─ PARAMETER_INDEX.md     参数索引（值 + 判据 + 跨层引用）
```

---

## 怎么用

### 查公式

```bash
python tools/index.py          # 生成 docs/INDEX.md
```

`docs/INDEX.md` 按**怎么用**组织，不按标准号组织：

- 「我要算壁厚」→ 看「按目标量反查」表（`solved_for`）
- 「这条什么时候不能用」→ 看「使用警示」表（`not_valid_when`）
- 「这个数哪来的」→ 看条目的 `source.locator`

### 查数据表

```bash
python tools/data_query.py                 # 查结构化数据表（不联网）
python tools/check_gb_15530.py             # 核对 GB/T 15530.1 数据的跨表引用完整性
```

### 查参数

```bash
python tools/param_query.py                # 概览：按标准/域/种类/证据状态分组
python tools/param_query.py --id P-TEST-002     # 单条详情：取值/判据/原文/出处/怎么用
python tools/param_query.py --std ASME-BPVC-I  # 按标准过滤
python tools/param_query.py --domain MATE       # 按域过滤
python tools/param_query.py --kind LIMIT        # 按种类过滤（CONSTANT/COEFFICIENT/LIMIT/THRESHOLD/RANGE/...）
python tools/param_query.py --graph             # 跨层关系图（参数 ↔ 公式）
```

参数条目回答的是「**这个数是多少，它是上限还是下限，出自哪本标准哪一条**」。
`value.relation` 表达该数在判据里的角色（`<=` 上限 / `>=` 下限 / `=` 精确值 /
`range` 区间 / `approx` 近似值），**不用 `=` 掩盖原文的「不超过 / 不得低于 / 超过」**。

同一物理量在不同标准里数值不同（CE 阈值 ≤0.45 vs <0.50；预热 250 °F(120 °C) vs 250 °F(121 °C)；
保温 1,100 °F(595 °C) vs 1,100 °F(600 °C)），本库**按标准分条记录，不合并、不取平均**。

### 取新标准的正文

```bash
# GB/T：先查目录与可得性，再取正文
python tools/gb_body_query.py --list        # 哪些 GB/T 有免费正文（先查这个，别白花时间）
python tools/fetch_gb.py --standard "GB/T 12221-2025"   # 正文层（栅格图）

# ASME：直取 IBR 镜像
python tools/fetch.py --source ASME-IA --url <url> --file <name>
```

**GB/T 取正文的三步链路，顺序不可颠倒**（少一步就拿不到图）：

| 步 | 调用 | 关键点 |
|---|---|---|
| 1 | `newGbInfo` | 建立会话，拿 `hcno` |
| 2 | `showGb?type=online&hcno=<X>` | 拿页面清单 |
| 3 | `viewGbImg?fileName=<bg 原样>` | **必须带 `Cache-Alive: chunked`**，否则返回 200 但 0 字节 |

页面是 **2320×3280 精灵图的 10×10 瓦片**（单瓦片 232×328），同组各页瓦片互不重叠，
纯白页 span 为 0。

### 校验与索引

```bash
python tools/validate.py        # 校验公式条目（只查结构与纪律，跨层引用完整性）
python tools/validate_data.py   # 校验数据表条目
python tools/validate_params.py # 校验参数条目（12 类必查项）
python tools/registry_dump.py   # sources.yaml -> registry.json
python tools/index.py           # 生成 docs/INDEX.md
python tools/build_docs.py      # 生成 STANDARD_COVERAGE.md / DATA_INDEX.md / PARAMETER_INDEX.md
python tools/pool.py --stats    # 候选池统计
```

### 自测（校验器必须有牙）

```bash
python tools/selftest_formula_validator.py   # 25 项负向注入
python tools/selftest_data_validator.py      # 23 项负向注入
python tools/selftest_param_validator.py     # 60 项负向注入
python tools/scan_homoglyphs.py              # 西里尔/拉丁同形字扫描
```

自测会**故意注入坏数据**（等级虚标、占位 project_usage、locator 指向不存在的文件、
`row_keys` 与 `rows` 错位、canonical 与 numeric 不自洽、relation 与原文判据方向不符、
视觉核验状态未升级……），确认校验器真的报错，而不是恒过。

---

## 三条铁律

### 1. 官方目录页 ≠ 条款正文

目录只证明「标准叫什么、什么版本、什么状态、在哪一页」，**不证明任何一条条款的内容**。
每条公式条目必须单独标证据等级。

> 实测：GB 目录 1197 条，其中**阀门相关 1003 条里只有 63 条有免费在线正文**（63 / 940 / 0），
> 其余 `showGb` 直接 404。**在目录里 ≠ 正文免费开放** —— 选标准前先查
> `kb/catalog/gb_body_availability.json`。

### 2. 抓不到就记抓不到

`body_status` 严格区分，**两级语义**：

- **registry 级** = 这个**源**能不能拿到正文
- **条目级** = **该条内容**的获取形态

| 值 | 含义 | 当前用在哪 |
|---|---|---|
| `FULL_TEXT_MIRROR` | 本机已实测拿到正文 | GB/T 15530.1-2008（页图在手）、ASME 9 源 |
| `OFFICIAL_LIST` | 只能拿到官方目录/范围页 | GB 目录、ASME 官方目录、GB 可得性台账 |
| `PAYWALL` | 正文付费，本机不可得 | ASME BPVC Section II / VIII、GB 下载口、ISO 官方 |
| `RENDERED_JS` | 正文只在 JS 渲染的在线阅读器可见；本库已用三步链路取到页图，但**无文字层，只能视觉读表** | GB/T 15530.1 的 6 条数据条目、allgosts / internet-law |
| `LOCAL_FILE` | 项目内已有本地正文 | ГОСТ 1536-76 的 7 条数据条目 |
| `DERIVED_NO_TEXT` | **非标准条款 / 自行推导，本机无对应标准正文** | 3 条通用工程公式 |

不美化失败。GB 下载口需 `verifyCode` 图形验证码 —— **本库主动放弃该路径**（不绕过反爬），
只用免费公开的在线预览。

### 3. 扫描件必须用**纯位图**核验，不能用整页渲染图

ASME BPVC-I 的 PDF 是**扫描件 + OCR 文本层叠加**（`producer: Adobe Acrobat 9.51
Paper Capture Plug-in`）。整页渲染出来的图 = 位图 + OCR 文本层**叠画**，
数字被 OCR 文本盖在印刷原貌上，**核出来的"值"是 OCR 的值，不是印刷的值**。

正确做法是用 `tools/raster_crop.py` 直接抽页内位图（`doc.extract_image()` 取面积最大那张），
按 px/pt 比例裁像素，**剥离 OCR 文本层**：

```bash
python tools/raster_crop.py <pdf> <page> --full <out.png>              # 整页纯位图
python tools/raster_crop.py <pdf> <page> --rect x0 x1 y0 y1 <out.png>    # 裁一块（PDF point 坐标）
python tools/raster_crop.py <pdf> <page> --probe x0 x1 y0 y1            # 只探位置，不出图
```

证据件统一入库 `kb/_evidence/`（kb 层共享，公式层 + 参数层共用），条目的
`source.visual_verified` 字段承载"这条已在纯位图上逐字核过"这个语义，
`tools/validate_params.py` 把它和 `evidence.status` 双向绑定：

- `status: VERIFIED_CLAUSE` ⇒ `visual_verified` 必须为 `true`
- `visual_verified: true` 却仍挂 `PENDING_VERIFICATION` / `UNVERIFIED_CLAUSE` ⇒ **报「状态未升级」**

当前 57 条参数里 **49 条已视觉核验**（全部来自 BPVC-I 的 p.104 / p.105 / p.145 纯位图），
其余 8 条（B31.1 Table 132）因无 PDF 而只能 `PENDING_VERIFICATION`。

---

## 证据等级

**本库继承项目根 `F:\设计探索\README.md` 的 E0–E3 口径**，不另立一套：

| 等级 | 含义 |
|---|---|
| E0 | 工具能运行 |
| E1 | 数值与公式自洽 ← **本库绝大多数结论在此级** |
| E2 | 在可比物理数据范围内得到验证 |
| E3 | 本产品/同等样机的相关实测支持 |

条目状态：`VERIFIED_CLAUSE`（已核条款）· `PENDING_VERIFICATION`（待核）·
`UNVERIFIED_CLAUSE`（条款未核）· `CONFLICT`（有冲突）· `SUPERSEDED`（已被替代）

`grade`（验证强度）与 `status`（条款核验状态）是**两条正交的轴**，不能互相替代：
`grade: E1` + `status: UNVERIFIED_CLAUSE` 表示「公式自洽，但条款原文没核到」。

> **当前 E2 / E3 各 0 条。** 计算应力（CalculiX FEA 对照）属 E1 强化，**不构成 E2** ——
> E2 要的是"可比物理数据"，不是自己算一遍。
>
> **校验器只查结构与纪律，不验证工程正确性。**
> `tools/validate.py` 通过 ≠ 公式是对的。

### 校验器护栏

三个校验器（公式 / 数据表 / 参数）共用 `tools/evidence_rules.py` 里的规则模块，避免口径漂移：

| 护栏 | 行为 |
|---|---|
| 出处不可核 → 等级封顶 E1 | `body_status` ∈ {`PAYWALL`, `DERIVED_NO_TEXT`, `OFFICIAL_LIST`} 时不得高于 E1 |
| `grade` / `status` 双写同步 | 两处等级字段必须一致 |
| E2/E3 必须有真实 `project_usage` | 占位符（`不适用`/`n/a`/`-` 等）不算 |
| 声称 `FULL_TEXT_MIRROR` 必须能落到磁盘 | `source.locator` 指向的文件必须**真实存在** |
| `row_keys` 必须与 `rows` 逐列对齐 | 数据侧专用，见 `kb/data.schema.json#x-row-key-alignment` |
| **视觉核验门槛（双向）** | 参数侧专用：`VERIFIED_CLAUSE` ⇒ `source.visual_verified=true`；反之 `visual_verified=true` 却仍挂待核/未核 ⇒ 报「状态未升级」 |

参数侧另有 12 类必查项（`tools/validate_params.py`）：ID 格式、枚举合法性、
**数值自洽**（`value.numeric` 必须能从 `value.canonical` 解析出来）、RANGE 的 min≤max、
`relation` 与 canonical 前导符号一致、`relation='range'` ⟺ canonical 含 `..`、
`display` 与 canonical 数值不漂移、registry 归一与 `body_status` 一致、跨层 ID 完整性等。

### 跨层引用完整性

公式与参数**互相引用**（公式指向它用的参数，参数指向它依赖的公式），
所以引用完整性必须用**合并后的 ID 集合**校验，不能只看单层。
合并集合 = 公式 ID ∪ 参数 ID（当前 **80 个**），统一由 `tools/kb_entries.py` 提供。

---

## 当前状态

| 项 | 数 |
|---|---|
| 公式条目 | **23 条**（已核 10 / 待核 3 / 条款未核 10） |
| 数据表条目 | **13 条**（已核 6 / 条款未核 7） |
| **参数条目** | **57 条**（已核 49 / 待核 8；**视觉核验 49 条**） |
| 候选池 | **188 条**（已采纳 1 → F-MAT-003；待复核 187，全部 `confidence: LOW`） |
| 目录资产 | GB 1197 + 可得性 1003（63/940/0）+ ASME 47 + IBR 120 |
| registry | 4 族 / 24 源 |
| 已持有正文 | **10 份标准 / 48 个文件 / 70.8 MB** |

按家族（来源：`docs/STANDARD_COVERAGE.md`）：

| 家族 | 登记源 | 有正文 | 正式公式 | 候选 | 数据表 | 参数 |
|---|---|---|---|---|---|---|
| GB | 5 | 3 | 1 | 0 | 6 | 0 |
| ASME | 14 | 11 | 16 | 188 | 0 | 57 |
| ГОСТ | 4 | 2 | 0 | 0 | 7 | 0 |
| ISO | 1 | 0 | 3 | 0 | 0 | 0 |
| 其他/通用 | — | — | 3 | 0 | 0 | 0 |
| **合计** | **24** | **16** | **23** | **188** | **13** | **57** |

**与本项目的关系**：项目产品是 522-35.4179СБ 止回-截止直通式法兰青铜阀（DN200 / PN6）。
BPVC-I 是钢/合金规范，其 11 条公式条目与 49 条参数条目的 `usage.where` 已**诚实标注
「本项目当前不直接适用，属标准资产沉淀/未来复用」**。真正直接对口的是 ГОСТ 1536-76（法兰接口）
与 ASME B31.4（管道阀门）。

**参数层的边界划分**：尺寸/公差/压力等级这类**多行表**留在数据表层（`kb/data/`）；
参数层只收**标量**（常数、系数、限值、阈值、材料性能、单位换算因子）。
两者不混——`kb/data/` 的行有列定义与行定位键，参数条目只有「一个数 + 它在判据里的角色」。

---

## 已知技术陷阱（踩过的坑，别再踩）

| 陷阱 | 表现 | 正确做法 |
|---|---|---|
| **希腊字母 ASCII 化** | `σ`→`S`、`σ_E`→`SE` | 抽取后做符号归一 |
| **双栏流式交错** | 公式被截断在行尾 | 必须做版面重建（y 聚类 + x 排序） |
| **上下标拆行** | `Z₁`→`ZI`、`F·t`→`Fir` | 用**算术展开因子个数**判定：`nar = 0.7 F t D` 符号 3 槽 vs 数值 4 因子 → 必为 F×t |
| **西里尔/拉丁同形字** | 西里尔 `Г`(U+0413) 与拉丁 `OCT` 拼成的 token，肉眼与 `GOST` 无异 → 俄标全线失灵 | 跑 `tools/scan_homoglyphs.py`；新源码西里尔一律 `\uXXXX` 转义 |
| **音译 ≠ 同形字** | 按 GOST 7.79-2000 / ISO 9，西里尔 `С` 长得像 C 但音译是 **S**，俄标缩写是 `GOST` 不是 `GOCT` | 归族用同形字折叠，id 归一用音译表 |
| **罗马数字边界误归** | 朴素子串 `"ASME BPVC Section I"` 会命中 `Section II / VIII / IX`，把材料许用应力条目静默归到 BPVC-I | 别名用正则 + 否定前瞻 `(?![IVX])`，见 `tools/standard_ids.py` |
| **两套标准号命名空间** | 条目侧 `source.standard_id` 是**标准全名**，registry 是**短 id**，两边各用各的映射 → 台账「公式」列全是 0 | 统一走 `tools/standard_ids.py` 的 `std_of()` |
| **官方目录 ≠ 正文** | 以为拿到条款了 | 逐条标证据等级 |
| **GB 精灵图重组** | 页面是 2320×3280 精灵图的瓦片拼合 | 见 `tools/fetch_gb.py` 注释；同组各页瓦片互不重叠 |
| **GB viewGbImg 缺头** | 返回 200 但 0 字节 | 必须带 `Cache-Alive: chunked` |
| **GB 会话顺序** | showGb 被重定向回详情页 | 必须先 `newGbInfo` |
| **死代理伪装成"数据源挂了"** | 脚本注入 `HTTP_PROXY=127.0.0.1:7890`，而 FlClash 处于 DNS-only 状态 → `connection refused` | `tools/net_env.py` 先探端口再决定设不设代理；不通就**主动清掉** env 残留 |
| **扫描件整页渲染 ≠ 印刷原貌** | 渲染图 = 位图 + OCR 文本层叠画，数字被 OCR 值盖住 | 必须用 `tools/raster_crop.py` 抽纯位图再核 |
| **千分位被 OCR 吞掉 / 小数点丢失** | SI 水常数印作「5 092」，OCR 读成 `5092`（**差 1000 倍**） | 见下方「5 092 定案」：位图像素 + 排印风格 + 量纲反解，三重独立证据 |

### 「5 092」定案 —— 数值三重独立证据链

BPVC-I p.104 的 SI 水试验理论流量常数，**扫描件排印为「5 092」（空格分隔，无小数点）**。
若照字面取 5092，与 ASME 自述 `W_T = theoretical flow, lb/hr (kg/hr)` 冲突 **1000 倍**。
定案 **5.092**，依据三条**互相独立**的证据：

| 证据 | 内容 |
|---|---|
| ① 位图像素 | 2400 dpi 裁切 + 列直方图：US 版「2,407」在 1579–1583 列有 5 列墨迹（逗号）；SI 版「5 092」在 1574–1587 共 **14 列纯空白**（空格），**无小数点墨迹** |
| ② ASME 排印风格 | 同一页 SI 版用空格千分位（`1 000` / `1 061` / `1 135.8`），**小数点一律保留**（`5.25`、`0.707`）；US 版用逗号千分位。故「5 092」是**漏排小数点**的排印缺陷 |
| ③ 量纲反解 | `C_SI = 1e-6 × √(2×1e6) × 3600 = 5.09117`（误差 0.02%）；取 5092 则流量大 1000 倍 |

> 这条同时验证了另一件事：**不能只靠一条证据就改数**。单看「页上写 5 092」会得出
> 「原文就是这样」；单看量纲会得出「原文写错了」。三条证据交叉才敢定案，且要**照录原文**、
> 在条目里注明这是 ASME 的排印缺陷，不擅自"修正"标准。

---

## 复现与核验

```bash
python tools/provenance.py --verify   # 重算哈希，报告正文是否被改动
python tools/provenance.py --report   # 打印人类可读台账
```

`runs/` 下每份正文都有 `provenance.json`（SHA256 / 抓取 URL / 抓取时间 / 页数 / 字符数），
**递归哈希正文子目录**（GB 的页图与精灵图同样进台账）。
**未来任何人都能确认"手上这份正文跟当初抓到的是同一份"。**

全局台账在 `runs/fetch_manifest.json`，同时统计**公式条目、数据表条目、参数条目**三类资产。

### 网络现状（记录于本次交付）

| 目标 | 状态 |
|---|---|
| `www.openstd.samr.gov.cn` / `law.resource.org` / `hf-mirror.com` / `www.meganorm.ru` | 直连可达 |
| `archive.org` | **直连超时（10060）** —— 故 B31.1 无 PDF，其 CE 公式只能 `PENDING_VERIFICATION` |
| 本机 7890 / 7897 / 1053 代理口 | 全部不监听 |

---

## 相关文档

- `F:\设计探索\README.md` —— 项目总纲与 E0–E3 证据分级（本库继承此口径）
- `F:\设计探索\图纸\AI阀门自主设计_边界与Agent执行方案_v1.0.md` —— 设计输入边界
- `F:\设计探索\runs\20261006\C0\10_handoff\设计输入基线报告_522-35-4179.md` —— 阻塞项 B1–B6
