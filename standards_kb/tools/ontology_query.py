#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""standards_kb 本体层查询工具。

本体层的存在意义不是"多存一份数据"，而是回答三类问题：

  1. 涉及哪些公式/参数/表列？      -> 按物理量（qid）或条目反查
  2. 在哪个地方？                   -> 标准 + 条款
  3. 怎么使用？                     -> 条目 usage.where / usage.how

其中"跨标准对齐"是本体层独有的能力：
同一个物理量在不同标准下可能由不同的公式计算、取不同的阈值，
本体把这些落到同一 qid 上，就能一张表横向对照。

用法：
  python tools/ontology_query.py qid Q:MAT:CARBON_EQUIVALENT
  python tools/ontology_query.py standard "ASME B31.1"
  python tools/ontology_query.py domain GEOM
  python tools/ontology_query.py symbol A
  python tools/ontology_query.py confusable
  python tools/ontology_query.py entry P-MAT-001
  python tools/ontology_query.py stats
  python tools/ontology_query.py collisions
  python tools/ontology_query.py --json qid Q:MAT:CARBON_EQUIVALENT

只读工具：不修改知识库任何文件。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onto_model as OM  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

LAYER_LABEL = {"formula": "公式", "parameter": "参数", "data": "数据表"}
KIND_LABEL = {"VALUE": "取值", "RESULT": "结果", "NONE": "仅表列"}


# --------------------------------------------------------------------------- #
# 通用小工具
# --------------------------------------------------------------------------- #
def _out(s: str = "") -> None:
    print(s)


def _rule(title: str = "", width: int = 78) -> None:
    if title:
        _out(f"-- {title} " + "-" * max(0, width - len(title) - 4))
    else:
        _out("-" * width)


def _usage_of(entry: dict) -> dict:
    u = entry.get("usage") or {}
    return u if isinstance(u, dict) else {}


def _value_line(entry: dict) -> str:
    """取条目的"值"表述：参数层用 canonical，公式层用表达式，数据层用表引用。"""
    layer = None
    for lay, tbl in (("formula", "x"),):
        pass
    v = entry.get("value") or {}
    if isinstance(v, dict) and v.get("canonical"):
        return str(v["canonical"])
    expr = entry.get("expression") or {}
    if isinstance(expr, dict) and expr.get("canonical"):
        return str(expr["canonical"])
    if entry.get("table_ref"):
        return str(entry["table_ref"])
    return "-"


def _layer_of(onto: OM.Onto, entry_id: str) -> str:
    return onto.layer_of(entry_id) or "-"


def _standards_of(onto: OM.Onto) -> list[str]:
    out = set()
    for layer in ("formula", "parameter", "data"):
        for e in onto.entries[layer].values():
            s = OM.entry_standard(e)
            if s:
                out.add(s)
    return sorted(out)


# --------------------------------------------------------------------------- #
# 各类查询
# --------------------------------------------------------------------------- #
def q_qid(onto: OM.Onto, qid: str) -> dict:
    """按物理量查：这是本体层的核心视图 —— 跨标准对齐。"""
    q = onto.quantities.get(qid)
    occs = sorted(
        onto.occurrences_of(qid),
        key=lambda o: (str(o.get("standard_id") or ""), str(o.get("entry_id"))),
    )
    crits = sorted(
        onto.criteria_of(qid),
        key=lambda c: (str(c.get("standard_id") or ""), str(c.get("entry_id"))),
    )
    sets = [s for s in onto.sets if s.get("quantity") == qid]
    cols = [c for c in onto.columns if c.get("quantity_or_text") == qid]
    binds = [b for b in onto.bindings if b.get("quantity") == qid]
    return {
        "qid": qid,
        "name_zh": (q or {}).get("name_zh"),
        "dimension": (q or {}).get("dimension"),
        "domain": (q or {}).get("domain"),
        "canonical_unit": (q or {}).get("canonical_unit"),
        "defined": q is not None,
        "occurrences": [
            {
                "entry_id": o.get("entry_id"),
                "layer": o.get("entry_layer"),
                "occurrence_kind": o.get("occurrence_kind"),
                "role": o.get("role"),
                "relation": o.get("relation"),
                "standard_id": o.get("standard_id"),
                "clause": o.get("clause"),
                "value": _value_line(onto.entry_of(o.get("entry_id")) or {}),
                "unit": ((onto.entry_of(o.get("entry_id")) or {}).get("value") or {}).get("unit_text"),
                "note": o.get("note"),
            }
            for o in occs
        ],
        "criteria": [
            {
                "cid": c.get("cid"),
                "entry_id": c.get("entry_id"),
                "relation": c.get("relation"),
                "threshold": c.get("threshold"),
                "unit": c.get("unit"),
                "standard_id": c.get("standard_id"),
                "clause": c.get("clause"),
            }
            for c in crits
        ],
        "equivalence_sets": [
            {
                "sid": s.get("sid"),
                "kind": s.get("kind"),
                "members": s.get("members"),
                "verdict": s.get("verdict"),
                "difference": s.get("difference"),
                "standards": s.get("standards"),
            }
            for s in sets
        ],
        "columns": cols,
        "bindings": binds,
    }


