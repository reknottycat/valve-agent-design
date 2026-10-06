from pathlib import Path
import subprocess,sys,json,tempfile,shutil,zipfile,hashlib
R=Path(__file__).resolve().parents[1];rows=[];docxml=[];arith=[]
with tempfile.TemporaryDirectory(dir=R/'verification',prefix='generation_') as t:
 d=Path(t)
 for name in ['build_calculation_book.py','rebuilt_chapters.py','current_flow_chapter.py','baseline_R0_source_manifest.json','new_source_manifest.json']:
  shutil.copyfile(R/name,d/name)
 for name in ['sources','sources_new']:shutil.copytree(R/name,d/name)
 for flags in [[],['-O']]:
  p=subprocess.run([sys.executable,*flags,str(d/'build_calculation_book.py')],text=True,capture_output=True)
  if p.returncode:raise RuntimeError(p.stderr)
  result=json.loads((d/'output/build_summary.json').read_text());rows.append({'mode':'optimized' if flags else 'normal','arithmetic_checks':result['arithmetic_checks'],'native_equations':result['native_equations'],'tables':result['tables'],'completed':True})
  with zipfile.ZipFile(next((d/'output').glob('*.docx'))) as z:docxml.append(z.read('word/document.xml'))
  arith.append((d/'arithmetic_verification.json').read_bytes())
 if docxml[0]!=docxml[1] or arith[0]!=arith[1]:raise RuntimeError('normal and optimized document semantics differ')
out={'scope':'DOCUMENT_GENERATION_ONLY','passed':True,'normal_and_optimized_document_xml_identical':True,'arithmetic_records_identical':True,'results':rows,'generator_sha256':hashlib.sha256((R/'build_calculation_book.py').read_bytes()).hexdigest()}
(R/'verification/generation_tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
