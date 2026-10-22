#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 openstd 新路径 /bzgk/std/std_list 是否服务端直出结果行与 hcno。"""
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

for q in ["GB/T 3045", "GB/T 13927", "GB/T 3098.1"]:
    url = f"{BASE}/bzgk/std/std_list?p.p1=0&p.p2={requests.utils.quote(q)}"
    html = s.get(url, timeout=30).text
    hcnos = re.findall(r"showInfo\('([0-9A-Za-z]+)'\)", html)
    stdnos = re.findall(r"GB(?:/T)?\s*[A-Z]?\s*\d+(?:\.\d+)?(?:-\d{4})?", html)
    print(f"== {q}  len={len(html)}  showInfo hcno={len(hcnos)} -> {hcnos[:5]}")
    if hcnos:
        # 取第一行的标准号
        m = re.search(r"GB[^<>\s]*", html[html.find("showInfo"):])
        print(f"   附近标准号: {html[max(0,html.find('showInfo')-300):html.find('showInfo')+80]!r}")
    print()
