#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""standards_kb / param_query.py —— 查参数条目(不联网)。

参数层是"标准里不需要再推导、只需要查"的东西:常数、系数、限值、阈值、
缺省替代值、单位换算因子、材料性能值。尺寸表/公差表/压力等级表在数据表层,
用 tools/data_query.py。

用法:
  python tools/param_query.py                         # 概览:按标准/域/种类统计
  python tools/param_query.py --id P-TEST-002         # 看单条完整内容
  python tools/param_query.py --kw 5.092              # 关键字搜(标题/别名/取值/单位/标签/原文)
  python tools/param_query.py --std ASME-BPVC-I      # 按标准
  python tools/param_query.py --domain TEST           # 按设计域
  python tools/param_query.py --kind CONSTANT         # 按参数种类
  python tools/param_query.py --status VERIFIED_CLAUSE
  python tools/param_query.py --grade E1
  python tools/param_query.py --graph P-TEST-002      # 跨层关系图(参数 <-> 公式)
  python tools/param_query.py --kw CE --json          # 机器可读输出

说明:
  --std 收短 id(ASME-BPVC-I / ASME-B31.1),内部走 tools/standard_ids.py 归一,
  与 registry 的 standard_id 对齐;也接受标准全名。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_entries as K  # noqa: E402
import standard_ids  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _short_std(entry: dict) -> str:
    return standard_ids.std_of((entry.get("source") or {}).get("standard_id") or "")


def _haystack(e: dict) -> str:
    """一条参数的全部可检索文本。"""
    v = e.get("value") or {}
    parts = [
        str(e.get("id") or ""),
        str(e.get("title_zh") or ""),
        str(e.get("title_en") or ""),
        str(e.get("unit") or ""),
        str(e.get("domain") or ""),
        str(e.get("param_kind") or ""),
        str(v.get("canonical") or ""),
        str(v.get("display") or ""),
        str(v.get("unit_text") or ""),
        str(e.get("symbol") or ""),
    ]
    parts += [str(x) for x in (e.get("aliases") or [])]
    parts += [str(x) for x in (e.get("tags") or [])]
    parts += [str(x) for x in ((e.get("source") or {}).get("cross_refs") or [])]
    parts += [str(x) for x in (e.get("related") or [])]
    parts.append(str((e.get("source") or {}).get("clause") or ""))
    parts.append(str((e.get("source") or {}).get("snippet") or ""))
    return "\n".join(parts)


def _row(e: dict) -> str:
    v = e.get("value") or {}
    src = e.get("source") or {}
    ev = e.get("evidence") or {}
    rel = v.get("relation") or ""
    val = v.get("display") or v.get("canonical") or ""
    if rel and rel != "=":
        val = f"{rel} {val}"
    vv = "V" if src.get("visual_verified") is True else " "
    return (f"{e.get('id',''):<13} {e.get('param_kind',''):<19} "
            f"{e.get('domain',''):<7} {ev.get('grade','')} "
            f"{ev.get('status',''):<21} {vv} "
            f"{_short_std(e):<14} {val:<26} {e.get('title_zh','')[:36]}")


HEADER = (f"{'ID':<13} {'KIND':<19} {'DOM':<7} {'G':<2} {'STATUS':<21} "
          f"{'V':<1} {'STANDARD':<14} {'VALUE':<26} TITLE")


