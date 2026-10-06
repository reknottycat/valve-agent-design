#!/usr/bin/env python3
"""Drawing-consistent axial-lift study, not an exact reconstruction or release.

One parameter owner, millimetres throughout. Fluid volume is derived from the
same voids and moving solids; no separate invented CFD valve geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent


def load_parameters(path=None):
    source = Path(path) if path else HERE.parent / 'T11/parameters.json'
    data = json.loads(source.read_text())
    if data['length_unit'] != 'mm' or data['status'] != 'EXPLORATORY_NOT_FROZEN':
        raise ValueError('Only explicitly exploratory millimetre parameters are accepted')
    p = {key: row['value'] for key, row in data['values'].items()}
    for key, value in p.items():
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Invalid parameter ' + key)
    p['seat_face_z']=p['chamber_floor_z']+p['seat_proud_height']
    if not (p['bore'] < p['seat_od'] <= p['disc_od'] < 2*p['chamber_radius']):
        raise ValueError('Invalid seat/disc/chamber nesting')
    if not (0 < p['disc_max_lift'] <= p['stem_travel'] and p['disc_max_lift'] < p['body_top']-p['seat_face_z']-p['disc_thickness']-p['guide_height']):
        raise ValueError('Lift/guide exceeds chamber envelope')
    return p, data, hashlib.sha256(source.read_bytes()).hexdigest()


def zcyl(x, radius, z0, height):
    return cq.Workplane('XY', origin=(x, 0, z0)).circle(radius).extrude(height)


def xcyl(x0, radius, length):
    return cq.Workplane('YZ', origin=(x0, 0, 0)).circle(radius).extrude(length)


def ellipse_loft(stations):
    # Explicit global planes avoid cumulative center/offset drift.
    wires = [cq.Workplane('YZ', origin=(x, 0, z)).ellipse(ry, rz).val()
             for x, z, ry, rz in stations]
    return cq.Workplane('XY').newObject([cq.Solid.makeLoft(wires, ruled=True)])


def make_model(p):
    L, rb, wall = p['face_to_face'], p['bore']/2, p['shell_wall']
    cx = L/2
    inlet_stations = [(0, 0, rb, rb), (p['flange_thickness'], 0, rb, rb),
                      (p['inlet_transition_end'], p['lower_channel_z'],
                       p['lower_channel_y_radius'], p['lower_channel_z_radius']),
                      (cx, p['lower_channel_z'], p['lower_channel_y_radius'], p['lower_channel_z_radius'])]
    outlet_stations = [(p['outlet_transition_start'], p['upper_channel_z'],
                        p['upper_channel_y_radius'], p['upper_channel_z_radius']),
                       (L-p['flange_thickness'], 0, rb, rb), (L, 0, rb, rb)]
    inlet = ellipse_loft(inlet_stations)
    outlet = ellipse_loft(outlet_stations)
    chamber = zcyl(cx, p['chamber_radius'], p['chamber_floor_z'], p['body_top']-p['chamber_floor_z'])
    throat = zcyl(cx, rb, p['lower_channel_z'], p['seat_face_z']-p['lower_channel_z'])
    flow_void = inlet.union(throat).union(chamber).union(outlet)
    outer_inlet = ellipse_loft([(x,z,ry+wall,rz+wall) for x,z,ry,rz in inlet_stations])
    outer_outlet = ellipse_loft([(x,z,ry+wall,rz+wall) for x,z,ry,rz in outlet_stations])
    outer = outer_inlet.union(outer_outlet).union(zcyl(cx, p['chamber_radius']+wall, p['body_bottom'], p['body_top']-p['body_bottom']))
    outer = outer.union(zcyl(cx, p['bonnet_flange_radius'], p['body_top']-p['body_flange_thickness'], p['body_flange_thickness']))
    h = p['raised_face_height']; t = p['flange_thickness']
    outer = outer.union(xcyl(0,p['raised_face_od']/2,h)).union(xcyl(h,p['flange_od']/2,t-h))
    outer = outer.union(xcyl(L-t,p['flange_od']/2,t-h)).union(xcyl(L-h,p['raised_face_od']/2,h))
    seat_pocket = zcyl(cx, p['seat_od']/2, p['seat_face_z']-p['seat_thickness'], p['seat_thickness'])
    body = outer.cut(flow_void).cut(seat_pocket)
    for i in range(p['flange_holes']):
        angle = math.radians(i*360/p['flange_holes'])
        y,z = p['bolt_circle']/2*math.cos(angle), p['bolt_circle']/2*math.sin(angle)
        for x in (0, L-t):
            body = body.cut(cq.Workplane('YZ',origin=(x,y,z)).circle(p['flange_hole_d']/2).extrude(t))
    seat = seat_pocket.cut(zcyl(cx,rb,p['seat_face_z']-p['seat_thickness']-1,p['seat_thickness']+2))
    disc = zcyl(cx,p['disc_od']/2,p['seat_face_z'],p['disc_thickness'])
    guide_z = p['seat_face_z']+p['disc_thickness']
    guide = zcyl(cx,p['guide_od']/2,guide_z,p['guide_height']).cut(zcyl(cx,p['guide_id']/2,guide_z,p['guide_height']+1))
    disc = disc.union(guide)
    bonnet = zcyl(cx,p['bonnet_flange_radius'],p['body_top'],p['bonnet_thickness'])
    bonnet = bonnet.union(zcyl(cx,p['neck_radius'],p['body_top']+p['bonnet_thickness'],
                              p['neck_top']-p['body_top']-p['bonnet_thickness']))
    bonnet = bonnet.cut(zcyl(cx,p['stem_bore_radius'],p['body_top']-1,p['neck_top']-p['body_top']+2))
    packing = zcyl(cx,p['stem_bore_radius'],p['packing_bottom'],p['packing_height']).cut(zcyl(cx,p['stem_od']/2,p['packing_bottom']-1,p['packing_height']+2))
    closed_top = p['upper_height']-p['stem_travel']
    hub_h=p['handwheel_hub_height'];rim=p['handwheel_rim_radius'];hub=p['handwheel_hub_radius']
    stem = zcyl(cx,p['stem_od']/2,guide_z,closed_top-hub_h-guide_z)
    stem = stem.union(cq.Workplane('XY',origin=(cx,0,closed_top-hub_h)).rect(p['stem_square'],p['stem_square']).extrude(hub_h))
    wheel_z = closed_top-rim
    wheel = cq.Workplane('XY').newObject([cq.Solid.makeTorus(p['handwheel_od']/2-rim,rim)]).translate((cx,0,wheel_z))
    wheel = wheel.union(zcyl(cx,hub,closed_top-hub_h,hub_h))
    spoke_min=hub-p['spoke_overlap'];spoke_max=p['handwheel_od']/2-rim+p['spoke_overlap']
    for angle in (0,90,180,270):
        spoke = cq.Workplane('XY',origin=(cx+(spoke_min+spoke_max)/2,0,wheel_z-p['spoke_thickness']/2)).rect(spoke_max-spoke_min,p['spoke_width']).extrude(p['spoke_thickness'])
        wheel = wheel.union(spoke.rotate((cx,0,0),(cx,0,1),angle))
    square=p['stem_square']+p['square_drive_clearance']
    wheel = wheel.cut(cq.Workplane('XY',origin=(cx,0,closed_top-hub_h-1)).rect(square,square).extrude(hub_h+2))
    static = {'body':body,'seat_ring':seat,'bonnet':bonnet,'packing':packing}
    moving = {'disc_guide':disc,'stem':stem,'handwheel':wheel}
    return {'static':static,'moving_closed':moving,'flow_void':flow_void,'parameter_values':p}


def pose(model, disc_lift=0., stem_retraction=0.):
    p=model['parameter_values']
    if not (0 <= disc_lift <= min(stem_retraction,p['disc_max_lift']) and 0 <= stem_retraction <= p['stem_travel']):
        raise ValueError('Disc cannot pass through the screw stop; pose outside admitted study stroke')
    parts=dict(model['static'])
    for name,shape in model['moving_closed'].items():
        parts[name]=shape.translate((0,0,disc_lift if name=='disc_guide' else stem_retraction))
    return parts


def fluid_domain(model, parts, extension_dn=3.):
    p=model['parameter_values']; L=p['face_to_face']; r=p['bore']/2; ext=extension_dn*p['bore']
    fluid=model['flow_void'].union(xcyl(-ext,r,ext)).union(xcyl(L,r,ext))
    # Study simplification: dead-end spindle cavity is capped at the modeled packing plane.
    neck_void=zcyl(L/2,p['stem_bore_radius'],p['body_top'],p['packing_bottom']-p['body_top'])
    fluid=fluid.union(neck_void)
    for name in ('disc_guide','stem','seat_ring'):
        fluid=fluid.cut(parts[name])
    return fluid


def export_candidate(output, parameter_path=None):
    p,metadata,digest=load_parameters(parameter_path); model=make_model(p)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    report={'schema':'valve.c2-build/1.0','status':'EXPLORATORY_NOT_FROZEN','parameters_sha256':digest,
            'builder_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'parameters':metadata,'poses':{},'manufacturing_authorized':False}
    for name,lift,stop in [('closed',0.,0.),('check_closed',0.,p['stem_travel']),('open',p['disc_max_lift'],p['stem_travel'])]:
        folder=output/name;folder.mkdir(exist_ok=True);parts=pose(model,lift,stop)
        assembly=cq.Assembly(name='C2_'+name)
        for part,shape in parts.items():
            shape.val().exportStep(str(folder/(part+'.step')))
            assembly.add(shape,name=part)
        assembly.save(str(folder/'assembly.step'))
        fluid=fluid_domain(model,parts)
        fluid.val().exportStep(str(folder/'fluid_domain_mm.step'))
        report['poses'][name]={'disc_lift_mm':lift,'stem_retraction_mm':stop,
            'fluid_solid_count':len(fluid.val().Solids()),
            'parts':{part:{'valid':shape.val().isValid(),'solids':len(shape.val().Solids()),
                           'volume_mm3':shape.val().Volume(1e-9)} for part,shape in parts.items()}}
    report['asset_hashes']={str(f.relative_to(output)):hashlib.sha256(f.read_bytes()).hexdigest()
                            for f in output.rglob('*.step')}
    (output/'build_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report['poses'],indent=2))
    return model


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'out');parser.add_argument('--parameters',type=Path)
    args=parser.parse_args();export_candidate(args.output,args.parameters)
