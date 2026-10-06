#!/usr/bin/env python3
"""C2 geometry withdrawal study only; never a field maintenance procedure."""
import hashlib
import json
import math
from pathlib import Path
import cadquery as cq

BASE=Path(__file__).resolve().parents[1];C2=BASE.parent/'C2'


def volume_common(a,b):
    ba,bb=a.BoundingBox(),b.BoundingBox()
    if any(getattr(ba,k+'max')<getattr(bb,k+'min')-1e-6 or getattr(bb,k+'max')<getattr(ba,k+'min')-1e-6 for k in 'xyz'):return 0.
    c=a.intersect(b)
    if not c.isValid():raise ValueError('Unknown assembly Boolean')
    v=c.Volume(1e-9) if c.Solids() else 0.
    if not math.isfinite(v) or v<0:raise ValueError('Unknown assembly intersection volume')
    return v


def main():
    build=json.loads((C2/'T12/out/build_report.json').read_text());parts={}
    for name in ('body','seat_ring','disc_guide','bonnet','packing','stem','handwheel'):
        key='closed/'+name+'.step';path=C2/'T12/out'/key
        if hashlib.sha256(path.read_bytes()).hexdigest()!=build['asset_hashes'][key]:raise ValueError('Frozen input changed')
        parts[name]=cq.importers.importStep(str(path)).val()
    samples=(0,25,50,100,150,200,250)
    rows=[]
    for lift in samples:
        moving=parts['disc_guide'].translate((0,0,lift))
        rows.append({'lift_mm':lift,'body_overlap_mm3':volume_common(moving,parts['body']),
                     'seat_overlap_mm3':volume_common(moving,parts['seat_ring'])})
    negative=volume_common(parts['disc_guide'].translate((0,0,200)),parts['bonnet'])
    fixed_stem_negative=volume_common(parts['disc_guide'].translate((0,0,25)),parts['stem'])
    passed=all(r['body_overlap_mm3']<1e-3 and r['seat_overlap_mm3']<1e-3 for r in rows)
    if not passed or negative<=1e-3 or fixed_stem_negative<=1e-3:raise RuntimeError('Withdrawal geometry or negative control failed')
    report={'status':'GEOMETRIC_ROUTE_ONLY','withdrawal_samples':rows,
            'requires_bonnet_and_stem_group_removed':True,
            'negative_control_disc_lift200_with_bonnet_present_overlap_mm3':negative,
            'negative_control_disc_lift25_with_fixed_stem_overlap_mm3':fixed_stem_negative,
            'scope':'Frozen C2 main geometry; not C3 joint coupon integration',
            'limits':['Discrete axial samples, not continuous swept-volume proof','Actual retention, guides, fasteners and lifting access not yet designed',
                      'No extraction-force or service-maintenance approval','Not instructions for work on physical equipment'],
            'manufacturing_authorized':False}
    (BASE/'T22/assembly_access.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
