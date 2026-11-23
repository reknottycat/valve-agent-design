#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 强度校核: 522-35.4179СБ DN200 PN6 青铜截止止回阀 阀体圆筒壳体
运行: python3 -I /tmp/valve-phase2/p0/strength_check.py
输入: 同目录 geometry_check.json (gh api 取自 reknottycat/valve-agent-design
      runs/20261006/C0/T12/out/geometry_check.json @ consolidated-main)
输出: results.json, strength_report.md (同目录)

公式(薄壁圆筒, 外径形式): P_allow = 2*S*t / (D_o - t), 适用 t/D_o < 0.1
许用应力: S = min(sigma_b/3.5, sigma_0.2/1.5) * eta_cast
材料假设 A-01: БрА10Ж3Мц2 铝青铜铸件, ГОСТ 18175-78 典型值
  sigma_b = 550 MPa, sigma_0.2 = 230 MPa, 铸件系数 eta_cast = 0.8
设计压力假设 A-02: 0.9 MPa (= 1.5 x PN6, 兼作水压试验压力校核)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------- 输入 ----------
geo = json.loads((HERE / "geometry_check.json").read_text(encoding="utf-8"))
D_i = float(geo["params"]["bore"])                      # 内径 200 mm
t_nom = float(geo["params"]["body_wall"])               # 名义壁厚 12 mm (CAD 参数)
t_min = float(geo["checks"]["wall_thickness"]["actual_min"])  # 模型实测最小壁厚 23.5 mm
hub_od = float(geo["params"]["hub_od"])                 # 247 mm, 用于自洽性交叉检查

PN = 0.6            # MPa, PN6
P_design = 0.9      # MPa, A-02 假设设计压力 = 1.5 x PN6
P_test = 1.5 * PN   # MPa, 水压试验压力

sigma_b = 550.0     # MPa, ГОСТ 18175-78 典型值(假设, 待材质证书确认)
sigma_02 = 230.0    # MPa
eta_cast = 0.8      # 铸件系数
n_b, n_y = 3.5, 1.5 # 安全系数: 抗拉/屈服

S = min(sigma_b / n_b, sigma_02 / n_y) * eta_cast
S_test_limit = 0.9 * sigma_02 * eta_cast  # 水压试验应力限值(保守取 0.9*σ0.2*铸件系数)


def shell_case(name, t, source):
    D_o = D_i + 2.0 * t
    ratio = t / D_o
    P_allow = 2.0 * S * t / (D_o - t)
    sigma_at_design = P_design * (D_o - t) / (2.0 * t)
    sigma_at_test = P_test * (D_o - t) / (2.0 * t)
    return {
        "case": name,
        "t_mm": t,
        "t_source": source,
        "D_o_mm": D_o,
        "t_over_Do": round(ratio, 4),
        "thin_wall_valid": ratio < 0.1,
        "P_allow_MPa": round(P_allow, 2),
        "margin_vs_0.9MPa": round(P_allow / P_design, 1),
        "margin_vs_0_9MPa": round(P_allow / P_design, 1),
        "sigma_hoop_at_0.9MPa": round(sigma_at_design, 2),
        "sigma_hoop_at_test_0.9MPa": round(sigma_at_test, 2),
        "sigma_hoop_at_test_0_9MPa": round(sigma_at_test, 2),
        "test_stress_limit_MPa": round(S_test_limit, 1),
        "hydro_test_pass": sigma_at_test <= S_test_limit,
        "design_pass": P_allow >= P_design,
    }


cases = [
    shell_case("nominal(保守设计基准)", t_nom, "geometry_check.json params.body_wall (CAD 名义参数)"),
    shell_case("actual_min(模型实测)", t_min, "geometry_check.json checks.wall_thickness.actual_min"),
    shell_case("sensitivity_low", 10.0, "DN200 PN6 青铜阀典型壁厚区间下限(估算, 仅敏感性分析)"),
    shell_case("sensitivity_high", 14.0, "典型壁厚区间上限(估算, 仅敏感性分析)"),
]

# 0.9 MPa 下所需最小壁厚 (由 P = 2St/(D_i+t) 反解)
t_req = P_design * D_i / (2.0 * S - P_design)

