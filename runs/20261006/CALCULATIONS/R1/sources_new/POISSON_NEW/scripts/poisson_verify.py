"""Independent analytic/flux checks of a real stock laplacianFoam solve."""
from pathlib import Path
import re,json,math,hashlib,datetime
root=Path(__file__).resolve().parents[1]
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
records=[]
for label in ['n5_right','n10_right','n5_wrong_sign']:
 case=root/'poisson-newrun'/label;ref=json.loads((case/'reference.json').read_text());
 need('internalField uniform 0;' in (case/'0/T').read_text(),'Initial internal field must be zero')
 opts=(case/'constant/fvOptions').read_text();need('selectionMode all;' in opts and 'volumeMode specific;' in opts and f'T ({ref["fvOptions_Su"]} 0);' in opts,'Unexpected analytic-source option settings')
 need('DT [0 2 -1 0 0 0 0] 1;' in (case/'constant/transportProperties').read_text(),'DT must be exactly one m2/s')
 log=(case/'log.laplacianFoam').read_text();need('SIMPLE solution converged' in log and re.search(r'^End\s*$',log,re.M) and 'FOAM FATAL' not in log,'No converged solve')
 times=[p for p in case.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name)];latest=max(times,key=lambda p:float(p.name));text=(latest/'T').read_text();m=re.search(r'internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
 need(bool(m),'Missing solved internal field');T=[float(x) for x in m[2].split()];need(len(T)==int(m[1])==ref['cell_count'],'field count')
 exact=[sum(v*v for v in c) for c in ref['C']];errors=[t-e for t,e in zip(T,exact)];need(all(math.isfinite(v) for v in T),'nonfinite solution')
 l2=math.sqrt(math.fsum(e*e*ref['V'] for e in errors));linf=max(map(abs,errors));faceflux=[(f['T_boundary']-T[f['owner']])*f['area']/f['normal_distance'] for f in ref['boundary_faces']];q=math.fsum(faceflux);target=6.0;source=-ref['fvOptions_Su']
 residuals=[{'initial':float(a),'final':float(b),'iterations':int(c)} for a,b,c in re.findall(r'Solving for T, Initial residual = ([-+\d.eE]+), Final residual = ([-+\d.eE]+), No Iterations (\d+)',log)]
 need(residuals and residuals[0]['initial']>.1 and sum(v['iterations'] for v in residuals)>0 and residuals[-1]['final']<1e-11,'Residual or actual-solve gate failed')
 need(abs(q-source)<1e-8,'Discrete boundary/source balance failed')
 target_pass=abs(q-target)<1e-8 and l2<.02
 if label.endswith('right'):need(target_pass,'Positive case failed analytic target')
 else:need(not target_pass and l2>.1 and q<0,'Wrong-sign negative case was not rejected')
 records.append({'case':label,'n':ref['n'],'cells':ref['cell_count'],'latest_time':latest.name,'initial_field':'uniform zero','analytic_target_laplacian':6,'fvOptions_Su':ref['fvOptions_Su'],'l2_temperature_error_K':l2,'linf_temperature_error_K':linf,'mean_error_K':math.fsum(errors)/len(errors),'numerical_outward_diffusive_gradient_flux_K_m3_per_s':q,'volume_source_for_DeltaT_equation_K_m3_per_s':source,'analytic_target_volume_source_K_m3_per_s':target,'balance_error':q-source,'matches_positive_analytic_target':target_pass,'linear_solver_calls':residuals,'linear_iterations_total':sum(v['iterations'] for v in residuals),'nonorthogonal_correctors':2,'mesh_nonorthogonality':'0 degrees, verified checkMesh','source_from_discrete_exact_field':False,'T_file_sha256':hashlib.sha256((latest/'T').read_bytes()).hexdigest(),'input_hashes':{str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['system','constant','0'] for p in (case/d).rglob('*') if p.is_file()}})
p0,p1=records[:2];ratio=p0['l2_temperature_error_K']/p1['l2_temperature_error_K'];order=math.log(ratio,2);need(3.5<ratio<4.5,'Refinement convergence not approximately second order')
report={'status':'STOCK_LAPLACIANFOAM_PDE_MMS_PASSED_ON_INDEPENDENT_CUBES','fresh_run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'records':records,'refinement_error_ratio':ratio,'observed_two_level_order':order,'equation_sign':'Native steady equation is -div(DT grad T)=Su; DT=1 and Su=-6 give DeltaT=+6','boundary':'Exact analytic T=x^2+y^2+z^2 evaluated at each planar face centre; internal initial T=0','flux_method':'Independent orthogonal cube half-cell finite-volume flux from solved T, exact face value, face area and normal distance. Not a generic nonorthogonal flux implementation.','scope':['Real native PDE solve; no manufactured discrete source','Only orthogonal independent unit cubes at 5^3 and 10^3','Source sign negative case converges numerically but is rejected against analytic target','Does not validate valve domain, nonorthogonal boundary consistency, or manufacturing release']}
(root/'poisson-newrun/results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2));print(json.dumps([{k:v for k,v in r.items() if k not in ['input_hashes','linear_solver_calls']} for r in records],indent=2))
