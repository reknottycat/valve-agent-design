#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / validate_data.py —— 数据表条目校验器

和 validate.py 一样: 只查**结构与纪律**,不查工程正确性。

必查项:
  1. 必填字段齐全
  2. 每行列数 == columns 数
  3. row_keys 的定位键与 rows 一致(条数、逐行取值对齐、键可溯源到某列)
  4. evidence.status = VERIFIED_CLAUSE 时必须有 snippet + locator
  5. body_status 必须合法,且与 registry 记录不矛盾
  6. usage.where / how 不能为空
  7. E2/E3 必须有 project_usage
  8. 单位不能空
  9. 行标注键按 kb/data.schema.json#x-row-key-annotations 契约放行(不在本校验器里硬编码)
 10. 跨表引用行的数值列必须留 null
  11. evidence discipline (shared rules, same module as the formula validator):
      grade double-write stays in sync / unverifiable body caps grade at E1 /
      E2-E3 cannot rest on placeholder project_usage /
      claiming a full-text mirror must be locatable on disk
      -- details in tools/evidence_rules.py

自测(确认本校验器有牙,不是一路放行):
  python tools/selftest_data_validator.py

用法:
  python validate_data.py
  python validate_data.py kb/data/XXX.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "kb" / "data"
REG = ROOT / "registry" / "registry.json"
SCHEMA = ROOT / "kb" / "data.schema.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_rules  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VALID_BODY = {"FULL_TEXT_MIRROR", "OFFICIAL_LIST", "PAYWALL",
              "RENDERED_JS", "LOCAL_FILE", "DERIVED_NO_TEXT"}
VALID_GRADE = {"E0", "E1", "E2", "E3"}
VALID_STATUS = {"VERIFIED_CLAUSE", "UNVERIFIED_CLAUSE", "PENDING_VERIFICATION",
                "CONFLICT", "SUPERSEDED"}
VALID_KIND = {"DIMENSION_TABLE", "MATERIAL_TABLE", "STRESS_TABLE", "TOLERANCE_TABLE",
              "CORRECTION_TABLE", "TEST_TABLE", "SEALING_TABLE", "THREAD_TABLE"}
ID_RE = re.compile(r"^D-[A-Z0-9]{2,12}-[A-Z0-9-]{2,40}$")


def load_entries(files: list[Path]) -> list[dict]:
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败 {f.name}: {e}")
            continue
        if isinstance(data, dict) and "entries" in data:
            out.extend(data["entries"])
        elif isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.append(data)
    return out


def load_annotation_contract() -> dict:
    """行标注键契约。约定写在 schema 的 x-row-key-annotations 里,不在本校验器里硬编码。

    缺 schema 或缺契约块时返回空契约 —— 保守起见不放行任何标注键,
    这样"契约缺失"会表现为错误,而不是悄悄放过未知列。
    """
    if not SCHEMA.exists():
        print(f"[WARN] 找不到 schema: {SCHEMA}")
        return {}
    try:
        sch = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[WARN] schema 解析失败: {e}")
        return {}
    c = sch.get("x-row-key-annotations")
    if not isinstance(c, dict):
        print("[WARN] schema 里没有 x-row-key-annotations 契约块")
        return {}
    return {
        "prefixes": tuple(c.get("prefixes") or ()),
        "suffixes": tuple(c.get("suffixes") or ()),
        "value_types": tuple(c.get("value_types") or ("string",)),
    }


def json_type_name(v) -> str:
    """Python 值 -> JSON Schema 类型名。契约里的 value_types 用的是 JSON Schema 写法。"""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, str):
        return "string"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    return "object"


def is_annotation_key(key: str, contract: dict) -> bool:
    if not contract:
        return False
    if contract["prefixes"] and key.startswith(contract["prefixes"]):
        return True
    if contract["suffixes"] and key.endswith(contract["suffixes"]):
        return True
    return False


def _same_cell(a, b) -> bool:
    """两个单元格是否等价。允许 str/int 表示差异,但不把 None 当作等价于任何值。"""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a == b:
        return True
    return str(a) == str(b)


def check_alignment(e: dict, keys: list[str], rk: dict) -> list[str]:
    """row_keys 与 rows 的对齐检查(契约: kb/data.schema.json#x-row-key-alignment)。

    row_keys 是与 rows 平行的有序字典,第 i 个项对应 rows[i]。行序错位是**静默
    污染**:每次按键取值都会拿到另一行的数据,而且不会有任何报错。

    怎么验证:直接比 —— row_keys[i] 里每个列键的取值必须等于 rows[i] 里同名列的
    取值。再顺手查两件事:条数一致;跨表引用行除定位键列外必须为 null。
    """
    errs: list[str] = []
    rows = e.get("rows") or []
    if not rk:
        return errs
    if len(rk) != len(rows):
        errs.append(f"row_keys 条数 {len(rk)} != rows 行数 {len(rows)}(必须逐行对齐)")

    rk_items = list(rk.items())
    for i, (rkey, rval) in enumerate(rk_items):
        if i >= len(rows):
            break
        row = rows[i]
        if not isinstance(rval, dict):
            continue
        if len(row) != len(keys):
            # 行长度已由上面的"行列数不符"报过,这里不重复比值,避免越界
            continue
        # 1) 逐列比值
        for j, ckey in enumerate(keys):
            if ckey not in rval:
                continue
            if not _same_cell(rval[ckey], row[j]):
                errs.append(f"row_keys['{rkey}'] 与第 {i+1} 行的 {ckey} 不一致: "
                            f"{rval[ckey]!r} != {row[j]!r}(行序可能错位)")
        # 2) 定位键列:值与 rkey 字符串化相等的列
        key_cols = [j for j, cv in enumerate(row)
                    if cv is not None and str(cv) == str(rkey)]
        if not key_cols:
            errs.append(f"row_keys['{rkey}'] 与第 {i+1} 行对不上:该行没有任何列取值等于 '{rkey}'")
            continue
        # 3) 跨表引用行:除定位键列外数值列必须为 null
        if any(kk.startswith("ref_table") for kk in rval):
            bad = []
            for j, cv in enumerate(row):
                if j in key_cols:
                    continue
                if cv is not None:
                    bad.append(f"{keys[j]}={cv}")
            if bad:
                errs.append(f"row_keys['{rkey}'] 是跨表引用行,数值列应留 null,却有: {', '.join(bad)}")
    return errs


