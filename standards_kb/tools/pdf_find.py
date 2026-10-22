#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_find.py — 在 PDF 文本层里搜索正则，返回命中页码与命中行。

为什么需要它
------------
候选池里的 `line_no` 指向的是 **djvu/OCR 文本层**的行号，不是 PDF 页码。
要升级成正式条目必须：(1) 找到该公式真实所在页；(2) 把那一页渲染成图肉眼核对。
没有「文本层 → 页码」的桥，这两步只能靠人肉翻页。

同时它也是一道**保真自检**：文本层说某公式在第 N 页，若 PDF 文本层在该页找不到
同样的字符串，说明 OCR 层与版面层已经不一致，条目不能标 VERIFIED_CLAUSE。

用法
----
  python tools/pdf_find.py --pdf runs/ASME-B31.1/asme_b31_1_2007.pdf --re "carbon equivalent"
  python tools/pdf_find.py --pdf <pdf> --re "<re>" --show   # 同时打印命中行上下文
  python tools/pdf_find.py --pdf <pdf> --text "CE = C +"     # 按整串查找

退出码：0 = 有命中，1 = 无命中，2 = 文件/参数错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def iter_pages(doc, pattern: str | None, text: str | None):
    rx = re.compile(pattern) if pattern else None
    for pno in range(doc.page_count):
        page = doc[pno]
        page_text = page.get_text("text")
        if text is not None:
            if text in page_text:
                yield pno + 1, [(i, ln) for i, ln in enumerate(page_text.splitlines()) if text in ln]
            continue
        hits = []
        for i, ln in enumerate(page_text.splitlines()):
            if rx.search(ln):
                hits.append((i, ln))
        if hits:
            yield pno + 1, hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--re", dest="pattern", help="正则模式")
    ap.add_argument("--text", help="整串查找（与 --re 二选一）")
    ap.add_argument("--show", action="store_true", help="打印命中行及上下文")
    ap.add_argument("--ctx", type=int, default=2, help="--show 的上下文行数")
    ap.add_argument("--max-hits", type=int, default=40, help="最多打印多少条命中")
    args = ap.parse_args()

    if not (args.pattern or args.text):
        print("必须给 --re 或 --text 其中之一")
        return 2

    pdf = Path(args.pdf)
    if not pdf.is_absolute():
        pdf = ROOT / pdf
    if not pdf.exists():
        print(f"找不到 PDF: {pdf}")
        return 2

    import pymupdf

    doc = pymupdf.open(pdf)
    total = 0
    pages = 0
    for pno, hits in iter_pages(doc, args.pattern, args.text):
        pages += 1
        total += len(hits)
        print(f"[PDF 第 {pno} 页] 命中 {len(hits)} 行")
        if args.show:
            full = doc[pno - 1].get_text("text").splitlines()
            for i, ln in hits[: args.max_hits]:
                lo = max(0, i - args.ctx)
                hi = min(len(full), i + args.ctx + 1)
                for k in range(lo, hi):
                    mark = ">>" if k == i else "  "
                    print(f"{mark}  {full[k]}")
                print("  " + "-" * 60)

    print(f"\n合计：{pages} 页命中，{total} 行")
    if pages == 0:
        print("提示：PDF 可能只有图像没有文本层，需要 OCR 后再定位。")
    return 0 if pages else 1


if __name__ == "__main__":
    raise SystemExit(main())
