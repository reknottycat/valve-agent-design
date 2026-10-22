#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / selftest_ontology_validator.py —— 本体校验器的负向注入自测

为什么必须有这个:
    校验器"全绿"有两种可能 —— 库真的自洽，或者校验器根本没在查。
    两者从输出上一模一样。唯一的分法是**故意把库改坏，看校验器抓不抓得到**。

做法:
    1. 把 kb/ 相关部分复制到临时目录（不动真库）
    2. 逐个注入一种违规（改方向、删映射、造幽灵引用、篡改比值…）
    3. 跑校验器，断言**预期的不变量代码**出现在结果里
    4. 收尾再跑一遍未改动的副本，断言 0 ERROR（防止"什么都报"式的假阳性）

每个用例只断言"预期代码出现"，不要求"只有这一个错误"——
因为一次违规常常同时触发多条不变量（例如删掉一个公式变量绑定，
既破坏映射 1:1，也让某个物理量变成悬空）。

用法:
    python tools/selftest_ontology_validator.py
    python tools/selftest_ontology_validator.py --verbose
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_ontology as VO  # noqa: E402

ROOT = VO.ROOT

# 需要复制的子集：本体资产 + 三层条目 + 三个 schema
COPY_ITEMS = [
    "kb/ontology",
    "kb/formulas",
    "kb/parameters",
    "kb/data",
    "kb/formula.schema.json",
    "kb/parameter.schema.json",
    "kb/data.schema.json",
]


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def _copy_kb(dest: Path) -> None:
    for item in COPY_ITEMS:
        src = ROOT / item
        if not src.exists():
            raise SystemExit(f"源缺失，无法复制: {src}")
        dst = dest / item
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def _yaml_p(root: Path, rel: str) -> Path:
    return root / "kb" / "ontology" / rel


def _json_p(root: Path, rel: str) -> Path:
    return root / "kb" / "ontology" / rel


def _load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _dump_yaml(p: Path, d) -> None:
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _dump_json(p: Path, d) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# 层名（本体三层的逻辑名）与目录名（磁盘上的文件夹名）不是同一个词。
# 之前直接用 layer 拼路径，去找 kb/formula 这个根本不存在的目录，
# 结果所有公式层变异都以 KeyError 收场 —— 假失败。
LAYER_DIR = {"formula": "formulas", "parameter": "parameters", "data": "data"}


def _entry_file(root: Path, layer: str, entry_id: str) -> Path:
    """在某一层里找到包含指定 entry id 的 JSON 文件。"""
    folder = root / "kb" / LAYER_DIR.get(layer, layer)
    for f in sorted(folder.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ents = data["entries"] if isinstance(data, dict) and "entries" in data else data
        if isinstance(ents, list) and any(isinstance(e, dict) and e.get("id") == entry_id for e in ents):
            return f
    raise KeyError(f"在 {layer} 层找不到条目 {entry_id}")


def _patch_entry(root: Path, layer: str, entry_id: str, fn) -> None:
    """对某个条目应用原地修改函数。"""
    f = _entry_file(root, layer, entry_id)
    data = json.loads(f.read_text(encoding="utf-8"))
    ents = data["entries"] if isinstance(data, dict) and "entries" in data else data
    for e in ents:
        if isinstance(e, dict) and e.get("id") == entry_id:
            fn(e)
            break
    else:
        raise KeyError(entry_id)
    if isinstance(data, dict) and "entries" in data:
        data["entries"] = ents
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        f.write_text(json.dumps(ents, ensure_ascii=False, indent=2), encoding="utf-8")


def _mut_first_set(root: Path, kind: str, fn) -> None:
    """就地修改 relations.yaml 里第一个指定 kind 的等价集。

    注意：必须在**同一份**已加载的文档上查找并修改 ——
    早期版本另加载了一份再改副本，结果写回的是未改动的原件，
    表现为"注入的违规一条都没被抓到"，是典型的假阴性陷阱。
    """
    p = _yaml_p(root, "relations.yaml")
    rels = _load_yaml(p)
    for s in rels.get("sets") or []:
        if s.get("kind") == kind:
            fn(s)
            break
    else:
        raise KeyError(f"找不到 kind={kind} 的等价集")
    _dump_yaml(p, rels)


# --------------------------------------------------------------------------- #
# 变异用例
# --------------------------------------------------------------------------- #
def mut_missing_param_mapping(root: Path) -> None:
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    del d["mappings"]["P-TEST-001"]
    _dump_json(p, d)


def mut_ghost_param_mapping(root: Path) -> None:
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-NOPE-999"] = {
        "quantity": "Q:TEST:WATER_FLOW_CONSTANT",
        "role": "CONSTANT",
        "relation": "=",
        "unit_system": "US",
        "contexts": [],
    }
    _dump_json(p, d)


