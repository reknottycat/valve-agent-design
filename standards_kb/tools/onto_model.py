#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / onto_model.py —— 本体层的统一加载与图构建入口

本体层是**独立映射层**：它不改写已核验条目，只声明"这些条目说的是不是同一个东西"。
因此本模块做三件事：

    1. 加载 kb/ontology/ 下的四类资产（规范 / 词表 / 等价集 / 三层映射）
    2. 把映射与已核验条目**对撞**，构建出可查询的图：
         occurrence —— 条目在本体中的投影（物理量 × 标准 × 条款 × 判据）
         binding    —— 公式局部符号 → 全局物理量
         column     —— 数据表列 → 全局物理量
         criterion  —— 由 occurrence 派生的判据视图（不单独存储）
    3. 提供跨层对齐所需的辅助函数（数值提取、有效取值、量纲比对）

为什么单独抽一个模块:
校验器、查询工具、索引生成器都要用同一套图。若三处各写一份加载逻辑,
必然出现"三个口径不一致"—— 而口径不一致会被当成"数据没问题"。
这与 tools/kb_entries.py 存在的理由完全一样。

occurrence 分型（见 ontology.yaml 的 occurrence_kinds）:
    VALUE  参数条目 —— 某物理量在某标准某条款下的一个取值，带判据方向
    RESULT 公式条目 —— 该公式算出哪个物理量（公式不是判据，故无 relation）
    (数据表条目不产生 occurrence，其列走 TableColumn)

用法:
    import onto_model as OM
    onto = OM.load()
    onto.occurrences           # entry_id -> occurrence dict
    onto.criteria              # cid -> criterion dict（派生）
    onto.bindings              # list of binding dict
    onto.columns               # list of column dict
    onto.qids                  # 词表里的全部物理量 ID
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ONT_DIR = ROOT / "kb" / "ontology"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_entries  # noqa: E402

LAYERS = ("formula", "parameter", "data")

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_SPACES = "   "
# 数字之间的空格（千分位/窄空格/全角空格）→ 视为无分隔
_GAP_RE = re.compile(r"(?<=\d)[   ]+(?=\d)")


# --------------------------------------------------------------------------- #
# 数值工具
# --------------------------------------------------------------------------- #
def numbers_in(text: str) -> set[float]:
    """从一段文本里抽出所有可比较的数值。

    处理三种千分位写法：逗号（2,407 / 1,100）、空格（1 100 / 5 092）、无分隔。
    文本里同一句话可能出现多种写法，所以三种变体都抽一遍再合并。
    """
    if not text:
        return set()
    out: set[float] = set()
    variants = [
        text,
        text.replace(",", ""),
        _GAP_RE.sub("", text.replace(",", "")),
    ]
    for v in variants:
        for m in _NUM_RE.findall(v):
            try:
                out.add(float(m))
            except ValueError:
                pass
    return out


def num_close(a: float, b: float, rel: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b)))


def effective_value(entry: dict) -> str:
    """取条目的"有效取值"字符串 —— 用于跨标准比对。

    优先用 value.display（人读的完整写法，如 "1,100 (595) °F(°C)"），
    没有则退回 value.canonical。两者都不含单位制差异信息时再补 unit_text。
    """
    v = entry.get("value") or {}
    disp = v.get("display")
    canon = v.get("canonical")
    base = str(disp if disp not in (None, "") else canon if canon not in (None, "") else "")
    unit = v.get("unit_text")
    if unit and base and str(unit) not in base:
        base = f"{base} {unit}"
    return base.strip()


def entry_text(entry: dict) -> str:
    """条目里可用于"取值回溯"的全部文本。"""
    v = entry.get("value") or {}
    src = entry.get("source") or {}
    parts = [
        str(entry.get("title_zh") or ""),
        str(entry.get("title_en") or ""),
        str(v.get("canonical") or ""),
        str(v.get("display") or ""),
        str(src.get("snippet") or ""),
    ]
    for alt in v.get("alt_values") or []:
        parts.append(str(alt.get("canonical") or ""))
        parts.append(str(alt.get("display") or ""))
    return "\n".join(p for p in parts if p)


def entry_numeric(entry: dict) -> float | None:
    """条目取值的数值形态（用于复算比值）。"""
    v = entry.get("value") or {}
    num = v.get("numeric")
    if isinstance(num, (int, float)) and not isinstance(num, bool):
        return float(num)
    nums = numbers_in(str(v.get("canonical") or ""))
    if not nums:
        return None
    return sorted(nums)[0]


def entry_relation(entry: dict) -> str | None:
    """条目判据方向（参数层 value.relation）。"""
    v = entry.get("value") or {}
    rel = v.get("relation")
    return str(rel) if rel not in (None, "") else None


def entry_standard(entry: dict) -> str:
    """条目的标准全名。数据条目的 standard_id 在顶层，公式/参数在 source 里。"""
    src = entry.get("source") or {}
    for cand in (src.get("standard_id"), entry.get("standard_id")):
        if cand:
            return str(cand)
    return ""


