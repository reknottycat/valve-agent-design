"""DIAGNOSTIC ONLY: no solver code; not a validated valve geometry."""
import os
CASE = None
GEO = dict(r_bore=0.1, L=0.3, UP=0.6, DNC=0.6, seat_od=0.116, disc_od=0.24, disc_thk=0.014, neck_bore_r=0.022, r_hub=0.1235, seat_h=0.026)

def build_geometry():
    import cadquery as cq
    g = GEO
    dom = cq.Workplane('YZ', origin=(-g['UP'], 0, 0)).circle(g['r_bore']).extrude(g['UP'] + g['L'] + g['DNC'])
    dom = dom.cut(cq.Workplane('XY', origin=(g['L'] / 2, 0, -g['r_hub'])).circle(g['neck_bore_r']).extrude(g['r_hub'] + 0.34))
    seat = cq.Workplane('YZ', origin=(g['L'] / 2 - 0.013, 0, 0)).circle(g['seat_od']).extrude(g['seat_h']).cut(cq.Workplane('YZ', origin=(g['L'] / 2 - 0.014, 0, 0)).circle(g['r_bore']).extrude(g['seat_h'] + 0.002))
    seat = seat.cut(cq.Workplane('XY', origin=(g['L'] / 2, 0, -0.15)).circle(g['neck_bore_r']).extrude(0.3))
    dom = dom.cut(seat)
    disc = cq.Workplane('YZ', origin=(g['L'] / 2 - g['disc_thk'] / 2, 0, 0)).circle(g['disc_od'] / 2).extrude(g['disc_thk'])
    dom = dom.cut(disc.rotate((g['L'] / 2, 0, -(g['disc_od'] / 2 - 0.03)), (0, 1, 0), 88))
    step = os.path.join(CASE, 'fluid_open.step')
    dom.val().exportStep(step)
    vol = dom.val().Volume()
    nsurf = len(dom.faces().vals())
    print('  流体域体积 = %.6f m3   x 跨度 = %.3f m   边界面数 = %d' % (vol, g['UP'] + g['L'] + g['DNC'], nsurf))
    return (step, vol, nsurf)

if __name__ == "__main__":
    raise SystemExit("Geometry-only diagnostic module. Use propose_flow_geometry.py; product solvers are disabled.")