def mut_missing_data_mapping(root: Path) -> None:
    p = _json_p(root, "mappings/data.json")
    d = _load_json(p)
    key = sorted(d["mappings"])[0]
    del d["mappings"][key]
    _dump_json(p, d)


def mut_drop_formula_variable(root: Path) -> None:
    p = _json_p(root, "mappings/formulas.json")
    d = _load_json(p)
    fm = d["mappings"]["F-STR-001"]
    fm["variables"].pop("p", None)
    _dump_json(p, d)


def mut_occurrence_to_unknown_qid(root: Path) -> None:
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-TEST-001"]["quantity"] = "Q:NOPE:NOT_A_QUANTITY"
    _dump_json(p, d)


def mut_drop_dangling_quantity(root: Path) -> None:
    """删掉一个只被公式变量绑定引用的物理量 → 绑定悬空。"""
    import onto_model as OM

    onto = OM.load(root)
    bound_only = [
        qid
        for qid in onto.qids
        if not onto.occurrences_of(qid) and any(b["quantity"] == qid for b in onto.bindings)
    ]
    if not bound_only:
        raise RuntimeError("找不到只被绑定引用的物理量，无法构造该用例")
    target = sorted(bound_only)[0]
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    v["quantities"] = [q for q in v["quantities"] if q.get("qid") != target]
    _dump_yaml(p, v)


def mut_weaken_relation(root: Path) -> None:
    """把 P-MAT-026 的严格大于弱化成大于等于。"""
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-MAT-026"]["relation"] = ">="
    _dump_json(p, d)


def mut_role_mismatch(root: Path) -> None:
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-TEST-001"]["role"] = "LIMIT"
    _dump_json(p, d)


def mut_extension_role_without_note(root: Path) -> None:
    """扩展角色（DEFINITION）但映射不写 note → 违规。"""
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-TEST-027"].pop("note", None)
    _dump_json(p, d)


def mut_drop_collision_note(root: Path) -> None:
    """抹掉符号碰撞的消歧说明 → 触发「需人工确认」清单。

    做法：找一个确实发生碰撞的公式符号，然后把三处可能的说明来源
    （映射 note、条目 usage、条目标题）全部清掉 —— 只剩"没有任何说明"这一种状态。
    """
    import onto_model as OM

    onto = OM.load(root)
    coll = OM.symbol_collisions(onto)
    target = None
    for sym, refs in coll.items():
        for ref in refs:
            if ref["ns"] == "formula":
                target = (sym, ref["where"])
                break
        if target:
            break
    if not target:
        raise RuntimeError("找不到公式命名空间的符号碰撞，无法构造该用例")
    sym, fid = target

    p = _json_p(root, "mappings/formulas.json")
    d = _load_json(p)
    (d["mappings"].get(fid) or {}).pop("note", None)
    _dump_json(p, d)

    def _blank(e: dict) -> None:
        e["usage"] = ""
        e["title_zh"] = "X"

    _patch_entry(root, "formula", fid, _blank)


def mut_drop_si_member(root: Path) -> None:
    _mut_first_set(root, "UNIT_CONVERSION", lambda s: s.pop("si_member", None))


def mut_drop_confusable_member(root: Path) -> None:
    """从一个 CONFUSABLE 集合里删掉一个真实成员 -> 触发 INV-06。

    INV-06 的判定口径是：某个物理量在 >=2 个标准下都有判据时，
    这些条目必须全部出现在某个同 quantity 的 CONFUSABLE 集合里。
    所以要删的必须是「删掉之后就不再被任何同 quantity 集合覆盖」的成员 ——
    删一个在别的集合里还有备份的成员是测不出 INV-06 的。
    """
    import onto_model as OM

    onto = OM.load(root)

    crit_by_q: dict = {}
    for c in onto.criteria.values():
        crit_by_q.setdefault(c.get("quantity"), {}).setdefault(
            c.get("standard_id") or "", set()
        ).add(c["entry_id"])

    conf_sets = list(onto.sets_of_kind("CONFUSABLE"))

    target_sid = None
    drop_id = None
    for s in conf_sets:
        q = s.get("quantity")
        if len(crit_by_q.get(q) or {}) < 2:
            continue  # 该物理量不在多个标准下都有判据，删了也测不出 INV-06
        others = set()
        for o in conf_sets:
            if o.get("sid") != s.get("sid") and o.get("quantity") == q:
                others.update(o.get("members") or [])
        for mid in list(s.get("members") or []):
            if mid not in others:
                target_sid = s.get("sid")
                drop_id = mid
                break
        if target_sid:
            break

    if not target_sid:
        raise RuntimeError("找不到可安全移除的 CONFUSABLE 成员，无法构造该用例")

    p = _yaml_p(root, "relations.yaml")
    rels = _load_yaml(p)
    for s in rels.get("sets") or []:
        if s.get("sid") == target_sid:
            s["members"] = [m for m in (s.get("members") or []) if m != drop_id]
            break
    else:
        raise KeyError(target_sid)
    _dump_yaml(p, rels)


