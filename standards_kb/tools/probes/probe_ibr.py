#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / probe_ibr.py —— 探测 law.resource.org 的 ASME IBR 镜像目录

law.resource.org/pub/us/cfr/ibr/<n>/ 是美国联邦法规「引用入册(IBR)」的
免费正文镜像,ASME 大部分标准都在里面。这是目前最可靠的 ASME 正文来源。

用法:
  python probe_ibr.py                # 列出 002 目录(=ASME 主目录)
  python probe_ibr.py 003            # 列出其它目录
  python probe_ibr.py --find b16.34  # 只看匹配的
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "runs" / "probe"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dir", nargs="?", default="002")
    ap.add_argument("--find", help="按关键字过滤,例: b16.34")
    args = ap.parse_args()

    base = f"https://law.resource.org/pub/us/cfr/ibr/{args.dir}/"
    print(f"GET {base}")
    try:
        html = get(base)
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}")
        return 1

    PROBE.mkdir(parents=True, exist_ok=True)
    (PROBE / f"ibr{args.dir}_index.html").write_text(html, encoding="utf-8")
    print(f"len={len(html)} -> runs/probe/ibr{args.dir}_index.html")

    links = re.findall(r'href="([^"]+)"', html)
    pdfs = [l for l in links if l.lower().endswith(".pdf")]
    print(f"href={len(links)} pdf={len(pdfs)}")

    # 把清单落盘,方便后续直接消费,不必反复联网
    lst = PROBE / f"ibr{args.dir}_links.txt"
    lst.write_text("\n".join(pdfs), encoding="utf-8")
    print(f"清单 -> {lst.relative_to(ROOT)}")

    if args.find:
        pat = args.find.lower()
        hit = [p for p in pdfs if pat in p.lower()]
        for p in hit:
            print("  HIT", p)
        if not hit:
            print(f"  无匹配 '{pat}'")
            # 打印相近的供人工判断
            near = [p for p in pdfs if pat.split(".")[0] in p.lower()]
            for p in near[:40]:
                print("  near", p)
    else:
        for p in pdfs:
            print(" ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
