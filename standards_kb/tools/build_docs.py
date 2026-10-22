#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / build_docs.py —— 生成标准覆盖表与数据/参数索引

产出
----
  docs/STANDARD_COVERAGE.md —— 每个已登记标准：拿到什么、公式密度多少、产出什么
  docs/DATA_INDEX.md        —— 数据表条目索引（怎么查尺寸/公差/材料）
  docs/PARAMETER_INDEX.md   —— 参数条目索引（怎么查常数/系数/限值/阈值）

docs/INDEX.md 由 tools/index.py 单独生成（公式索引）。

纪律
----
本文件是**事实汇总**，不写「应该覆盖什么」这类计划性表述。
覆盖率低的就如实显示低。
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_entries as K  # noqa: E402
from standard_ids import family_of, std_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "kb"
DOCS = ROOT / "docs"
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_json(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_formulas() -> list[dict]:
    """公式条目。加载逻辑统一走 tools/kb_entries.py（共享模块）。

    口径统一的理由：三个校验器、索引器、查询器如果各写一份加载逻辑，
    迟早会出现「某个工具少算了几条」的口径漂移，而这种漂移会被误读成
    「数据没问题」。
    """
    return K.formula_entries()


def load_data_entries() -> list[dict]:
    """数据表条目。"""
    return K.data_entries()


def load_params() -> list[dict]:
    """参数条目（第三类知识对象：常数/系数/限值/阈值/材料性能等标量）。"""
    return K.param_entries()


def load_candidates() -> list[dict]:
    """候选池条目。

    kb/candidates/pool.json 的实际结构是
      {schema, generated_at, note, counts, by_standard: {<source_id>: [条目...]}}
    每条用 `source_id` 标注来源，不是 `source.standard_id`。
    """
    p = KB / "candidates" / "pool.json"
    d = load_json(p)
    if not d:
        return []
    if isinstance(d, dict):
        by_std = d.get("by_standard")
        if isinstance(by_std, dict):
            out = []
            for sid, items in by_std.items():
                for it in items or []:
                    r = dict(it)
                    r.setdefault("source_id", sid)
                    out.append(r)
            return out
        for k in ("candidates", "pool", "items", "records"):
            if isinstance(d.get(k), list):
                return d[k]
        return []
    return d


def ontology_summary() -> dict:
    """本体层统计摘要。本体层缺失时返回 error，不让覆盖表整个挂掉。"""
    try:
        import onto_model as OM
        onto = OM.load(ROOT)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    mapped = 0
    for lay in ("formula", "parameter", "data"):
        mapped += len(((onto.maps.get(lay) or {}).get("mappings") or {}))
    return {
        "quantities": len(onto.quantities),
        "contexts": len(onto.contexts),
        "sets": len(onto.sets),
        "occurrences": len(onto.occurrences),
        "criteria": len(onto.criteria),
        "bindings": len(onto.bindings),
        "columns": len(onto.columns),
        "mapped_entries": mapped,
        "collisions": len(OM.symbol_collisions(onto)),
        "open_questions": len(onto.open_questions),
    }


def build_coverage() -> str:
    reg = load_json(ROOT / "registry" / "registry.json") or {}
    formulas = load_formulas()
    data_entries = load_data_entries()
    params = load_params()
    cands = load_candidates()

    # 公式按标准归集
    #
    # 标准号归一口径（标准全名 -> 短 id、西里尔音译、家族归类）统一放在
    # tools/standard_ids.py；覆盖表与正文台账共用同一套映射，避免口径漂移。

    by_std: dict[str, list[dict]] = defaultdict(list)

    # 数据表条目同样按归一后的短 id 归集
    by_data: dict[str, list[dict]] = defaultdict(list)
    for d in data_entries:
        by_data[std_of(d.get("standard_id", ""))].append(d)
    for f in formulas:
        by_std[std_of(f["source"].get("standard_id", ""))].append(f)

    # 参数条目同样按归一后的短 id 归集
    by_param: dict[str, list[dict]] = defaultdict(list)
    for p in params:
        by_param[std_of(p["source"].get("standard_id", ""))].append(p)

    # 候选池按 source_id 归集
    cand_by_std: dict[str, int] = defaultdict(int)
    for c in cands:
        sid = c.get("source_id") or ""
        if sid:
            cand_by_std[sid] += 1

    L = []
    L.append("# 标准覆盖表")
    L.append("")
    L.append("> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。")
    L.append("> 记录的是**实测状态**，不是计划。覆盖为空就是空。")
    L.append("")

    # 家族汇总
    #
    # 归族与标准号归一的口径统一放在 tools/standard_ids.py（共享模块），
    # 覆盖表与正文台账用同一套映射，避免两边归属不一致。
    # 公式的 source.standard_id 是**标准全名**（如 "ASME BPVC Section I-2010"），
    # 与 registry 的源 id（如 "ASME-BPVC-I"）不是同一套命名，
    # 因此按关键词归族，而不是按 id 前缀。

    L.append("## 家族汇总")
    L.append("")
    L.append("| 家族 | 登记源数 | 已持有正文 | 正式公式条目 | 候选池 | 数据表条目 | 参数条目 |")
    L.append("|---|---|---|---|---|---|---|")
    fam_rows = []
    for fam, fdata in (reg.get("families") or {}).items():
        srcs = fdata.get("sources", [])
        n_body = sum(1 for s in srcs if s.get("body_status") in
                     ("FULL_TEXT_MIRROR", "LOCAL_FILE"))
        fam_formulas = [f for f in formulas
                        if family_of(f["source"].get("standard_id", "")) == fam]
        fam_data = [d for d in data_entries
                    if family_of(d.get("standard_id", "")) == fam]
        fam_param = [p for p in params
                     if family_of(p["source"].get("standard_id", "")) == fam]
        fam_cand = sum(n for s, n in cand_by_std.items()
                       if family_of(s) == fam)
        fam_rows.append((fam, fdata.get("label", ""), len(srcs), n_body,
                         len(fam_formulas), fam_cand, len(fam_data),
                         len(fam_param)))

    # 归不到任何已登记家族的内容(通用工程力学、通用机械设计等)不能悄悄消失,
    # 单列一行;再给合计行,让读者能自己复算总数。
    reg_fams = set(reg.get("families") or {})
    other_f = [f for f in formulas
               if family_of(f["source"].get("standard_id", "")) not in reg_fams]
    other_d = [d for d in data_entries
               if family_of(d.get("standard_id", "")) not in reg_fams]
    other_p = [p for p in params
               if family_of(p["source"].get("standard_id", "")) not in reg_fams]
    other_c = sum(n for s, n in cand_by_std.items()
                  if family_of(s) not in reg_fams)

    for fam, label, ns, nb, nf, nc, nd, np_ in fam_rows:
        L.append(f"| {fam} | {ns} | {nb} | {nf} | {nc} | {nd} | {np_} |")
    if other_f or other_d or other_c or other_p:
        L.append(f"| 其他/通用 | — | — | {len(other_f)} | {other_c} | "
                 f"{len(other_d)} | {len(other_p)} |")
    tot_f = sum(r[4] for r in fam_rows) + len(other_f)
    tot_c = sum(r[5] for r in fam_rows) + other_c
    tot_d = sum(r[6] for r in fam_rows) + len(other_d)
    tot_p = sum(r[7] for r in fam_rows) + len(other_p)
    L.append(f"| **合计** | {sum(r[2] for r in fam_rows)} | "
             f"{sum(r[3] for r in fam_rows)} | **{tot_f}** | **{tot_c}** | "
             f"**{tot_d}** | **{tot_p}** |")
    L.append("")
    L.append("> 「其他/通用」= 公式、数据或参数来自通用工程知识，"
             "不属于 GB/ASME/ГОСТ/ISO 任一已登记家族，单独列出不混进家族数。")
    L.append("")

    # 逐源明细
    L.append("## 逐源明细")
    L.append("")
    L.append("| 源 ID | 家族 | 类型 | 正文状态 | 抽取方式 | 正式公式 | 数据表 | 参数 | 候选 | 备注 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for fam, fdata in (reg.get("families") or {}).items():
        for s in fdata.get("sources", []):
            sid = s.get("id", "")
            # 候选池以**源 id** 为键（source_id），直接对应
            nc = cand_by_std.get(sid, 0)
            # 正式条目按归一后的短 id 归集（源级目录不产出条目）
            std_id = s.get("standard_id", "")
            key = std_of(std_id) if std_id else ""
            nf = len(by_std.get(key, []))
            nd = len(by_data.get(key, []))
            npar = len(by_param.get(key, []))
            note = (s.get("notes") or "").split("\n")[0][:56]
            L.append(
                f"| `{sid}` | {fam} | {s.get('kind','')} | "
                f"{s.get('body_status','')} | {s.get('extraction','')} | "
                f"{nf} | {nd} | {npar} | {nc} | {note} |")
    L.append("")

    # 公式来源分布
    L.append("## 公式来源分布")
    L.append("")
    L.append("| 标准 | 条款/出处 | 条目数 | 已核 | 待核 | 条款未核 |")
    L.append("|---|---|---|---|---|---|")
    for std_id in sorted(by_std):
        items = by_std[std_id]
        ver = sum(1 for e in items
                  if e["evidence"]["status"] == "VERIFIED_CLAUSE")
        pend = sum(1 for e in items
                   if e["evidence"]["status"] == "PENDING_VERIFICATION")
        unv = sum(1 for e in items
                  if e["evidence"]["status"] == "UNVERIFIED_CLAUSE")
        names = sorted({e["source"].get("standard_id", "") for e in items})
        L.append(f"| `{std_id}` | {' / '.join(names)[:56]} | {len(items)} | "
                 f"{ver} | {pend} | {unv} |")
    L.append("")

    # 参数来源分布
    L.append("## 参数来源分布")
    L.append("")
    L.append("| 标准 | 条款/出处 | 条目数 | 已核 | 待核 | 条款未核 | 视觉核验 |")
    L.append("|---|---|---|---|---|---|---|")
    for std_id in sorted(by_param):
        items = by_param[std_id]
        ver = sum(1 for e in items
                  if e["evidence"]["status"] == "VERIFIED_CLAUSE")
        pend = sum(1 for e in items
                   if e["evidence"]["status"] == "PENDING_VERIFICATION")
        unv = sum(1 for e in items
                  if e["evidence"]["status"] == "UNVERIFIED_CLAUSE")
        vis = sum(1 for e in items
                  if (e.get("source") or {}).get("visual_verified") is True)
        names = sorted({e["source"].get("standard_id", "") for e in items})
        L.append(f"| `{std_id}` | {' / '.join(names)[:56]} | {len(items)} | "
                 f"{ver} | {pend} | {unv} | {vis} |")
    L.append("")
    L.append("> 「视觉核验」= 该条目的数值在 PDF **纯位图**（剥离 OCR 文本层）上"
             "逐字肉眼核过。只有这一层核验通过，才允许标 `VERIFIED_CLAUSE`。")
    L.append("")

    # 本体层（映射层，不产生新事实）
    onto_s = ontology_summary()
    L.append("## 本体层（映射层）")
    L.append("")
    if onto_s.get("error"):
        L.append(f"> 本体层统计失败：{onto_s['error']}")
        L.append("")
    else:
        L.append("本体层是建立在三类条目之上的**映射层**：它不新增任何事实，"
                 "只声明「这些条目说的是不是同一个东西」。")
        L.append("完整索引见 [`ONTOLOGY_INDEX.md`](ONTOLOGY_INDEX.md)。")
        L.append("")
        L.append("| 项 | 值 |")
        L.append("|---|---|")
        L.append(f"| 已映射条目 | **{onto_s['mapped_entries']}** / "
                 f"{len(formulas) + len(data_entries) + len(params)} |")
        L.append(f"| 物理量 Quantity | {onto_s['quantities']} |")
        L.append(f"| 上下文 Context | {onto_s['contexts']} |")
        L.append(f"| 等价集 EquivalenceSet | {onto_s['sets']} |")
        L.append(f"| 出现 Occurrence | {onto_s['occurrences']} |")
        L.append(f"| 判据 Criterion（派生） | {onto_s['criteria']} |")
        L.append(f"| 变量绑定 VariableBinding | {onto_s['bindings']} |")
        L.append(f"| 表列投影 TableColumn | {onto_s['columns']} |")
        L.append(f"| 符号碰撞组 | {onto_s['collisions']} |")
        L.append(f"| 未决问题登记 | {onto_s['open_questions']} |")
        L.append("")
        L.append("> **符号碰撞组** = 同一个字母在库里指向多个物理量（实测 13 组）。"
                 "这是读公式时最容易串味的地方，消歧靠 qid，不靠人脑。")
        L.append("> **未决问题登记** = 疑似同族但证据不足以合并的物理量。"
                 "本库宁可留待决，也不靠命名相似度擅自合并。")
        L.append("")

    # 覆盖缺口（诚实列出）
    L.append("## 已知覆盖缺口")
    L.append("")
    L.append("以下为**实测确认**的空缺，不是推测：")
    L.append("")
    gaps = [
        ("ASME B16.34（阀门主标准）", "law.resource.org 与 archive.org 均无免费全文"),
        ("ASME B16.5 / B16.10 / B16.20 / B16.25", "同上，阀门系列其余部分缺正文"),
        ("ASME B31.3", "同上"),
        ("ASME BPVC Section II / Section VIII", "law.resource.org 与 archive.org 均无免费全文"
         "（archive.org 的 gov.law.asme.* 集合 47 项实测无 bpvc.ii / bpvc.viii），"
         "已登记为 PAYWALL 源，相关条目 body_status 同步为 PAYWALL"),
        ("ISO / IEC 全文", "iso.org 返回 403，webstore.iec.ch 需购买"),
        ("GB/T 正文文本层", "正文为栅格图，需 OCR；目录已有 1197 条，"
                            "正文可得性逐条记录在 gb_body_availability.json"
                            "（阀门相关 1003 条中仅 63 条有免费正文：63/940/0）"),
        ("ГОСТ 族", "meganorm.ru 已验证可取，但尚未批量抓取；"
                    "当前仅项目内 ГОСТ 1536-76 一份"),
    ]
    for what, why in gaps:
        L.append(f"- **{what}** —— {why}")
    L.append("")

    L.append("---")
    L.append("")
    L.append(f"生成时间：{datetime.now(CST).isoformat(timespec='seconds')}")
    return "\n".join(L)


def build_data_index() -> str:
    entries = load_data_entries()
    L = []
    L.append("# 数据表索引")
    L.append("")
    L.append("> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。")
    L.append("> 数据表条目本体在 `kb/data/`，机器抽取的原始行在 `kb/data/raw/`。")
    L.append("")
    L.append("## 概况")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 数据表条目总数 | **{len(entries)}** |")
    by_std = defaultdict(int)
    for e in entries:
        by_std[e.get("standard_id", "?")] += 1
    L.append(f"| 覆盖标准 | {len(by_std)} |")
    L.append("")

    if not entries:
        L.append("（暂无数据表条目）")
        L.append("")
        return "\n".join(L)

    # 按标准分组
    L.append("## 按标准浏览")
    L.append("")
    for std in sorted(by_std):
        items = [e for e in entries if e.get("standard_id") == std]
        L.append(f"### {std} —— {len(items)} 条")
        L.append("")
        L.append("| ID | 表名 | 条款 | 类型 | 行数 | 定位 |")
        L.append("|---|---|---|---|---|---|")
        for e in items:
            rows = len(e.get("rows", []) or [])
            # 定位串在 source.locator(字符串);老条目可能把 locator 放在根级
            src = e.get("source") or {}
            loc = src.get("locator") or e.get("locator") or ""
            if isinstance(loc, dict):
                loc = loc.get("where") or loc.get("table_ref") or ""
            where = e.get("table_ref") or ""
            loc_cell = f"`{loc}`" if loc else (where or "—")
            L.append(
                f"| `{e.get('id','')}` | {e.get('title_zh','')} | "
                f"{e.get('clause','')} | {e.get('table_kind','')} | {rows} | "
                f"{loc_cell} |")
        L.append("")

    # 字段字典（去重后的列定义）
    L.append("## 字段字典")
    L.append("")
    L.append("同一列在多个表中语义一致时，合并列出。")
    L.append("")
    L.append("| 键 | 中文名 | 原文 | 单位 |")
    L.append("|---|---|---|---|")
    seen: dict[str, dict] = {}
    for e in entries:
        for c in e.get("columns", []) or []:
            k = c.get("key", "")
            if k and k not in seen:
                seen[k] = c
    for k in sorted(seen):
        c = seen[k]
        L.append(f"| `{k}` | {c.get('name_zh','')} | {c.get('name_orig','')} | "
                 f"{c.get('unit','')} |")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**使用提醒**：数据表条目的 `evidence.status` 若为 `UNVERIFIED_CLAUSE`，"
             "表示行已抽取但尚未逐行核对原文，不得直接作为尺寸依据。")
    L.append("")
    L.append(f"生成时间：{datetime.now(CST).isoformat(timespec='seconds')}")
    return "\n".join(L)


def build_parameter_index() -> str:
    """参数条目索引（第三类知识对象）。

    参数是**标量**：常数、系数、限值、阈值、材料性能、单位换算因子。
    与公式（表达式）、数据表（多行表）形状不同，索引方式也不同：
    这里按「值 + 判据」列出来，方便直接查"这个数是多少、上限还是下限"。
    """
    entries = load_params()
    L = []
    L.append("# 参数索引")
    L.append("")
    L.append("> 本文件由 `tools/build_docs.py` 自动生成，请勿手工编辑。")
    L.append("> 参数条目本体在 `kb/parameters/`，证据件在 `kb/_evidence/`。")
    L.append("")

    L.append("## 概况")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 参数条目总数 | **{len(entries)}** |")
    by_std = defaultdict(int)
    for e in entries:
        by_std[(e.get("source") or {}).get("standard_id", "?")] += 1
    L.append(f"| 覆盖标准 | {len(by_std)} |")
    vis = sum(1 for e in entries
              if (e.get("source") or {}).get("visual_verified") is True)
    L.append(f"| 视觉核验条目 | {vis} |")
    L.append("")

    if not entries:
        L.append("（暂无参数条目）")
        L.append("")
        return "\n".join(L)

    # 按种类分布
    L.append("## 按种类分布")
    L.append("")
    L.append("| 种类 | 条目数 | 说明 |")
    L.append("|---|---|---|")
    kind_desc = {
        "CONSTANT": "常数（SI/英制水常数等）",
        "COEFFICIENT": "系数（修正因子、比例系数）",
        "LIMIT": "限值（不得超过/不得低于）",
        "THRESHOLD": "阈值（判据门槛）",
        "RANGE": "区间（允许范围）",
        "DEFAULT_SUBSTITUTE": "缺省替代值",
        "UNIT_FACTOR": "单位换算因子",
        "MATERIAL_PROPERTY": "材料性能",
    }
    kind_count = defaultdict(int)
    for e in entries:
        kind_count[e.get("param_kind", "?")] += 1
    for k in sorted(kind_count):
        L.append(f"| `{k}` | {kind_count[k]} | {kind_desc.get(k, '')} |")
    L.append("")

    # 按域分布
    L.append("## 按域分布")
    L.append("")
    dom_count = defaultdict(int)
    for e in entries:
        dom_count[e.get("domain", "?")] += 1
    L.append("| 域 | 条目数 |")
    L.append("|---|---|")
    for k in sorted(dom_count):
        L.append(f"| `{k}` | {dom_count[k]} |")
    L.append("")

    # 按标准浏览
    L.append("## 按标准浏览")
    L.append("")
    for std in sorted(by_std):
        items = [e for e in entries
                 if (e.get("source") or {}).get("standard_id") == std]
        L.append(f"### {std} —— {len(items)} 条")
        L.append("")
        L.append("| ID | 名称 | 种类 | 值 | 判据 | 条款 | 状态 |")
        L.append("|---|---|---|---|---|---|---|")
        for e in items:
            v = e.get("value") or {}
            src = e.get("source") or {}
            ev = e.get("evidence") or {}
            val = v.get("canonical") or v.get("display") or ""
            val = str(val).replace("|", "\\|")
            rel = v.get("relation") or ""
            clause = src.get("clause") or ""
            L.append(
                f"| `{e.get('id','')}` | {e.get('title_zh','')} | "
                f"`{e.get('param_kind','')}` | {val} | `{rel}` | {clause} | "
                f"{ev.get('status','')} |")
        L.append("")

    # 跨层引用
    L.append("## 跨层引用")
    L.append("")
    L.append("参数条目会指向它依赖的公式条目（`F-` 前缀），公式条目也会反向指向参数。")
    L.append("")
    L.append("| 参数 ID | 引用公式 | 引用参数 |")
    L.append("|---|---|---|")
    n_rel = 0
    for e in entries:
        rel = e.get("related") or []
        if not isinstance(rel, list):
            continue
        frefs = [r for r in rel if isinstance(r, str) and r.startswith("F-")]
        prefs = [r for r in rel if isinstance(r, str) and r.startswith("P-")]
        if not frefs and not prefs:
            continue
        n_rel += 1
        L.append(f"| `{e.get('id','')}` | "
                 f"{' '.join(f'`{x}`' for x in frefs) or '—'} | "
                 f"{' '.join(f'`{x}`' for x in prefs) or '—'} |")
    if not n_rel:
        L.append("| — | — | — |")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**使用提醒**：")
    L.append("")
    L.append("1. `evidence.status` 为 `VERIFIED_CLAUSE` 的条目，其数值已在 PDF "
             "**纯位图**（剥离 OCR 文本层）上逐字肉眼核过，可直接引用。")
    L.append("2. `PENDING_VERIFICATION` 表示数值已抽取但尚未逐字核过，"
             "**不得直接作为计算依据**。")
    L.append("3. `value.relation` 表达该数在判据里的角色："
             "`<=` 上限 / `>=` 下限 / `=` 精确值 / `range` 区间 / `approx` 近似值。"
             "不要用 `=` 掩盖原文的「不超过 / 不得低于 / 超过」。")
    L.append("4. 同一物理量在不同标准里数值不同（如 CE 阈值、预热温度），"
             "本库**按标准分条记录**，不合并、不取平均。")
    L.append("")
    L.append(f"生成时间：{datetime.now(CST).isoformat(timespec='seconds')}")
    return "\n".join(L)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "STANDARD_COVERAGE.md").write_text(build_coverage(), encoding="utf-8")
    (DOCS / "DATA_INDEX.md").write_text(build_data_index(), encoding="utf-8")
    (DOCS / "PARAMETER_INDEX.md").write_text(build_parameter_index(), encoding="utf-8")
    print(f"已生成 -> {DOCS.relative_to(ROOT)}/STANDARD_COVERAGE.md")
    print(f"已生成 -> {DOCS.relative_to(ROOT)}/DATA_INDEX.md")
    print(f"已生成 -> {DOCS.relative_to(ROOT)}/PARAMETER_INDEX.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
