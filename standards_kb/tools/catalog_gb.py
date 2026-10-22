#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / catalog_gb.py —— 抓取 GB/T 国家标准全文公开系统的目录层

定位
----
目录层 ≠ 条款正文。

本工具只回答一件事：**「有哪些 GB/T 标准跟我有关，它们叫什么、什么版本、
什么状态、在哪一页、能不能拿到正文」**。

它产出的是**可复用的标准目录资产**（标准号 / 标题 / 状态 / 日期 / hcno /
ICS / 类别），供后续反复查询，而不是一次性抓完就扔。

实测事实（本机 2026-10-22 / 2026-10-23 验证）
------------------------------------------------
- 旧路径 `/bzgk/gb/std_list` 已失效；新路径 `/bzgk/std/std_list` **服务端渲染**，
  静态 GET 直接含结果行，不需要浏览器执行 JS。
- 结果行在 `<table class="table result_list">` 的第二个 `<tbody>` 里。
- 每行关键字段：
    标准号   <td ...><a onclick="showInfo('HCNO');">GB/T 30453-2013</a></td>
    名称     <td class="mytxt" ...><a onclick="showInfo('HCNO');">标题</a></td>
    类别     <td>推标 / 强标</td>
    状态     <td><span class="text-success">现行</span></td>  (或 text-danger 废止)
    发布日期 <td>2013-12-31 00:00:00.0</td>
    实施日期 <td>2014-10-01 00:00:00.0</td>
- `hcno` 是正文页的唯一钥匙：**先 `newGbInfo?hcno=` 建会话，再 `showGb`**，
  顺序反了会被重定向回详情页（见 tools/fetch_gb.py）。
- 检索总条数在页面里是 `var count = N;`。

纪律
----
- 抓不到就记抓不到。每个查询单独记 status，绝不假装成功。
- 原始 HTML 落盘 + SHA256 登记，未来不用重下、也能复核解析是否正确。
- 本工具**不解析正文**，正文由 fetch_gb.py 负责。

用法
----
  python catalog_gb.py --query "GB/T 30453" --query "GB/T 1226"
  python catalog_gb.py --from-file tools/gb_queries.txt
  python catalog_gb.py --query "GB/T 1226" --page 2
  python catalog_gb.py --show            # 只看已落盘的目录
