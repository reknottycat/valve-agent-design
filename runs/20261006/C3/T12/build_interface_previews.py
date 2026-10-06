#!/usr/bin/env python3
"""Separate joint/packing coupons and drive envelopes, not manufacturing parts."""
import hashlib
import json
import math
from pathlib import Path
import sys

import cadquery as cq

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE/'T11'))
sys.path.insert(0,str(BASE.parent/'CLOUD/T04'))
from check_interfaces import evaluate,unwrap
from geometry_gate import check_exchange,measure as coarse_measure,step_length_unit


def ring(ro,ri,z,h,xy=(0.,0.)):
    return cq.Workplane('XY',origin=(*xy,z)).circle(ro).circle(ri).extrude(h)


def cyl(r,z,h,xy=(0.,0.)):
    return cq.Workplane('XY',origin=(*xy,z)).circle(r).extrude(h)


def hex_proxy(af,bore,z,h,xy):
    return cq.Workplane('XY',origin=(*xy,z)).polygon(6,2*af/math.sqrt(3)).extrude(h).cut(cyl(bore/2,z-1,h+2,xy))


def measured(s):
    data=coarse_measure(s);data['volume']=s.Volume(1e-9)
    for row,solid in zip(data['components'],s.Solids()):row['volume']=solid.Volume(1e-9)
    return data


