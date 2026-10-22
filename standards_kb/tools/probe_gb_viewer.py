#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""落盘 GB 阅读器页面并定位「每页图片」的 URL 构造规则。"""
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
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
                  "Referer": f"{BASE}/bzgk/std/std_list"})

HCNO = "3FC66D5433FEE4423518769107CF035A"
url = f"{BASE}/bzgk/std/showGb?type=online&hcno={HCNO}"
r = s.get(url, timeout=60)
html = r.text
out = Path(__file__).resolve().parent.parent / "runs" / "probe"
out.mkdir(parents=True, exist_ok=True)
(out / "gb_showgb.html").write_text(html, encoding="utf-8")
print(f"-> {out/'gb_showgb.html'}  {len(html)} B")

# 找图片/页面数据源
for pat, tag in [
    (r"""['"]([^'"]*\.(?:jpg|jpeg|png|gif|pdf|webp)[^'"]*)['"]""", "file-url"),
    (r"""\$\.(?:get|post|ajax)\(\s*['"]([^'"]+)['"]""", "ajax"),
    (r"""url\s*[:=]\s*['"]([^'"]+)['"]""", "url"),
    (r"""['"](/bzgk/[A-Za-z0-9_./?=&{}+-]+)['"]""", "bzgk"),
    (r"""(getPage[A-Za-z]*|loadPage[A-Za-z]*|pageUrl[A-Za-z]*)""", "fn"),
    (r"""XMLHttpRequest\(\)""", "xhr"),
]:
    hits = sorted(set(re.findall(pat, html, re.I)))
    if hits:
        print(f"\n[{tag}] {len(hits)} hits")
        for h in hits[:25]:
            print("   ", h[:170])

# 关键: 找 AJAX 的 data 参数与路径拼接
for m in re.finditer(r"""\$\.ajax\(\{""", html):
    seg = html[m.start():m.start()+700]
    print("\n=== ajax block ===\n", seg[:700])
