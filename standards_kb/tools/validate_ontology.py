#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / validate_ontology.py —— 本体层一致性校验器

执行 kb/ontology/ontology.yaml 里声明的 INV-01 ~ INV-11，并追加一组
跨层结构一致性检查（枚举合法、映射与条目 1:1、单位与标准号对齐等）。

定位声明（与本体规范一致）:
    本校验器只检查**结构与纪律**，不冒充工程正确性验证。
    它能回答的是"本体内部自洽吗""本体与已核验条目对得上吗"，
    不能回答"这个阈值在工程上对吗" —— 后者由条目的证据等级承担。

严重级别:
    ERROR  —— 违反不变量，必须修
    WARN   —— 疑似问题，需要人工看一眼
    REVIEW —— 「需人工确认」清单（INV-04 明确要求不报错但必须列出来）

退出码:
    0 = 无 ERROR（可含 WARN / REVIEW）
    1 = 有 ERROR
    2 = 校验器自身异常（资产缺失等）

用法:
    python tools/validate_ontology.py
    python tools/validate_ontology.py --json out.json
    python tools/validate_ontology.py --root <另一个库根目录>   # 供自测用
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import onto_model as OM  # noqa: E402

ROOT = OM.ROOT

ERROR = "ERROR"
WARN = "WARN"
REVIEW = "REVIEW"

_ARITH_OK = re.compile(r"^[0-9\.\+\-\*/\(\)\s]+$")


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    invariant: str = ""
    where: str = ""

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "invariant": self.invariant,
            "where": self.where,
            "message": self.message,
        }


@dataclass
class Report:
    findings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, code: str, severity: str, message: str, invariant: str = "", where: str = "") -> None:
        self.findings.append(Finding(code, severity, message, invariant, where))

    def error(self, code: str, message: str, invariant: str = "", where: str = "") -> None:
        self.add(code, ERROR, message, invariant, where)

    def warn(self, code: str, message: str, invariant: str = "", where: str = "") -> None:
        self.add(code, WARN, message, invariant, where)

    def review(self, code: str, message: str, invariant: str = "", where: str = "") -> None:
        self.add(code, REVIEW, message, invariant, where)

    @property
    def n_errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == ERROR)

    @property
    def n_warns(self) -> int:
        return sum(1 for f in self.findings if f.severity == WARN)

    @property
    def n_review(self) -> int:
        return sum(1 for f in self.findings if f.severity == REVIEW)

    def by_severity(self) -> dict:
        out: dict[str, list] = {}
        for f in self.findings:
            out.setdefault(f.severity, []).append(f)
        return out


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def norm_text(s: str) -> str:
    """归一化：压空白、小写，便于子串比对。"""
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def eval_arith(expr: str) -> float | None:
    """受限算术求值：只允许数字与 + - * / ( )，任何其他字符一律拒绝。

    用于复算 relation_note / ratio_note 里的表达式，不做通用求值。
    """
    e = str(expr or "").strip()
    if not e or not _ARITH_OK.match(e):
        return None
    try:
        tree = ast.parse(e, mode="eval")
    except SyntaxError:
        return None
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Load,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            return None
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            return None
    try:
        return float(eval(compile(tree, "<ratio>", "eval"), {"__builtins__": {}}, {}))
    except Exception:
        return None


def expr_head(note: str) -> str:
    """取算式说明里 "=" 之前的部分（若无 "=" 则取整段）。"""
    s = str(note or "").strip()
    if "=" in s:
        s = s.split("=", 1)[0]
    return s.strip()


def domain_enum(root: Path) -> tuple[set[str], list[str]]:
    """从公式/参数 schema 取 domain 枚举（两层必须同枚举）。

    这是"本体不引入新 domain 值"的机器口径来源：不另立一份枚举，
    直接以条目 schema 为准，避免本体与条目各说一套。
    """
    enums: dict[str, set[str]] = {}
    problems: list[str] = []
    for layer in ("formula", "parameter"):
        p = root / "kb" / f"{layer}.schema.json"
        if not p.exists():
            problems.append(f"缺少 schema: kb/{layer}.schema.json")
            continue
        try:
            sch = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            problems.append(f"schema 解析失败 kb/{layer}.schema.json: {exc}")
            continue
        dom = ((sch.get("properties") or {}).get("domain") or {}).get("enum") or []
        enums[layer] = set(dom)
    if len(enums) == 2 and enums["formula"] != enums["parameter"]:
        problems.append(
            "公式层与参数层的 domain 枚举不一致："
            f"仅公式有 {sorted(enums['formula'] - enums['parameter'])}，"
            f"仅参数有 {sorted(enums['parameter'] - enums['formula'])}"
        )
    union: set[str] = set()
    for v in enums.values():
        union |= v
    return union, problems


