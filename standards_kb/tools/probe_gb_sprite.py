#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载 GB 阅读器 sprite,并在详情页里找 PDF/文本下载口。"""
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
                  "Referer": f"{BASE}/bzgk/std/showGb"})

probe = Path(__file__).resolve().parent.parent / "runs" / "probe"
probe.mkdir(parents=True, exist_ok=True)

# ---------- 1) sprite 下载 ----------
p = probe / "gb_showgb.html"
html = p.read_text(encoding="utf-8", errors="replace")
bg = re.search(r"""class="page" bg="([^"]+)""", html).group(1)
u = f"{BASE}/bzgk/std/viewGbImg?fileName={bg}"
r = s.get(u, timeout=90)
ct = r.headers.get("Content-Type", "")
ext = ".jpg" if "jpeg" in ct or r.content[:3] == b"\xff\xd8\xff" else (".png" if "png" in ct else ".bin")
f = probe / f"gb_sprite{ext}"
f.write_bytes(r.content)
print(f"[sprite] {r.status_code} {ct} {len(r.content)} B -> {f}")

# ---------- 2) 详情页里的下载/文本口 ----------
print("\n=== newGbInfo 详情页按钮与接口 ===")
d = s.get(f"{BASE}/bzgk/std/newGbInfo?hcno=3FC66D5433FEE4423518769107CF035A", timeout=30)
(d_probe := probe / "gb_newgbinfo.html").write_text(d.text, encoding="utf-8")
dh = d.text
for pat, tag in [
    (r"""showGb\(([^)]*)\)""", "showGb-args"),
    (r"""onclick=["']([^"']+)["']""", "onclick"),
    (r"""\$\.(?:post|get|ajax)\(\s*\{?\s*url\s*[:=]\s*['"]([^'"]+)['"]""", "ajax-url"),
    (r"""['"]([^'"]*download[^'"]*)['"]""", "download"),
    (r"""['"]([^'"]*\.pdf[^'"]*)['"]""", "pdf"),
    (r"""['"](/bzgk/[A-Za-z0-9_./-]+)['"]""", "bzgk"),
]:
    hits = sorted(set(re.findall(pat, dh, re.I)))
    if hits:
        print(f"  [{tag}] {hits[:12]}")

# 详情页里 showGb 的完整调用上下文
for m in re.finditer(r"showGb\(", dh):
    print("\n  showGb ctx:", dh[max(0, m.start()-260):m.start()+200].replace("\n", " ")[:460])
    break
