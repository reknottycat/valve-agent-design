#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 openstd 列表页的内联 <script> 整段落盘,便于人工读接口构造。"""
from __future__ import annotations
import re, sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env
prepare_env(verbose=False)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "https://openstd.samr.gov.cn"
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"})

url = f"{BASE}/bzgk/std/std_list?p.p1=0&p.p2=GB%2FT%203045"
html = s.get(url, timeout=30).text

out = Path(__file__).resolve().parent.parent / "runs" / "probe"
out.mkdir(parents=True, exist_ok=True)
(out / "gb_std_list.html").write_text(html, encoding="utf-8")

scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
body = "\n/* ---------- next script ---------- */\n".join(s for s in scripts if s.strip())
(out / "gb_std_list_inline.js").write_text(body, encoding="utf-8")
print(f"HTML -> {out/'gb_std_list.html'}  ({len(html)} B)")
print(f"inline JS -> {out/'gb_std_list_inline.js'}  ({len(body)} B)")

# 只打印与接口/参数相关的行
for i, line in enumerate(body.splitlines(), 1):
    if re.search(r"hcno|\$\.ajax|\$\.post|\$\.get|url\s*:|function\s+\w+|std_list|showGb|open\(", line):
        print(f"{i:>4}: {line[:220]}")
