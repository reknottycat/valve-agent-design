#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / fetch_many.py —— 批量取正文并逐份登记

比逐个跑 fetch.py 快,适合一次补一批标准。
每一份都单独算 SHA256、单独写台账,失败不中断其它项,失败就如实记 FAIL。

用法:
  python fetch_many.py --file plan.json
  python fetch_many.py --file plan.json --jobs 4
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CST = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def one(job: dict) -> dict:
    sid = job["source_id"]
    url = job["url"]
    fname = job.get("file") or url.rsplit("/", 1)[-1].split("?")[0]
    out = RUNS / sid
    out.mkdir(parents=True, exist_ok=True)
    target = out / fname

    if target.exists() and target.stat().st_size > 0:
        return {"source_id": sid, "filename": fname, "url": url,
                "sha256": sha256_file(target), "bytes": target.stat().st_size,
                "status": "CACHED", "note": job.get("note", "")}

    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
            code = r.status
    except urllib.error.HTTPError as e:
        return {"source_id": sid, "filename": fname, "url": url, "sha256": None,
                "bytes": 0, "status": f"HTTP_{e.code}", "note": job.get("note", "")}
    except Exception as e:
        return {"source_id": sid, "filename": fname, "url": url, "sha256": None,
                "bytes": 0, "status": "FETCH_ERROR", "error": f"{type(e).__name__}: {e}",
                "note": job.get("note", "")}

    target.write_bytes(body)
    return {"source_id": sid, "filename": fname, "url": url,
            "sha256": sha256_file(target), "bytes": len(body),
            "status": "OK", "content_type": ctype, "note": job.get("note", "")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True, help="计划文件(JSON 数组)")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()

    plan = json.loads(Path(args.file).read_text(encoding="utf-8"))
    results = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(one, j): j for j in plan}
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            mark = {"OK": "OK  ", "CACHED": "CACHED"}.get(r["status"], "FAIL")
            print(f"[{mark}] {r['source_id']:<16}{r['filename']:<34}"
                  f"{r['bytes']:>12,}  {r['status']}")

    mf = RUNS / "fetch_manifest_raw.json"
    old = {}
    if mf.exists():
        try:
            old = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old = {}
    recs = old.get("records", [])
    keys = {(r["source_id"], r["filename"]) for r in results}
    recs = [r for r in recs if (r["source_id"], r["filename"]) not in keys]
    recs += results
    mf.write_text(json.dumps({
        "updated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "records": sorted(recs, key=lambda r: (r["source_id"], r["filename"])),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for r in results if r["status"] in ("OK", "CACHED"))
    print(f"\n{ok}/{len(results)} 成功 -> {mf.relative_to(ROOT)}")
    print("提示: 跑 provenance.py 刷新台账")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
