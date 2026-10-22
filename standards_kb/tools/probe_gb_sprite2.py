#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""试各种 fileName 传参形态拿到 sprite 字节。"""
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
html = r0.text
m_bg = re.search(r"""class="page" bg="([^"]+)""", html)
if not m_bg:
    # 回退: 用已落盘的页面,避免每次重拉都打站点
    cached = probe / "gb_showgb.html"
    if not cached.exists():
        print("showGb 未返回页面结构且无缓存,退出")
        raise SystemExit(1)
    html = cached.read_text(encoding="utf-8", errors="replace")
    m_bg = re.search(r"""class="page" bg="([^"]+)""", html)
    print(f"[fallback] 用缓存页面解析 bg (len={len(html)})")
bg = m_bg.group(1)
s.headers["Referer"] = show_url
print(f"bg(raw)     = {bg}")
print(f"bg(decoded) = {urllib.parse.unquote(bg)}")

variants = {
    "A raw-in-url":      f"{BASE}/bzgk/std/viewGbImg?fileName={bg}",
    "B decoded-in-url":  f"{BASE}/bzgk/std/viewGbImg?fileName={urllib.parse.unquote(bg)}",
    "C params-raw":      None,   # params dict, requests 会原样发送 %2F? 实际会再编码
    "D params-decoded":  None,
    "E gb-path":         f"{BASE}/bzgk/gb/viewGbImg?fileName={bg}",
}
for tag, u in variants.items():
    if u is None:
        continue
    try:
        r = s.get(u, timeout=90)
        print(f"[{tag}] {r.status_code} {r.headers.get('Content-Type','')} {len(r.content)} B")
        if len(r.content) > 100:
            (probe / f"gb_sprite_{tag.split()[0]}.bin").write_bytes(r.content)
    except Exception as e:
        print(f"[{tag}] ERR {e}")

# params 形态
for tag, val in (("C params-raw", bg), ("D params-decoded", urllib.parse.unquote(bg))):
    try:
        r = s.get(f"{BASE}/bzgk/std/viewGbImg", params={"fileName": val}, timeout=90)
        print(f"[{tag}] {r.status_code} {r.headers.get('Content-Type','')} {len(r.content)} B  url={r.url[-90:]}")
        if len(r.content) > 100:
            (probe / f"gb_sprite_{tag.split()[0]}.bin").write_bytes(r.content)
    except Exception as e:
        print(f"[{tag}] ERR {e}")

# download 页内容
s.headers["Referer"] = f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}"
rd = s.get(f"{BASE}/bzgk/std/showGb?type=download&hcno={HCNO}", timeout=60)
(probe / "gb_download_page.html").write_text(rd.text, encoding="utf-8")
txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", rd.text, flags=re.S)
txt = re.sub(r"<[^>]+>", " ", txt); txt = re.sub(r"\s+", " ", txt).strip()
print(f"\n[download 页 可见文本 {len(txt)}B]\n{txt[:700]}")
for pat in [r"""['"]([^'"]*(?:download|zip|rar|pdf|xls|doc)[^'"]*)['"]""",
            r"""\$\.(?:ajax|post|get)\(\s*\{?[^)]{0,200}?url\s*[:=]\s*['"]([^'"]+)['"]""",
            r"""form[^>]*action=["']([^"']+)["']"""]:
    hits = sorted(set(re.findall(pat, rd.text, re.I)))
    if hits:
        print(f"  {pat[:38]:<40} -> {hits[:10]}")