def q_standard(onto: OM.Onto, needle: str) -> dict:
    """按标准查：该标准涉及哪些物理量、哪些条目。"""
    needle = needle.strip()
    rows = []
    qids = set()
    for layer in ("formula", "parameter", "data"):
        for eid, e in sorted(onto.entries[layer].items()):
            std = OM.entry_standard(e)
            if not std or needle.lower() not in std.lower():
                continue
            occ = onto.occurrences.get(eid)
            qid = (occ or {}).get("quantity")
            if qid:
                qids.add(qid)
            rows.append(
                {
                    "entry_id": eid,
                    "layer": layer,
                    "title_zh": e.get("title_zh"),
                    "standard_id": std,
                    "clause": OM.entry_clause(e),
                    "quantity": qid,
                    "quantity_name": onto.qname(qid) if qid else None,
                    "value": _value_line(e),
                }
            )
    return {
        "query": needle,
        "standards": sorted({r["standard_id"] for r in rows}),
        "entry_count": len(rows),
        "quantity_count": len(qids),
        "quantities": sorted(qids),
        "entries": rows,
    }


def q_domain(onto: OM.Onto, domain: str) -> dict:
    """按域查。域在公式层与参数层是共享枚举。"""
    domain = domain.strip().upper()
    rows = []
    qids = set()
    for layer in ("formula", "parameter", "data"):
        for eid, e in sorted(onto.entries[layer].items()):
            dom = e.get("domain") or e.get("design_domain")
            if not dom or str(dom).upper() != domain:
                continue
            occ = onto.occurrences.get(eid)
            qid = (occ or {}).get("quantity")
            if qid:
                qids.add(qid)
            rows.append(
                {
                    "entry_id": eid,
                    "layer": layer,
                    "title_zh": e.get("title_zh"),
                    "standard_id": OM.entry_standard(e),
                    "clause": OM.entry_clause(e),
                    "quantity": qid,
                    "quantity_name": onto.qname(qid) if qid else None,
                    "value": _value_line(e),
                }
            )
    return {
        "query": domain,
        "entry_count": len(rows),
        "quantity_count": len(qids),
        "quantities": sorted(qids),
        "entries": rows,
    }


def q_symbol(onto: OM.Onto, sym: str) -> dict:
    """按符号查 —— 消歧视图：同一个字母在库里到底指几个东西。"""
    idx = OM.symbol_index(onto)
    hits = []
    for s, refs in sorted(idx.items()):
        if s.lower() != sym.strip().lower():
            continue
        for r in refs:
            hits.append(
                {
                    "symbol": s,
                    "namespace": r["ns"],
                    "quantity": r["qid"],
                    "quantity_name": onto.qname(r["qid"]),
                    "where": r["where"],
                }
            )
    qids = sorted({h["quantity"] for h in hits})
    return {
        "query": sym,
        "hit_count": len(hits),
        "distinct_quantities": qids,
        "ambiguous": len(qids) >= 2,
        "hits": hits,
    }


