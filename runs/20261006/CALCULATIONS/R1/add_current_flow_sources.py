from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parent;F=Path('/workspace/shared/valve-cfd-rebuilt-20261006');M=Path('/workspace/shared/valve-mesh-repair-rebuilt-20261006')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((F/'evidence/flow_study_plan.json').read_text());acc=json.loads((M/'evidence/acceptance.json').read_text())
if plan['status']!='PLANNED_NOT_RUN' or plan['manufacturing_authorized'] is not False:raise RuntimeError('Plan state changed; inspect before accepting')
for row in plan['cases']:
 for k in ['actual_mesh_flux_m3_s','computed_pressure_drop_Pa','computed_loss_coefficient']:
  if row[k] is not None:raise RuntimeError('Plan contains execution value; requires separate review')
if sha(F/'scripts/prepare_flow_study.py')!=plan['sources']['preparer_sha256']:raise RuntimeError('Plan script binding')
for key,rel in [('basis_sha256','C4/T06/research_basis.json'),('parameters_sha256','C2/T11/parameters.json'),('property_code_sha256','C4/T06/seawater_study.py'),('property_data_sha256','C4/T06/seawater_study_cases.json')]:
 if sha(R/'sources'/rel)!=plan['sources'][key]:raise RuntimeError('Plan frozen input binding '+key)
for name,dig in acc['final_mesh_hashes'].items():
 if sha(M/'cases/final_candidate/constant/polyMesh'/name)!=dig:raise RuntimeError('New mesh binding '+name)
if sha(M/'evidence/checkMesh.final.log')!=acc['final_native_check_sha256']:raise RuntimeError('Raw checkMesh binding')
if sha(F/'cases/exact_hxt12/fluid_si.msh')!=acc['source_sha256']:raise RuntimeError('Actual Gmsh source binding')
manifest=json.loads((R/'new_source_manifest.json').read_text());old={x['path']:x for x in manifest['files']}
spec=[('FLOW_PLAN_NEW/flow_study_plan.json',F/'evidence/flow_study_plan.json'),('FLOW_PLAN_NEW/prepare_flow_study.py',F/'scripts/prepare_flow_study.py')]
for name in ['acceptance.json','agglomeration_identity.json','patch_merge_identity.json','source_identity.json','build_provenance.json','tests.normal.log','tests.optimized.log','checkMesh.final.log']:
 spec.append(('MESH_REPAIR_NEW/'+name,M/'evidence'/name))
for rel,src in spec:
 dst=R/'sources_new'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 old[rel]={'path':rel,'source':str(src),'sha256':sha(dst),'bytes':dst.stat().st_size}
manifest['files']=list(old.values());(R/'new_source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(R/'verification/current_flow_source_bindings.json').write_text(json.dumps({'passed':True,'plan_only':True,'plan_output_values_all_null':True,'current_mesh_files_match_new_acceptance':True,'mesh_native_log_sha256':acc['final_native_check_sha256'],'not_a_PDE_or_flow_acceptance':True},indent=2)+'\n')
print('Bound and copied',len(spec),'current planning and mesh files')
