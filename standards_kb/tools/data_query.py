#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""standards_kb / data_query.py —— 查结构化数据表(不联网)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python data_query.py <raw_tables.json> [Dn值] [表号]")
        return 1
    p = Path(sys.argv[1])
    d = json.loads(p.read_text(encoding="utf-8"))
    want_dn = sys.argv[2] if len(sys.argv) > 2 else None
    want_tbl = sys.argv[3] if len(sys.argv) > 3 else None

    for t in d["tables"]:
        if want_tbl and str(t["index"]) != want_tbl:
            continue
        print(f"=== 表 {t['index']}  ({len(t['data_rows'])} 行)")
        ctx = t["context"]
        # 找压力等级描述
        import re
        m = re.findall(r"Для Р[^\n]{0,120}", ctx)
        for s in m[:2]:
            print("   范围:", s.strip()[:110])
        for hr in t["header_rows"]:
            print("   表头:", " | ".join(x for x in hr if x))
        for r in t["data_rows"]:
            if want_dn and r[0].strip() != want_dn:
                continue
            print("   行:", " | ".join(r))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
