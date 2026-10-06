from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parent;S=Path('/workspace/shared/valve-disc-rebuilt-20261006');P=Path('/workspace/shared/valve-solvers-rebuilt-20261006/poisson-newrun')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((S/'summary.json').read_text())
if summary['old_solver_data_restored'] is not False or len(summary['rows'])!=6:raise RuntimeError('Fresh structural source scope invalid')
checks=[];snap=[]
def copy(src,rel):
 dst=R/'sources_new'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 snap.append({'path':rel,'source':str(src),'sha256':sha(dst),'bytes':dst.stat().st_size})
for row in summary['rows']:
 name=f"disc_h{row['target_h_mm']}_{row['order']}";c=S/'cases'/name;mp=c/'FROZEN_MANIFEST.json'
 if sha(mp)!=row['manifest_sha256']:raise RuntimeError('Manifest mismatch '+name)
 mm=json.loads(mp.read_text())
 for fn,digest in mm['files'].items():
  if sha(c/fn)!=digest:raise RuntimeError('Frozen structural bytes changed '+name+'/'+fn)
 for fn in ['model.json','run.json','results.json','FROZEN_MANIFEST.json']:
  copy(c/fn,'STRUCTURAL_NEW/cases/'+name+'/'+fn)
 result=json.loads((c/'results.json').read_text());run=json.loads((c/'run.json').read_text());model=json.loads((c/'model.json').read_text())
 if run['input_sha256']!=sha(c/'disc.inp') or run['solver_script_sha256']!=sha(c/'solver_script_snapshot.py'):raise RuntimeError('Run/script/input chain '+name)
 for key,digest in result['raw_input_output_binding'].items():
  if sha(c/key)!=digest:raise RuntimeError('Raw result binding '+name+'/'+key)
 for sr in model['sources'].values():
  if sha(Path(sr['path']))!=sr['sha256']:raise RuntimeError('Upstream source binding '+sr['path'])
 checks.append({'case':name,'manifest_sha256':sha(mp),'frozen_files_verified':len(mm['files']),'run_utc':run['fresh_run_utc'],'raw_DAT_sha256':sha(c/'disc.dat'),'source_and_run_hashes_match':True})
for fn in ['summary.json','summary.csv','README.md','scripts/structural.py','scripts/freeze.py','scripts/summarize.py','evidence/persisted_source_index.json','evidence/fresh_case_gate_tests.json','evidence/extra_tampering_tests.json','evidence/source_gate_tests.json','fresh_mesh_sensitivity.png']:
 copy(S/fn,'STRUCTURAL_NEW/'+fn)
for order in ['C3D4','C3D10']:
 name='pressure_patch_'+order;c=S/'cases'/name
 fr=json.loads((S/'evidence'/(name+'_freeze.json')).read_text())
 mp=c/'FROZEN_MANIFEST.json'
 if sha(mp)!=fr['manifest_sha256']:raise RuntimeError('Patch frozen manifest '+name)
 mm=json.loads(mp.read_text())
 for fn,digest in mm['files'].items():
  if sha(c/fn)!=digest:raise RuntimeError('Patch frozen bytes '+name+'/'+fn)
 for fn in ['model.json','run.json','results.json','FROZEN_MANIFEST.json']:
  copy(c/fn,'STRUCTURAL_NEW/cases/'+name+'/'+fn)
 checks.append({'case':name,'manifest_sha256':sha(mp),'frozen_files_verified':len(mm['files']),'fresh_patch_verified':True})
poisson=json.loads((P/'results.json').read_text())
for rr in poisson['records']:
 c=P/rr['case']
 for fn,digest in rr['input_hashes'].items():
  if sha(c/fn)!=digest:raise RuntimeError('Poisson input hash '+rr['case']+'/'+fn)
 if sha(c/rr['latest_time']/'T')!=rr['T_file_sha256']:raise RuntimeError('Poisson solved T mismatch')
 for fn in ['reference.json','log.laplacianFoam','log.checkMesh','constant/fvOptions','constant/transportProperties','system/fvSchemes','system/fvSolution']:
  copy(c/fn,'POISSON_NEW/'+rr['case']+'/'+fn)
 checks.append({'case':rr['case'],'inputs_verified':len(rr['input_hashes']),'solved_T_sha256':rr['T_file_sha256'],'analytic_target_match':rr['matches_positive_analytic_target']})
for fn in ['results.json','README.zh-CN.md','source-excerpts/createFields.H','source-excerpts/laplacianFoam.C','source-excerpts/SemiImplicitSource.C']:
 copy(P/fn,'POISSON_NEW/'+fn)
for fn in ['poisson_prepare.py','poisson_verify.py']:
 copy(P.parent/'scripts'/fn,'POISSON_NEW/scripts/'+fn)
(R/'verification/fresh_source_hash_bindings.json').write_text(json.dumps({'passed':True,'old_lost_R1_reused':False,'checks':checks},ensure_ascii=False,indent=2)+'\n')
(R/'new_source_manifest.json').write_text(json.dumps({'fresh_only':True,'files':snap},ensure_ascii=False,indent=2)+'\n')
print('Fresh frozen sources checked; copied',len(snap),'files')
