#!/usr/bin/env python3
"""Measure planar support areas; never infer pressure/sealing acceptance."""
import hashlib
import json
import math
from pathlib import Path
import sys
import cadquery as cq

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE.parent/'C2/T22'))
from validate_lift_model import contact_area


def read(folder,name):return cq.importers.importStep(str(folder/(name+'.step')))


def require_full(actual,expected,label):
    if not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-6,abs_tol=1e-3):
        raise RuntimeError('Incomplete geometric support '+label)


def main():
    data=json.loads((BASE/'T11/interface_candidates.json').read_text());rows=[]
    preview=json.loads((BASE/'T12/out/preview_report.json').read_text())
    if preview['interfaces_sha256']!=hashlib.sha256((BASE/'T11/interface_candidates.json').read_bytes()).hexdigest():
        raise ValueError('Stale interface preview')
    for c in data['bonnet_joint_candidates']:
        p={k:v['value'] for k,v in c['values'].items()};folder=BASE/'T12/out'/c['id']
        body=read(folder,'body_flange_coupon');cover=read(folder,'cover_coupon');gasket=read(folder,'gasket_uncompressed')
        area=math.pi*(p['gasket_od']**2-p['gasket_id']**2)/4
        contacts={'body':contact_area(gasket,body),'cover':contact_area(gasket,cover)}
        for name,v in contacts.items():require_full(v,area,c['id']+':gasket:'+name)
        expected_washer=math.pi*(p['washer_od']**2-p['bolt_hole_d']**2)/4
        washers=[]
        for i in range(1,c['bolt_count']+1):
            for suffix,plate in [('lower',body),('upper',cover)]:
                a=contact_area(read(folder,f'washer_{suffix}_{i:02}'),plate)
                require_full(a,expected_washer,c['id']+':washer');washers.append(a)
        rows.append({'id':c['id'],'gasket_face_area_mm2':area,'gasket_contact_mm2':contacts,
                     'washer_faces_checked':len(washers),'washer_expected_face_mm2':expected_washer,
                     'washer_min_contact_mm2':min(washers),'geometric_support':'FULL_FOR_GASKET_AND_WASHERS',
                     'strength_seating_preload_acceptance':'UNASSESSED'})
    folder=BASE/'T12/out/packing_gland';housing=read(folder,'housing_coupon');follower=read(folder,'follower_and_collar')
    c={k:v['value'] for k,v in data['common'].items()};g={k:v['value'] for k,v in data['packing_gland']['values'].items()}
    first=read(folder,'packing_ring_1');last=read(folder,f"packing_ring_{g['ring_count']}")
    annulus=math.pi*(c['stuffing_box_d']**2-c['stem_d']**2)/4
    bottom=contact_area(first,housing);top=contact_area(last,follower)
    if not all(math.isfinite(v) and 0<v<=annulus+1e-3 for v in (bottom,top)):raise RuntimeError('Unknown packing contact')
    packing={'annular_face_area_mm2':annulus,'bottom_housing_contact_mm2':bottom,'top_follower_contact_mm2':top,
             'bottom_contact_fraction':bottom/annulus,'top_contact_fraction':top/annulus,
             'status':'PARTIAL_GEOMETRIC_END_SUPPORT','extrusion_compression_and_leakage_acceptance':'UNASSESSED'}
    result={'status':'GEOMETRIC_MEASUREMENTS_ONLY','interfaces_sha256':hashlib.sha256((BASE/'T11/interface_candidates.json').read_bytes()).hexdigest(),
            'joint_support':rows,'packing_end_support':packing,'manufacturing_authorized':False}
    (BASE/'T22/surface_support.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
