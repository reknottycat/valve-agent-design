#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / standard_ids.py —— 标准号归一（共享口径）

为什么要有这个模块
------------------
本库里有**两套标准号命名空间**，它们不是一回事：

  * 条目侧 source.standard_id / 数据条目 standard_id
    = 标准**全名**，如 "ASME BPVC Section I-2010"、"GB/T 15530.1-2008"
  * registry standard_id / runs/ 正文目录名
    = **短 id**，如 "ASME-BPVC-I"、"GB-GB_T_15530.1-2008"

两边的对应关系**不能靠字符串前缀猜**，只能靠一张显式别名表。
build_docs.py（覆盖表）和 provenance.py（正文台账）必须用**同一张表**，
否则同一批条目在两份文档里会归属到不同标准，台账就失去对账价值。

两个必须记住的坑
----------------
1. **西里尔 -> 拉丁是「音译」，不是「同形字映射」。**
   按 GOST 7.79-2000 / ISO 9，西里尔 Es (U+0421) 长得像拉丁 C，但音译是 **S**，
   所以俄标缩写拼作 G-O-S-T。早期用同形字表把 Es 映成 C，规范化出 "GOCT"，
   俄标全被判成「其他/通用」。本模块的 translit() 是音译表。

2. **别名匹配不能停在罗马数字边界上。**
   朴素子串测试 "ASME BPVC Section I" 会同时命中
   "Section II"、"Section VIII"、"Section IX"，
   于是把一条 **Section II 材料许用应力**条目静默归到 BPVC Section I 名下。
   下面的模式都带显式否定前瞻 (?![IVX])。

本文件**不直接出现西里尔字母**，一律用 \\uXXXX 转义 ——
肉眼分不清的字符就别让它进源码。

用法
----
    from standard_ids import std_of, family_of
    std_of("ASME BPVC Section I-2010")    -> "ASME-BPVC-I"
    std_of("ASME BPVC Section II Part D") -> "ASME-BPVC-II"
    family_of("\u0413\u041e\u0421\u0422 1536-76")        -> "GOST"
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 西里尔 -> 拉丁：音译表（GOST 7.79-2000 / ISO 9）
# ---------------------------------------------------------------------------
CYR_LAT = {
    "\u0410": "A", "\u0411": "B", "\u0412": "V", "\u0413": "G",
    "\u0414": "D", "\u0415": "E", "\u0401": "Yo", "\u0416": "Zh",
    "\u0417": "Z", "\u0418": "I", "\u0419": "J", "\u041a": "K",
    "\u041b": "L", "\u041c": "M", "\u041d": "N", "\u041e": "O",
    "\u041f": "P", "\u0420": "R", "\u0421": "S", "\u0422": "T",
    "\u0423": "U", "\u0424": "F", "\u0425": "X", "\u0426": "C",
    "\u0427": "Ch", "\u0428": "Sh", "\u0429": "Shch", "\u042a": "",
    "\u042b": "Y", "\u042c": "", "\u042d": "E", "\u042e": "Yu",
    "\u042f": "Ya",
    "\u0430": "a", "\u0431": "b", "\u0432": "v", "\u0433": "g",
    "\u0434": "d", "\u0435": "e", "\u0451": "yo", "\u0436": "zh",
    "\u0437": "z", "\u0438": "i", "\u0439": "j", "\u043a": "k",
    "\u043b": "l", "\u043c": "m", "\u043d": "n", "\u043e": "o",
    "\u043f": "p", "\u0440": "r", "\u0441": "s", "\u0442": "t",
    "\u0443": "u", "\u0444": "f", "\u0445": "x", "\u0446": "c",
    "\u0447": "ch", "\u0448": "sh", "\u0449": "shch", "\u044a": "",
    "\u044b": "y", "\u044c": "", "\u044d": "e", "\u044e": "yu",
    "\u044f": "ya",
}

# ---------------------------------------------------------------------------
# 西里尔同形字 -> 拉丁：视觉折叠（只用于**归族**，不做 id 归一）
# ---------------------------------------------------------------------------
HOMOGLYPH = {
    "\u0410": "A", "\u0412": "B", "\u0413": "G", "\u0415": "E", "\u041a": "K",
    "\u041c": "M", "\u041d": "H", "\u041e": "O", "\u0420": "P",
    "\u0421": "C", "\u0422": "T", "\u0425": "X", "\u0405": "S",
    "\u0406": "I", "\u0408": "J", "\u04ae": "Y", "\u0490": "G",
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
    "\u0433": "g", "\u0435": "e", "\u0441": "c", "\u0442": "t",
    "\u0445": "x", "\u0455": "s", "\u0456": "i", "\u0458": "j",
}

# 家族关键词。GOST 同时接受 "GOCT"（同形字折叠后的产物），双保险。
FAM_KEYS = {
    "GB": ("GB/", "GB/T", "GB "),
    "ASME": ("ASME",),
    "GOST": ("GOST", "GOCT"),
    "ISO": ("ISO", "IEC"),
}

# ---------------------------------------------------------------------------
# 短 id -> 全名匹配模式（正则）
# ---------------------------------------------------------------------------
# 注意否定前瞻：Section I 后面不能紧跟 I/V/X（否则会命中 II/VIII/IX）。
STD_ALIAS = {
    "ASME-BPVC-I": (r"ASME\s+BPVC\s+Section\s+I(?![IVX])",),
    "ASME-BPVC-II": (r"ASME\s+BPVC\s+Section\s+II(?![IVX])",),
    "ASME-BPVC-IV": (r"ASME\s+BPVC\s+Section\s+IV(?![IVX])",),
    "ASME-BPVC-VII": (r"ASME\s+BPVC\s+Section\s+VII(?![IVX])",),
    "ASME-BPVC-VIII": (r"ASME\s+BPVC\s+Section\s+VIII(?![IVX])",),
    "ASME-BPVC-IX": (r"ASME\s+BPVC\s+Section\s+IX(?![IVX])",),
    "ASME-B31.1": (r"ASME\s+B31\.1(?![0-9])",),
    "ASME-B31.4": (r"ASME\s+B31\.4(?![0-9])",),
    "ASME-B31.9": (r"ASME\s+B31\.9(?![0-9])",),
    "ASME-B16.9": (r"ASME\s+B16\.9(?![0-9])",),
    "GOST-1536-76": (r"1536-76",),
}

_COMPILED = {sid: tuple(re.compile(p, re.IGNORECASE) for p in pats)
             for sid, pats in STD_ALIAS.items()}


def translit(text: str) -> str:
    """西里尔 -> 拉丁**音译**（GOST 7.79-2000 / ISO 9）。ASCII 原样保留。"""
    return "".join(CYR_LAT.get(c, c) for c in (text or ""))


def fold(text: str) -> str:
    """西里尔同形字 -> 拉丁（视觉折叠）。只用于归族。"""
    return "".join(HOMOGLYPH.get(c, c) for c in (text or ""))


def std_of(text: str) -> str:
    """标准全名 -> 规范短 id。认不出来就**原样返回**，绝不硬塞。"""
    t = translit(text).upper()
    for sid, pats in _COMPILED.items():
        for p in pats:
            if p.search(t):
                return sid
    return text or "?"


def family_of(text: str) -> str:
    """标准名 -> 家族（GB / ASME / GOST / ISO / OTHER）。"""
    t = fold(text).upper()
    for fam, keys in FAM_KEYS.items():
        for k in keys:
            if k.upper() in t:
                return fam
    return "OTHER"