"""
from __future__ import annotations

import argparse
import hashlib
import html as htmlmod
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CAT_DIR = ROOT / "kb" / "catalog"
RAW_DIR = ROOT / "runs" / "probe" / "gb_stdlist"
OUT = CAT_DIR / "gb_openstd.json"

BASE = "https://openstd.samr.gov.cn/bzgk/std/std_list"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://openstd.samr.gov.cn/bzgk/std/",
}


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def http_get(url: str, timeout: int = 60) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def fetch_list_page(query: str, page: int = 1, page_size: int = 50,
                    timeout: int = 60, retries: int = 3) -> dict:
    """抓一页检索结果。返回 status / raw / url。

    站点偶发读超时（实测「耐压试验」查询命中过），故带退避重试。
    """
    params = {"p.p1": "0", "p.p2": query, "pageSize": str(page_size)}
    if page > 1:
        params["page"] = str(page)
    url = BASE + "?" + urllib.parse.urlencode(params)

    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            code, raw, ctype = http_get(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            # 4xx 不重试（重试也没用），5xx 重试
            if e.code < 500:
                return {"status": f"HTTP_{e.code}", "raw": b"", "url": url,
                        "error": str(e.reason)}
            last_err = f"HTTP_{e.code} {e.reason}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        else:
            text = raw.decode("utf-8", errors="replace")
            return {"status": "OK", "raw": raw, "text": text, "url": url,
                    "content_type": ctype, "http_code": code}
        if attempt < retries:
            time.sleep(1.5 * attempt)
    return {"status": "FETCH_ERROR", "raw": b"", "url": url, "error": last_err}


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
HCNO_RE = re.compile(r"showInfo\(\s*'([0-9A-Fa-f]{8,})'\s*\)")
STDNO_RE = re.compile(r"^\s*(GB(?:/T|/Z|/ZT)?\s*[\d.]+-\d{4})\s*$")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# 注意：页面里的 `var count = N;` 不是检索结果总数（实测 GB/T 1226 时 count=1 但实际 5 条）。
# 真正的总数在分页条 "共</a>&nbsp;5&nbsp;<a style=...>条标准"，
# 其中「共」到「条标准」之间隔着 &nbsp;/<a>/style 串，可能超过 40 个字符，间隔要放宽。
TOTAL_RE = re.compile(r"共.{0,160}?(\d{1,6}).{0,160}?条标准", re.S)
COUNT_RE = re.compile(r"var\s+count\s*=\s*(\d+)\s*;")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_tags(s: str) -> str:
    return WS_RE.sub(" ", htmlmod.unescape(TAG_RE.sub("", s))).strip()


def parse_rows(text: str) -> list[dict]:
    """从列表页 HTML 抽出结果行。"""
    rows: list[dict] = []

    # 只在结果表范围内找，避免抓到筛选面板里的杂 <tr>
    m = re.search(r'<table[^>]*class="[^"]*result_list[^"]*"(.*?)</table>', text, re.S)
    scope = m.group(1) if m else text

    for tr in ROW_RE.findall(scope):
        cells = CELL_RE.findall(tr)
        if len(cells) < 9:
            continue  # 表头行 / 缺列行

        hcnos = HCNO_RE.findall(tr)
        if not hcnos:
            continue
        hcno = hcnos[0]

        # 第 2 列 = 标准号，第 5 列 = 名称
        std_txt = strip_tags(cells[1])
        title_txt = strip_tags(cells[4])
        if not STDNO_RE.match(std_txt):
            continue

        rows.append({
            "hcno": hcno,
            "standard_no": std_txt,
            "title_zh": title_txt,
            "language": strip_tags(cells[2]),
            "adopted": strip_tags(cells[3]),
            "category": strip_tags(cells[5]),
            "status": strip_tags(cells[6]),
            "publish_date": (DATE_RE.search(strip_tags(cells[7])) or [None, None])[1]
            if DATE_RE.search(strip_tags(cells[7])) else None,
            "implement_date": (DATE_RE.search(strip_tags(cells[8])) or [None, None])[1]
            if DATE_RE.search(strip_tags(cells[8])) else None,
        })
    return rows


def parse_total(text: str) -> int | None:
    """检索结果总数。取分页条里的「共 N 条标准」。"""
    m = TOTAL_RE.search(text)
    if m:
        return int(m.group(1))
    m2 = COUNT_RE.search(text)
    return int(m2.group(1)) if m2 else None


def parse_count_var(text: str) -> int | None:
    """页面 `var count` —— 与结果总数无关，仅留作诊断。"""
    m = COUNT_RE.search(text)
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# 目录资产
# --------------------------------------------------------------------------
def load_catalog() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {
        "schema": "standards_kb.catalog.gb/1.0",
        "source": {
            "id": "GB-PUB",
            "title": "国家标准全文公开系统",
            "url": BASE,
            "body_status": "OFFICIAL_LIST",
            "note": "目录层只证明标准号/名称/状态/日期，不证明任何条款内容。",
        },
        "generated_at": None,
        "queries": [],
        "standards": {},
    }


def save_catalog(cat: dict) -> None:
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    cat["generated_at"] = datetime.now(CST).isoformat(timespec="seconds")
    cat["stats"] = {
        "standard_count": len(cat["standards"]),
        "query_count": len(cat["queries"]),
        "by_status": _tally(cat["standards"].values(), "status"),
        "by_category": _tally(cat["standards"].values(), "category"),
    }
    OUT.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")


def _tally(rows, key: str) -> dict:
    out: dict[str, int] = {}
    for r in rows:
        v = (r.get(key) or "").strip() or "(空)"
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def record_query(cat: dict, query: str, page: int, res: dict, rows: list[dict],
                 total: int | None) -> None:
    entry = {
        "query": query,
        "page": page,
        "url": res.get("url"),
        "status": res.get("status"),
        "rows_found": len(rows),
        "total_reported": total,
        "fetched_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    if res.get("text"):
        cv = parse_count_var(res["text"])
        if cv is not None:
            entry["count_var_diagnostic"] = cv
    if res.get("error"):
        entry["error"] = res["error"]

    if res.get("status") == "OK" and res.get("raw"):
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.-]+", "_", query)
        raw_path = RAW_DIR / f"{safe}.p{page}.html"
        raw_path.write_bytes(res["raw"])
        entry["raw_file"] = str(raw_path.relative_to(ROOT))
        entry["raw_sha256"] = sha256_bytes(res["raw"])
        entry["raw_bytes"] = len(res["raw"])

    # 去掉同一 query+page 的旧记录
    cat["queries"] = [q for q in cat["queries"]
                      if not (q.get("query") == query and q.get("page") == page)]
    cat["queries"].append(entry)

    for r in rows:
        h = r["hcno"]
        prev = cat["standards"].get(h)
        if prev:
            prev.setdefault("found_by", [])
            if query not in prev["found_by"]:
                prev["found_by"].append(query)
        else:
            r["found_by"] = [query]
            cat["standards"][h] = r


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", action="append", default=[],
                    help="标准号或关键字，可重复")
    ap.add_argument("--from-file", help="每行一个查询的文件")
    ap.add_argument("--page", type=int, default=1, help="起始页码（默认 1）")
    ap.add_argument("--pages", type=int, default=1,
                    help="每查询抓几页；0 = 自动按站点总数抓完")
    ap.add_argument("--page-size", type=int, default=50, help="每页条数（默认 50）")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--show", action="store_true", help="只打印已落盘目录")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.show:
        if not OUT.exists():
            print("还没有目录文件。先跑一次 --query。")
            return 0
        cat = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"生成时间 {cat.get('generated_at')}  共 {len(cat['standards'])} 个标准")
        for h, s in sorted(cat["standards"].items(),
                           key=lambda kv: kv[1].get("standard_no", "")):
            print(f"  {s.get('standard_no',''):<22} {s.get('status',''):<6} "
                  f"{s.get('category',''):<4} {s.get('title_zh','')[:40]}")
        return 0

    queries = list(args.query)
    if args.from_file:
        p = Path(args.from_file)
        if not p.is_absolute():
            p = ROOT / p
        queries += [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")]

    if not queries:
        ap.error("需要 --query 或 --from-file")

    diag = prepare_env(verbose=True)
    cat = load_catalog()
    cat.setdefault("net_env", diag)

    for q in queries:
        pg = args.page
        max_pages = args.pages if args.pages > 0 else 999
        pages_done = 0
        while pages_done < max_pages:
            pages_done += 1
            print(f"\n[GB] 查询 {q!r} 第 {pg} 页")
            res = fetch_list_page(q, page=pg, page_size=args.page_size)
            if res["status"] != "OK":
                print(f"     失败: {res['status']} {res.get('error','')}")
                record_query(cat, q, pg, res, [], None)
                break
            rows = parse_rows(res["text"])
            total = parse_total(res["text"])
            print(f"     OK  {len(rows)} 行  (站点报告总数 {total})")
            record_query(cat, q, pg, res, rows, total)

            if args.pages > 0:
                break
            # 自动翻页：按「本次查询已收录数」判停，而不是全局总数
            # （全局数会被其他查询的历史结果污染，导致第一页就停）
            if total is None:
                break
            if len(rows) == 0:
                break
            got_this_query = sum(1 for s in cat["standards"].values()
                                 if q in (s.get("found_by") or []))
            if got_this_query >= total:
                break
            pg += 1

    save_catalog(cat)
    print(f"\n目录已更新 -> {Path(args.out).relative_to(ROOT)}")
    print(f"  标准 {len(cat['standards'])} 个，查询 {len(cat['queries'])} 次")
    print("  提示：目录不等于正文。正文取回用 tools/fetch_gb.py（需 hcno）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
