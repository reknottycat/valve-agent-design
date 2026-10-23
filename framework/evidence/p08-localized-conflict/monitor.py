import json,os,signal,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent;stage=sys.argv[1];env=dict(os.environ,PYTHONPATH='/workspace/shared/valve-gmsh-trial-20261023/vendor',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
start=time.monotonic();reason=None;peak=0
with (root/'evidence'/f'{stage}.log').open('w') as log:
 p=subprocess.Popen([sys.executable,str(root/'trial.py'),stage],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  try:
   rss=int(next(x.split()[1] for x in Path(f'/proc/{p.pid}/status').read_text().splitlines() if x.startswith('VmRSS:')))*1024;peak=max(peak,rss)
  except (OSError,StopIteration):rss=0
  if time.monotonic()-start>180:reason='wall_timeout_180s'
  if rss>2*1024**3:reason='rss_cap_2GiB'
  if reason:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
  time.sleep(.1)
 rc=p.wait()
(root/'evidence'/f'{stage}-receipt.json').write_text(json.dumps({'stage':stage,'returncode':rc,'stop_reason':reason,'elapsed_s':time.monotonic()-start,'sampled_peak_rss_bytes':peak,'limits_are_cost_controls_not_quality_criteria':True},indent=2)+'\n')
print(stage,rc,reason);sys.exit(rc if rc>=0 else 1)
