#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / build_docs.py —— 生成标准覆盖表与数据索引

产出
----
  docs/STANDARD_COVERAGE.md —— 每个已登记标准：拿到什么、公式密度多少、产出什么
  docs/DATA_INDEX.md        —— 数据表条目索引（怎么查尺寸/公差/材料）

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
    out = []
    for f in sorted((KB / "formulas").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.extend(d if isinstance(d, list) else [d])
    return out


def load_data_entries() -> list[dict]:
    out = []
    for f in sorted((KB / "data").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("entries"), list):
            out.extend(d["entries"])
    return out


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


def build_coverage() -> str:
    reg = load_json(ROOT / "registry" / "registry.json") or {}
    formulas = load_formulas()
    data_entries = load_data_entries()
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
    L.append("| 家族 | 登记源数 | 已持有正文 | 正式公式条目 | 候选池 | 数据表条目 |")
    L.append("|---|---|---|---|---|---|")
    fam_rows = []
    for fam, fdata in (reg.get("families") or {}).items():
        srcs = fdata.get("sources", [])
        n_body = sum(1 for s in srcs if s.get("body_status") in
                     ("FULL_TEXT_MIRROR", "LOCAL_FILE"))
        fam_formulas = [f for f in formulas
                        if family_of(f["source"].get("standard_id", "")) == fam]
        fam_data = [d for d in data_entries
                    if family_of(d.get("standard_id", "")) == fam]
        fam_cand = sum(n for s, n in cand_by_std.items()
                       if family_of(s) == fam)
        fam_rows.append((fam, fdata.get("label", ""), len(srcs), n_body,
                         len(fam_formulas), fam_cand, len(fam_data)))

    # 归不到任何已登记家族的内容(通用工程力学、通用机械设计等)不能悄悄消失,
    # 单列一行;再给合计行,让读者能自己复算总数。
    reg_fams = set(reg.get("families") or {})
    other_f = [f for f in formulas
               if family_of(f["source"].get("standard_id", "")) not in reg_fams]
    other_d = [d for d in data_entries
               if family_of(d.get("standard_id", "")) not in reg_fams]
    other_c = sum(n for s, n in cand_by_std.items()
                  if family_of(s) not in reg_fams)

    for fam, label, ns, nb, nf, nc, nd in fam_rows:
        L.append(f"| {fam} | {ns} | {nb} | {nf} | {nc} | {nd} |")
    if other_f or other_d or other_c:
        L.append(f"| 其他/通用 | — | — | {len(other_f)} | {other_c} | {len(other_d)} |")
    tot_f = sum(r[4] for r in fam_rows) + len(other_f)
    tot_c = sum(r[5] for r in fam_rows) + other_c
    tot_d = sum(r[6] for r in fam_rows) + len(other_d)
    L.append(f"| **合计** | {sum(r[2] for r in fam_rows)} | "
             f"{sum(r[3] for r in fam_rows)} | **{tot_f}** | **{tot_c}** | **{tot_d}** |")
    L.append("")
    L.append("> 「其他/通用」= 公式或数据来自通用工程知识，"
             "不属于 GB/ASME/ГОСТ/ISO 任一已登记家族，单独列出不混进家族数。")
    L.append("")

    # 逐源明细
    L.append("## 逐源明细")
    L.append("")
    L.append("| 源 ID | 家族 | 类型 | 正文状态 | 抽取方式 | 正式公式 | 数据表 | 候选 | 备注 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
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
            note = (s.get("notes") or "").split("\n")[0][:56]
            L.append(
                f"| `{sid}` | {fam} | {s.get('kind','')} | "
                f"{s.get('body_status','')} | {s.get('extraction','')} | "
                f"{nf} | {nd} | {nc} | {note} |")
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


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "STANDARD_COVERAGE.md").write_text(build_coverage(), encoding="utf-8")
    (DOCS / "DATA_INDEX.md").write_text(build_data_index(), encoding="utf-8")
    print(f"已生成 -> {DOCS.relative_to(ROOT)}/STANDARD_COVERAGE.md")
    print(f"已生成 -> {DOCS.relative_to(ROOT)}/DATA_INDEX.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
