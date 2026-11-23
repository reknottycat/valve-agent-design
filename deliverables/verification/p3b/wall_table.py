#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3b 壁厚-压力表: 按 P0 公式核对 (python3 -I)
公式来源: /tmp/valve-phase2/p0/strength_check.py
  S = min(σb/3.5, σ0.2/1.5) * η_cast(0.8)
  t_req = P * D_i / (2S - P)
  P_allow = 2*S*t / (D_o - t),  D_o = D_i + 2t
  σ_hoop = P*(D_o-t)/(2t)
几何: D_i=200 mm (geometry_check.json bore), t_nom=12, t_actual_min=23.5
"""
import json, math

D_I = 200.0
T_NOM = 12.0
T_ACT = 23.5
PN = 0.6
P_TEST = 1.5 * PN  # 0.9 MPa
ETA = 0.8
NB, NY = 3.5, 1.5

def S(sb, s02):
    return min(sb / NB, s02 / NY) * ETA

def t_req(P, s):
    return P * D_I / (2.0 * s - P)

def case(t, s, P):
    Do = D_I + 2 * t
    return {
        "t": t, "Do": Do, "t_Do": t / Do, "thin": (t / Do) < 0.1,
        "P_allow": 2 * s * t / (Do - t),
        "sigma_at_P": P * (Do - t) / (2 * t),
    }

mats = {
    # B148 sand cast C95400 min via CDA (75 ksi / 30 ksi 0.5% EUL / 12%)
    "C95400_B148_sandcast_min": {"sb": 75 * 6.894757, "s02": 30 * 6.894757,
        "src": "CDA C95400 As Sand Cast M01, ASTM/ASME B148 (ksi*6.894757)"},
    # P0 baseline GOST typical (assumption A-01)
    "GOST_18175_typical_P0": {"sb": 550.0, "s02": 230.0,
        "src": "GOST 18175-78 handbook typical used in P0"},
}

out = {"inputs": {"D_i_mm": D_I, "t_nom_mm": T_NOM, "t_actual_min_mm": T_ACT,
                  "PN_MPa": PN, "P_test_MPa": P_TEST, "eta": ETA, "n_b": NB, "n_y": NY},
       "materials": {}, "pressure_rows": [], "corrosion_allowance_rows": []}

for name, m in mats.items():
    s = S(m["sb"], m["s02"])
    gov = "sigma_0.2/1.5" if m["s02"] / NY < m["sb"] / NB else "sigma_b/3.5"
    rec = {"sigma_b": round(m["sb"], 2), "sigma_0.2": round(m["s02"], 2),
           "S_MPa": round(s, 2), "governed_by": gov, "source": m["src"],
           "S_test_limit_MPa": round(0.9 * m["s02"] * ETA, 2),
           "t_req": {}}
    for P in (0.6, 0.9, 1.6):
        rec["t_req"][str(P)] = round(t_req(P, s), 3)
        for t, tag in ((T_NOM, "t_nominal"), (T_ACT, "t_actual_min")):
            c = case(t, s, P)
            out["pressure_rows"].append({
                "material": name, "P_MPa": P, "case": tag, **c,
                "P_allow": round(c["P_allow"], 3),
                "sigma_at_P": round(c["sigma_at_P"], 3),
                "t_Do": round(c["t_Do"], 4),
                "design_pass": c["P_allow"] >= P,
            })
    # hydro at t_nom
    c = case(T_NOM, s, P_TEST)
    rec["hydro_at_t_nom"] = {
        "sigma_MPa": round(c["sigma_at_P"], 3),
        "limit_MPa": rec["S_test_limit_MPa"],
        "pass": c["sigma_at_P"] <= rec["S_test_limit_MPa"],
    }
    out["materials"][name] = rec

# corrosion allowance rows: t_spec = t_req + c, compare to t_nom
s_b148 = S(mats["C95400_B148_sandcast_min"]["sb"], mats["C95400_B148_sandcast_min"]["s02"])
for c_allow in (0.0, 1.0, 2.0, 3.0):
    row = {"corrosion_allowance_mm": c_allow, "by_P": {}}
    for P in (0.6, 0.9, 1.6):
        tr = t_req(P, s_b148)
        t_min = tr + c_allow
        row["by_P"][str(P)] = {
            "t_pressure_req_mm": round(tr, 3),
            "t_min_spec_mm": round(t_min, 3),
            "t_nominal_ok": T_NOM >= t_min,
            "P_allow_at_t_nom": round(case(T_NOM, s_b148, 0.0)["P_allow"], 3) if False else round(2 * s_b148 * T_NOM / (D_I + 2 * T_NOM - T_NOM), 3),
        }
    out["corrosion_allowance_rows"].append(row)

print(json.dumps(out, ensure_ascii=False, indent=2))
open("/tmp/valve-phase2/p3b/wall_table.json", "w").write(json.dumps(out, ensure_ascii=False, indent=2))
