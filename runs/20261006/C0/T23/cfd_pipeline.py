#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
522-35.4179-C0  CFD 完整流水线
run 20261006 / candidate C0   任务 T23 / T25 / T28 / T30

CadQuery 建开启位流体域(含阀座环与开启位摆盘)
 -> Gmsh .geo 按包围盒打物理边界 -> MSH 4.1
 -> gmshToFoam -> checkMesh -> simpleFoam + kOmegaSST
 -> 面积平均法提取 Δp -> 多速度点扫掠 -> Kv/Cv 与 C02 曲线

踩过的坑(已固化,勿回退):
 1. 几何必须统一用【米】;STEP 不带单位,混入 mm 会与 OpenFOAM SI 制冲突。
 2. Gmsh 的 -clmax 要 %.4f;写 %.1f 会把 0.010 变成 0.0,网格退化。
 3. OpenFOAM 2506 的 gmshToFoam 只认 MSH 4.1,不能手写 MSH 2.2。
 4. 未命名的边界面会归入 defaultFaces —— BC 必须按【实际 patch 名】生成,
    写死 inlet/outlet/wall 会在 defaultFaces 上 FATAL。
 5. fvSolution 里必须保留 residualControl,否则 simpleFoam 不判收敛。
"""
import os, sys, math, json, subprocess, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = "/root/valve_cfd"
ENV  = "/usr/lib/openfoam/openfoam2506"
FOAMFILE = 'FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       %s;\n    object      %s;\n}\n\n'

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def w(path, cls, obj, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(FOAMFILE % (cls, obj)); f.write(body)

# ============================================================ 1. 几何(单位:米)
GEO = dict(r_bore=0.100, L=0.300, UP=0.600, DNC=0.600,
           seat_od=0.116, disc_od=0.240, disc_thk=0.014,
           neck_bore_r=0.022, r_hub=0.1235, seat_h=0.026)

def build_geometry():
    import cadquery as cq
    g = GEO
    dom = cq.Workplane("YZ", origin=(-g["UP"], 0, 0)).circle(g["r_bore"]).extrude(
        g["UP"] + g["L"] + g["DNC"])
    dom = dom.cut(cq.Workplane("YZ", origin=(g["L"]/2 - 0.013, 0, 0))
                  .circle(g["seat_od"]).extrude(g["seat_h"]))
    dom = dom.cut(cq.Workplane("XY", origin=(g["L"]/2, 0, -g["r_hub"]))
                  .circle(g["neck_bore_r"]).extrude(g["r_hub"] + 0.34))
    seat = (cq.Workplane("YZ", origin=(g["L"]/2 - 0.013, 0, 0))
            .circle(g["seat_od"]).extrude(g["seat_h"])
            .cut(cq.Workplane("YZ", origin=(g["L"]/2 - 0.014, 0, 0))
                 .circle(g["r_bore"]).extrude(g["seat_h"] + 0.002)))
    seat = seat.cut(cq.Workplane("XY", origin=(g["L"]/2, 0, -0.15))
                    .circle(g["neck_bore_r"]).extrude(0.30))
    dom = dom.cut(seat)
    disc = (cq.Workplane("YZ", origin=(g["L"]/2 - g["disc_thk"]/2, 0, 0))
            .circle(g["disc_od"]/2).extrude(g["disc_thk"]))
    dom = dom.cut(disc.rotate((g["L"]/2, 0, -(g["disc_od"]/2 - 0.030)), (0, 1, 0), 88))
    step = os.path.join(CASE, "fluid_open.step")
    dom.val().exportStep(step)
    vol = dom.val().Volume()
    nsurf = len(dom.faces().vals())
    print("  流体域体积 = %.6f m3   x 跨度 = %.3f m   边界面数 = %d"
          % (vol, g["UP"] + g["L"] + g["DNC"], nsurf))
    return step, vol, nsurf

# ============================================================ 2. 网格
GEO_TMPL = """// 自动生成 by cfd_pipeline.py
// 只命名 inlet/outlet;未命名面会被 gmshToFoam 归入 defaultFaces,
// 本算例的 BC 生成器把 defaultFaces 当壁面处理(见 ROLE 映射)。
SetFactory("OpenCASCADE");
Merge "%(step)s";
Physical Surface("inlet",  1) = { Surface In BoundingBox{%(xl1).4f, -0.5, -0.5, %(xl2).4f, 0.5, 0.5} };
Physical Surface("outlet", 2) = { Surface In BoundingBox{%(xr1).4f, -0.5, -0.5, %(xr2).4f, 0.5, 0.5} };
Physical Volume("fluid",    4) = { 1 };
"""

def gen_mesh(step, clmax, nsurf=None):
    geo = os.path.join(CASE, "fluid.geo")
    msh = os.path.join(CASE, "fluid.msh")
    # 域从 -UP 起算,右端是 L + DNC(不是 UP+L+DNC —— 这里错过一次)
    xmin, xmax = -GEO["UP"], GEO["L"] + GEO["DNC"]
    with open(geo, "w") as f:
        # 端盖面被 BoundingBox 整体包含才会命中;管壁跨越全长,因此无论盒多宽都不被包含。
        # 用"左半区/右半区"这种大范围盒是无歧义的。
        # 端盖面必须【被包含】在盒内,因此边界要略微跨过端面本身。
        # 管壁跨越全长,不会被任一半区盒整块包含,故不会误判。
        f.write(GEO_TMPL % dict(step=os.path.basename(step),
                                xl1=xmin-1.0, xl2=xmin+0.001,
                                xr1=xmax-0.001, xr2=xmax+1.0))
    _, out = sh('gmsh -3 "%s" -format msh4 -o "%s" -clmax %.4f -v 3 2>&1 | tail -12'
                % (geo, msh, clmax), cwd=CASE)
    for ln in out.splitlines():
        if "nodes" in ln and "elements" in ln:
            print("  " + ln.strip())
    err = [l for l in out.splitlines() if "Error" in l]
    if err:
        print("  gmsh 错误: " + err[0][:130])
        return None
    return msh

def retag_boundaries(src, dst):
    """解析 MSH 4.1,把边界面三角形按节点 x 极值改写物理标签为 1(inlet)/2(outlet)/3(wall)。

    MSH4.1 节点行: dim tag x y z
    MSH4.1 单元行: elmType numTags numNodes <tag1=physical> <tag2=elementary> entityDim entityTag elmTag <nodes...>
    """
    txt = open(src).read().splitlines()
    # --- 读节点 ---
    nodes = {}
    if "$Nodes" in txt:
        i = txt.index("$Nodes") + 1
        i += 1                                  # 跳过 "1 n n minTag maxTag"
        while txt[i].strip() != "$EndNodes":
            t = txt[i].split()
            if len(t) >= 5:
                nodes[int(t[1])] = (float(t[2]), float(t[3]), float(t[4]))
            i += 1
    if not nodes:
        print("  !! MSH4.1 节点解析失败")
        return None
    # --- 改写元素物理标签 ---
    ei = txt.index("$Elements") + 1
    nblocks = int(txt[ei]); j = ei + 1
    counts = {"inlet": 0, "outlet": 0, "wall": 0}
    xs = [p[0] for p in nodes.values()]
    xmin, xmax = min(xs), max(xs)
    tol = max(abs(xmax - xmin), 1.0) * 1e-6
    for _ in range(nblocks):
        hdr = txt[j].split(); j += 1
        nelem = int(hdr[1])
        for k in range(nelem):
            t = txt[j+k].split()
            if int(t[0]) == 2:                    # 三角形 = 边界面
                nn = int(t[2])
                cx = [nodes[int(x)][0] for x in t[3+nn:]]
                if max(cx) <= xmin + tol:
                    t[3], key = "1", "inlet"
                elif min(cx) >= xmax - tol:
                    t[3], key = "2", "outlet"
                else:
                    t[3], key = "3", "wall"
                counts[key] += 1
                txt[j+k] = " ".join(t)
        j += nelem
    open(dst, "w").write("\n".join(txt) + "\n")
    print("  x 范围 [%.3f, %.3f] m" % (xmin, xmax))
    print("  物理边界: inlet=%d  outlet=%d  wall=%d 面片"
          % (counts["inlet"], counts["outlet"], counts["wall"]))
    return dst

def read_patches():
    """解析 constant/polyMesh/boundary 中的 patch 名。
    实际格式是 name / { / type ... ; 的多行结构,不能靠固定行偏移,改用正则。"""
    import re
    p = os.path.join(CASE, "constant/polyMesh/boundary")
    if not os.path.exists(p):
        return []
    txt = open(p).read()
    return [m.group(1) for m in
            re.finditer(r"^\s{4}(\S+)\s*\n\s*\{\s*\n\s*type\s+\w+", txt, re.M)]

# ============================================================ 3. 算例
def write_case(v, patches):
    C = CASE
    w(f"{C}/system/controlDict", "dictionary", "controlDict", """application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 3000;
deltaT 1;
writeControl timeStep;
writeInterval 3000;
purgeWrite 0;
writeFormat ascii;
writeFormatOptions { precision 10; }
timeFormat general;
timePrecision 8;
functions
{
  pIn  { type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
         writeControl timeStep; writeInterval 3000;
         regionType patch; name inlet; operation areaAverage; fields (p); }
  pOut { type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
         writeControl timeStep; writeInterval 3000;
         regionType patch; name outlet; operation areaAverage; fields (p); }
}
""")
    w(f"{C}/system/fvSchemes", "dictionary", "fvSchemes", """ddtSchemes { default steady; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U)     bounded Gauss linearUpwind grad(U);
    div(phi,k)     bounded Gauss limitedLinear 1;
    div(phi,omega) bounded Gauss limitedLinear 1;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")
    w(f"{C}/system/fvSolution", "dictionary", "fvSolution", """solvers
{
  p     { solver GAMG; tolerance 1e-7; relTol 0.01; }
  U     { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0; }
  k     { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0; }
  omega { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0; }
}
SIMPLE
{
  nNonOrthogonalCorrectors 0;
  consistent no;
  residualControl { p 1e-6; U 1e-7; k 1e-7; omega 1e-7; }
}
relaxationFactors
{
  fields { p 0.3; }
  equations { U 0.7; k 0.7; omega 0.7; }
}
""")
    ROLE = {"inlet": "IN", "outlet": "OUT"}
    def blk(kind):
        out = ""
        for name in patches:
            r = ROLE.get(name, "WALL")
            if kind == "U":
                t, val = (("fixedValue", "uniform (%g 0 0)" % v) if r == "IN" else
                          (("zeroGradient", None) if r == "OUT" else ("noSlip", None)))
            elif kind == "p":
                t, val = (("zeroGradient", None) if r == "IN" else
                          (("fixedValue", "uniform 0") if r == "OUT" else ("zeroGradient", None)))
            elif kind == "k":
                t, val = (("fixedValue", "uniform 0.002") if r == "IN" else
                          (("zeroGradient", None) if r == "OUT" else ("kqRWallFunction", "uniform 0.002")))
            elif kind == "omega":
                t, val = (("fixedValue", "uniform 0.1") if r == "IN" else
                          (("zeroGradient", None) if r == "OUT" else ("omegaWallFunction", "uniform 0.1")))
            else:
                t, val = (("calculated", "uniform 0") if r in ("IN", "OUT")
                          else ("nutkWallFunction", "uniform 0"))
            out += "    %s\n    {\n        type %s;\n" % (name, t)
            if val:
                out += "        value %s;\n" % val
            out += "    }\n"
        return out
    w(f"{C}/0/U",     "volVectorField", "U",
      "dimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\nboundaryField\n{\n" + blk("U") + "}\n")
    w(f"{C}/0/p",     "volScalarField", "p",
      "dimensions [0 2 -2 0 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n" + blk("p") + "}\n")
    w(f"{C}/0/k",     "volScalarField", "k",
      "dimensions [0 2 -2 0 0 0 0];\ninternalField uniform 0.002;\nboundaryField\n{\n" + blk("k") + "}\n")
    w(f"{C}/0/omega", "volScalarField", "omega",
      "dimensions [0 0 -1 0 0 0 0];\ninternalField uniform 0.1;\nboundaryField\n{\n" + blk("omega") + "}\n")
    w(f"{C}/0/nut",   "volScalarField", "nut",
      "dimensions [0 2 -1 0 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n" + blk("nut") + "}\n")
    w(f"{C}/constant/transportProperties", "dictionary", "transportProperties", "nu 1e-6;\n")
    w(f"{C}/constant/momentumTransport", "dictionary", "momentumTransport",
      "simulationType RAS;\nRAS { model kOmegaSST; turbulence on; printCoeffs on; }\n")

# ============================================================ 4. 单点求解
def run_point(v, clmax, rebuild_mesh):
    C = CASE
    if rebuild_mesh:
        pm = os.path.join(C, "constant/polyMesh")
        if os.path.isdir(pm):
            shutil.rmtree(pm)
        step, _, ns = build_geometry()
        gen_mesh(step, clmax, ns)
    sh(". %s/etc/bashrc >/dev/null 2>&1 && gmshToFoam fluid.msh > log.gmshToFoam 2>&1" % ENV, cwd=C)
    sh(". %s/etc/bashrc >/dev/null 2>&1 && checkMesh > log.checkMesh 2>&1" % ENV, cwd=C)
    cm = open(f"{C}/log.checkMesh").read() if os.path.exists(f"{C}/log.checkMesh") else ""
    patches = read_patches()
    write_case(v, patches)
    sh(". %s/etc/bashrc >/dev/null 2>&1 && simpleFoam > log.simpleFoam 2>&1" % ENV, cwd=C)
    sf = open(f"{C}/log.simpleFoam").read() if os.path.exists(f"{C}/log.simpleFoam") else ""
    conv = "SIMPLE solution converged" in sf
    resid, cur = {}, ""
    for ln in sf.splitlines():
        if ln.startswith("Solving for"):
            cur = ln.split("Solving for ")[1].split(",")[0].strip()
        if "Final residual" in ln:
            resid[cur] = float(ln.split("Final residual = ")[1].split(",")[0])
    cont = [l for l in sf.splitlines() if "continuity errors" in l]
    dp = None
    if conv:
        sh(". %s/etc/bashrc >/dev/null 2>&1 && postProcess -func pIn -func pOut -time latest > log.pp 2>&1" % ENV, cwd=C)
        try:
            f = f"{C}/postProcessing/pIn/0/surfaceFieldValue.dat"
            g = f"{C}/postProcessing/pOut/0/surfaceFieldValue.dat"
            pi = float(open(f).read().strip().splitlines()[-1].split(":")[-1])
            po = float(open(g).read().strip().splitlines()[-1].split(":")[-1])
            dp = pi - po
        except Exception:
            dp = None
    info = {}
    for key in ("cells:", "faces:", "points:"):
        for ln in cm.splitlines():
            if key in ln:
                try: info[key.strip(":")] = int(ln.split(key)[1].strip().split()[0])
                except Exception: pass
    for key in ("Max aspect ratio", "Non-orthogonality"):
        for ln in cm.splitlines():
            if key.lower() in ln.lower(): info[key] = ln.strip()
    return dict(velocity=v, clmax_mm=clmax*1000, patches=patches,
                mesh_ok=("Mesh OK" in cm), converged=conv, dp_pa=dp,
                residuals=resid, mesh_info=info,
                continuity=cont[-1].strip() if cont else None,
                exec_time_s=None)

# ============================================================ 5. 曲线后处理
def to_kv(v, dp_pa, rho=998.0):
    if not dp_pa or dp_pa <= 0: return None
    A = math.pi * GEO["r_bore"]**2
    Q = A * v                                   # m3/s
    dp_bar = dp_pa / 1e5
    Kv = Q * 3600.0 * math.sqrt(rho / 998.0 / dp_bar)
    return dict(Q_m3h=round(Q*3600, 1), dp_bar=round(dp_bar, 5),
                Kv=round(Kv, 1), Cv_US=round(Kv*1.156, 1))

# ============================================================ main
if __name__ == "__main__":
    print("=" * 74)
    print("522-35.4179-C0  CFD  (OpenFOAM 2506 / Gmsh 4.12.1 / kOmegaSST)")
    print("=" * 74)
    os.makedirs(CASE, exist_ok=True)
    print("[1] 开启位流体域")
    step, _, ns = build_geometry()
    print("[2] 网格 (clmax=10mm)")
    gen_mesh(step, 0.010, ns)
    print("[3] 代表工况 (v=3 m/s) —— 先打通链条,不直接铺开")
    r0 = run_point(3.0, 0.010, rebuild_mesh=False)
    print("    patches   : %s" % r0["patches"])
    print("    mesh_ok   : %s" % r0["mesh_ok"])
    print("    converged : %s" % r0["converged"])
    print("    dp        : %s Pa" % r0["dp_pa"])
    print("    mesh      : %s" % r0["mesh_info"])
    if not r0["converged"]:
        print("\n!! 未收敛 -> 不铺开全曲线。先定位数值问题。")
        sys.exit(2)

    print("[4] 速度点扫掠 (C02 流量-压降曲线)")
    runs = [r0]
    for v in (1.0, 2.0, 4.0, 5.0):
        r = run_point(v, 0.010, rebuild_mesh=False)
        runs.append(r)
        kv = to_kv(v, r["dp_pa"])
        print("    v=%.1f  dp=%8.1f Pa  conv=%s  %s"
              % (v, r["dp_pa"] or -1, r["converged"],
                 ("Kv=%.0f Cv=%.0f" % (kv["Kv"], kv["Cv_US"])) if kv else "Kv=n/a"))
    print("[5] 网格加密敏感性 (v=3 m/s)")
    for cl in (0.016, 0.006):
        r = run_point(3.0, cl, rebuild_mesh=True)
        runs.append(r)
        print("    clmax=%4.1fmm cells=%-9s dp=%s Pa conv=%s"
              % (cl*1000, r["mesh_info"].get("cells"), r["dp_pa"], r["converged"]))

    out = os.path.join(HERE, "cfd_results.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"schema": "valve.cfd_results/1.0",
                   "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "solver": "OpenFOAM 2506 simpleFoam + kOmegaSST",
                   "mesh": "Gmsh 4.12.1 tetrahedral, MSH 4.1",
                   "medium": "water, nu=1e-6 m2/s, rho=998 kg/m3 (20C)",
                   "geometry": "full-open passage incl. seat ring + tilted disc",
                   "coefficient_def": "Kv = Q[m3/h]*sqrt(SG/dP[bar]); Cv_US = 1.156*Kv",
                   "runs": runs,
                   "kv_table": [{"velocity": r["velocity"], **(to_kv(r["velocity"], r["dp_pa"]) or {})}
                                for r in runs if r["dp_pa"]]}, fh,
                  ensure_ascii=False, indent=2)
    print("\n结果已写入 %s" % out)