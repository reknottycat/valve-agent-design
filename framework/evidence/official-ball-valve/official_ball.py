"""Foundation 11 ballValve: same physics, two values of the geometry parameter lPipe.
Run after install_openfoam() on a Linux CPU worker. No product Kz or pressure certification.
"""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def replace_one(path, pattern, replacement):
    text, n = re.subn(pattern, replacement, path.read_text(), flags=re.M)
    if n != 1: raise ValueError(f'{path.name}: expected one match, got {n}')
    path.write_text(text)


def measurements(case, output, length):
    names = ('inlet','lowerOutlet','upperOutlet')
    # End planes must actually move; a different input file alone is not proof.
    mesh_log = (case/'log.checkMesh').read_text()
    pos = length*.01
    for patch, axis, coordinate in [('inlet',0,-pos),('lowerOutlet',1,-pos),('upperOutlet',1,pos)]:
        line=next(l for l in mesh_log.splitlines() if re.match(r'^\s*'+patch+r'\s+\d+\s+\d+\s+',l))
        groups=re.findall(r'\(([^()]+)\)',line)[-2:]
        if len(groups)!=2 or not all(abs(float(g.split()[axis])-coordinate)<1e-6 for g in groups): raise ValueError(f'Unexpected physical end plane for {patch}: {line}')
    if not re.search(r'^Mesh OK\.$',mesh_log,re.M):raise ValueError('Initial native mesh check did not pass')
    solve=(case/'log.foamRun').read_text(errors='replace');times=re.findall(r'^Time = ([-+\d.eE]+)s?\s*$',solve,re.M)
    if not times or abs(float(times[-1])-1)>1e-6 or not re.search(r'^End\s*$',solve,re.M) or 'FOAM FATAL' in solve: raise ValueError('Official end time not reached')
    rows={}; ids=[n+'FlowRate' for n in names]+[n+'Pressure' for n in names]
    for name in ids:
        files=list((case/'postProcessing'/name).glob('*/surfaceFieldValue.dat'))
        if len(files)!=1:raise ValueError(f'{name}: need one measured series, got {files}')
        series={}
        for line in files[0].read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                t,v=map(float,line.split());
                if not math.isfinite(t) or not math.isfinite(v) or t in series:raise ValueError('invalid series '+name)
                series[t]=v
        rows[name]=series
        shutil.copyfile(files[0],output/(name+'.dat'))
    ts=sorted(rows[ids[0]])
    if len(ts)<20 or abs(ts[-1]-1)>1e-6 or any(sorted(series)!=ts for series in rows.values()):raise ValueError('Missing or unmatched physical times')
    def integral(v): return sum((b-a)*(x+y)*.5 for a,b,x,y in zip(ts,ts[1:],v,v[1:]))
    q=[[rows[n][t] for t in ts] for n in ids[:3]]
    qin=-integral(q[0]); residual=integral([abs(sum(x)) for x in zip(*q)])
    if qin<=0:raise ValueError('No net inflow')
    metric=residual/qin
    sampled={}
    for t in (.25,.5,.75,1.):
        # Linear interpolation on physical time; adaptive timesteps can differ by case.
        import bisect
        i=bisect.bisect_left(ts,t)
        if i==len(ts) or (i==0 and t!=ts[0]): raise ValueError('missing phase')
        def at(name):
            a,b=ts[max(0,i-1)],ts[i]; return rows[name][b] if t==b or a==b else rows[name][a]+(rows[name][b]-rows[name][a])*(t-a)/(b-a)
        sampled[str(t)]={'inflow_m3_s':-at(ids[0]),'lower_out_m3_s':at(ids[1]),'upper_out_m3_s':at(ids[2]),'inlet_minus_lower_kinematic_pressure_m2_s2':at(ids[3])-at(ids[4]),'inlet_minus_upper_kinematic_pressure_m2_s2':at(ids[3])-at(ids[5])}
    return {'lPipe':length,'end_plane_distance_m':pos,'physical_time_s':ts[-1],'samples':len(ts),'interval_start_s':ts[0],'net_inlet_volume_m3':qin,'integrated_absolute_flux_imbalance':metric,'phase_samples':sampled,'flow_balance_pass':metric<=.001,'geometry_mesh_sha256':hashlib.sha256((case/'constant/polyMesh/points').read_bytes()).hexdigest()}