base = cases[0]
if base["design_pass"] and base["thin_wall_valid"] and base["hydro_test_pass"]:
    verdict = "RELEASE_HOLD_CONDITIONAL"
    verdict_zh = ("A-02 建议解除 HOLD(有条件): 按 CAD 名义壁厚 12 mm 计算, "
                  "P_allow = %.2f MPa >> 0.9 MPa, 水压试验校核通过。"
                  "条件: 结论依赖 A-01 材料假设与 CAD 模型壁厚, 需制造图纸与材质证书最终确认。"
                  % base["P_allow_MPa"])
elif not base["design_pass"]:
    verdict = "DERATE_OR_HOLD"
    verdict_zh = "P_allow < 0.9 MPa: 需降压或维持 HOLD 并复核壁厚。"
else:
    verdict = "HOLD"
    verdict_zh = "数据不足或公式适用性不满足, 维持 HOLD。"

results = {
    "inputs": {
        "D_i_mm": D_i, "t_nom_mm": t_nom, "t_actual_min_mm": t_min,
        "hub_od_mm": hub_od,
        "hub_od_consistency": abs(hub_od - (D_i + 2 * t_min)) < 0.5,
        "PN_MPa": PN, "P_design_MPa": P_design, "P_test_MPa": P_test,
        "sigma_b_MPa": sigma_b, "sigma_0.2_MPa": sigma_02,
        "eta_cast": eta_cast, "n_b": n_b, "n_y": n_y,
    },
    "S_allow_MPa": round(S, 2),
    "S_governed_by": "sigma_0.2/1.5" if sigma_02 / n_y < sigma_b / n_b else "sigma_b/3.5",
    "t_required_at_0.9MPa_mm": round(t_req, 3),
    "cases": cases,
    "verdict": verdict,
    "verdict_zh": verdict_zh,
}
(HERE / "results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- 报告 ----------
rows = "\n".join(
    "| {case} | {t_mm:g} | {D_o_mm:g} | {t_over_Do:.4f} | {thin_wall} | "
    "{P_allow_MPa:.2f} | {margin_vs_0_9MPa:.1f}x | {sigma_hoop_at_test_0_9MPa:.2f} | {hydro} |".format(
        thin_wall="是" if c["thin_wall_valid"] else "否",
        hydro="通过" if c["hydro_test_pass"] else "不通过", **c)
    for c in cases)

report = f"""# P0 强度校核报告 — 522-35.4179СБ DN200 PN6 青铜截止止回阀 阀体

日期: 2026-11-23 | 计算脚本: strength_check.py (python3 -I 运行, 可复现)
数据来源: reknottycat/valve-agent-design @ consolidated-main,
runs/20261006/C0/T12/out/geometry_check.json (gh api 单文件读取, 未 clone 仓库)

## 1. 结论

**{verdict_zh}**

- 许用应力 S = {S:.2f} MPa (由 {results['S_governed_by']} 控制)
- 保守基准 (名义壁厚 {t_nom:g} mm): **P_allow = {base['P_allow_MPa']:.2f} MPa**, 为 0.9 MPa 假设的 {base['margin_vs_0.9MPa']:.1f} 倍
- 0.9 MPa 下理论所需最小壁厚仅 **{t_req:.2f} mm** (不含腐蚀/铸造裕量), 名义 12 mm 远超需求
- 水压试验 1.5×PN6 = 0.9 MPa: 试验环向应力 {base['sigma_hoop_at_test_0.9MPa']:.2f} MPa << 限值 {S_test_limit:.1f} MPa, **通过**
- 即使取典型壁厚估算区间下限 10 mm (敏感性分析), P_allow = {cases[2]['P_allow_MPa']:.2f} MPa, 结论不变

## 2. 计算方法

薄壁圆筒外径形式: **P_allow = 2·S·t / (D_o − t)**, 其中 D_o = D_i + 2t, D_i = {D_i:g} mm (bore)。
适用范围 t/D_o < 0.1, 各工况校验见下表。
反解所需壁厚: t_req = P·D_i / (2S − P)。
水压试验校核: σ_test = P_test·(D_o − t)/(2t) ≤ 0.9·σ0.2·η_cast = {S_test_limit:.1f} MPa (保守限值)。

## 3. 许用应力取值依据

| 参数 | 取值 | 依据 |
|---|---|---|
| σb | 550 MPa | БрА10Ж3Мц2, ГОСТ 18175-78 典型值 (**假设, 待材质证书确认, 依赖 A-01**) |
| σ0.2 | 230 MPa | 同上 |
| 安全系数 n_b / n_y | 3.5 / 1.5 | 常温静载常规取值 (抗拉/屈服) |
| 铸件系数 η_cast | 0.8 | 砂型铸造青铜件常规取值 |
| S | min(550/3.5, 230/1.5)×0.8 = **{S:.2f} MPa** | 屈服准则控制 |

## 4. 计算结果

| 工况 | t (mm) | D_o (mm) | t/D_o | 薄壁适用 | P_allow (MPa) | 对 0.9 MPa 裕度 | 试验应力 (MPa) | 水压校核 |
|---|---|---|---|---|---|---|---|---|
{rows}

## 5. 假设与数据来源清单 (全部显式列出)

1. **壁厚来源**: 非典型值估算 — 取自 CAD 模型 geometry_check.json:
   名义 params.body_wall = {t_nom:g} mm (保守设计基准);
   实测最小 checks.wall_thickness.actual_min = {t_min:g} mm。
   自洽性: D_i + 2×{t_min:g} = {D_i + 2 * t_min:g} mm = params.hub_od ({hub_od:g} mm), 交叉验证一致;
   step_roundtrip 体积相对误差 0, 几何数据与 STEP 模型一致, 故未另行下载 STEP。
   **注意: 壁厚为 CAD 模型数据, 未经制造图纸确认** (原 geometry_check 对壁厚仅给
   "通过(量级)" 判定, 且 GA 带 * 尺寸为参考值)。10/14 mm 两行仅为敏感性分析用的估算区间。
2. **材料 (A-01, 仍为假设)**: БрА10Ж3Мц2 铝青铜铸件, σb/σ0.2 取 ГОСТ 18175-78 典型值,
   未核对材质证书; 若实际为其他牌号需重算。
3. **温度**: 假设常温 (≤50 °C, 海水/淡水工况), 未做高温折减。
4. **载荷**: 仅内压静载; 未计入管道附加载荷、水锤、螺栓预紧、法兰/阀盖/阀瓣弯曲应力。
5. **腐蚀/铸造裕量**: 未从壁厚中扣除; 因 t_req ≈ {t_req:.2f} mm, 即使扣 3 mm 裕量结论仍成立。
6. **铸件系数 0.8**: 假设常规砂型铸造质量, 无损检测等级未知。
7. **范围限制**: 本校核仅覆盖阀体圆筒壳体段; 法兰 (t=15 mm)、阀盖 (t=22 mm)、
   阀瓣、阀杆强度不在本 P0 范围内, 需另行校核。

## 6. A-02 处置建议

**建议: 解除 HOLD (有条件)** — 设计压力 0.9 MPa 相对壳体承压能力裕度约 {base['margin_vs_0.9MPa']:.0f} 倍,
即使壁厚按估算下限 10 mm 或扣除 3 mm 裕量, 裕度仍 >10 倍, 结论对壁厚不确定性鲁棒。
解除条件 (转入后续任务跟踪, 不阻塞 A-02):
- 制造图纸确认名义壁厚 ≥12 mm (当前为 CAD 模型数据);
- A-01 材质证书确认 БрА10Ж3Мц2 及力学性能;
- 法兰/阀盖等其余承压件校核 (P0 范围外)。

## 7. 产出文件

- /tmp/valve-phase2/p0/geometry_check.json (输入, gh api 获取)
- /tmp/valve-phase2/p0/strength_check.py (可复现计算脚本)
- /tmp/valve-phase2/p0/results.json (机器可读结果)
- /tmp/valve-phase2/p0/strength_report.md (本报告, 由脚本生成)
"""
(HERE / "strength_report.md").write_text(report, encoding="utf-8")

print(json.dumps(results, ensure_ascii=False, indent=2))
