#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / catalog_ibr.py —— 把 law.resource.org 的 IBR 索引解析成结构化目录

这个站点是「美国联邦法规引用入册(IBR)」的免费正文镜像站。
每个子目录(002=ASME 主目录 等)下是一张表,每行给出一份标准:

    文件名 | 日期 | 大小 | 标题 + [CFR 引用条款]

本地镜像遵循固定命名,所以正文直链可推导:
    https://law.resource.org/pub/us/cfr/ibr/<dir>/<filename>

产出 kb/catalog/law_resource_ibr.json —— 一份可检索、可增量刷新的标准目录。
有了它,以后要补正文只需按标准号查表,不用再上网搜。

用法:
  python catalog_ibr.py                 # 抓取并解析(默认 002)
  python catalog_ibr.py --dirs 002 003  # 指定多个目录
  python catalog_ibr.py --offline       # 不联网,用已有的 runs/probe 缓存
  python catalog_ibr.py --find b16.34   # 只打印匹配项
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "runs" / "probe"
CATALOG = ROOT / "kb" / "catalog" / "law_resource_ibr.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S | re.I)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
HREF_RE = re.compile(r'href="([^"]+)"', re.I)
TAG_RE = re.compile(r"<[^>]+>")


def clean(s: str) -> str:
    s = TAG_RE.sub("", s)
    s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", s).strip()


def fetch(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse_dir(dirname: str, html: str) -> list[dict]:
    base = f"https://law.resource.org/pub/us/cfr/ibr/{dirname}/"
    out = []
    for row in ROW_RE.findall(html):
        tds = TD_RE.findall(row)
        if len(tds) < 4:
            continue
        name = clean(tds[1])
        if not name or name.endswith("/"):
            continue  # 目录行
        date = clean(tds[2])
        size = clean(tds[3])
        title = clean(tds[4]) if len(tds) > 4 else ""
        hrefs = HREF_RE.findall(tds[1])
        archive_url = next((h for h in hrefs if "archive.org/details" in h), "")
        dl_url = next((h for h in hrefs if "archive.org/download" in h), "")

        m = re.match(r"asme\.(.+?)\.(\d{4})\.(pdf|html|svg\.html|txt)$", name, re.I)
        code = m.group(1) if m else ""
        year = m.group(2) if m else ""
        ext = m.group(3) if m else name.rsplit(".", 1)[-1]

        cfr = ""
        cm = re.search(r"\[([^\]]+)\]", title)
        if cm:
            cfr = cm.group(1)
            title = title[:cm.start()].strip()

        out.append({
            "dir": dirname,
            "file": name,
            "ext": ext,
            "standard_code": code.upper(),
            "year": year,
            "title": title,
            "cfr_cite": cfr,
            "size_text": size,
            "local_url": f"{base}{name}",
            "archive_details": archive_url,
            "archive_download": dl_url,
        })
    return out


def guess_kind(code: str) -> str:
    """按标准号粗判标准类型 —— 决定它是给公式还是给尺寸。"""
    c = code.upper()
    if c.startswith("BPVC"):
        if re.match(r"BPVC\s*(I|II|VIII)\b", c) or c in ("BPVC I", "BPVC II", "BPVC VIII"):
            return "MECHANICS"
        return "CODE"
    if c.startswith("B16"):
        if any(k in c for k in ("B16.5", "B16.9", "B16.25", "B16.47", "B16.48")):
            return "DIMENSION"
        return "MECHANICS"
    if c.startswith("B31"):
        return "MECHANICS"
    if c.startswith("B30"):
        return "SAFETY"
    if c.startswith("PCC"):
        return "CODE"
    return "OTHER"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dirs", nargs="*", default=["002"])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--find", help="按关键字过滤打印")
    args = ap.parse_args()

    PROBE.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for d in args.dirs:
        cache = PROBE / f"ibr{d}_index.html"
        if args.offline and cache.exists():
            html = cache.read_text(encoding="utf-8")
            print(f"[cache] {cache.name} len={len(html)}")
        else:
            url = f"https://law.resource.org/pub/us/cfr/ibr/{d}/"
            print(f"GET {url}")
            try:
                html = fetch(url)
            except Exception as e:
                print(f"  FAIL {type(e).__name__}: {e}")
                continue
            cache.write_text(html, encoding="utf-8")
        got = parse_dir(d, html)
        print(f"  解析 {len(got)} 条")
        rows += got

    # 只保留可下载的正文(pdf/txt),html 是目录说明页
    bodies = [r for r in rows if r["ext"] in ("pdf", "txt")]
    for r in bodies:
        r["kind_guess"] = guess_kind(r["standard_code"])

    payload = {
        "schema": "standards_kb.catalog/1.0",
        "source": "law.resource.org/pub/us/cfr/ibr/",
        "license_note": ("美国联邦法规引用入册(IBR)公开镜像;各标准版权仍属 ASME 等原发布方。"
                         "本目录只用于工程检索,不用于再分发。"),
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "dirs_scanned": args.dirs,
        "counts": {
            "rows_total": len(rows),
            "bodies": len(bodies),
            "by_kind": {k: sum(1 for b in bodies if b["kind_guess"] == k)
                        for k in sorted({b["kind_guess"] for b in bodies})},
        },
        "entries": bodies,
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {CATALOG.relative_to(ROOT)}  正文 {len(bodies)} 份")
    print("分类:", payload["counts"]["by_kind"])

    if args.find:
        pat = args.find.lower()
        hit = [b for b in bodies if pat in b["file"].lower() or pat in b["title"].lower()]
        for b in hit:
            print(f"  {b['file']:<34}{b['size_text']:>8}  {b['title'][:60]}")
        if not hit:
            print(f"  无匹配 '{pat}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
