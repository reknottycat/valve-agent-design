#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / provenance.py —— 正文来源台账(可复用层)

为什么有这个工具
----------------
「抓到过一次」不等于「以后还能用」。本工具给每一份已落地的标准正文建立
**可复现的台账**: 文件哈希、抓取 URL、获取时间、页数/字符数、抽取产出量。
以后任何人(或别的 Agent)想知道「手上有哪些正文、还差哪些」,
跑一条命令就有答案,不用重新上网找一遍。

产出
----
  runs/<source_id>/provenance.json   每份正文一份台账(逐文件)
  runs/fetch_manifest.json           全局台账(按标准聚合)

用法
----
  python provenance.py              # 建/刷新台账
  python provenance.py --verify     # 重算哈希,报告漂移(文件被改/丢失)
  python provenance.py --report     # 只打印人类可读摘要
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_entries as K  # noqa: E402
from standard_ids import std_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
KB = ROOT / "kb"
REG_JSON = ROOT / "registry" / "registry.json"
CST = timezone(timedelta(hours=8))

# runs/probe 是探测过程的临时产物,不是资产,不进台账
SCRATCH_DIRS = {"probe"}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, CST).isoformat(timespec="seconds")


def file_kind(p: Path) -> str:
    suf = p.suffix.lower()
    return {".pdf": "pdf", ".txt": "text", ".json": "json",
            ".djvu": "text"}.get(suf, suf.lstrip(".") or "bin")


def pdf_stats(p: Path) -> dict:
    try:
        import pymupdf  # noqa: F401
        doc = pymupdf.open(p)
        n = doc.page_count
        doc.close()
        return {"pages": n}
    except Exception as e:  # 取不到就明说,不要伪造
        return {"pages": None, "pages_error": f"{type(e).__name__}: {e}"}


def text_stats(p: Path) -> dict:
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
        return {"chars": len(t), "lines": t.count("\n") + 1}
    except Exception as e:
        return {"chars": None, "chars_error": f"{type(e).__name__}: {e}"}


def load_registry() -> dict:
    if REG_JSON.exists():
        return json.loads(REG_JSON.read_text(encoding="utf-8"))
    return {}


def registry_sources(reg: dict) -> dict[str, dict]:
    """把 registry.json 里 families.*.sources 摊平成 {id: source}。"""
    out: dict[str, dict] = {}
    for fam, fdata in (reg.get("families") or {}).items():
        for s in (fdata.get("sources") or []):
            sid = s.get("id")
            if sid:
                out[sid] = {**s, "family": fam}
    return out


