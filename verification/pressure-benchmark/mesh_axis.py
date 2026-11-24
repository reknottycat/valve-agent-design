#!/usr/bin/env python3
"""Structured MSH 2.2 in metres. Analytic nozzle benchmark, NOT tilted-disc CAD."""
import argparse
import json
import math
import os
from pathlib import Path

ANGLE = math.radians(5)
R = 0.1
L = 0.04
NAMES = ('inlet', 'outlet', 'walls', 'wedgeMinus', 'wedgePlus')


def generate(path, fraction, nr=25):
    if not 0 < fraction <= 1 or nr < 2:
        raise ValueError('require 0 < throat area fraction <= 1 and nr >= 2')
    # Include both shoulders and throat exactly, without short accidental segments.
    xs = [-.60 + i*.56/112 for i in range(112)] + [-L+i*2*L/32 for i in range(32)] + [L+i*1.16/232 for i in range(233)]
    throat = R * math.sqrt(fraction)
    def radius(x):
        return R if abs(x) >= L else throat + (R-throat)*(1-math.cos(math.pi*x/L))/2
    nodes, cells, faces = [], [], []
    def add(pt):
        nodes.append(pt)
        return len(nodes)
    def ring(x):
        axis = add((x, 0., 0.)); row = [(axis,axis)]
        for j in range(1,nr+1):
            r = radius(x)*j/nr
            row.append(tuple(add((x,r*math.cos(ANGLE/2),s*r*math.sin(ANGLE/2))) for s in (-1,1)))
        return row
    rows = [ring(x) for x in xs]
    for i,(a,b) in enumerate(zip(rows,rows[1:])):
        for j in range(nr):
            am,ap=a[j]; bm,bp=b[j]; cm,cp=a[j+1]; dm,dp=b[j+1]
            if j==0:
                cells.append((6,(am,cm,cp,bm,dm,dp)))
                left,right=(am,cp,cm),(bm,dm,dp)
            else:
                cells.append((5,(am,bm,dm,cm,ap,bp,dp,cp)))
                left,right=(am,ap,cp,cm),(bm,dm,dp,bp)
            if i==0: faces.append((1,left))
            if i==len(rows)-2: faces.append((2,right))
            if j==nr-1: faces.append((3,(cm,cp,dp,dm)))
            faces.extend(((4,(am,cm,dm,bm)),(5,(ap,bp,dp,cp))))
    with path.open('w') as f:
        f.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n6\n')
        for i,name in enumerate(NAMES,1): f.write(f'2 {i} "{name}"\n')
        f.write(f'3 11 "fluid"\n$EndPhysicalNames\n$Nodes\n{len(nodes)}\n')
        for i,(x,y,z) in enumerate(nodes,1): f.write(f'{i} {x:.17g} {y:.17g} {z:.17g}\n')
        f.write(f'$EndNodes\n$Elements\n{len(cells)+len(faces)}\n')
        elements=[(2 if len(ns)==3 else 3,tag,ns) for tag,ns in faces]+[(kind,11,ns) for kind,ns in cells]
        for i,(kind,tag,ns) in enumerate(elements,1): f.write(f'{i} {kind} 2 {tag} {tag} '+ ' '.join(map(str,ns))+'\n')
        f.write('$EndElements\n')
    # Straight-sided sector: its triangle area is sin(angle)*r^2/2.
    a,b=(R+throat)/2,(R-throat)/2
    exact=.5*math.sin(ANGLE)*((1.8-2*L)*R**2+2*L*(a*a+b*b/2))
    return dict(model='analytic_nozzle_benchmark_only',cells=len(cells),wedge_deg=5,open_area_fraction=fraction,throat_radius_m=throat,inlet_area_m2=.5*math.sin(ANGLE)*R*R,volume_reference_m3=exact)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('output',type=Path); args=p.parse_args()
    stats=generate(args.output,float(os.getenv('P2_OPEN_FRAC','0.5')))
    from verify_axis import verify
    stats.update(verify(args.output,stats))
    args.output.with_name(args.output.stem+'_info.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats,ensure_ascii=False))
