#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / fetch.py —— 取标准正文并登记

职责:
  1. 按 registry/sources.yaml 的 source id 取正文
  2. 算 SHA256 并落盘到 runs/<source_id>/
  3. 记录「实测拿到了没有」—— 拿不到就是拿不到,不美化
  4. 正文不落地到仓库(gitignore),只在 manifest 里登记摘要

用法:
  python fetch.py --list
  python fetch.py --source ASME-IA --file asme.b31.9.2008_djvu.txt
  python fetch.py --source GOST-MEGANORM --url https://.../x.pdf --file x.pdf
  python fetch.py --manifest          # 只看已登记的抓取结果
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from net_env import prepare_env  # noqa: E402
import provenance  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
REGISTRY = ROOT / "registry" / "sources.yaml"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CST = timezone(timedelta(hours=8))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry() -> dict:
    """极简 YAML 读取 —— 只取 sources 段需要的字段,避免引入 pyyaml 依赖。

    完整 YAML 解析请用 tools/registry_dump.py 生成的 registry.json。
    """
    reg = ROOT / "registry" / "registry.json"
    if reg.exists():
        return json.loads(reg.read_text(encoding="utf-8"))
    raise SystemExit(
        "找不到 registry/registry.json。先运行:\n"
        "  python tools/registry_dump.py"
    )


def fetch(url: str, timeout: int = 60) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def do_fetch(source_id: str, url: str, filename: str, note: str = "") -> dict:
    outdir = RUNS / source_id
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / filename

    if target.exists():
        digest = sha256_file(target)
        print(f"CACHED  {source_id}/{filename}  sha256={digest[:16]}...")
        return {
            "source_id": source_id, "url": url, "filename": filename,
            "sha256": digest, "bytes": target.stat().st_size,
            "status": "CACHED", "content_type": "", "note": note,
        }

    print(f"GET     {url}")
    try:
        code, body, ctype = fetch(url)
    except urllib.error.HTTPError as e:
        print(f"FAIL    HTTP {e.code}  {e.reason}")
        return {"source_id": source_id, "url": url, "filename": filename,
                "sha256": None, "bytes": 0, "status": f"HTTP_{e.code}",
                "content_type": "", "note": note}
    except Exception as e:
        print(f"FAIL    {type(e).__name__}: {e}")
        return {"source_id": source_id, "url": url, "filename": filename,
                "sha256": None, "bytes": 0, "status": "FETCH_ERROR",
                "content_type": "", "note": note, "error": str(e)}

    target.write_bytes(body)
    digest = sha256_file(target)
    print(f"OK      {code} {len(body):,} bytes -> {target.relative_to(ROOT)}")
    print(f"        sha256={digest}")
    return {
        "source_id": source_id, "url": url, "filename": filename,
        "sha256": digest, "bytes": len(body), "status": "OK",
        "content_type": ctype, "note": note,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="列出 registry 里的 source")
    ap.add_argument("--source", help="source id")
    ap.add_argument("--url", help="直接指定 URL(覆盖 registry)")
    ap.add_argument("--file", help="落盘文件名")
    ap.add_argument("--manifest", action="store_true", help="打印抓取清单")
    args = ap.parse_args()

    reg = load_registry()

    if args.list:
        for fam, fdata in reg.get("families", {}).items():
            print(f"\n[{fam}] {fdata.get('label','')}")
            for s in fdata.get("sources", []):
                print(f"  {s['id']:<18} {s.get('body_status',''):<18} {s['title'][:52]}")
        return 0

    if args.manifest:
        mf = RUNS / "fetch_manifest.json"
        if not mf.exists():
            print("还没有抓取清单。先跑 --source。")
            return 0
        print(mf.read_text(encoding="utf-8"))
        return 0

    if not args.source:
        ap.error("需要 --source 或 --list")

    # 找 source
    found = None
    for fdata in reg.get("families", {}).values():
        for s in fdata.get("sources", []):
            if s["id"] == args.source:
                found = s
    if not found:
        print(f"registry 里没有 source id: {args.source}")
        return 1

    url = args.url or found.get("url")
    if not url:
        print(f"{args.source} 没有可用 URL")
        return 1
    filename = args.file or os.path.basename(url.split("?")[0]) or "download.bin"

    # 代理自愈：本机常年挂着 FlClash(127.0.0.1:7890)，进程只剩守护服务时端口全灭，
    # 但系统 env 里的 HTTP_PROXY 还在 —— 任何尊重 env 的客户端都会静默走死代理，
    # 报 Connection refused(10061)，极易被误判成「对方站点挂了」。
    # 这里先探端口：不通就主动清掉残留 env，让请求直连。
    diag = prepare_env(verbose=True)
    if diag.get("action") == "dropped_dead_proxy_env":
        print(f"[fetch] 代理自愈：已清除 {diag['dropped']}，本次直连\n")

    rec = do_fetch(args.source, url, filename)

    # 正文台账由 provenance.py 独家维护（schema: standards_kb.fetch_manifest/1.0）。
    # 这里不再自己往 fetch_manifest.json 里塞 records —— 两个工具同文件不同 schema
    # 会互相踩，且会让 provenance --verify 读出假漂移。
    manifest = provenance.rebuild_manifest(load_registry())
    mf = provenance.write_manifest(manifest)
    print(f"\n已登记 -> {mf.relative_to(ROOT)}  (抓取结果 {rec['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