def q_confusable(onto: OM.Onto, qid: str | None) -> dict:
    """易混对清单：跨标准同判据不同取值，必须一起看。"""
    out = []
    for s in onto.sets_of_kind("CONFUSABLE"):
        if qid and s.get("quantity") != qid:
            continue
        vals = []
        for v in s.get("values") or []:
            e = onto.entry_of(v.get("entry_id")) or {}
            vals.append(
                {
                    "entry_id": v.get("entry_id"),
                    "relation": v.get("relation"),
                    "value": v.get("value"),
                    "si_value": v.get("si_value"),
                    "unit": v.get("unit"),
                    "clause": v.get("clause"),
                    "standard_id": OM.entry_standard(e),
                }
            )
        out.append(
            {
                "sid": s.get("sid"),
                "quantity": s.get("quantity"),
                "quantity_name": onto.qname(s.get("quantity") or ""),
                "members": s.get("members"),
                "standards": s.get("standards"),
                "values": vals,
                "difference": s.get("difference"),
                "risk": s.get("risk"),
                "verdict": s.get("verdict"),
                "cross_standard": s.get("cross_standard"),
            }
        )
    return {"query": qid, "count": len(out), "sets": out}


def q_entry(onto: OM.Onto, eid: str) -> dict:
    """按条目查：反查它落在哪些物理量上、涉及哪些等价集。"""
    e = onto.entry_of(eid)
    if e is None:
        return {"query": eid, "found": False}
    occ = onto.occurrences.get(eid)
    qid = (occ or {}).get("quantity")
    sets = [s.get("sid") for s in onto.sets if eid in (s.get("members") or [])]
    u = _usage_of(e)
    return {
        "query": eid,
        "found": True,
        "layer": onto.layer_of(eid),
        "title_zh": e.get("title_zh"),
        "quantity": qid,
        "quantity_name": onto.qname(qid or ""),
        "occurrence_kind": (occ or {}).get("occurrence_kind"),
        "role": (occ or {}).get("role"),
        "standard_id": OM.entry_standard(e),
        "clause": OM.entry_clause(e),
        "value": _value_line(e),
        "equivalence_sets": sets,
        "usage_where": u.get("where") or [],
        "usage_how": u.get("how"),
        "related": e.get("related") or [],
    }


def q_stats(onto: OM.Onto) -> dict:
    kinds: dict[str, int] = {}
    for o in onto.occurrences.values():
        k = str(o.get("occurrence_kind"))
        kinds[k] = kinds.get(k, 0) + 1
    sets_by_kind: dict[str, int] = {}
    for s in onto.sets:
        k = str(s.get("kind"))
        sets_by_kind[k] = sets_by_kind.get(k, 0) + 1
    stds: dict[str, int] = {}
    for layer in ("formula", "parameter", "data"):
        for e in onto.entries[layer].values():
            s = OM.entry_standard(e) or "(未标注)"
            stds[s] = stds.get(s, 0) + 1
    domains: dict[str, int] = {}
    for q in onto.quantities.values():
        d = str(q.get("domain"))
        domains[d] = domains.get(d, 0) + 1
    return {
        "spec_version": (onto.spec.get("meta") or {}).get("version"),
        "quantities": len(onto.quantities),
        "contexts": len(onto.contexts),
        "equivalence_sets": len(onto.sets),
        "sets_by_kind": sets_by_kind,
        "occurrences": len(onto.occurrences),
        "occurrences_by_kind": kinds,
        "criteria": len(onto.criteria),
        "bindings": len(onto.bindings),
        "columns": len(onto.columns),
        "entries": {lay: len(onto.entries[lay]) for lay in ("formula", "parameter", "data")},
        "quantities_by_domain": dict(sorted(domains.items())),
        "entries_by_standard": dict(sorted(stds.items())),
        "open_questions": len(onto.open_questions),
        "symbol_collisions": len(OM.symbol_collisions(onto)),
    }