def curated_entries_by_standard() -> dict[str, list[str]]:
    """统计 kb/formulas/ 里每份标准固化了多少条正式条目。"""
    out: dict[str, list[str]] = {}
    fdir = KB / "formulas"
    if not fdir.exists():
        return out
    for f in sorted(fdir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries = data if isinstance(data, list) else [data]
        for e in entries:
            if not isinstance(e, dict):
                continue
            sid = ((e.get("source") or {}).get("standard_id")) or ""
            if sid:
                out.setdefault(sid, []).append(e.get("id", "?"))
    return out


def curated_data_entries_by_standard() -> dict[str, list[str]]:
    """Count curated DATA-table entries in kb/data/, grouped by standard id.

    Formula entries and data-table entries are two different assets; the ledger
    must report both, otherwise a standard that only produced data tables
    (e.g. GB/T 15530.1-2008) looks empty in the manifest.
    """
    out: dict[str, list[str]] = {}
    ddir = KB / "data"
    if not ddir.exists():
        return out
    for f in sorted(ddir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            entries = data.get("entries") or []
        elif isinstance(data, list):
            entries = data
        else:
            entries = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            sid = e.get("standard_id") or ((e.get("source") or {}).get("standard_id")) or ""
            if sid:
                out.setdefault(sid, []).append(e.get("id", "?"))
    return out


def curated_param_entries_by_standard() -> dict[str, list[str]]:
    """Count curated PARAMETER entries in kb/parameters/, grouped by standard id.

    Parameters are the third knowledge-object layer (scalars: constants,
    coefficients, limits, thresholds, material properties, unit factors).
    They are a different asset from formula entries and data-table entries,
    so the ledger must report them separately -- otherwise a standard that
    only produced scalar parameters looks empty in the manifest.
    """
    out: dict[str, list[str]] = {}
    pdir = KB / "parameters"
    if not pdir.exists():
        return out
    for f in sorted(pdir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = data.get("entries") or []
        else:
            entries = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            sid = ((e.get("source") or {}).get("standard_id")) or ""
            if sid:
                out.setdefault(sid, []).append(e.get("id", "?"))
    return out


def _entry_standard(e: dict) -> str:
    """条目所属标准全名。公式/参数在 source 里，数据表在顶层。"""
    src = e.get("source") or {}
    return str(src.get("standard_id") or e.get("standard_id") or "")


def curated_ontology_entries_by_standard() -> dict[str, list[str]]:
    """统计**已纳入本体映射**的条目，按标准分组。

    本体层是映射层，不产生新事实。台账要能看出
    「某标准有 12 条公式，但只有 8 条进了本体」这种缺口，
    所以这里统计的是被本体映射覆盖的条目，而不是本体自己造的东西。
    """
    out: dict[str, list[str]] = {}
    onto_dir = KB / "ontology" / "mappings"
    if not onto_dir.exists():
        return out
    mapped: set[str] = set()
    for fname in ("formulas.json", "parameters.json", "data.json"):
        p = onto_dir / fname
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for eid in (doc.get("mappings") or {}):
            mapped.add(eid)
    if not mapped:
        return out
    for layer in ("formula", "parameter", "data"):
        for e in (K.formula_entries(ROOT) if layer == "formula"
                  else K.param_entries(ROOT) if layer == "parameter"
                  else K.data_entries(ROOT)):
            eid = e.get("id")
            if not eid or eid not in mapped:
                continue
            sid = _entry_standard(e)
            if sid:
                out.setdefault(sid, []).append(eid)
    return out


def ontology_asset_stats() -> dict:
    """本体层资产统计（词表/等价集/映射/投影/碰撞）。

    失败时返回 error 字段而不是抛异常 —— 台账不该因为本体层缺失而整体挂掉。
    """
    try:
        import onto_model as OM
        onto = OM.load(ROOT)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    mapped = 0
    for lay in ("formula", "parameter", "data"):
        mapped += len(((onto.maps.get(lay) or {}).get("mappings") or {}))
    return {
        "quantities": len(onto.quantities),
        "contexts": len(onto.contexts),
        "equivalence_sets": len(onto.sets),
        "occurrences": len(onto.occurrences),
        "criteria": len(onto.criteria),
        "variable_bindings": len(onto.bindings),
        "table_columns": len(onto.columns),
        "mapped_entries": mapped,
        "open_questions": len(onto.open_questions),
        "symbol_collisions": len(OM.symbol_collisions(onto)),
    }


def candidate_count(source_id: str) -> tuple[int, list[str]]:
    """统计该标准目录下已落地的候选公式文件与条目数。"""
    d = RUNS / source_id
    n = 0
    files = []
    if d.exists():
        for p in sorted(d.glob("*__candidates.json")) + sorted(d.glob("*__pdfcandidates.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else (
                data.get("candidates") or data.get("formulas") or [])
            n += len(items)
            files.append(f"{p.name} ({len(items)} 条)")
    return n, files


def build(source_id: str, reg_src: dict | None) -> dict:
    d = RUNS / source_id
    files = []
    for p in sorted(d.rglob("*")):
        if not p.is_file() or p.name == "provenance.json":
            continue
        rec = {
            "filename": p.relative_to(d).as_posix(),
            "kind": file_kind(p),
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
            "file_mtime": iso(p.stat().st_mtime),
        }
        if rec["kind"] == "pdf":
            rec.update(pdf_stats(p))
        elif rec["kind"] == "text":
            rec.update(text_stats(p))
        files.append(rec)

    cand_n, cand_files = candidate_count(source_id)

    std_key = None
    if reg_src:
        std_key = std_of(reg_src.get("standard_id") or reg_src.get("id") or "")

    curated = []
    curated_data = []
    curated_param = []
    curated_ontology = []
    if std_key:
        for k, ids in curated_entries_by_standard().items():
            if std_of(k) == std_key:
                curated += ids
        for k, ids in curated_data_entries_by_standard().items():
            if std_of(k) == std_key:
                curated_data += ids
        for k, ids in curated_param_entries_by_standard().items():
            if std_of(k) == std_key:
                curated_param += ids
        for k, ids in curated_ontology_entries_by_standard().items():
            if std_of(k) == std_key:
                curated_ontology += ids

    rec = {
        "source_id": source_id,
        "standard_id": std_key,
        "registry": {
            "family": (reg_src or {}).get("family"),
            "kind": (reg_src or {}).get("kind"),
            "body_status": (reg_src or {}).get("body_status"),
            "title": (reg_src or {}).get("title"),
            "url": (reg_src or {}).get("url"),
        },
        "has_body": bool(files),
        "files": files,
        "candidates_extracted": cand_n,
        "candidate_files": cand_files,
        "curated_entries": sorted(curated),
        "curated_data_entries": sorted(curated_data),
        "curated_param_entries": sorted(curated_param),
        "curated_ontology_entries": sorted(curated_ontology),
        "rebuilt_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    return rec


def rebuild_manifest(reg: dict | None = None) -> dict:
    """扫描 runs/ 重建全局正文台账。**纯函数，不写盘**。

    单独拆出来是为了让 fetch.py 复用同��份 schema：
    以前 fetch.py 自己往 fetch_manifest.json 里塞 `records` 列表，
    而本工具写的是 `standards` 列表 —— 两个工具同文件不同 schema，
    结果 fetch.py 读到别人的文件直接 KeyError('records')。
    现在**只有本模块能写 fetch_manifest.json**。
    """
    reg = reg if reg is not None else load_registry()
    rsrc = registry_sources(reg)
    curated_by_std = curated_entries_by_standard()
    curated_data_by_std = curated_data_entries_by_standard()
    curated_param_by_std = curated_param_entries_by_standard()
    curated_ontology_by_std = curated_ontology_entries_by_standard()

    std_dirs = []
    if RUNS.exists():
        std_dirs = [p for p in sorted(RUNS.iterdir())
                    if p.is_dir() and p.name not in SCRATCH_DIRS]

    manifest = {
        "schema": "standards_kb.fetch_manifest/1.0",
        "updated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "note": ("登记本地已落地的标准正文。只证明「这份正文在这儿、哈希是多少」，"
                 "不证明条款级结论正确 —— 结论见 kb/formulas/ 每条的 evidence 字段。"),
        "standards": [],
    }
    for sd in std_dirs:
        manifest["standards"].append(build(sd.name, rsrc.get(sd.name)))

    manifest["summary"] = {
        "data_entries": sum(len(v) for v in curated_data_by_std.values()),
        "parameter_entries": sum(len(v) for v in curated_param_by_std.values()),
        "standards_with_body": sum(1 for s in manifest["standards"] if s["has_body"]),
        "standards_total": len(manifest["standards"]),
        "files": sum(len(s["files"]) for s in manifest["standards"]),
        "bytes": sum(f["bytes"] for s in manifest["standards"] for f in s["files"]),
        "candidates": sum(s["candidates_extracted"] for s in manifest["standards"]),
        "curated_entries": sum(len(v) for v in curated_by_std.values()),
        "ontology_entries": sum(len(v) for v in curated_ontology_by_std.values()),
        "ontology": ontology_asset_stats(),
    }
    return manifest


def write_manifest(manifest: dict) -> Path:
    """把台账写盘（fetch_manifest.json 的**唯一**写入口）。"""
    mf = RUNS / "fetch_manifest.json"
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return mf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true", help="重算哈希,报告漂移")
    ap.add_argument("--report", action="store_true", help="只打印摘要,不写文件")
    args = ap.parse_args()

    reg = load_registry()
    rsrc = registry_sources(reg)
    curated_by_std = curated_entries_by_standard()

    if not RUNS.exists():
        print("runs/ 不存在")
        return 1

    std_dirs = [p for p in sorted(RUNS.iterdir())
                if p.is_dir() and p.name not in SCRATCH_DIRS]

    manifest = rebuild_manifest(reg)

    drift = []
    for sd in std_dirs:
        rec = next(s for s in manifest["standards"] if s["source_id"] == sd.name)
        pf = sd / "provenance.json"
        if args.verify:
            if not pf.exists():
                drift.append((sd.name, "MISSING_PROVENANCE", "无台账文件"))
            else:
                old = json.loads(pf.read_text(encoding="utf-8"))
                oldmap = {f["filename"]: f["sha256"] for f in old.get("files", [])}
                newmap = {f["filename"]: f["sha256"] for f in rec["files"]}
                for name, dig in newmap.items():
                    if name not in oldmap:
                        drift.append((sd.name, name, "新增文件,台账未更新"))
                    elif oldmap[name] != dig:
                        drift.append((sd.name, name, "哈希变化: 内容被修改"))
                for name in oldmap:
                    if name not in newmap:
                        drift.append((sd.name, name, "文件已丢失"))
        if not args.report:
            pf.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.report:
        write_manifest(manifest)

    # --- 打印 ---
    print(f"{'标准':<18}{'正文':<8}{'文件':<6}{'大小':>12}  候选  公式  数据  参数  状态")
    print("-" * 86)
    for s in manifest["standards"]:
        body = "有" if s["has_body"] else "缺"
        size = sum(f["bytes"] for f in s["files"])
        size_s = f"{size/1048576:.1f} MB" if size >= 1048576 else f"{size/1024:.0f} KB"
        st = s["registry"].get("body_status") or "-"
        print(f"{s['source_id']:<18}{body:<8}{len(s['files']):<6}{size_s:>12}  "
              f"{s['candidates_extracted']:>4}  {len(s['curated_entries']):>4}  "
              f"{len(s.get('curated_data_entries', [])):>4}  "
              f"{len(s.get('curated_param_entries', [])):>4}  {st}")

    sm = manifest["summary"]
    print("-" * 86)
    print(f"正文标准 {sm['standards_with_body']}/{sm['standards_total']} | "
          f"文件 {sm['files']} 个 / {sm['bytes']/1048576:.1f} MB | "
          f"待复核候选 {sm['candidates']} 条 | 公式条目 {sm['curated_entries']} 条 | "
          f"数据表 {sm['data_entries']} 条 | "
          f"参数表 {sm['parameter_entries']} 条 | "
          f"本体映射 {sm.get('ontology_entries', 0)} 条")
    onto = sm.get("ontology") or {}
    if onto.get("error"):
        print(f"本体层统计失败: {onto['error']}")
    else:
        print(f"本体层: 物理量 {onto.get('quantities', 0)} | "
              f"上下文 {onto.get('contexts', 0)} | "
              f"等价集 {onto.get('equivalence_sets', 0)} | "
              f"出现 {onto.get('occurrences', 0)} | "
              f"判据 {onto.get('criteria', 0)} | "
              f"变量绑定 {onto.get('variable_bindings', 0)} | "
              f"表列 {onto.get('table_columns', 0)} | "
              f"碰撞组 {onto.get('symbol_collisions', 0)} | "
              f"未决问题 {onto.get('open_questions', 0)}")

    if args.verify:
        if not drift:
            print("\n校验通过:无漂移。")
        else:
            print(f"\n发现 {len(drift)} 处漂移:")
            for sid, name, msg in drift:
                print(f"  [{sid}] {name}: {msg}")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