def print_detail(e: dict, all_by_id: dict) -> None:
    v = e.get("value") or {}
    src = e.get("source") or {}
    ev = e.get("evidence") or {}
    ap = e.get("applicability") or {}
    us = e.get("usage") or {}

    print("=" * 78)
    print(f"{e.get('id')}  {e.get('title_zh')}")
    if e.get("title_en"):
        print(f"  EN      : {e['title_en']}")
    print(f"  种类    : {e.get('param_kind')}   域: {e.get('domain')}   符号: {e.get('symbol') or '-'}")
    print(f"  取值    : {v.get('canonical')}" + (f"   ({v.get('display')})" if v.get("display") else ""))
    if v.get("relation"):
        print(f"  判据关系: {v['relation']}   数值: {v.get('numeric')}"
              + (f"   区间: [{v.get('min')}, {v.get('max')}]" if v.get("min") is not None else ""))
    print(f"  单位    : {e.get('unit')}" + (f"   原文单位串: {v.get('unit_text')}" if v.get("unit_text") else ""))
    for a in (v.get("alt_values") or []):
        print(f"  其它制值: {a.get('canonical')} ({a.get('display')}) {a.get('unit_text') or ''}")
        if a.get("note"):
            print(f"            {a['note']}")
    if e.get("aliases"):
        print(f"  别名    : {' / '.join(e['aliases'])}")
    if e.get("tags"):
        print(f"  标签    : {' / '.join(e['tags'])}")

    print(f"\n  ── 出处 ──")
    print(f"  标准    : {src.get('standard_id')}  ({_short_std(e)})")
    print(f"  条款    : {src.get('clause')}")
    print(f"  正文状态: {src.get('body_status')}   视觉核验: {src.get('visual_verified')}")
    print(f"  定位    : {src.get('locator')}")
    if src.get("snippet"):
        print(f"  原文    : {src['snippet']}")
    if src.get("extraction_note"):
        print(f"  抽取说明: {src['extraction_note'][:400]}")

    print(f"\n  ── 证据 ──")
    print(f"  等级    : {ev.get('grade')}   状态: {ev.get('status')}")
    if ev.get("verified_on"):
        print(f"  核验日  : {ev['verified_on']}   {ev.get('verified_by') or ''}")
    if ev.get("note"):
        print(f"  备注    : {ev['note']}")

    print(f"\n  ── 适用范围 ──")
    for x in (ap.get("valid_when") or []):
        print(f"  [可用]  {x}")
    for x in (ap.get("not_valid_when") or []):
        print(f"  [禁用]  {x}")
    for x in (ap.get("range_limits") or []):
        print(f"  [范围]  {x}")
    if ap.get("conservatism"):
        print(f"  [保守性] {ap['conservatism']}")
    for x in (ap.get("must_pair_with") or []):
        print(f"  [须并用] {x}")

    print(f"\n  ── 怎么用 ──")
    for x in (us.get("where") or []):
        print(f"  场景    : {x}")
    print(f"  做法    : {us.get('how')}")
    for x in (us.get("step_order") or []):
        print(f"    {x}")
    for x in (us.get("output_used_by") or []):
        print(f"  被消费于: {x}")
    for x in (us.get("pitfalls") or []):
        print(f"  [坑]    {x}")

    for x in (e.get("project_usage") or []):
        print(f"\n  ── 本项目 ── {x.get('task')} / {x.get('status')}")
        if x.get("note"):
            print(f"  {x['note']}")

    refs = (e.get("related") or []) + (src.get("cross_refs") or [])
    if refs:
        print(f"\n  ── 关联 ──")
        for r in dict.fromkeys(refs):
            other = all_by_id.get(r)
            if other:
                lay = K.id_layer(r)
                print(f"  {r:<13} [{lay:<7}] {other.get('title_zh','')}")
            else:
                print(f"  {r:<13} [缺失] !! 引用了不存在的 ID")


def print_graph(eid: str, all_by_id: dict) -> int:
    """跨层关系图:参数 <-> 公式。"""
    e = all_by_id.get(eid)
    if not e:
        print(f"找不到 {eid}")
        return 1
    src = e.get("source") or {}
    refs = list(dict.fromkeys((e.get("related") or []) + (src.get("cross_refs") or [])))
    print(f"{eid}  {e.get('title_zh')}")
    print(f"  来自: {(src.get('standard_id') or '')} {src.get('clause') or ''}")
    if not refs:
        print("  (无关联条目)")
        return 0
    print(f"  关联 {len(refs)} 条:")
    for r in refs:
        other = all_by_id.get(r)
        lay = K.id_layer(r)
        if other:
            print(f"    [{lay:<7}] {r:<13} {other.get('title_zh','')}")
        else:
            print(f"    [{lay:<7}] {r:<13} !! 引用了不存在的 ID")
    return 0