# --------------------------------------------------------------------------- #
# 文本渲染
# --------------------------------------------------------------------------- #
def r_qid(d: dict, onto: OM.Onto | None = None) -> None:
    if not d["defined"]:
        _out(f"物理量 {d['qid']} 未在词表中定义。")
        return
    _out(f"物理量 {d['qid']}")
    _out(f"  名称       {d['name_zh']}")
    _out(f"  维度/域    {d['dimension']} / {d['domain']}")
    _out(f"  规范单位   {d['canonical_unit']}")
    if d["equivalence_sets"]:
        for s in d["equivalence_sets"]:
            _out(f"  等价集     {s['sid']} [{s['kind']}]  判定：{s.get('verdict') or '-'}")
    _rule("出现位置（occurrence）")
    if not d["occurrences"]:
        _out("  (无)")
    for o in d["occurrences"]:
        _out(
            f"  [{LAYER_LABEL.get(o['layer'], o['layer'])}/{KIND_LABEL.get(o['occurrence_kind'], o['occurrence_kind'])}]"
            f" {o['entry_id']}  {o.get('standard_id') or '-'}"
        )
        _out(f"      条款   {o.get('clause') or '-'}")
        _out(f"      值/式  {o.get('value') or '-'}   判据方向 {o.get('relation') or '-'}")
        if o.get("note"):
            _out(f"      注     {o['note']}")
    _rule("判据（criterion，由 occurrence 派生）")
    if not d["criteria"]:
        _out("  (无 —— 该物理量目前只出现在公式结果或表列里，没有独立的阈值判据)")
    for c in d["criteria"]:
        _out(f"  {c['entry_id']}  {c.get('standard_id') or '-'}  {c.get('clause') or '-'}")
        thr = str(c.get("threshold") or "-")
        rel = str(c.get("relation") or "")
        # canonical 里通常已经带了方向，避免打两遍
        head = thr if thr.startswith(rel) else (f"{rel} {thr}" if rel else thr)
        _out(f"      {head}  [" + str(c.get('unit') or '-') + "]")
    if d["bindings"]:
        _rule("公式变量绑定")
        for b in d["bindings"]:
            qname = onto.qname(b["quantity"]) if onto else b["quantity"]
            _out(f"  {b['formula_id']} : {b['local_symbol']} -> {b['quantity']}  ({qname})")
    if d["columns"]:
        _rule("数据表列")
        for c in d["columns"]:
            _out(f"  {c['entry_id']}.{c['column_key']}  单位 {c.get('unit') or '-'}")


def r_standard(d: dict) -> None:
    _out(f"标准检索：{d['query']}")
    _out(f"  命中标准   {', '.join(d['standards']) or '(无)'}")
    _out(f"  条目 {d['entry_count']} 条，涉及物理量 {d['quantity_count']} 个")
    _rule("条目")
    for r in d["entries"]:
        _out(
            f"  [{LAYER_LABEL.get(r['layer'], r['layer'])}] {r['entry_id']}  {r['title_zh']}"
        )
        _out(f"      标准   {r['standard_id']}  |  {r['clause'] or '-'}")
        _out(f"      物理量 {r['quantity'] or '-'}  {r['quantity_name'] or ''}")
        _out(f"      值     {r['value']}")


def r_domain(d: dict) -> None:
    _out(f"域检索：{d['query']}")
    _out(f"  条目 {d['entry_count']} 条，涉及物理量 {d['quantity_count']} 个")
    _rule("条目")
    for r in d["entries"]:
        _out(f"  [{LAYER_LABEL.get(r['layer'], r['layer'])}] {r['entry_id']}  {r['title_zh']}")
        _out(f"      {r['standard_id']}  |  {r['clause'] or '-'}")
        _out(f"      物理量 {r['quantity'] or '-'} {r['quantity_name'] or ''}   值 {r['value']}")


def r_symbol(d: dict) -> None:
    _out(f"符号检索：{d['query']}")
    if not d["hit_count"]:
        _out("  (无命中)")
        return
    _out(f"  命中 {d['hit_count']} 处，涉及 {len(d['distinct_quantities'])} 个物理量"
         + ("  ← 有歧义，必须靠 qid 消歧" if d["ambiguous"] else ""))
    for h in d["hits"]:
        _out(f"  [{h['namespace']}] {h['symbol']}  ->  {h['quantity']}")
        _out(f"      {h['quantity_name']}   出现于 {h['where']}")


def r_confusable(d: dict) -> None:
    _out(f"易混对清单（共 {d['count']} 组）")
    for s in d["sets"]:
        _rule(s["sid"])
        _out(f"  物理量 {s['quantity']}  ({s['quantity_name']})")
        _out(f"  标准   {', '.join(s.get('standards') or [])}")
        for v in s["values"]:
            _out(
                f"    {v['entry_id']:<12} {v['relation'] or ''} {v['value']}"
                f"  [{v.get('unit') or '-'}]  {v.get('standard_id') or ''}"
            )
            _out(f"        条款 {v.get('clause') or '-'}")
        _out(f"  差异   {s.get('difference') or '-'}")
        _out(f"  风险   {s.get('risk') or '-'}")
        _out(f"  判定   {s.get('verdict') or '-'}")


