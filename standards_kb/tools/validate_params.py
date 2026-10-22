#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / validate_params.py —— 参数条目校验器

校验的是**结构与纪律**，不是工程正确性。
一个参数即使 100% 符合 schema，也可能理解错了标准 —— 那是人工/复核的事。

本层与公式层最大的不同，有一条是本层独有的硬门槛：

  ┌────────────────────────────────────────────────────────────┐
  │ evidence.status = VERIFIED_CLAUSE  ⇒  source.visual_verified│
  │ 必须为 true                                                  │
  └────────────────────────────────────────────────────────────┘

理由：BPVC-I / B31.1 这类 PDF 是「扫描位图 + OCR 文本层」的叠合物。
整页渲染图上，OCR 文本层是**盖在**扫描位图上面的第二层。实测本库遇到的
退化形态：π→7T、√→j、0.975→0.97S、1,500→I,SOO、5→S、千分位分隔符被吞
（"5 092"→"5092"）、"3/4"→"%"、"1/2"→"lV"。
也就是说，**文本层读出来的数字本身可能就是错的**。
只有用 tools/raster_crop.py 剥离文本层、取纯扫描位图、在页图上逐字核过，
才允许写 VERIFIED_CLAUSE。

反向也要卡住：已经在页图上核过（visual_verified=true）的条目，
状态还挂在 PENDING_VERIFICATION，说明核验结论没被采纳 —— 也要报。

必查项:
  1. 必填字段齐全
  2. id 格式 ^P-[A-Z]{2,4}-\\d{3}$；param_kind / relation / domain / body_status 枚举
  3. 数值自洽：value.numeric 必须在 value.canonical 里有据可查（能解析出同一数）
  4. RANGE 类必须给 min/max 且 min ≤ max，且两端都能在 canonical 里找到
  5. relation 与 canonical 的符号必须一致（"<=" 开头 ⇒ relation 必须是 "<="）
  6. display 里的数字必须包含 numeric（display/canonical 漂移检查）
  7. 视觉核验门槛（见上）
  8. source.standard_id 必须能归一到 registry 已登记标准，且 body_status 与 registry 一致
  9. related / cross_refs 指向的 ID 必须存在（公式层 F-xxx 与参数层 P-xxx 合并集合）
 10. applicability / usage 不得为空
 11. 证据等级纪律（共享规则，见 tools/evidence_rules.py）
 12. ID 不重复

用法:
  python tools/validate_params.py                 # 校验 kb/parameters/ 下全部条目
  python tools/validate_params.py kb/parameters/seed_bpvc_pg69.json

自测（确认本校验器有牙，不是一路放行）:
  python tools/selftest_param_validator.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARAM_DIR = ROOT / "kb" / "parameters"
REG = ROOT / "registry" / "registry.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_rules  # noqa: E402
import kb_entries  # noqa: E402
import standard_ids  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VALID_PARAM_KIND = {
    "CONSTANT", "COEFFICIENT", "LIMIT", "THRESHOLD",
    "RANGE", "DEFAULT_SUBSTITUTE", "UNIT_FACTOR", "MATERIAL_PROPERTY",
}
VALID_RELATION = {"=", "<", "<=", ">", ">=", "±", "range", "approx"}
VALID_DOMAIN = {"FLOW", "STRUCT", "SEAL", "BOLT", "MATE", "TEST",
                "GEOM", "THERM", "MASS", "DRIVE", "TOL", "PIPE"}
VALID_STATUS = {"VERIFIED_CLAUSE", "UNVERIFIED_CLAUSE", "PENDING_VERIFICATION",
                "CONFLICT", "SUPERSEDED"}
VALID_GRADE = {"E0", "E1", "E2", "E3"}
VALID_BODY = {"FULL_TEXT_MIRROR", "OFFICIAL_LIST", "PAYWALL",
              "RENDERED_JS", "LOCAL_FILE", "DERIVED_NO_TEXT"}