# --------------------------------------------------------------------------- #
# 主校验
# --------------------------------------------------------------------------- #
def validate(root: Path | None = None) -> Report:
    base = Path(root) if root else ROOT
    rep = Report()
    onto = OM.load(base)

    if not onto.spec:
        rep.error("ONTO-000", "本体规范缺失或为空：kb/ontology/ontology.yaml", "INV-00")
        return rep
    if not onto.quantities:
        rep.error("ONTO-001", "词表缺失或为空：kb/ontology/vocabulary.yaml", "INV-00")
        return rep

    cv = onto.controlled
    dims = set(cv.get("dimension") or [])
    roles = set(cv.get("role") or [])
    rels_v = set(cv.get("relation") or [])
    unit_systems = set(cv.get("unit_system") or [])
    ctx_kinds = set(cv.get("context_kind") or [])

    dom_enum, dom_problems = domain_enum(base)
    for msg in dom_problems:
        rep.error("DOM-000", msg, "INV-00")

    rep.stats = {
        "quantities": len(onto.quantities),
        "contexts": len(onto.contexts),
        "sets": len(onto.sets),
        "occurrences": len(onto.occurrences),
        "criteria": len(onto.criteria),
        "bindings": len(onto.bindings),
        "columns": len(onto.columns),
        "open_questions": len(onto.open_questions),
        "entries": {k: len(v) for k, v in onto.entries.items()},
    }

    # ================================================================== #
    # 受控词表 / 枚举合法性
    # ================================================================== #
    for qid, q in sorted(onto.quantities.items()):
        d = q.get("dimension")
        if d not in dims:
            rep.error("VOC-001", f"物理量 dimension={d!r} 不在受控词表内", "INV-09", qid)
        if dom_enum and q.get("domain") not in dom_enum:
            rep.error(
                "VOC-002",
                f"物理量 domain={q.get('domain')!r} 不在条目 domain 枚举内"
                f"（允许：{sorted(dom_enum)}）",
                "INV-09",
                qid,
            )
        if not str(q.get("canonical_unit") or "").strip():
            rep.error("VOC-003", "canonical_unit 为空（无量纲写 dimensionless）", "INV-09", qid)

    for xid, c in sorted(onto.contexts.items()):
        if ctx_kinds and c.get("kind") not in ctx_kinds:
            rep.error(
                "VOC-004",
                f"上下文 kind={c.get('kind')!r} 不在受控词表内（允许：{sorted(ctx_kinds)}）",
                "INV-08",
                xid,
            )

    # ================================================================== #
    # INV-01 条目映射完整性
    # ================================================================== #
    for layer in OM.LAYERS:
        entries = onto.entries.get(layer) or {}
        mappings = (onto.maps.get(layer) or {}).get("mappings") or {}
        for eid in sorted(set(entries) - set(mappings)):
            rep.error("INV-01", "条目没有本体映射", "INV-01", f"{layer}/{eid}")
        for eid in sorted(set(mappings) - set(entries)):
            rep.error("INV-01", "映射指向不存在的条目", "INV-01", f"{layer}/{eid}")
        dup = [k for k, v in mappings.items() if isinstance(v, list)]
        for k in dup:
            rep.error("INV-01", "同一条目出现多条映射", "INV-01", f"{layer}/{k}")

    # ================================================================== #
    # INV-02 occurrence 唯一归属 + 悬空物理量
    # ================================================================== #
    referenced_qids: set[str] = set()
    for eid, occ in sorted(onto.occurrences.items()):
        qid = occ.get("quantity")
        if not qid:
            rep.error("INV-02", "occurrence 未绑定物理量", "INV-02", eid)
            continue
        if qid not in onto.quantities:
            rep.error("INV-02", f"occurrence 指向未定义的物理量 {qid}", "INV-02", eid)
            continue
        referenced_qids.add(qid)

    for b in onto.bindings:
        qid = b.get("quantity")
        if qid not in onto.quantities:
            rep.error("INV-02", f"变量绑定指向未定义的物理量 {qid}", "INV-02", b.get("bid"))
        else:
            referenced_qids.add(qid)

    for c in onto.columns:
        qid = c.get("quantity_or_text")
        if qid in (None, "", "text"):
            continue
        if qid not in onto.quantities:
            rep.error(
                "INV-02",
                f"表列绑定指向未定义的物理量 {qid}",
                "INV-02",
                c.get("tcid"),
            )
        else:
            referenced_qids.add(qid)

    for qid in sorted(set(onto.quantities) - referenced_qids):
        rep.error(
            "INV-02",
            "物理量既无 occurrence 引用也无变量绑定引用（悬空）",
            "INV-02",
            qid,
        )

    # ================================================================== #
    # INV-03 判据方向不可弱化
    # ================================================================== #
    for eid, occ in sorted(onto.occurrences.items()):
        if occ.get("entry_layer") != "parameter":
            continue
        entry = onto.entries["parameter"].get(eid) or {}
        want = OM.entry_relation(entry)
        got = occ.get("relation")
        if want != got:
            rep.error(
                "INV-03",
                f"本体判据方向 {got!r} 与条目原文方向 {want!r} 不一致",
                "INV-03",
                eid,
            )
        if got is not None and rels_v and got not in rels_v:
            rep.error("INV-03", f"relation={got!r} 不在受控词表内", "INV-03", eid)

    # 角色必须与条目 param_kind 一致（本体不重新分类）
    # 规则见 ontology.yaml controlled_vocabulary.role_vs_param_kind：
    #   role ∈ param_kind 值域      → 必须相等（本体不许重新分类条目）
    #   role ∈ 扩展值 {CONVERSION/SUBSTITUTE/DEFINITION} → 允许细一层，但映射必须写 note
    param_kinds = {
        str(e.get("param_kind"))
        for e in onto.entries["parameter"].values()
        if e.get("param_kind")
    }
    role_ext = {"CONVERSION", "SUBSTITUTE", "DEFINITION"}
    for k in sorted(param_kinds - roles):
        rep.error(
            "VOC-005",
            f"条目 param_kind={k!r} 不在本体 role 受控词表内"
            f"（role 值域必须覆盖 param_kind 值域）",
            "INV-09",
        )
    for eid, occ in sorted(onto.occurrences.items()):
        if occ.get("entry_layer") != "parameter":
            continue
        entry = onto.entries["parameter"].get(eid) or {}
        kind = entry.get("param_kind")
        role = occ.get("role")
        if kind and role and kind != role:
            if role in role_ext:
                m = (onto.maps.get("parameter", {}).get("mappings") or {}).get(eid) or {}
                if not str(m.get("note") or "").strip():
                    rep.error(
                        "INV-03",
                        f"role={role!r} 比条目 param_kind={kind!r} 细一层，"
                        f"但映射未写 note 说明依据",
                        "INV-03",
                        eid,
                    )
            else:
                rep.error(
                    "INV-03",
                    f"本体 role={role!r} 与条目 param_kind={kind!r} 不一致",
                    "INV-03",
                    eid,
                )
        if roles and role not in roles:
            rep.error("INV-03", f"role={role!r} 不在受控词表内", "INV-03", eid)
        us = occ.get("unit_system")
        if unit_systems and us not in unit_systems:
            rep.error("INV-03", f"unit_system={us!r} 不在受控词表内", "INV-03", eid)

    # ================================================================== #
    # INV-04 符号碰撞消歧（不报错，列「需人工确认」）
    # ================================================================== #
    collisions = OM.symbol_collisions(onto)
    for sym, refs in collisions.items():
        for ref in refs:
            if ref["ns"] != "formula":
                continue
            fid = ref["where"]
            m = (onto.maps.get("formula", {}).get("mappings") or {}).get(fid) or {}
            entry = onto.entries["formula"].get(fid) or {}
            notes = " ".join(
                [
                    str(m.get("note") or ""),
                    str(entry.get("usage") or ""),
                    str(entry.get("title_zh") or ""),
                ]
            )
            if sym.lower() not in notes.lower():
                rep.review(
                    "INV-04",
                    f"符号 {sym!r} 绑定到 {ref['qid']}，"
                    f"但 {fid} 的 note/usage 未提及该符号，消歧依据需人工补写",
                    "INV-04",
                    fid,
                )

    # ================================================================== #
    # INV-05 单位制配对双向闭合
    # ================================================================== #
    for s in onto.sets_of_kind("UNIT_CONVERSION"):
        sid = s.get("sid")
        members = list(s.get("members") or [])
        us_m = s.get("us_member")
        si_m = s.get("si_member")
        if not us_m or not si_m:
            rep.error("INV-05", "UNIT_CONVERSION 集合缺少 us_member / si_member", "INV-05", sid)
        for side, mid in (("US", us_m), ("SI", si_m)):
            if mid and mid not in members:
                rep.error("INV-05", f"{side} 侧成员 {mid} 不在 members 里", "INV-05", sid)
        if us_m and si_m and us_m == si_m:
            rep.error("INV-05", "US 与 SI 两侧指向同一条目", "INV-05", sid)
        for mid in members:
            occ = onto.occurrences.get(mid)
            if occ is None:
                rep.error("INV-05", f"成员 {mid} 不是已映射条目", "INV-05", sid)
                continue
            if mid == us_m and occ.get("unit_system") not in ("US", "MIXED"):
                rep.warn(
                    "INV-05",
                    f"US 侧成员 unit_system={occ.get('unit_system')!r}",
                    "INV-05",
                    sid,
                )
            if mid == si_m and occ.get("unit_system") not in ("SI", "MIXED"):
                rep.warn(
                    "INV-05",
                    f"SI 侧成员 unit_system={occ.get('unit_system')!r}",
                    "INV-05",
                    sid,
                )
        if not s.get("expression_ratio"):
            rep.error("INV-05", "UNIT_CONVERSION 集合缺少 expression_ratio", "INV-05", sid)

    # ================================================================== #
    # INV-06 易混对必须显式登记
    # ================================================================== #
    conf_by_q: dict[str, set[str]] = {}
    for s in onto.sets_of_kind("CONFUSABLE"):
        qid = s.get("quantity")
        for mid in s.get("members") or []:
            conf_by_q.setdefault(qid, set()).add(mid)

    crit_by_q: dict[str, dict[str, dict]] = {}
    for cid, c in onto.criteria.items():
        qid = c.get("quantity")
        std = c.get("standard_id") or ""
        crit_by_q.setdefault(qid, {}).setdefault(std, {})[c["entry_id"]] = c

    for qid, by_std in sorted(crit_by_q.items()):
        if len(by_std) < 2:
            continue
        covered = conf_by_q.get(qid, set())
        all_entries = {eid for d in by_std.values() for eid in d}
        for eid in sorted(all_entries - covered):
            rep.error(
                "INV-06",
                f"物理量 {qid} 在多个标准下都有判据，但 {eid} 未登记为易混对"
                f"（须加入某个 CONFUSABLE 集合，或显式声明等价）",
                "INV-06",
                eid,
            )

    # ================================================================== #
    # INV-07 阈值可回溯
    # ================================================================== #
    for cid, c in sorted(onto.criteria.items()):
        eid = c["entry_id"]
        entry = onto.entry_of(eid) or {}
        v = entry.get("value") or {}
        text = OM.entry_text(entry)
        snippet = str((entry.get("source") or {}).get("snippet") or "")
        nums = OM.numbers_in(text)
        num = c.get("threshold_numeric")

        if isinstance(num, (int, float)) and not isinstance(num, bool):
            if any(OM.num_close(float(num), n, rel=1e-9) for n in nums):
                continue  # 阈值数值在条目可回溯文本中直接出现
            # 条目的 canonical 本身是算式时，阈值必须可由该算式复算得到
            canon = str(v.get("canonical") or "")
            expr_val = eval_arith(canon)
            if expr_val is None or not OM.num_close(float(num), expr_val, rel=1e-9):
                rep.error(
                    "INV-07",
                    f"阈值 {num} 既未出现在条目的可回溯文本中，"
                    f"也不能由条目的 canonical 算式 {canon!r} 复算得到",
                    "INV-07",
                    eid,
                )
            else:
                snums = OM.numbers_in(snippet)
                for n in OM.numbers_in(canon):
                    if not any(OM.num_close(n, s, rel=1e-9) for s in snums):
                        rep.warn(
                            "INV-07",
                            f"canonical 算式 {canon!r} 中的数字 {n} 未出现在原文 snippet 里"
                            f"（可能是排印写法差异，需人工确认）",
                            "INV-07",
                            eid,
                        )
            continue

        # 无数值阈值：区间端点必须能回溯
        checked_any = False
        for bound in ("min", "max"):
            b = v.get(bound)
            if isinstance(b, (int, float)) and not isinstance(b, bool):
                checked_any = True
                if not any(OM.num_close(float(b), n, rel=1e-9) for n in nums):
                    rep.error(
                        "INV-07",
                        f"区间端点 {bound}={b} 未出现在条目的可回溯文本中",
                        "INV-07",
                        eid,
                    )
        if checked_any:
            continue

        thr = str(c.get("threshold") or "").strip()
        if thr and norm_text(thr) not in norm_text(text):
            rep.error(
                "INV-07",
                f"阈值文本 {thr!r} 未出现在条目的可回溯文本中",
                "INV-07",
                eid,
            )

    # ================================================================== #
    # INV-08 上下文不得越界
    # ================================================================== #
    for eid, occ in sorted(onto.occurrences.items()):
        for xid in occ.get("contexts") or []:
            if xid not in onto.contexts:
                rep.error("INV-08", f"上下文 {xid} 未在词表中定义", "INV-08", eid)
    for layer in ("formula", "parameter"):
        for eid, m in (onto.maps.get(layer, {}).get("mappings") or {}).items():
            for xid in m.get("contexts") or []:
                if xid not in onto.contexts:
                    rep.error("INV-08", f"上下文 {xid} 未在词表中定义", "INV-08", f"{layer}/{eid}")

    # ================================================================== #
    # INV-09 已在上方 VOC-003 一并执行（canonical_unit 必填）
    # ================================================================== #

    # ================================================================== #
    # INV-10 本体不产生新事实
    # ================================================================== #
    for s in onto.sets:
        sid = s.get("sid")
        kind = s.get("kind")
        members = list(s.get("members") or [])
        # (c) members 必须是真实条目
        for mid in members:
            if onto.layer_of(mid) is None:
                rep.error("INV-10", f"等价集成员 {mid} 不是已映射条目", "INV-10", sid)
        # 集合声明的 quantity 必须存在，且成员确实属于该 quantity
        sq = s.get("quantity")
        if sq:
            if sq not in onto.quantities:
                rep.error("INV-10", f"等价集 quantity {sq} 未在词表中定义", "INV-10", sid)
            for mid in members:
                occ = onto.occurrences.get(mid)
                if occ and occ.get("quantity") != sq:
                    rep.error(
                        "INV-10",
                        f"成员 {mid} 属于 {occ.get('quantity')}，与集合 quantity {sq} 不符",
                        "INV-10",
                        sid,
                    )

        if kind == "CONFUSABLE":
            # (a) 登记的取值必须能在该条目里找到
            for val in s.get("values") or []:
                mid = val.get("entry_id")
                entry = onto.entry_of(mid) or {}
                text = OM.entry_text(entry)
                nums = OM.numbers_in(text)
                raw = val.get("value")
                if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    if not any(OM.num_close(float(raw), n, rel=1e-9) for n in nums):
                        rep.error(
                            "INV-10",
                            f"登记取值 {raw} 未出现在条目 {mid} 的可回溯文本中",
                            "INV-10",
                            sid,
                        )
                else:
                    if norm_text(str(raw)) not in norm_text(text):
                        rep.error(
                            "INV-10",
                            f"登记取值 {raw!r} 未出现在条目 {mid} 的可回溯文本中",
                            "INV-10",
                            sid,
                        )
                si_val = val.get("si_value")
                if isinstance(si_val, (int, float)) and not isinstance(si_val, bool):
                    if not any(OM.num_close(float(si_val), n, rel=1e-9) for n in nums):
                        rep.error(
                            "INV-10",
                            f"登记公制值 {si_val} 未出现在条目 {mid} 的可回溯文本中",
                            "INV-10",
                            sid,
                        )
                # 登记的判据方向必须与条目一致
                want = OM.entry_relation(entry)
                if val.get("relation") and want and val["relation"] != want:
                    rep.error(
                        "INV-10",
                        f"登记判据方向 {val['relation']!r} 与条目方向 {want!r} 不一致",
                        "INV-10",
                        sid,
                    )

        if kind == "UNIT_CONVERSION":
            # (b) expression_ratio 必须可复算
            ratio = s.get("expression_ratio")
            note = s.get("ratio_note") or ""
            expr = expr_head(note)
            val = eval_arith(expr)
            if val is None:
                rep.error(
                    "INV-10",
                    f"ratio_note 不是可求值的算式：{note!r}",
                    "INV-10",
                    sid,
                )
            elif not OM.num_close(float(ratio), val, rel=1e-6):
                rep.error(
                    "INV-10",
                    f"expression_ratio={ratio} 与算式 {expr!r} 的结果 {val!r} 不符"
                    f"（相对偏差 {abs(float(ratio) - val) / max(abs(val), 1e-12):.3e}）",
                    "INV-10",
                    sid,
                )
            # 算式里的数字必须来自两个成员条目
            member_nums: set[float] = set()
            for mid in members:
                entry = onto.entry_of(mid) or {}
                member_nums |= OM.numbers_in(OM.entry_text(entry))
            for n in OM.numbers_in(expr):
                if not any(OM.num_close(n, m, rel=1e-9) for m in member_nums):
                    rep.error(
                        "INV-10",
                        f"算式 {expr!r} 中的数字 {n} 无法在成员条目里找到",
                        "INV-10",
                        sid,
                    )

        if kind == "COLUMN_CORRESPONDENCE":
            for qid in s.get("shared_quantities") or []:
                if qid not in onto.quantities:
                    rep.error("INV-10", f"共享物理量 {qid} 未在词表中定义", "INV-10", sid)
            for nm in s.get("near_miss") or []:
                for key in ("gb_quantity", "gost_quantity"):
                    qid = nm.get(key)
                    if qid and qid not in onto.quantities:
                        rep.error("INV-10", f"近似对物理量 {qid} 未在词表中定义", "INV-10", sid)
                    if not nm.get("verdict"):
                        rep.error("INV-10", "近似对缺少 verdict（必须说明为何不合并）", "INV-10", sid)

    # ================================================================== #
    # INV-11 同名不同 qid 必须合并或显式登记
    # ================================================================== #
    oq_qids: set[str] = set()
    for oq in onto.open_questions:
        for qid in oq.get("quantities") or []:
            oq_qids.add(qid)
    by_name: dict[str, list[str]] = {}
    for qid, q in onto.quantities.items():
        by_name.setdefault(str(q.get("name_zh") or "").strip(), []).append(qid)
    for name, qids in sorted(by_name.items()):
        if not name or len(qids) < 2:
            continue
        for qid in sorted(qids):
            if qid not in oq_qids:
                rep.error(
                    "INV-11",
                    f"物理量名 {name!r} 对应多个 qid（{sorted(qids)}），"
                    f"且 {qid} 未在 open_questions 中登记",
                    "INV-11",
                    qid,
                )

    # ================================================================== #
    # 跨层结构一致性（映射 ↔ 条目 1:1）
    # ================================================================== #
    for fid, m in (onto.maps.get("formula", {}).get("mappings") or {}).items():
        entry = onto.entries["formula"].get(fid)
        if entry is None:
            continue
        want = {v.get("symbol") for v in (entry.get("variables") or []) if v.get("symbol")}
        got = set((m.get("variables") or {}).keys())
        if want != got:
            rep.error(
                "XREF-001",
                f"变量绑定与条目变量符号不一致：缺 {sorted(want - got)}，多 {sorted(got - want)}",
                "INV-01",
                fid,
            )
        rq = m.get("result_quantity")
        if not rq:
            rep.error("XREF-002", "缺少 result_quantity", "INV-02", fid)
        elif rq not in onto.quantities:
            rep.error("XREF-002", f"result_quantity {rq} 未在词表中定义", "INV-02", fid)

    for eid, m in (onto.maps.get("data", {}).get("mappings") or {}).items():
        entry = onto.entries["data"].get(eid)
        if entry is None:
            continue
        want = {c.get("key") for c in (entry.get("columns") or []) if c.get("key")}
        got = set((m.get("columns") or {}).keys())
        if want != got:
            rep.error(
                "XREF-003",
                f"表列映射与条目列不一致：缺 {sorted(want - got)}，多 {sorted(got - want)}",
                "INV-01",
                eid,
            )
        for c in (entry.get("columns") or []):
            key = c.get("key")
            spec = (m.get("columns") or {}).get(key)
            if not spec:
                continue
            wu = str(c.get("unit") or "")
            gu = str(spec.get("unit") or "")
            if wu and gu and wu != gu:
                rep.error(
                    "XREF-004",
                    f"列 {key} 的单位不一致：条目 {wu!r} vs 本体 {gu!r}",
                    "INV-09",
                    eid,
                )
        for field_name in ("standard_id", "clause"):
            ev = entry.get(field_name)
            mv = m.get(field_name)
            if ev and mv and str(ev) != str(mv):
                rep.error(
                    "XREF-005",
                    f"{field_name} 不一致：条目 {ev!r} vs 本体 {mv!r}",
                    "INV-01",
                    eid,
                )

    # 数据表列绑定的物理量必须存在，且 text 列必须显式标 text
    for c in onto.columns:
        qid = c.get("quantity_or_text")
        if qid not in (None, "") and qid != "text" and qid not in onto.quantities:
            rep.error("XREF-006", f"表列物理量 {qid} 未在词表中定义", "INV-02", c.get("tcid"))

    return rep


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def render(rep: Report, onto: OM.Onto) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("standards_kb / 本体层校验报告")
    lines.append("=" * 72)
    st = rep.stats or {}
    lines.append(
        "资产: "
        + f"物理量 {st.get('quantities', 0)} / 上下文 {st.get('contexts', 0)} / "
        + f"等价集 {st.get('sets', 0)} / occurrence {st.get('occurrences', 0)} / "
        + f"判据 {st.get('criteria', 0)} / 变量绑定 {st.get('bindings', 0)} / "
        + f"表列绑定 {st.get('columns', 0)}"
    )
    ent = st.get("entries") or {}
    lines.append(
        "条目: " + ", ".join(f"{k}={v}" for k, v in sorted(ent.items()))
        + f"  | 未决问题登记 {st.get('open_questions', 0)} 组"
    )
    lines.append("")

    by_sev = rep.by_severity()
    for sev, title in ((ERROR, "错误 ERROR"), (WARN, "警告 WARN"), (REVIEW, "需人工确认 REVIEW")):
        items = by_sev.get(sev, [])
        lines.append(f"--- {title}: {len(items)} ---")
        if not items:
            lines.append("  (无)")
        for f in items:
            inv = f" [{f.invariant}]" if f.invariant else ""
            loc = f" @ {f.where}" if f.where else ""
            lines.append(f"  {f.code}{inv}{loc}")
            lines.append(f"      {f.message}")
        lines.append("")

    lines.append("-" * 72)
    lines.append(
        f"结论: ERROR {rep.n_errors} / WARN {rep.n_warns} / REVIEW {rep.n_review}"
        + ("  → 校验通过" if rep.n_errors == 0 else "  → 校验未通过")
    )
    lines.append("（本校验器只查结构与纪律，不构成工程正确性验证）")
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="本体层一致性校验器")
    ap.add_argument("--root", default=None, help="库根目录（默认用本仓库）")
    ap.add_argument("--json", default=None, help="把结果写成 JSON 文件")
    ap.add_argument("--quiet", action="store_true", help="只输出结论行")
    args = ap.parse_args()

    root = Path(args.root) if args.root else ROOT
    try:
        rep = validate(root)
        onto = OM.load(root)
    except Exception as exc:  # pragma: no cover
        print(f"校验器自身异常: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(render(rep, onto))
    else:
        print(f"ERROR {rep.n_errors} / WARN {rep.n_warns} / REVIEW {rep.n_review}")

    if args.json:
        payload = {
            "schema": "standards_kb.ontology.validation/1.0",
            "root": str(root),
            "stats": rep.stats,
            "summary": {
                "error": rep.n_errors,
                "warn": rep.n_warns,
                "review": rep.n_review,
            },
            "findings": [f.as_dict() for f in rep.findings],
        }
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 报告已写出: {args.json}")

    return 1 if rep.n_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