def r_entry(d: dict) -> None:
    if not d["found"]:
        _out(f"条目 {d['query']} 不存在。")
        return
    _out(f"条目 {d['query']}  [{LAYER_LABEL.get(d['layer'], d['layer'])}]")
    _out(f"  标题     {d['title_zh']}")
    _out(f"  物理量   {d['quantity']}  {d['quantity_name']}")
    _out(f"  投影类型 {d['occurrence_kind']}   role {d['role'] or '-'}")
    _out(f"  标准     {d['standard_id']}  |  {d['clause'] or '-'}")
    _out(f"  值       {d['value']}")
    if d["equivalence_sets"]:
        _out(f"  等价集   {', '.join(d['equivalence_sets'])}")
    _rule("在哪用")
    for w in d["usage_where"]:
        _out(f"  - {w}")
    _rule("怎么用")
    _out(f"  {d['usage_how'] or '-'}")
    if d["related"]:
        _out(f"  关联条目 {', '.join(d['related'])}")


def r_stats(d: dict) -> None:
    _out(f"本体规范版本 {d['spec_version']}")
    _out(f"  物理量 {d['quantities']}  上下文 {d['contexts']}  等价集 {d['equivalence_sets']} {d['sets_by_kind']}")
    _out(f"  occurrence {d['occurrences']} {d['occurrences_by_kind']}")
    _out(f"  criterion {d['criteria']}  变量绑定 {d['bindings']}  表列 {d['columns']}")
    _out(f"  条目 {d['entries']}")
    _out(f"  符号碰撞组 {d['symbol_collisions']}   未决问题 {d['open_questions']}")
    _rule("物理量按域")
    for k, v in d["quantities_by_domain"].items():
        _out(f"  {k:<8} {v}")
    _rule("条目按标准")
    for k, v in d["entries_by_standard"].items():
        _out(f"  {v:>3}  {k}")


def r_collisions(onto: OM.Onto) -> None:
    coll = OM.symbol_collisions(onto)
    _out(f"符号碰撞清单（{len(coll)} 组）—— 同一个字母指向多个物理量")
    for sym, refs in coll.items():
        _out(f"  {sym}  ->  {sorted({r['qid'] for r in refs})}")
        for r in refs:
            _out(f"      [{r['ns']}] {r['where']}  {r['qid']}  ({onto.qname(r['qid'])})")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="standards_kb 本体层查询")
    ap.add_argument("mode", help="qid / standard / domain / symbol / confusable / entry / stats / collisions")
    ap.add_argument("arg", nargs="?", default="", help="查询目标")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--root", default=str(ROOT), help="standards_kb 根目录")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

    onto = OM.load(Path(args.root))
    mode = args.mode.strip()

    if mode == "qid":
        if not args.arg:
            ap.error("qid 模式需要物理量 ID，例如 Q:MAT:CARBON_EQUIVALENT")
        d = q_qid(onto, args.arg.strip())
        if args.json:
            print(json.dumps(d, ensure_ascii=False, indent=2))
        else:
            r_qid(d, onto)
        return 0 if d["defined"] else 2

    if mode == "standard":
        if not args.arg:
            ap.error("standard 模式需要标准名片段")
        d = q_standard(onto, args.arg)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_standard(d)
        return 0

    if mode == "domain":
        if not args.arg:
            ap.error("domain 模式需要域名")
        d = q_domain(onto, args.arg)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_domain(d)
        return 0

    if mode == "symbol":
        if not args.arg:
            ap.error("symbol 模式需要符号")
        d = q_symbol(onto, args.arg)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_symbol(d)
        return 0

    if mode == "confusable":
        d = q_confusable(onto, args.arg.strip() or None)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_confusable(d)
        return 0

    if mode == "entry":
        if not args.arg:
            ap.error("entry 模式需要条目 ID")
        d = q_entry(onto, args.arg.strip())
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_entry(d)
        return 0 if d["found"] else 2

    if mode == "stats":
        d = q_stats(onto)
        print(json.dumps(d, ensure_ascii=False, indent=2)) if args.json else r_stats(d)
        return 0

    if mode == "collisions":
        if args.json:
            coll = OM.symbol_collisions(onto)
            print(json.dumps(coll, ensure_ascii=False, indent=2))
        else:
            r_collisions(onto)
        return 0

    ap.error(f"未知模式：{mode}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
