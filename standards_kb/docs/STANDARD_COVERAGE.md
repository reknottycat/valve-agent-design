# 标准覆盖表

> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。
> 记录的是**实测状态**，不是计划。覆盖为空就是空。

## 家族汇总

| 家族 | 登记源数 | 已持有正文 | 正式公式条目 | 候选池 | 数据表条目 | 参数条目 |
|---|---|---|---|---|---|---|
| GB | 5 | 3 | 1 | 0 | 6 | 0 |
| ASME | 14 | 11 | 16 | 188 | 0 | 57 |
| GOST | 4 | 2 | 0 | 0 | 7 | 0 |
| ISO | 1 | 0 | 3 | 0 | 0 | 0 |
| 其他/通用 | — | — | 3 | 0 | 0 | 0 |
| **合计** | 24 | 16 | **23** | **188** | **13** | **57** |

> 「其他/通用」= 公式、数据或参数来自通用工程知识，不属于 GB/ASME/ГОСТ/ISO 任一已登记家族，单独列出不混进家族数。

## 逐源明细

| 源 ID | 家族 | 类型 | 正文状态 | 抽取方式 | 正式公式 | 数据表 | 参数 | 候选 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| `GB-PUB` | GB | CODE | FULL_TEXT_MIRROR | HTML_TABLE | 0 | 0 | 0 | 0 | 旧路径 /bzgk/gb/std_list 已失效；新路径 /bzgk/std/std_list 可用。 结果行 |
| `GB-PUB-BODY` | GB | CODE | FULL_TEXT_MIRROR | IMAGE_OCR | 0 | 0 | 0 | 0 | 三步链路，**顺序不可颠倒**： |
| `GB-GB_T_15530.1-2008` | GB | DIMENSION | FULL_TEXT_MIRROR | IMAGE_OCR | 0 | 6 | 0 | 0 | 本库**第一本真正取到正文的 GB/T 标准**：15 页、4 张精灵图（2320x3280，10x10 瓦片） |
| `GB-PUB-AVAIL` | GB | CODE | OFFICIAL_LIST | MANUAL | 0 | 0 | 0 | 0 | 逐条记录「该标准有没有免费在线正文」：OPEN_BODY / NO_BODY / ERROR。 **在目录里 ≠ |
| `GB-DOWNLOAD` | GB | CODE | PAYWALL | MANUAL | 0 | 0 | 0 | 0 | 需 verifyCode 图形验证码。**本库主动放弃此路径**（不绕过反爬机制）， 只用免费公开的在线预览路径 |
| `ASME-OFFICIAL` | ASME |  | OFFICIAL_LIST | MANUAL | 0 | 0 | 0 | 0 | 官方目录页只能证明标准名称、范围与现行版本 |
| `ASME-IBR` | ASME |  | FULL_TEXT_MIRROR | PDF_TEXT | 0 | 0 | 0 | 0 | 这是美国联邦法规合法引用(IBR)的免费镜像,是 ASME 正文最可靠的免费来源。 目录索引: https:// |
| `ASME-IA` | ASME |  | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 0 | 47 项含 B16.9 / B31.1 / B31.4 / B31.8 / B31.9 / BPVC I,IV, |
| `ASME-B16.9` | ASME | DIMENSION | FULL_TEXT_MIRROR | PDF_TEXT | 0 | 0 | 0 | 0 | 这本标准是尺寸/公差型（tmin、slope 1:3、角度公差、尺寸表）, 不含力学公式。属于「接口尺寸源」,不 |
| `ASME-B31.1` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 1 | 0 | 8 | 21 | 动力管道。含管道应力（膨胀/柔性）、支吊架载荷等公式族， 与阀门本体计算不同源但常被引用作对照基准。 |
| `ASME-B31.4` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 13 | 管道阀门专章,含阀门壳体应力与试验要求——本项目阀门类型的直接对口标准 |
| `ASME-B31.8` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 0 | 塑料管,本项目金属阀不直接适用,登记备查 |
| `ASME-B31.9` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 5 | OCR 文本层双栏流式交错,且希腊字母被 ASCII 化（S=σ, SE=σ_e）。 抽取器必须做版面重建 +  |
| `ASME-BPVC-I` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 12 | 0 | 49 | 116 | 锅炉压力容器规则,含大量应力/载荷/许用应力公式,是力学公式密度最高的一档。 已产出 9 条正式公式条目（kb/ |
| `ASME-BPVC-IV` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 29 | 采暖锅炉。含燃烧器/受热面热负荷公式族 |
| `ASME-BPVC-VII` | ASME | MECHANICS | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 0 | 动力锅炉。含汽包/过热器等高温部件公式族 |
| `ASME-BPVC-IX` | ASME | CODE | FULL_TEXT_MIRROR | OCR_TEXT | 0 | 0 | 0 | 4 | 焊接工艺评定。是本项目青铜阀焊接工艺的**体系性依据**（非公式源） |
| `ASME-BPVC-II` | ASME | MECHANICS | PAYWALL | NONE | 1 | 0 | 0 | 0 | 材料许用应力（allowable stress）分部，是压力容器材料选用的主依据。 **实测：law.resou |
| `ASME-BPVC-VIII` | ASME | CODE | PAYWALL | NONE | 2 | 0 | 0 | 0 | 压力容器建造规则（Division 1），含 UG-27 许用应力与应力分类条款。 **实测：law.resou |
| `GOST-MEGANORM` | GOST |  | FULL_TEXT_MIRROR | PDF_TEXT | 0 | 0 | 0 | 0 | 俄文 PDF,文本层正常(pymupdf 提取得到正确西里尔字母)。 实测样本为 ГОСТ 54544-2014 |
| `GOST-ALLGOSTS` | GOST |  | RENDERED_JS | MANUAL | 0 | 0 | 0 | 0 | 需浏览器执行校验脚本;项目已有的 gost1536/gost1536.htm 即出自该站 |
| `GOST-INTERNETLAW` | GOST |  | RENDERED_JS | MANUAL | 0 | 0 | 0 | 0 |  |
| `GOST-LOCAL` | GOST | DIMENSION | LOCAL_FILE | HTML_TABLE | 0 | 7 | 0 | 0 | 已由 gost1536/parse.py 解析为 gost1536.txt（45KB）， 并结构化为 7 条尺寸 |
| `ISO-OFFICIAL` | ISO |  | PAYWALL | MANUAL | 0 | 0 | 0 | 0 | 目录页可证明标准号、版本、现行状态;条款正文需购买 |

