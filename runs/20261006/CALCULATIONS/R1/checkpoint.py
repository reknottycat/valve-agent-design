from pathlib import Path
import hashlib,json,zipfile,sys
R=Path(__file__).resolve().parent
stage=sys.argv[1] if len(sys.argv)>1 else 'WORKING'
status=json.loads((R/'checkpoint_status.json').read_text());status['stage']=stage;status['final_frozen']=(stage=='FROZEN_WORKING_DRAFT_R1')
if status['final_frozen']:
 freeze=json.loads((R/'freeze_record.json').read_text())
 for item in freeze['frozen_files']:
  if hashlib.sha256((R/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Frozen identity mismatch '+item['path'])
(R/'checkpoint_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
exclude={'artifact_manifest.json','library_checkpoint_receipt.json','checkpoint_library_identity.json','last_checkpoint.json'}
files=[]
for p in sorted(R.rglob('*')):
 rel=p.relative_to(R)
 if not p.is_file() or p.suffix=='.zip' or any(x.startswith('.') or x=='__pycache__' for x in rel.parts) or rel.parts[0]=='qa' or p.name in exclude:continue
 files.append(p)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'revision':'R1_REBUILT','stage':stage,'files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
(R/'artifact_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');files.append(R/'artifact_manifest.json')
z=R/'522-35.4179_R1_计算书重建检查点.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as out:
 for p in files:out.write(p,str(p.relative_to(R)))
with zipfile.ZipFile(z) as out:
 if out.testzip():raise RuntimeError('CRC failure')
 for x in manifest['files']:
  if hashlib.sha256(out.read(x['path'])).hexdigest()!=x['sha256']:raise RuntimeError('Archive mismatch '+x['path'])
res={'stage':stage,'archive':str(z),'files':len(files),'bytes':z.stat().st_size,'sha256':sha(z)}
(R/'last_checkpoint.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print(json.dumps(res,ensure_ascii=False))
