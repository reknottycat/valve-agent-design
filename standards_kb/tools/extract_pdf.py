#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / extract_pdf.py —— 基于 PDF 版面坐标的公式抽取

为什么需要这个:
  OCR 文本层(djvu.txt)把表格和公式拆成无序散片,单行/跨行拼接只能捞到骨架。
  但 PDF 本身带版面信息: 文字块坐标、字号、方向、行间距。
  同一个"行"(同一 baseline、同一字号、水平相邻)的文字块才是一行公式。

做法:
  1. pymupdf 提取文字块 + 坐标 + 字号
  2. 按 y 聚类成"行"(容差按字号自适应)
  3. 同一行内按 x 排序拼回,保留块间空格
  4. 再做公式判定

效果: 表格里的公式会按行重建,不再散成碎片。

用法:
  python extract_pdf.py --source ASME-BPvc-I --pdf <path.pdf>
  python extract_pdf.py --source X --pdf a.pdf --pages 200-260
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 从 extract.py 复用判定与归一逻辑(同目录 import)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import (  # noqa: E402
    EQ_RE, NOT_FORMULA, UNIT_ONLY, guess_domain, normalize_expr,
    normalize_symbols,
)


def rows_from_page(page, y_tol_ratio: float = 0.55):
    """把一页的文字块按 y 聚成行,行内按 x 排序。

    返回 [(y_center, [ (x0, text, size), ... ]), ...]
    """
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        return []

    items = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans)
            if not text.strip():
                continue
            size = max((s.get("size", 0) for s in spans), default=0)
            x0 = line.get("bbox", (0, 0, 0, 0))[0]
            y0 = line.get("bbox", (0, 0, 0, 0))[1]
            items.append((y0, x0, text, size))

    if not items:
        return []

    sizes = [it[3] for it in items if it[3] > 0]
    base = sorted(sizes)[len(sizes) // 2] if sizes else 10.0
    tol = max(1.5, base * y_tol_ratio * 0.5)

    items.sort(key=lambda t: (t[0], t[1]))
    rows = []
    cur = []
    cur_y = None
    for y0, x0, text, size in items:
        if cur_y is None or abs(y0 - cur_y) <= tol:
            cur.append((x0, text, size))
            cur_y = y0 if cur_y is None else cur_y
        else:
            rows.append(cur)
            cur = [(x0, text, size)]
            cur_y = y0
    if cur:
        rows.append(cur)

    out = []
    for row in rows:
        row.sort(key=lambda t: t[0])
        out.append((row[0][0], row))
    return out


def join_row(cells) -> str:
    """行内拼接: 相邻块之间补空格(OCR 常吞空格)。"""
    parts = []
    prev_x1 = None
    for x0, text, size in cells:
        t = text.strip()
        if not t:
            continue
        if prev_x1 is not None:
            parts.append(" ")
        parts.append(t)
        prev_x1 = x0
    return " ".join(parts)


def extract_pdf(pdf_path: Path, pages_spec: str | None = None) -> tuple[list[dict], int]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    if pages_spec:
        if "-" in pages_spec:
            a, b = pages_spec.split("-")
            lo, hi = int(a), int(b)
        else:
            lo = hi = int(pages_spec)
        lo = max(0, lo - 1)
        hi = min(doc.page_count, hi)
        idxs = range(lo, hi)
    else:
        idxs = range(doc.page_count)

    cands: list[dict] = []
    seen: set[str] = set()

    for pi in idxs:
        page = doc[pi]
        rows = rows_from_page(page)
        row_texts = [join_row(cells) for _, cells in rows]

        for ri, s in enumerate(row_texts):
            t = s.strip()
            if not t or len(t) < 4 or len(t) > 400:
                continue
            if UNIT_ONLY.match(t):
                continue
            m = EQ_RE.match(t)
            if not m:
                continue
            lhs = m.group(1).strip()
            if lhs.lower() in NOT_FORMULA:
                continue
            rhs = m.group(2).strip()
            if not rhs:
                continue
            if not re.search(r"[\d\(\+\-\*/^√π]|sqrt|log|exp", rhs, re.IGNORECASE):
                continue
            if re.match(r"^(fig|figure|table|note|see|para|sec)\b", t, re.IGNORECASE):
                continue
            has_op = bool(re.search(r"[\+\-\*/\^]", rhs))
            if not has_op:
                if len(rhs.split()) >= 4:
                    continue
                if not re.search(r"\d", rhs):
                    continue

            norm = normalize_expr(normalize_symbols(t))
            if norm in seen:
                continue
            seen.add(norm)

            ctx_lo = max(0, ri - 2)
            ctx_hi = min(len(row_texts), ri + 3)
            cands.append({
                "expr": norm,
                "lhs": normalize_symbols(m.group(1)).strip(),
                "rhs": normalize_symbols(rhs).strip(),
                "page": pi + 1,
                "line_no": ri + 1,
                "context": "\n".join(row_texts[ctx_lo:ctx_hi]).strip()[:600],
                "domain": guess_domain("\n".join(row_texts[ctx_lo:ctx_hi])),
                "ocr_degraded": bool(re.search(r"\b(Sc|SE|Sa|Sm|Sy|Su|St)\b", t)),
                "confidence": "LOW",
                "form": "pdf_layout_row",
            })

    return cands, doc.page_count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--pdf", required=True, help="PDF 路径")
    ap.add_argument("--pages", help="页范围,如 200-260")
    ap.add_argument("--out", help="输出文件名")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        pdf = RUNS / args.source / args.pdf
    if not pdf.exists():
        print(f"找不到 PDF: {args.pdf}")
        return 1

    print(f"解析 {pdf} ...")
    cands, npages = extract_pdf(pdf, args.pages)
    print(f"  共 {npages} 页,候选 {len(cands)} 条")

    out_name = args.out or f"{args.source}__pdfcandidates.json"
    outdir = pdf.parent
    out = {
        "schema": "standards_kb.candidates/1.0",
        "method": "pdf_layout_row",
        "source_id": args.source,
        "pdf": str(pdf.relative_to(ROOT)) if ROOT in pdf.parents else str(pdf),
        "pages_scanned": npages,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "candidate_count": len(cands),
        "note": "基于 PDF 版面坐标重建行。仍为 CANDIDATE/LOW,须复核。",
        "candidates": cands,
    }
    (outdir / out_name).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    by_dom: dict[str, int] = {}
    for c in cands:
        by_dom[c["domain"]] = by_dom.get(c["domain"], 0) + 1
    print("按域:", ", ".join(f"{k}={v}" for k, v in sorted(by_dom.items(), key=lambda x: -x[1])))
    print(f"-> {(outdir / out_name)}")
    print("\n前 15 条:")
    for c in cands[:15]:
        print(f"  p{c['page']:<5} {c['domain']:<7} {c['expr'][:86]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
