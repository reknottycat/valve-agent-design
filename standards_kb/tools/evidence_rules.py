#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / evidence_rules.py —— 证据等级与出处纪律的共享规则

为什么单独抽一个模块:公式校验器(validate.py)和数据校验器(validate_data.py)
都要执行同一批等级规则。两边各写一份必然漂移,而"两个校验器口径不一致"
本身就是一个会被当成"数据没问题"的隐性缺陷。

规则来源是项目根 README 的 E0-E3 定义,不要在本文件里另立一套:
    E0 工具能运行
    E1 数值与公式自洽
    E2 在可比物理数据范围内得到验证
    E3 本产品/同等样机的相关实测支持

关键推论(本文件的核心):
    出处不可核(body_status 属于 PAYWALL / DERIVED_NO_TEXT / OFFICIAL_LIST)
    => 最多只能做到 E1「数值与公式自洽」
    => 绝不可能达到 E2「可比物理数据验证」,因为正文没拿到就没法比。
所以 body_status 给 grade 设上限,这是可机器检查的,不需要人肉判断。

同理:
    grade = E2/E3  <=>  必须真有物理数据/实测支撑
    => project_usage 不能只是占位符("N/A"/"不适用" 之类)
    => 声明 FULL_TEXT_MIRROR(本机已实测拿到正文) <=>  必须给得出可定位的文件
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GRADE_ORDER = {"E0": 0, "E1": 1, "E2": 2, "E3": 3}

# 这些 body_status 的共同含义是"本机拿不到可核的正文":
#   PAYWALL       正文付费,本机不可得
#   DERIVED_NO_TEXT  非标准条款/自行推导,没有标准正文
#   OFFICIAL_LIST 只有官方目录/范围页,证明名称与状态,不证明条款
# 这三种情况下,证据等级封顶 E1。
UNVERIFIABLE_BODY = ("PAYWALL", "DERIVED_NO_TEXT", "OFFICIAL_LIST")
MAX_GRADE_UNVERIFIABLE = "E1"

# project_usage 里等于"本条与本项目无关"的占位写法
NO_PROJECT_USAGE_MARKERS = {"不适用", "不涉及", "n/a", "na", "none", "-"}

# 定位串里像本地路径的片段。只用 ASCII 字符集:中文说明文字(如"图像核读 ")
# 不应该被吸进路径里,否则拼出来的路径永远不存在。
_PATH_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_\-./\\]*\.(?:txt|pdf|png|jpe?g|htm|html|json|csv|xml|yaml|yml)"
)


def grade_at_most(grade: str, cap: str) -> bool:
    """grade 是否不超过 cap。等级名不认识时按最宽松处理,由调用方另报非法值。"""
    g, c = GRADE_ORDER.get(grade), GRADE_ORDER.get(cap)
    if g is None or c is None:
        return True
    return g <= c


def locator_paths(locator: str) -> list[str]:
    """从定位串里抽出本地路径候选(去掉 #片段 与行号后缀)。"""
    if not locator:
        return []
    out: list[str] = []
    for m in _PATH_RE.finditer(locator):
        p = m.group(0).split("#", 1)[0]
        p = p.replace("\\", "/").strip("./")
        if p and p not in out:
            out.append(p)
    return out


def locator_files_exist(locator: str) -> bool:
    """定位串里至少有一个本地文件真实存在。"""
    for p in locator_paths(locator):
        if (ROOT / p).exists():
            return True
    return False


def check_evidence(entry: dict) -> list[str]:
    """检查证据等级与出处是否自洽。返回错误信息列表(空 = 通过)。

    对公式条目和数据表条目通用:两边都有 evidence / source / body_status。
    """
    errs: list[str] = []
    ev = entry.get("evidence") or {}
    src = entry.get("source") or {}

    grade = ev.get("grade")
    status = ev.get("status")
    body = entry.get("body_status") or src.get("body_status")
    eid = entry.get("id", "<no-id>")

    if grade is None:
        errs.append("evidence.grade 缺失")
        return errs

    # --- 1) 等级双写必须同步 ---
    # source.evidence_grade 是 evidence.grade 的冗余副本。两处各写各的,
    # 就会出现"证据块说 E1、出处块说 E2"的分裂,读的人各看一处就得到不同答案。
    sg = src.get("evidence_grade")
    if sg is not None and sg != grade:
        errs.append(f"source.evidence_grade={sg!r} 与 evidence.grade={grade!r} 不一致")

    # --- 2) 出处不可核 => 等级封顶 E1 ---
    if body in UNVERIFIABLE_BODY and not grade_at_most(grade, MAX_GRADE_UNVERIFIABLE):
        errs.append(f"body_status={body} 表示本机拿不到可核正文,"
                    f"等级不得高于 {MAX_GRADE_UNVERIFIABLE},实际为 {grade}")

    # --- 3) E2/E3 必须有真正的项目支撑 ---
    if grade in ("E2", "E3"):
        pu = entry.get("project_usage")
        if not pu:
            errs.append(f"证据等级 {grade} 必须有 project_usage 支撑")
        else:
            live = [p for p in pu
                    if str(p.get("status", "")).strip().lower() not in NO_PROJECT_USAGE_MARKERS
                    and str(p.get("task", "")).strip().lower() not in NO_PROJECT_USAGE_MARKERS]
            if not live:
                errs.append(f"证据等级 {grade} 的 project_usage 全部是占位符"
                            f"(如 N/A/不适用),没有任何真实项目支撑")

    # --- 4) 声称有正文就必须定位得到 ---
    if body == "FULL_TEXT_MIRROR":
        loc = src.get("locator")
        if not loc:
            errs.append("body_status=FULL_TEXT_MIRROR(本机已实测拿到正文) 必须给 source.locator")
        elif not locator_files_exist(loc):
            errs.append(f"source.locator 引用的本地文件都不存在,无法回溯: {loc!r}")

    return errs
