#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 docs/ONTOLOGY_INDEX.md —— 本体层索引。

与 docs/INDEX.md（公式索引）、docs/DATA_INDEX.md（数据表索引）、
docs/PARAMETER_INDEX.md（参数索引）并列，是第四篇索引文档。

本体索引回答的不是"有哪些条目"，而是：
  - 同一个物理量在不同标准下取值是否一致（跨标准对齐）
  - 哪些符号在不同地方指不同的东西（消歧）
  - 哪些判据看着像但不能互换（易混对）

只读工具：只读 kb/ontology/ 与条目层，不修改任何文件。
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onto_model as OM  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CST = timezone(timedelta(hours=8))

LAYER_LABEL = {"formula": "公式", "parameter": "参数", "data": "数据表"}
KIND_LABEL = {"VALUE": "取值", "RESULT": "结果", "NONE": "仅表列"}


def _esc(s) -> str:
    """表格单元格转义：竖线与换行会破坏 Markdown 表格。"""
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def _value_of(entry: dict) -> str:
    v = entry.get("value") or {}
    if isinstance(v, dict) and v.get("canonical"):
        return str(v["canonical"])
    expr = entry.get("expression") or {}
    if isinstance(expr, dict) and expr.get("canonical"):
        return str(expr["canonical"])
    if entry.get("table_ref"):
        return str(entry["table_ref"])
    return "-"


