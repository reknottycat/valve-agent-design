#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 sprite 0 字节: 看响应头/编码/流式读取。"""
from __future__ import annotations
import re, sys, urllib.parse
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env
prepare_env(verbose=False)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://openstd.samr.gov.cn"
HCNO = "3FC66D5433FEE4423518769107CF035A"
probe = Path(__file__).resolve().parent.parent / "runs" / "probe"

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"})
show_url = f"{BASE}/bzgk/std/showGb?type=online&hcno={HCNO}"
r0 = s.get(show_url, timeout=90)
print(f"[showGb] {r0.status_code} len={len(r0.text)} cookies={s.cookies.get_dict()}")
html = r0.text
m_bg = re.search(r"""class="page" bg="([^"]+)""", html)
bg = m_bg.group(1) if m_bg else "2SINXrj4%2FVraK2yTCYP8roRdvDElptsFR48Bo8tYdV4pKgp2AjVUx7%2Fr3YfMDTJd"
dec = urllib.parse.unquote(bg)

s.headers["Referer"] = show_url
s.headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
s.headers["Sec-Fetch-Dest"] = "image"
s.headers["Sec-Fetch-Mode"] = "no-cors"
s.headers["Sec-Fetch-Site"] = "same-origin"

u = f"{BASE}/bzgk/std/viewGbImg?fileName={dec}"
r = s.get(u, timeout=120, stream=True, allow_redirects=True)
print(f"\n[GET] {r.status_code}")
for k in ("Content-Type", "Content-Length", "Transfer-Encoding", "Content-Encoding",
          "Content-Range", "Accept-Ranges", "Server", "Cache-Control", "Location"):
    if k in r.headers:
        print(f"   {k}: {r.headers[k]}")
print("   final url:", r.url[:160])

total = 0
out = probe / "gb_sprite.webp"
with out.open("wb") as fh:
    for chunk in r.iter_content(chunk_size=65536):
        if chunk:
            total += len(chunk); fh.write(chunk)
print(f"   流式读到 {total} B -> {out}")
if total:
    head = out.read_bytes()[:16]
    print(f"   头16字节: {head!r}")
    try:
        from PIL import Image
        im = Image.open(out)
        print(f"   尺寸: {im.size} 模式 {im.mode}")
    except Exception as e:
        print(f"   (PIL: {e})")