## 公式来源分布

| 标准 | 条款/出处 | 条目数 | 已核 | 待核 | 条款未核 |
|---|---|---|---|---|---|
| `ASME-B31.1` | ASME B31.1-2007 | 1 | 0 | 1 | 0 |
| `ASME-BPVC-I` | ASME BPVC Section I (PG-27) / ASME BPVC Section I-2010 | 12 | 10 | 2 | 0 |
| `ASME-BPVC-II` | ASME BPVC Section II Part D (材料许用应力表) | 1 | 0 | 0 | 1 |
| `ASME-BPVC-VIII` | ASME BPVC Section VIII-1 (UG-27(b)) / ASME BPVC Section  | 2 | 0 | 0 | 2 |
| `GB/T 3098.1 (紧固件机械性能) / ASME B16.5 (法兰)` | GB/T 3098.1 (紧固件机械性能) / ASME B16.5 (法兰) | 1 | 0 | 0 | 1 |
| `IEC 60534-2-1:2011` | IEC 60534-2-1:2011 | 2 | 0 | 0 | 2 |
| `ISO 5208:2015 (密封等级) / 通用密封力学` | ISO 5208:2015 (密封等级) / 通用密封力学 | 1 | 0 | 0 | 1 |
| `通用工程力学（座面几何分解）` | 通用工程力学（座面几何分解） | 1 | 0 | 0 | 1 |
| `通用机械设计（螺旋传动摩擦理论）` | 通用机械设计（螺旋传动摩擦理论） | 1 | 0 | 0 | 1 |
| `通用机械（杠杆原理）` | 通用机械（杠杆原理） | 1 | 0 | 0 | 1 |

## 参数来源分布

| 标准 | 条款/出处 | 条目数 | 已核 | 待核 | 条款未核 | 视觉核验 |
|---|---|---|---|---|---|---|
| `ASME-B31.1` | ASME B31.1-2007 | 8 | 0 | 8 | 0 | 0 |
| `ASME-BPVC-I` | ASME BPVC Section I-2010 | 49 | 49 | 0 | 0 | 49 |

> 「视觉核验」= 该条目的数值在 PDF **纯位图**（剥离 OCR 文本层）上逐字肉眼核过。只有这一层核验通过，才允许标 `VERIFIED_CLAUSE`。

## 本体层（映射层）

本体层是建立在三类条目之上的**映射层**：它不新增任何事实，只声明「这些条目说的是不是同一个东西」。
完整索引见 [`ONTOLOGY_INDEX.md`](ONTOLOGY_INDEX.md)。

| 项 | 值 |
|---|---|
| 已映射条目 | **93** / 93 |
| 物理量 Quantity | 140 |
| 上下文 Context | 18 |
| 等价集 EquivalenceSet | 14 |
| 出现 Occurrence | 80 |
| 判据 Criterion（派生） | 57 |
| 变量绑定 VariableBinding | 127 |
| 表列投影 TableColumn | 126 |
| 符号碰撞组 | 13 |
| 未决问题登记 | 2 |

> **符号碰撞组** = 同一个字母在库里指向多个物理量（实测 13 组）。这是读公式时最容易串味的地方，消歧靠 qid，不靠人脑。
> **未决问题登记** = 疑似同族但证据不足以合并的物理量。本库宁可留待决，也不靠命名相似度擅自合并。

## 已知覆盖缺口

以下为**实测确认**的空缺，不是推测：

- **ASME B16.34（阀门主标准）** —— law.resource.org 与 archive.org 均无免费全文
- **ASME B16.5 / B16.10 / B16.20 / B16.25** —— 同上，阀门系列其余部分缺正文
- **ASME B31.3** —— 同上
- **ASME BPVC Section II / Section VIII** —— law.resource.org 与 archive.org 均无免费全文（archive.org 的 gov.law.asme.* 集合 47 项实测无 bpvc.ii / bpvc.viii），已登记为 PAYWALL 源，相关条目 body_status 同步为 PAYWALL
- **ISO / IEC 全文** —— iso.org 返回 403，webstore.iec.ch 需购买
- **GB/T 正文文本层** —— 正文为栅格图，需 OCR；目录已有 1197 条，正文可得性逐条记录在 gb_body_availability.json（阀门相关 1003 条中仅 63 条有免费正文：63/940/0）
- **ГОСТ 族** —— meganorm.ru 已验证可取，但尚未批量抓取；当前仅项目内 ГОСТ 1536-76 一份

---

生成时间：2026-10-23T00:25:12+08:00