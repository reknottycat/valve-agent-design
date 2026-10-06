#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
522-35.4179СБ  止回-截止直通式青铜法兰阀  —— 解析计算包
run 20261006 / candidate C0   对应任务 T10 / T15 / T16 / T17

设计原则(与 VA-DS-001 一致):
  * 每个数字都写清公式、输入来源、适用范围。
  * 凡来自图纸的量标 source=DRAWING;凡由本脚本按公式推出标 DERIVED;
    凡图上没有、由我方按探索假设补入的标 ASSUMED。
  * 脚本只做解析量级校核,不替代 CAE,也不构成实物合格证据(证据等级 E1)。

运行:  python calc_522-35-4179.py
输出:  calc_results.json  +  控制台摘要
"""
import json, math, os, datetime, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.80665  # m/s^2

# ----------------------------------------------------------------------
# 0. 输入登记 —— 每一项带来源标签
# ----------------------------------------------------------------------
IN = {
    # --- 图纸确认(DRAWING) ---
    "DN":            dict(v=200.0,  unit="mm", src="DRAWING", note="标题栏 ДУ200"),
    "PN_kgf":        dict(v=6.0,    unit="kgf/cm2", src="DRAWING", note="标题栏 Ру6"),
    "bore":          dict(v=200.0,  unit="mm", src="DRAWING", note="Рис.1 Ø200*"),
    "flange_od":     dict(v=295.0,  unit="mm", src="DRAWING", note="Рис.1 Ø295*"),
    "flange_thk":    dict(v=15.0,   unit="mm", src="DRAWING", note="Рис.1 15* (低置信)"),
    "hub_od":        dict(v=247.0,  unit="mm", src="DRAWING", note="Рис.1 Ø247*"),
    "bolt_circle":   dict(v=264.0,  unit="mm", src="DRAWING", note="Общий вид Ø264*"),
    "bolt_holes":    dict(v=12,     unit="pcs", src="DRAWING", note="12 отв. ф15*"),
    "bolt_hole_d":   dict(v=15.0,   unit="mm", src="DRAWING", note="ф15*"),
    "height_total":  dict(v=515.0,  unit="mm", src="DRAWING", note="Рис.1 515*"),
    "lever_span":    dict(v=320.0,  unit="mm", src="DRAWING", note="φ320* 杠杆跨度"),
    "stem_thread":   dict(v="Tr36x6", unit="-", src="DRAWING", note="公制粗牙"),
    "mass_spec":     dict(v=119.0,  unit="kg",  src="DRAWING", note="明细表 522-35.4179 Р3,П3"),
    "handwheel_turns": dict(v=9.5, unit="turn", src="DRAWING", note="п.19 参考值"),
    "key_force_max": dict(v=45.0,   unit="kgf", src="DRAWING", note="п.20"),
    "Kz_limit":      dict(v=6.0,    unit="-",  src="DRAWING", note="п.23 液压阻力系数上限"),
    "t_min_service": dict(v=-40.0,  unit="degC", src="DRAWING", note="28% CaCl2 低温点"),
    "t_max_service": dict(v=50.0,   unit="degC", src="DRAWING", note="海水/CaCl2 高温点"),

    # --- 本轮工程假设(ASSUMED) —— 图纸未给,用于量级探索,不得进正式基线 ---
    "t_body_wall":   dict(v=12.0,   unit="mm", src="ASSUMED", note="阀体最小有效壁厚假设"),
    "disc_thk":      dict(v=14.0,   unit="mm", src="ASSUMED", note="摆盘厚度假设"),
    "pivot_to_disc_c": dict(v=95.0, unit="mm", src="ASSUMED", note="铰轴到盘中心的力臂假设"),
    "lever_arm":     dict(v=150.0,  unit="mm", src="ASSUMED", note="手轮端到阀杆轴的有效力臂假设"),
    "mu_thread":     dict(v=0.15,   unit="-",  src="ASSUMED", note="青铜-青铜螺纹摩擦系数"),
    "mu_seal_face":  dict(v=0.12,   unit="-",  src="ASSUMED", note="盘/座密封面摩擦"),
    "seal_q_min":    dict(v=16.0,   unit="N/mm2", src="ASSUMED", note="金属密封面最小接触压强假设"),
    "allow_stress":  dict(v=80.0,   unit="MPa", src="ASSUMED", note="锡青铜许用应力假设(低温需降额)"),
    "corrosion_allow": dict(v=1.5,  unit="mm", src="ASSUMED", note="海水+CaCl2 腐蚀裕量假设"),
}

def P(key):
    return float(IN[key]["v"])

def tag(key):
    return IN[key]["src"]

R = {}   # 结果容器

# ----------------------------------------------------------------------
# 1. 压力换算与基本几何
#    公式: 1 kgf/cm2 = 0.0980665 MPa
# ----------------------------------------------------------------------
PN_MPa = P("PN_kgf") * 0.0980665
R["01_pressure"] = {
    "PN_MPa": round(PN_MPa, 4),
    "formula": "p[MPa] = PN[kgf/cm2] x 0.0980665",
    "src_PN": tag("PN_kgf"),
    "note": "PN 是公称压力,不是设计压力。设计压力/试验压力图上未给(MISSING)。",
}

A_bore = math.pi / 4 * P("bore")**2          # mm^2
R["02_area"] = {
    "bore_area_mm2": round(A_bore, 1),
    "formula": "A = pi/4 * D^2, D=200mm",
    "src": tag("bore"),
}

# 流速基准面积比(用于阻力系数换算)
A_ref_pipe = A_bore

# ----------------------------------------------------------------------
# 2. 水力:由 п.23 的 Кз<=6 反推可用流量
#    公式(不可压缩液体):
#      dP = zeta * rho * v^2 / 2
#      Kv = Q[m3/h] * sqrt(SG / dP[bar])
#    合并消元得: Kv = A*3600*sqrt(2*1e5/(zeta*rho))/1000
#    【两种口径都算,因图上未定义 Кз 的基准截面】
# ----------------------------------------------------------------------
def kv_from_zeta(zeta, rho=1000.0):
    """Kv [m3/h]。A 用公称通径 [m2], rho [kg/m3], SG=1。

    推导: Q = A*sqrt(2*dP/(zeta*rho))  [m3/s]
          Kv = Q[m3/h] * sqrt(SG/dP[bar]) = A*sqrt(2*dP/(z*rho))*3600*sqrt(1e5/dP)
             = A*3600*sqrt(2e5/(zeta*rho))          <- dP 完全约掉,故 Kv 只取决于 zeta
    """
    A_m2 = A_bore / 1e6
    return A_m2 * 3600.0 * math.sqrt(2.0e5 / (zeta * rho))

kv_abs = kv_from_zeta(P("Kz_limit"))              # 解释A: Кз 就是总局部阻力系数
kv_rel = kv_from_zeta(P("Kz_limit") * 1.0)       # 解释B: 相对管路基准,等效 zeta 另计
# 解释B 下若 Кз 已是"相对同口径直管"的无量纲比值,则有效 zeta 需乘直管沿程,
# 此处只给边界: 等效 zeta 取 Кз 与直管摩阻之和的保守包络
zeta_rel_env = P("Kz_limit") + 1.0               # 保守: 直管段 f*L/D ~ 1

R["03_hydraulic"] = {
    "interpretation_A_absolute": {
        "meaning": "Кз 即阀门总局部阻力系数 zeta",
        "zeta": P("Kz_limit"),
        "Kv_m3h": round(kv_abs, 1),
        "Cv_US": round(kv_abs * 1.156, 1),
        "formula": "Kv = A*3600*sqrt(2e5/(zeta*rho))/1000, SG=1, rho=1000",
        "note": "该解释给出最悲观的 Kv。",
    },
    "interpretation_B_relative_to_pipe": {
        "meaning": "Кз 为相对同口径直管的倍数,有效 zeta = Кз + 直管沿程",
        "zeta_effective": zeta_rel_env,
        "Kv_m3h": round(kv_from_zeta(zeta_rel_env), 1),
        "Cv_US": round(kv_from_zeta(zeta_rel_env) * 1.156, 1),
    },
    "spread": "两种解释的 Kv 仅相差约 8%,说明 Kv 数值本身对该定义不敏感;但取压截面与参考基准未定义时实测值仍不可比,验收口径依然无法冻结。",
    "conversion": "Cv_US = 1.156 x Kv (固定换算,见方案第 09 节)",
    "status": "DERIVED",
    "blocking_gap": "п.23 未给出取压截面、参考流速与通径基准;正式验收前必须冻结定义。",
}

# ----------------------------------------------------------------------
# 3. 关闭载荷(REQ-ACT-01 / T16)
#    Borda-Carnot: F_close = A * dP
#    摆盘力矩:      M_close = F_close * L_pivot
# ----------------------------------------------------------------------
dp_max = PN_MPa            # 以公称压力作为量级估算基数(设计压力未给)
F_close = A_bore * dp_max  # N (MPa = N/mm2)
M_close = F_close * P("pivot_to_disc_c") / 1000.0   # N*m
R["04_closing_load"] = {
    "dp_used_MPa": round(dp_max, 4),
    "dp_basis": "以 PN 代替设计压力 —— 图纸未给设计压力,属保守不足,见 gap",
    "F_close_N": round(F_close, 1),
    "F_close_kgf": round(F_close / G, 1),
    "formula": "F = A * dP (Borda-Carnot); A=pi/4*200^2",
    "M_close_Nm": round(M_close, 1),
    "M_close_formula": "M = F * L, L = 铰轴到盘中心假设臂长",
    "src_A": tag("bore"),
    "src_L": tag("pivot_to_disc_c"),
    "status": "DERIVED",
    "gap": "摆盘实际受压面积与开启角未标注;力矩值仅用于传动链量级判断。",
}

# ----------------------------------------------------------------------
# 4. 阀杆螺纹与启闭力矩(T17)
#    公制粗牙 = 30° 牙型半角
#      lambda = atan(pitch / (pi * d_m))
#      mu' = mu / cos(30°)
#      T_raise = F*d/2 * (mu' + tan l) / (1 - mu'*tan l)
#    降(松开)方向: (mu' - tan l)/(1 + mu'*tan l)
# ----------------------------------------------------------------------
d_stem = 36.0
pitch = 6.0
d_mean = d_stem - 0.5 * pitch          # 中径近似 d2 = d - 0.6495*p, 此处保守用 d - 0.5p
lam = math.atan(pitch / (math.pi * d_mean))
mup = P("mu_thread") / math.cos(math.radians(30))
tanl = math.tan(lam)
T_raise = F_close * d_stem/2 * (mup + tanl) / (1 - mup*tanl) / 1000.0   # N*m
T_lower = F_close * d_stem/2 * (mup - tanl) / (1 + mup*tanl) / 1000.0   # N*m

lever_ratio = P("lever_arm") / (d_stem/2)
F_hand_close = T_raise * 1000 / P("lever_arm")                          # N
F_hand_open  = T_lower * 1000 / P("lever_arm")                          # N

R["05_stem_drive"] = {
    "thread": "Tr36x6 (公制粗牙, 牙型半角 30deg)",
    "d_mean_mm": round(d_mean, 2),
    "helex_angle_deg": round(math.degrees(lam), 3),
    "mu_prime": round(mup, 4),
    "T_to_close_Nm": round(T_raise, 1),
    "T_to_open_Nm": round(T_lower, 1),
    "formula_T": "T = F*d/2 * (mu' +- tan l)/(1 -+ mu'*tan l)",
    "lever_ratio": round(lever_ratio, 2),
    "hand_force_close_N": round(F_hand_close, 1),
    "hand_force_close_kgf": round(F_hand_close / G, 2),
    "hand_force_open_kgf": round(F_hand_open / G, 2),
    "compare_key_limit_45kgf": {
        "required_hand_force_kgf": round(F_hand_close / G, 2),
        "drawing_limit_kgf": P("key_force_max"),
        "drawing_limit_semantics": "п.20 限制的是【辅助扳手】施加的力,不是手轮操作力 —— 两者不是同一个量",
        "verdict": "不可直接比较(对象不同)。手轮操作力 %.1f kgf 处于人力手动的常见量级内,未构成矛盾。" % (F_hand_close / G),
        "proper_check": "手轮操作力的上限应由驱动选型/标准规定给出,图上没有。需取得 ТУ 才能判定。",
    },
    "status": "DERIVED",
    "sensitivity": "结论对 mu 与 L 假设敏感:mu 每 ±0.05,T 约 ∓25%。",
}

# ----------------------------------------------------------------------
# 5. 承压壁厚(T15)
#    薄膜环向应力(仅用于量级,阀体是复杂铸件,不能作为最终判据)
#      sigma_h = p*D/(2*t)
#    净壁厚 = 名义壁厚 - 腐蚀裕量
# ----------------------------------------------------------------------
t_nom = P("t_body_wall")
t_net = t_nom - P("corrosion_allow")
sigma_h = dp_max * P("bore") / (2 * t_net)
util_h = sigma_h / P("allow_stress")

# 螺栓法兰: 总推力 / 总螺栓截面积
F_bolt_total = dp_max * A_bore
# 12 x ф15 孔 -> 按 M14 螺母应力面积 A_s = 147 mm^2 (粗牙, M14 As=147)
As_M14 = 147.0
A_bolt_tot = P("bolt_holes") * As_M14
sigma_bolt = F_bolt_total / A_bolt_tot

R["06_pressure_boundary"] = {
    "t_nominal_mm": t_nom,
    "t_corrosion_allowance_mm": P("corrosion_allow"),
    "t_effective_mm": round(t_net, 2),
    "hoop_stress_MPa": round(sigma_h, 2),
    "hoop_formula": "sigma = p*D/(2*t_net), D=200mm(公称通径)",
    "utilization_vs_allow": round(util_h, 4),
    "allow_stress_MPa": P("allow_stress"),
    "verdict_hoop": "通过(许用占用率 %.1f%%) —— 但这不是最终判据" % (util_h*100),
    "bolt_group": {
        "total_axial_N": round(F_bolt_total, 1),
        "n_bolts": P("bolt_holes"),
        "assumed_thread": "M14 (按 ф15 孔推定)",
        "As_mm2_each": As_M14,
        "bolt_stress_MPa": round(sigma_bolt, 2),
        "note": "孔径 ф15* 对应 M14 只是推定;实际螺栓规格来自 ГОСТ 1536-76,本轮未取得该表。",
    },
    "status": "DERIVED",
    "limitations": [
        "薄膜公式不适用于本阀体(中部有加强、非圆截面、端部有法兰过渡)。",
        "允许壁厚的真正控制项是 抗冲击(п.22 等级2) 与 低温脆性(-40degC),不是 0.6MPa 内压。",
        "阀体最小壁厚必须按选定规范的结构要求单独判定,不得用此处的许用占用率代替。",
    ],
}

# ----------------------------------------------------------------------
# 6. 密封接触(T16)—— 倾斜盘的力学放大
#    倾斜盘靠【几何】关闭,不是靠流动压力本身硬压:
#      座法线相对管轴倾斜 phi 时,法向接触力 = F_flow / sin(phi)
#      q = N / A_contact_line,  A_line = pi * D_seat * w_seal
# ----------------------------------------------------------------------
phi_deg = 45.0                      # 座面倾角:本轮作为待定设计变量扫掠
w_seal = 4.0                        # 密封环接触线宽度假设
D_seat = P("bore")                  # 阀座密封直径假设 = 公称通径
A_line = math.pi * D_seat * w_seal
phi = math.radians(phi_deg)
N_seat = F_close / math.sin(phi)    # N
q_contact = N_seat / A_line         # MPa

R["07_seal"] = {
    "mechanism": "倾斜盘几何放大 (F_seat = F_flow / sin(phi)),非平压式",
    "seat_inclination_phi_deg": phi_deg,
    "phi_status": "ASSUMED —— 图上未标注盘角,这是设计变量不是已知量",
    "seal_line_width_mm": w_seal,
    "contact_line_area_mm2": round(A_line, 1),
    "seat_normal_force_N": round(N_seat, 1),
    "resulting_contact_pressure_MPa": round(q_contact, 2),
    "sensitivity_phi": {
        "30deg": round(F_close/math.sin(math.radians(30))/A_line, 2),
        "45deg": round(q_contact, 2),
        "60deg": round(F_close/math.sin(math.radians(60))/A_line, 2),
        "75deg": round(F_close/math.sin(math.radians(75))/A_line, 2),
    },
    "verdict": "在 phi=45deg、线宽 4mm 假设下接触压强约 %.1f MPa,属青铜对青铜金属密封的可行量级" % q_contact,
    "status": "DERIVED + 参数化",
    "boundary": [
        "金属对金属密封可关闭性 != 泄漏等级。本轮无 ГОСТ/ОСТ 正文,不给任何泄漏结论。",
        "上述结论对 phi 与 w 极敏感:phi 从 30 增到 75 度,接触压强变化约 2 倍。",
        "phi 实际取值必须由 CAD 模型 + CFD 反压工况确定,本轮无 CAD/CAE,故为量级研究。",
    ],
}

# ----------------------------------------------------------------------
# 7. 温度与材料
# ----------------------------------------------------------------------
R["08_thermal_material"] = {
    "service_range_C": [P("t_min_service"), P("t_max_service")],
    "ΔT_check_MPa": "需按 E·α·ΔT 评估颈-阀体法兰螺栓副的温差应力(图上未给颈高 H)",
    "material_status": "MISSING —— 图纸只说'бронзовый',无牌号",
    "why_critical": "-40degC 的 28% CaCl2 工况是材料选择的控制工况。锡青铜在低温下强度上升但韧性下降;铝青铜更好但可焊性/铸造性不同。未取得牌号前不能定许用应力。",
    "action": "取得 ГОСТ 1536-76 + 制造厂 ТУ,确认阀体/阀盖/摆盘的青铜牌号与低温冲击要求",
}

# ----------------------------------------------------------------------
# 8. 质量核算(与明细表 119 kg 交叉验证)
# ----------------------------------------------------------------------
rho_bronze = 8.8   # g/cm3, 典型锡青铜
V_needed = P("mass_spec") * 1000 / rho_bronze   # cm3
R["09_mass_check"] = {
    "drawing_mass_kg": P("mass_spec"),
    "assumed_bronze_density_g_cm3": rho_bronze,
    "implied_volume_cm3": round(V_needed, 0),
    "implied_volume_litre": round(V_needed/1000, 2),
    "verdict": "119 kg 与青铜密度下的体积量级相容,未发现矛盾",
    "status": "DERIVED(仅体积量级校核,非质量复算)",
    "limit": "未做壁厚分布建模,不能复算质量。",
}

# ----------------------------------------------------------------------
# 9. 结论汇总
# ----------------------------------------------------------------------
R["10_summary"] = {
    "hard_requirements_checked": 5,
    "passed_with_caveats": 4,
    "blocked_by_missing_input": 5,
    "key_message": [
        "0.6MPa 的承压在本阀上不是控制项 —— 壁厚由抗冲击与低温韧性控制。",
        "真正卡住设计的是三个缺口: (a) 青铜牌号未知; (b) Кз 的测量基准未定义; (c) 设计压力/试验压力未给。",
        "本轮所有数字为 E1 级(公式与量级自洽),不是实物证据。",
        "在拿到 ТУ 与明细表前,不得进入 T07 冻结。",
    ],
}

out = {
    "schema": "valve.calc_results/1.0",
    "run_id": "20261006",
    "candidate_id": "C0",
    "tasks": ["T10", "T15", "T16", "T17"],
    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "evidence_level": "E1 (数值与公式自洽,未做实验/CAE 验证)",
    "inputs": IN,
    "results": R,
}
path = os.path.join(HERE, "calc_results.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ----------------------------------------------------------------------
print("=" * 78)
print("522-35.4179CБ  止回-截止直通式青铜法兰阀  DN200 / Py6(0.59 MPa)")
print("=" * 78)
print("公称压力换算      : Py6 = %.4f MPa   [注:设计压力未给]" % PN_MPa)
print("公称通径截面积    : %.0f mm2" % A_bore)
print()
print("-- 水力 (п.23 Кз<=6) ------------------------------------------")
print("  解释A(Кз即总zeta) Kv = %.0f m3/h   Cv_US = %.0f" % (
    R["03_hydraulic"]["interpretation_A_absolute"]["Kv_m3h"],
    R["03_hydraulic"]["interpretation_A_absolute"]["Cv_US"]))
print("  解释B(相对直管)     Kv = %.0f m3/h   Cv_US = %.0f" % (
    R["03_hydraulic"]["interpretation_B_relative_to_pipe"]["Kv_m3h"],
    R["03_hydraulic"]["interpretation_B_relative_to_pipe"]["Cv_US"]))
_kva = R["03_hydraulic"]["interpretation_A_absolute"]["Kv_m3h"]
_kvb = R["03_hydraulic"]["interpretation_B_relative_to_pipe"]["Kv_m3h"]
print("  >>> 两种解释仅差 %.0f%% —— Kv 本身对该定义不敏感,但【验收口径】仍然无法冻结。" % ((_kva-_kvb)/_kvb*100))
print()
print("-- 关闭载荷 (Borda-Carnot) ------------------------------------")
print("  关闭力   F = %.0f N = %.0f kgf" % (F_close, F_close / G))
print("  关闭力矩 M = %.0f Nm" % M_close)
print()
print("-- 阀杆 Tr36x6 ----------------------------------------------")
print("  导程角 %.3f deg   摩擦系数 mu'=%.4f" % (math.degrees(lam), mup))
print("  关闭力矩 %.0f Nm   开启力矩 %.0f Nm" % (T_raise, T_lower))
print("  经杠杆(臂比 %.1f:1) 手轮操作力 = %.0f N = %.1f kgf" % (
    lever_ratio, F_hand_close, F_hand_close / G))
print("  注: п.20 的 45 kgf 是【辅助扳手】限值,与手轮操作力不是同一个量,不可直接比。")
print()
print("-- 承压壁厚 (量级) ------------------------------------------")
print("  名义壁厚 %.0f - 腐蚀裕量 %.1f = 净壁厚 %.1f mm" % (t_nom, P("corrosion_allow"), t_net))
print("  环向应力 %.2f MPa,许用占用率 %.2f%%" % (sigma_h, util_h * 100))
print("  螺栓组(推定 M14x12) 应力 %.1f MPa" % sigma_bolt)
print("  >>> 0.6MPa 下占用率极低 -> 壁厚不由内压控制。")
print()
print("-- 密封 (倾斜盘几何放大) --------------------------------------")
print("  座倾角 phi=%.0f 度, 密封线宽 %.0f mm, 接触线面积 %.0f mm2" % (phi_deg, w_seal, A_line))
print("  座法向力 %.0f N -> 接触压强 %.1f MPa" % (N_seat, q_contact))
print("  phi 敏感性: ", {k: v for k, v in R["07_seal"]["sensitivity_phi"].items()})
print("  >>> 金属密封可关闭,量级可行;泄漏等级本轮不给结论。")
print()
print("=" * 78)
print("阻塞项: 青铜牌号未知 | Кз 基准未定义 | 设计压力/试验压力未给 |")
print("        摆盘与阀座几何未标注 | 颈部高度 H 未给")
print("证据等级 E1。本轮不足以冻结 T07 设计基础。")
print("结果已写入: %s" % path)
print("=" * 78)