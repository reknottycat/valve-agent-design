#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在已落盘的阅读器 HTML 里找页面数据的真实载体。"""
from __future__ import annotations
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = Path(__file__).resolve().parent.parent / "runs" / "probe" / "gb_showgb.html"
html = p.read_text(encoding="utf-8", errors="replace")
print(f"len={len(html)}")

print("data:image 出现次数:", html.count("data:image"))
print("base64 出现次数:", html.count("base64"))
print("<img 次数:", html.count("<img"))
print("<canvas 次数:", html.count("<canvas"))
print("<embed 次数:", html.count("<embed"))
print("iframe 次数:", html.count("iframe"))

# 看最大的几段脚本块
scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
scripts.sort(key=len, reverse=True)
for i, sc in enumerate(scripts[:4]):
    print(f"\n===== script #{i} len={len(sc)} =====")
    # 只打印含 url/path/ajax/src 的行
    for ln, line in enumerate(sc.splitlines(), 1):
        if re.search(r"src\s*=|url|path|ajax|XMLHttp|\.php|\.do|image|page", line, re.I) and len(line) < 300:
            print(f"  {ln:>4}: {line.strip()[:220]}")

# 直接找 XHR 上下文
for m in re.finditer(r"new XMLHttpRequest", html):
    seg = html[max(0, m.start()-300):m.start()+900]
    print("\n=== XHR context ===\n", seg[:1200])
    break
