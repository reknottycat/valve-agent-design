#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gb_body_query.py —— 查询 GB/T 正文的**免费可得性**台账。

为什么需要
----------
「标准在目录里」和「标准有免费正文」是两件事。实测 1003 条阀门相关 GB/T 中，
只有 63 条（6.3%）能拿到在线正文，其余 940 条 `showGb` 直接 404。
选标准之前先查这张表，否则会白花时间在抓不到的正文上。

用法
----
  # 列出全部有正文的（默认只看现行）
  python tools/gb_body_query.py --open

  # 含废止
  python tools/gb_body_query.py --open --all-status

  # 按关键词筛（标准号或中文标题）
  python tools/gb_body_query.py --open --kw 阀门
  python tools/gb_body_query.py --open --kw GB/T 24919

  # 查某条标准的状态（给了标准号就精确查）
  python tools/gb_body_query.py --no GB/T 11698-2008

  # 按状态统计
  python tools/gb_body_query.py --stats

退出码：0 = 有命中，1 = 无命中，2 = 参数/文件错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "kb" / "catalog" / "gb_body_availability.json"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load() -> dict:
    if not LEDGER.exists():
        print(f"找不到台账 {LEDGER}\n先跑：python tools/probe_gb_body.py --only-valence --resume")
        raise SystemExit(2)
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--open", action="store_true", help="只列有免费正文的")
    ap.add_argument("--no", dest="no_body", action="store_true", help="只列无正文的")
    ap.add_argument("--stats", action="store_true", help="按状态统计")
    ap.add_argument("--all-status", action="store_true", help="含废止/即将实施")
    ap.add_argument("--kw", nargs="*", default=None, help="关键词（标准号或标题子串）")
    args = ap.parse_args()

    data = load()
    std = data.get("standards", {})
    rows = list(std.values())

    if args.stats:
        from collections import Counter
        print(f"台账时间: {data.get('probed_at')}   范围: {data.get('scope')}")
        print(f"总条目: {len(rows)}")
        print(f"body_status: {json.dumps(data.get('tally', {}), ensure_ascii=False)}")
        print("\n按标准现行状态 × 有无正文:")
        c = Counter((v.get("status"), v.get("body_status")) for v in rows)
        for (st, bs), n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {st:<8} {bs:<12} {n:>5}")
        return 0

    if args.kw:
        kws = [k.lower() for k in args.kw]
        rows = [v for v in rows
                if any(k in v.get("standard_no", "").lower() or k in v.get("title_zh", "").lower()
                       for k in kws)]

    if args.open:
        rows = [v for v in rows if v.get("body_status") == "OPEN_BODY"]
    elif args.no_body:
        rows = [v for v in rows if v.get("body_status") == "NO_BODY"]

    if not args.all_status:
        rows = [v for v in rows if v.get("status") == "现行"]

    rows.sort(key=lambda v: v.get("standard_no", ""))

    print(f"共 {len(rows)} 条"
          + ("（含全部现行状态）" if args.all_status else "（仅现行）"))
    print("-" * 78)
    for v in rows:
        mark = "*" if v.get("status") == "现行" else " "
        pages = v.get("page_count")
        pages_s = f"{pages}p" if pages else "  -"
        print(f"{mark} {v.get('standard_no',''):<24} {pages_s:>5}  {v.get('title_zh','')[:44]}")
    print("-" * 78)
    print("* = 现行   （空 = 无免费正文；ERROR 表示探测时网络异常，用 --resume 重试）")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
