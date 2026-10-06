"""C4 selected study inputs remain distinct from controlled operating/rated values."""
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REQUIRED_UNKNOWN = {'actual_operating_pressure_MPa','manufacturer_rating_MPa','physical_proof_pressure_MPa','transient_time_history','selected_part_materials','material_allowable_stresses_MPa','seating_preload_N','packing_friction_N','thread_tolerance_class','bolt_preload_N','gasket_material','applicable_classification'}


def number(value, label, minimum=0, strict=False):
    if type(value) not in (float,int) or not math.isfinite(value) or value < minimum or (strict and value == minimum):
        raise ValueError('Invalid numeric value: '+label)
    return value


def validate(basis, check_files=True):
    if basis['schema'] != 'valve.c4-study-basis/1.0' or basis['status'] != 'SELECTED_BASE_STUDY_NOT_PRODUCT_RATING':
        raise ValueError('Unsupported research basis')
    target = basis['target']
    if target['designation'] != '522-35.4179' or target['medium'] != 'seawater' or target['service_temperature_C'] != [-2,50]:
        raise ValueError('Base-variant source applicability drift')
    if set(basis['unresolved']) != REQUIRED_UNKNOWN or any(v is not None for v in basis['unresolved'].values()):
        raise ValueError('Unknown rating/material/test values must remain explicit and unresolved')
    if set(basis['release']) != {'manufacturing_authorized','engineering_acceptance','solver_execution_allowed','github_write_allowed'} or any(v is not False for v in basis['release'].values()):
        raise ValueError('Study calculation cannot authorize engineering release or paused operations')
    conversion = basis['pressure_unit_conversion']
    if conversion['catalog_unit'] != 'kgf/cm2' or not math.isclose(number(conversion['kgf_cm2_to_MPa'],'kgf conversion',strict=True),.0980665,rel_tol=0,abs_tol=1e-12):
        raise ValueError('Pressure unit conversion mismatch')
    if not math.isclose(number(conversion['catalog_converted_MPa'],'catalog pressure',strict=True),number(conversion['catalog_value'],'catalog marking',strict=True)*.0980665,rel_tol=1e-12):
        raise ValueError('Catalog physical conversion mismatch')
    required={'internal_design_pressure':('MPa(g)',.63),'maximum_static_closure_differential':('MPa',.63),'ambient_absolute_pressure':('MPa(abs)',.101325),'salinity':('g/kg',35.)}
    for key,(unit,value) in required.items():
        row=basis['selected_study_inputs'][key]
        if row['unit'] != unit or row['kind'] != 'STUDY_ASSUMPTION' or not math.isclose(number(row['value'],key,strict=True),value,rel_tol=1e-12):
            raise ValueError('Explicit selected study input drift '+key)
    expected_kinds=['CONDITIONAL_UNIT_INTERPRETATION','ANALOG_NOMINAL_UNIT_CONVERSION','STUDY_ASSUMPTION','OVERLOAD_SENSITIVITY_NOT_PROOF_TEST']
    rows=basis['pressure_sensitivity']
    if len(rows)!=4 or len({r['id'] for r in rows})!=4 or [r['kind'] for r in rows]!=expected_kinds:
        raise ValueError('Missing/duplicated/mislabeled pressure sensitivity')
    for r,e in zip(rows,[6*.0980665,6.3*.0980665,.63,1.]):
        if not math.isclose(number(r['pressure_MPa_g'],'pressure',strict=True),e,rel_tol=1e-12):
            raise ValueError('Uncontrolled pressure sample')
    t=basis['thread_study'];c=basis['collar_study']
    for key in ['pitch_diameter_mm','nominal_external_root_d_mm','nominal_internal_root_d_mm','nominal_internal_major_d_mm','lead_mm']:
        number(t[key],key,strict=True)
    if not t['nominal_external_root_d_mm'] < t['nominal_internal_root_d_mm'] < t['pitch_diameter_mm'] < t['nominal_internal_major_d_mm']:
        raise ValueError('Thread radial nesting invalid')
    if type(t['starts_assumed']) is not int or t['starts_assumed'] != 1 or not 0<number(t['axial_half_flank_angle_deg_assumed'],'half-angle')<45:
        raise ValueError('Unsupported thread lead/profile')
    for row in [t,c]:
        if not row['friction_coefficients']:
            raise ValueError('Missing friction study')
        for mu in row['friction_coefficients']:
            if number(mu,'friction')>=1:raise ValueError('Unsupported friction')
    if not 0<number(c['inner_d_mm'],'collar inner',strict=True)<number(c['outer_d_mm'],'collar outer',strict=True):
        raise ValueError('Collar nesting invalid')
    for length in t['effective_engagement_lengths_mm']:number(length,'engagement',strict=True)
    if check_files:
        required_paths={'../C2/T11/parameters.json','../C2/artifact_manifest.json','../C3/T11/interface_candidates.json','../C3/artifact_manifest.json'}
        if set(basis['input_hashes'])!=required_paths:raise ValueError('Missing inherited source pin')
        for path,digest in basis['input_hashes'].items():
            if hashlib.sha256((BASE/path).read_bytes()).hexdigest()!=digest:raise ValueError('Changed inherited input '+path)
    return {'study_input_gate':'PASS','basis_class':'EXPLICIT_STUDY_ASSUMPTIONS','manufacturing_authorized':False}


if __name__=='__main__':
    print(json.dumps(validate(json.loads((BASE/'T06/research_basis.json').read_text())),indent=2))
