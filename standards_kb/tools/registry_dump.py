#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / registry_dump.py —— 把 registry/sources.yaml 转成 registry.json

用 PyYAML 真解析(手搓 YAML 解析器在块标量/嵌套列表上必炸,已踩过)。
装不上 PyYAML 时:
  pip install pyyaml
没有 PyYAML 工具链跑不起来,这不是可选依赖。

转换后做严格校验 —— 不认识的 body_status 直接报错,不静默丢弃。
用法: python registry_dump.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("缺 PyYAML。先装: pip install pyyaml")
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "registry" / "sources.yaml"
DST = ROOT / "registry" / "registry.json"

VALID_STATUS = {
    "FULL_TEXT_MIRROR", "OFFICIAL_LIST", "PAYWALL",
    "RENDERED_JS", "LOCAL_FILE", "DERIVED_NO_TEXT",
}
REQUIRED_SOURCE_FIELDS = {"id", "title", "body_status"}
REQUIRED_FAMILY_FIELDS = {"label", "sources"}


def main() -> int:
    try:
        doc = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        print(f"YAML 解析失败:\n{e}")
        return 1

    if not isinstance(doc, dict):
        print("registry 顶层不是映射")
        return 1

    errs = []
    families = doc.get("families")
    if not isinstance(families, dict) or not families:
        errs.append("缺 families 段或为空")
    else:
        for fam, fdata in families.items():
            if not isinstance(fdata, dict):
                errs.append(f"{fam}: 不是映射")
                continue
            miss = REQUIRED_FAMILY_FIELDS - set(fdata.keys())
            if miss:
                errs.append(f"{fam}: 缺字段 {sorted(miss)}")
                continue
            seen = set()
            for s in fdata["sources"]:
                sid = s.get("id", "?")
                if sid in seen:
                    errs.append(f"{fam}: source id 重复 -> {sid}")
                seen.add(sid)
                m = REQUIRED_SOURCE_FIELDS - set(s.keys())
                if m:
                    errs.append(f"{fam}/{sid}: 缺字段 {sorted(m)}")
                if s.get("body_status") not in VALID_STATUS:
                    errs.append(f"{fam}/{sid}: body_status 非法 -> {s.get('body_status')!r}")
                if s.get("body_status") == "FULL_TEXT_MIRROR" and not (
                    s.get("local") or s.get("url")
                ):
                    errs.append(f"{fam}/{sid}: FULL_TEXT_MIRROR 必须给 url 或 local")

    if errs:
        print("registry 校验失败:")
        for e in errs:
            print("  -", e)
        return 1

    DST.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    n = sum(len(f.get("sources", [])) for f in families.values())
    print(f"registry OK: {len(families)} 族 / {n} 个源 -> {DST.relative_to(ROOT)}")
    for fam, fdata in families.items():
        print(f"  {fam:<6} {fdata.get('label','')}")
        for s in fdata["sources"]:
            flag = "OK " if s.get("verified_this_session") else "   "
            print(f"      {flag}{s['id']:<18} {s['body_status']:<18} {s['title'][:46]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
