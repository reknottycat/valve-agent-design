#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""standards_kb / probe_ibr_dirs.py —— 列出 IBR 站点所有子目录并全量建目录。"""
from __future__ import annotations

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


def get(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    PROBE.mkdir(parents=True, exist_ok=True)
    base = "https://law.resource.org/pub/us/cfr/ibr/"
    print("GET", base)
    try:
        html = get(base)
    except Exception as e:
        print("FAIL", e)
        return 1
    (PROBE / "ibr_root.html").write_text(html, encoding="utf-8")
    print("len", len(html))
    dirs = sorted(set(re.findall(r'href="(\d{3})/"', html)))
    if not dirs:
        dirs = sorted(set(re.findall(r'href="([^"/]+)/"', html)))
    print("子目录:", dirs)
    (PROBE / "ibr_dirs.txt").write_text("\n".join(dirs), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
