#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / probe_gb_body.py —— 探测目录里哪些 GB/T 标准**真的有免费在线正文**

为什么需要这个
--------------
`kb/catalog/gb_openstd.json` 有 1197 条标准，但「在目录里」≠「正文免费开放」。
国标全文公开系统只对**部分**标准开放在线预览，���的跳 404。

这层探测产出一张**可复用资产**：
  kb/catalog/gb_body_availability.json
  ��� hcno -> {standard_no, title_zh, status, body_status, page_count, probe_at}
body_status 取值：
  OPEN_BODY   在线正文可取（已验证 showGb 返回 div.page）
  NO_BODY     站点 404，该标准无免费在线正文
  ERROR       其他错误（网络/限流），下次可重试

用法
----
  python probe_gb_body.py                      # 探全部 1197 条
  python probe_gb_body.py --limit 40           # 只探前 40 条（试水）
  python probe_gb_body.py --only-valence       # 只探目录里 阀门/法兰/压力管道 相关
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "kb" / "catalog" / "gb_openstd.json"
OUT = ROOT / "kb" / "catalog" / "gb_body_availability.json"

BASE = "https://openstd.samr.gov.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_entries() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    std = data.get("standards") or {}
    out = []
    for hcno, rec in std.items():
        r = dict(rec)
        r["hcno"] = r.get("hcno") or hcno
        out.append(r)
    return out


class Sess:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

    def probe(self, hcno: str) -> dict:
        ni = f"{BASE}/bzgk/std/newGbInfo?hcno={hcno}"
        try:
            self.op.open(urllib.request.Request(ni, headers=self.h), timeout=45).read()
            show = f"{BASE}/bzgk/std/showGb?type=online&hcno={hcno}"
            r = self.op.open(
                urllib.request.Request(show, headers={**self.h, "Referer": ni}),
                timeout=90)
            html = r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"body_status": "NO_BODY"}
            return {"body_status": "ERROR", "error": f"HTTP_{e.code}"}
        except Exception as e:
            return {"body_status": "ERROR", "error": f"{type(e).__name__}: {e}"}

        m = re.search(r"var\s+page\s*=\s*(\d+)", html)
        n = int(m.group(1)) if m else 0
        has = bool(re.search(r'<div id="\d+" class="page"', html))
        if not has:
            return {"body_status": "NO_BODY",
                    "note": "showGb 200 但无 div.page（骨架页）"}
        return {"body_status": "OPEN_BODY", "page_count": n}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="只探前 N 条")
    ap.add_argument("--only-valence", action="store_true",
                    help="只探阀门/法兰/压力管道/密封/紧固件 相关")
    ap.add_argument("--delay", type=float, default=0.35, help="每条间隔秒")
    ap.add_argument("--resume", action="store_true", help="跳过已探测过的条目")
    args = ap.parse_args()

    prepare_env(verbose=True)

    entries = load_entries()
    if args.only_valence:
        kw = ("阀", "法兰", "压力管道", "密封", "螺栓", "紧固件", "管路")
        entries = [e for e in entries
                   if any(k in (e.get("title_zh") or "") for k in kw)]
    if args.limit:
        entries = entries[:args.limit]

    prev: dict = {}
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8")).get("standards", {})
    if args.resume:
        # 只跳过**终态**条目（OPEN_BODY / NO_BODY）。ERROR 是网络异常导致的未完成，
        # 必须重试 —— 否则「重跑 --resume 可补」这句话是假的。
        # 404 属于确定性结论（NO_BODY），不属于 ERROR，重试没有意义。
        terminal = {"OPEN_BODY", "NO_BODY"}
        retry = [h for h, r in prev.items() if r.get("body_status") not in terminal]
        entries = [e for e in entries
                   if e["hcno"] not in prev or prev[e["hcno"]].get("body_status") not in terminal]
        print(f"resume: 跳过已探终态 {len(prev) - len(retry)} 条，"
              f"待探 {len(entries)} 条（含 {len(retry)} 条重试）")

    print(f"待探测 {len(entries)} 条")
    sess = Sess()
    out = dict(prev)
    # run_tally 只统计**本次运行**处理的条目，用于进度显示；
    # 落盘的 tally 必须由 out 全量重算 —— 否则 --resume 时台账里的计数
    # 会小于 standards 里的实际条数（实测台账写 57/926/8，records 实际 60/934/9）。
    run_tally = {"OPEN_BODY": 0, "NO_BODY": 0, "ERROR": 0}
    t0 = time.time()

    def derive_tally(records: dict) -> dict:
        t = {"OPEN_BODY": 0, "NO_BODY": 0, "ERROR": 0}
        for r in records.values():
            k = r.get("body_status", "ERROR")
            t[k] = t.get(k, 0) + 1
        return t

    for i, e in enumerate(entries, 1):
        res = sess.probe(e["hcno"])
        rec = {
            "standard_no": e.get("standard_no", ""),
            "title_zh": e.get("title_zh", ""),
            "status": e.get("status", ""),
            "publish_date": e.get("publish_date", ""),
            "body_status": res["body_status"],
            "probe_at": datetime.now(CST).isoformat(timespec="seconds"),
        }
        if "page_count" in res:
            rec["page_count"] = res["page_count"]
        if "error" in res:
            rec["error"] = res["error"]
        out[e["hcno"]] = rec
        run_tally[res["body_status"]] = run_tally.get(res["body_status"], 0) + 1

        if i % 25 == 0 or i == len(entries):
            el = time.time() - t0
            cum = derive_tally(out)
            print(f"  [{i}/{len(entries)}] 本次 开放={run_tally['OPEN_BODY']} "
                  f"无正文={run_tally['NO_BODY']} 错误={run_tally['ERROR']}"
                  f" | 累计 开放={cum['OPEN_BODY']} 无正文={cum['NO_BODY']} "
                  f"错误={cum['ERROR']} 用时 {el:.0f}s")

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "schema": "standards_kb.gb_body_availability/1.0",
            "probed_at": datetime.now(CST).isoformat(timespec="seconds"),
            "scope": "only_valence" if args.only_valence else "all_catalog",
            "tally": derive_tally(out),
            "standards": out,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        time.sleep(args.delay)

    final = derive_tally(out)
    print(f"\n完成 -> {OUT.relative_to(ROOT)}")
    print(f"  全量 {len(out)} 条：开放正文 {final['OPEN_BODY']} / "
          f"无正文 {final['NO_BODY']} / 错误 {final['ERROR']}")
    if final["ERROR"]:
        print(f"  提示：{final['ERROR']} 条因网络异常未探到，重跑 --resume 可补。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
