#!/usr/bin/env python3
"""Evaluate fit, source status and dependencies without selecting pressure hardware."""
import hashlib
import json
import math
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ALLOWED={'PROPOSED','INHERITED_STUDY','DERIVED_STUDY'}


def finite_positive(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0


def require_unknowns(mapping,required):
    if not set(required)<=set(mapping) or any(v is not None for v in mapping.values()):
        raise ValueError('Missing or silently selected required unresolved design field')


def unwrap(rows):
    result={}
    for key,row in rows.items():
        expected_unit='count' if key=='ring_count' else 'mm'
        if row['kind'] not in ALLOWED or row['unit']!=expected_unit or not finite_positive(row['value']):
            raise ValueError('Invalid or untraceable interface field '+key)
        if expected_unit=='count' and type(row['value']) is not int:raise ValueError('Fractional ring count')
        result[key]=row['value']
    return result


def joint_metrics(common,candidate):
    require_unknowns(candidate['unresolved'],('bolt_material','strength_class','preload_N','tightening_torque_Nm',
                     'gasket_material','gasket_compression','flange_stress_acceptance'))
    if candidate['selected'] is not False:
        raise ValueError('Unreviewed bolt/gasket strength or selection is not permitted')
    p=unwrap(candidate['values']);n=candidate['bolt_count']
    if type(n) is not int or n<3:raise ValueError('Invalid bolt count')
    hole_radius=p['bolt_hole_d']/2;pitch_radius=p['bolt_circle_d']/2
    metrics={'radial_bolt_clearance_mm':(p['bolt_hole_d']-p['bolt_nominal_d'])/2,
             'hole_to_flange_edge_mm':p['flange_od']/2-pitch_radius-hole_radius,
             'washer_to_flange_edge_mm':p['flange_od']/2-pitch_radius-p['washer_od']/2,
             'washer_radial_band_mm':(p['washer_od']-p['bolt_hole_d'])/2,
             'washer_to_pressure_opening_gap_mm':pitch_radius-p['washer_od']/2-common['pressure_opening_d']/2,
             'washer_to_nut_envelope_margin_mm':p['washer_od']/2-p['nut_af_envelope']/math.sqrt(3),
             'nut_proxy_wall_mm':(p['nut_af_envelope']-p['bolt_nominal_d'])/2,
             'nut_envelope_to_flange_edge_mm':p['flange_od']/2-pitch_radius-p['nut_af_envelope']/math.sqrt(3),
             'gasket_to_hole_gap_mm':pitch_radius-hole_radius-p['gasket_od']/2,
             'gasket_width_mm':(p['gasket_od']-p['gasket_id'])/2,
             'gasket_to_pressure_opening_gap_mm':(p['gasket_id']-common['pressure_opening_d'])/2,
             'adjacent_hole_ligament_mm':2*pitch_radius*math.sin(math.pi/n)-p['bolt_hole_d'],
             'adjacent_washer_gap_mm':2*pitch_radius*math.sin(math.pi/n)-p['washer_od'],
             'adjacent_nut_envelope_gap_mm':2*pitch_radius*math.sin(math.pi/n)-2*p['nut_af_envelope']/math.sqrt(3)}
    failures=[key for key,v in metrics.items() if not finite_positive(v)]
    pressure_area=math.pi*common['pressure_opening_d']**2/4
    return {'id':candidate['id'],'fit_gate':'PASS' if not failures else 'FAIL','metrics':metrics,'failures':failures,
            'opening_area_mm2':pressure_area,
            'opening_area_divided_by_fastener_count_mm2':pressure_area/n,
            'load_scope':'Geometric opening area only. Effective pressure/sealing diameter, true joint separating force and load sharing remain unknown.',
            'nominal_grip_mm':p['body_flange_t']+p['gasket_nominal_t']+p['cover_flange_t']+2*p['washer_t'],
            'qualification':'Positive geometric distances only; not code minimums, strength, gasket seating, preload or torque acceptance'}


def evaluate(data):
    if data['release_authorized'] is not False or data['solver_execution_allowed'] is not False:
        raise ValueError('Interface study cannot authorize release or a solver')
    require_unknowns(data['global_unknowns'],('design_pressure_MPa','material_grade_selection','allowable_stresses','design_torque_Nm'))
    ids=[c['id'] for c in data['bonnet_joint_candidates']+data['drive_nut_candidates']]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,50}',x) for x in ids):
        raise ValueError('Candidate identifiers must be unique safe local names')
    base=HERE.parents[1]/'C2/T11/parameters.json'
    if hashlib.sha256(base.read_bytes()).hexdigest()!=data['base_parameters_sha256']:
        raise ValueError('Frozen C2 baseline changed')
    common=unwrap(data['common']);gland=unwrap(data['packing_gland']['values'])
    if not (common['stem_d']<gland['follower_id']<gland['follower_od']<common['stuffing_box_d']):
        raise ValueError('Packing follower nesting invalid')
    if not (gland['housing_od']>common['stuffing_box_d'] and gland['collar_od']>gland['follower_od']):
        raise ValueError('Housing/collar envelope nesting invalid')
    if not (gland['gland_stud_nominal_d']<gland['gland_stud_hole_d']<gland['gland_washer_od']):
        raise ValueError('Gland stud/hole/washer nesting invalid')
    if gland['gland_washer_od']/2<=gland['gland_nut_af_envelope']/math.sqrt(3):
        raise ValueError('Gland washer does not cover hex-envelope footprint')
    if gland['gland_stud_pitch']/2-gland['gland_washer_od']/2<=common['stuffing_box_d']/2:
        raise ValueError('Gland washer crosses stuffing opening')
    if gland['gland_washer_od']/2+gland['gland_stud_pitch']/2>=gland['collar_bar_length']/2 or gland['gland_washer_od']>=gland['collar_bar_width']:
        raise ValueError('Gland washer overhangs proposed crossbar')
    if not (gland['blind_hole_bottom_offset']<gland['stud_bottom_offset']<common['neck_top_z']-common['packing_bottom_z']):
        raise ValueError('Blind hole and stud axial nesting invalid')
    b={k:v['value'] for k,v in json.loads(base.read_text())['values'].items()}
    inherited={'pressure_opening_d':2*b['chamber_radius'],'stem_d':b['stem_od'],
               'valve_center_x':b['face_to_face']/2,
               'stuffing_box_d':2*b['stem_bore_radius'],'packing_bottom_z':b['packing_bottom'],
               'neck_top_z':b['neck_top'],
               'handwheel_hub_closed_bottom_z':b['upper_height']-b['stem_travel']-b['handwheel_hub_height']}
    for key,value in inherited.items():
        if not math.isclose(common[key],value,rel_tol=0,abs_tol=1e-9):raise ValueError('Inherited datum drift '+key)
    require_unknowns(data['packing_gland']['unresolved'],('packing_material','compression_load_N','allowable_compression_ratio','leakage_acceptance'))
    if data['packing_gland']['selected'] is not False:
        raise ValueError('Packing selection/load must remain unresolved')
    packing_top=common['packing_bottom_z']+gland['packing_height']
    follower_collar_bottom=common['neck_top_z']+gland['gland_gap']
    if packing_top>=follower_collar_bottom:raise ValueError('No positive follower sleeve length')
    gland_nut_top=follower_collar_bottom+gland['gland_collar_t']+gland['gland_washer_t']+gland['gland_nut_h_envelope']
    support_bottom=gland_nut_top+common['minimum_visual_gap']
    available=common['handwheel_hub_closed_bottom_z']-support_bottom
    drives=[]
    for n in data['drive_nut_candidates']:
        if n['selected'] is not False or not finite_positive(n['length']) or not finite_positive(n['body_od']) or n['body_od']<=common['stem_d']:
            raise ValueError('Invalid drive scenario')
        gap=available-n['length']
        drives.append({'id':n['id'],'nut_bottom_z_mm':support_bottom,'nut_top_z_mm':support_bottom+n['length'],
                       'handwheel_hub_gap_mm':gap,'packaging_gate':'PASS' if gap>=common['minimum_visual_gap'] else 'FAIL',
                       'additional_axial_space_required_mm':max(0,common['minimum_visual_gap']-gap),
                       'status':'UNSELECTED','thread_capacity':'UNASSESSED','full_drive_fit':'UNASSESSED','source_kind':n['kind'],
                       'qualification':'Envelope screen only; thread hand, material, retention, engagement and supplier drawing remain unresolved'})
    return {'schema':'valve.c3-interface-check/1.0','status':'UNSELECTED_STUDY','joint_candidates':[joint_metrics(common,r) for r in data['bonnet_joint_candidates']],
            'packing_stack':{'packing_top_z_mm':packing_top,'follower_collar_bottom_z_mm':follower_collar_bottom,
                             'gland_nut_top_z_mm':gland_nut_top,
                             'gland_stud_tip_z_mm':gland_nut_top+gland['gland_stud_protrusion'],
                             'drive_support_bottom_z_mm':support_bottom,
                             'scope_note':'Support plane is a proposed nut-top stack datum; full support/retention geometry and vendor flange not modeled',
                             'nut_available_axial_space_mm':available,
                             'follower_radial_clearance_mm':(common['stuffing_box_d']-gland['follower_od'])/2,
                             'stem_radial_clearance_mm':(gland['follower_id']-common['stem_d'])/2,
                             'packing_compression_and_leakage':'UNASSESSED'},
            'drive_candidates':drives,'selection':None,'manufacturing_authorized':False,
            'minimal_owner_decisions':['Governing product variant and pressure-temperature/differential duty',
               'Governing classification/standards edition and authorized acceptance basis',
               'Whether a new derivative may change reference external envelope; no such change has been selected']}


def main():
    source=HERE/'interface_candidates.json';data=json.loads(source.read_text());report=evaluate(data)
    report['interfaces_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    report['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=HERE.parent/'T22/interface_check.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
