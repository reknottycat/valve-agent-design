#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反向注入测试:确认 validate_data.py 真的会抓错,不是一路放行。

校验器只查结构与纪律 —— 但"只查纪律"不等于"不查"。这个脚本往真实条目上
注入各类典型缺陷,断言校验器必须报错;再断言真实条目必须零错。

用法: python tools/selftest_data_validator.py
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_data as V

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = json.loads((V.ROOT / "kb" / "data" / "GB_T_15530.1-2008.json").read_text(encoding="utf-8"))
contract = V.load_annotation_contract()
BASE = next(e for e in DATA["entries"] if e["id"] == "D-GBT15530-PN10-RF")

cases = []


def case(name, mutate, should_fail=True):
    e = copy.deepcopy(BASE)
    mutate(e)
    errs = V.check(e, {}, contract)
    cases.append((name, errs, should_fail))


# --- 真实条目必须零错 ---
case("真实条目(不应有错)", lambda e: None, should_fail=False)

# --- 结构缺陷 ---
case("未知列", lambda e: e["row_keys"]["10"].__setitem__("bogus_col", "1"))
case("标注键取值类型错", lambda e: e["row_keys"]["10"].__setitem__("ref_note", 123))
case("列键伪装成标注键", lambda e: e["columns"][1].__setitem__("key", "ref_x"))
case("行列数不符", lambda e: e["rows"].__setitem__(0, e["rows"][0][:-1]))
case("row_keys 条数 != rows 行数", lambda e: e["row_keys"].pop("175"))
def _rotate_values(e):
    """把 row_keys 的值整体轮转一格:键集与条数完全不变,只有行↔值的配对错位。"""
    rk = e["row_keys"]
    ks = list(rk.keys())
    vals = [rk[k] for k in ks]
    vals = vals[1:] + vals[:1]
    for k, v in zip(ks, vals):
        rk[k] = v


case("row_keys 条数不变但整体错位一格", _rotate_values)
case("引用行数值被填 0(应留 null)",
     lambda e: e["rows"][0].__setitem__(1, 0))
case("row_keys 值不是对象", lambda e: e["row_keys"].__setitem__("10", "oops"))
case("缺必填字段", lambda e: e.pop("usage"))

# --- 纪律缺陷 ---
case("VERIFIED_CLAUSE 缺 snippet", lambda e: e["source"].pop("snippet", None))
case("VERIFIED_CLAUSE 缺 locator", lambda e: e["source"].pop("locator", None))
case("E2 缺 project_usage",
     lambda e: (e["evidence"].__setitem__("grade", "E2"), e.pop("project_usage", None)))
case("id 格式不合规", lambda e: e.__setitem__("id", "D-bad id"))
case("table_kind 非法", lambda e: e.__setitem__("table_kind", "WHATEVER"))
case("evidence.status 非法", lambda e: e["evidence"].__setitem__("status", "FINE"))
case("usage.where 为空", lambda e: e["usage"].__setitem__("where", []))
case("usage.how 为空", lambda e: e["usage"].__setitem__("how", ""))
case("列缺 unit", lambda e: e["columns"][0].__setitem__("unit", ""))
case("columns key 重复",
     lambda e: e["columns"][1].__setitem__("key", e["columns"][0]["key"]))

# --- 等级纪律(共享规则,与公式校验器同一份) ---
case("出处不可核(PAYWALL)却给 E2",
     lambda e: (e.__setitem__("body_status", "PAYWALL"),
                e["evidence"].__setitem__("grade", "E2")))
case("E2 的 project_usage 全是占位符",
     lambda e: (e["evidence"].__setitem__("grade", "E2"),
                e.__setitem__("project_usage",
                              [{"task": "N/A", "status": "not-applicable", "note": "x"}])))
case("声称 FULL_TEXT_MIRROR 但 locator 指向不存在的文件",
     lambda e: (e.__setitem__("body_status", "FULL_TEXT_MIRROR"),
                e["source"].__setitem__(
                    "locator", "runs/NO_SUCH_DIR/no_such_file.txt#t1")))

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
