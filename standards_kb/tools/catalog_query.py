#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""standards_kb / catalog_query.py —— 查目录,不做任何抓取。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "kb" / "catalog" / "law_resource_ibr.json"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    pats = sys.argv[1:]
    d = json.loads(CAT.read_text(encoding="utf-8"))
    ents = d["entries"]
    if not pats:
        print(f"共 {len(ents)} 条")
        for e in ents:
            print(f"  {e['file']:<36}{e['size_text']:>8}  {e['title'][:64]}")
        return 0
    for p in pats:
        pl = p.lower()
        hits = [e for e in ents if pl in e["file"].lower() or pl in e["title"].lower()]
        print(f"--- '{p}' -> {len(hits)} 条")
        for e in hits:
            print(f"  {e['file']:<34}{e['size_text']:>8}  {e['kind_guess']:<10}{e['title'][:58]}")
            print(f"       {e['local_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