def mut_numeric_not_traceable(root: Path) -> None:
    """把条目的数值改成与 canonical 不符 → 阈值不可回溯。"""
    _patch_entry(
        root,
        "parameters",
        "P-MAT-001",
        lambda e: (e.get("value") or {}).update({"numeric": 0.451234}),
    )


def mut_unknown_context(root: Path) -> None:
    p = _json_p(root, "mappings/parameters.json")
    d = _load_json(p)
    d["mappings"]["P-TEST-001"]["contexts"] = list(
        d["mappings"]["P-TEST-001"].get("contexts") or []
    ) + ["X:NOPE:NOT_A_CONTEXT"]
    _dump_json(p, d)


def mut_empty_canonical_unit(root: Path) -> None:
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    for q in v["quantities"]:
        if q.get("qid") == "Q:MAT:CARBON_EQUIVALENT":
            q["canonical_unit"] = ""
            break
    _dump_yaml(p, v)


def mut_confusable_value_fabricated(root: Path) -> None:
    _mut_first_set(
        root, "CONFUSABLE", lambda s: s["values"][0].__setitem__("value", 0.999999)
    )


def mut_expression_ratio_wrong(root: Path) -> None:
    _mut_first_set(
        root, "UNIT_CONVERSION", lambda s: s.__setitem__("expression_ratio", 1.234567)
    )


def mut_ratio_note_fabricated(root: Path) -> None:
    _mut_first_set(root, "UNIT_CONVERSION", lambda s: s.__setitem__("ratio_note", "5.092 / 1234"))


def mut_member_not_real(root: Path) -> None:
    _mut_first_set(
        root,
        "CONFUSABLE",
        lambda s: s.__setitem__("members", ["P-NOPE-999"] + list(s["members"])[1:]),
    )


def mut_same_name_new_qid(root: Path) -> None:
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    v["quantities"].append(
        {
            "qid": "Q:MAT:CARBON_EQUIVALENT_COPY",
            "name_zh": "碳当量 CE",
            "name_en": "carbon equivalent (duplicate)",
            "domain": "MATE",
            "dimension": "DIMENSIONLESS",
            "canonical_unit": "dimensionless",
        }
    )
    _dump_yaml(p, v)


def mut_data_column_dropped(root: Path) -> None:
    p = _json_p(root, "mappings/data.json")
    d = _load_json(p)
    key = sorted(d["mappings"])[0]
    cols = d["mappings"][key]["columns"]
    cols.pop(sorted(cols)[0])
    _dump_json(p, d)


def mut_data_column_unit(root: Path) -> None:
    p = _json_p(root, "mappings/data.json")
    d = _load_json(p)
    key = sorted(d["mappings"])[0]
    cols = d["mappings"][key]["columns"]
    ck = sorted(cols)[0]
    cols[ck]["unit"] = "banana"
    _dump_json(p, d)


def mut_data_standard_mismatch(root: Path) -> None:
    p = _json_p(root, "mappings/data.json")
    d = _load_json(p)
    key = sorted(d["mappings"])[0]
    d["mappings"][key]["standard_id"] = "NOT THE REAL STANDARD"
    _dump_json(p, d)


def mut_bad_dimension(root: Path) -> None:
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    for q in v["quantities"]:
        if q.get("qid") == "Q:MAT:CARBON_EQUIVALENT":
            q["dimension"] = "BANANA"
            break
    _dump_yaml(p, v)


def mut_bad_domain(root: Path) -> None:
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    for q in v["quantities"]:
        if q.get("qid") == "Q:MAT:CARBON_EQUIVALENT":
            q["domain"] = "BANANA"
            break
    _dump_yaml(p, v)


def mut_bad_context_kind(root: Path) -> None:
    p = _yaml_p(root, "vocabulary.yaml")
    v = _load_yaml(p)
    for c in v["contexts"]:
        if c.get("xid") == "X:UNIT_SYSTEM:US":
            c["kind"] = "BANANA"
            break
    _dump_yaml(p, v)


def mut_param_kind_not_in_role_vocab(root: Path) -> None:
    _patch_entry(root, "parameters", "P-TEST-001", lambda e: e.update({"param_kind": "BANANA"}))


