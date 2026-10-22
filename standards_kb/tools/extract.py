#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / extract.py —— 从标准正文里挖出公式候选

这是本项目最脏的一块活,原因在实测里都碰到了:
  1. OCR 把希腊字母 ASCII 化:  S=σ, SE=σ_e, Sc=σ_c, Sa=σ_a
  2. OCR 双栏交错:  左栏右栏按行交替,不重建版面就会把公式切成两半
  3. PDF 提取的公式常带上下标碎片: "σ\nh\n=\n"
  4. 公式在表格里: 行列关系丢失
  5. 指数/上下标被拆成独立行: "P\nD\n2\n"

策略: **不追求全自动,追求"高召回候选 + 严格人工确认"**。
  工具产出候选(candidate),标 CANDIDATE 状态,人工/Agent 复核后才成为公式条目。
  这符合项目既有纪律: 没拿到正文不给条款级结论;抽取出来也要标状态。

用法:
  python extract.py --source ASME-B31.9 --file b31_9_djvu.txt
  python extract.py --source ASME-B16.9 --file asme_b16_9_2003.txt --min-eq 3
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

# Windows 控制台默认 GBK,遇到希腊字母/引号会 UnicodeEncodeError 直接崩。
# 统一强制 UTF-8 输出,避免打印环节打断流水线。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. 符号归一: OCR 的 ASCII 化希腊字母 -> 真希腊字母
#    只在「明显是应力/应变符号」的位置替换,避免误伤普通 S/P/E。
# ---------------------------------------------------------------------------
GREEK_MAP = {
    "S": "σ", "Sc": "σ_c", "SE": "σ_E", "Sa": "σ_a", "Sm": "σ_m",
    "Sy": "σ_y", "Su": "σ_u", "St": "σ_t", "Sa_": "σ_a",
    "E": "E", "G": "G", "K": "K", "A": "A",
}

