#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
show_lines.py — 按行号查看标准文本层，用于条款号复核。

为什么需要它：
    候选池里每条候选都带 `line_no`（djvu 文本层行号）。要把它升级成正式
    条目，必须能回到原文确认 (a) 公式本身、(b) 所属段落号、(c) 适用条件。
    人工反复翻 1.1 MB 的 txt 很慢，这个工具把「定位 → 读上下文」压缩成一条命令。

用法：
    python tools/show_lines.py <文件> <起> [止]
    python tools/show_lines.py <文件> --grep <正则> [--ctx N]

示例：
    python tools/show_lines.py runs/ASME-B31.1/asme_b31_1_2007_djvu.txt 15370 15410
    python tools/show_lines.py runs/ASME-B31.4/asme_b31_4_2002_djvu.txt --grep "reinforcement area required" --ctx 6

输出约定：
    - 每行前缀 `[行号]`，行号从 1 开始（与候选池 line_no 对齐方式：候选池记的是
      0 基索引，本工具同时打印 0 基索引列，便于直接回查候选记录）。
    - 所有输出强制 UTF-8，避免 Windows CP936 控制台抛 UnicodeEncodeError。
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def cmd_range(lines: list[str], start: int, end: int) -> None:
    n = len(lines)
    # 1 基输入 → 0 基切片
    lo = max(1, start)
    hi = min(n, end if end >= start else start)
    for i in range(lo - 1, hi):
        print(f"[{i + 1:>7} | idx {i:>7}] {lines[i]}")


def cmd_grep(lines: list[str], pattern: str, ctx: int) -> None:
    rx = re.compile(pattern, re.IGNORECASE)
    hits = [i for i, ln in enumerate(lines) if rx.search(ln)]
    if not hits:
        print(f"(无匹配: {pattern})")
        return
    print(f"命中 {len(hits)} 处，模式: {pattern}\n")
    shown = set()
    for h in hits:
        lo = max(0, h - ctx)
        hi = min(len(lines), h + ctx + 1)
        if any(k in shown for k in range(lo, hi)):
            continue
        for k in range(lo, hi):
            if k in shown:
                continue
            shown.add(k)
            mark = ">>" if k == h else "  "
            print(f"{mark}[{k + 1:>7} | idx {k:>7}] {lines[k]}")
        print("-" * 70)


def main() -> int:
    ap = argparse.ArgumentParser(description="按行号/正则查看标准文本层")
    ap.add_argument("file", help="文本层文件路径（通常是 runs/<STD>/*.txt）")
    ap.add_argument("start", nargs="?", type=int, help="起始行（1 基）")
    ap.add_argument("end", nargs="?", type=int, help="结束行（1 基，含）")
    ap.add_argument("--grep", help="正则搜索模式")
    ap.add_argument("--ctx", type=int, default=3, help="--grep 的上下文行数（默认 3）")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"文件不存在: {path}")
        return 1

    lines = load_lines(path)
    if args.grep:
        cmd_grep(lines, args.grep, args.ctx)
    elif args.start is not None:
        cmd_range(lines, args.start, args.end if args.end is not None else args.start)
    else:
        print(json.dumps({"file": str(path), "lines": len(lines)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
