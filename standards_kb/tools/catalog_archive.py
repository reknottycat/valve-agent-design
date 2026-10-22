#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / catalog_archive.py —— 盘点 archive.org 上 gov.law.asme.* 的可下载正文

archive.org 的 gov.law.asme.* 集合是 ASME 正文最大的免费来源。
每个 item 含:
    asme.<编号>.<年>.pdf        扫描件(可能无文本层)
    asme.<编号>.<年>_djvu.txt    OCR 文本层(直接可抽公式)
    asme.<编号>.<年>.html        归档说明页

产出 kb/catalog/archive_asme.json —— 逐 item 列出可下载文件与体积,
以后补正文按图索骥,不用再探测。

用法:
  python catalog_archive.py
  python catalog_archive.py --find b16.34
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "kb" / "catalog" / "archive_asme.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CST = timezone(timedelta(hours=8))
API = ("https://archive.org/advancedsearch.php?q=identifier:gov.law.asme.*"
       "&fl[]=identifier&fl[]=title&rows=300&page=1&output=json")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--find", help="按关键字过滤打印")
    args = ap.parse_args()

    print("GET search API")
    raw = get(API)
    data = json.loads(raw.decode("utf-8", "replace"))
    docs = data.get("response", {}).get("docs", [])
    print(f"命中 {len(docs)} 个 item")

    items = []
    for d in docs:
        ident = d.get("identifier", "")
        if not ident.startswith("gov.law.asme."):
            continue
        base = ident[len("gov.law."):]
        print(f"  metadata {ident}")
        try:
            meta = json.loads(get(f"https://archive.org/metadata/{ident}").decode("utf-8", "replace"))
        except Exception as e:
            print(f"    FAIL metadata: {type(e).__name__}")
            continue
        files = []
        for f in meta.get("files", []):
            name = f.get("name", "")
            if name.lower().endswith((".pdf", ".txt")) and not name.startswith("__"):
                files.append({
                    "name": name,
                    "bytes": int(f.get("size") or 0),
                    "kind": "pdf" if name.lower().endswith(".pdf") else "text",
                    "url": f"https://archive.org/download/{ident}/{name}",
                })
        files.sort(key=lambda x: (x["kind"] != "pdf", x["name"]))
        items.append({
            "item_id": ident,
            "code": base.replace(".pdf", ""),
            "title": (d.get("title") or [""])[0] if isinstance(d.get("title"), list) else (d.get("title") or ""),
            "files": files,
            "has_pdf": any(f["kind"] == "pdf" for f in files),
            "has_text": any(f["kind"] == "text" for f in files),
        })

    items.sort(key=lambda x: x["code"])
    payload = {
        "schema": "standards_kb.catalog/1.0",
        "source": "archive.org advancedsearch identifier:gov.law.asme.*",
        "note": ("每个 item 的 files 列出可直接下载的 PDF 与 OCR 文本层。"
                 "同名 item 的 PDF 是扫描件(常无文本层),抽公式优先用 _djvu.txt,"
                 "要版面坐标再取 PDF。"),
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {CATALOG.relative_to(ROOT)}  item {len(items)} 个")
    for it in items:
        flags = ("P" if it["has_pdf"] else "-") + ("T" if it["has_text"] else "-")
        print(f"  [{flags}] {it['code']:<28}{it['title'][:58]}")

    if args.find:
        pl = args.find.lower()
        print(f"--- '{pl}'")
        for it in items:
            if pl in it["code"].lower() or pl in it["title"].lower():
                print("  ", it["code"], "|", it["title"][:70])
                for f in it["files"]:
                    print(f"      {f['kind']:<5}{f['bytes']:>12,}  {f['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
