#!/usr/bin/env python3
"""Fail-closed evidence binding. Every public report begins RUNNING, ends PASS/FAIL."""
import datetime,hashlib,json,os,uuid
from pathlib import Path

class BindingError(RuntimeError): pass

def require(test,message):
    if not test: raise BindingError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def write_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    tmp.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n'); os.replace(tmp,path)

def snapshot(path):
    path=Path(path)
    require(path.exists(),f'missing input: {path}')
    require(not path.is_symlink(),f'symlink input forbidden: {path}')
    if path.is_file(): return {'kind':'file','sha256':sha(path),'bytes':path.stat().st_size}
    require(path.is_dir(),f'not a regular file/directory: {path}')
    files={}; directories=[]
    for p in sorted(path.rglob('*')):
        if '__pycache__' in p.parts: continue
        require(not p.is_symlink(),f'symlink input forbidden: {p}')
        rel=p.relative_to(path).as_posix()
        if p.is_dir(): directories.append(rel)
        elif p.is_file(): files[rel]={'sha256':sha(p),'bytes':p.stat().st_size}
        else: raise BindingError(f'nonregular input: {p}')
    return {'kind':'directory','directories':directories,'files':files}

def begin_report(output,operation,run_id):
    output=Path(output)
    if output.exists():
        old=output.read_bytes(); backup=output.parent/'superseded_reports'/f'{output.name}.{hashlib.sha256(old).hexdigest()}.json'
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists(): backup.write_bytes(old)
    report={'schema':'valve-mesh-evidence-v2','operation':operation,'run_id':run_id,'attempt_id':uuid.uuid4().hex,'status':'RUNNING','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(output,report)
    return report

def audit_report(operation,output,input_paths,compute,run_id=None):
    report=begin_report(output,operation,run_id or 'standalone-'+uuid.uuid4().hex)
    try:
        resolved={k:Path(p).resolve() for k,p in input_paths.items()}
        for p in resolved.values():
            require(not Path(output).resolve().is_relative_to(p),'report must be outside input tree')
        before={k:snapshot(p) for k,p in resolved.items()}
        code=snapshot(Path(__file__).parent)
        report['input_paths']={k:str(p) for k,p in resolved.items()}; report['inputs_before']=before; report['code_snapshot']=code
        result=compute()
        after={k:snapshot(p) for k,p in resolved.items()}
        require(before==after,'input changed during geometry audit')
        require(code==snapshot(Path(__file__).parent),'audit code changed during execution')
        report.update(status='PASS',inputs_after=after,result=result)
        write_json(output,report); return report
    except BaseException as e:
        report.update(status='FAIL',error_type=type(e).__name__,error=str(e))
        write_json(output,report)
        raise
