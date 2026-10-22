#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / crop_pdf.py —— 把 PDF 指定页的指定行渲染成 PNG，供肉眼核对公式

为什么需要
----------
OCR 文本层与版面层都会退化：
  - 根号 √  → "7" / "1" / "j"
  - 下标 1  → "I"
  - 数字 5  → "S"
  - 系数 0.15 → "O.IS"
逐字记录退化后的文本只能做到 PENDING_VERIFICATION。
把原文渲染成图片直接看，才能把「不确定」升级为「已核」。

用法
----
  python crop_pdf.py --pdf runs/ASME-BPVC-I/bpvc_i.pdf --page 241 \
      --match "Z1 =|Z2 =" --out runs/probe/z1z2.png --pad 8 --dpi 300
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_line_bands(page, pattern: str, pad: float = 8.0):
    """在页面上找匹配的行，返回其 bbox 带（已按 pad 扩展）。"""
    import pymupdf

    rx = re.compile(pattern)
    bands = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans)
            if rx.search(text):
                x0, y0, x1, y1 = line["bbox"]
                bands.append((x0, y0, x1, y1, text.strip()))
    if not bands:
        return []
    bands.sort(key=lambda t: t[1])
    return bands


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True, help="PDF 页码（1 起）")
    ap.add_argument("--match", required=True, help="行内匹配正则")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=float, default=8.0, help="上下留白 pt")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--x0", type=float, default=None, help="裁切左界 pt")
    ap.add_argument("--x1", type=float, default=None, help="裁切右界 pt")
    ap.add_argument("--row-hint", type=float, default=None,
                    help="只保留命中行附近 ±N pt（需配合 --x0/--x1）")
    args = ap.parse_args()

    import pymupdf

    pdf = Path(args.pdf)
    if not pdf.is_absolute():
        pdf = ROOT / pdf
    if not pdf.exists():
        print(f"找不到 PDF: {pdf}")
        return 1

    doc = pymupdf.open(pdf)
    page = doc[args.page - 1]
    bands = find_line_bands(page, args.match, args.pad)
    if not bands:
        print(f"第 {args.page} 页没有匹配 {args.match!r} 的行")
        return 1

    print(f"命中 {len(bands)} 行：")
    for x0, y0, x1, y1, t in bands:
        print(f"  y={y0:7.1f}..{y1:7.1f}  {t[:110]}")

    # 把所有命中行合成一个纵向带（中间不断开，便于看上下文连续）
    if args.row_hint is not None and len(bands) > 1:
        # 只保留命中行之间连续、间距小于 row_hint 的那一段
        groups: list[list] = [[bands[0]]]
        for b in bands[1:]:
            if b[1] - groups[-1][-1][1] <= args.row_hint:
                groups[-1].append(b)
            else:
                groups.append([b])
        # 取包含命中最多的一段
        groups.sort(key=lambda g: -len(g))
        bands = groups[0]

    y_top = max(0.0, min(b[1] for b in bands) - args.pad)
    y_bot = min(page.rect.height, max(b[3] for b in bands) + args.pad)
    x0 = args.x0 if args.x0 is not None else 0.0
    x1 = args.x1 if args.x1 is not None else page.rect.width
    clip = pymupdf.Rect(x0, y_top, x1, y_bot)

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    pix = page.get_pixmap(dpi=args.dpi, clip=clip)
    pix.save(out)
    print(f"-> {out.relative_to(ROOT)}  {pix.width}x{pix.height}px  clip={clip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
