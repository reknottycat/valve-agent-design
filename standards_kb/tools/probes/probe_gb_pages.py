#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从阅读器 HTML 提取页面清单(bg 属性)并试下载第一页图片。"""
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

p = Path(__file__).resolve().parent.parent / "runs" / "probe" / "gb_showgb.html"
html = p.read_text(encoding="utf-8", errors="replace")

# 1) 页数
m = re.search(r"var page\s*=\s*(\d+)", html)
print("页数 var page =", m.group(1) if m else "?")

# 2) .page 元素与 bg 属性
bg_all = re.findall(r"""class=["'][^"']*\bpage\b[^"']*["'][^>]*\bbg=["']([^"']+)["']""", html)
bg_all2 = re.findall(r"""\bbg=["']([^"']+\.(?:jpg|jpeg|png|gif|webp))["']""", html)
print(f"class 含 page 的 bg: {len(bg_all)}  任意 bg 图片名: {len(bg_all2)}")
bgs = bg_all or bg_all2
for b in bgs[:6]:
    print("   bg:", b)

# 3) 第一个 .page 区块的原文,看有没有文字层
i = html.find('class="page')
if i < 0:
    i = html.find("class='page")
print("\n=== 第一个 .page 区块 ===")
print(html[i-200:i+1400] if i >= 0 else "(未找到)")

# 4) 试下载第一页图片
if bgs:
    u = f"{BASE}/bzgk/std/viewGbImg?fileName={bgs[0]}"
    r = s.get(u, timeout=60, referer=f"{BASE}/bzgk/std/showGb")
    outdir = Path(__file__).resolve().parent.parent / "runs" / "probe" / "gb_page"
    outdir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    for cand in (".jpg", ".png", ".jpeg"):
        if cand in r.headers.get("Content-Type", "") or r.content[:3] == b"\xff\xd8\xff":
            ext = cand; break
    f = outdir / f"page001{ext}"
    f.write_bytes(r.content)
    print(f"\n下载 {u}\n  {r.status_code} {r.headers.get('Content-Type')} {len(r.content)} B -> {f}")
