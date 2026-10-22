#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全库扫描"拉丁/西里尔同形字混写"的隐患。

起因: build_docs.py 里 FAM_KEYS["GOST"] 的键写成 "Г + OCT"
      —— Г/О 是西里尔、C/T 是拉丁,肉眼与 "GOCT"/"GOST" 几乎无异。
      结果俄标匹配全线失灵,且肉眼 diff / grep / 打印都发现不了。

扫描规则:
  取文件里所有"词"(连续字母),若同时含拉丁字母和西里尔字母,
  则该词是混写 —— 几乎必然是 bug 或至少是极高风险。

纯西里尔词(比如 "ГОСТ")、纯拉丁词(比如 "ASME")都正常,不报。

用法: python tools/scan_homoglyphs.py [目录...]
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCAN_EXT = {".py", ".json", ".yaml", ".yml", ".md", ".txt", ".csv"}
SKIP_DIRS = {".git", "runs", "__pycache__", ".venv"}

# 西里尔 -> 拉丁 同形字（用于判断"这个西里尔字母长得像哪个拉丁字母"）
HOMO = {
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "Ѕ": "S",
    "І": "I", "Ј": "J", "Г": "G", "У": "Y",
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "т": "t", "х": "x", "у": "y", "к": "k", "м": "m", "в": "b",
    "н": "h", "і": "i", "ј": "j", "г": "r",
}

LATIN = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
CYR = set("АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя")
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def scan_file(p: Path) -> list[tuple[int, str, str]]:
    hits = []
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        for tok in TOKEN.findall(line):
            has_lat = any(c in LATIN for c in tok)
            has_cyr = any(c in CYR for c in tok)
            if not (has_lat and has_cyr):
                continue
            # 全部西里尔字母都能对上某个拉丁同形字 -> 可疑混写
            cyr_chars = [c for c in tok if c in CYR]
            disp = "".join(c if ord(c) < 128 else f"<U+{ord(c):04X}>" for c in tok)
            hits.append((lineno, tok, disp))
    return hits


def main() -> int:
    roots = [Path(a) for a in sys.argv[1:]] or [ROOT]
    total = 0
    files_hit = 0
    for root in roots:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in SCAN_EXT:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            hits = scan_file(p)
            if not hits:
                continue
            files_hit += 1
            rel = p.relative_to(ROOT) if str(p).startswith(str(ROOT)) else p
            print(f"\n{rel}")
            seen = set()
            for lineno, tok, disp in hits:
                key = (tok, disp)
                if key in seen:
                    continue
                seen.add(key)
                total += 1
                lat = [c for c in tok if c in LATIN]
                cyr = [c for c in tok if c in CYR]
                print(f"  L{lineno:<5} {disp:<46} 拉丁部分={''.join(lat)} 西里尔部分={''.join(cyr)}")
    print(f"\n共 {files_hit} 个文件命中 {total} 处混写")
    if total:
        print("提示: 混写词几乎必然是 bug —— 肉眼与纯拉丁/纯西里尔版本无法区分。")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
