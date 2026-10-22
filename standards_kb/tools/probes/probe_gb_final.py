#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GB 正文获取终局验证: 会话 + sprite + download 通道。"""
from __future__ import annotations
import re, sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env
prepare_env(verbose=False)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://openstd.samr.gov.cn"
HCNO = "3FC66D5433FEE4423518769107CF035A"
probe = Path(__file__).resolve().parent.parent / "runs" / "probe"
probe.mkdir(parents=True, exist_ok=True)

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
                  "Referer": f"{BASE}/bzgk/std/std_list"})

# 0) 详情页拿 data-value
d = s.get(f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}", timeout=30)
for cls in ("xz_btn", "ck_btn"):
    m = re.search(rf"""class=["'][^"']*{cls}[^"']*["'][^>]*data-value=["']([^"']+)["']""", d.text)
    if not m:
        m = re.search(rf"""data-value=["']([^"']+)["'][^>]*class=["'][^"']*{cls}""", d.text)
    print(f"[{cls}] data-value = {m.group(1) if m else '(未找到)'}")

# 1) 先 GET showGb 建会话
show_url = f"{BASE}/bzgk/std/showGb?type=online&hcno={HCNO}"
r0 = s.get(show_url, timeout=90)
print(f"\n[showGb] {r0.status_code} len={len(r0.text)} cookies={dict(s.cookies)}")
html = r0.text
bg = re.search(r"""class="page" bg="([^"]+)""", html).group(1)

# 2) sprite —— 带完整 Referer + 会话
s.headers["Referer"] = show_url
u = f"{BASE}/bzgk/std/viewGbImg?fileName={bg}"
r = s.get(u, timeout=120)
ct = r.headers.get("Content-Type", "")
ext = ".webp" if "webp" in ct else (".jpg" if "jpeg" in ct else ".png" if "png" in ct else ".bin")
f = probe / f"gb_sprite{ext}"
f.write_bytes(r.content)
print(f"[sprite] {r.status_code} {ct} {len(r.content)} B -> {f}")
if len(r.content) > 0:
    try:
        from PIL import Image
        im = Image.open(f)
        print(f"        图片尺寸: {im.size}  模式 {im.mode}")
    except Exception as e:
        print(f"        (PIL 不可用: {e})")

# 3) download 通道
for t in ("download", "online"):
    du = f"{BASE}/bzgk/std/showGb?type={t}&hcno={HCNO}"
    rd = s.get(du, timeout=90, allow_redirects=True)
    print(f"\n[showGb type={t}] {rd.status_code} len={len(rd.content)} "
          f"ctype={rd.headers.get('Content-Type','')} final={rd.url[:110]}")
    if "text/html" in rd.headers.get("Content-Type", ""):
        m = re.search(r"""var page\s*=\s*(\d+)""", rd.text)
        print(f"        HTML 页面，var page = {m.group(1) if m else '?'}")
    else:
        out = probe / f"gb_download_{t}{Path(rd.url).suffix or '.bin'}"
        out.write_bytes(rd.content)
        print(f"        -> {out}")