ID_RE = re.compile(r"^P-[A-Z]{2,4}-\d{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 千分位逗号当成分隔符："2,407" → 2407；"1,135.8" → 1135.8
_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
# 分数 a/b，允许混合数 "1 1/2"
_FRAC_RE = re.compile(r"(?:(\d+)\s+)?(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)")

# canonical / display 开头的比较符号，与 relation 必须一致
_LEAD_SYMBOL = {"<=": "<=", "<": "<", ">=": ">=", ">": ">"}

REL_TOL = 1e-9
ABS_TOL = 1e-12


# ---------------------------------------------------------------------------
# 数值抽取
# ---------------------------------------------------------------------------
def numbers_in(text: str) -> list[float]:
    """从一段文字里抽"能作为数值读出来"的候选。

    覆盖四种形态：
      * 纯小数            2407 / 5.092 / 0.707 / 0.30
      * 千分位            "2,407" / "1,135.8"
      * 分数              "1/500" / "3/8" / "0.90/51.45"
      * 混合分数          "1 1/2"
    抽分数时会同时保留分子分母本身（"3/8" 给出 0.375 / 3 / 8），
    因为 canonical 里往往同时存在英制分母和公制括号值。
    """
    s = (text or "").replace("\u00a0", " ")
    out: list[float] = []

    for m in _FRAC_RE.finditer(s):
        whole, num, den = m.group(1), m.group(2), m.group(3)
        try:
            val = float(num) / float(den)
        except ZeroDivisionError:
            continue
        if whole:
            val += float(whole)
        out.append(val)

    for m in _NUM_RE.finditer(s):
        out.append(float(m.group(0).replace(",", "")))

    return out


def _has_number(cands: list[float], target: float) -> bool:
    return any(math.isclose(c, target, rel_tol=REL_TOL, abs_tol=ABS_TOL)
               for c in cands)


def _registry_index() -> dict[str, dict]:
    """registry/registry.json → {source_id: source}"""
    out: dict[str, dict] = {}
    if not REG.exists():
        return out
    try:
        reg = json.loads(REG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    for fam in (reg.get("families") or {}).values():
        for s in (fam or {}).get("sources") or []:
            sid = s.get("id")
            if sid:
                out[sid] = s
    return out


# ---------------------------------------------------------------------------
# 主校验
# ---------------------------------------------------------------------------
def check_entry(e: dict, known_ids: set[str], reg_index: dict[str, dict]) -> list[str]:
    errs: list[str] = []
    eid = e.get("id", "<no-id>")

    # --- 1. 必填 ---
    for f in ("id", "title_zh", "param_kind", "value", "unit", "domain",
              "source", "applicability", "usage", "evidence"):
        if f not in e or e[f] in (None, "", [], {}):
            errs.append(f"缺必填字段 {f}")
    if errs:
        return errs

    if not ID_RE.match(str(e["id"])):
        errs.append(f"id 格式不合规: {e['id']!r}（应为 P-<域>-<三位序号>）")

    if e["param_kind"] not in VALID_PARAM_KIND:
        errs.append(f"param_kind 非法: {e['param_kind']!r}")

    if e["domain"] not in VALID_DOMAIN:
        errs.append(f"domain 非法: {e['domain']!r}")

    if not str(e["unit"]).strip():
        errs.append("unit 不能为空")

    # --- 2. value ---
    val = e["value"]
    if not isinstance(val, dict):
        errs.append("value 必须是对象")
        return errs

    canonical = str(val.get("canonical") or "").strip()
    if not canonical:
        errs.append("value.canonical 不能为空")

    rel = val.get("relation")
    if rel is not None and rel not in VALID_RELATION:
        errs.append(f"value.relation 非法: {rel!r}")

    kind = e["param_kind"]
    if kind in ("LIMIT", "THRESHOLD") and not rel:
        errs.append(f"param_kind={kind} 必须给 value.relation，不要只写数字")

    num = val.get("numeric")
    cands = numbers_in(canonical)

    # 数值自洽：numeric 必须能在 canonical 里解析出来
    if num is not None:
        if not isinstance(num, (int, float)) or isinstance(num, bool):
            errs.append(f"value.numeric 必须是数字: {num!r}")
        elif not _has_number(cands, float(num)):
            errs.append(
                f"value.numeric={num!r} 在 value.canonical={canonical!r} 里解析不出来"
                f"（canonical 中可读出的数: {sorted(set(cands))}）")

    # 区间：min/max 与 relation 的一致性
    mn, mx = val.get("min"), val.get("max")
    has_both = mn is not None and mx is not None
    if rel == "range" and not has_both:
        errs.append("value.relation='range' 必须同时给 value.min 与 value.max")
    if kind == "RANGE" and not has_both:
        errs.append("param_kind=RANGE 必须同时给 value.min 与 value.max")
    if has_both:
        if not isinstance(mn, (int, float)) or not isinstance(mx, (int, float)):
            errs.append("value.min/value.max 必须是数字")
        else:
            if mn > mx:
                errs.append(f"value.min={mn!r} > value.max={mx!r}，区间上下界反了")
            if rel != "range":
                errs.append(f"value.min/value.max 同时给出时 relation 必须是 'range'，实际 {rel!r}")
            for bound, tag in ((mn, "min"), (mx, "max")):
                if not _has_number(cands, float(bound)):
                    errs.append(f"value.{tag}={bound!r} 在 canonical={canonical!r} 里解析不出来")

    # relation 与 canonical 的符号必须一致
    for sym, need in _LEAD_SYMBOL.items():
        if canonical.startswith(sym):
            if rel != need:
                errs.append(f"canonical 以 {sym!r} 开头，relation 必须是 {need!r}，实际 {rel!r}")
            break

    # relation='range' ⟺ canonical 用 '..' 表达区间
    if rel == "range" and ".." not in canonical:
        errs.append(f"relation='range' 但 canonical={canonical!r} 里没有区间记号 '..'")
    if rel != "range" and ".." in canonical:
        errs.append(f"canonical={canonical!r} 用了区间记号 '..'，relation 应为 'range'，实际 {rel!r}")

    # display 与 canonical 的数值漂移
    display = val.get("display")
    if display:
        d_cands = numbers_in(str(display))
        probes: list[float] = []
        if num is not None and isinstance(num, (int, float)) and not isinstance(num, bool):
            probes.append(float(num))
        if has_both and isinstance(mn, (int, float)) and isinstance(mx, (int, float)):
            probes.extend([float(mn), float(mx)])
        for p in probes:
            if not _has_number(d_cands, p):
                errs.append(f"value.display={display!r} 里找不到 value 的数 {p!r}"
                            f"（display 与 canonical 疑似漂移）")

    # alt_values
    for i, alt in enumerate(val.get("alt_values") or []):
        if not isinstance(alt, dict) or not str(alt.get("canonical") or "").strip():
            errs.append(f"value.alt_values[{i}] 缺 canonical")

    # --- 3. source ---
    src = e["source"]
    if not isinstance(src, dict):
        errs.append("source 必须是对象")
        return errs

    for f in ("standard_id", "clause", "body_status"):
        if not src.get(f):
            errs.append(f"source 缺字段 {f}")
    if src.get("body_status") and src["body_status"] not in VALID_BODY:
        errs.append(f"source.body_status 非法: {src['body_status']!r}")

    # standard_id 必须能归一到 registry 已登记标准，且 body_status 与 registry 一致
    std_full = str(src.get("standard_id") or "")
    if std_full:
        sid = standard_ids.std_of(std_full)
        if sid not in reg_index:
            errs.append(f"source.standard_id={std_full!r} 归一后得到 {sid!r}，"
                        f"registry 里没有登记这个标准")
        else:
            reg_body = reg_index[sid].get("body_status")
            if reg_body and src.get("body_status") and reg_body != src.get("body_status"):
                errs.append(f"source.body_status={src.get('body_status')!r} 与 registry "
                            f"里 {sid} 的 {reg_body!r} 不一致")

    # --- 4. 视觉核验门槛（本层独有） ---
    ev = e.get("evidence") or {}
    status = ev.get("status")
    vv = src.get("visual_verified")

    if status not in VALID_STATUS:
        errs.append(f"evidence.status 非法: {status!r}")
    if ev.get("grade") not in VALID_GRADE:
        errs.append(f"evidence.grade 非法: {ev.get('grade')!r}")

    if status == "VERIFIED_CLAUSE":
        if vv is not True:
            errs.append("evidence.status=VERIFIED_CLAUSE 要求 source.visual_verified=true"
                        "（数值必须在剥离 OCR 文本层的纯扫描页图上逐字核过）")
        if not src.get("snippet"):
            errs.append("VERIFIED_CLAUSE 必须给 source.snippet")
        if not src.get("locator"):
            errs.append("VERIFIED_CLAUSE 必须给 source.locator")

    if vv is True and status in ("PENDING_VERIFICATION", "UNVERIFIED_CLAUSE"):
        errs.append(f"source.visual_verified=true（已在页图核过）但 evidence.status="
                    f"{status!r}，状态未升级")

    if ev.get("verified_on") and not DATE_RE.match(str(ev["verified_on"])):
        errs.append(f"evidence.verified_on 格式应为 YYYY-MM-DD: {ev['verified_on']!r}")

    # --- 5. 等级纪律（共享规则） ---
    errs.extend(evidence_rules.check_evidence(e))

    # --- 6. applicability / usage ---
    ap = e["applicability"]
    if not ap.get("valid_when"):
        errs.append("applicability.valid_when 不能为空")
    if not ap.get("not_valid_when"):
        errs.append("applicability.not_valid_when 不能为空")

    us = e["usage"]
    if not us.get("where"):
        errs.append("usage.where 不能为空")
    if not us.get("how"):
        errs.append("usage.how 不能为空")

    # --- 7. 引用完整性（公式层 ∪ 参数层） ---
    for rid in (e.get("related") or []) + (src.get("cross_refs") or []):
        if rid not in known_ids:
            errs.append(f"引用的 ID 不存在（公式层或参数层）: {rid}")

    return errs


def main() -> int:
    argv = sys.argv[1:]
    if argv:
        files = [Path(a) if Path(a).exists() else PARAM_DIR / a for a in argv]
    else:
        files = sorted(PARAM_DIR.glob("*.json"))

    if not files:
        print("kb/parameters/ 下没有条目")
        return 0

    entries: list[dict] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败 {f.name}: {e}")
            continue
        if isinstance(data, list):
            entries.extend(data)
        elif isinstance(data, dict) and "entries" in data:
            entries.extend(data["entries"])
        else:
            entries.append(data)

    known_ids = kb_entries.known_ids()
    reg_index = _registry_index()
    dup = kb_entries.duplicates(kb_entries.param_entries())
    if dup:
        print(f"ID 重复: {dup}")

    total_err = 0
    for e in entries:
        errs = check_entry(e, known_ids, reg_index)
        if errs:
            total_err += len(errs)
            print(f"\n[FAIL] {e.get('id','?')}  {e.get('title_zh','')}")
            for x in errs:
                print(f"       - {x}")
        else:
            st = e["evidence"]["status"]
            gr = e["evidence"]["grade"]
            vv = "V" if (e.get("source") or {}).get("visual_verified") is True else "-"
            print(f"[ OK ] {e['id']:<14} {e['param_kind']:<19} {e['domain']:<7} {gr} "
                  f"{st:<21} {vv} {e['title_zh'][:30]}")

    print(f"\n共 {len(entries)} 条,错误 {total_err} 处,重复 ID {len(dup)} 个")
    print("注意:本校验器只查结构与纪律,不验证工程正确性。")
    return 1 if total_err or dup else 0


if __name__ == "__main__":
    raise SystemExit(main())
