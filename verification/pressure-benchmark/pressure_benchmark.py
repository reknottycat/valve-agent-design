"""Kaggle CPU, Foundation v11. Analytic pipe and nozzle only; SI units."""
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from mesh_axis import generate
from prepare_case import build, write
from set_wedge_patches import convert

RHO, NU, U, D, LENGTH = 1000., .001, .05, .2, 1.8
TOL = dict(pipe_error=.03, imbalance=.001, flux_error=.001, dp_span=.005)


def run(cmd, cwd, log, of=False):
    if of:
        cmd = ['bash', '-c', 'source /opt/openfoam11/etc/bashrc >/dev/null && exec "$@"', 'foam', *cmd]
    with log.open('w') as f:
        rc = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        raise RuntimeError(f'{cmd[-1]} failed ({rc}): {log.read_text(errors="replace")[-2200:]}')


def install(work):
    if Path('/opt/openfoam11/etc/bashrc').is_file(): return
    run(['bash','-ec','''set -o pipefail
. /etc/os-release
[ "$ID" = ubuntu ]
case "$VERSION_CODENAME" in jammy|noble) ;; *) exit 2;; esac
curl -fsSL --retry 2 https://dl.openfoam.org/gpg.key | gpg --dearmor > /tmp/p2-of11.gpg
printf 'deb [signed-by=/tmp/p2-of11.gpg] https://dl.openfoam.org/ubuntu %s main\n' "$VERSION_CODENAME" >/etc/apt/sources.list.d/p2-of11.list
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=2 update
pkg=$(apt-cache show --no-all-versions openfoam11)
path=$(printf '%s\\n' "$pkg" | grep '^Filename: ' | cut -d' ' -f2)
sha=$(printf '%s\\n' "$pkg" | grep '^SHA256: ' | cut -d' ' -f2)
[[ $sha =~ ^[a-f0-9]{64}$ && $path == dists/"$VERSION_CODENAME"/main/binary-amd64/openfoam11_*.deb ]]
curl --proto '=https' --proto-redir '=https' --retry 2 -fsSL "https://downloads.sourceforge.net/project/foam/foam/ubuntu/$path" -o /tmp/p2-openfoam11.deb
printf '%s  %s\\n' "$sha" /tmp/p2-openfoam11.deb | sha256sum -c -
apt-get -o Acquire::Retries=2 install -y --no-install-recommends /tmp/p2-openfoam11.deb
'''],work,work/'install.log')


def entries(path):
    data=path.read_text().split('}',1)[1]; m=re.search(r'(?m)^\s*(\d+)\s*\n\s*\(\s*\n(.*?)\n\s*\)',data,re.S)
    if not m: raise ValueError('cannot read '+str(path))
    lines=m[2].strip().splitlines()
    if len(lines)!=int(m[1]): raise ValueError('wrong entry count '+str(path))
    return lines


def parabolic(case):
    mesh=case/'constant/polyMesh'; boundary=(mesh/'boundary').read_text()
    b=re.search(r'\binlet\s*\{([^{}]+)\}',boundary)[1]; start=int(re.search(r'startFace\s+(\d+)',b)[1]); n=int(re.search(r'nFaces\s+(\d+)',b)[1]); rr=[]
    for l in entries(mesh/'points'):
        x,y,z=map(float,l.strip().strip('()').split());rr.append(y*y+z*z)
    vals=[]
    for face in entries(mesh/'faces')[start:start+n]:
        ids=map(int,re.search(r'\(([^)]+)\)',face)[1].split()); r2=[rr[i] for i in ids]; vals.append(2*U*(1-(min(r2)+max(r2))/(2*(D/2)**2)))
    p=case/'0/U'; s=p.read_text(); s,nsub=re.subn(r'(\binlet\s*\{[^{}]*?\bvalue\s+)uniform\s*\([^)]*\)',lambda m:m[1]+'nonuniform List<vector>\n'+str(n)+'\n(\n'+'\n'.join(f'({v:.15g} 0 0)' for v in vals)+'\n)',s); assert nsub==1; p.write_text(s)


