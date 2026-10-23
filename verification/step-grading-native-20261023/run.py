from pathlib import Path
import os,sys,json,hashlib,subprocess,time,signal,psutil
R=Path(__file__).parent.resolve();EXPECTED=Path('/workspace/shared/valve-step-grading-native-20261023');assert R==EXPECTED
SRC=Path('/workspace/shared/valve-step-grading-volume-20261023/fresh-local-surface.msh');SHA='4e1b4168c9cfdd8d248a54dbbe2411c6fd7661305e479d77f53e3a0f07568a98';assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
T=Path('/workspace/shared/valve-openfoam-quality-20261023/root/usr');C=R/'case';assert C.is_relative_to(R)
assert not (C/'constant/polyMesh').exists(),'Refuse repeated conversion or scaling'
env=os.environ.copy();env.update(WM_PROJECT_DIR=str(T/'share/openfoam'),FOAM_ETC=str(T/'share/openfoam/etc'),LD_LIBRARY_PATH=str(T/'lib/dummy')+':'+str(T/'lib'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
commands=[('export-run',[sys.executable,str(R/'export_copy.py')]),('convert',[str(T/'bin/gmshToFoam'),'-case',str(C),str(R/'source-copy-ascii22-mm.msh')]),('scale',[str(T/'bin/transformPoints'),'-case',str(C),'-scale','0.001']),('verify',[sys.executable,str(R/'verify_conversion.py')]),('checkMesh',[str(T/'bin/checkMesh'),'-case',str(C),'-constant','-allGeometry','-allTopology','-noFunctionObjects'])]
for name,args in commands:
 if '-case' in args:assert Path(args[args.index('-case')+1]).resolve()==C
proof={'commands':commands,'cwd':str(R),'env_overrides':{k:env[k] for k in ['WM_PROJECT_DIR','FOAM_ETC','LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},'input_sha256':SHA,'new_case':str(C),'conversion_has_not_run':True}
(R/'evidence/preflight.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof,indent=2),flush=True)
if '--execute' not in sys.argv:sys.exit()
for name,args in commands:
 assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
 start=time.monotonic();peak=0;reason=None
 with (R/'evidence'/f'{name}.log').open('w') as f:
  q=subprocess.Popen(args,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  while q.poll() is None:
   try:rss=psutil.Process(q.pid).memory_info().rss;peak=max(peak,rss)
   except psutil.NoSuchProcess:break
   if rss>2147483648 or time.monotonic()-start>180:reason='guard';os.killpg(q.pid,signal.SIGTERM);break
   time.sleep(.1)
  code=q.wait()
 result={'argv':args,'cwd':str(R),'exit_code':code,'peak_rss':peak,'seconds':time.monotonic()-start,'stop':reason};(R/'evidence'/f'{name}.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
 assert code==0 and reason is None,result
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA
