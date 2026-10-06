#!/usr/bin/env python3
"""Independent arithmetic implementation of published mathematical correlations.

Sharqawy, Lienhard & Zubair (2010), DWT16:354–380, Eqs8,22,23.
Uses the rounded coefficients printed in the paper, not the MIT MATLAB code.
Only the 0–50 degC,30–40g/kg study window is implemented. P=0.101325MPa(abs).
No pressure correction and no below-zero extrapolation. This is study data.
"""
from pathlib import Path
import json,math,hashlib
P0=0.101325

REFERENCE_ROWS={(0,30):(1024.0,1.887e-3),(0,35):(1028.0,1.906e-3),(0,40):(1032.0,1.925e-3),
          (20,30):(1021.1,1.065e-3),(20,35):(1024.9,1.077e-3),(20,40):(1028.8,1.089e-3),
          (50,30):(1010.3,.587e-3),(50,35):(1014.0,.594e-3),(50,40):(1017.7,.602e-3)}

def rho_mu(T_C,S_g_kg,pressure_MPa_abs=P0):
    for value in (T_C,S_g_kg,pressure_MPa_abs):
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError("Property inputs must be finite non-boolean numbers")
    if not math.isclose(pressure_MPa_abs,P0,rel_tol=0,abs_tol=1e-12):raise ValueError("Pressure correction is not implemented; P0 properties only")
    if not 0 <= T_C <= 50: raise ValueError('outside study/property window0–50°C; do not extrapolate−2°C')
    if not 30 <= S_g_kg <= 40: raise ValueError('outside selected salinity study window30–40g/kg')
    t=T_C; s=S_g_kg/1000
    water=999.9 + .02034*t - .006162*t*t + 2.261e-5*t**3 - 4.657e-8*t**4
    dissolved=802*s - 2.001*s*t + .01677*s*t*t - 3.060e-5*s*t**3 - 1.613e-5*s*s*t*t
    rho=water+dissolved
    mu_water=4.2844e-5 + 1/(.157*(t+64.993)**2-91.296)
    factor=1+(1.541+.01998*t-9.52e-5*t*t)*s+(7.974-.07561*t+.0004724*t*t)*s*s
    mu=mu_water*factor
    return rho,mu,mu/rho

def validate_dataset(data):
    if data['status']!='EXPLICIT_ASSUMED_STUDY_COMPOSITION' or data['manufacturing_authorized'] is not False or data['temperature_scope_C']!=[0,50] or data['cold_endpoint_C']!=-2 or data['cold_endpoint_status']!='OUTSIDE_IMPLEMENTED_CORRELATION_DOMAIN_AND_PHASE_UNRESOLVED' or data['property_use_at_design_pressure']!='UNASSESSED_PRESSURE_DEPENDENCE_NOT_IMPLEMENTED':
        raise ValueError('Property dataset scope mismatch')
    if data['script_sha256']!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():raise ValueError('Stale property script provenance')
    rows=data['rows']
    if len(rows)!=len(REFERENCE_ROWS):raise ValueError('Property point count mismatch')
    seen=set()
    for row in rows:
        t,s=row['temperature_C'],row['reference_composition_salinity_g_kg']
        expected=rho_mu(t,s,row['reference_pressure_MPa_absolute'])
        point=(t,s)
        if point not in REFERENCE_ROWS or point in seen:raise ValueError('Unexpected or duplicated property point')
        seen.add(point)
        for key,value in zip(('density_kg_m3','dynamic_viscosity_Pa_s','kinematic_viscosity_m2_s'),expected):
            actual=row[key]
            if type(actual) not in (int,float) or not math.isfinite(actual) or actual<=0 or not math.isclose(actual,value,rel_tol=1e-12,abs_tol=1e-15):raise ValueError('Property value does not recompute: '+key)
        ref_rho,ref_mu=REFERENCE_ROWS[point]
        if row['reference_table_density_kg_m3']!=ref_rho or row['reference_table_viscosity_Pa_s']!=ref_mu:raise ValueError('Reference table value changed')
        if not abs(expected[0]-ref_rho)<.1 or not abs(expected[1]-ref_mu)<1e-6:raise ValueError('Reference table comparison failed')
        if row['actual_seawater_measurement'] is not False or row['pressure_correction_applied'] is not False:raise ValueError('Property applicability overclaimed')
    if seen!=set(REFERENCE_ROWS):raise ValueError('Missing property reference point')
    return {'property_arithmetic_gate':'PASS','reference_points':len(seen),'cold_endpoint':'HOLD','design_pressure_correction':'UNASSESSED'}

def main():
    dest=Path(__file__).with_name("seawater_study_cases.json")
    dest.write_text(json.dumps({"status":"RUNNING","manufacturing_authorized":False}))
    rows=[]
    # Reference values read from MIT2023 tables, printed p2 and p21.

    for t in [0,20,50]:
        for s in [30,35,40]:
            rho,mu,nu=rho_mu(t,s);rr,mm=REFERENCE_ROWS[t,s]
            # Rounded source table and independently rounded published coefficients.
            if not abs(rho-rr)<.1:raise ValueError(('Density reference mismatch',t,s,rho,rr))
            if not abs(mu-mm)<1e-6:raise ValueError(('Viscosity reference mismatch',t,s,mu,mm))
            rows.append({'temperature_C':t,'reference_composition_salinity_g_kg':s,
                         'reference_pressure_MPa_absolute':P0,'density_kg_m3':rho,
                         'dynamic_viscosity_Pa_s':mu,'kinematic_viscosity_m2_s':nu,
                         'reference_table_density_kg_m3':rr,'reference_table_viscosity_Pa_s':mm,
                         'source':'Sharqawy2010Eqs8,22,23; MIT2023tables2,21',
                         'actual_seawater_measurement':False,'pressure_correction_applied':False})
    try:rho_mu(-2,35)
    except ValueError: pass
    else:raise AssertionError('−2°C input must be rejected')
    data={'schema':'valve.seawater_study/1.0','status':'EXPLICIT_ASSUMED_STUDY_COMPOSITION',
          'salinity_status':'not supplied by drawing;35g/kg reference with30/40 sensitivity',
          'method':'Independent published equation arithmetic; no MATLAB source bundled',
          'pressure_scope':'P0=0.101325MPa(abs) only; property pressure dependence not evaluated',
          'temperature_scope_C':[0,50],'cold_endpoint_C':-2,'cold_endpoint_status':'OUTSIDE_IMPLEMENTED_CORRELATION_DOMAIN_AND_PHASE_UNRESOLVED',
          'density_correlation_accuracy_percent':0.14,'viscosity_correlation_accuracy_percent':1.5,
          'accuracy_note':'MIT table labels; not CFD prediction uncertainty or salinity uncertainty',
          'rows':rows,'validation':'9 cases match rounded primary tables within0.1kg/m³ and1e-6Pa·s; negativeT rejected',
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'manufacturing_authorized':False,'property_use_at_design_pressure':'UNASSESSED_PRESSURE_DEPENDENCE_NOT_IMPLEMENTED'}
    validate_dataset(data)
    dest=Path(__file__).with_name('seawater_study_cases.json');dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([r for r in rows if r['reference_composition_salinity_g_kg']==35],ensure_ascii=False,indent=2))
    print('PASS9 table crosschecks; cold guard')
if __name__=='__main__':main()
