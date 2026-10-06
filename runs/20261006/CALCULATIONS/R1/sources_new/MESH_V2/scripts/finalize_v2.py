#!/usr/bin/env python3
"""Verify a caller-pinned immutable revalidation seal; never refresh evidence hashes."""
import sys
sys.dont_write_bytecode=True
import argparse,json,re
from pathlib import Path
from binding import require,sha,snapshot,write_json,begin_report

STAGES=['native_baseline','native_agglomerated','native_final','source_identity','agglomeration','patch_merge']

def finalize(manifest_path,expected_sha,output):
    manifest_path=Path(manifest_path); root=manifest_path.parent
    report=begin_report(output,'verify_frozen_revalidation','pending-seal-verification')
    try:
        require(bool(re.fullmatch(r'[0-9a-f]{64}',expected_sha)),'caller-pinned manifest SHA256 required')
        require(sha(manifest_path)==expected_sha,'revalidation manifest differs from caller-pinned digest')
        manifest=json.loads(manifest_path.read_text())
        require(manifest.get('schema')=='valve-mesh-revalidation-seal-v2','wrong manifest schema')
        require(manifest.get('stage_names')==STAGES,'required fresh stages missing')
        require(set(manifest.get('directory_snapshots',{}))=={'data','scripts','tests','stage_evidence'},'incomplete sealed directories')
        for directory,expected in manifest['directory_snapshots'].items():
            require(snapshot(root/directory)==expected,f'frozen input/code/evidence changed: {directory}')
        reports={}
        for stage in STAGES:
            r=json.loads((root/'stage_evidence'/f'{stage}.json').read_text()); reports[stage]=r
            require(r.get('status')=='PASS' and r.get('run_id')==manifest['run_id'],f'failed or foreign stage: {stage}')
            require(r.get('operation')==stage,f'wrong operation: {stage}')
            require(r.get('code_snapshot')==manifest['directory_snapshots']['scripts'],f'stage/code mismatch: {stage}')
        roles={'native_baseline':'baseline','native_agglomerated':'agglomerated','native_final':'final_candidate'}
        for stage,role in roles.items():
            r=reports[stage]
            require(r['inputs_after']==manifest['sealed_inputs'][role],f'native check not bound to frozen {role}')
            require(r.get('core_inputs_unchanged') is True,f'native checker modified {role}')
            require(r.get('returncode')==0,f'checker did not complete: {stage}')
            require(r['argv'][-1].endswith('/data/'+role) and '-allTopology -allGeometry' in r['argv'][2],f'wrong native arguments: {stage}')
            log=root/r['log_relative_path'];require(sha(log)==r['log_sha256'],f'checker log replaced: {stage}')
        require(reports['native_final'].get('native_mesh_ok') is True,'final native check not Mesh OK')
        require(reports['native_baseline'].get('native_mesh_ok') is False and reports['native_agglomerated'].get('native_mesh_ok') is False,'historical failure revalidation missing')
        txt=(root/reports['native_final']['log_relative_path']).read_text()
        require(re.search(r'^Mesh OK\.\s*$',txt,re.M) is not None and not re.search(r'\bFailed\b|\bFATAL\b',txt),'native final log not clean Mesh OK')
        maps={'source_identity':{'source':'source','baseline':'baseline'},'agglomeration':{'baseline':'baseline','candidate':'agglomerated'},'patch_merge':{'before':'agglomerated','after':'final_candidate'}}
        for stage,mapping in maps.items():
            r=reports[stage]; require(r['inputs_before']==r['inputs_after'],f'audit input changed: {stage}')
            require(set(r['inputs_after'])==set(mapping),f'audit inputs incomplete: {stage}')
            for name,role in mapping.items(): require(r['inputs_after'][name]==manifest['sealed_inputs'][role],f'audit not bound to frozen input: {stage}/{role}')
        # Acceptance identifies the pre-bound manifest, not freshly inventoried mesh hashes.
        report.update(status='PASS',run_id=manifest['run_id'],acceptance='FROZEN_MESH_REVALIDATION_VERIFIED',manifest_sha256=expected_sha,mesh_hashes=manifest['sealed_inputs']['final_candidate']['files'],scope=manifest['scope'],warning='54 faces above 70 degrees remain; maximum 77.471484007812791 degrees. No valve-flow or manufacturing approval.')
        write_json(output,report);return report
    except BaseException as e:
        report.update(status='FAIL',error_type=type(e).__name__,error=str(e));write_json(output,report);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    r=finalize(a.manifest,a.manifest_sha256,a.output);print(json.dumps({'status':r['status'],'manifest_sha256':r['manifest_sha256']},indent=2))
