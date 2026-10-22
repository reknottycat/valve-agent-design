#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / fetch_gb.py —— 取 GB/T 国家标准全文公开系统的**正文**（栅格页图）

定位
----
catalog_gb.py 负责**目录层**（有哪些标准、什么状态、在哪一页）。
本工具负责**正文层**（把某一标准的每一页取回来，组装成可 OCR 的整页 PNG）。

GB 正文的特殊性
--------------
GB/T 正文**没有 HTML 文字层**，正文是图片。所以「取正文」= 取页图，
再交给 OCR（PaddleOCR-VL）转文本。本工具只负责**忠实取回 + 忠实重组**，
不做识别。

三步链路（顺序不可颠倒，实测）
------------------------------
  1. GET /bzgk/std/newGbInfo?hcno=<HCNO>
       —— 建立会话。**必须先做这步**，否则 showGb 会被重定向回详情页。
  2. GET /bzgk/std/showGb?type=online&hcno=<HCNO>
       —— 拿正文页 HTML。内含 `var page = N` 与 N 个 `<div id="i" class="page" bg="...">`。
  3. GET /bzgk/std/viewGbImg?fileName=<bg 原样>
       —— 取精灵图。**必须带请求头 `Cache-Alive: chunked`**，
          否则返回 200 但 Content-Length: 0（拿到 0 字节）。
       实际会 302 跳到 /bzgk/data/<标准号>/<W>-<H>-<序号>_<tok>.webp。

精灵图与页的重组算法（实测确认）
--------------------------------
  - 精灵图 2320×3280 = 10 列 × 10 行瓦片，瓦片 232×328 像素。
  - 一个 bg（精灵图）承载**连续 4~5 页**（实测：88 页 → 22 张精灵图）。
  - 每个 `<div class="page">` 内有若干 `<span class="pdfImg-{列}-{行}"
    style="background-position: -{sx}px -{sy}px;">`：
        源位置 = 精灵图内 (-sx, -sy) 处的 232×328 瓦片
        目标位置 = 画布上 (列×232, 行×328)
  - 同一组内各页的源瓦片**互不重叠**（实测页0=50块 / 页2=25块 / 页4=20块，重叠 0）。
  - 某些页是**纯白页**（0 个 span），属正常（封面背白、空白插页）。

纪律
----
- 抓不到就记抓不到，逐页记 status。
- 每份落盘文件算 SHA256 登记，未来不用重下。
- 重组是**像素搬运**，不做任何内容判断；OCR 另由 tools 层处理。

用法
----
  python fetch_gb.py --standard "GB/T 30453-2013"     # 查目录拿 hcno 再取正文
  python fetch_gb.py --hcno 3FC66D5433FEE4423518769107CF035A
  python fetch_gb.py --standard "GB/T 1226-2017" --max-pages 5
  python fetch_gb.py --manifest                         # 看已取过的正文
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net_env import prepare_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
CATALOG = ROOT / "kb" / "catalog" / "gb_openstd.json"
MANIFEST = RUNS / "gb_fetch_manifest.json"

BASE = "https://openstd.samr.gov.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))

