#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / build_data.py —— 把「机器抽出的表」+「人写的列定义与语义」合成正式数据条目

分工:
  parse_gost.py / extract_pdf.py  负责**取数**(行、页码、上下文)
  build_data.py                   负责**定名**(列的中文名、压力等级、适用范围、证据等级)

为什么要分开: 取数是机器的活,容易错; 定名是人的活,不能机器代劳。
混在一起就会出现「机器把列名猜错,却看不出来」。

产出 kb/data/<name>.json,格式符合 kb/data.schema.json。

用法:
  python build_data.py kb/data/specs/gost_1536_76.spec.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def num(v):
    """把 '12' / '1,5' / 'М14' 规整: 数字转 float,逗号小数点转点,其余保留字符串。

    raw 里可能已经是 int/float(人工转录常直接写数值),也可能是 None(留空的
    跨表引用行),这些都要能原样通过,不能因为类型不是 str 就炸。
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    v = str(v).strip()
    if not v:
        return None
    t = v.replace(",", ".")
    try:
        return float(t) if "." in t else int(t)
    except ValueError:
        return v


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python build_data.py <spec.json>")
        return 1
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    raw = json.loads((ROOT / spec["raw_tables"]).read_text(encoding="utf-8"))
    raw_by_index = {t["index"]: t for t in raw["tables"]}

    entries = []
    for tspec in spec["tables"]:
        rt = raw_by_index.get(tspec["index"])
        if not rt:
            print(f"  跳过 表{tspec['index']}: raw 里没有")
            continue
        cols = spec["column_sets"][tspec["column_set"]]
        ncol = len(cols)
        # 行定位键取自第几列。默认第 0 列(DN / 首个主键);
        # 压力-温度等级表首列是"型式"、第二列才是 PN,需按表指定。
        key_col = tspec.get("key_column", 0)
        # 跨表引用行的附加说明(如"使用 PN25 的 RF 型法兰尺寸"),键=行定位键
        # 可写在 tspec.row_notes,也可统一写在 spec.row_notes[表号]
        row_notes = tspec.get("row_notes")
        if row_notes is None:
            row_notes = spec.get("row_notes", {}).get(str(tspec["index"]), {})

        rows, keys = [], {}
        for r in rt["data_rows"]:
            if len(r) < ncol:
                print(f"  警告 表{tspec['index']} 行 {r} 列数 {len(r)} < {ncol},跳过")
                continue
            vals = [num(x) for x in r[:ncol]]
            rows.append(vals)
            k = str(r[key_col])
            entry = {c["key"]: vals[i] for i, c in enumerate(cols)}
            if k in row_notes:
                entry.update(row_notes[k])
            keys[k] = entry

        # 以下四项允许按表覆盖: 不同性质的表(压力-温度等级 vs 尺寸表)
        # 种类不同、使用场景不同、抽取方式说明不同。
        table_kind = tspec.get("table_kind", spec.get("table_kind", "DIMENSION_TABLE"))
        design_domain = tspec.get("design_domain", spec.get("design_domain", "GEOM"))
        usage = tspec.get("usage", spec.get("usage"))
        if not usage:
            print(f"  跳过 表{tspec['index']}: spec 与 tspec 均未提供 usage")
            continue
        if tspec.get("extraction_note"):
            extraction_note = tspec["extraction_note"]
        else:
            extraction_note = (
                f"机器抽取: {spec['upstream']}。"
                f"原始表头为两行合并结构(组名 + 子列名),列名由人工按标准语义指认,"
                f"非机器猜读。抽取行数 {len(rt['data_rows'])}。")

        # 定位串: 默认 spec.source_file,若表自带 source_page 则拼成 file/page
        locator_base = spec["source_file"]
        if tspec.get("source_page"):
            locator_base = f"{locator_base.rstrip('/')}/{tspec['source_page']}"

        entries.append({
            "id": tspec["id"],
            "title_zh": tspec["title_zh"],
            "title_orig": f"{spec['standard_title_orig']} — {tspec['clause']}",
            "table_kind": table_kind,
            "design_domain": design_domain,
            "standard_id": spec["standard_id"],
            "clause": tspec["clause"],
            "table_ref": tspec.get("chart_ref", tspec["clause"]),
            "body_status": spec["body_status"],
            "columns": cols,
            "rows": rows,
            "row_keys": keys,
            "source": {
                "locator": f"{locator_base}#table{tspec['index']}",
                "snippet": rt["context_head"][:300],
                "extraction_method": spec["extraction_method"],
                "extraction_note": extraction_note,
            },
            "evidence": {
                **spec["evidence"],
                "verified_on": datetime.now(CST).date().isoformat(),
                "verified_by": "standards_kb/build_data.py + 人工列定义",
            },
            "usage": usage,
            "project_usage": tspec.get("project_usage", []),
            "related": tspec.get("related", []),
        })

    out = {
        "schema": "standards_kb.data_set/1.0",
        "standard_id": spec["standard_id"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "count": len(entries),
        "entries": entries,
    }
    dst = ROOT / "kb" / "data" / f"{spec['standard_id'].replace(' ', '_').replace('/', '_')}.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {dst.relative_to(ROOT)}  {len(entries)} 个数据条目")
    for e in entries:
        print(f"   {e['id']:<24}{len(e['rows']):>3} 行  {e['title_zh'][:46]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