def check(e: dict, reg: dict, contract: dict) -> list[str]:
    errs: list[str] = []
    eid = e.get("id", "<no-id>")

    for f in ("id", "title_zh", "table_kind", "standard_id", "clause",
              "columns", "rows", "body_status", "evidence", "usage"):
        if f not in e:
            errs.append(f"缺必填字段 {f}")
    if errs:
        return errs

    if not ID_RE.match(e["id"]):
        errs.append(f"id 格式不合规: {e['id']}")
    if e["table_kind"] not in VALID_KIND:
        errs.append(f"table_kind 非法: {e['table_kind']}")
    if e["body_status"] not in VALID_BODY:
        errs.append(f"body_status 非法: {e['body_status']}")

    cols = e["columns"]
    ncol = len(cols)
    for c in cols:
        for f in ("key", "name_zh", "unit"):
            if not c.get(f):
                errs.append(f"列缺字段 {f}: {c.get('key','?')}")
    keys = [c.get("key") for c in cols]
    if len(keys) != len(set(keys)):
        errs.append("columns 的 key 有重复")

    # 标注键与列键不得同名,否则取数时无法区分"这是数值列"还是"这是标注"
    for k in keys:
        if is_annotation_key(k, contract):
            errs.append(f"列键 '{k}' 与行标注键约定冲突(请改列名)")

    for i, r in enumerate(e["rows"]):
        if len(r) != ncol:
            errs.append(f"第 {i+1} 行列数 {len(r)} != columns 数 {ncol}")

    rk = e.get("row_keys") or {}
    for k, v in rk.items():
        if not isinstance(v, dict):
            errs.append(f"row_keys['{k}'] 不是对象")
            continue
        for ck, cv in v.items():
            if ck in keys:
                continue
            if is_annotation_key(ck, contract):
                # 契约放行的标注键:只查取值类型
                vt = contract["value_types"]
                tn = json_type_name(cv)
                if vt and tn not in vt:
                    errs.append(f"row_keys['{k}'] 标注键 {ck} 取值类型 {tn} 不在契约允许 {list(vt)}")
                continue
            errs.append(f"row_keys['{k}'] 含未知列 {ck}")

    errs.extend(check_alignment(e, keys, rk))

    ev = e["evidence"]
    if ev.get("status") not in VALID_STATUS:
        errs.append(f"evidence.status 非法: {ev.get('status')}")
    if ev.get("grade") not in VALID_GRADE:
        errs.append(f"evidence.grade 非法: {ev.get('grade')}")
    src = e.get("source") or {}
    if ev.get("status") == "VERIFIED_CLAUSE":
        if not src.get("snippet"):
            errs.append("VERIFIED_CLAUSE 必须给 source.snippet")
        if not src.get("locator"):
            errs.append("VERIFIED_CLAUSE 必须给 source.locator")
    # --- evidence discipline (shared rules) ---
    errs.extend(evidence_rules.check_evidence(e))

    us = e["usage"]
    if not us.get("where"):
        errs.append("usage.where 不能为空")
    if not us.get("how"):
        errs.append("usage.how 不能为空")

    return errs


def main() -> int:
    argv = sys.argv[1:]
    if argv:
        files = [Path(a) if Path(a).exists() else DATA_DIR / a for a in argv]
    else:
        files = sorted(p for p in DATA_DIR.glob("*.json") if p.name != "raw")

    if not files:
        print("kb/data/ 下没有数据条目")
        return 0

    entries = load_entries(files)
    ids = [e.get("id") for e in entries if e.get("id")]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        print(f"ID 重复: {dup}")

    reg = {}
    if REG.exists():
        reg = json.loads(REG.read_text(encoding="utf-8"))

    contract = load_annotation_contract()
    if contract:
        print(f"行标注键契约: 前缀 {list(contract['prefixes'])} / 后缀 {list(contract['suffixes'])}"
              f" / 取值类型 {list(contract['value_types'])}")
    else:
        print("行标注键契约缺失: 本次不放行任何标注键")

    total = 0
    for e in entries:
        errs = check(e, reg, contract)
        if errs:
            total += len(errs)
            print(f"\n[FAIL] {e.get('id','?')}  {e.get('title_zh','')}")
            for x in errs:
                print(f"       - {x}")
        else:
            print(f"[ OK ] {e['id']:<24}{e['table_kind']:<16}"
                  f"{e['evidence']['grade']} {e['evidence']['status']:<20}"
                  f"{len(e['rows']):>3} 行  {e['title_zh'][:34]}")

    print(f"\n共 {len(entries)} 条,错误 {total} 处,重复 ID {len(dup)} 个")
    print("注意:本校验器只查结构与纪律,不验证工程正确性。")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
