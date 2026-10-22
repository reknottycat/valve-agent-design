#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""standards_kb / enc_probe.py —— 判定文本文件的真实编码(避免中文 Windows 的 CP936 误读)。"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CAND = ["utf-8", "cp1251", "utf-16", "cp936", "latin-1"]


def score(data: bytes, enc: str) -> float:
    try:
        t = data.decode(enc)
    except Exception:
        return -1.0
    if not t:
        return -1.0
    bad = t.count("\ufffd")
    # 控制字符(除 \t \n \r)越少越好
    ctrl = sum(1 for c in t if ord(c) < 32 and c not in "\t\n\r")
    return (len(t) / max(len(data), 1)) * (1 - (bad + ctrl) / max(len(t), 1))


def main() -> int:
    for arg in sys.argv[1:]:
        p = Path(arg)
        data = p.read_bytes()
        print(f"=== {p.name}  {len(data):,} bytes")
        rows = []
        for enc in CAND:
            s = score(data, enc)
            if s >= 0:
                rows.append((s, enc))
        rows.sort(reverse=True)
        for s, enc in rows[:3]:
            t = data.decode(enc, "replace")
            preview = "".join(c if c.isprintable() or c in "\n\t" else "." for c in t[:220])
            print(f"  {enc:<10} score={s:.4f}  {preview[:200]}")
        # UTF-8 尝试下的西里尔字母占比
        try:
            t8 = data.decode("utf-8", "replace")
            cyr = sum(1 for c in t8 if "\u0400" <= c <= "\u04FF")
            cjk = sum(1 for c in t8 if "\u4E00" <= c <= "\u9FFF")
            print(f"  utf8 下: 西里尔 {cyr} 字, 汉字 {cjk} 字")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
