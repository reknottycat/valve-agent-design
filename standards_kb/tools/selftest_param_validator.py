#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反向注入测试:确认 validate_params.py 真的会抓错,不是一路放行。

校验器只查结构与纪律 —— 但"只查纪律"不等于"不查"。这个脚本往真实条目上
注入各类典型缺陷,断言校验器必须报错;再断言真实条目必须零错。

重点覆盖本层独有的两条硬门槛:
  - evidence.status = VERIFIED_CLAUSE  =>  source.visual_verified 必须为 true
    （扫描型 PDF 的 OCR 文本层会把 π 打成 7T、把 0.975 打成 0.97S、
      把 "5 092" 打成 "5092"，不剥文本层看纯位图就没资格写 VERIFIED_CLAUSE）
  - source.visual_verified = true      =>  状态不能还挂在 PENDING_VERIFICATION

以及数值自洽:
  - value.numeric 必须能在 value.canonical 里解析出来
  - RANGE 类必须给 min/max 且 min <= max
  - relation 与 canonical 的符号必须一致
  - display 与 canonical 的数值不能漂移

用法: python tools/selftest_param_validator.py
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_params as V  # noqa: E402
import kb_entries as K  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PARAM_DIR = V.ROOT / "kb" / "parameters"


def load_all():
    out = []
    for f in sorted(PARAM_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.append(data)
    return out


ALL = load_all()
BY_ID = {e["id"]: e for e in ALL if e.get("id")}
# 引用完整性用全库合并集合(公式 + 参数),与 validate_params.py 的 main() 一致
KNOWN = {e.get("id") for e in ALL if e.get("id")} | K.formula_ids()
FORMULA_IDS = sorted(K.formula_ids())
PARAM_IDS = sorted(K.param_ids())

# 基准条目:
#   P-TEST-001  E1/VERIFIED_CLAUSE/visual_verified=true, canonical "2407", display "2,407"
#   P-TEST-002  canonical "5.092"  —— 用来复现"5 092"这个真实历史坑
#   P-TEST-009  RANGE, canonical "0.15..0.75", min/max 齐
#   P-MAT-001   LIMIT, canonical "<= 0.45", relation "<=" —— 用来测符号一致性
BASE = BY_ID["P-TEST-001"]
BASE_SI = BY_ID["P-TEST-002"]
BASE_RANGE = BY_ID["P-TEST-009"]
BASE_LIMIT = BY_ID["P-MAT-001"]

cases = []


def case(name, mutate, should_fail=True, base=None):
    e = copy.deepcopy(base or BASE)
    mutate(e)
    errs = V.check_entry(e, KNOWN, V._registry_index())
    cases.append((name, errs, should_fail))


# --- 真实条目必须零错 ---
case("真实条目(不应有错)", lambda e: None, should_fail=False)
case("真实 RANGE 条目(不应有错)", lambda e: None, should_fail=False, base=BASE_RANGE)
case("真实 LIMIT 条目(不应有错)", lambda e: None, should_fail=False, base=BASE_LIMIT)

# --- 结构缺陷 ---
case("缺必填字段 usage", lambda e: e.pop("usage"))
case("缺必填字段 value", lambda e: e.pop("value"))
case("缺必填字段 source", lambda e: e.pop("source"))
case("id 格式不合规", lambda e: e.__setitem__("id", "P-bad id"))
case("id 前缀不是 P-", lambda e: e.__setitem__("id", "F-TEST-001"))
case("param_kind 非法", lambda e: e.__setitem__("param_kind", "WHATEVER"))
case("domain 非法", lambda e: e.__setitem__("domain", "MATERIAL"))
case("unit 为空", lambda e: e.__setitem__("unit", ""))
case("value.canonical 为空", lambda e: e["value"].__setitem__("canonical", ""))
case("value.relation 非法", lambda e: e["value"].__setitem__("relation", "=>"))
case("LIMIT 类缺 relation",
     lambda e: (e.__setitem__("param_kind", "LIMIT"),
                e["value"].pop("relation", None)))
case("THRESHOLD 类缺 relation",
     lambda e: (e.__setitem__("param_kind", "THRESHOLD"),
                e["value"].pop("relation", None)))

# --- 数值自洽 ---
case("numeric 在 canonical 里解析不出来",
     lambda e: e["value"].__setitem__("numeric", 2407.5))
case("numeric 是字符串", lambda e: e["value"].__setitem__("numeric", "2407"))
case("numeric 是布尔", lambda e: e["value"].__setitem__("numeric", True))
case("★ canonical 变成 OCR 退化形态 '5 092'（复现真实历史坑）",
     lambda e: e["value"].__setitem__("canonical", "5 092"),
     base=BASE_SI)
case("canonical 带千分位但数值仍对得上（应通过）",
     lambda e: e["value"].__setitem__("canonical", "2,407"),
     should_fail=False)
case("RANGE 缺 min/max",
     lambda e: (e.__setitem__("param_kind", "RANGE"),
                e["value"].pop("min", None),
                e["value"].pop("max", None)),
     base=BASE_RANGE)
case("relation='range' 但缺 min/max",
     lambda e: (e["value"].pop("min", None),
                e["value"].pop("max", None)),
     base=BASE_RANGE)
case("区间上下界反了(min > max)",
     lambda e: (e["value"].__setitem__("min", 0.75),
                e["value"].__setitem__("max", 0.15)),
     base=BASE_RANGE)
case("min 不在 canonical 里",
     lambda e: e["value"].__setitem__("min", 0.11),
     base=BASE_RANGE)
case("max 不在 canonical 里",
     lambda e: e["value"].__setitem__("max", 0.99),
     base=BASE_RANGE)
case("同时给 min/max 但 relation 不是 range",
     lambda e: e["value"].__setitem__("relation", "="),
     base=BASE_RANGE)
case("relation='range' 但 canonical 没有区间记号",
     lambda e: e["value"].__setitem__("canonical", "0.15"),
     base=BASE_RANGE)
case("canonical 有区间记号但 relation 不是 range",
     lambda e: e["value"].__setitem__("relation", "="),
     base=BASE_RANGE)

# --- relation 与 canonical 的符号一致性 ---
case("canonical 以 '<=' 开头但 relation 是 '='",
     lambda e: e["value"].__setitem__("relation", "="),
     base=BASE_LIMIT)
case("canonical 以 '<' 开头但 relation 是 '<='",
     lambda e: e["value"].__setitem__("canonical", "< 0.45"),
     base=BASE_LIMIT)

# --- display 与 canonical 漂移 ---
case("display 里的数与 canonical 对不上",
     lambda e: e["value"].__setitem__("display", "2,400"))
case("display 缺少数值",
     lambda e: e["value"].__setitem__("display", "见 F-TEST-001"))
case("alt_values 缺 canonical",
     lambda e: e["value"].__setitem__("alt_values", [{"display": "x"}]))

# --- 视觉核验门槛（本层独有） ---
case("★ VERIFIED_CLAUSE 但 visual_verified=False",
     lambda e: e["source"].__setitem__("visual_verified", False))
case("★ VERIFIED_CLAUSE 但 visual_verified 字段缺失",
     lambda e: e["source"].pop("visual_verified", None))
case("★ visual_verified=True 但状态还挂 PENDING_VERIFICATION",
     lambda e: e["evidence"].__setitem__("status", "PENDING_VERIFICATION"))
case("★ visual_verified=True 但状态是 UNVERIFIED_CLAUSE",
     lambda e: e["evidence"].__setitem__("status", "UNVERIFIED_CLAUSE"))
case("VERIFIED_CLAUSE 缺 snippet", lambda e: e["source"].pop("snippet", None))
case("VERIFIED_CLAUSE 缺 locator", lambda e: e["source"].pop("locator", None))
case("verified_on 格式错", lambda e: e["evidence"].__setitem__("verified_on", "2026/10/22"))

# --- source / registry 一致性 ---
case("source.body_status 非法",
     lambda e: e["source"].__setitem__("body_status", "MADE_UP"))
case("standard_id 归一到未登记标准",
     lambda e: e["source"].__setitem__("standard_id", "ASME B16.34-2009"))
case("body_status 与 registry 不一致",
     lambda e: e["source"].__setitem__("body_status", "PAYWALL"))
case("source 缺 clause", lambda e: e["source"].__setitem__("clause", ""))
case("source 缺 standard_id", lambda e: e["source"].__setitem__("standard_id", ""))

# --- 引用完整性（公式层 ∪ 参数层） ---
case("related 指向不存在的 ID", lambda e: e.__setitem__("related", ["P-NOPE-999"]))
case("cross_refs 指向不存在的 ID",
     lambda e: e["source"].__setitem__("cross_refs", ["F-NOPE-999"]))
case("related 指向真实存在的公式 ID（应通过）",
     lambda e: e.__setitem__("related", [FORMULA_IDS[0]] if FORMULA_IDS else ["F-NONE"]),
     should_fail=False)
case("related 指向真实存在的参数 ID（应通过）",
     lambda e: e.__setitem__("related", [PARAM_IDS[0]] if PARAM_IDS else ["P-NONE"]),
     should_fail=False)

# --- applicability / usage ---
case("applicability.valid_when 为空",
     lambda e: e["applicability"].__setitem__("valid_when", []))
case("applicability.not_valid_when 为空",
     lambda e: e["applicability"].__setitem__("not_valid_when", []))
case("usage.where 为空", lambda e: e["usage"].__setitem__("where", []))
case("usage.how 为空", lambda e: e["usage"].__setitem__("how", ""))

# --- 等级纪律（共享规则） ---
case("evidence.grade 非法", lambda e: e["evidence"].__setitem__("grade", "E9"))
case("evidence.status 非法", lambda e: e["evidence"].__setitem__("status", "FINE"))
case("等级双写不同步",
     lambda e: e["source"].__setitem__("evidence_grade", "E2"))
case("出处不可核(PAYWALL)却给 E2",
     lambda e: (e["source"].__setitem__("body_status", "PAYWALL"),
                e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2")))
case("E2 缺 project_usage",
     lambda e: (e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2"),
                e.pop("project_usage", None)))
case("E2 的 project_usage 全是占位符",
     lambda e: (e["evidence"].__setitem__("grade", "E2"),
                e["source"].__setitem__("evidence_grade", "E2"),
                e.__setitem__("project_usage",
                              [{"task": "N/A", "status": "not-applicable", "note": "x"}])))
case("FULL_TEXT_MIRROR 的 locator 指向不存在的文件",
     lambda e: e["source"].__setitem__(
         "locator", "kb/_evidence/NO_SUCH_FILE.png (PDF p.999)"))

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
