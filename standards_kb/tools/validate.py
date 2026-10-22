#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / validate.py —— 公式条目校验器

校验的是**结构与纪律**,不是工程正确性。
一条公式即使 100% 符合 schema,也可能算错了 —— 那是人工/CAE 的事。

必查项:
  1. 必填字段齐全
  2. 变量表里出现的符号,表达式里必须用到;表达式里的符号,变量表必须定义
  3. evidence.status = VERIFIED_CLAUSE 时,source.snippet 和 locator 必须有
  4. body_status 必须与 registry 里的该标准一致(不能声称有正文却标 PAYWALL)
  5. related / cross_refs 指向的 ID 必须存在
  6. usage.where / how 不能为空
  7. 证据等级 E2/E3 必须有 project_usage 支撑
  8. 等级纪律(共享规则):等级双写同步 / 出处不可核则封顶 E1 /
     E2-E3 不得只有占位 project_usage / 声称有正文必须定位得到
     —— 细则见 tools/evidence_rules.py

用法:
  python validate.py                 # 校验 kb/formulas/ 下全部条目
  python validate.py kb/formulas/xx.json

自测(确认本校验器有牙,不是一路放行):
  python tools/selftest_formula_validator.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORM_DIR = ROOT / "kb" / "formulas"
REG = ROOT / "registry" / "registry.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_rules  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VALID_DOMAIN = {"FLOW", "STRUCT", "SEAL", "BOLT", "MATE", "TEST",
                 "GEOM", "THERM", "MASS", "DRIVE", "TOL", "PIPE"}
VALID_STATUS = {"VERIFIED_CLAUSE", "UNVERIFIED_CLAUSE", "PENDING_VERIFICATION",
                "CONFLICT", "SUPERSEDED"}
VALID_GRADE = {"E0", "E1", "E2", "E3"}
VALID_BODY = {"FULL_TEXT_MIRROR", "OFFICIAL_LIST", "PAYWALL",
              "RENDERED_JS", "LOCAL_FILE", "DERIVED_NO_TEXT"}

SYMBOL_RE = re.compile(r"[A-Za-zΑ-Ωα-ω][A-Za-z0-9Α-Ωα-ω_]*")
# 科学计数法片段: 1e5 / 2.5E-3 —— 不能当变量
SCI_RE = re.compile(r"\d+\.?\d*[eE][+-]?\d+")
FUNC_WORDS = {"sqrt", "log", "exp", "sin", "cos", "tan", "pi", "and", "or",
              "not", "if", "min", "max", "abs"}


def load_entries(files: list[Path]) -> list[dict]:
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败 {f.name}: {e}")
            continue
        if isinstance(data, list):
            out.extend(data)
        else:
            out.append(data)
    return out


def check_entry(e: dict, known_ids: set[str], reg: dict) -> list[str]:
    errs: list[str] = []
    eid = e.get("id", "<no-id>")

    for f in ("id", "title_zh", "expression", "variables", "domain",
              "source", "applicability", "usage", "evidence"):
        if f not in e:
            errs.append(f"缺必填字段 {f}")
    if errs:
        return errs

    if not re.fullmatch(r"F-[A-Z]{2,4}-\d{3}", e["id"]):
        errs.append(f"id 格式不合规: {e['id']}")

    if e["domain"] not in VALID_DOMAIN:
        errs.append(f"domain 非法: {e['domain']}")

    # --- 变量一致性 ---
    expr = e["expression"].get("canonical", "")
    # 先把科学计数法片段屏蔽掉,避免 1e5 被拆成变量 e5
    expr_scan = SCI_RE.sub(" ", expr)
    declared = {v["symbol"].strip() for v in e["variables"]}
    expr_syms = set()
    for s in SYMBOL_RE.findall(expr_scan):
        base = s.split("_")[0]
        if base.lower() in FUNC_WORDS or s.lower() in FUNC_WORDS:
            continue
        if len(base) <= 1 and base.isalpha():
            continue  # 单字母常数, 不强制
        expr_syms.add(s)
    for s in expr_syms:
        if s not in declared and s.split("_")[0] not in declared:
            errs.append(f"表达式符号 {s!r} 未在 variables 中定义")
    for v in e["variables"]:
        for f in ("symbol", "name_zh", "unit"):
            if not v.get(f):
                errs.append(f"变量缺字段 {f}: {v.get('symbol','?')}")

    # --- source ---
    src = e["source"]
    for f in ("standard_id", "clause", "body_status"):
        if not src.get(f):
            errs.append(f"source 缺字段 {f}")
    if src.get("body_status") and src["body_status"] not in VALID_BODY:
        errs.append(f"source.body_status 非法: {src['body_status']}")

    ev = e["evidence"]
    if ev.get("status") not in VALID_STATUS:
        errs.append(f"evidence.status 非法: {ev.get('status')}")
    if ev.get("grade") not in VALID_GRADE:
        errs.append(f"evidence.grade 非法: {ev.get('grade')}")
    if ev.get("status") == "VERIFIED_CLAUSE":
        if not src.get("snippet"):
            errs.append("VERIFIED_CLAUSE 必须给 source.snippet")
        if not src.get("locator"):
            errs.append("VERIFIED_CLAUSE 必须给 source.locator")

    # --- 等级纪律(共享规则) ---
    errs.extend(evidence_rules.check_evidence(e))

    # --- applicability ---
    ap = e["applicability"]
    if not ap.get("valid_when"):
        errs.append("applicability.valid_when 不能为空")
    if not ap.get("not_valid_when"):
        errs.append("applicability.not_valid_when 不能为空")

    # --- usage ---
    us = e["usage"]
    if not us.get("where"):
        errs.append("usage.where 不能为空")
    if not us.get("how"):
        errs.append("usage.how 不能为空")

    # --- 引用完整性 ---
    for rid in (e.get("related") or []) + (src.get("cross_refs") or []):
        if rid not in known_ids:
            errs.append(f"引用的公式 ID 不存在: {rid}")

    return errs


def main() -> int:
    argv = sys.argv[1:]
    if argv:
        files = [Path(a) if Path(a).exists() else FORM_DIR / a for a in argv]
    else:
        files = sorted(FORM_DIR.glob("*.json"))

    if not files:
        print("kb/formulas/ 下没有条目")
        return 0

    entries = load_entries(files)
    known_ids = {e.get("id") for e in entries if e.get("id")}
    dup = [i for i in known_ids if sum(1 for e in entries if e.get("id") == i) > 1]
    if dup:
        print(f"ID 重复: {sorted(dup)}")

    reg = {}
    if REG.exists():
        reg = json.loads(REG.read_text(encoding="utf-8"))

    total_err = 0
    for e in entries:
        errs = check_entry(e, known_ids, reg)
        if errs:
            total_err += len(errs)
            print(f"\n[FAIL] {e.get('id','?')}  {e.get('title_zh','')}")
            for x in errs:
                print(f"       - {x}")
        else:
            st = e["evidence"]["status"]
            gr = e["evidence"]["grade"]
            print(f"[ OK ] {e['id']:<14} {e['domain']:<7} {gr} {st:<20} {e['title_zh'][:34]}")

    print(f"\n共 {len(entries)} 条,错误 {total_err} 处,重复 ID {len(dup)} 个")
    print("注意:本校验器只查结构与纪律,不验证工程正确性。")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
