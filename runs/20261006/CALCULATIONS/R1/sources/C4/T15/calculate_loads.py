#!/usr/bin/env python3
"""Reproducible pressure-component and screw/joint sensitivity arithmetic. No solver."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'T06'))
from basis_gate import validate, number


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def pressure_force(coefficients, pin, pout):
    for value in (pin,pout):number(value,'gauge pressure')
    for side in ('inlet','outlet'):
        value=coefficients[side]
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid signed pressure area')
    return coefficients['inlet']*pin+coefficients['outlet']*pout


def screw_model(force, d2, lead, half_axial_deg, mu):
    for label,v in [('force',force),('friction',mu)]:number(v,label)
    for label,v in [('pitch diameter',d2),('lead',lead)]:number(v,label,strict=True)
    number(half_axial_deg,'flank angle')
    if not 0<=half_axial_deg<45 or mu>=1:raise ValueError('Unsupported angle or friction')
    lam=math.atan(lead/(math.pi*d2))
    # Convert axial-section half flank angle to its normal-plane value.
    phi=math.atan(math.tan(math.radians(half_axial_deg))*math.cos(lam))
    effective_mu=mu/math.cos(phi);tl=math.tan(lam)
    if 1-effective_mu*tl<=0:raise ValueError('Singular screw equation')
    torque=force*d2/2000*(tl+effective_mu)/(1-effective_mu*tl)
    efficiency=tl*(math.cos(phi)-mu*tl)/(math.cos(phi)*tl+mu)
    ideal=force*lead/(2*math.pi*1000)
    if not math.isclose(torque*efficiency,ideal,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Independent efficiency/work identity mismatch')
    return {'thread_torque_Nm':torque,'ideal_frictionless_torque_Nm':ideal,
            'thread_efficiency':efficiency,'lead_angle_deg':math.degrees(lam),
            'normal_half_flank_angle_deg':math.degrees(phi),
            'static_self_lock_model':effective_mu>tl,
            'self_lock_mu_threshold':math.cos(phi)*tl}


def pressure_area_integrity(data):
    expected_paths={f'{pose}/{name}.step' for pose in ('closed','check_closed') for name in ('fluid_domain_mm','disc_guide','stem')}
    if set(data['input_asset_sha256']) != expected_paths:
        raise ValueError('Pressure-area provenance must include all six fixed STEP assets')
    for relative,digest in data['input_asset_sha256'].items():
        if not isinstance(digest,str) or digest!=sha(BASE.parent/'C2/T12/out'/relative):
            raise ValueError('Pressure-area asset hash mismatch '+relative)
    params_path=BASE.parent/'C2/T11/parameters.json'
    if data['parameters_sha256']!=sha(params_path):raise ValueError('Pressure-area parameter hash mismatch')
    parameters={k:v['value'] for k,v in json.loads(params_path.read_text())['values'].items()}
    disk=lambda diameter:math.pi*diameter**2/4
    if data['status']!='GEOMETRIC_PRESSURE_AREA_PASS' or data['manufacturing_authorized'] is not False:
        raise ValueError('Unaccepted pressure geometry')
    if (data['length_unit'],data['pressure_unit'],data['force_unit'])!=('mm','MPa','N'):
        raise ValueError('Pressure-area unit mismatch')
    if set(data['poses'])!={'closed','check_closed'}:raise ValueError('Missing pressure pose')
    for pose_name,pose in data['poses'].items():
        if pose['pressure_compartments']!=2 or pose['analytical_check']!='PASS':raise ValueError('Invalid compartment check')
        for part in ('disc_guide','stem'):
            for side in ('inlet','outlet'):
                row=pose['parts'][part][side];summed=0.
                for face in row['faces']:
                    area=number(face['wetted_area_mm2'],'wetted area')
                    normal=face['outward_normal_z']
                    if type(normal) not in (int,float) or not math.isfinite(normal) or abs(normal)>1+1e-9:raise ValueError('Invalid face normal')
                    coef=face['axial_force_coefficient_mm2']
                    if not math.isfinite(coef) or not math.isclose(coef,-normal*area,rel_tol=1e-9,abs_tol=1e-6):raise ValueError('Face pressure sign mismatch')
                    summed+=coef
                actual=row['axial_force_coefficient_N_per_MPa']
                expected_map={'disc_guide':{'inlet':disk(parameters['bore']),'outlet':-disk(parameters['seat_od'])+(disk(parameters['stem_od']) if pose_name=='closed' else 0.)},'stem':{'inlet':0.,'outlet':disk(parameters['stem_od']) if pose_name=='check_closed' else 0.}}
                expected=expected_map[part][side]
                if not math.isclose(pose['independent_projected_area_control'][part][side],expected,rel_tol=1e-9,abs_tol=1e-3):raise ValueError('Saved analytic control differs from independently loaded parameters')
                if not all(type(v) in (float,int) and math.isfinite(v) for v in (actual,expected)) or not math.isclose(summed,actual,abs_tol=1e-3) or not math.isclose(actual,expected,rel_tol=1e-7,abs_tol=1e-3):
                    raise ValueError('Pressure face sum/analytical mismatch')
    for side in ('inlet','outlet'):
        sums=[sum(p['parts'][name][side]['axial_force_coefficient_N_per_MPa'] for name in ('disc_guide','stem')) for p in data['poses'].values()]
        if not math.isclose(*sums,rel_tol=1e-9,abs_tol=1e-3):raise ValueError('Disc+stem pressure-area transfer mismatch between poses')


def calculate(basis, areas, c2, c3):
    validate(basis,check_files=False);pressure_area_integrity(areas)
    p={k:v['value'] for k,v in c2['values'].items()}
    cases=[]
    for sample in basis['pressure_sensitivity']:
        pressure=sample['pressure_MPa_g']
        modes=[('forward-held','closed',pressure,0),('reverse-check','check_closed',0,pressure),
               ('common-held','closed',pressure,pressure),('common-check','check_closed',pressure,pressure),
               ('forward-free-diagnostic','check_closed',pressure,0)]
        for mode,pose,pin,pout in modes:
            forces={name:pressure_force({side:row['axial_force_coefficient_N_per_MPa'] for side,row in data.items()},pin,pout) for name,data in areas['poses'][pose]['parts'].items()}
            row={'case':sample['id']+'/'+mode,'sample_kind':sample['kind'],'pose':pose,
                 'inlet_pressure_MPa_g':pin,'outlet_pressure_MPa_g':pout,'inlet_minus_outlet_MPa':pin-pout,
                 'disc_pressure_force_z_N':forces['disc_guide'],'stem_pressure_force_z_N':forces['stem'],
                 'actual_contact_reaction_N':None,'actual_drive_force_N':None,'engineering_acceptance':False}
            if pose=='check_closed':
                required=-forces['disc_guide']
                row.update({'pressure_only_equilibrium_seat_reaction_z_N':required,
                            'pressure_only_unilateral_contact':'NONNEGATIVE_SEAT_REACTION' if required>=0 else 'WOULD_REQUIRE_TENSILE_SEAT_REACTION',
                            'contact_note':'Pressure-only diagnostic omits gravity, friction, preload and dynamics; negative seat reaction cannot sustain a free closed state in this reduced model'})
            else:
                row.update({'pressure_only_equilibrium_seat_reaction_z_N':None,
                            'pressure_only_unilateral_contact':'TWO_CONTACT_REACTIONS_UNDETERMINED',
                            'contact_note':'Seat and screw contact reactions are not uniquely determined from net pressure force; seating preload/compliance/weight required'})
            cases.append(row)
    main_pressure=basis['selected_study_inputs']['internal_design_pressure']['value']
    f=next(r['disc_pressure_force_z_N'] for r in cases if r['case']=='selected-study/forward-held')
    thread=basis['thread_study'];collar=basis['collar_study'];drive=[]
    mean_collar_r=(collar['inner_d_mm']+collar['outer_d_mm'])/4
    for mu in thread['friction_coefficients']:
        screw=screw_model(f,thread['pitch_diameter_mm'],thread['lead_mm'],thread['axial_half_flank_angle_deg_assumed'],mu)
        for cmu in collar['friction_coefficients']:
            ct=f*cmu*mean_collar_r/1000;total=screw['thread_torque_Nm']+ct
            drive.append({'thread_mu_assumed':mu,'collar_mu_assumed':cmu,**screw,'collar_torque_Nm':ct,
                          'combined_model_torque_Nm':total,'handwheel_rim_force_N':total/(p['handwheel_od']/2000),
                          'load_used_N':f,'force_kind':'FORWARD_HYDRAULIC_COMPONENT_ONLY_NOT_FINAL_REQUIRED_THRUST'})
    root_area=math.pi*thread['nominal_external_root_d_mm']**2/4
    bearing_proxy=[{'engagement_scenario_mm':L,'uniform_projected_flank_area_mm2':math.pi*thread['pitch_diameter_mm']*L/2,
                    'uniform_mean_projected_flank_pressure_MPa':f/(math.pi*thread['pitch_diameter_mm']*L/2)} for L in thread['effective_engagement_lengths_mm']]
    joints=[]
    for candidate in c3['bonnet_joint_candidates']:
        v={k:r['value'] for k,r in candidate['values'].items()};low,high=v['gasket_id'],v['gasket_od']
        for label,diameter in [('inner-edge',low),('mid-annulus',(low+high)/2),('outer-edge',high)]:
            load=main_pressure*math.pi*diameter**2/4
            joints.append({'candidate':candidate['id'],'pressure_MPa_g':main_pressure,'effective_diameter_scenario':label,
                           'assumed_effective_pressure_diameter_mm':diameter,'pressure_separation_component_N':load,
                           'equal_count_division_N':load/candidate['bolt_count'],
                           'actual_bolt_load_N':None,'preload_N':None,'selected':False})
    return {'schema':'valve.c4-load-study/1.0','status':'PRESSURE_COMPONENT_AND_SENSITIVITY_STUDY',
            'reference_atmosphere_MPa_abs':basis['selected_study_inputs']['ambient_absolute_pressure']['value'],
            'pressure_convention':'Gauge-pressure increments relative to the assumed common external atmospheric baseline; reference atmospheric/contact prestress not solved',
            'cases':cases,'pressure_only_temperature_scope_C':[-2,20,50],
            'thermal_material_effects_evaluated':False,
            'drive_sensitivity':{'hydraulic_force_component_N':f,'rows':drive,'nominal_root_axial_component_MPa':f/root_area,
                                 'nominal_root_d_mm':thread['nominal_external_root_d_mm'],'nominal_root_is_minimum_manufactured_diameter':False,
                                 'uniform_thread_flank_proxy':bearing_proxy,
                                 'collar_effective_radius_mm':mean_collar_r,
                                 'seating_preload_packing_bearing_selection':'UNRESOLVED_NOT_ZERO_IN_FINAL_DESIGN',
                                 'auxiliary_wrench_45kgf_comparison':'NOT_MADE_DIFFERENT_APPLICATION_POINT_AND_MISSING_WRENCH_GEOMETRY',
                                 'limitations':['Coulomb quasistatic model; assumed friction is not measured and does not validate backdrive resistance under vibration',
                                                'Torque magnitudes concern motion against an opposing hydraulic-component load, not full actuator sizing',
                                                'Uniform flank area ignores first-thread concentration, wear, shear and actual engagement end effects',
                                                'Collar proxy is not a selected thrust bearing; its torque/load path requires integrated drive design']},
            'joint_pressure_diameter_sensitivity':joints,
            'joint_limit':'Effective sealing diameter is unknown; these are alternative pressure-load components, not pressure-joint acceptance, actual bolt force, gasket residual clamp or preload',
            'manufacturing_authorized':False,'solver_execution_performed':False}


def main():
    out=BASE/'T15/load_study.json'
    out.write_text(json.dumps({'status':'RUNNING','manufacturing_authorized':False}))
    try:
        paths={'basis':BASE/'T06/research_basis.json','pressure_areas':BASE/'T19/pressure_areas.json','parameters':BASE.parent/'C2/T11/parameters.json','interfaces':BASE.parent/'C3/T11/interface_candidates.json'}
        b,a,p,c=[json.loads(paths[k].read_text()) for k in ('basis','pressure_areas','parameters','interfaces')]
        validate(b)
        if a['extractor_sha256']!=sha(BASE/'T19/extract_pressure_faces.py') or a['parameters_sha256']!=sha(paths['parameters']):raise ValueError('Stale CAD pressure-area extraction')
        for relative,digest in a['input_asset_sha256'].items():
            if digest!=sha(BASE.parent/'C2/T12/out'/relative):raise ValueError('Changed pressure input asset')
        result=calculate(b,a,p,c);result['input_hashes']={name:sha(path) for name,path in paths.items()};result['calculator_sha256']=sha(Path(__file__))
        out.write_text(json.dumps(result,indent=2))
        for name,rows in [('load_cases',result['cases']),('drive_sensitivity',result['drive_sensitivity']['rows']),('joint_sensitivity',result['joint_pressure_diameter_sensitivity'])]:
            with (BASE/f'T15/{name}.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
        print(json.dumps({'status':result['status'],'cases':len(result['cases']),'drive_scenarios':len(result['drive_sensitivity']['rows']),'joint_scenarios':len(result['joint_pressure_diameter_sensitivity']),'primary_cases':[r for r in result['cases'] if r['case'].startswith('selected-study/')],'nominal_root_axial_MPa':result['drive_sensitivity']['nominal_root_axial_component_MPa']},indent=2))
    except Exception as exc:
        out.write_text(json.dumps({'status':'FAIL','error':str(exc),'manufacturing_authorized':False},indent=2));raise


if __name__=='__main__':main()
