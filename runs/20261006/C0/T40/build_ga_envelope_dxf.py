#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
522-35.4179СБ  GA 外形重建 —— DXF 生成器
run 20261006 / candidate C0   对应任务 T40(外形图)/ T11(接口与骨架)

【重要边界】
  1. 本图所有外形尺寸在原图上均带 *,技术要求第 31 条规定「带 * 的尺寸仅供参考」。
     因此本脚本生成的是【包络校核用参考几何】,不是受控接口,不得作为制造依据。
  2. 结构长度(face-to-face)原图未读到,H(颈高)只给了符号无数值。
     这两项不做臆测,脚本按参数留空并在图上显式标注 UNKNOWN。
  3. 只重建外形包络(法兰/阀体/颈部/杠杆),不重建内部件 —— 内部件原图零标注。

输出: 522-35.4179_C0_GA_envelope.dxf  (DXF R12 ASCII, 仅 LINE/CIRCLE/TEXT)
"""
import math, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 已从图纸确认的外形参数(全部带 *,BOUNDED) ----------------------
P = dict(
    DN            = 200.0,   # 标题栏 ДУ200
    bore          = 200.0,   # Ø200*
    hub_od        = 247.0,   # Ø247*
    flange_od     = 295.0,   # Ø295*
    bolt_circle   = 264.0,   # Ø264*
    bolt_holes    = 12,      # 12 отв.
    bolt_hole_d   = 15.0,    # ф15*
    height_total  = 515.0,   # 515*
    lever_span    = 320.0,   # ф320*
    gauge_square  = 24.0,    # □24*
    face_to_face  = None,    # ★ 原图未读到 -> 留空
    neck_height_H = None,    # ★ 原图只给符号 H -> 留空
)

E = []          # DXF 实体累积
LAYERS = {"OUTLINE": 7, "HIDDEN": 8, "CENTER": 1, "DIM": 3, "TEXT": 2, "NOTE": 6}


def _e(code, val):
    E.append(str(code)); E.append(str(val))


def line(x1, y1, x2, y2, layer="OUTLINE"):
    _e(0, "LINE"); _e(8, layer)
    _e(10, "%.4f" % x1); _e(20, "%.4f" % y1); _e(30, "0.0")
    _e(11, "%.4f" % x2); _e(21, "%.4f" % y2); _e(31, "0.0")


def circle(cx, cy, r, layer="OUTLINE"):
    _e(0, "CIRCLE"); _e(8, layer)
    _e(10, "%.4f" % cx); _e(20, "%.4f" % cy); _e(30, "0.0")
    _e(40, "%.4f" % r)


def text(x, y, s, h=5.0, layer="TEXT", rot=0.0):
    _e(0, "TEXT"); _e(8, layer)
    _e(10, "%.4f" % x); _e(20, "%.4f" % y); _e(30, "0.0")
    _e(40, "%.4f" % h); _e(1, s); _e(50, "%.1f" % rot)


def leader(x1, y1, x2, y2, txt, h=4.5):
    line(x1, y1, x2, y2, "DIM")
    line(x2, y2, x2 + 26, y2, "DIM")
    text(x2 + 28, y2 - h / 2, txt, h, "DIM")


# =====================================================================
# 视图 1: Общий вид(主视,沿管轴看)—— 全部尺寸来自图纸,可完整重建
# =====================================================================
def front_view(ox, oy):
    cx, cy = ox, oy
    rf, rh, rb, rbc = P["flange_od"]/2, P["hub_od"]/2, P["bore"]/2, P["bolt_circle"]/2

    circle(cx, cy, rf)                                   # 法兰外径 Ø295*
    circle(cx, cy, rh)                                   # 阀体凸台 Ø247*
    circle(cx, cy, rb)                                   # 通径 Ø200*
    circle(cx, cy, rbc, "CENTER")                        # 螺栓圆 Ø264*
    line(cx - rf - 20, cy, cx + rf + 20, cy, "CENTER")
    line(cx, cy - rf - 20, cx, cy + rf + 20, "CENTER")

    for i in range(P["bolt_holes"]):                      # 12 x ф15*
        a = math.radians(i * 360.0 / P["bolt_holes"])
        circle(cx + rbc*math.cos(a), cy + rbc*math.sin(a), P["bolt_hole_d"]/2)

    # 颈部 + 顶端(高度按 H 未知处理:画一段示意长度并显式标注 UNKNOWN)
    neck_w = rh * 0.72
    neck_h = 150.0                                       # 仅为可视图长度,非设计值
    for sx in (-1, 1):
        line(cx + sx*neck_w, cy + rh, cx + sx*neck_w, cy + rh + neck_h)
    line(cx - neck_w, cy + rh + neck_h, cx + neck_w, cy + rh + neck_h)
    gs = P["gauge_square"]/2
    line(cx - gs, cy + rh + neck_h, cx + gs, cy + rh + neck_h)     # □24* 表接头
    line(cx - gs, cy + rh + neck_h, cx - gs, cy + rh + neck_h + 24)
    line(cx + gs, cy + rh + neck_h, cx + gs, cy + rh + neck_h + 24)
    line(cx - gs, cy + rh + neck_h + 24, cx + gs, cy + rh + neck_h + 24)

    leader(cx + rf, cy + rf*0.72, cx + rf + 30, cy + rf + 40, "OD295*")
    leader(cx + rbc, cy + rbc*0.34, cx + rf + 30, cy + rf + 18, "12 x 15* / BC264*")
    leader(cx + rh*0.7, cy + rh*0.7, cx + rf + 30, cy + rf - 4, "OD247*")
    leader(cx + rb*0.7, cy - rb*0.7, cx + rf + 30, cy + rf - 26, "BORE 200")
    leader(cx, cy + rh + neck_h + 24, cx + rf + 30, cy + rh + neck_h + 30, "SQ24* (pos.15)")
    text(cx - rf - 30, cy + rh + neck_h + 55, "H = UNKNOWN (drawing gives symbol only)", 5.0, "NOTE")
    text(cx - rf - 30, cy + rh + neck_h + 43, "neck shown schematically, NOT to scale", 4.0, "NOTE")
    return cx - rf - 40, cy - rf - 40, cx + rf + 210, cy + rh + neck_h + 70


# =====================================================================
# 视图 2: 侧视/剖视 —— 结构长度未知,只画【纵向包络】并显式留空
# =====================================================================
def side_view(ox, oy):
    rf, rb = P["flange_od"]/2, P["bore"]/2
    hgt = P["height_total"]
    body_len = 240.0                                     # ★ 仅示意,非 face-to-face
    x0 = ox - body_len/2

    for sx in (-1, 1):                                   # 两端法兰(厚度按 15*)
        xa = x0 if sx < 0 else x0 + body_len - 15
        xb = xa + 15
        line(xa, oy - rf, xa, oy + rf)
        line(xb, oy - rf, xb, oy + rf)
        line(xa, oy + rf, xb, oy + rf)
        line(xa, oy - rf, xb, oy - rf)
    # 阀体外廓
    line(x0, oy + rf, x0 + 15, oy + rf)
    line(x0 + 15, oy + rf, x0 + 15, oy + rb)
    line(x0 + 15, oy + rb, x0 + body_len - 15, oy + rb)
    line(x0 + 15, oy + rb, x0 + 15, oy - rb)
    line(x0 + 15, oy - rb, x0 + body_len - 15, oy - rb)
    line(x0 + body_len - 15, oy + rb, x0 + body_len - 15, oy + rf)
    line(x0 + body_len - 15, oy - rb, x0 + body_len - 15, oy - rf)
    # 颈 + 杠杆
    nw = 45.0
    line(x0 + body_len/2 - nw, oy + rf, x0 + body_len/2 - nw, oy + hgt - 30)
    line(x0 + body_len/2 + nw, oy + rf, x0 + body_len/2 + nw, oy + hgt - 30)
    lv = P["lever_span"]/2
    line(x0 + body_len/2 - lv, oy + hgt - 30, x0 + body_len/2 + lv, oy + hgt - 30)
    for sx in (-1, 1):                                   # 杠杆端球
        circle(x0 + body_len/2 + sx*lv, oy + hgt - 30, 9)
    line(x0 + body_len/2, oy - rf, x0 + body_len/2, oy - rf - 25, "CENTER")
    line(x0 - 20, oy, x0 + body_len + 20, oy, "CENTER")

    leader(x0 + body_len/2 - lv, oy + hgt - 30, x0 - 40, oy + hgt - 10, "LEVER SPAN 320*")
    leader(x0 + 7, oy + rf, x0 - 40, oy + rf + 40, "FLANGE 15*")
    leader(x0, oy + rf, x0 - 40, oy + rf + 18, "OD295*")
    leader(x0 + body_len/2, oy - rf - 25, x0 - 40, oy - rf - 45, "TR36x6 STEM (pivot axis)")

    text(x0 - 40, oy - rf - 68,
         "FACE-TO-FACE = UNKNOWN - not legible on source drawing", 5.0, "NOTE")
    text(x0 - 40, oy - rf - 80,
         "obtain from GOST 1536-76; body_len shown is SCHEMATIC ONLY", 4.2, "NOTE")
    text(x0 - 40, oy - rf - 92,
         "internal parts (disc/seat/stem) NOT reconstructed - zero dimensions on GA", 4.2, "NOTE")
    return x0 - 60, oy - rf - 110, x0 + body_len + 60, oy + hgt


# =====================================================================
# 标题块 + 参数表
# =====================================================================
def title_block(x, y):
    w, h = 210.0, 96.0
    for i in range(4):
        yy = y + i*h/4
        line(x, yy, x + w, yy, "OUTLINE")
    for i in range(3):
        xx = x + i*w/3
        line(xx, y, xx, y + h, "OUTLINE")
    rows = [
        "522-35.4179-C0   GA ENVELOPE RECONSTRUCTION",
        "DN200 / PN6 (0.588 MPa)  BRONZE  SWING-DISC CHECK+SHUTOFF",
        "SOURCE: 2 scanned sheets, read via PaddleOCR-VL + zoom verify",
        "ALL DIMS CARRY '*' ON SOURCE = REFERENCE ONLY (note 31)",
        "NOT A MANUFACTURING BASIS. DESIGN STATUS: INPUTS_REGISTERED",
        "T07 FROZEN = NO. Internal geometry unknown.",
    ]
    for i, s in enumerate(rows):
        text(x + 4, y + h - 12 - i*13.5, s, 4.0, "TEXT")


def param_table(x, y):
    rows = [
        ("bore",        "200", "mm", "CONFIRMED", "*"),
        ("flange OD",   "295", "mm", "CONFIRMED", "*"),
        ("hub OD",      "247", "mm", "CONFIRMED", "*"),
        ("bolt circle", "264", "mm", "CONFIRMED", "*"),
        ("holes",       "12x15", "mm", "CONFIRMED", "*"),
        ("height",      "515", "mm", "CONFIRMED", "*"),
        ("lever span",  "320", "mm", "CONFIRMED", "*"),
        ("gauge sq",    "24",  "mm", "CONFIRMED", "*"),
        ("stem thread", "Tr36x6","-", "CONFIRMED", "*"),
        ("mass",        "119", "kg", "CONFIRMED", "-"),
        ("face-to-face", "?","mm", "MISSING",  "-"),
        ("neck height H","?","mm", "MISSING",  "-"),
        ("bronze grade", "?","-",  "MISSING",  "-"),
        ("design press", "?","MPa", "MISSING",  "-"),
    ]
    cw = [46, 26, 14, 34, 10]
    yy = y
    text(x, yy, "PARAMETER / VALUE / UNIT / STATUS / MARK", 5.0, "TEXT")
    yy -= 12
    hdr = ["PARAMETER", "VALUE", "UNIT", "STATUS", "MARK"]
    xx = x
    for w, s in zip(cw, hdr):
        text(xx, yy, s, 4.0, "TEXT"); xx += w
    yy -= 4
    line(x, yy, x + sum(cw), yy, "OUTLINE")
    yy -= 10
    for name, val, unit, st, mark in rows:
        xx = x
        for w, s in zip(cw, [name, val, unit, st, mark]):
            text(xx, yy, s, 4.0, "TEXT"); xx += w
        yy -= 11
    return yy


# =====================================================================
# 组装 DXF
# =====================================================================
def build_dxf(path):
    b = front_view(0, 0)
    s = side_view(b[2] + 120, 0)
    title_block(s[0], s[1] + 130)
    param_table(s[0], s[1] + 250)

    d = []
    d += ["0", "SECTION", "2", "HEADER",
          "9", "$ACADVER", "1", "AC1009",
          "9", "$INSUNITS", "70", "4",          # 4 = millimeters
          "0", "ENDSEC"]
    d += ["0", "SECTION", "2", "TABLES",
          "0", "TABLE", "2", "LAYER", "70", str(len(LAYERS))]
    for name, color in LAYERS.items():
        d += ["0", "LAYER", "2", name, "70", "0", "62", str(color), "6", "CONTINUOUS"]
    d += ["0", "ENDTAB", "0", "ENDSEC"]
    d += ["0", "SECTION", "2", "ENTITIES"]
    d += E
    d += ["0", "ENDSEC", "0", "EOF"]

    with open(path, "w", encoding="ascii", errors="replace") as f:
        f.write("\n".join(d) + "\n")
    return len(E) // 2


if __name__ == "__main__":
    out = os.path.join(HERE, "522-35.4179_C0_GA_envelope.dxf")
    n = build_dxf(out)
    print("=" * 70)
    print("DXF 生成完成")
    print("  文件 : %s" % out)
    print("  实体 : %d" % n)
    print("  单位 : mm (INSUNITS=4)")
    print("  图层 : %s" % ", ".join(LAYERS))
    print()
    print("  重建来源:bore/flange/hub/bolt circle/holes/height/lever/gauge  (CONFIRMED)")
    print("  未臆测  :face-to-face, neck height H, 全部内部件几何")
    print("  用途    :包络校核与接口讨论。制造依据须回 GOST 1536-76 + CAD 原图。")
    print("=" * 70)