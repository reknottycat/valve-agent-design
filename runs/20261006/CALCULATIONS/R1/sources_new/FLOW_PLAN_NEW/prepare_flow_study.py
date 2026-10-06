#!/usr/bin/env python3
"""Prepare explicit flow study assumptions and formula values; run no solver."""
import argparse,hashlib,importlib.util,json,math
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(repo,output):
 repo,output=Path(repo).resolve(),Path(output).resolve()
 if output.exists():raise ValueError('Use a new study-input file')
 property_code=repo/'runs/20261006/C4/T06/seawater_study.py';property_data=repo/'runs/20261006/C4/T06/seawater_study_cases.json'
 spec=importlib.util.spec_from_file_location('frozen_seawater',property_code);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.validate_dataset(json.loads(property_data.read_text()))
 basis_file=repo/'runs/20261006/C4/T06/research_basis.json';basis=json.loads(basis_file.read_text())
 if basis['target']['designation']!='522-35.4179' or basis['target']['selection']!='USER_SELECTED_UNSUFFIXED_BASE':raise ValueError('Unexpected target variant')
 params_file=repo/'runs/20261006/C2/T11/parameters.json';params=json.loads(params_file.read_text())['values']
 D=params['bore']['value']*.001
 if type(D) not in (float,int) or not math.isfinite(D) or D<=0:raise ValueError('Invalid nominal diameter')
 rho,mu,nu=module.rho_mu(20.,35.,.101325);area=math.pi*D**2/4
 cases=[]
 for label,speed,regime in [('laminar_diagnostic_Re10',10*nu/D,'LAMINAR_NUMERICAL_DIAGNOSTIC'),('speed_sensitivity_0_5',.5,'TURBULENCE_MODEL_AND_NEAR_WALL_VERIFICATION_REQUIRED'),('speed_sensitivity_1_0',1.,'TURBULENCE_MODEL_AND_NEAR_WALL_VERIFICATION_REQUIRED'),('speed_sensitivity_2_0',2.,'TURBULENCE_MODEL_AND_NEAR_WALL_VERIFICATION_REQUIRED')]:
  cases.append({'id':label,'status':'STUDY_ASSUMPTION_NOT_RUN','inlet_fixed_face_speed_m_s':speed,'nominal_D_Reynolds_from_face_speed':speed*D/nu,'nominal_circle_flow_m3_s':speed*area,'nominal_circle_flow_m3_h':speed*area*3600,'dynamic_pressure_from_face_speed_Pa':rho*speed**2/2,'regime_scope':regime,'actual_mesh_flux_m3_s':None,'computed_pressure_drop_Pa':None,'computed_loss_coefficient':None})
 data={'schema':'valve.c5-reexecution-flow-plan/1.0','status':'PLANNED_NOT_RUN','target':basis['target']['designation'],'manufacturing_authorized':False,
 'selected_study_property_state':{'temperature_C':20.,'salinity_g_kg':35.,'pressure_MPa_absolute':.101325,'density_kg_m3':rho,'dynamic_viscosity_Pa_s':mu,'kinematic_viscosity_m2_s':nu,'actual_duty_or_measurement':False,'pressure_correction_implemented':False,'minus_2C_phase_and_property_gate':'UNRESOLVED'},
 'nominal_diameter_m':D,'nominal_circle_area_m2':area,'cases':cases,
 'pose':{'disc_lift_mm':params['disc_max_lift']['value'],'stem_retraction_mm':params['stem_travel']['value'],'scope':'Fixed fully-open research geometry, treated as restrained for this CFD study; no prediction of spontaneous lift, force equilibrium, or closing behavior'},
 'domain':{'inlet_x_m':-3*D,'outlet_x_m':params['face_to_face']['value']*.001+3*D,'straight_extensions_each_DN':3,'scope':'Port-to-port pressure loss includes numerical straight extensions and developing/disturbed flow; not automatically the isolated-valve coefficient'},
 'pressure_interpretation':{'field':'simpleFoam p has dimensions m2/s2; multiply by rho for Pa','reference_outlet_kinematic_p':0,'reference_outlet_axis_absolute_pressure_Pa':101325.,'design_load_pressure_MPa_g':basis['selected_study_inputs']['internal_design_pressure']['value'],'scope':'0.63 MPa(g) is a separate structural study load, not an imposed flow pressure drop. The initial CFD property state remains the validated atmospheric reference. Explicit gravity is omitted from this constant-density flow equation; physical vertical pressure-force postprocessing needs a separately stated hydrostatic reconstruction and contact-wetting check.'},
 'formulas':{'Re':'U_face*D/nu','Q_nominal_m3_s':'U_face*pi*D^2/4','dynamic_pressure_Pa':'rho*U_face^2/2','measured_flow':'Use the actual outward-normal surface flux phi: Qin<0 and Qout>0','mass_imbalance':'abs(Qin+Qout)/max(abs(Qin),abs(Qout)); reject zero/nonfinite denominator','loss_coefficient_reporting':'Use a declared reference velocity Q_actual/(pi*D^2/4); distinguish static, total-pressure, port-to-port and pipe-corrected quantities'},
 'execution_prerequisites':['Current mesh files bound to a fresh full checkMesh PASS with all warnings retained','Independent native field/face probe verification','Nonzero-source Poisson verification on this valve domain and appropriate mesh/scheme sensitivity','Actual case input hashes, solver/library fingerprints before launch','Residual history, pressure-drop/flow stabilization, mass balance, finite/bounded fields and model-specific near-wall checks'],
 'drawing_note24_coefficient_limit_assessment':'UNASSESSED: governing test/tap and operating-flow conditions not established; no automatic <=6 pass from a port coefficient',
 'modeling_limits':['Study speeds are deliberate sensitivity values, not sourced rated product flow or user operating data','The Re10 held-open case is a numerical diagnostic, not expected natural valve operation','No coupled disc motion, water hammer, cavitation, leakage, thermal stress or pressure-dependent property validation','No source standard or manufacturer rating is inferred from solver convergence'],
 'sources':{'basis_sha256':sha(basis_file),'parameters_sha256':sha(params_file),'property_code_sha256':sha(property_code),'property_data_sha256':sha(property_data),'preparer_sha256':sha(__file__),
 'concept_documentation':'https://doc.openfoam.com/2306/tools/processing/solvers/rtm/incompressible/simpleFoam/','version_note':'Online overview is2306; actual1912 syntax must be verified against installed official examples and real executions, not assumed cross-version equivalent'}}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(data,indent=2,allow_nan=False));print(json.dumps(cases,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();build(a.repo,a.output)