def build(root: Path | None = None) -> str:
    onto = OM.load(root or ROOT)
    L: list[str] = []

    # ------------------------------------------------------------------ 概况
    kinds: dict[str, int] = defaultdict(int)
    for o in onto.occurrences.values():
        kinds[str(o.get("occurrence_kind"))] += 1
    sets_by_kind: dict[str, int] = defaultdict(int)
    for s in onto.sets:
        sets_by_kind[str(s.get("kind"))] += 1
    dom_count: dict[str, int] = defaultdict(int)
    for q in onto.quantities.values():
        dom_count[str(q.get("domain"))] += 1

    # 每个 qid 出现在哪些标准
    q_stds: dict[str, set[str]] = defaultdict(set)
    q_occ: dict[str, list[dict]] = defaultdict(list)
    for o in onto.occurrences.values():
        qid = o.get("quantity")
        if not qid:
            continue
        q_stds[qid].add(str(o.get("standard_id") or "(未标注)"))
        q_occ[qid].append(o)

    multi_std = {q: s for q, s in q_stds.items() if len(s) >= 2}

    L.append("# 本体索引")
    L.append("")
    L.append("> 本文件由 `tools/build_ontology_index.py` 自动生成，请勿手工编辑。")
    L.append("> 本体层本体在 `kb/ontology/`，规范版本 "
             f"`{(onto.spec.get('meta') or {}).get('version')}`。")
    L.append("")

    L.append("## 概况")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 物理量 Quantity | **{len(onto.quantities)}** |")
    L.append(f"| 上下文 Context | {len(onto.contexts)} |")
    L.append(f"| 等价集 EquivalenceSet | {len(onto.sets)} |")
    for k in sorted(sets_by_kind):
        L.append(f"| └ `{k}` | {sets_by_kind[k]} |")
    L.append(f"| 出现 Occurrence | **{len(onto.occurrences)}** |")
    for k in sorted(kinds):
        L.append(f"| └ `{k}` | {kinds[k]} |")
    L.append(f"| 判据 Criterion（派生） | {len(onto.criteria)} |")
    L.append(f"| 变量绑定 VariableBinding | {len(onto.bindings)} |")
    L.append(f"| 表列投影 TableColumn | {len(onto.columns)} |")
    L.append(f"| 跨标准物理量 | **{len(multi_std)}** |")
    L.append(f"| 符号碰撞组 | {len(OM.symbol_collisions(onto))} |")
    L.append(f"| 未决问题登记 | {len(onto.open_questions)} |")
    L.append("")

    L.append("## 跨标准对齐对照")
    L.append("")
    L.append("同一个物理量在多个标准下出现时的取值对照。这是本体层最核心的一张表 ——")
    L.append("公式层和参数层各自都能查到数，但只有把两边落到同一个 qid 上，")
    L.append("才能一眼看出「这个数在两个标准里不一样」。")
    L.append("")
    if not multi_std:
        L.append("（暂无跨标准物理量）")
        L.append("")
    else:
        L.append("| 物理量 | 名称 | 标准数 | 各标准取值 | 判定 |")
        L.append("|---|---|---|---|---|")
        for qid in sorted(multi_std, key=lambda q: (-len(multi_std[q]), q)):
            q = onto.quantities.get(qid) or {}
            cells = []
            verdicts = []
            for o in sorted(q_occ[qid], key=lambda o: (str(o.get("standard_id")), str(o.get("entry_id")))):
                e = onto.entry_of(o.get("entry_id")) or {}
                v = _value_of(e)
                rel = o.get("relation")
                if rel and not str(v).startswith(str(rel)):
                    v = f"{rel} {v}"
                std = str(o.get("standard_id") or "?")
                cells.append(f"{std}: `{o.get('entry_id')}` {v}")
            for s in onto.sets:
                if s.get("quantity") == qid and s.get("kind") == "CONFUSABLE":
                    verdicts.append(f"`{s.get('sid')}` {s.get('verdict') or ''}".strip())
            L.append(
                f"| `{qid}` | {_esc(q.get('name_zh'))} | {len(multi_std[qid])} | "
                f"{'<br>'.join(cells)} | {'<br>'.join(verdicts) or '—'} |"
            )
        L.append("")

    # ------------------------------------------------------------ 物理量清单
    L.append("## 物理量清单")
    L.append("")
    L.append("按域分组。`条目数` 指该物理量在三层里出现的次数"
             "（公式结果 / 参数取值 / 表列投影各算一次）。")
    L.append("")
    L.append("| 域 | 物理量数 |")
    L.append("|---|---|")
    for k in sorted(dom_count):
        L.append(f"| `{k}` | {dom_count[k]} |")
    L.append("")
    for dom in sorted(dom_count):
        rows = []
        for qid, q in onto.quantities.items():
            if str(q.get("domain")) != dom:
                continue
            occs = q_occ.get(qid) or []
            stds = sorted({str(o.get("standard_id") or "?") for o in occs})
            syms = q.get("symbol_candidates") or []
            rows.append(
                f"| `{qid}` | {_esc(q.get('name_zh'))} | "
                f"{_esc(q.get('dimension'))} | {_esc(q.get('canonical_unit'))} | "
                f"{' '.join(f'`{s}`' for s in syms) or '—'} | {len(occs)} | "
                f"{'<br>'.join(stds) or '—'} |"
            )
        if not rows:
            continue
        L.append(f"### 域 `{dom}`（{len(rows)} 个）")
        L.append("")
        L.append("| qid | 名称 | 量纲 | 规范单位 | 符号候选 | 条目数 | 涉及标准 |")
        L.append("|---|---|---|---|---|---|---|")
        L.extend(rows)
        L.append("")

    # ---------------------------------------------------------- 符号碰撞
    coll = OM.symbol_collisions(onto)
    L.append("## 符号碰撞与消歧")
    L.append("")
    if not coll:
        L.append("（无）")
        L.append("")
    else:
        L.append(f"同一个字母在库里指向 {len(coll)} 组不同物理量。"
                 "**这是读公式时最容易出错的地方** —— "
                 "只看字母不看 qid，就会在两个标准之间串味。")
        L.append("")
        L.append("| 符号 | 物理量 | 出现位置 |")
        L.append("|---|---|---|")
        for sym, refs in coll.items():
            for r in refs:
                L.append(
                    f"| `{sym}` | `{r['qid']}`<br>{_esc(onto.qname(r['qid']))} | "
                    f"[{r['ns']}] {_esc(r['where'])} |"
                )
        L.append("")

    # ------------------------------------------------------------ 易混对
    L.append("## 易混对清单")
    L.append("")
    L.append("跨标准同判据不同取值，必须一起看。`verdict` 是本库给出的判定结论。")
    L.append("")
    L.append("| 等价集 | 物理量 | 各标准取值 | 差异 | 判定 |")
    L.append("|---|---|---|---|---|")
    for s in onto.sets_of_kind("CONFUSABLE"):
        vals = []
        for v in s.get("values") or []:
            e = onto.entry_of(v.get("entry_id")) or {}
            std = OM.entry_standard(e) or "?"
            vals.append(f"{std}: `{v.get('entry_id')}` {v.get('relation') or ''} {v.get('value')}")
        L.append(
            f"| `{s.get('sid')}` | `{s.get('quantity')}`<br>{_esc(onto.qname(str(s.get('quantity'))))} | "
            f"{'<br>'.join(vals)} | {_esc(s.get('difference'))} | {_esc(s.get('verdict'))} |"
        )
    L.append("")

    # --------------------------------------------------------- 其他等价集
    L.append("## 其他等价集")
    L.append("")
    L.append("### 单位换算（UNIT_CONVERSION）")
    L.append("")
    L.append("| 等价集 | US 侧 | SI 侧 | 表达式比值 |")
    L.append("|---|---|---|---|")
    for s in onto.sets_of_kind("UNIT_CONVERSION"):
        L.append(
            f"| `{s.get('sid')}` | `{s.get('us_member')}` | `{s.get('si_member')}` | "
            f"`{s.get('expression_ratio')}` |"
        )
    L.append("")
    L.append("### 列对应（COLUMN_CORRESPONDENCE）")
    L.append("")
    L.append("| 等价集 | 物理量 | 对应列 |")
    L.append("|---|---|---|")
    for s in onto.sets_of_kind("COLUMN_CORRESPONDENCE"):
        L.append(
            f"| `{s.get('sid')}` | `{s.get('quantity')}` | "
            f"{'<br>'.join(f'`{m}`' for m in (s.get('members') or []))} |"
        )
    L.append("")

    # ------------------------------------------------------------ 上下文
    L.append("## 上下文清单")
    L.append("")
    L.append("| xid | 类别 | 名称 |")
    L.append("|---|---|---|")
    for xid, c in onto.contexts.items():
        L.append(f"| `{xid}` | `{c.get('kind')}` | {_esc(c.get('name_zh'))} |")
    L.append("")

    # ------------------------------------------------------------ 未决问题
    L.append("## 未决问题登记")
    L.append("")
    L.append("本体不产生新事实。**疑似同族但无法确认的物理量不合并**，"
             "而是登记在这里，等证据到位再定案。")
    L.append("")
    if not onto.open_questions:
        L.append("（无）")
        L.append("")
    else:
        for oq in onto.open_questions:
            L.append(f"### {oq.get('id')} —— {oq.get('title')}")
            L.append("")
            L.append(f"- 涉及物理量：{', '.join(f'`{q}`' for q in (oq.get('quantities') or []))}")
            L.append(f"- 问题：{str(oq.get('question') or '').strip()}")
            L.append(f"- 未合并原因：{str(oq.get('not_merged_because') or '').strip()}")
            L.append(f"- 解决路径：{str(oq.get('resolution_hint') or '').strip()}")
            L.append("")

    # ------------------------------------------------------------ 使用提醒
    L.append("---")
    L.append("")
    L.append("**使用提醒**：")
    L.append("")
    L.append("1. 本体层**不产生新事实**。所有数值、条款、判定方向都来自条目层；"
             "本体只声明「这些条目说的是不是同一个东西」。")
    L.append("2. 查数请以条目层为准，本体索引只做**定位与对照**。"
             "数值是否可信看条目的 `evidence.status`。")
    L.append("3. 读公式时不要只看字母。符号碰撞是实测出来的（见上表），"
             "必须经 qid 确认物理量。")
    L.append("4. `verdict: 不可互换` 的易混对，套错标准即误判，"
             "引用时必须带标准号。")
    L.append("5. 交互式查询：`python tools/ontology_query.py qid <QID>`、"
             "`symbol <SYM>`、`confusable`、`standard <名>`。")
    L.append("")
    L.append(f"生成时间：{datetime.now(CST).isoformat(timespec='seconds')}")
    return "\n".join(L)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "ONTOLOGY_INDEX.md"
    out.write_text(build(), encoding="utf-8")
    print(f"已生成 -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
