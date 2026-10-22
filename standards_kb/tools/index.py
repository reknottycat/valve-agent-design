#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / index.py —— 生成使用索引

用户实际会怎么查这套库?
  1. "我要算壁厚,该用哪个公式"      -> 按 solved_for / domain 查
  2. "这条公式什么时候不能用"        -> 查 not_valid_when
  3. "这个数是哪来的"                -> 查 source / evidence
  4. "全库有哪些公式"                -> 总览表

所以索引要按「怎么用」组织,不是按标准号组织。

用法:
  python index.py             # 生成 docs/INDEX.md
  python index.py --by domain # 分域清单
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORM_DIR = ROOT / "kb" / "formulas"
OUT = ROOT / "docs" / "INDEX.md"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DOMAIN_ZH = {
    "FLOW": "流动 / 水力", "STRUCT": "结构 / 承压", "SEAL": "密封",
    "BOLT": "螺栓 / 连接", "MATE": "材料 / 许用值", "TEST": "试验",
    "GEOM": "几何 / 公差", "THERM": "热 / 膨胀", "MASS": "质量 / 惯性",
    "DRIVE": "驱动 / 力矩", "TOL": "公差配合", "PIPE": "管道 / 支吊架",
}

STATUS_ZH = {
    "VERIFIED_CLAUSE": "已核条款", "UNVERIFIED_CLAUSE": "条款未核",
    "PENDING_VERIFICATION": "待核", "CONFLICT": "有冲突",
    "SUPERSEDED": "已被替代",
}


def load() -> list[dict]:
    out = []
    for f in sorted(FORM_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        out.extend(data if isinstance(data, list) else [data])
    return out


def build_index(entries: list[dict]) -> str:
    by_dom: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_dom[e["domain"]].append(e)

    L = []
    L.append("# 标准公式库 —— 使用索引")
    L.append("")
    L.append("> 本文件由 `tools/index.py` 自动生成,请勿手工编辑。")
    L.append("> 公式条目本体在 `kb/formulas/`,标准源登记在 `registry/sources.yaml`。")
    L.append("")

    # 统计
    n_ver = sum(1 for e in entries if e["evidence"]["status"] == "VERIFIED_CLAUSE")
    n_unv = sum(1 for e in entries if e["evidence"]["status"] == "UNVERIFIED_CLAUSE")
    L.append("## 概况")
    L.append("")
    L.append(f"| 项 | 值 |")
    L.append(f"|---|---|")
    L.append(f"| 公式总数 | **{len(entries)}** |")
    L.append(f"| 已核条款 (VERIFIED_CLAUSE) | {n_ver} |")
    L.append(f"| 条款未核 (UNVERIFIED_CLAUSE) | {n_unv} |")
    L.append(f"| 覆盖设计域 | {len(by_dom)} |")
    L.append("")

    # 按域
    L.append("## 按设计域浏览")
    L.append("")
    for dom in sorted(by_dom, key=lambda d: -len(by_dom[d])):
        L.append(f"### {DOMAIN_ZH.get(dom, dom)}  (`{dom}`)  — {len(by_dom[dom])} 条")
        L.append("")
        L.append("| ID | 公式 | 证据 | 状态 | 来源 | 怎么用 |")
        L.append("|---|---|---|---|---|---|")
        for e in sorted(by_dom[dom], key=lambda x: x["id"]):
            ev = e["evidence"]
            use = e["usage"]["how"].replace("|", "/").replace("\n", " ")
            use = use[:70] + ("…" if len(use) > 70 else "")
            L.append(
                f"| `{e['id']}` | {e['title_zh']} | {ev['grade']} | "
                f"{STATUS_ZH.get(ev['status'], ev['status'])} | "
                f"{e['source']['standard_id']} {e['source'].get('clause','')} | {use} |"
            )
        L.append("")

    # 按「我要算什么」反查
    L.append("## 按目标量反查（我要算 X → 用哪条）")
    L.append("")
    L.append("| 目标量 | 公式 ID | 名称 | 适用前提 |")
    L.append("|---|---|---|---|")
    for e in sorted(entries, key=lambda x: x["id"]):
        solved = e["expression"].get("solved_for")
        if not solved:
            continue
        pre = e["applicability"]["valid_when"][0]
        L.append(f"| `{solved}` | `{e['id']}` | {e['title_zh']} | {pre[:46]} |")
    L.append("")

    # 警示清单
    L.append("## 使用警示（最容易踩的坑）")
    L.append("")
    L.append("| ID | 不可用条件 | 常见误用 |")
    L.append("|---|---|---|")
    for e in sorted(entries, key=lambda x: x["id"]):
        pit = e["usage"].get("pitfalls") or []
        if not pit and not e["applicability"].get("not_valid_when"):
            continue
        nv = "; ".join(e["applicability"].get("not_valid_when", []))[:52]
        p = "; ".join(pit)[:52]
        L.append(f"| `{e['id']}` | {nv} | {p} |")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**纪律提醒**：本库只提供公式与其适用边界。")
    L.append("`UNVERIFIED_CLAUSE` 表示尚未拿到标准正文核对,不得直接作为条款级依据。")
    L.append("任何据此做出的设计结论,仍受项目 `E0-E3` 证据等级约束。")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--by", choices=["domain", "status"], default="domain")
    args = ap.parse_args()

    entries = load()
    if not entries:
        print("没有公式条目")
        return 0

    if args.by == "domain":
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(build_index(entries), encoding="utf-8")
        print(f"索引已生成 -> {OUT.relative_to(ROOT)}  ({len(entries)} 条)")
    else:
        by: dict[str, int] = defaultdict(int)
        for e in entries:
            by[e["evidence"]["status"]] += 1
        for k, v in sorted(by.items()):
            print(f"{STATUS_ZH.get(k,k):<12} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
