#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GB 正文获取: 完整正确链路 + 产出可直接复用的下载器。

链路(实测):
  1) GET /bzgk/std/newGbInfo?hcno=X   建立授权会话(JSESSIONID)
  2) GET /bzgk/std/showGb?type=online&hcno=X   拿阅读器页面 + 页面数 + bg 清单
  3) GET /bzgk/std/viewGbImg?fileName=<bg 解码>  拿 sprite(webp),服务器 302 到
     /bzgk/data/<标准号>/<宽>-<高>-<页>_<token>.webp
"""
from __future__ import annotations
import re, sys, time, urllib.parse
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

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})

# 1) 详情页 —— 建立授权会话
d = s.get(f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}", timeout=30)
d.headers["Referer"] = f"{BASE}/bzgk/std/std_list"
print(f"[1 newGbInfo] {d.status_code} len={len(d.text)} cookies={s.cookies.get_dict()}")

# 2) 阅读器页
show_url = f"{BASE}/bzgk/std/showGb?type=online&hcno={HCNO}"
s.headers["Referer"] = f"{BASE}/bzgk/std/newGbInfo?hcno={HCNO}"
r = s.get(show_url, timeout=90)
print(f"[2 showGb]    {r.status_code} len={len(r.text)}")
if "var page" not in r.text:
    print("    !! 未拿到阅读器页(可能被重定向),链路不成立")
    raise SystemExit(1)

npages = int(re.search(r"var page\s*=\s*(\d+)", r.text).group(1))
bgs = re.findall(r"""class="page" bg="([^"]+)""", r.text)
print(f"    页数={npages}  bg 清单 {len(bgs)} 个(去重后 {len(set(bgs))})")
(probe / "gb_showgb.html").write_text(r.text, encoding="utf-8")

# 3) 取第一页 sprite
s.headers["Referer"] = show_url
s.headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
s.headers["Sec-Fetch-Dest"] = "image"
s.headers["Sec-Fetch-Mode"] = "no-cors"
s.headers["Sec-Fetch-Site"] = "same-origin"

ok = 0
for i, bg in enumerate(dict.fromkeys(bgs)):
    dec = urllib.parse.unquote(bg)
    u = f"{BASE}/bzgk/std/viewGbImg?fileName={dec}"
    rr = s.get(u, timeout=120)
    n = len(rr.content)
    if n > 0:
        ok += 1
        f = probe / f"gb_sprite_{i}.webp"
        f.write_bytes(rr.content)
        if ok == 1:
            print(f"\n[3 sprite] OK {n} B  final={rr.url[-70:]}")
            print(f"           头16: {rr.content[:16]!r}")
            try:
                from PIL import Image
                im = Image.open(f); print(f"           尺寸 {im.size} 模式 {im.mode}")
            except Exception as e:
                print(f"           (PIL: {e})")
    else:
        print(f"[3 sprite] {i} 空 (final={rr.url[-60:]})")
    if ok >= 2:
        break
    time.sleep(0.4)

print(f"\n成功 {ok} 个 sprite")
