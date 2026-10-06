#!/usr/bin/env python3
"""Fresh revalidation of frozen v1 mesh copies. No mesh construction or flow solve."""
import sys
sys.dont_write_bytecode=True
import argparse,json,re,subprocess,uuid
from pathlib import Path
import meshio
import repair_mesh as repair
from audit_agglomeration import audit as audit_agglomeration
from binding import require,sha,snapshot,write_json,begin_report,audit_report

STAGES=['native_baseline','native_agglomerated','native_final','source_identity','agglomeration','patch_merge']

def native_check(root,name,case,expectation,run_id,env,binary):
    output=root/'stage_evidence'/f'{name}.json'; log=root/'stage_evidence'/f'{name}.log'
    report=begin_report(output,name,run_id)
    try:
        require(not log.exists(),'native log output must be fresh')
        before=snapshot(case); code=snapshot(root/'scripts'); executable=sha(binary); environment=sha(env)
        report.update(input_path=str(case),inputs_before=before,code_snapshot=code,binary=str(binary),binary_sha256=executable,environment_script=str(env),environment_script_sha256=environment)
        argv=['bash','-c','source "$1"; exec "$2" -case "$3" -allTopology -allGeometry','mesh-quality-revalidation',str(env),str(binary),str(case)]
        with log.open('w') as stream: result=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,check=False)
        after=snapshot(case); text=log.read_text()
        require(result.returncode==0,f'checkMesh exited {result.returncode}')
        require('OPENFOAM=1912 patch=200626' in text and '-allTopology -allGeometry' in text,'unexpected native version or arguments')
        require(not re.search(r'\bFATAL\b',text),'native FATAL')
        a,b=before['files'],after['files']; changed=[p for p in set(a)|set(b) if a.get(p)!=b.get(p)]
        require(all(p.startswith('constant/polyMesh/sets/') for p in changed),'checkMesh changed a mesh/system input')
        require(code==snapshot(root/'scripts') and sha(binary)==executable and sha(env)==environment,'checker/code changed during execution')
        mesh_ok=bool(re.search(r'^Mesh OK\.\s*$',text,re.M))
        if expectation=='mesh_ok': require(mesh_ok and not re.search(r'\bFailed\b',text),'final native mesh did not pass')
        elif expectation=='nine_determinant_failures': require(not mesh_ok and 'Failed 1 mesh checks.' in text and 'Cells with small determinant (< 0.001) found, number of cells: 9' in text,'baseline failure differs')
        elif expectation=='two_planar_failures': require(not mesh_ok and 'Failed 1 mesh checks.' in text and 'Concave cells (using face planes) found, number of cells: 2' in text,'intermediate failure differs')
        else: raise RuntimeError('unknown native expectation')
        report.update(status='PASS',inputs_after=after,core_inputs_unchanged=True,changed_diagnostic_set_files=sorted(changed),native_mesh_ok=mesh_ok,expectation=expectation,argv=argv,returncode=result.returncode,log_relative_path=str(log.relative_to(root)),log_sha256=sha(log))
        write_json(output,report); return report
    except BaseException as e:
        report.update(status='FAIL',error_type=type(e).__name__,error=str(e));write_json(output,report);raise

def run(root,env,binary):
    root=root.resolve(); run_id='revalidation-v2-'+uuid.uuid4().hex
    status=begin_report(root/'pipeline_status.json','fresh_revalidation',run_id)
    try:
        require(not (root/'revalidation_manifest.json').exists(),'manifest exists; require a new revalidation directory')
        require(not any((root/'stage_evidence').iterdir()),'stage evidence directory must be fresh')
        cases={k:root/'data'/k for k in ['baseline','agglomerated','final_candidate']}; source=root/'data/fluid_si.msh'
        require(sha(source)=='df5a517ff53b569a481315614d3cd4d8ba1662095fa3c7eeae96dd3cbd2430a3','wrong frozen source')
        native_check(root,'native_baseline',cases['baseline'],'nine_determinant_failures',run_id,env,binary)
        native_check(root,'native_agglomerated',cases['agglomerated'],'two_planar_failures',run_id,env,binary)
        native_check(root,'native_final',cases['final_candidate'],'mesh_ok',run_id,env,binary)
        def identity():
            gm=meshio.read(source)
            return repair.source_identity(repair.read_mesh(cases['baseline']),gm.points,gm.cells_dict['tetra'],gm.cells_dict['triangle'],gm.cell_data_dict['gmsh:physical']['triangle'],gm.field_data)
        audit_report('source_identity',root/'stage_evidence/source_identity.json',{'source':source,'baseline':cases['baseline']},identity,run_id)
        audit_report('agglomeration',root/'stage_evidence/agglomeration.json',{'baseline':cases['baseline'],'candidate':cases['agglomerated']},lambda:audit_agglomeration(cases['baseline'],cases['agglomerated']),run_id)
        audit_report('patch_merge',root/'stage_evidence/patch_merge.json',{'before':cases['agglomerated'],'after':cases['final_candidate']},lambda:repair.verify_patch_merge(repair.read_mesh(cases['agglomerated']),repair.read_mesh(cases['final_candidate'])),run_id)
        manifest={'schema':'valve-mesh-revalidation-seal-v2','run_id':run_id,'statement':'Fresh current revalidation; does not claim bindings were collected during v1 historical operations','stage_names':STAGES,'directory_snapshots':{n:snapshot(root/n) for n in ['data','scripts','tests','stage_evidence']},'sealed_inputs':{**{k:snapshot(p) for k,p in cases.items()},'source':snapshot(source)},'baseline_archive_sha256':'23e8105fad661a0f8dedc4dff78a4ccc57f1c848ea59a0ef3fd841dbcf8d3113','scope':'Mesh checks and geometry audits only; no flow solve or manufacturing approval'}
        write_json(root/'revalidation_manifest.json',manifest)
        digest=sha(root/'revalidation_manifest.json');(root/'manifest_sha256.txt').write_text(digest+'  revalidation_manifest.json\n')
        status.update(status='PASS',manifest_sha256=digest,run_id=run_id);write_json(root/'pipeline_status.json',status)
        print('Fresh revalidation sealed. Supply this exact digest to finalization: '+digest,flush=True)
    except BaseException as e:
        status.update(status='FAIL',error_type=type(e).__name__,error=str(e));write_json(root/'pipeline_status.json',status);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--env',required=True);p.add_argument('--checkmesh',required=True);a=p.parse_args()
    run(Path(a.root),Path(a.env),Path(a.checkmesh))
