from pathlib import Path
import hashlib,json,re,shutil
R=Path(__file__).resolve().parent;S=Path('/workspace/shared/valve-mesh-repair-rebuilt-20261006/revalidation_v2')
PIN='98976d5277a5592284cd20c9dbce095d7c7b845e036417ade65c90e5aff0bd05'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(S/'revalidation_manifest.json')!=PIN:raise RuntimeError('Mesh v2 externally pinned seal mismatch')
m=json.loads((S/'revalidation_manifest.json').read_text());checked=0
for group,inv in m['directory_snapshots'].items():
 actual={str(p.relative_to(S/group)) for p in (S/group).rglob('*') if p.is_file()}
 if actual!=set(inv['files']):raise RuntimeError('Mesh v2 inventory mismatch '+group)
 for rel,rec in inv['files'].items():
  p=S/group/rel
  if sha(p)!=rec['sha256'] or p.stat().st_size!=rec['bytes']:raise RuntimeError('Mesh v2 frozen byte mismatch '+str(p))
  checked+=1
payload=0
for line in (S/'SHA256SUMS').read_text().splitlines():
 dig,rel=line.split(None,1);p=S/rel.strip()
 if sha(p)!=dig:raise RuntimeError('Mesh v2 package byte mismatch '+str(p))
 payload+=1
for rel in ['verification/acceptance.normal.json','verification/acceptance.optimized.json','verification/independent-finalize.json']:
 a=json.loads((S/rel).read_text())
 if a['status']!='PASS' or a['manifest_sha256']!=PIN:raise RuntimeError('Mesh v2 acceptance mismatch '+rel)
review=json.loads((S/'verification/independent-review.json').read_text())
if review['pinned_manifest_sha256']!=PIN or review['gate_tests']['normal_tests']!=31 or review['gate_tests']['optimized_tests']!=31:raise RuntimeError('Review scope mismatch')
log=(S/'stage_evidence/native_final.log').read_text()
if 'Mesh OK.' not in log or 'Failed ' in log or 'FOAM FATAL' in log:raise RuntimeError('Native mesh check not accepted')
def val(pattern):return float(re.search(pattern,log).group(1).rstrip('.'))
num={key:int(val(r'^\s*'+label+r':\s*(\d+)')) for key,label in []}
num={'cells':int(val(r'\n\s+cells:\s+(\d+)')),'points':int(val(r'\n\s+points:\s+(\d+)')),'faces':int(val(r'\n\s+faces:\s+(\d+)')),'native_total_volume_m3':val(r'Total volume = ([0-9.eE+-]+)'), 'maximum_nonorthogonality_degrees':val(r'non-orthogonality Max: ([0-9.eE+-]+)'), 'faces_over_70_degrees':int(val(r'faces: (\d+)\.')), 'maximum_skewness':val(r'Max skewness = ([0-9.eE+-]+)'), 'min_cell_determinant':val(r'wellposedness\) : minimum: ([0-9.eE+-]+)'), 'normal_and_optimized_tests':31}
g=review['geometry_checks'];num['source_native_conversion_note']={'conversion_differing_scalars':g['conversion_scalars_differing_one_ulp'],'conversion_max_absolute_difference_m':g['maximum_conversion_difference_m'],'conversion_max_ulp':1};num['manifest_sha256']=PIN;num['native_log_sha256']=sha(S/'stage_evidence/native_final.log');num['scope']='MESH_GEOMETRY_AND_BINDINGS_ONLY'
manifest=json.loads((R/'new_source_manifest.json').read_text());old={x['path']:x for x in manifest['files']}
for p in sorted(S.rglob('*')):
 rel=p.relative_to(S)
 if not p.is_file() or rel.parts[0] in ['data','provenance'] or '__pycache__' in rel.parts:continue
 dst=R/'sources_new/MESH_V2'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 key='MESH_V2/'+str(rel);old[key]={'path':key,'source':str(p),'sha256':sha(dst),'bytes':dst.stat().st_size}
p=R/'sources_new/MESH_V2/book_values.json';p.write_text(json.dumps(num,indent=2)+'\n');old['MESH_V2/book_values.json']={'path':'MESH_V2/book_values.json','source':'DERIVED from pinned MESH_V2/stage_evidence/native_final.log and verification/independent-review.json using add_mesh_v2_sources.py','sha256':sha(p),'bytes':p.stat().st_size}
manifest['files']=list(old.values());(R/'new_source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
report={'passed':True,'mesh_scope_only':True,'pinned_manifest_sha256':PIN,'frozen_inventory_files_checked':checked,'package_payload_files_checked':payload,'book_values_parsed_from_fresh_native_log':True,'normal_and_optimized_acceptance_and_independent_review_match':True,'upstream_library_file_id':'libfile_d1fe3abe4124819191187761705c99c6','upstream_archive_sha256':'aa2410a92d6aa64dc6e9f0a6253f4a82e1a5cceb9814557b3a84b4190d2f667e'}
(R/'verification/mesh_v2_final_source_binding.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
