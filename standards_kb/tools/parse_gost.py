#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / parse_gost.py —— 把 ГОСТ 正文的表格抽成结构化 JSON

输入是项目内 gost1536/parse.py 产出的扁平文本(UTF-8),格式:

    TEXT: <段落>
    === TABLE (16 rows) ===
    表头第1行 | ...
    表头第2行 | ...
    20 | 95 | 65 | 42 | ...
    === END TABLE ===

站点装饰(搜索框、广告、导航)会被识别并剔除 —— 那些不是标准内容。

产出:
    kb/data/raw/gost_1536_76_tables.json   结构化表(含上下文句)
    runs/GOST-LOCAL/gost_1536_76_clean.md  干净可读版(俄文原文)

用法:
  python parse_gost.py <gost.txt> <out.json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TABLE_RE = re.compile(r"^=== TABLE \((\d+) rows\) ===$")
END_RE = re.compile(r"^=== END TABLE ===$")

# 站点装饰特征 —— 命中即判为非标准内容
CHROME_MARKERS = [
    "Поиск по реквизитам", "Показать все найденные", "Упорядочить по номеру",
    "Ya.Context.AdvManager", "renderTo:", "Искать все виды документов",
    "База 1", "База 2", "База 3", "На главную",
]


def is_chrome(text: str) -> bool:
    return any(m in text for m in CHROME_MARKERS)


def split_row(line: str) -> list[str]:
    parts = [p.strip() for p in line.split("|")]
    return [p for p in parts]


def parse(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    tables: list[dict] = []
    i = 0
    last_text = ""
    while i < len(lines):
        line = lines[i].rstrip()
        m = TABLE_RE.match(line)
        if not m:
            if line.startswith("TEXT:"):
                last_text = line[5:].strip()
            i += 1
            continue

        declared = int(m.group(1))
        i += 1
        rows: list[list[str]] = []
        raw_lines = 0
        while i < len(lines) and not END_RE.match(lines[i].rstrip()):
            raw = lines[i]
            if raw.strip():
                raw_lines += 1
                if not is_chrome(raw):
                    rows.append(split_row(raw))
            i += 1
        i += 1  # skip END

        if not rows or is_chrome(last_text):
            continue

        # 找数据起始行: 第一列能解析为数字的位置
        data_start = None
        for idx, r in enumerate(rows):
            if not r:
                continue
            first = r[0].replace(",", ".").strip()
            if re.fullmatch(r"\d+(\.\d+)?", first):
                data_start = idx
                break
        if data_start is None:
            continue

        header = [r for r in rows[:data_start] if r]
        data = [r for r in rows[data_start:] if r]

        tables.append({
            "index": len(tables) + 1,
            "declared_rows": declared,
            "parsed_rows": len(rows),
            "header_rows": header,
            "data_rows": data,
            "context": last_text[-600:],
            "context_head": last_text[:300],
        })
    return tables


def merged_header(header_rows: list[list[str]]) -> list[str]:
    """把多行表头拼成一行。

    ГОСТ 1536-76 的表头是两行合并结构:第一行是组名
    (如 'Ру, МПа, не более' / 'Размеры, мм'),第二行才是子列名
    (D / D1 / D2 / ...)。只取最后一行会把列数砍掉一半 ——
    表 6/7 有 11 列,只取末行只剩 2 列,数据行因此被截断。
    """
    if not header_rows:
        return []
    width = max(len(r) for r in header_rows)
    out: list[str] = []
    for col in range(width):
        parts: list[str] = []
        for r in header_rows:
            cell = r[col].strip() if col < len(r) else ""
            if cell and cell not in parts:
                parts.append(cell)
        out.append(" ".join(parts))
    return out


def to_markdown(tables: list[dict], text_before: str) -> str:
    out = ["# ГОСТ 1536-76 — 结构化表格摘录", "",
           "> 本文件由 tools/parse_gost.py 自动生成,内容逐字来自标准正文。", ""]
    for t in tables:
        out.append(f"## 表 {t['index']}")
        if t["context_head"]:
            out.append(f"*上下文*: {t['context_head'][:280]}")
            out.append("")
        for hr in t["header_rows"]:
            out.append(f"**表头**: {' | '.join(x for x in hr if x)}")
        out.append("")
        hdr = merged_header(t["header_rows"])
        out.append("| " + " | ".join(hdr) + " |")
        out.append("|" + "|".join(["---"] * len(hdr)) + "|")
        for r in t["data_rows"]:
            cells = r[:len(hdr)] + [""] * max(0, len(hdr) - len(r))
            out.append("| " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python parse_gost.py <gost.txt> [out.json]")
        return 1
    src = Path(sys.argv[1])
    tables = parse(src)
    print(f"解析 {len(tables)} 张表 (源 {src.name})")

    if len(sys.argv) > 2:
        dst = Path(sys.argv[2])
    else:
        dst = ROOT / "kb" / "data" / "raw" / f"{src.stem}_tables.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps({
        "schema": "standards_kb.raw_tables/1.0",
        "source_file": src.name,
        "standard_id": "ГОСТ 1536-76",
        "table_count": len(tables),
        "tables": tables,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {dst}")

    md = src.parent / f"{src.stem}_clean.md"
    md.write_text(to_markdown(tables, src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"-> {md}")

    for t in tables:
        head = " / ".join(x for x in merged_header(t["header_rows"]) if x)
        print(f"  表{t['index']}: {len(t['data_rows'])} 行 | {len(t['header_rows'])} 行表头 | {head[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