TILE_W, TILE_H = 232, 328
GRID = 10
SPRITE_W, SPRITE_H = TILE_W * GRID, TILE_H * GRID  # 2320 x 3280

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# --------------------------------------------------------------------------
# HTTP（stdlib + cookiejar，零第三方 HTTP 依赖）
# --------------------------------------------------------------------------
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class GbSession:
    """保持 JSESSIONID 的会话，顺序敏感。"""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.base_headers = {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def get(self, url: str, headers: dict | None = None,
            timeout: int = 120) -> tuple[int, bytes, str, str]:
        h = dict(self.base_headers)
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with self.opener.open(req, timeout=timeout) as r:
            return (r.status, r.read(),
                    r.headers.get("Content-Type", ""), r.geturl())


# --------------------------------------------------------------------------
# 目录查询：标准号 -> hcno
# --------------------------------------------------------------------------
def load_catalog() -> list[dict]:
    """目录条目列表。catalog_gb.py 产出的是 {hcno: {...}} 字典，这里摊平。"""
    if not CATALOG.exists():
        raise SystemExit(
            "找不到 kb/catalog/gb_openstd.json。先跑:\n"
            "  python tools/catalog_gb.py --from-file tools/gb_queries.txt")
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        std = data.get("standards")
        if isinstance(std, dict):
            out = []
            for hcno, rec in std.items():
                if isinstance(rec, dict):
                    r = dict(rec)
                    r.setdefault("hcno", hcno)
                    out.append(r)
            return out
        for key in ("standards", "items", "records", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data


def _norm(s: str) -> str:
    return re.sub(r"[\s\-–—_/]+", "", (s or "")).upper()


def find_in_catalog(standard: str) -> dict | None:
    """按标准号（可带或不带年份）匹配目录。返回最合适的一条。"""
    want = _norm(standard)
    entries = load_catalog()
    exact, loose = [], []
    for e in entries:
        num = _norm(e.get("standard_no") or e.get("number") or e.get("std_no") or "")
        if not num:
            continue
        if num == want:
            exact.append(e)
        elif want.startswith(num) or num.startswith(want):
            loose.append(e)
    pool = exact or loose
    if not pool:
        return None
    # 优先现行、其次年份最新
    def score(e: dict) -> tuple:
        st = str(e.get("status") or "")
        alive = 0 if ("废止" in st or "作废" in st) else 1
        return (alive, str(e.get("publish_date") or ""))
    pool.sort(key=score, reverse=True)
    return pool[0]


# --------------------------------------------------------------------------
# 正文页解析
# --------------------------------------------------------------------------
DIV_RE = re.compile(r'<div id="(\d+)" class="page" bg="([^"]*)"')
SPAN_RE = re.compile(
    r'<span class="pdfImg-(\d+)-(\d+)" '
    r'style="background-position:\s*(-?\d+)px\s*(-?\d+)px;">')


def parse_show_gb(html: str) -> tuple[int, list[dict]]:
    """解析正文页 HTML -> (总页数, 每页的瓦片布局)。"""
    m = re.search(r"var\s+page\s*=\s*(\d+)", html)
    total = int(m.group(1)) if m else 0

    starts = [(mm.start(), mm.group(1), mm.group(2)) for mm in DIV_RE.finditer(html)]
    pages: list[dict] = []
    for i, (off, pid, bg) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else len(html)
        seg = html[off:nxt]
        spans = SPAN_RE.findall(seg)
        tiles = [
            {
                "col": int(a), "row": int(b),
                "src_x": -int(x), "src_y": -int(y),
            }
            for a, b, x, y in spans
        ]
        pages.append({
            "page_id": int(pid),
            "bg": bg,
            "tiles": tiles,
            "blank": not tiles,
        })
    return total, pages


# --------------------------------------------------------------------------
# 抓取
# --------------------------------------------------------------------------
def fetch_sprite(sess: GbSession, bg: str, referer: str) -> tuple[bytes, str]:
    """取一张精灵图。**必须带 Cache-Alive: chunked**，否则 0 字节。"""
    url = f"{BASE}/bzgk/std/viewGbImg?fileName={bg}"
    code, body, ctype, final = sess.get(url, headers={
        "Referer": referer,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Cache-Alive": "chunked",
    })
    if not body:
        raise RuntimeError(
            f"精灵图返回 0 字节 (code={code}, ctype={ctype})。"
            "多半是缺 Cache-Alive 头或会话已失效。")
    return body, final


def compose_page(sprite, tiles: list[dict]):
    """按瓦片布局把精灵图重组成一整页 PNG。"""
    from PIL import Image  # 局部导入：只在真正重组时才需要

    canvas = Image.new("RGB", (SPRITE_W, SPRITE_H), (255, 255, 255))
    sw, sh = sprite.size
    for t in tiles:
        sx, sy = t["src_x"], t["src_y"]
        if sx < 0 or sy < 0 or sx + TILE_W > sw or sy + TILE_H > sh:
            continue
        canvas.paste(sprite.crop((sx, sy, sx + TILE_W, sy + TILE_H)),
                     (t["col"] * TILE_W, t["row"] * TILE_H))
    return canvas


def do_fetch(standard: str, hcno: str, max_pages: int = 0,
             out_dir: Path | None = None) -> dict:
    cat = find_in_catalog(standard) if standard else None
    if not hcno:
        if not cat:
            raise SystemExit(
                f"目录里找不到 {standard!r}。先跑 catalog_gb.py 补目录，"
                "或直接用 --hcno。")
        hcno = cat.get("hcno") or ""
    if not hcno:
        raise SystemExit(f"{standard!r} 在目录里没有 hcno，无法取正文。")

    std_id = (cat or {}).get("standard_no") or standard or hcno[:12]
    std_id = re.sub(r"[^A-Za-z0-9._-]+", "_", std_id)
    out_dir = out_dir or (RUNS / f"GB-{std_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    sess = GbSession()
    new_info = f"{BASE}/bzgk/std/newGbInfo?hcno={hcno}"
    show_url = f"{BASE}/bzgk/std/showGb?type=online&hcno={hcno}"

    print(f"[1/3] newGbInfo  {hcno}")
    sess.get(new_info, timeout=60)

    print(f"[2/3] showGb     {show_url}")
    try:
        code, body, ctype, final = sess.get(show_url, headers={"Referer": new_info},
                                           timeout=180)
    except urllib.error.HTTPError as e:
        # 404 = 该标准**没有在线免费正文**（很常见，不是抓取失败）
        if e.code == 404:
            raise SystemExit(
                f"{std_id} 没有在线正文（站点返回 404）。\n"
                "这不是抓取失败——该标准的免费正文在国标全文公开系统里本就不开放。\n"
                "请改用离线来源（GB 官方 PDF、或标准馆/出版社渠道），"
                "或从候选池中另选可开放正文的标准。")
        raise
    html = body.decode("utf-8", errors="replace")
    (out_dir / "showgb.html").write_text(html, encoding="utf-8")
    total, pages = parse_show_gb(html)
    print(f"      var page={total}  div.page={len(pages)}")

    if not pages:
        raise SystemExit("正文页解析不到 div.page —— 站点结构可能已变。")

    if max_pages and max_pages < len(pages):
        pages = pages[:max_pages]

    # 按 bg 分组，只下载用得到的精灵图
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for p in pages:
        groups.setdefault(p["bg"], []).append(p)
    print(f"[3/3] 精灵图 {len(groups)} 张 / 页 {len(pages)}")

    sprite_dir = out_dir / "sprites"
    sprite_dir.mkdir(parents=True, exist_ok=True)
    page_dir = out_dir / "pages"
    page_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for gi, (bg, gpages) in enumerate(groups.items()):
        want = [p for p in gpages if not p["blank"]]
        if not want:
            for p in gpages:
                records.append({
                    "page_id": p["page_id"], "status": "BLANK",
                    "note": "纯白页（0 个瓦片）",
                })
            continue

        # 精灵图缓存：同 bg 同一次会话内取一次
        sname = hashlib.sha256(bg.encode("utf-8")).hexdigest()[:16] + ".webp"
        spath = sprite_dir / sname
        if spath.exists() and spath.stat().st_size > 0:
            sbytes = spath.read_bytes()
            sfinal = f"(cached) {sname}"
        else:
            try:
                sbytes, sfinal = fetch_sprite(sess, bg, show_url)
            except Exception as e:
                print(f"      精灵图失败 bg#{gi}: {e}")
                for p in gpages:
                    records.append({"page_id": p["page_id"], "status": "SPRITE_FAIL",
                                    "error": str(e)})
                continue
            spath.write_bytes(sbytes)

        from PIL import Image
        import io
        sprite = Image.open(io.BytesIO(sbytes)).convert("RGB")

        for p in gpages:
            if p["blank"]:
                records.append({"page_id": p["page_id"], "status": "BLANK",
                                "note": "纯白页（0 个瓦片）"})
                continue
            canvas = compose_page(sprite, p["tiles"])
            pname = f"p{p['page_id']:04d}.png"
            ppath = page_dir / pname
            canvas.save(ppath)
            records.append({
                "page_id": p["page_id"], "status": "OK",
                "file": f"pages/{pname}",
                "sha256": sha256_file(ppath),
                "bytes": ppath.stat().st_size,
                "tiles": len(p["tiles"]),
                "sprite": sname,
            })
        print(f"      精灵图 {gi+1}/{len(groups)}  {len(gpages)} 页  "
              f"{len(sbytes):,} bytes")

    meta = {
        "standard": standard,
        "standard_id": std_id,
        "hcno": hcno,
        "title": (cat or {}).get("title_zh") or (cat or {}).get("title", ""),
        "catalog_status": (cat or {}).get("status", ""),
        "publish_date": (cat or {}).get("publish_date", ""),
        "source": "GB-PUB",
        "url": show_url,
        "page_count": total,
        "fetched_at": datetime.now(CST).isoformat(timespec="seconds"),
        "body_status": "FULL_TEXT_MIRROR",
        "extraction": "OCR_TEXT",
        "notes": "GB/T 正文为栅格图，无文字层；本层只取图不识别，"
                 "OCR 由后续工具处理。",
        "sprite_groups": len(groups),
        "pages": records,
    }
    (out_dir / "fetch_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for r in records if r["status"] == "OK")
    print(f"\n完成：{ok}/{len(records)} 页成功 -> {out_dir.relative_to(ROOT)}")
    return meta


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------
def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"records": []}


def save_manifest(rec: dict) -> None:
    mf = load_manifest()
    mf["records"] = [r for r in mf["records"]
                     if r.get("standard_id") != rec.get("standard_id")]
    mf["records"].append(rec)
    mf["updated_at"] = datetime.now(CST).isoformat(timespec="seconds")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(mf, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--standard", help="标准号，如 GB/T 30453-2013")
    ap.add_argument("--hcno", help="直接给 hcno（跳过目录查询）")
    ap.add_argument("--max-pages", type=int, default=0,
                    help="只取前 N 页（调试用）")
    ap.add_argument("--manifest", action="store_true", help="打印已取正文清单")
    ap.add_argument("--list", action="store_true", help="列出目录中可用标准")
    args = ap.parse_args()

    prepare_env(verbose=True)

    if args.manifest:
        mf = load_manifest()
        if not mf.get("records"):
            print("还没有取过 GB 正文。")
            return 0
        for r in mf["records"]:
            ok = sum(1 for p in r.get("pages", []) if p.get("status") == "OK")
            tot = len(r.get("pages", []))
            print(f"{r.get('standard_id'):<24} {r.get('title','')[:40]:<42} "
                  f"{ok}/{tot} 页  {r.get('fetched_at','')}")
        return 0

    if args.list:
        for e in load_catalog()[:60]:
            print(f"{e.get('standard_no',''):<20} {str(e.get('title',''))[:52]}")
        return 0

    if not args.standard and not args.hcno:
        ap.error("需要 --standard 或 --hcno")

    meta = do_fetch(args.standard or "", args.hcno or "", args.max_pages)
    save_manifest(meta)
    print(f"已登记 -> {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