def export_parts(folder,parts):
    folder.mkdir(parents=True,exist_ok=True);records={}
    for name,wp in parts.items():
        shape=wp.val()
        if not shape.isValid() or len(shape.Solids())!=1:raise RuntimeError('Invalid preview part '+name)
        f=folder/(name+'.step');shape.exportStep(str(f));readback=cq.importers.importStep(str(f)).val()
        exchange=check_exchange(measured(shape),measured(readback))
        if exchange['status']!='PASS' or step_length_unit(f)['unit']!='mm':raise RuntimeError('Preview exchange failed '+name)
        records[name]={'volume_mm3':shape.Volume(1e-9),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'exchange':exchange,
                       'material':None,'qualification':'ENVELOPE_ONLY'}
    compound=cq.Compound.makeCompound([w.val() for w in parts.values()]);file=folder/'assembly.step';compound.exportStep(str(file))
    imported=cq.importers.importStep(str(file)).val();exchange=check_exchange(measured(compound),measured(imported))
    if exchange['status']!='PASS':raise RuntimeError('Assembly exchange failed')
    return {'parts':records,'part_count':len(parts),'assembly_exchange':exchange,
            'assembly_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}


def joint_preview(common,candidate):
    p=unwrap(candidate['values']);n=candidate['bolt_count']
    tb,tc,tg,tw,hn=p['body_flange_t'],p['cover_flange_t'],p['gasket_nominal_t'],p['washer_t'],p['nut_h_envelope']
    cover_z=tb+tg;top=cover_z+tc
    body=ring(p['flange_od']/2,common['pressure_opening_d']/2,0,tb)
    cover=ring(p['flange_od']/2,common['stuffing_box_d']/2,cover_z,tc)
    parts={'gasket_uncompressed':ring(p['gasket_od']/2,p['gasket_id']/2,tb,tg)}
    for i in range(n):
        a=math.tau*i/n;xy=(p['bolt_circle_d']/2*math.cos(a),p['bolt_circle_d']/2*math.sin(a))
        body=body.cut(cyl(p['bolt_hole_d']/2,-1,tb+2,xy))
        cover=cover.cut(cyl(p['bolt_hole_d']/2,cover_z-1,tc+2,xy))
        low=-tw-hn-p['stud_protrusion_each'];high=top+tw+hn+p['stud_protrusion_each']
        parts[f'stud_{i+1:02}']=cyl(p['bolt_nominal_d']/2,low,high-low,xy)
        for suffix,z in [('lower',-tw),('upper',top)]:
            parts[f'washer_{suffix}_{i+1:02}']=ring(p['washer_od']/2,p['bolt_hole_d']/2,z,tw,xy)
        for suffix,z in [('lower',-tw-hn),('upper',top+tw)]:
            parts[f'nut_proxy_{suffix}_{i+1:02}']=hex_proxy(p['nut_af_envelope'],p['bolt_nominal_d'],z,hn,xy)
    parts['body_flange_coupon']=body;parts['cover_coupon']=cover
    return parts


def packing_preview(common,data):
    g=unwrap(data['values']);cx=common['valve_center_x'];xy=(cx,0.);z=common['packing_bottom_z'];top=common['neck_top_z']
    housing=cyl(g['housing_od']/2,z-g['housing_below_packing'],top-z+g['housing_below_packing'],xy)
    housing=housing.cut(cyl(common['stuffing_box_d']/2,z,top-z+1,xy))
    housing=housing.cut(cyl(g['follower_id']/2,z-g['housing_below_packing']-1,g['housing_below_packing']+2,xy))
    parts={};height=g['packing_height']/g['ring_count']
    for i in range(g['ring_count']):
        parts[f'packing_ring_{i+1}']=ring(common['stuffing_box_d']/2,common['stem_d']/2,z+i*height,height,xy)
    collar_z=top+g['gland_gap'];packing_top=z+g['packing_height']
    follower=ring(g['follower_od']/2,g['follower_id']/2,packing_top,collar_z-packing_top,xy)
    collar=ring(g['collar_od']/2,g['follower_id']/2,collar_z,g['gland_collar_t'],xy)
    crossbar=cq.Workplane('XY',origin=(cx,0,collar_z)).rect(g['collar_bar_length'],g['collar_bar_width']).extrude(g['gland_collar_t'])
    collar=collar.union(crossbar).cut(cyl(g['follower_id']/2,collar_z-1,g['gland_collar_t']+2,xy))
    for i,sign in enumerate((-1,1),1):
        bolt_xy=(cx+sign*g['gland_stud_pitch']/2,0.)
        housing=housing.cut(cyl(g['gland_stud_hole_d']/2,z+g['blind_hole_bottom_offset'],top-z-g['blind_hole_bottom_offset']+1,bolt_xy))
        collar=collar.cut(cyl(g['gland_stud_hole_d']/2,collar_z-1,g['gland_collar_t']+2,bolt_xy))
        washer_z=collar_z+g['gland_collar_t'];nut_z=washer_z+g['gland_washer_t']
        parts[f'gland_stud_{i}']=cyl(g['gland_stud_nominal_d']/2,z+g['stud_bottom_offset'],nut_z+g['gland_nut_h_envelope']+g['gland_stud_protrusion']-z-g['stud_bottom_offset'],bolt_xy)
        parts[f'gland_washer_{i}']=ring(g['gland_washer_od']/2,g['gland_stud_hole_d']/2,washer_z,g['gland_washer_t'],bolt_xy)
        parts[f'gland_nut_proxy_{i}']=hex_proxy(g['gland_nut_af_envelope'],g['gland_stud_nominal_d'],nut_z,g['gland_nut_h_envelope'],bolt_xy)
    parts['housing_coupon']=housing;parts['follower_and_collar']=follower.union(collar)
    parts['stem_proxy']=cyl(common['stem_d']/2,z-g['stem_proxy_below_packing'],g['stem_proxy_length'],xy)
    return parts


def main():
    file=BASE/'T11/interface_candidates.json';data=json.loads(file.read_text());report=evaluate(data)
    common=unwrap(data['common']);out=HERE/'out';out.mkdir(exist_ok=True)
    result={'schema':'valve.c3-preview/1.0','interfaces_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'status':'UNSELECTED_COUPONS_AND_ENVELOPES',
            'checker_sha256':hashlib.sha256((BASE/'T11/check_interfaces.py').read_bytes()).hexdigest(),
            'joint_candidates':{},'drive_candidates':[],'manufacturing_authorized':False,
            'limits':['No threads modeled; smooth mating cylinders are interface proxies',
                      'No material, bolt grade, preload, torque, packing compression or load capacity selected',
                      'Joint coupons are separate from C2 and are not integrated pressure-bearing valve parts']}
    for candidate,metrics in zip(data['bonnet_joint_candidates'],report['joint_candidates']):
        if metrics['fit_gate']!='PASS':raise RuntimeError('Cannot preview invalid joint dimensions')
        result['joint_candidates'][candidate['id']]=export_parts(out/candidate['id'],joint_preview(common,candidate))
    result['packing_gland']=export_parts(out/'packing_gland',packing_preview(common,data['packing_gland']))
    base=BASE.parent/'C2';build=json.loads((base/'T12/out/build_report.json').read_text())
    wheel_path=base/'T12/out/closed/handwheel.step'
    if hashlib.sha256(wheel_path.read_bytes()).hexdigest()!=build['asset_hashes']['closed/handwheel.step']:
        raise ValueError('Frozen handwheel changed')
    wheel=cq.importers.importStep(str(wheel_path)).val()
    for candidate,fit in zip(data['drive_nut_candidates'],report['drive_candidates']):
        nut=ring(candidate['body_od']/2,common['stem_d']/2,fit['nut_bottom_z_mm'],candidate['length'],(common['valve_center_x'],0))
        folder=out/candidate['id'];saved=export_parts(folder,{'nut_cylindrical_envelope':nut})
        common_shape=nut.val().intersect(wheel)
        if not common_shape.isValid():raise ValueError('Invalid drive/wheel Boolean')
        volume=common_shape.Volume(1e-9) if common_shape.Solids() else 0.
        if not math.isfinite(volume) or volume<0:raise ValueError('Unknown drive overlap')
        result['drive_candidates'].append({'id':candidate['id'],'measured_overlap_with_C2_handwheel_mm3':volume,
                                          'measured_collision':volume>1e-3,'axial_envelope_screen':fit,'export':saved,
                                          'qualification':'Nominal cylindrical envelope only, not exact vendor CAD or suitability approval'})
    (out/'preview_report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'joint_part_counts':{k:v['part_count'] for k,v in result['joint_candidates'].items()},
                      'packing_parts':result['packing_gland']['part_count'],
                      'drive_collisions':[{k:x[k] for k in ('id','measured_overlap_with_C2_handwheel_mm3','measured_collision')} for x in result['drive_candidates']]},indent=2))


if __name__=='__main__':main()
