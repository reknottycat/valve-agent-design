#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反向注入测试:确认 validate.py 真的会抓错,不是一路放行。

校验器只查结构与纪律 —— 但"只查纪律"不等于"不查"。这个脚本往真实条目上
注入各类典型缺陷,断言校验器必须报错;再断言真实条目必须零错。

重点覆盖本轮新增的等级纪律(tools/evidence_rules.py):
  - 等级双写(source.evidence_grade 与 evidence.grade)必须同步
  - 出处不可核(PAYWALL / DERIVED_NO_TEXT / OFFICIAL_LIST)时等级封顶 E1
  - E2/E3 的 project_usage 不能全是占位符
  - 声称 FULL_TEXT_MIRROR 必须给得出磁盘上真实存在的定位文件

用法: python tools/selftest_formula_validator.py
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as V
import kb_entries as K

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FORM_DIR = V.ROOT / "kb" / "formulas"


def load_all():
    out = []
    for f in sorted(FORM_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.append(data)
    return out


ALL = load_all()
# 引用完整性用全库合并集合(公式 + 参数),与 validate.py 的 main() 保持一致
KNOWN = {e.get("id") for e in ALL if e.get("id")} | K.param_ids()
PARAM_IDS = sorted(K.param_ids())
# F-MAT-002: E1/VERIFIED_CLAUSE,带 snippet + 真实存在的 locator,适合当基准
BASE = next(e for e in ALL if e["id"] == "F-MAT-002")

cases = []


def case(name, mutate, should_fail=True):
    e = copy.deepcopy(BASE)
    mutate(e)
    errs = V.check_entry(e, KNOWN, {})
    cases.append((name, errs, should_fail))


# --- 真实条目必须零错 ---
case("真实条目(不应有错)", lambda e: None, should_fail=False)

# --- 结构缺陷 ---
case("缺必填字段", lambda e: e.pop("usage"))
case("id 格式不合规", lambda e: e.__setitem__("id", "F-bad id"))
case("domain 非法", lambda e: e.__setitem__("domain", "WHATEVER"))
case("变量未在 variables 中定义",
     lambda e: e["expression"].__setitem__("canonical", "sigma_allow * q_new"))
case("usage.where 为空", lambda e: e["usage"].__setitem__("where", []))
case("usage.how 为空", lambda e: e["usage"].__setitem__("how", ""))
case("related 指向不存在的 ID", lambda e: e.__setitem__("related", ["F-NOPE-999"]))
case("cross_refs 指向不存在的 ID",
     lambda e: e["source"].__setitem__("cross_refs", ["F-NOPE-999"]))
# --- 跨层引用(公式 <-> 参数)---
case("related 指向不存在的参数 ID",
     lambda e: e.__setitem__("related", ["P-NOPE-999"]))
case("related 指向真实存在的参数 ID(应通过)",
     lambda e: e.__setitem__("related", [PARAM_IDS[0]] if PARAM_IDS else ["P-NONE"]),
     should_fail=False)
case("变量缺 unit", lambda e: e["variables"][0].__setitem__("unit", ""))

# --- 纪律缺陷 ---
case("VERIFIED_CLAUSE 缺 snippet", lambda e: e["source"].pop("snippet", None))
case("VERIFIED_CLAUSE 缺 locator", lambda e: e["source"].pop("locator", None))
case("evidence.grade 非法", lambda e: e["evidence"].__setitem__("grade", "E9"))
case("evidence.status 非法", lambda e: e["evidence"].__setitem__("status", "FINE"))
case("source.body_status 非法", lambda e: e["source"].__setitem__("body_status", "MADE_UP"))

# --- 等级纪律(本轮新增) ---
case("等级双写不同步",
     lambda e: e["source"].__setitem__("evidence_grade", "E2"))
case("出处不可核(PAYWALL)却给 E2",
     lambda e: (e["source"].__setitem__("body_status", "PAYWALL"),
                e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2")))
case("出处不可核(DERIVED_NO_TEXT)却给 E3",
     lambda e: (e["source"].__setitem__("body_status", "DERIVED_NO_TEXT"),
                e["evidence"].__setitem__("grade", "E3"),
                e["source"].__setitem__("evidence_grade", "E3")))
case("E2 缺 project_usage",
     lambda e: (e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2"),
                e.pop("project_usage", None)))
case("E2 的 project_usage 全是占位符",
     lambda e: (e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2"),
                e.__setitem__("project_usage",
                              [{"task": "N/A", "status": "not-applicable", "note": "x"}])))
case("FULL_TEXT_MIRROR 但无 locator",
     lambda e: e["source"].__setitem__("locator", ""))
case("FULL_TEXT_MIRROR 但无 locator（status 非 VERIFIED，隔离新规则）",
     lambda e: (e["source"].__setitem__("locator", ""),
                e["evidence"].__setitem__("status", "PENDING_VERIFICATION"),
                e["source"].pop("snippet", None)))
case("FULL_TEXT_MIRROR 的 locator 指向不存在的文件",
     lambda e: e["source"].__setitem__(
         "locator", "runs/NO_SUCH_DIR/no_such_file.txt L123"))

ok = True
for name, errs, should_fail in cases:
    got = len(errs) > 0
    good = got == should_fail
    ok = ok and good
    mark = "PASS" if good else "FAIL"
    expect = "应报错" if should_fail else "应通过"
    print(f"[{mark}] {name} ({expect}): {len(errs)} 错"
          + (f"  {errs[0]}" if errs else ""))

print(f"\n负向测试 {len(cases)} 项:", "全部符合预期" if ok else "有不符合预期的项")
print("注意:本校验器只查结构与纪律,不验证工程正确性。")
sys.exit(0 if ok else 1)