def entry_clause(entry: dict) -> str:
    src = entry.get("source") or {}
    for cand in (src.get("clause"), entry.get("clause")):
        if cand:
            return str(cand)
    return ""


# --------------------------------------------------------------------------- #
# 图模型
# --------------------------------------------------------------------------- #
@dataclass
class Onto:
    spec: dict = field(default_factory=dict)
    vocab: dict = field(default_factory=dict)
    rels: dict = field(default_factory=dict)
    maps: dict = field(default_factory=dict)          # layer -> mapping doc
    entries: dict = field(default_factory=dict)        # layer -> {id: entry}
    quantities: dict = field(default_factory=dict)     # qid -> quantity
    contexts: dict = field(default_factory=dict)       # xid -> context
    sets: list = field(default_factory=list)
    occurrences: dict = field(default_factory=dict)    # entry_id -> occurrence
    bindings: list = field(default_factory=list)       # formula variable bindings
    columns: list = field(default_factory=list)         # table column bindings
    criteria: dict = field(default_factory=dict)       # cid -> criterion（派生）
    open_questions: list = field(default_factory=list)

    # ---------------- 便捷视图 ----------------
    @property
    def qids(self) -> set[str]:
        return set(self.quantities)

    @property
    def xids(self) -> set[str]:
        return set(self.contexts)

    @property
    def controlled(self) -> dict:
        """本体规范里的受控词表。"""
        return self.spec.get("controlled_vocabulary") or {}

    def qname(self, qid: str) -> str:
        q = self.quantities.get(qid) or {}
        return str(q.get("name_zh") or qid)

    def xname(self, xid: str) -> str:
        c = self.contexts.get(xid) or {}
        return str(c.get("name_zh") or xid)

    def layer_of(self, entry_id: str) -> str | None:
        for layer, table in self.entries.items():
            if entry_id in table:
                return layer
        return None

    def entry_of(self, entry_id: str) -> dict | None:
        layer = self.layer_of(entry_id)
        if layer is None:
            return None
        return self.entries[layer].get(entry_id)

    def quantity_of(self, entry_id: str) -> str | None:
        occ = self.occurrences.get(entry_id)
        return occ.get("quantity") if occ else None

    def occurrences_of(self, qid: str) -> list[dict]:
        return [o for o in self.occurrences.values() if o.get("quantity") == qid]

    def criteria_of(self, qid: str) -> list[dict]:
        return [c for c in self.criteria.values() if c.get("quantity") == qid]

    def sets_of_kind(self, kind: str) -> list[dict]:
        return [s for s in self.sets if s.get("kind") == kind]

    def standard_of(self, entry_id: str) -> str:
        e = self.entry_of(entry_id)
        if e is None:
            return ""
        return entry_standard(e)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_map(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load(root: Path | None = None) -> Onto:
    """加载本体层全部资产并构建图。"""
    base = Path(root) if root else ROOT
    ont_dir = base / "kb" / "ontology"

    onto = Onto()
    onto.spec = _load_yaml(ont_dir / "ontology.yaml")
    onto.vocab = _load_yaml(ont_dir / "vocabulary.yaml")
    onto.rels = _load_yaml(ont_dir / "relations.yaml")
    onto.open_questions = list(onto.vocab.get("open_questions") or [])

    for q in onto.vocab.get("quantities") or []:
        if isinstance(q, dict) and q.get("qid"):
            onto.quantities[q["qid"]] = q
    for c in onto.vocab.get("contexts") or []:
        if isinstance(c, dict) and c.get("xid"):
            onto.contexts[c["xid"]] = c

    onto.sets = list(onto.rels.get("sets") or [])

    for layer, fname in (
        ("formula", "formulas.json"),
        ("parameter", "parameters.json"),
        ("data", "data.json"),
    ):
        doc = _load_map(ont_dir / "mappings" / fname)
        onto.maps[layer] = doc

    onto.entries = {
        "formula": {e["id"]: e for e in kb_entries.formula_entries(base) if e.get("id")},
        "parameter": {e["id"]: e for e in kb_entries.param_entries(base) if e.get("id")},
        "data": {e["id"]: e for e in kb_entries.data_entries(base) if e.get("id")},
    }

    # ---- occurrence VALUE：参数条目 → 取值型投影 ----
    for eid, m in (onto.maps.get("parameter", {}).get("mappings") or {}).items():
        entry = onto.entries["parameter"].get(eid)
        src = (entry or {}).get("source") or {}
        onto.occurrences[eid] = {
            "oid": f"O:{eid}",
            "entry_id": eid,
            "entry_layer": "parameter",
            "occurrence_kind": "VALUE",
            "quantity": m.get("quantity"),
            "role": m.get("role"),
            "relation": m.get("relation"),
            "unit_system": m.get("unit_system"),
            "contexts": list(m.get("contexts") or []),
            "standard_id": src.get("standard_id"),
            "clause": src.get("clause"),
            "note": m.get("note"),
        }

    # ---- occurrence RESULT：公式条目 → 结果型投影 ----
    for fid, m in (onto.maps.get("formula", {}).get("mappings") or {}).items():
        entry = onto.entries["formula"].get(fid)
        src = (entry or {}).get("source") or {}
        onto.occurrences[fid] = {
            "oid": f"O:{fid}",
            "entry_id": fid,
            "entry_layer": "formula",
            "occurrence_kind": "RESULT",
            "quantity": m.get("result_quantity"),
            "role": None,
            "relation": None,
            "unit_system": None,
            "contexts": [],
            "standard_id": src.get("standard_id"),
            "clause": src.get("clause"),
            "note": m.get("note"),
        }

    # ---- criterion：occurrence 的派生视图（relation 非空即成判据） ----
    for eid, occ in onto.occurrences.items():
        if not occ.get("relation"):
            continue
        entry = onto.entry_of(eid) or {}
        v = entry.get("value") or {}
        onto.criteria[f"C:{eid}"] = {
            "cid": f"C:{eid}",
            "entry_id": eid,
            "quantity": occ.get("quantity"),
            "relation": occ.get("relation"),
            "threshold": v.get("canonical"),
            "threshold_numeric": v.get("numeric"),
            "unit": v.get("unit_text"),
            "contexts": list(occ.get("contexts") or []),
            "standard_id": occ.get("standard_id"),
            "clause": occ.get("clause"),
        }

    # ---- binding：公式局部符号 → 全局物理量 ----
    for fid, m in (onto.maps.get("formula", {}).get("mappings") or {}).items():
        for sym, qid in (m.get("variables") or {}).items():
            onto.bindings.append(
                {
                    "bid": f"B:{fid}:{sym}",
                    "formula_id": fid,
                    "local_symbol": sym,
                    "quantity": qid,
                }
            )

    # ---- column：数据表列 → 全局物理量 ----
    for eid, m in (onto.maps.get("data", {}).get("mappings") or {}).items():
        for col, spec in (m.get("columns") or {}).items():
            onto.columns.append(
                {
                    "tcid": f"TC:{eid}:{col}",
                    "entry_id": eid,
                    "column_key": col,
                    "quantity_or_text": (spec or {}).get("quantity_or_text"),
                    "unit": (spec or {}).get("unit"),
                }
            )

    return onto


def symbol_index(onto: Onto) -> dict[str, list[dict]]:
    """符号 → 引用位置表。区分两个命名空间。

    formula 命名空间：公式里的局部符号（读者在公式上看到的那个字母）
    vocab   命名空间：词表 quantity 的 symbol_candidates（标准表里的列符号）

    两个命名空间之间也会撞（如公式的 L=升程 vs 法兰表的 L=螺栓孔径），
    所以额外提供 casefold 视图。
    """
    idx: dict[str, list[dict]] = {}
    for b in onto.bindings:
        idx.setdefault(b["local_symbol"], []).append(
            {"ns": "formula", "qid": b["quantity"], "where": b["formula_id"]}
        )
    for qid, q in onto.quantities.items():
        for sym in q.get("symbol_candidates") or []:
            idx.setdefault(sym, []).append(
                {"ns": "vocab", "qid": qid, "where": f"{qid} (symbol_candidates)"}
            )
    return idx


def symbol_collisions(onto: Onto) -> dict[str, list[dict]]:
    """符号碰撞表：同一符号绑定到多个不同物理量。

    返回 {symbol: [引用位点...]}，只保留"指向 ≥2 个不同 qid"的符号。
    """
    out: dict[str, list[dict]] = {}
    for sym, refs in symbol_index(onto).items():
        qids = {r["qid"] for r in refs}
        if len(qids) >= 2:
            out[sym] = refs
    return dict(sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass
    onto = load()
    print(f"本体规范 meta.version : {onto.spec.get('meta', {}).get('version')}")
    print(f"词表: quantity {len(onto.quantities)} 个, context {len(onto.contexts)} 个")
    print(f"等价集 {len(onto.sets)} 组: {sorted({s.get('kind') for s in onto.sets})}")
    print(f"映射: " + ", ".join(f"{k}={len((v.get('mappings') or {}))}" for k, v in onto.maps.items()))
    kinds: dict[str, int] = {}
    for o in onto.occurrences.values():
        kinds[o["occurrence_kind"]] = kinds.get(o["occurrence_kind"], 0) + 1
    print(
        "图: occurrence "
        + str(len(onto.occurrences))
        + " ("
        + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
        + f"), criterion {len(onto.criteria)}, binding {len(onto.bindings)}, column {len(onto.columns)}"
    )
    print(f"条目: " + ", ".join(f"{k}={len(v)}" for k, v in onto.entries.items()))
    print(f"未决问题登记 {len(onto.open_questions)} 组")
    coll = symbol_collisions(onto)
    print(f"符号碰撞 {len(coll)} 组: " + ", ".join(f"{s}×{len({r['qid'] for r in v})}" for s, v in coll.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
