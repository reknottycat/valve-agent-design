#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GB 国标全文公开系统 —— 静态接口探测

已知正文页形如 /bzgk/gb/showGb?type=online&hcno=<hash>
问题: 检索结果由 JS 渲染,静态 GET/POST 拿不到 hcno。
本脚本穷举常见的 openstd 后端接口形态,看哪个能直接吐 JSON/HTML 结果行。
"""
from __future__ import annotations
import json, re, sys, urllib.parse
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://openstd.samr.gov.cn"
HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Referer": f"{BASE}/bzgk/gb/std_list",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}

def show(tag, r, want=None, maxlen=260):
    body = r.text
    print(f"[{tag}] {r.status_code} len={len(body)} ctype={r.headers.get('Content-Type','')}")
    snippet = body[:maxlen].replace("\n", " ")
    print("   ", snippet)
    if want:
        m = re.findall(want, body)
        print(f"    MATCH {want} -> {len(m)} hits: {m[:6]}")
    print()

def main():
    s = requests.Session()
    s.headers.update(HDRS)

    # 1) 检索 POST
    print("=" * 60, "\n1) POST /bzgk/gb/std_list (表单检索)\n")
    for payload in [
        {"r": "", "page": "1", "pageSize": "10", "p.p1": "0", "p.p90": "circulation_date", "p.p91": "desc"},
        {"p.p1": "1", "p.p2": "GB/T 12234"},
        {"searchText": "GB/T 12234"},
    ]:
        try:
            r = s.post(f"{BASE}/bzgk/gb/std_list", data=payload, timeout=25)
            show(f"POST {list(payload)[:2]}", r, r"hcno=([0-9A-Za-z]+)")
        except Exception as e:
            print(f"[POST {list(payload)[:2]}] ERR {type(e).__name__}: {e}\n")

    # 2) 直连 JSON 接口(几种常见形态)
    print("=" * 60, "\n2) 可能的 JSON 后端\n")
    urls = [
        f"{BASE}/bzgk/gb/std_list?r=0.5648383059571312&page=1&pageSize=10&p.p1=0&p.p90=circulation_date&p.p91=desc",
        f"{BASE}/bzgk/gb/std_listType?p.p1=0&p.p2=GB%2FT%2012234",
        f"{BASE}/bzgk/gb/newGbInfo?hcno=0",
        f"{BASE}/bzgk/gb/showGb?type=online&hcno=0",
    ]
    for u in urls:
        try:
            r = s.get(u, timeout=25)
            show(u.replace(BASE, ""), r, r"hcno=([0-9A-Za-z]+)")
        except Exception as e:
            print(f"[{u}] ERR {type(e).__name__}: {e}\n")

    # 3) 首页里有没有裸的 JSON/接口线索
    print("=" * 60, "\n3) 首页脚本里的接口线索\n")
    try:
        r = s.get(f"{BASE}/bzgk/gb/std_list", timeout=25)
        for pat in [r"""url\s*[:=]\s*['"]([^'"]*std[^'"]*)['"]""",
                    r"""\$\.(?:post|get|ajax)\(\s*['"]([^'"]+)['"]""",
                    r"""(/bzgk/[A-Za-z0-9_/]+)"""]:
            hits = re.findall(pat, r.text)
            uniq = sorted(set(hits))[:15]
            print(f"  {pat[:40]:<42} -> {uniq}")
    except Exception as e:
        print("  ERR", e)

if __name__ == "__main__":
    main()