# --------------------------------------------------------------------------- #
# 用例表：(名称, 变异函数, 期望出现的代码, 期望严重级别)
# --------------------------------------------------------------------------- #
CASES = [
    ("漏映射-参数", mut_missing_param_mapping, "INV-01", VO.ERROR),
    ("幽灵映射-参数", mut_ghost_param_mapping, "INV-01", VO.ERROR),
    ("漏映射-数据", mut_missing_data_mapping, "INV-01", VO.ERROR),
    ("公式变量绑定与条目不一致", mut_drop_formula_variable, "XREF-001", VO.ERROR),
    ("occurrence 指向未定义物理量", mut_occurrence_to_unknown_qid, "INV-02", VO.ERROR),
    ("物理量悬空（绑定指向已删除的量）", mut_drop_dangling_quantity, "INV-02", VO.ERROR),
    ("判据方向被弱化", mut_weaken_relation, "INV-03", VO.ERROR),
    ("角色与条目分类不符", mut_role_mismatch, "INV-03", VO.ERROR),
    ("扩展角色但缺 note", mut_extension_role_without_note, "INV-03", VO.ERROR),
    ("符号碰撞缺消歧说明", mut_drop_collision_note, "INV-04", VO.REVIEW),
    ("US/SI 配对缺一侧", mut_drop_si_member, "INV-05", VO.ERROR),
    ("易混对漏登记成员", mut_drop_confusable_member, "INV-06", VO.ERROR),
    ("阈值数值不可回溯", mut_numeric_not_traceable, "INV-07", VO.ERROR),
    ("上下文越界", mut_unknown_context, "INV-08", VO.ERROR),
    ("物理量缺 canonical_unit", mut_empty_canonical_unit, "VOC-003", VO.ERROR),
    ("易混对登记值凭空捏造", mut_confusable_value_fabricated, "INV-10", VO.ERROR),
    ("expression_ratio 与算式不符", mut_expression_ratio_wrong, "INV-10", VO.ERROR),
    ("比值算式含凭空数字", mut_ratio_note_fabricated, "INV-10", VO.ERROR),
    ("等价集成员不存在", mut_member_not_real, "INV-10", VO.ERROR),
    ("同名不同 qid 未登记", mut_same_name_new_qid, "INV-11", VO.ERROR),
    ("表列映射与条目列不一致", mut_data_column_dropped, "XREF-003", VO.ERROR),
    ("表列单位与条目不一致", mut_data_column_unit, "XREF-004", VO.ERROR),
    ("数据映射标准号与条目不一致", mut_data_standard_mismatch, "XREF-005", VO.ERROR),
    ("物理量 dimension 非法", mut_bad_dimension, "VOC-001", VO.ERROR),
    ("物理量 domain 非法", mut_bad_domain, "VOC-002", VO.ERROR),
    ("上下文 kind 非法", mut_bad_context_kind, "VOC-004", VO.ERROR),
    ("条目 param_kind 不在 role 词表", mut_param_kind_not_in_role_vocab, "VOC-005", VO.ERROR),
]


def run_case(name: str, mutate, code: str, severity: str, verbose: bool) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="kb_onto_selftest_") as td:
        tmp = Path(td)
        _copy_kb(tmp)
        try:
            mutate(tmp)
        except Exception as exc:
            return False, f"变异构造失败: {exc}"
        try:
            rep = VO.validate(tmp)
        except Exception as exc:
            return False, f"校验器异常: {exc}"
        hits = [f for f in rep.findings if f.code == code and f.severity == severity]
        if hits:
            detail = hits[0].message
            return True, detail
        got = sorted({f"{f.code}/{f.severity}" for f in rep.findings})
        return False, f"未抓到 {code}/{severity}；实际结果: {got}"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="本体校验器负向注入自测")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("=" * 72)
    print("standards_kb / 本体校验器负向注入自测")
    print("=" * 72)

    # 0) 基线：未改动的副本必须是 0 ERROR
    with tempfile.TemporaryDirectory(prefix="kb_onto_selftest_base_") as td:
        tmp = Path(td)
        _copy_kb(tmp)
        base = VO.validate(tmp)
    print(f"基线（未改动副本）: ERROR {base.n_errors} / WARN {base.n_warns} / REVIEW {base.n_review}")
    if base.n_errors:
        print("  ✗ 基线就不干净，自测无意义 —— 先修本体库")
        for f in base.findings:
            if f.severity == VO.ERROR:
                print(f"    {f.code} @ {f.where}: {f.message}")
        return 1
    print("  ✓ 基线干净")
    print("")

    passed = 0
    failed: list[tuple[str, str]] = []
    for name, mutate, code, severity in CASES:
        ok, detail = run_case(name, mutate, code, severity, args.verbose)
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name}  → 期望 {code}/{severity}")
        if ok:
            passed += 1
            if args.verbose:
                print(f"      {detail}")
        else:
            failed.append((name, detail))
            print(f"      {detail}")

    print("")
    print("-" * 72)
    print(f"结论: {passed}/{len(CASES)} 用例通过")
    if failed:
        print("失败用例:")
        for name, detail in failed:
            print(f"  - {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
