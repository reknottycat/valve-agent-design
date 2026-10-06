#!/usr/bin/env python3
"""New-manifest creation is separate from READ-ONLY frozen numerical verification."""
import argparse,hashlib,json,pathlib
import numpy as np
import structural as s

def create(case,manifest):
    s.need(not manifest.exists(),'Refusing to overwrite an immutable manifest')
    # Creation is explicitly not verification. Caller must retain the returned binding.
    files={str(p.relative_to(case)):s.sha(p) for p in sorted(case.rglob('*')) if p.is_file() and p!=manifest and '__pycache__' not in p.parts}
    obj=dict(schema='disc_frozen_manifest/1',files=files,creation_only_not_verification=True)
    with manifest.open('x') as f:f.write(json.dumps(obj,indent=2)+'\n')
    return dict(action='CREATED_NEW_IMMUTABLE_MANIFEST',manifest=str(manifest),manifest_sha256=s.sha(manifest),files=len(files))

def verify(case,manifest,expected):
    s.need(s.sha(manifest)==expected,'Immutable manifest binding mismatch; rebaselining refused')
    data=json.loads(manifest.read_text());s.need(isinstance(data.get('files'),dict),'Invalid manifest')
    for rel,wanted in data['files'].items():
        p=pathlib.Path(rel);s.need(not p.is_absolute() and '..' not in p.parts,'Unsafe manifest path');target=case/p;s.need(target.is_file() and s.sha(target)==wanted,'Frozen file hash mismatch: '+rel)
    run=json.loads((case/'run.json').read_text());s.need(s.sha(case/'solver_script_snapshot.py')==run['solver_script_sha256'],'Historical solver script snapshot does not match run')
    fresh,arrays=s.calculate(case);cached=json.loads((case/'results.json').read_text());s.need(cached.get('passed_integrity') is True,'Cached result is not accepted')
    s.need(cached['raw_input_output_binding']==fresh['raw_input_output_binding'],'Cache binding does not match raw INP/DAT/model/run')
    for key in ('maximum_nodal_displacement_mm','strain_energy_Nmm','half_external_work_Nmm','raw_von_mises_peak_MPa','force_equilibrium_relative_error'):
        s.need(abs(cached[key]-fresh[key])<1e-11,'Raw reparse differs from cached metric: '+key)
    old=np.load(case/'solution.npz')
    for key,value in arrays.items():s.need(np.array_equal(old[key],value),'Raw reparse differs from solution cache: '+key)
    return dict(passed=True,read_only=True,manifest_regenerated=False,manifest_sha256=expected,files_verified=len(data['files']),raw_DAT_reparsed=True,solver_script_sha256=run['solver_script_sha256'],checker_sha256=s.sha(pathlib.Path(__file__)),postprocessor_sha256=s.sha(pathlib.Path(s.__file__)),fresh_checks=fresh)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create','verify']);p.add_argument('case');p.add_argument('--manifest',default='FROZEN_MANIFEST.json');p.add_argument('--expected-sha256');a=p.parse_args();case=pathlib.Path(a.case).resolve();manifest=case/a.manifest
    if a.action=='create':result=create(case,manifest)
    else:s.need(a.expected_sha256 is not None,'Verification requires an externally retained manifest SHA');result=verify(case,manifest,a.expected_sha256)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
