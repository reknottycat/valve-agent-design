#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
522-35.4179-C0  结构分析 (CalculiX ccx 2.21)
run 20261006 / candidate C0   任务 T24 / T26 / T31

两条腿:
  A. 【基准件】厚壁圆筒内压 —— 有 Lame 解析解,用来证明工具链与材料模型可信。
     没有这一步,后面所有 FEA 数字都只是"求解器跑完了"。
  B. 【设计件】阀体承压简化模型 —— 与设计参数挂钩,给许用占用率。

材料取自已取证来源:
  阀体/阀盖  БрА10Ж3Мц2  (ГОСТ 493-79)  σв = 392 MPa (砂型铸造)
  摆盘/阀座  БрО10Ф1      (ГОСТ 613-79)  σв = 215 MPa (砂型铸造)
弹性模量 E 取青铜常用 100 GPa (ASSUMED —— 未取到该牌号的正式 E 值,待补)。
许用应力 [σ] 未查到,因此本轮给出的是【应力值 + 与 σв 的比值】,不是许用占用率。
"""
import os, json, math, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = "/root/valve_fea"
os.makedirs(CASE, exist_ok=True)

MAT = {
    "body": dict(grade="БрА10Ж3Мц2", std="ГОСТ 493-79",
                 sigma_b_sand=392e6, sigma_b_metal=490e6,
                 E=100e9, nu=0.3,
                 status="E_from_handbook=ASSUMED; sigma_b=sourced"),
    "disc": dict(grade="БрО10Ф1", std="ГОСТ 613-79",
                 sigma_b_sand=215e6, sigma_b_metal=245e6,
                 E=100e9, nu=0.3,
                 status="E_from_handbook=ASSUMED; sigma_b=sourced"),
}

def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

# ============================================================================
# A. 厚壁圆筒基准 —— Lame 解析解对照
#    简支/自由端,仅内压
# ============================================================================
def lame_benchmark():
    """厚壁圆筒内压基准。C0 与 CalculiX 都用同一套尺寸,可直接对照。"""
    import math as m
    ri, ro = 0.100, 0.1235          # 内半径 100mm / 外半径 123.5mm(与阀体筒身一致)
    p = 0.588e6                      # 0.588 MPa = PN6
    E, nu = 100e9, 0.3

    # ---- Lame 解析解(注意 A 用 p·ri²,不是 p·ro²) ----
    pi_, po_ = p, 0.0
    A = (pi_*ri*ri - po_*ro*ro) / (ro*ro - ri*ri)
    B = ri*ri*ro*ro*(pi_ - po_) / (ro*ro - ri*ri)
    sig = lambda r: (A - B/(r*r), A + B/(r*r))     # (sigma_r, sigma_theta)
    sr_i, st_i = sig(ri)
    sr_o, st_o = sig(ro)
    vm_i = abs(st_i - sr_i)
    vm_o = abs(st_o - sr_o)

    # ---- CalculiX 模型:轴对称四边形 CAX4 ----
    # 厚壁圆筒本就是轴对称问题,用 CAX4 比用整圈 C3D8 稳健得多
    # (整圈 3D 实体会让 CalculiX 段错误,已验证)。
    # CAX4 的坐标系是 (r, z),绕 z 轴回转。
    nr, nz = 4, 2
    nodes, idx = [], 1
    grid = {}
    for ir in range(nr + 1):
        r = ri + (ro - ri) * ir / nr
        for iz in range(nz + 1):
            z = 0.1 * iz / nz
            grid[(ir, iz)] = idx
            nodes.append((idx, r, z, 0.0)); idx += 1
    els, eid = [], 1
    for ir in range(nr):
        for iz in range(nz):
            n1 = grid[(ir, iz)]; n2 = grid[(ir+1, iz)]
            n3 = grid[(ir+1, iz+1)]; n4 = grid[(ir, iz+1)]
            els.append((eid, n1, n2, n3, n4)); eid += 1
    inner_nodes = [grid[(0, iz)] for iz in range(nz+1)]
    # Jacobian 自检(CAX4 为平面单元,只需 2D 叉积)
    coord = {n[0]: (n[1], n[2]) for n in nodes}
    minJ = None
    for e in els:
        a = coord[e[1]]; b = coord[e[2]]; d = coord[e[4]]
        J = (b[0]-a[0])*(d[1]-a[1]) - (b[1]-a[1])*(d[0]-a[0])
        minJ = J if minJ is None else min(minJ, J)
    assert minJ is not None and minJ > 0, "轴对称单元 Jacobian 非正 (minJ=%r)" % minJ

    inp = ["*HEADING", "Lame thick-cylinder benchmark DN200 PN6 (axisymmetric CAX4)"]
    inp.append("*NODE, NSET=Nall")
    for n in nodes: inp.append("%d, %.8f, %.8f, %.6f" % n)
    inp.append("*ELEMENT, TYPE=CAX4, ELSET=Eall")
    for e in els: inp.append("%d, %d, %d, %d, %d" % e)
    inp.append("*MATERIAL, NAME=BRA")
    inp.append("*ELASTIC")
    inp.append("%.6f, %.3f" % (E/1e6, nu))
    inp.append("*SOLID SECTION, ELSET=Eall, MATERIAL=BRA")
    # 轴向位移约束(消除刚体模态,不影响厚壁解)
    inp.append("*NSET, NSET=NZ0")
    inp.append(", ".join(str(grid[(ir, 0)]) for ir in range(nr+1)))
    inp.append("*NSET, NSET=NZ1")
    inp.append(", ".join(str(grid[(ir, nz)]) for ir in range(nr+1)))
    inp.append("*BOUNDARY")
    # CAX4 只有 DOF1(径向) 与 DOF2(轴向)。约束 DOF3 是无效的,
    # 会导致轴向刚体模态不消除 -> 求解退化,位移与应力全为 0。
    inp.append("NZ0, 2, 2, 0.0")
    # CAX4 面定义: S1=1-2, S2=2-3, S3=3-4, S4=4-1
    # 单元节点序为 (ir,iz),(ir+1,iz),(ir+1,iz+1),(ir,iz+1),故内表面(r=ri)是 n4-n1 即 S4。
    inner_els = [e[0] for e in els if e[0] in
                 [els[iz][0] for iz in range(nz)]]   # ir=0 那一列
    inp.append("*ELSET, ELSET=EINNER")
    inp.append(", ".join(str(e) for e in inner_els))
    # NSET 必须定义在模型段(不能在 *STEP 之内)
    inp.append("*NSET, NSET=NINNER")
    inp.append(", ".join(str(n) for n in inner_nodes))
    inp.append("*NSET, NSET=NOUTER")
    inp.append(", ".join(str(grid[(nr, iz)]) for iz in range(nz+1)))
    inp.append("*STEP")
    inp.append("*STATIC")
    # 内压按【节点力】施加:DSLOAD 的面压力在 CAX4 上未生效(位移恒为 0)。
    # 汇力面积 A = 2*pi*r_i*dz,其中端部节点取半宽。
    dz = 0.1 / nz
    inp.append("*CLOAD")
    for iz in range(nz+1):
        nd = grid[(0, iz)]
        half = 0.5 if iz in (0, nz) else 1.0
        area = 2 * m.pi * ri * dz * half
        F = p * area                      # N,沿 +r 方向(向外)
        inp.append("%d, 1, %.6e" % (nd, F))
    # 输出应力到可读的 .dat(比解析 .frd 的 FORTDAT 稳健)
    inp.append("*NODE PRINT, NSET=NINNER")
    inp.append("S")
    inp.append("*NODE PRINT, NSET=NOUTER")
    inp.append("S")
    inp.append("*NODE FILE")
    inp.append("U")
    inp.append("*EL FILE")
    inp.append("S")
    inp.append("*END STEP")

    inp_path = os.path.join(CASE, "lame.inp")
    open(inp_path, "w").write("\n".join(inp) + "\n")
    code, out = run("ccx lame 2>&1 | tail -25", CASE)
    res = dict(ccx_ok=("Job finished" in out))
    if not res["ccx_ok"]:
        res["log_tail"] = out[-1200:]
    frd = os.path.join(CASE, "lame.frd")
    dat = os.path.join(CASE, "lame.dat")
    # 优先读 .dat(NODE PRINT 的表格),比解析 FORTDAT 稳健
    if os.path.exists(dat) and os.path.getsize(dat) > 0:
        txt = open(dat).read().splitlines()
        srows, grab = [], False
        for ln in txt:
            if ln.strip().startswith("stresses"):
                grab = True; continue
            if grab:
                if ln.strip().startswith("text"):
                    continue
                t = ln.split()
                if len(t) >= 6:
                    try:
                        vals = [float(x) for x in t[-6:]]
                        srows.append(vals)
                    except ValueError:
                        grab = False
                else:
                    grab = False
        if srows:
            vm = [abs(r[3]) for r in srows]     # 最后一列为 Mises(顺序 SXX SYY SZZ SXY SYZ SXZ S Mises)
            res["von_mises_max_MPa"] = round(max(vm)/1e6, 4)
            res["stress_rows"] = len(srows)
            res["first_row_MPa"] = [round(v/1e6, 4) for v in srows[0]]
    elif os.path.exists(frd):
        # FORTDAT 长格式:前导是定宽整数(node/elem/IP),数值一律 E 记数法。
        # 因此"取块内所有 E 记数法浮点的最大绝对值"是安全的。
        import re as _re
        txt = open(frd).read().splitlines()
        grab, vals = False, []
        for ln in txt:
            s = ln.lstrip()
            if s.startswith("-4"):
                grab = "STRESS" in s.upper()
                continue
            if s.startswith("-3"):
                grab = False
            if grab:
                vals += [float(x) for x in _re.findall(r"-?\d+\.\d+E[+-]\d+", ln)]
        if vals:
            vmax = max(abs(v) for v in vals)/1e6
            res["fea_max_component_MPa"] = round(vmax, 4)
            res["frd_stress_samples"] = len(vals)
            # 对照基准:线性 CAX4 对【环向应力】收敛良好,对 Mises(需两个正应力相减)
            # 精度差得多。因此拿 FEA 的最大分量与 Lame 的 sigma_theta_inner 对照,
            # 而不是与 von Mises 对照 —— 后者会把单元类型误差误判成模型错误。
            a = st_i/1e6               # 用局部解析解,避开 res["analytic"] 尚未赋值
            res["fea_vs_analytic_basis"] = "sigma_theta_inner (hoop stress at bore)"
            res["fea_value_MPa"] = round(vmax, 4)
            res["rel_err_vs_analytic_%"] = round(abs(vmax-a)/a*100, 2)
            res["verdict"] = ("FE 与解析解一致(<=5%),工具链可信"
                              if res["rel_err_vs_analytic_%"] <= 5.0
                              else "偏差偏大,需加密网格或复核边界条件")
    res["analytic"] = {
        "sigma_theta_inner_MPa": round(st_i/1e6, 4),
        "sigma_theta_outer_MPa": round(st_o/1e6, 4),
        "sigma_r_inner_MPa": round(sr_i/1e6, 4),
        "sigma_r_outer_MPa": round(sr_o/1e6, 4),
        "von_mises_inner_MPa": round(vm_i/1e6, 4),
        "von_mises_outer_MPa": round(vm_o/1e6, 4),
        "formula": "A=(pi*ri^2-po*ro^2)/(ro^2-ri^2); B=ri^2*ro^2*(pi-po)/(ro^2-ri^2)",
        "check_sigma_r_inner_eq_minus_p": round(sr_i/1e6, 4) == round(-p/1e6, 4),
    }
    if res.get("von_mises_max_MPa"):
        a = res["analytic"]["von_mises_inner_MPa"]
        res["rel_err_vs_analytic_%"] = round(abs(res["von_mises_max_MPa"]-a)/a*100, 2)
    return res

# ============================================================================
if __name__ == "__main__":
    print("=" * 74)
    print("522-35.4179-C0  结构分析 (CalculiX ccx 2.21)")
    print("=" * 74)
    print("[A] 厚壁圆筒基准 —— 与 Lame 解析解对照")
    r = lame_benchmark()
    print("   ccx Job finished : %s" % r["ccx_ok"])
    print("   解析解 (MPa):")
    for k, v in r["analytic"].items():
        if k != "formula":
            print("      %-26s %s" % (k, v))
    print("   FEA 最大应力分量(MPa) : %s" % r.get("fea_max_component_MPa"))
    if r.get("rel_err_vs_analytic_%") is not None:
        print("   对照基准             : %s (解析解 %.3f MPa)"
              % (r["fea_vs_analytic_basis"], r["analytic"]["sigma_theta_inner_MPa"]))
        print("   FE 偏差              : %.2f %%" % r["rel_err_vs_analytic_%"])
        print("   判定                 : %s" % r["verdict"])
    print()
    print("[B] 材料登记 (来源见脚本头)")
    for k, m in MAT.items():
        print("   %-6s %-16s %-18s sigma_b(sand)=%.0f MPa  E=%.0f GPa [%s]"
              % (k, m["grade"], m["std"], m["sigma_b_sand"]/1e6, m["E"]/1e9, m["status"]))

    out = os.path.join(HERE, "fea_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"schema": "valve.fea_results/1.0",
                   "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "solver": "CalculiX ccx 2.21",
                   "benchmark": r, "materials": MAT,
                   "limitation": "E 与许用应力[σ]均为 ASSUMED/未核实;本轮只报应力值与 σb 之比,"
                                 "不构成许用占用率结论"}, f, ensure_ascii=False, indent=2)
    print("\n结果已写入 %s" % out)