from pathlib import Path
import json,shutil,subprocess,tempfile,sys,hashlib
R=Path(__file__).resolve().parents[1]
results=[]
with tempfile.TemporaryDirectory(dir=R/'verification',prefix='source_guard_') as t:
 d=Path(t)
 for name in ['build_calculation_book.py','baseline_R0_source_manifest.json','new_source_manifest.json']:
  shutil.copyfile(R/name,d/name)
 for name in ['sources','sources_new']:shutil.copytree(R/name,d/name)
 for mode in [[],['-O']]:
  for area,rel,message in [('R0','sources/C2/T15/calc_results.json','Restored R0 source changed'),('fresh','sources_new/STRUCTURAL_NEW/summary.json','Fresh source snapshot changed')]:
   p=d/rel;old=p.read_bytes();p.write_bytes(old+b'\n')
   run=subprocess.run([sys.executable,*mode,str(d/'build_calculation_book.py')],capture_output=True,text=True)
   p.write_bytes(old)
   okay=run.returncode!=0 and message in run.stderr
   if not okay:raise RuntimeError('Source mutation was not rejected')
   results.append({'mode':'optimized' if mode else 'normal','mutation':area+'_append_byte','rejected':okay})
  run=subprocess.run([sys.executable,*mode,str(d/'build_calculation_book.py'),'--refresh-sources'],capture_output=True,text=True)
  okay=run.returncode!=0 and 'Recovered R0 snapshot is frozen' in run.stderr
  if not okay:raise RuntimeError('Refresh was not rejected')
  results.append({'mode':'optimized' if mode else 'normal','mutation':'refresh_R0_switch','rejected':okay})
result={'scope':'DOCUMENT_SOURCE_BYTE_GUARDS_ONLY','passed':True,'cases':results,'generator_sha256':hashlib.sha256((R/'build_calculation_book.py').read_bytes()).hexdigest()}
(R/'verification/source_guard_test_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