def print_overview(entries: list[dict]) -> None:
    print(f"参数条目共 {len(entries)} 条\n")

    by_std: dict[str, int] = {}
    by_dom: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    vv_true = 0
    for e in entries:
        by_std[_short_std(e)] = by_std.get(_short_std(e), 0) + 1
        d = e.get("domain", "?")
        by_dom[d] = by_dom.get(d, 0) + 1
        k = e.get("param_kind", "?")
        by_kind[k] = by_kind.get(k, 0) + 1
        st = (e.get("evidence") or {}).get("status", "?")
        by_status[st] = by_status.get(st, 0) + 1
        if (e.get("source") or {}).get("visual_verified") is True:
            vv_true += 1

    for title, d in (("按标准", by_std), ("按设计域", by_dom),
                     ("按参数种类", by_kind), ("按证据状态", by_status)):
        print(f"  {title}:")
        for k in sorted(d, key=lambda x: (-d[x], x)):
            print(f"    {k:<24} {d[k]:>3}")
        print()
    print(f"  已做视觉核验(纯扫描位图逐字核过): {vv_true}/{len(entries)}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description="参数条目查询")
    ap.add_argument("--id", help="按 ID 精确查")
    ap.add_argument("--kw", help="关键字(标题/别名/取值/单位/标签/原文)")
    ap.add_argument("--std", help="按标准(短 id 或全名)")
    ap.add_argument("--domain", help="按设计域")
    ap.add_argument("--kind", help="按参数种类")
    ap.add_argument("--status", help="按证据状态")
    ap.add_argument("--grade", help="按证据等级")
    ap.add_argument("--graph", help="显示某条目的跨层关系图")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    entries = K.param_entries()
    if not entries:
        print("kb/parameters/ 下没有条目")
        return 0

    all_by_id: dict[str, dict] = {}
    for e in K.formula_entries() + entries:
        if e.get("id"):
            all_by_id[e["id"]] = e

    if args.graph:
        return print_graph(args.graph, all_by_id)

    sel = entries
    filtered = False
    if args.id:
        sel = [e for e in sel if e.get("id") == args.id]
        filtered = True
    if args.kw:
        kw = args.kw.lower()
        sel = [e for e in sel if kw in _haystack(e).lower()]
        filtered = True
    if args.std:
        want = standard_ids.std_of(args.std)
        sel = [e for e in sel if _short_std(e) == want]
        filtered = True
    if args.domain:
        sel = [e for e in sel if e.get("domain") == args.domain]
        filtered = True
    if args.kind:
        sel = [e for e in sel if e.get("param_kind") == args.kind]
        filtered = True
    if args.status:
        sel = [e for e in sel if (e.get("evidence") or {}).get("status") == args.status]
        filtered = True
    if args.grade:
        sel = [e for e in sel if (e.get("evidence") or {}).get("grade") == args.grade]
        filtered = True

    # 不带任何过滤条件时出概览,而不是把 57 条全刷出来
    if not filtered and not args.json:
        print_overview(entries)
        return 0

    if args.json:
        print(json.dumps(sel, ensure_ascii=False, indent=2))
        return 0

    if args.id:
        if not sel:
            print(f"找不到 {args.id}")
            return 1
        for e in sel:
            print_detail(e, all_by_id)
        return 0

    if not sel:
        print("没有命中任何参数条目")
        return 0

    print(HEADER)
    print("-" * 150)
    for e in sel:
        print(_row(e))
    print(f"\n共 {len(sel)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
