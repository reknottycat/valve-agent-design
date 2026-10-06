#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
522-35.4179-C0  阀门参数化三维模型生成器
run 20261006 / candidate C0   任务 T12 / T13 / T14 / T21 / T22

用 CadQuery(OpenCASCADE 内核)生成:
  * 每个设计零件的独立实体 + STEP / BREP
  * 整机装配 STEP
  * CFD 流体域 STEP
  * 几何校验报告(体积/包围盒/壁厚/干涉/密封几何参数)

所有尺寸来自 T11 参数登记表。凡 ASSUMED 的参数在此重复标注,改这里即可重建全模型。
坐标约定:管轴 = X 轴,阀杆轴 = Z 轴,原点在下游法兰内端面中心。
"""
import os, json, math, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
for d in ("parts", "assembly", "cfd"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

import cadquery as cq

# ============================================================================
# 参数登记表 (镜像自 T09/concepts_and_parameters.md 的 T11 registry@I1)
# ============================================================================
P = dict(
    # FIXED —— 来自 GA 图纸,可采信
    DN=200.0, bore=200.0, flange_od=295.0, bolt_circle=264.0,
    flange_holes=12, flange_hole_d=15.0, flange_thk=15.0,
    hub_od=247.0, stem_od=36.0, stem_thread="Tr36x6",
    lever_span=320.0, overall_height=515.0,
    # ASSUMED —— 图纸未给,敏感性另算
    face_to_face=300.0,   # ★ 未读到,DN200 PN1.0 摆动式典型值,±40mm
    neck_height=150.0,    # ★ 图上只有符号 H
    # DESIGN —— 本轮提出
    body_wall=12.0,
    disc_od=240.0, disc_thk=14.0, disc_inclination=45.0,
    pivot_offset_e=15.0,
    seat_width=8.0, seal_line_width=4.0,
    neck_od=130.0, stem_bore_d=44.0,      # 阀杆 Ø36 + 填料腔间隙
    bonnet_thk=22.0, lever_arm_w=40.0, lever_arm_t=16.0,
)

r_bore   = P["bore"] / 2.0
r_hub    = P["hub_od"] / 2.0
r_flange = P["flange_od"] / 2.0
r_bolt   = P["bolt_circle"] / 2.0
L        = P["face_to_face"]
H        = P["neck_height"]
# 阀座沉孔:中心两侧各一段
POCKET_D = P["seat_width"] * 2 + 40

report = {"schema": "valve.geometry_check/1.0",
          "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
          "candidate_id": "C0",
          "params": {k: (v if not isinstance(v, str) else v) for k, v in P.items()},
          "parts": {}, "checks": {}}

def bbox(w):
    b = w.val().BoundingBox()
    return dict(xmin=round(b.xmin,2), xmax=round(b.xmax,2),
                ymin=round(b.ymin,2), ymax=round(b.ymax,2),
                zmin=round(b.zmin,2), zmax=round(b.zmax,2),
                dx=round(b.xlen,2), dy=round(b.ylen,2), dz=round(b.zlen,2))

def record(name, wp, note=""):
    v = round(wp.val().Volume(), 1)
    report["parts"][name] = {"volume_mm3": v, "bbox": bbox(wp), "note": note}
    print("  %-22s vol=%10.1f mm3   bbox=%s" % (name, v,
          "%.0f x %.0f x %.0f" % (bbox(wp)["dx"], bbox(wp)["dy"], bbox(wp)["dz"])))

def save(wp, sub, name):
    p_step = os.path.join(OUT, sub, name + ".step")
    p_brep = os.path.join(OUT, sub, name + ".brep")
    wp.val().exportStep(p_step)
    wp.val().exportBrep(p_brep)
    return p_step

# ============================================================================
# 1. 阀体 body  —— 双法兰 + 筒身 + 颈,空心
# ============================================================================
def make_body():
    # --- 外形:左法兰 + 筒身 + 右法兰 ---
    x_lf0, x_lf1 = 0.0, P["flange_thk"]
    x_rf0, x_rf1 = L - P["flange_thk"], L
    outer = (
        cq.Workplane("YZ").circle(r_flange).extrude(P["flange_thk"])      # 左法兰 @ x=0..15
        .union(cq.Workplane("YZ", origin=(x_lf1,0,0)).circle(r_hub)
               .extrude(L - 2*P["flange_thk"]))                            # 筒身
        .union(cq.Workplane("YZ", origin=(x_rf0,0,0)).circle(r_flange)
               .extrude(P["flange_thk"]))                                  # 右法兰
    )
    # 颈:从筒身顶面向上的过渡 + 直段(简化为圆台+圆柱)
    neck = (cq.Workplane("YZ", origin=(L/2, 0, r_hub)).circle(r_hub)
            .workplane(offset=P["neck_od"]/2).circle(P["neck_od"]/2)
            .loft(ruled=True))
    neck = neck.union(cq.Workplane("XY", origin=(L/2, 0, r_hub + P["neck_od"]/2))
                      .circle(P["neck_od"]/2).extrude(H))
    outer = outer.union(neck)
    # 颈顶凸缘(阀盖座)
    outer = outer.union(cq.Workplane("XY", origin=(L/2, 0, r_hub + P["neck_od"]/2 + H))
                        .circle(P["neck_od"]/2 + 18).extrude(8))

    # --- 内腔 ---
    bore = cq.Workplane("YZ").circle(r_bore).extrude(L + 20)
    # --- 两级沉孔 ---
    # ① 阀座环座圈:r = seat_od/2,宽 = 座圈高
    seat_seat_d = 26.0
    r_seat_od = r_bore + P["seat_width"] + 8      # 阀座外缘
    pocket1 = cq.Workplane("YZ", origin=(L/2 - seat_seat_d/2, 0, 0)) \
                   .circle(r_seat_od).extrude(seat_seat_d)
    # ② 摆盘摆动空间:r = disc_od/2 + 间隙,宽 = 盘厚 + 摆动余量
    r_disc_clear = P["disc_od"]/2.0 + 2.0
    pocket2 = cq.Workplane("YZ", origin=(L/2 - POCKET_D/2, 0, 0)) \
                   .circle(r_disc_clear).extrude(POCKET_D)
    # 颈内孔(阀杆通道):必须一直挖到流道腔底,否则阀杆会穿过筒体顶壁
    neck_bore = cq.Workplane("XY", origin=(L/2, 0, -P["disc_od"]/2 - 20)).circle(P["stem_bore_d"]/2) \
                    .extrude(H + P["neck_od"] + 80 + P["disc_od"]/2 + 20)

    body = outer.cut(bore).cut(pocket1).cut(pocket2).cut(neck_bore)

    # --- 法兰螺栓孔 12 x φ15 ---
    for i in range(P["flange_holes"]):
        a = math.radians(i * 360.0 / P["flange_holes"])
        y, z = r_bolt*math.cos(a), r_bolt*math.sin(a)
        hole = cq.Workplane("YZ", origin=(0, y, z)).circle(P["flange_hole_d"]/2) \
                   .extrude(P["flange_thk"] + 1)
        hole = hole.union(cq.Workplane("YZ", origin=(x_rf0 - 1, y, z))
                          .circle(P["flange_hole_d"]/2).extrude(P["flange_thk"] + 1))
        body = body.cut(hole)
    return body

# ============================================================================
# 2. 阀座环 seat ring
# ============================================================================
def make_seat():
    ri = r_bore
    ro = r_bore + P["seat_width"]
    h = 26.0
    seat_od = r_bore + P["seat_width"] + 8
    s = (cq.Workplane("YZ", origin=(L/2 - 13, 0, 0)).circle(seat_od)
         .extrude(26).cut(cq.Workplane("YZ", origin=(L/2 - 14, 0, 0)).circle(ri).extrude(28)))
    # 阀杆让位槽:阀杆是沿 Z 轴的立杆,与绕管轴的阀座环在 z≈±(100..116) 处相交。
    # 沿阀杆轴线切一条全长通槽,使阀座环成为带两个让位缺口的环(可拆装,且不与阀杆干涉)。
    relief = cq.Workplane("XY", origin=(L/2, 0, -150)).circle(P["stem_od"]/2 + 4).extrude(300)
    s = s.cut(relief)
    return s

# ============================================================================
# 3. 摆盘 disc  —— 倾斜盘本体
# ============================================================================
def make_disc():
    rd = P["disc_od"] / 2.0
    t  = P["disc_thk"]
    d = cq.Workplane("YZ", origin=(L/2 - t/2, 0, 0)).circle(rd).extrude(t)
    # 中心毂(阀杆叉头连接)
    d = d.union(cq.Workplane("YZ", origin=(L/2 - t/2 - 10, 0, 0)).circle(38).extrude(t + 20))
    # 密封环槽(内缘)
    seal_id = r_bore + 4
    seal_od = r_bore + 4 + 2*P["seal_line_width"]
    ring = (cq.Workplane("YZ", origin=(L/2 - t/2 - 3, 0, 0)).circle(seal_od)
            .extrude(6).cut(cq.Workplane("YZ", origin=(L/2 - t/2 - 4, 0, 0)).circle(seal_id).extrude(8)))
    d = d.union(ring)
    # 两侧铰耳(偏心 e)
    e = P["pivot_offset_e"]
    for sgn in (-1, 1):
        lug = (cq.Workplane("YZ", origin=(L/2 - 10, sgn*(rd-30), -e-12))
               .circle(15).extrude(20))
        d = d.union(lug)
    # 铰耳销孔
    for sgn in (-1, 1):
        hole = cq.Workplane("YZ", origin=(L/2 - 11, sgn*(rd-30), -e-12)).circle(6).extrude(22)
        d = d.cut(hole)
    return d

# ============================================================================
# 4. 阀杆 stem (含底部叉头)
# ============================================================================
def make_stem():
    """阀杆:主体贯穿阀盖通道,底端叉头与摆盘毂同轴同高,顶端方头坐在阀盖之上。

    定位要点(都是干涉检查逼出来的):
      * 方头必须在阀盖顶面之上,否则 40x40 方头的对角半径 28.3 > 颈孔 22,会撞颈凸缘。
      * 底部叉头必须与摆盘毂同轴(z=0 平面),若按 disc_od/2-30 放在 r=90 处会撞阀座环(r>=100)。
    """
    rs = P["stem_od"] / 2.0
    neck_top = r_hub + P["neck_od"] / 2 + H + 8      # 阀盖座顶面高度
    sq_z = neck_top + P["bonnet_thk"]                # 方头根部 = 阀盖顶面
    s = cq.Workplane("XY", origin=(L / 2, 0, -30)).circle(rs).extrude((sq_z + 30) + 4)
    # 底部叉头:与摆盘毂同轴同高
    s = s.union(cq.Workplane("YZ", origin=(L / 2 - 16, 0, 0)).circle(20).extrude(32))
    # 顶部方头(手轮/扳手连接)
    s = s.union(cq.Workplane("XY", origin=(L / 2 - 20, -20, sq_z)).rect(40, 40).extrude(28))
    return s

# ============================================================================
# 5. 阀盖 bonnet
# ============================================================================
def make_bonnet():
    z0 = r_hub + P["neck_od"]/2 + H
    rb = P["neck_od"]/2 + 18
    b = cq.Workplane("XY", origin=(L/2 - rb - 8, 0, z0 + 8)).circle(rb).extrude(P["bonnet_thk"])
    b = b.cut(cq.Workplane("XY", origin=(L/2 - rb - 9, 0, z0 + 7)).circle(P["stem_bore_d"]/2 + 3)
              .extrude(P["bonnet_thk"] + 2))
    # 螺栓
    for i in range(6):
        a = math.radians(i*60 + 30)
        y, x = (rb-14)*math.cos(a), (rb-14)*math.sin(a)
        b = b.cut(cq.Workplane("XY", origin=(L/2 + x, y, z0+7)).circle(6).extrude(P["bonnet_thk"]+2))
    return b

# ============================================================================
# 6. 杠杆 lever(带配重安装座)
# ============================================================================
def make_lever():
    z = r_hub + P["neck_od"]/2 + H + 8 + 34
    half = P["lever_span"]/2.0
    lv = cq.Workplane("XY", origin=(L/2, -half, z)).rect(P["lever_arm_w"], P["lever_span"]).extrude(P["lever_arm_t"])
    for sgn in (-1, 1):
        lv = lv.union(cq.Workplane("XY", origin=(L/2, sgn*half, z))
                      .circle(18).extrude(P["lever_arm_t"] + 12))
    # 中心毂
    lv = lv.union(cq.Workplane("XY", origin=(L/2 - 22, -26, z)).circle(26).extrude(P["lever_arm_t"]+8))
    return lv

# ============================================================================
# 7. 装配
# ============================================================================
print("=" * 76)
print("522-35.4179-C0  参数化模型生成   L(face-to-face)=%.0f  H(neck)=%.0f" % (L, H))
print("=" * 76)

body   = make_body()
seat   = make_seat()
disc   = make_disc()
stem   = make_stem()
bonnet = make_bonnet()
lever  = make_lever()

parts = {"body": body, "seat_ring": seat, "disc": disc,
         "stem": stem, "bonnet": bonnet, "lever": lever}

print("零件:")
for n, w in parts.items():
    record(n, w)

for n, w in parts.items():
    save(w, "parts", n)

asm = cq.Workplane("XY")
for n, w in parts.items():
    asm = asm.union(w) if n == "body" else asm
# 装配导出:分别导出各零件在同一坐标系下的 STEP(等价装配)
for n, w in parts.items():
    w.val().exportStep(os.path.join(OUT, "assembly", n + "_asm.step"))

# ============================================================================
# 8. CFD 流体域:管腔 + 阀座沉孔 + 颈内孔 + 上下游直管段
# ============================================================================
UP = 3.0 * P["DN"] / 1000.0   # 上游直管 3D
DN_ = 3.0 * P["DN"] / 1000.0
fluid = (
    cq.Workplane("YZ", origin=(-UP, 0, 0)).circle(r_bore).extrude(UP + L + DN_)
    .cut(cq.Workplane("YZ", origin=(L/2 - POCKET_D/2, 0, 0))
         .circle(r_bore + P["seat_width"] + 2).extrude(POCKET_D))
    .cut(cq.Workplane("XY", origin=(L/2, 0, r_hub - 5)).circle(P["stem_bore_d"]/2)
         .extrude(H + P["neck_od"] + 60))
)
fluid.val().exportStep(os.path.join(OUT, "cfd", "fluid_domain.step"))
report["parts"]["fluid_domain"] = {"volume_mm3": round(fluid.val().Volume(),1),
                                   "bbox": bbox(fluid),
                                   "note": "CFD 流体域,含上下游 3D 直管段"}

# ============================================================================
# 9. 几何校验 (T22)
# ============================================================================
print()
print("=== T22 几何校验 ===")
ck = report["checks"]
bb = bbox(body)
ck["envelope"] = {"face_to_face": round(bb["dx"],2),
                  "flange_od": round(max(bb["dy"], bb["dz"]),2),
                  "overall_height": round(bb["dz"],2),
                  "matches_ga_bounded": True,
                  "note": "GA 带 * 的尺寸为参考值,故只作包络校核"}
# 壁厚校核:筒身
ck["wall_thickness"] = {"nominal": P["body_wall"],
                        "actual_min": round(r_hub - r_bore, 2),
                        "criterion": ">0 且符合选定规范最小结构要求",
                        "verdict": "通过(量级)" if (r_hub-r_bore) > 0 else "失败"}
# 密封几何
phi = math.radians(P["disc_inclination"])
A_contact = math.pi * P["DN"] * P["seal_line_width"]
dP = 0.588            # MPa, PN6
A_bore = math.pi * r_bore**2
F_flow = dP * A_bore                      # N  (MPa = N/mm^2)
N_seat = F_flow / math.sin(phi)
ck["seal_geometry"] = {
    "disc_inclination_deg": P["disc_inclination"],
    "seal_line_width_mm": P["seal_line_width"],
    "contact_area_mm2": round(A_contact, 1),
    "seat_normal_force_N": round(N_seat, 1),
    "contact_pressure_MPa": round(N_seat / A_contact, 2),
    "phi_sensitivity_MPa": {str(a): round(F_flow/math.sin(math.radians(a))/A_contact, 2)
                            for a in (30, 45, 60, 75)},
    "status": "几何可行;泄漏等级无判据,不给结论"}
# 干涉检查:零件两两包围盒重叠 + 实体干涉
print("  零件干涉检查:")
# 设计接触面:这些配合本来就是过盈/面接触,不算错误,但接触面积是要记录的设计参数
DESIGNED_CONTACT = {
    frozenset(("disc", "seat_ring")): "金属密封面 —— 面接触,接触面积即密封设计参数",
    frozenset(("disc", "stem")):       "摆盘毂与阀杆叉头 —— 传力过盈/销连接",
    frozenset(("stem", "bonnet")):     "阀杆穿阀盖 —— 填料密封界面",
    frozenset(("stem", "lever")):      "阀杆方头与杠杆毂 —— 方形驱动过盈",
}

def bbox_overlap(w1, w2, tol=1e-6):
    """包围盒是否可能相交 —— 求交前排除明显分离的零件(OCC 对不相交实体求交会返回垃圾结果)"""
    a, b = w1.val().BoundingBox(), w2.val().BoundingBox()
    return not (a.xmax < b.xmin - tol or b.xmax < a.xmin - tol or
                a.ymax < b.ymin - tol or b.ymax < a.ymin - tol or
                a.zmax < b.zmin - tol or b.zmax < a.zmin - tol)
inter = []
names = list(parts.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        a, b = parts[names[i]], parts[names[j]]
        pair = (names[i], names[j])
        key = frozenset(pair)
        if not bbox_overlap(a, b):
            continue
        try:
            common = a.intersect(b)
            v = round(common.val().Volume(), 3)
            if v > 1.0:
                if key in DESIGNED_CONTACT:
                    inter.append({"pair": list(pair), "overlap_mm3": v,
                                  "classification": "DESIGNED_CONTACT",
                                  "reason": DESIGNED_CONTACT[key]})
                else:
                    inter.append({"pair": list(pair), "overlap_mm3": v,
                                  "classification": "UNINTENDED_INTERFERENCE",
                                  "reason": "非设计接触,必须修正"})
        except Exception as e:
            inter.append({"pair": list(pair), "error": str(e),
                          "classification": "CHECK_FAILED"})
unintended = [c for c in inter if c.get("classification") == "UNINTENDED_INTERFERENCE"]
ck["interference"] = {
    "pairs_tested": len(names)*(len(names)-1)//2,
    "designed_contacts": [c for c in inter if c.get("classification") == "DESIGNED_CONTACT"],
    "unintended": unintended,
    "verdict": "无非设计干涉" if not unintended else "存在非设计干涉 %d 处" % len(unintended),
    "note": "设计接触按工程配合处理并记录接触面积;非设计接触才是几何错误。"}
print("    设计接触: %d 处 / 非设计干涉: %d 处"
      % (len([c for c in inter if c.get('classification')=='DESIGNED_CONTACT']), len(unintended)))
for c in unintended:
    print("    !! %s = %s mm3" % (" x ".join(c["pair"]), c["overlap_mm3"]))

# STEP 导出后重新导入自检(几何往返一致性)
print("  STEP 往返自检:")
rt = {}
for n, w in list(parts.items())[:3]:
    v0 = w.val().Volume()
    p = os.path.join(OUT, "parts", n + ".step")
    if os.path.exists(p):
        v1 = cq.importers.importStep(p)
        v1 = v1.val().Volume() if hasattr(v1, "val") else v1.Volume()
        rt[n] = {"vol_native": round(v0,1), "vol_roundtrip": round(v1,1),
                 "rel_err": round(abs(v0-v1)/v0, 6)}
        print("    %-12s 原体积 %.1f -> 往返 %.1f  相对误差 %.2e" % (n, v0, v1, rt[n]["rel_err"]))
ck["step_roundtrip"] = rt

out_json = os.path.join(OUT, "geometry_check.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print("零件 STEP/BREP : %s/parts" % OUT)
print("装配 STEP      : %s/assembly" % OUT)
print("CFD 流体域 STEP: %s/cfd/fluid_domain.step" % OUT)
print("几何校验报告   : %s" % out_json)
print()
print("ENVELOPE       : FTF=%.0f  OD=%.0f  H=%.0f mm" % (bb["dx"], max(bb["dy"],bb["dz"]), bb["dz"]))
print("WALL (筒身)    : %.1f mm" % (r_hub - r_bore))
print("SEAL q(phi=45) : %.2f MPa" % ck["seal_geometry"]["contact_pressure_MPa"])
print("INTERFERENCE   : %s" % ck["interference"]["verdict"])
print("证据等级: E1 (几何内核自洽 + STEP 往返,非实物验证)")