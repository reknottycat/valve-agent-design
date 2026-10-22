#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 openstd 页面 HTML / JS 里挖出真实的数据接口路径。

背景: 检索结果由 JS 注入,静态 GET/POST 拿不到 hcno。
但 JS 必须在某个时刻请求数据 —— 把那段 JS 拉下来找 URL 即可。
"""
from __future__ import annotations
import re, sys, urllib.parse
import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from net_env import prepare_env

prepare_env()  # 清掉可能残留的死代理 env（FlClash DNS-only 时会误报连接拒绝）

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "https://openstd.samr.gov.cn"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}

s = requests.Session(); s.headers.update(HDRS)
url = f"{BASE}/bzgk/std/std_list?p.p1=0&p.p2=GB%2FT%203045"
html = s.get(url, timeout=30).text
print(f"HTML len={len(html)}")

# 1) 内联 script 里的接口线索
inline = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))
pats = [
    r"""url\s*:\s*['"]([^'"]+)['"]""",
    r"""\$\.(?:post|get|ajax)\(\s*['"]([^'"]+)['"]""",
    r"""['"](/bzgk/[A-Za-z0-9_./-]+)['"]""",
    r"""['"]([^'"]*std_list[^'"]*)['"]""",
    r"""hcno['"]?\s*[:=]\s*['"]([^'"]+)['"]""",
]
for p in pats:
    hits = sorted(set(re.findall(p, inline)))
    print(f"  inline {p[:38]:<40} -> {hits[:12]}")

# 2) 外链 script
srcs = re.findall(r"""<script[^>]+src=["']([^"']+)["']""", html)
print(f"\n外链 script {len(srcs)} 个:")
api_hits = set()
for src in srcs:
    full = urllib.parse.urljoin(url, src)
    try:
        js = s.get(full, timeout=30).text
    except Exception as e:
        print(f"  ERR {src}: {e}"); continue
    for p in [r"""['"]([^'"]*std_list[^'"]*)['"]""",
              r"""['"]([^'"]*std_[A-Za-z0-9_]+[^'"]*)['"]""",
              r"""['"](/bzgk/[A-Za-z0-9_./-]+)['"]""",
              r"""\$\.ajax\(\{[^}]*url\s*:\s*['"]([^'"]+)['"]"""]:
        for h in re.findall(p, js):
            api_hits.add(h)
    print(f"  {src.split('/')[-1]:<40} len={len(js)}")

print("\n=== 所有 API 路径候选 ===")
for h in sorted(api_hits):
    if any(k in h for k in ("std", "gb", "hcno", "show")):
        print("  ", h)
