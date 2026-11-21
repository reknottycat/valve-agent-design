"""Size/identity/persistence gates for only new continuation outputs, never source checkpoint."""
from pathlib import Path
from window_contract import WindowContract
import os,stat,re,math
TOTAL=256*1024**2
PER_FILE=64*1024**2
MANDATORY={'U','p','phi','uniform/time','uniform/cumulativeContErr'}
OPTIONAL={'uniform/functionObjects/functionObjectProperties'}

def scan_outputs(case,bindings,contract,sha=None,require_complete=False,expected_stages=None):
    if not isinstance(contract, WindowContract):raise TypeError("explicit validated WindowContract required")
    source=contract.time_name(contract.start);outputs=tuple(contract.time_name(s) for s in contract.output_states)
    if require_complete:
        if expected_stages is None:raise ValueError("complete checkpoint scan requires actual native stages")
        written=expected_stages
        if type(written) is not dict or set(written)!=set(outputs):raise ValueError("native written stages require exact string state keys")
        for n,recorded in written.items():
            if type(recorded) is not dict or type(recorded.get("index")) is not int:raise ValueError("native written index invalid")
            cum=recorded.get("cumulativeContErr")
            if type(cum) not in (int,float) or not math.isfinite(cum):raise ValueError("native written cumulativeContErr invalid")
    case=Path(case);files={};dirs=[];errors=[];total=0
    for name in (source,'constant'):
        p=case/name
        if not p.is_symlink() or str(p.resolve())!=bindings[name]:errors.append('input symlink binding drift '+name)
    if (case/'system').is_symlink() or not (case/'system').is_dir():errors.append('system directory not owned real directory')
    tmp=case.parent/'tmp'
    if tmp.is_symlink() or not tmp.is_dir():errors.append('temporary output directory redirected/missing')
    stack=[p for p in case.iterdir() if p.name not in (source,'constant','system')]
    if tmp.is_dir() and not tmp.is_symlink():stack.extend(tmp.iterdir())
    while stack:
        p=stack.pop();rel=('@tmp/'+str(p.relative_to(tmp))) if p.is_relative_to(tmp) else str(p.relative_to(case))
        try:st=p.lstat()
        except FileNotFoundError:
            if require_complete:errors.append('output vanished during terminal scan '+rel)
            continue
        if stat.S_ISLNK(st.st_mode):errors.append('new output symlink '+rel);continue
        if stat.S_ISDIR(st.st_mode):
            dirs.append(rel)
            if len(dirs)>16:errors.append('too many new directories');break
            stack.extend(p.iterdir())
        elif stat.S_ISREG(st.st_mode):
            total+=st.st_size;files[rel]={'bytes':st.st_size}
            if st.st_size>PER_FILE:errors.append('per-file bytes exceeded '+rel)
            if len(files)>64:errors.append('too many new files');break
        else:errors.append('new output nonregular object '+rel)
        if rel.split('/',1)[0] not in (*outputs,'@tmp'):errors.append('unexpected new output root '+rel)
    if require_complete and any(k.startswith('@tmp/') for k in files):errors.append('temporary outputs remain at terminal state')
    if total>TOTAL:errors.append('total new outputs including partial/temp exceeded256MiB')
    states={}
    for n in outputs:
        p=case/n;present={k[len(n)+1:] for k in files if k.startswith(n+'/')};missing=sorted(MANDATORY-present);unexpected=sorted(present-MANDATORY-OPTIONAL)
        valid=p.is_dir() and not p.is_symlink() and not missing and not unexpected and all(files[n+'/'+k]['bytes']>0 for k in present)
        states[n]={'real_directory':p.is_dir() and not p.is_symlink(),'mandatory_missing':missing,'unexpected_files':unexpected,'complete_structure':valid}
        if require_complete:
            if not valid:errors.append('checkpoint incomplete/unsupported files '+n)
            else:
                time=(p/'uniform/time').read_text();cum=(p/'uniform/cumulativeContErr').read_text()
                for key,want in [('value',float(n)),('deltaT',contract.delta_t),('deltaT0',contract.delta_t0)]:
                    matches=re.findall(r'^\s*'+key+r'\s+([^;]+);',time,re.M)
                    if len(matches)!=1 or float(matches[0])!=want:errors.append('checkpoint time '+n+' '+key)
                ix=re.findall(r'^\s*index\s+([^;]+);',time,re.M)
                if len(ix)!=1 or not re.fullmatch(r'[0-9]+',ix[0].strip()):errors.append('checkpoint time index invalid '+n)
                else:
                    states[n]['native_time_index']=int(ix[0])
                    if int(ix[0])!=contract.index_for(int(n)):errors.append('checkpoint index differs from contract '+n)
                if re.findall(r'^\s*name\s+"?([^";\s]+)"?\s*;',time,re.M)!=[n]:errors.append('checkpoint time name '+n)
                vals=re.findall(r'^\s*value\s+([^;]+);',cum,re.M)
                if len(vals)!=1 or not math.isfinite(float(vals[0])):errors.append('checkpoint cumulativeContErr nonfinite/missing '+n)
                else:states[n]['cumulativeContErr']=float(vals[0])
                recorded=written[n]
                if states[n].get('native_time_index')!=recorded['index']:errors.append('checkpoint index differs from native written stage '+n)
                if states[n].get('cumulativeContErr')!=recorded['cumulativeContErr']:errors.append('checkpoint cumulativeContErr differs from native written stage '+n)
                for field,typ in [('U','volVectorField'),('p','volScalarField'),('phi','surfaceScalarField')]:
                    with (p/field).open('rb') as f:header=f.read(4096).decode('ascii',errors='strict')
                    if re.findall(r'\bclass\s+(\w+)\s*;',header)!=[typ]:errors.append('checkpoint field class '+n+'/'+field)
                    if re.findall(r'\bobject\s+(\w+)\s*;',header)!=[field]:errors.append('checkpoint field object '+n+'/'+field)
    if sha is not None and not errors:
        for rel,entry in files.items():entry['sha256']=sha(tmp/rel[5:] if rel.startswith('@tmp/') else case/rel)
    return {'total_new_file_bytes_including_partial':total,'total_limit_bytes':TOTAL,'per_file_limit_bytes':PER_FILE,'all_observed_files_hashed':sha is not None and not errors,'files':dict(sorted(files.items())),'new_directories':sorted(dirs),'states':states,'violations':errors,'complete':require_complete and not errors,'restart_qualified':False,'enforcement':'polling plus per-file RLIMIT_FSIZE and postcheck; no OS aggregate quota, transient overshoot not ruled out'}
