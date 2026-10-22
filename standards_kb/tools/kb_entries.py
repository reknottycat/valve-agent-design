#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / kb_entries.py —— 三类知识对象的统一加载入口

知识库现在有三类知识对象,各有一层目录、一套 schema:

    公式条目    kb/formulas/*.json     JSON 数组            F-XXX-NNN
    数据表条目  kb/data/*.json         {"entries":[...]}    D-XXX-NNN
    参数条目    kb/parameters/*.json   JSON 数组            P-XXX-NNN

为什么要有这个模块:
公式层和参数层会**互相引用** —— 公式要指向它用的参数(P-TEST-021 等),
参数要指向它依赖的公式(F-TEST-001 等)。所以引用完整性检查必须用
**合并后的 ID 集合**,不能只看单层。两边各写一份加载逻辑必然漂移,
而"两个校验器口径不一致"本身就是一个会被当成"数据没问题"的隐性缺陷。

ID 命名空间天然不冲突(前缀不同),但重复 ID 仍需在层内检查。

用法:
    import kb_entries as K
    K.formula_entries()   # list[dict]
    K.param_entries()     # list[dict]
    K.known_ids()         # 公式 + 参数 的合并 ID 集合
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORM_DIR = ROOT / "kb" / "formulas"
PARAM_DIR = ROOT / "kb" / "parameters"
DATA_DIR = ROOT / "kb" / "data"

FORMULA_PREFIX = "F-"
PARAM_PREFIX = "P-"
DATA_PREFIX = "D-"


def load_json(path: Path) -> object | None:
    """读一个 JSON 文件。解析失败返回 None(调用方决定怎么报)。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _flatten(data: object) -> list[dict]:
    """把两种文件形态都摊平成 list[dict]。

    公式/参数文件是 JSON 数组;数据文件是 {"entries":[...]} 字典。
    """
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict):
        ents = data.get("entries")
        if isinstance(ents, list):
            return [e for e in ents if isinstance(e, dict)]
    return []


def load_dir(directory: Path) -> list[dict]:
    """加载一个目录下的全部条目文件。"""
    out: list[dict] = []
    if not directory.exists():
        return out
    for f in sorted(directory.glob("*.json")):
        out.extend(_flatten(load_json(f)))
    return out


def formula_entries() -> list[dict]:
    return load_dir(FORM_DIR)


def param_entries() -> list[dict]:
    return load_dir(PARAM_DIR)


def data_entries() -> list[dict]:
    return load_dir(DATA_DIR)


def _ids(entries: list[dict]) -> set[str]:
    return {e.get("id") for e in entries if isinstance(e.get("id"), str)}


def formula_ids() -> set[str]:
    return _ids(formula_entries())


def param_ids() -> set[str]:
    return _ids(param_entries())


def known_ids() -> set[str]:
    """公式层 + 参数层的合并 ID 集合(引用完整性用这个)。"""
    return formula_ids() | param_ids()


def duplicates(entries: list[dict]) -> list[str]:
    """层内重复 ID。返回排好序的重复 ID 列表。"""
    seen: dict[str, int] = {}
    for e in entries:
        i = e.get("id")
        if isinstance(i, str):
            seen[i] = seen.get(i, 0) + 1
    return sorted(i for i, n in seen.items() if n > 1)


def id_layer(id_str: str) -> str:
    """判断一个 ID 属于哪一层。未知前缀返回 'UNKNOWN'。"""
    if not isinstance(id_str, str):
        return "UNKNOWN"
    if id_str.startswith(FORMULA_PREFIX):
        return "FORMULA"
    if id_str.startswith(PARAM_PREFIX):
        return "PARAM"
    if id_str.startswith(DATA_PREFIX):
        return "DATA"
    return "UNKNOWN"


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    fs = formula_entries()
    ps = param_entries()
    ds = data_entries()
    print(f"公式条目 {len(fs)} 条,重复 ID {duplicates(fs)}")
    print(f"参数条目 {len(ps)} 条,重复 ID {duplicates(ps)}")
    print(f"数据条目 {len(ds)} 条,重复 ID {duplicates(ds)}")
    print(f"合并 ID 集合(公式+参数) {len(known_ids())} 个")
