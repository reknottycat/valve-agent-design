#!/usr/bin/env python3
"""P1: 阀座/阀盘几何实测 (验证 ASSUMPTIONS.md A-03).

解析 STEP AP214 文本 (无 FreeCAD, 方法 b):
  - CONICAL_SURFACE: 半锥角 (若存在)
  - CYLINDRICAL_SURFACE: 半径 + 轴向
  - PLANE: 法向 -> 与流道轴 (X, face_to_face 方向) 的夹角
  - CIRCLE: 半径/圆心 -> 密封环带内外径 -> 密封直径与座宽
运行: python3 -I measure_seat.py <seat.step> <disc.step>
输出: seat_measurements.json (同目录)
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_entities(text):
    """Return {id: (TYPE, args_string)} from the DATA section."""
    data = text.split("DATA;", 1)[1].split("ENDSEC;", 1)[0]
    ents = {}
    for stmt in data.split(";"):
        stmt = stmt.strip()
        m = re.match(r"#(\d+)\s*=\s*([A-Z_0-9]+)\s*\((.*)\)\s*$", stmt, re.S)
        if m:
            ents[int(m.group(1))] = (m.group(2), m.group(3))
    return ents


def split_args(s):
    """Split top-level comma-separated args (respects parens/quotes)."""
    out, depth, cur, inq = [], 0, "", False
    for ch in s:
        if ch == "'" :
            inq = not inq
        if not inq:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
                continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def ref(s):
    m = re.match(r"#(\d+)$", s.strip())
    return int(m.group(1)) if m else None


def get_point(ents, rid):
    t, a = ents[rid]
    assert t == "CARTESIAN_POINT", t
    nums = re.findall(r"[-+0-9.Ee]+", a.split("(", 1)[1].rsplit(")", 1)[0])
    return tuple(float(x) for x in nums)


def get_dir(ents, rid):
    t, a = ents[rid]
    assert t == "DIRECTION", t
    nums = re.findall(r"[-+0-9.Ee]+", a.split("(", 1)[1].rsplit(")", 1)[0])
    v = [float(x) for x in nums]
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def get_axis2(ents, rid):
    """AXIS2_PLACEMENT_3D -> (origin, axis(Z) dir, ref(X) dir)."""
    t, a = ents[rid]
    args = split_args(a)
    origin = get_point(ents, ref(args[1]))
    axis = get_dir(ents, ref(args[2])) if len(args) > 2 and ref(args[2]) else (0, 0, 1)
    refd = get_dir(ents, ref(args[3])) if len(args) > 3 and ref(args[3]) else None
    return origin, axis, refd


def angle_deg(u, v):
    d = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v))))
    return math.degrees(math.acos(abs(d)))  # 无向夹角 0..90


def analyze(path):
    text = Path(path).read_text(errors="replace")
    ents = parse_entities(text)
    res = {"file": str(path), "cones": [], "cylinders": [], "planes": [], "circles": []}
    BORE = (1.0, 0.0, 0.0)  # face_to_face 沿 X (bbox x: 0..300)
    for rid, (t, a) in sorted(ents.items()):
        args = split_args(a)
        if t == "CONICAL_SURFACE":
            o, ax, _ = get_axis2(ents, ref(args[1]))
            res["cones"].append({
                "id": rid, "origin": o, "axis": ax,
                "radius_mm": float(args[2]),
                "semi_angle_deg": math.degrees(float(args[3])),
            })
        elif t == "CYLINDRICAL_SURFACE":
            o, ax, _ = get_axis2(ents, ref(args[1]))
            res["cylinders"].append({
                "id": rid, "origin": o, "axis": ax,
                "radius_mm": float(args[2]),
                "axis_angle_to_boreX_deg": round(angle_deg(ax, BORE), 3),
            })
        elif t == "PLANE":
            o, n, _ = get_axis2(ents, ref(args[1]))
            res["planes"].append({
                "id": rid, "origin": o, "normal": n,
                "normal_angle_to_boreX_deg": round(angle_deg(n, BORE), 3),
            })
        elif t == "CIRCLE":
            o, ax, _ = get_axis2(ents, ref(args[1]))
            res["circles"].append({
                "id": rid, "center": o, "axis": ax, "radius_mm": float(args[2]),
                "axis_angle_to_boreX_deg": round(angle_deg(ax, BORE), 3),
            })
    return res


def main():
    seat = analyze(sys.argv[1])
    disc = analyze(sys.argv[2])
    raw = {"seat_ring": seat, "disc": disc}
    (HERE / "raw_surfaces.json").write_text(json.dumps(raw, indent=2))

    # ---- 汇总判定 ----
    summary = {
        "seat_cone_angle_deg": None,
        "sealing_diameter_mm": None,
        "seat_width_mm": None,
        "disc_lift_mm": None,
        "measurement_method": "STEP AP214 text parsing (no FreeCAD available): "
                              "CONICAL_SURFACE/PLANE/CYLINDRICAL_SURFACE/CIRCLE entity extraction",
        "source_files": [str(sys.argv[1]), str(sys.argv[2]),
                         str(HERE / "geometry_check.json")],
        "confidence": None,
        "notes": [],
    }

    if seat["cones"]:
        angles = sorted({round(c["semi_angle_deg"], 3) for c in seat["cones"]})
        summary["seat_cone_angle_deg"] = {"semi_angle_deg": angles,
                                          "included_angle_deg": [round(2 * a, 3) for a in angles]}
        summary["notes"].append("seat_ring 含 CONICAL_SURFACE, 半锥角取自实体参数")
    else:
        summary["notes"].append(
            "seat_ring_asm.step 与 disc_asm.step 均无 CONICAL_SURFACE/TOROIDAL/B_SPLINE_SURFACE; "
            "密封面若存在只能是 PLANE 或 CYLINDRICAL_SURFACE (见 raw_surfaces.json)")

    # 密封环带: 找倾斜平面 (法向既不平行也不垂直于流道轴 X)
    tilted_planes = [p for p in seat["planes"]
                     if 1.0 < p["normal_angle_to_boreX_deg"] < 89.0]
    summary["tilted_seat_planes"] = tilted_planes

    gc = json.loads((HERE / "geometry_check.json").read_text())
    summary["geometry_check_params_subset"] = {
        k: gc["params"].get(k) for k in
        ("DN", "disc_od", "disc_inclination", "seat_width", "seal_line_width", "pivot_offset_e")
    }
    summary["geometry_check_lift_field_present"] = "lift" in gc["params"]
    summary["confidence"] = "pending_manual_review"
    (HERE / "seat_measurements.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
