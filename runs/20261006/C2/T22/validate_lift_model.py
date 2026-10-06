#!/usr/bin/env python3
"""Explicit geometry/motion checks. No material or pressure qualification."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'T12'))
sys.path.insert(0,str(HERE.parents[1]/'CLOUD/T04'))
from build_lift_model import load_parameters, make_model, pose, fluid_domain
from geometry_gate import check_geometry, check_exchange, measure as measure_default, step_length_unit
import cadquery as cq


def measure(shape):
    result=measure_default(shape)
    # Default nonadaptive OCCT mass integration drifted 2.1e-6 on the lofted shell.
    # Tighten integration, not the 1e-6 exchange acceptance threshold.
    result['volume']=shape.Volume(1e-9)
    result['volume_integration_tolerance']=1e-9
    for item,solid in zip(result['components'],shape.Solids()):
        item['volume']=solid.Volume(1e-9)
    return result


def checked_overlap_value(valid, volume):
    if valid is not True or type(volume) not in (int,float) or not math.isfinite(volume) or volume<0:
        raise ValueError('Invalid/unknown Boolean intersection; cannot declare no interference')
    return volume


def overlap(a,b):
    x,y=a.val().BoundingBox(),b.val().BoundingBox()
    if any((getattr(x,k+'max') < getattr(y,k+'min')-1e-6 or getattr(y,k+'max') < getattr(x,k+'min')-1e-6)
           for k in 'xyz'):
        return 0.
    common=a.intersect(b).val()
    if not common.isValid():
        raise ValueError('Boolean intersection BREP invalid')
    return checked_overlap_value(True, common.Volume(1e-9) if common.Solids() else 0.)


def contact_area(a,b):
    # Common(solid, solid) omits zero-volume boundary contact. Compare planar faces explicitly.
    total=0.
    for fa in a.val().Faces():
        if fa.geomType()!='PLANE':continue
        n=fa.normalAt();ba=fa.BoundingBox()
        for fb in b.val().Faces():
            if fb.geomType()!='PLANE' or n.dot(fb.normalAt())>-1+1e-7:continue
            if abs((fa.Center()-fb.Center()).dot(n))>1e-6:continue
            bb=fb.BoundingBox()
            if any(getattr(ba,k+'max')<getattr(bb,k+'min')-1e-6 or
                   getattr(bb,k+'max')<getattr(ba,k+'min')-1e-6 for k in 'xyz'):continue
            common=fa.intersect(fb)
            if not common.isValid():raise ValueError('Contact Boolean BREP invalid')
            total+=checked_overlap_value(True,common.Area())
    return total


def check_disc_contacts(lift,stem,contacts,seat_area,stem_area):
    for area in contacts.values():checked_overlap_value(True,area)
    failures=[]
    if contacts['body']>1e-3:failures.append('UNINTENDED_DISC_BODY_CONTACT')
    if lift==0 and not math.isclose(contacts['seat_ring'],seat_area,rel_tol=1e-6,abs_tol=1e-3):
        failures.append('CLOSED_SEAT_CONTACT')
    if lift>0 and contacts['seat_ring']>1e-3:failures.append('OPEN_SEAT_CONTACT')
    if lift<stem and contacts['stem']>1e-3:failures.append('FREE_LIFT_CONTACT')
    if lift==stem and not math.isclose(contacts['stem'],stem_area,rel_tol=1e-6,abs_tol=1e-3):
        failures.append('STOP_CONTACT_MISSING')
    return failures


def validate(output, parameter_path=None):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'geometry_check.json').write_text(json.dumps({'geometry_gate':'RUNNING',
          'status':'BUILD_AND_VALIDATION_IN_PROGRESS','manufacturing_authorized':False},indent=2))
    p,meta,digest=load_parameters(parameter_path);m=make_model(p)
    report={'schema':'valve.c2-geometry/1.0','parameters_sha256':digest,
            'builder_code_sha256':hashlib.sha256((HERE.parent/'T12/build_lift_model.py').read_bytes()).hexdigest(),
            'validator_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'status':'EXPLORATORY_GEOMETRY_ONLY','parts':{},'motion':[],'fluid_states':[],
            'contact_method':'Opposing coplanar face-face Boolean intersections; curved contacts not assessed',
            'engineering_compliance':'NOT_ASSESSED','manufacturing_authorized':False,
            'limitations':['Motion is sampled, not a mathematical proof for every intermediate position',
                          'Geometric interference checks do not establish load carrying capacity or leak tightness',
                          'Analytical cylinder wall offsets are not a certified global minimum wall',
                          'Bonnet bolt, gasket, anti-rotation, guide and packing details remain proposed/incomplete']}
    errors=[]
    (out/'geometry_check.json').write_text(json.dumps({**report,'geometry_gate':'RUNNING'},indent=2))
    closed=pose(m)
    for name,w in closed.items():
        s=w.val();a=measure(s);f=out/(name+'.step');s.exportStep(str(f));loaded=cq.importers.importStep(str(f)).val()
        g=check_geometry(a);x=check_exchange(a,measure(loaded));u=step_length_unit(f)
        report['parts'][name]={'native_mm':a,'geometry_gate':g,'step_exchange':x,'step_unit':u}
        if g['status']!='PASS' or x['status']!='PASS' or u['unit']!='mm':errors.append('PART:'+name)
    static=list(m['static']);static_overlaps=[]
    for a,b in itertools.combinations(static,2):
        volume=overlap(closed[a],closed[b])
        if volume>1e-3:static_overlaps.append({'pair':[a,b],'overlap_mm3':volume})
    if static_overlaps:errors.append('STATIC_INTERFERENCE')
    report['static_overlaps']=static_overlaps
    lift_samples=sorted(set(min(s,p['disc_max_lift']) for s in (0.,1.,5.,10.,20.,35.,p['disc_max_lift'])))
    stem_samples=sorted(set(min(s,p['stem_travel']) for s in (0.,1.,5.,10.,20.,35.,p['stem_travel'])))
    for stem in stem_samples:
        for lift in lift_samples:
            if lift>stem:continue
            parts=pose(m,lift,stem);collisions=[]
            for a,b in itertools.combinations(parts,2):
                if a in static and b in static:continue
                volume=overlap(parts[a],parts[b])
                if volume>1e-3:collisions.append({'pair':[a,b],'overlap_mm3':volume})
            contacts={name:contact_area(parts['disc_guide'],parts[name]) for name in ('body','seat_ring','stem')}
            seat_area=math.pi*(p['seat_od']**2-p['bore']**2)/4
            failures=check_disc_contacts(lift,stem,contacts,seat_area,math.pi*p['stem_od']**2/4)
            errors.extend(f'{failure}:{lift}:{stem}' for failure in failures)
            report['motion'].append({'disc_lift_mm':lift,'stem_retraction_mm':stem,'overlaps':collisions,
                                     'disc_contact_area_mm2':contacts})
            if collisions:errors.append(f'MOTION:{lift}:{stem}')
    for lift in lift_samples:
        parts=pose(m,lift,p['stem_travel']);f=fluid_domain(m,parts);a=measure(f.val())
        expected=2 if lift==0 else 1
        gate=check_geometry(a,expected_solids=expected,expected_span=p['face_to_face']+6*p['bore'])
        # Ensure distinct intended ends are represented; gate cannot pass on a stray detached component.
        inlet_hits=sum(c['xmin'] < -3*p['bore']+1e-5 for c in a['components'])
        outlet_hits=sum(c['xmax'] > p['face_to_face']+3*p['bore']-1e-5 for c in a['components'])
        if inlet_hits!=1 or outlet_hits!=1:gate['status']='FAIL';gate['failures'].append('END_CONNECTIVITY')
        if lift==0 and any(c['xmin']<0 and c['xmax']>p['face_to_face'] for c in a['components']):
            gate['status']='FAIL';gate['failures'].append('CLOSED_BYPASS')
        report['fluid_states'].append({'disc_lift_mm':lift,'expected_solids':expected,'measurement_mm':a,'gate':gate})
        if gate['status']!='PASS':errors.append(f'FLUID:{lift}')
    upper=pose(m,p['disc_max_lift'],p['stem_travel'])
    top=max(s.val().BoundingBox().zmax for s in upper.values())
    body_box=closed['body'].val().BoundingBox()
    report['reference_checks']={'face_to_face_mm':body_box.xlen,'target_face_to_face_reference_mm':p['face_to_face'],
                                'upper_height_mm':top,'target_upper_height_reference_mm':p['upper_height'],
                                'handwheel_y_span_mm':upper['handwheel'].val().BoundingBox().ylen,
                                'target_handwheel_od_reference_mm':p['handwheel_od']}
    for actual,target in ((body_box.xlen,p['face_to_face']),(top,p['upper_height']),
                         (upper['handwheel'].val().BoundingBox().ylen,p['handwheel_od'])):
        if abs(actual-target)>1e-4:errors.append('REFERENCE_ENVELOPE')
    report['geometry_gate']='PASS' if not errors else 'FAIL';report['failures']=errors
    (out/'geometry_check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'geometry_gate':report['geometry_gate'],'failures':errors,
                      'motion_states':len(report['motion']),'flow_states':len(report['fluid_states']),
                      'reference_checks':report['reference_checks']},indent=2))
    return 0 if not errors else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'out');parser.add_argument('--parameters',type=Path)
    args=parser.parse_args();raise SystemExit(validate(args.output,args.parameters))
