#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对 GB/T 15530.1-2008 数据条目: schema 合法性 + 关键行数值 + 跨表引用完整性。

用法: python tools/check_gb_15530.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = ROOT / "kb" / "data" / "GB_T_15530.1-2008.json"
SCHEMA = ROOT / "kb" / "data.schema.json"

# 原文核对基准(2026-10-22 两轮独立视觉读数,逐格对照官方在线阅读页图像)
EXPECT = {
    "D-GBT15530-PN6-RF": {
        200: dict(D=320, K=280, L=18, n=8, bolt_thread="M16", d=258, f=3, C=22, N=234, R=6),
    },
    "D-GBT15530-PN10-RF": {
        200: dict(D=340, K=295, L=22, n=8, bolt_thread="M20", d=268, f=3, C=26, N=240, R=8),
    },
    "D-GBT15530-PN16-RF": {
        200: dict(D=340, K=295, L=22, n=12, bolt_thread="M20", d=268, f=3, C=26, N=240, R=8),
    },
    "D-GBT15530-PN25-RF": {
        200: dict(D=360, K=310, L=26, n=12, bolt_thread="M24", d=278, f=3, C=30, N=246, R=8),
    },
}

# 跨表引用必须成对: 引用方声明 ref_table,被引用方必须真的存在
REF_TARGETS = {
    "D-GBT15530-PN10-RF": {"表 6", "表 5"},
    "D-GBT15530-PN16-RF": {"表 6"},
}

errors: list[str] = []
notes: list[str] = []


def check(cond: bool, msg: str) -> None:
    (notes if cond else errors).append(("OK   " if cond else "FAIL ") + msg)


def main() -> int:
    if not DATA.exists():
        print(f"数据文件不存在: {DATA}")
        return 1
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    entries = {e["id"]: e for e in doc["entries"]}
    check(len(entries) == len(doc["entries"]), f"条目 ID 无重复 ({len(entries)} 条)")
    check(doc.get("count") == len(doc["entries"]), "count 与 entries 长度一致")
    check(doc.get("standard_id") == "GB/T 15530.1-2008", "standard_id 正确")

    req = schema["required"]
    body_status_enum = set(schema["properties"]["body_status"]["enum"])
    kind_enum = set(schema["properties"]["table_kind"]["enum"])
    domain_enum = set(schema["properties"]["design_domain"]["enum"])
    status_enum = set(schema["properties"]["evidence"]["properties"]["status"]["enum"])
    grade_enum = set(schema["properties"]["evidence"]["properties"]["grade"]["enum"])

    for eid, e in entries.items():
        for k in req:
            if k not in e:
                errors.append(f"FAIL {eid}: 缺必填字段 {k}")
        if e.get("body_status") not in body_status_enum:
            errors.append(f"FAIL {eid}: body_status 非法 {e.get('body_status')}")
        if e.get("table_kind") not in kind_enum:
            errors.append(f"FAIL {eid}: table_kind 非法 {e.get('table_kind')}")
        if e.get("design_domain") not in domain_enum:
            errors.append(f"FAIL {eid}: design_domain 非法 {e.get('design_domain')}")
        ev = e.get("evidence", {})
        if ev.get("grade") not in grade_enum:
            errors.append(f"FAIL {eid}: evidence.grade 非法 {ev.get('grade')}")
        if ev.get("status") not in status_enum:
            errors.append(f"FAIL {eid}: evidence.status 非法 {ev.get('status')}")
        ncol = len(e["columns"])
        for i, r in enumerate(e["rows"]):
            if len(r) != ncol:
                errors.append(f"FAIL {eid}: 第 {i} 行列数 {len(r)} != columns {ncol}")
        # 行定位键必须覆盖全部行
        if len(e.get("row_keys", {})) != len(e["rows"]):
            errors.append(f"FAIL {eid}: row_keys 数量 {len(e.get('row_keys', {}))} != rows {len(e['rows'])}")
        u = e.get("usage", {})
        if not u.get("where") or not u.get("how"):
            errors.append(f"FAIL {eid}: usage.where/how 为空")
        if "locator" not in e.get("source", {}):
            errors.append(f"FAIL {eid}: source.locator 缺失")

    # 关键行数值核对
    for eid, rows in EXPECT.items():
        e = entries.get(eid)
        if not e:
            errors.append(f"FAIL 缺条目 {eid}")
            continue
        for dn, want in rows.items():
            got = e["row_keys"].get(str(dn))
            if not got:
                errors.append(f"FAIL {eid}: 缺 DN{dn} 行")
                continue
            for k, v in want.items():
                if got.get(k) != v:
                    errors.append(f"FAIL {eid} DN{dn}.{k}: 期望 {v!r}, 实得 {got.get(k)!r}")
                else:
                    notes.append(f"OK   {eid} DN{dn}.{k} = {v!r}")

    # 跨表引用: 引用方要标 ref_table,被引用的条目要存在
    clause_of = {eid: e.get("clause") for eid, e in entries.items()}
    for eid, targets in REF_TARGETS.items():
        e = entries.get(eid)
        if not e:
            continue
        refs = {k.get("ref_table") for k in e["row_keys"].values() if k.get("ref_table")}
        for t in targets:
            if t not in refs:
                errors.append(f"FAIL {eid}: 未标注引用 {t}")
            elif t not in clause_of.values():
                errors.append(f"FAIL {eid}: 引用的 {t} 在本文件中不存在")
            else:
                notes.append(f"OK   {eid} 引用 {t} 存在")
        # 被引用的行数值列必须为 null(不能是 0)
        for k, v in e["row_keys"].items():
            if v.get("ref_table"):
                leaked = [c["key"] for c in e["columns"]
                          if c["key"] not in ("Dn", "type", "pn")
                          and v.get(c["key"]) is not None]
                if leaked:
                    errors.append(f"FAIL {eid} DN{k}: 跨表引用行却有数值 {leaked}")
                else:
                    notes.append(f"OK   {eid} DN{k} 为纯引用行(数值列为空)")

    print(f"检查项 {len(notes) + len(errors)}  通过 {len(notes)}  失败 {len(errors)}")
    for m in errors:
        print("  " + m)
    if errors:
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
