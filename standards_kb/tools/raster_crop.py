# -*- coding: utf-8 -*-
"""raster_crop.py — 从扫描型 PDF 中抽取【纯扫描位图】并按 PDF 点坐标裁剪。

为什么需要这个工具：
    archive.org 提供的 ASME BPVC PDF 是 "Xerox 扫描 + Adobe Paper Capture OCR" 产物。
    页面主体是 1-bit 位图，OCR 文本层是【重新排布】的 Type1 字体并叠画在位图之上。
    因此 get_pixmap() 渲染出来的是 "OCR 文本 + 扫描原图" 的叠加层，不是印刷原貌；
    OCR 会吞掉空格、吃掉小数点、把数字认错。
    要核原文印刷体，必须绕开文本层，直接取位图像素。

用法：
    python tools/raster_crop.py <pdf> <page> --full <out.png>              导出整页位图
    python tools/raster_crop.py <pdf> <page> --rect x0 x1 y0 y1 <out.png>    按点坐标裁剪
    python tools/raster_crop.py <pdf> <page> --probe <x0> <x1> <y0> <y1>      只报列直方图

坐标为 PDF point（1/72 inch），原点在左上角。--scale N 对裁剪结果做 N 倍 LANCZOS 放大。
"""
import sys
import io
import fitz
from PIL import Image


def load_raster(doc, page):
    imgs = page.get_images(full=True)
    if not imgs:
        raise SystemExit("page has no raster image (not a scanned page)")
    # 取面积最大的那张
    best = None
    for img in imgs:
        d = doc.extract_image(img[0])
        size = (d.get("width") or 0) * (d.get("height") or 0)
        if best is None or size > best[0]:
            best = (size, d)
    return Image.open(io.BytesIO(best[1]["image"]))


def main(argv):
    if len(argv) < 4:
        raise SystemExit(__doc__)
    pdf_path = argv[1]
    page_no = int(argv[2])
    mode = argv[3]

    doc = fitz.open(pdf_path)
    page = doc[page_no - 1]
    pr = page.rect
    im = load_raster(doc, page)
    sx = im.size[0] / pr.width
    sy = im.size[1] / pr.height
    print("raster=%dx%d  page=%.2fx%.2f pt  scale=%.4f px/pt" % (
        im.size[0], im.size[1], pr.width, pr.height, sx))

    if mode == "--full":
        out = argv[4]
        im.save(out)
        print("saved", out, im.size)
        return

    if mode == "--rect":
        x0, x1, y0, y1 = (float(v) for v in argv[4:8])
        out = argv[8]
        scale = int(argv[9]) if len(argv) > 9 else 1
    elif mode == "--probe":
        x0, x1, y0, y1 = (float(v) for v in argv[4:8])
    else:
        raise SystemExit("mode must be --full / --rect / --probe")

    px0, px1 = int(x0 * sx), int(x1 * sx)
    py0, py1 = int(y0 * sy), int(y1 * sy)
    crop = im.crop((px0, py0, px1, py1))
    print("pixel box: x=[%d,%d) y=[%d,%d)  size=%s" % (px0, px1, py0, py1, crop.size))

    if mode == "--probe":
        w, h = crop.size
        px = crop.load()
        for cx in range(w):
            cnt = sum(1 for cy in range(h) if px[cx, cy] < 128)
            print("%5d: %3d %s" % (px0 + cx, cnt, "#" * cnt))
        return

    if scale > 1:
        crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
    crop.save(out)
    print("saved", out, crop.size)


if __name__ == "__main__":
    main(sys.argv)
