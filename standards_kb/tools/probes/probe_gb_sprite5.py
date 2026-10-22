#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sprite 仍空: 逐个加头组合试。JS 里那句 setRequestHeader('Cache-Alive','chunked') 是关键。"""
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
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def fresh():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    s.get(f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}", timeout=30)
    show = f"{BASE}/bzgk/std/showGb?type=online&hcno={HCNO}"
    s.headers["Referer"] = f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}"
    r = s.get(show, timeout=90)
    bg = re.search(r"""class="page" bg="([^"]+)""", r.text).group(1)
    return s, show, bg

s, show, bg = fresh()
print("bg =", bg)

combos = [
    ("plain", {}),
    ("Cache-Alive:chunked", {"Cache-Alive": "chunked"}),
    ("Cache-Alive+SecFetch", {"Cache-Alive": "chunked",
                             "Sec-Fetch-Dest": "image", "Sec-Fetch-Mode": "no-cors",
                             "Sec-Fetch-Site": "same-origin"}),
    ("X-Requested-With", {"X-Requested-With": "XMLHttpRequest"}),
    ("no-referer", {"__delref__": True}),
]
for tag, extra in combos:
    ss, sh, b = fresh()
    h = dict(ss.headers)
    h["Referer"] = sh
    h["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    h.update(extra)
    if extra.pop("__delref__", None):
        h.pop("Referer", None)
    u = f"{BASE}/bzgk/std/viewGbImg?fileName={b}"
    try:
        rr = ss.get(u, timeout=120, headers=h)
        n = len(rr.content)
        print(f"[{tag:<22}] {rr.status_code} {rr.headers.get('Content-Type',''):<12} "
              f"len={n:<8} clen={rr.headers.get('Content-Length')} final={rr.url[-42:]}")
        if n:
            (probe / f"gb_ok_{tag.split()[0]}.webp").write_bytes(rr.content)
    except Exception as e:
        print(f"[{tag:<22}] ERR {e}")

# 直接打最终静态路径
final = None
ss, sh, b = fresh()
rr = ss.get(f"{BASE}/bzgk/std/viewGbImg?fileName={b}", timeout=120,
            headers={**ss.headers, "Referer": sh})
final = rr.url
print(f"\n[final path] {final}")
r2 = ss.get(final, timeout=120, headers={**ss.headers, "Referer": sh,
                                         "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
                                         "Cache-Alive": "chunked"})
print(f"[direct]     {r2.status_code} {r2.headers.get('Content-Type')} len={len(r2.content)} "
      f"clen={r2.headers.get('Content-Length')}")
if len(r2.content):
    (probe / "gb_ok_direct.webp").write_bytes(r2.content)