def main():
    work=Path(tempfile.mkdtemp(prefix='ballvalve-')); output=Path('/kaggle/working/ballvalve');output.mkdir(parents=True,exist_ok=True)
    result={'example':'Foundation 11 incompressibleFluid/ballValve','scope':'official tutorial and geometric sensitivity, not validation of the 57 mm valve','flow_balance_limit':.001,'changes':{'execution':'2 ranks; report numerical data instead of reconstructing visualization fields','observations':'three additional area-mean static kinematic pressures; identical in both cases','variant_only':'lPipe 50 -> 60; rPipe, rBall, motion, fluid, pressure boundary conditions and endTime unchanged'},'cases':[], 'passed':False}
    try:
        install_openfoam(work)
        # #calc in the official dictionary compiles code: never execute it as root.
        of=Path('/opt/openfoam11'); tut=of/'tutorials/incompressibleFluid/ballValve'; resource=of/'tutorials/resources/blockMesh/ballValve'
        result['source_sha256']={str(p.relative_to(of)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (tut/'Allrun',tut/'system/controlDict',tut/'constant/dynamicMeshDict',tut/'0/U',tut/'0/p',resource)}
        for length in (50,60):
            label=f'lPipe{length}';folder=output/label;folder.mkdir();case=work/label;shutil.copytree(tut,case);shutil.copyfile(resource,case/'system/blockMeshDict');replace_one(case/'system/blockMeshDict',r'^lPipe\s+50;',f'lPipe {length};');replace_one(case/'system/decomposeParDict',r'^numberOfSubdomains\s+8;','numberOfSubdomains 2;')
            control=case/'system/controlDict';insert='';
            for n in ('inlet','lowerOutlet','upperOutlet'):
                insert+=f'\n    {n}Pressure {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); select patch; patch {n}; fields (p); operation areaAverage; writeFields false; writeControl timeStep; writeInterval 1; }}'
            replace_one(control,r'^functions\s*\{','functions\n{'+insert)
            # Official patchFlowRate uses its own logging cadence; force same native cadence for pressure and flow if necessary by using its config, not interpolation across missing series.
            text=control.read_text()
            for n in ('inlet','lowerOutlet','upperOutlet'):
                text=text.replace(f'#includeFunc patchFlowRate(name={n}FlowRate, patch={n})',f'{n}FlowRate {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); select patch; patch {n}; fields (phi); operation sum; writeFields false; writeControl timeStep; writeInterval 1; }}')
            control.write_text(text)
            driver=case/'Allrun';s=driver.read_text();assert s.count('runApplication blockMesh -dict $FOAM_TUTORIALS/resources/blockMesh/ballValve')==1;s=s.replace('runApplication blockMesh -dict $FOAM_TUTORIALS/resources/blockMesh/ballValve','runApplication blockMesh\nrunApplication checkMesh -allGeometry -allTopology\ngrep -q "^Mesh OK\\.$" log.checkMesh');assert '# Reconstruct' in s;driver.write_text(s.split('# Reconstruct')[0]);
            if os.geteuid()==0:
                # Only disposable job directory is transferred to the unprivileged tutorial user.
                subprocess.run(['chown','-R','nobody',str(work)],check=True);prefix=['runuser','-u','nobody','--']
            else:prefix=[]
            with (folder/'driver.log').open('w') as log:
                subprocess.run(prefix+['env','HOME='+str(work),'USER='+('nobody' if prefix else os.environ.get('USER','foam')),'bash','-c','source /opt/openfoam11/etc/bashrc >/dev/null && exec sh -e ./Allrun'],cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=14400)
            row=measurements(case,folder,length);result['cases'].append(row)
            if not row['flow_balance_pass']:raise ValueError(f'{label} failed flow conservation')
        a,b=result['cases']
        if a['geometry_mesh_sha256']==b['geometry_mesh_sha256']: raise ValueError('Input parameter changed but native mesh did not')
        result['phase_differences_variant_minus_baseline']={t:{k:b['phase_samples'][t][k]-value for k,value in row.items()} for t,row in a['phase_samples'].items()}
        result['reported_pressure_changed']=any(abs(v)>1e-5 for row in result['phase_differences_variant_minus_baseline'].values() for k,v in row.items() if 'pressure' in k)
        if not result['reported_pressure_changed']: raise ValueError('No observable pressure response in sampled phases; do not claim sensitivity')
        result['passed']=True
    except BaseException as e:
        result['error']=repr(e);raise
    finally:
        for case in sorted(work.glob('lPipe*')):
            for f in case.glob('log.*'):
                with f.open('rb') as src,gzip.open(output/case.name/(f.name+'.gz'),'wb') as dst:shutil.copyfileobj(src,dst)
        (output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,allow_nan=False),flush=True)

def run(cmd, cwd, log, of=False):
    """Execute command with OpenFOAM environment if needed."""
    if of:
        cmd = ['bash', '-c',
               'source /opt/openfoam11/etc/bashrc >/dev/null && exec "$@"',
               'foam', *cmd]
    with log.open('w') as f:
        rc = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        raise RuntimeError(
            f'{cmd[-1]} failed ({rc}): {log.read_text(errors="replace")[-2200:]}'
        )


def install_openfoam(work):
    """Install OpenFOAM 11 on Ubuntu (Jammy/Noble)."""
    if Path('/opt/openfoam11/etc/bashrc').is_file():
        return

    run(['bash', '-ec', '''set -o pipefail
. /etc/os-release
[ "$ID" = ubuntu ]
case "$VERSION_CODENAME" in jammy|noble) ;; *) exit 2;; esac
curl -fsSL --retry 2 https://dl.openfoam.org/gpg.key | gpg --dearmor > /tmp/valve3d-of11.gpg
printf 'deb [signed-by=/tmp/valve3d-of11.gpg] https://dl.openfoam.org/ubuntu %s main\n' "$VERSION_CODENAME" >/etc/apt/sources.list.d/valve3d-of11.list
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=2 update
pkg=$(apt-cache show --no-all-versions openfoam11)
path=$(printf '%s\\n' "$pkg" | grep '^Filename: ' | cut -d' ' -f2)
sha=$(printf '%s\\n' "$pkg" | grep '^SHA256: ' | cut -d' ' -f2)
[[ $sha =~ ^[a-f0-9]{64}$ && $path == dists/"$VERSION_CODENAME"/main/binary-amd64/openfoam11_*.deb ]]
curl --proto '=https' --proto-redir '=https' --retry 2 -fsSL "https://downloads.sourceforge.net/project/foam/foam/ubuntu/$path" -o /tmp/valve3d-openfoam11.deb
printf '%s  %s\\n' "$sha" /tmp/valve3d-openfoam11.deb | sha256sum -c -
apt-get -o Acquire::Retries=2 install -y --no-install-recommends /tmp/valve3d-openfoam11.deb
'''], work, work/'install.log')



if __name__=="__main__": main()