def evaluate(c,area):
    series=[]
    for name in ('pInlet','pOutlet','qInlet','qOutlet'):
        (p,)=list((c/'postProcessing'/name).glob('*/surfaceFieldValue.dat')); rows=[list(map(float,l.split())) for l in p.read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')]; series.append(rows[-20:])
    times=[r[0] for r in series[0]]
    if len(times)!=20 or times[-1]!=1200 or any([r[0] for r in s]!=times for s in series) or any(not math.isfinite(v) for s in series for row in s for v in row): raise ValueError('incomplete or invalid final samples')
    dp=[]; im=[]; fe=[]
    for pi,po,qi,qo in zip(*series):
        dp.append(RHO*(pi[1]-po[1])); im.append(abs(qi[1]+qo[1])/(U*area)); fe.append(max(abs(-qi[1]/(U*area)-1),abs(qo[1]/(U*area)-1)))
    mean=sum(dp)/len(dp); return dict(dp_Pa=mean,dp_span=(max(dp)-min(dp))/mean if mean>0 else None,imbalance=max(im),flux_error=max(fe),window_iterations=[times[0],times[-1]])


def case_run(name,fraction,work,ref):
    c=work/name; c.mkdir(); (c/'system').mkdir(); msh=c/'fluid_flow.msh'; info=ref[name+'Info']; msh.write_bytes(gzip.decompress((Path(__file__).parent/(name+'.msh.gz')).read_bytes())); sha=hashlib.sha256(msh.read_bytes()).hexdigest()
    if sha!=ref[name]: raise ValueError('mesh hash mismatch: '+name)
    write(str(c/'system/controlDict'),'dictionary','controlDict','application foamRun; startFrom startTime; startTime 0; stopAt endTime; endTime 1200; deltaT 1; writeControl timeStep; writeInterval 1200; writePrecision 14;\n');
    for filename in ('fvSchemes','fvSolution'): write(str(c/'system'/filename),'dictionary',filename,'')
    run(['gmshToFoam',msh.name],c,c/'import.log',True); b=c/'constant/polyMesh/boundary'; b.write_text(convert(b.read_text()))
    build(str(c),'laminar',U,RHO,NU,1200,10); parabolic(c)
    s=c/'system'; p=s/'controlDict'; fc=p.read_text().split('functions\n',1)[1]; write(str(p),'dictionary','controlDict','application foamRun; solver incompressibleFluid; startFrom startTime; startTime 0; stopAt endTime; endTime 1200; deltaT 1; writeControl timeStep; writeInterval 1200; writePrecision 14;\nfunctions\n'+fc)
    p=s/'fvSchemes';p.write_text(p.read_text().replace('default Euler','default steadyState'))
    write(str(s/'fvSolution'),'dictionary','fvSolution','''solvers { p {solver GAMG; smoother GaussSeidel; tolerance 1e-11; relTol 0.01;} U {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0.01;} }\nSIMPLE { nNonOrthogonalCorrectors 1; consistent no; }\nrelaxationFactors { fields {p 0.3;} equations {U 0.7;} }\n''')
    run(['checkMesh'],c,c/'mesh.log',True); log=(c/'mesh.log').read_text()
    if 'Mesh OK.' not in log or not re.search(r'Number of regions:\s*1\b',log,re.I) or int(re.search(r'(?m)^\s*cells:\s*(\d+)',log)[1])!=info['cells']: raise ValueError('mesh acceptance failed: '+log[-1800:])
    run(['foamRun','-solver','incompressibleFluid'],c,c/'solver.log',True); result=evaluate(c,info['inlet_area_m2']);result.update(cells=info['cells'],mesh_sha256=sha)
    if fraction==1: result['reference_Pa']=32*RHO*NU*U*LENGTH/D**2;result['pipe_error']=abs(result['dp_Pa']/result['reference_Pa']-1)
    result['pass']=result['dp_Pa']>0 and all(result[k] is not None and result[k]<=v for k,v in TOL.items() if k in result);return result


def main():
    work=Path(os.environ.get('BENCH_WORK','/kaggle/working/pressure-test'));work.mkdir(parents=True,exist_ok=False); out=work/'result.json'; res={'model':'analytic_benchmark_only','limits':TOL,'cases':{}}; ref=json.loads((Path(__file__).parent/'mesh_hashes.json').read_text())
    try:
        install(work)
        for name,frac in [('pipe',1.),('nozzle',.5)]:
            v=case_run(name,frac,work,ref);res['cases'][name]=v;print(name,v,flush=True)
            if not v['pass']: raise ValueError(name+' physics gate failed')
        res['pass']=True
    except Exception as exc:
        res.update({'pass':False,'error':str(exc)});raise
    finally: out.write_text(json.dumps(res,indent=2,allow_nan=False))

if __name__=='__main__': main()
