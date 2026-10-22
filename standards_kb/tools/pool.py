#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / pool.py —— 把各标准抽出的候选公式汇成「待复核池」

为什么要有池子
--------------
抽取器一次能出几十上百条候选,但每条都可能是表格值、符号定义、OCR 噪声。
池子解决三件事:

  1. 累积: 每次重跑抽取器,候选都进同一个池,带**稳定 ID**(内容哈希),
     不会因为重新抽取而丢失复核进度。
  2. 可追溯: 每条候选都带 source_id / 页码 / 行号 / 上下文原文。
  3. 可交接: 复核结论存在 kb/candidates/reviewed.json 里,
     人工或 Agent 标注「采纳→正式条目 ID」或「否决→理由」,
     下次跑不会丢。

产出:
  kb/candidates/pool.json          全池(按标准分组)
  kb/candidates/<source_id>.json   单标准切片
  kb/candidates/reviewed.json       复核记录(本工具只读,不覆盖)

用法:
  python pool.py             # 汇总
  python pool.py --stats     # 只看统计
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
POOL_DIR = ROOT / "kb" / "candidates"
REGISTRY = ROOT / "registry" / "registry.json"
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def canonical_ids() -> dict[str, str]:
    """小写目录名 -> registry 里的规范 source_id。

    为什么需要: runs/ 下的目录名历史上出现过大小写漂移
    (ASME-BPvc-I -> ASME-BPVC-I)。若 pool_id 直接用目录名,
    改个名就等于换了一批 ID,复核进度全丢。
    以 registry 为准做一次规范化,ID 就与目录名解耦。
    """
    if not REGISTRY.exists():
        return {}
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, str] = {}
    for fam in (data.get("families") or {}).values():
        for s in fam.get("sources") or []:
            sid = s.get("id")
            if sid:
                out[sid.lower()] = sid
    return out


def resolve_source_id(dir_name: str, table: dict[str, str]) -> str:
    """目录名 -> 规范 id。registry 里没有就沿用目录名(并保持原样)。"""
    if dir_name.lower() in table:
        return table[dir_name.lower()]
    return dir_name


def stable_id(source_id: str, page, line_no, expr: str) -> str:
    raw = f"{source_id}|{page}|{line_no}|{expr}".encode("utf-8")
    return "C-" + hashlib.sha256(raw).hexdigest()[:12]


def load_items(path: Path) -> tuple[list[dict], str]:
    """兼容两种抽取产物: 纯 list, 或带 candidates/formulas 键的 dict。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, "list"
    for key in ("candidates", "formulas", "items"):
        if isinstance(data.get(key), list):
            return data[key], key
    return [], "none"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    reviewed_path = POOL_DIR / "reviewed.json"
    reviewed = {}
    if reviewed_path.exists():
        try:
            reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            reviewed = {}

    by_std: dict[str, list[dict]] = {}
    id_table = canonical_ids()
    for d in sorted(RUNS.iterdir()) if RUNS.exists() else []:
        if not d.is_dir():
            continue
        source_id = resolve_source_id(d.name, id_table)
        for f in sorted(d.glob("*candidates.json")):
            try:
                items, shape = load_items(f)
            except (json.JSONDecodeError, OSError):
                continue
            if not items:
                continue
            extractor = "extract_pdf" if "pdfcandidates" in f.name else "extract"
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    continue
                expr = (it.get("expr") or "").strip()
                if not expr:
                    continue
                pid = stable_id(source_id, it.get("page"), it.get("line_no"), expr)
                rec = {
                    "pool_id": pid,
                    "source_id": source_id,
                    "extractor": extractor,
                    "page": it.get("page"),
                    "line_no": it.get("line_no"),
                    "expr": expr,
                    "lhs": it.get("lhs"),
                    "rhs": it.get("rhs"),
                    "domain": it.get("domain"),
                    "ocr_degraded": bool(it.get("ocr_degraded")),
                    "confidence": it.get("confidence") or "LOW",
                    "context": (it.get("context") or "")[:1200],
                    "status": "CANDIDATE",
                    "promoted_to": None,
                }
                rv = reviewed.get(pid)
                if rv:
                    rec["status"] = rv.get("status", "CANDIDATE")
                    rec["promoted_to"] = rv.get("promoted_to")
                    rec["review_note"] = rv.get("note")
                by_std.setdefault(source_id, []).append(rec)

    total = sum(len(v) for v in by_std.values())
    promoted = sum(1 for v in by_std.values() for c in v if c["promoted_to"])
    rejected = sum(1 for v in by_std.values() for c in v if c["status"] == "REJECTED")

    if args.stats:
        print(f"候选池 {total} 条 | 已采纳 {promoted} | 已否决 {rejected} | 待复核 {total-promoted-rejected}")
        for sid, items in by_std.items():
            print(f"  {sid:<18}{len(items):>5} 条")
        return 0

    POOL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "standards_kb.candidate_pool/1.0",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "note": ("候选 = 抽取器自动发现但未经确认的公式行。全部 confidence=LOW,"
                 "OCR 来源另有 ocr_degraded 标记。复核结论写入 reviewed.json,"
                 "pool_id 稳定(内容哈希),重跑抽取不丢进度。"),
        "counts": {"total": total, "promoted": promoted,
                   "rejected": rejected, "pending": total - promoted - rejected},
        "by_standard": {k: v for k, v in by_std.items()},
    }
    (POOL_DIR / "pool.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for sid, items in by_std.items():
        (POOL_DIR / f"{sid}.json").write_text(json.dumps({
            "source_id": sid,
            "generated_at": payload["generated_at"],
            "count": len(items),
            "candidates": items,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清理陈旧切片: 目录改名后旧切片仍在,会造成「同一标准两个文件」的错觉
    keep = {f"{sid}.json" for sid in by_std} | {"pool.json", "reviewed.json"}
    for stale in POOL_DIR.glob("*.json"):
        if stale.name not in keep:
            stale.unlink()
            print(f"   清理陈旧切片: {stale.name}")

    print(f"-> kb/candidates/pool.json   候选 {total} 条")
    for sid, items in by_std.items():
        print(f"   {sid:<18}{len(items):>5}")
    print(f"已采纳 {promoted} | 已否决 {rejected} | 待复核 {total-promoted-rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