# 应力符号上下文: 出现在 stress/allowable/psi/kPa 附近才换
STRESS_CONTEXT = re.compile(
    r"stress|allowable|psi|kPa|MPa|yield|tensile|hoop|longitudinal|compressive",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 2. 公式行识别
# ---------------------------------------------------------------------------
EQ_RE = re.compile(r"([A-Za-zΑ-Ωα-ω][A-Za-z0-9Α-Ωα-ω_]*(?:\s*_\{?[A-Za-z0-9Α-Ωα-ω]+\}?)?)\s*=\s*(.+)")
VAR_LHS = re.compile(r"^[A-Za-zΑ-Ωα-ω][A-Za-z0-9Α-Ωα-ω_]*$")

# 明显不是公式的词
NOT_FORMULA = {
    "note", "notes", "table", "figure", "fig", "sec", "para", "para.",
    "see", "eq", "eq.", "no", "no.", "page", "chapter", "appendix",
    "in", "is", "are", "was", "were", "and", "or", "of", "to", "for",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "type", "date", "edition", "copyright", "isbn", "doi",
}

# 数字/单位行
UNIT_ONLY = re.compile(r"^\s*[\d.,\s°%±()/×xX-]+\s*[a-zA-Z]{0,12}\s*$")


def looks_like_formula(line: str) -> bool:
    s = line.strip()
    if len(s) < 4 or len(s) > 400:
        return False
    if UNIT_ONLY.match(s):
        return False
    m = EQ_RE.match(s)
    if not m:
        return False
    lhs = m.group(1).strip()
    if lhs.lower() in NOT_FORMULA:
        return False
    rhs = m.group(2).strip()
    if len(rhs) < 1:
        return False

    # 右侧必须像表达式: 含数字/运算符/变量, 不能是纯单词
    if not re.search(r"[\d\(\+\-\*/^√π]|sqrt|log|exp|sin|cos|tan", rhs, re.IGNORECASE):
        return False
    if rhs.lower() in NOT_FORMULA:
        return False
    # 排除 "Fig. 1 = ..." 之类
    if re.match(r"^(fig|figure|table|note|see|para|sec)\b", s, re.IGNORECASE):
        return False

    # ---- 关键区分: 工程公式 vs 符号定义表 ----
    # 定义表形如 "S = basic allowable stress value prior to applying..."
    #   右侧是自然语言(多个单词 + 无运算符)
    # 工程公式形如 "t = 5PL/4.85w" / "h = 0.8/n (h - 20 In)"
    #   右侧含运算符, 或 含数字与变量混合, 或 短且密集
    has_operator = bool(re.search(r"[\+\-\*/\^]", rhs))
    word_count = len(rhs.split())
    if has_operator:
        # 有运算符 -> 高概率是公式; 但 "N + T = normalizing" 这种要排除
        if re.match(r"^(not |no\.?\s|yes|true|false|and |or )", rhs, re.IGNORECASE):
            return False
        return True
    # 无运算符时: 右侧像自然语言定义则排除
    if word_count >= 4:
        return False
    # 右侧短且含数字 -> 可能是 "y = 0.4" 这类常数定义, 保留为低优先级
    return bool(re.search(r"\d", rhs))


def normalize_symbols(text: str) -> str:
    """把 OCR ASCII 化的应力符号还原。保守: 只在应力语境下替换单个 S。"""
    out = text
    # Sc / SE / Sa 这类多字符先换(带下划线形式)
    for k in ("Sc", "SE", "Sa", "Sm", "Sy", "Su", "St"):
        out = re.sub(rf"(?<![A-Za-z]){k}(?![A-Za-z0-9])", GREEK_MAP[k], out)
    # 单个 S -> σ,仅当整行含应力语境
    if STRESS_CONTEXT.search(out):
        out = re.sub(r"(?<![A-Za-z0-9_])S(?![A-Za-z0-9_])", "σ", out)
    return out


def normalize_expr(s: str) -> str:
    """规范化表达式: 统一乘除号, 去掉多余空白, 下标统一。"""
    s = s.strip()
    s = s.replace("×", "*").replace("·", "*").replace("÷", "/")
    s = re.sub(r"\s*=\s*", " = ", s)
    s = re.sub(r"\s*([+\-*/^()]+)\s*", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 下标: S1 -> S_1 ; Xa -> X_a (仅当后面跟数字或已知后缀)
    s = re.sub(r"\b([A-Za-zΑ-Ωα-ω])(\d)\b", r"\1_\2", s)
    return s


def guess_domain(text: str) -> str:
    t = text.lower()
    if re.search(r"flow|discharge|coefficient|cv\b|kv\b|head loss|orifice|drag", t):
        return "FLOW"
    if re.search(r"wall thickness|min.*thickness|t_m\b|schedule|corrosion allowance", t):
        return "STRUCT"
    if re.search(r"seal|gasket|leak|contact stress|seat", t):
        return "SEAL"
    if re.search(r"bolt|thread|fastener|stud", t):
        return "BOLT"
    if re.search(r"material|yield|tensile|elongation|allowable stress", t):
        return "MATE"
    if re.search(r"hydrostatic|test pressure|shell test|fugitive", t):
        return "TEST"
    if re.search(r"dimension|tolerance|fit|surface finish|roughness", t):
        return "GEOM"
    if re.search(r"thermal|expansion|temperature gradient|heat transfer", t):
        return "THERM"
    if re.search(r"torque|moment|lever|actuat|operator force", t):
        return "DRIVE"
    if re.search(r"mass|weight|inertia|centre of gravity", t):
        return "MASS"
    return "GEOM"


def extract_from_text(text: str, min_eq: int = 2, ctx_lines: int = 2) -> list[dict]:
    """从纯文本抽公式候选。返回候选列表(不是成品条目)。

    跨行重组: OCR/表格化会把一个公式拆成多行
        "CE = C + ( Mn + SO / 6 + ( Cr + Mo + V )/ 5 + ( Ni + Cu )/ 15"
        "CE = C + ( Mn + Si )/ 6 + 0.15"
    或者
        "WM = A - ( d + 2t n ) t r F"
    单行判定会漏掉大量跨行公式,这里做窗口式拼接再判定。
    """
    lines = text.split("\n")
    cands: list[dict] = []
    seen: set[str] = set()

    # ---- 阶段1: 单行公式 ----
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not looks_like_formula(line):
            continue
        norm = normalize_expr(normalize_symbols(line))
        if norm in seen:
            continue
        seen.add(norm)
        m = EQ_RE.match(line)
        lo = max(0, i - ctx_lines)
        hi = min(len(lines), i + ctx_lines + 1)
        cands.append({
            "expr": norm,
            "lhs": normalize_symbols(m.group(1)).strip() if m else "",
            "rhs": normalize_symbols(m.group(2)).strip() if m else "",
            "line_no": i + 1,
            "line_span": [i + 1, i + 1],
            "context": "\n".join(lines[lo:hi]).strip()[:600],
            "domain": guess_domain("\n".join(lines[lo:hi])),
            "ocr_degraded": bool(re.search(r"\b(Sc|SE|Sa|Sm|Sy|Su|St)\b", line)),
            "confidence": "LOW",
            "form": "single_line",
        })

    # ---- 阶段2: 跨行公式(左式在上一行,续行在下) ----
    # 特征: 本行以 '=' 或运算符开头, 或上一行以 '=' 结尾且本行是续行
    for i in range(len(lines) - 1):
        a = lines[i].strip()
        b = lines[i + 1].strip()
        if not a or not b:
            continue
        # 上一行必须有 '=' 且右侧看似未闭合/未完成
        if "=" not in a or "=" in b:
            continue
        if not re.match(r"^[\w\.\)\]]", b):
            continue
        # b 应当是运算符开头或纯数值/变量串
        if not re.match(r"^[\+\-\*/\^]?\s*[\w\.\(\[\)0-9]", b):
            continue
        merged = a + " " + b
        m = EQ_RE.match(merged.strip())
        if not m:
            continue
        rhs = m.group(2).strip()
        if not re.search(r"[\d\(\+\-\*/\^]", rhs):
            continue
        if not re.search(r"[=+\-*/\^]", rhs):
            continue
        norm = normalize_expr(normalize_symbols(merged.strip()))
        if norm in seen:
            continue
        seen.add(norm)
        lo = max(0, i - ctx_lines)
        hi = min(len(lines), i + 3 + ctx_lines)
        cands.append({
            "expr": norm,
            "lhs": normalize_symbols(m.group(1)).strip(),
            "rhs": normalize_symbols(rhs).strip(),
            "line_no": i + 1,
            "line_span": [i + 1, i + 2],
            "context": "\n".join(lines[lo:hi]).strip()[:600],
            "domain": guess_domain("\n".join(lines[lo:hi])),
            "ocr_degraded": True,
            "confidence": "LOW",
            "form": "multiline",
        })

    return cands


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="source id,例:ASME-B31.9")
    ap.add_argument("--file", required=True, help="相对 runs/<source>/ 的文件名")
    ap.add_argument("--min-eq", type=int, default=2, help="每页最少公式数才算有效页")
    ap.add_argument("--out", help="输出文件名(默认 <source>__candidates.json)")
    ap.add_argument("--no-pdf", action="store_true", help="不尝试 PDF,按纯文本处理")
    args = ap.parse_args()

    src_dir = RUNS / args.source
    path = src_dir / args.file
    if not path.exists():
        print(f"找不到 {path}")
        print("先跑 fetch.py 下载正文。")
        return 1

    text = path.read_text(encoding="utf-8", errors="replace")
    print(f"读取 {path.relative_to(ROOT)}  ({len(text):,} 字符)")

    # PDF 有文本层则优先用 PDF,否则用随附的 txt
    if not args.no_pdf and path.suffix.lower() == ".pdf":
        try:
            import pymupdf
            doc = pymupdf.open(path)
            text = "\n\f\n".join(doc[i].get_text() for i in range(doc.page_count))
            print(f"  PDF 文本层提取: {doc.page_count} 页, {len(text):,} 字符")
        except Exception as e:
            print(f"  PDF 提取失败({e}),退回原文本")

    cands = extract_from_text(text)

    # 按页统计
    pages = text.split("\n\f\n")
    page_hits = {}
    for c in cands:
        pass

    out_name = args.out or f"{args.source}__candidates.json"
    out = {
        "schema": "standards_kb.candidates/1.0",
        "source_id": args.source,
        "file": str(path.relative_to(ROOT)),
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "text_chars": len(text),
        "candidate_count": len(cands),
        "note": "全部为 CANDIDATE,confidence=LOW。抽取器不判定正确性,须人工/Agent 复核后转成公式条目。",
        "candidates": cands,
    }
    (src_dir / out_name).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n候选公式 {len(cands)} 条 -> {(src_dir / out_name).relative_to(ROOT)}")
    by_dom: dict[str, int] = {}
    for c in cands:
        by_dom[c["domain"]] = by_dom.get(c["domain"], 0) + 1
    print("按域:", ", ".join(f"{k}={v}" for k, v in sorted(by_dom.items(), key=lambda x: -x[1])))
    print("\n前 12 条样本:")
    for c in cands[:12]:
        flag = " [OCR]" if c["ocr_degraded"] else ""
        print(f"  L{c['line_no']:<6} {c['domain']:<7}{flag} {c['expr'][:88]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
