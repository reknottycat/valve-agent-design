import subprocess,time,pathlib,sys,os,json,signal,resource
import psutil
b=pathlib.Path(__file__).parent;label=sys.argv[1];cmd=sys.argv[2:]
start=time.monotonic();peak=0;reason=None
with (b/'evidence'/f'{label}.log').open('w') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  try: rss=psutil.Process(p.pid).memory_info().rss;peak=max(peak,rss)
  except psutil.NoSuchProcess: break
  if rss>2*1024**3 or time.monotonic()-start>180:
   reason='resource_guard';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(.1)
 code=p.wait()
r={'command':cmd,'exit_code':code,'peak_rss_bytes':peak,'elapsed_s':time.monotonic()-start,'stop_reason':reason}
(b/'evidence'/f'{label}.json').write_text(json.dumps(r,indent=2));print(r);sys.exit(code)
