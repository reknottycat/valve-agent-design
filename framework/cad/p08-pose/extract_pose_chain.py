import json,hashlib,sys
from pathlib import Path
def extract(summary_path,scope_path,index_path):
 paths=[Path(summary_path),Path(scope_path)];index=json.loads(Path(index_path).read_text())['drive_products'];provenance=[]
 for p in paths:
  pin=next(x for x in index if x['name']==p.name);h=hashlib.sha256(p.read_bytes()).hexdigest()
  if h!=pin['sha256']:raise ValueError('Historical evidence hash mismatch: '+p.name)
  provenance.append({'name':p.name,'sha256':h,'url':pin['url'],'bytes':p.stat().st_size})
 s=json.loads(paths[0].read_text());sc=json.loads(paths[1].read_text());r=s['independent_export_review']
 return {'scope':'Historical source-to-nominal-pose evidence, NOT a new CAD pose measurement','sources':provenance,'nominal_pose':sc['pose'],'historical_pose_identity':r['pose_identity'],'historical_tested_hashes':r['tested_hashes'],'historical_geometry_checks_passed':r['geometry_checks_passed'],'historical_qualification_holds':r['qualification_holds'],'this_run_recomputed_pose':False,'final_mesh_mapping_verified':False,'actual_product_seat_datum_verified':False,'missing_for_new_independent_pose_measurement':['Exact pinned source/disc_AGR1.step and output/disc_AGR1_open57.step geometry bytes or a verified CAD face correspondence','Exact pinned source/seat_source.step and documented seat/closed-disc reference plane identifying what mechanical lift measures','Pinned build_fluid_domain.py and source/SOURCE_MANIFEST.json for direct script-level placement review; only their historical tested hashes are available in this recovered subset'],'stop_condition':'Historical source chain recovered and hashes checked; no geometry reconstruction or repeated simulation in this subtask'}
if __name__=='__main__':print(json.dumps(extract(*sys.argv[1:]),indent=2,ensure_ascii=False))
