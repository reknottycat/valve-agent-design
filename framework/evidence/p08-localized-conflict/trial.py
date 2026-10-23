import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse, hashlib, json, time, resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step')
PIN='a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787'
RULES=Path('/workspace/shared/valve-mesh-baseline-20261022/source/valve-whole-flow-mesh-WFM1-20261011/P08_native_whole_coarse_A02/ACTUAL_REGENERATED_SURFACE_NATIVE_REGION_RULES_A01.json')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data): (ROOT/'evidence'/name).write_text(json.dumps(data,indent=2)+'\n')
def mesh_count(dim):
 types,tags,_=gmsh.model.mesh.getElements(dim)
 return {str(int(t)):len(v) for t,v in zip(types,tags)}
p=argparse.ArgumentParser();p.add_argument('stage',choices=['surface','volume']);a=p.parse_args();start=time.monotonic()
assert digest(SOURCE)==PIN
rules=json.loads(RULES.read_text())['regions']
gmsh.initialize(['trial','-nopopup']);gmsh.option.setNumber('General.AbortOnError',0);gmsh.logger.start();gmsh.option.setNumber('General.NumThreads',1)
for key in ('Geometry.OCCFixDegenerated','Geometry.OCCFixSmallEdges','Geometry.OCCFixSmallFaces','Geometry.OCCSewFaces','Geometry.OCCMakeSolids'):
 gmsh.option.setNumber(key,0)
gmsh.option.setNumber('Geometry.OCCBoundsUseStl',1)
gmsh.model.occ.importShapes(str(SOURCE));gmsh.model.occ.synchronize()
volumes=gmsh.model.getEntities(3);surfaces=gmsh.model.getEntities(2)
assert len(volumes)==1 and len(surfaces)==132,(volumes,len(surfaces))
mapping=[];used=set()
for dim,tag in surfaces:
 bbox=gmsh.model.occ.getBoundingBox(dim,tag);area=gmsh.model.occ.getMass(dim,tag)
 candidates=[r for r in rules if max(abs(x-y) for x,y in zip(bbox,r['finite_support_bbox_xyz_minmax_mm']))<0.2 and abs(area-r['CAD_area_mm2'])<max(1e-5,1e-7*area)]
 assert len(candidates)==1,(tag,bbox,area,len(candidates))
 r=candidates[0];sid=r['original_finite_face_fingerprint_tag'];assert sid not in used;used.add(sid)
 name='inlet' if sid==79 else 'outlet' if sid==34 else f'wall_FDG_{sid}'
 gmsh.model.addPhysicalGroup(2,[tag],sid);gmsh.model.setPhysicalName(2,sid,name)
 mapping.append({'gmsh_surface':tag,'source_face':sid,'role':name,'family':r['feature_family'],'area_mm2':area,'bbox_mm':bbox,'source_bbox_max_delta_mm':max(abs(x-y) for x,y in zip(bbox,r['finite_support_bbox_xyz_minmax_mm'])),'mapping_bbox_tolerance_mm':0.2})
gmsh.model.addPhysicalGroup(3,[volumes[0][1]],1);gmsh.model.setPhysicalName(3,1,'fluid_proxy')
volume=gmsh.model.occ.getMass(*volumes[0]);assert abs(volume-64142426.1438)<0.1
save('geometry.json',{'source_sha256':PIN,'rule_sha256':digest(RULES),'gmsh_version':gmsh.__version__,'volumes':len(volumes),'surfaces':len(surfaces),'volume_mm3':volume,'mapping':mapping,'healing_requested':False})
# Deliberately coarse pilot, NOT critical passage or CFD mesh acceptance.
for key,value in [('Mesh.MeshSizeFromPoints',0),('Mesh.MeshSizeFromCurvature',12),('Mesh.MeshSizeExtendFromBoundary',0),('Mesh.MeshSizeMin',0.05),('Mesh.MeshSizeMax',25),('Mesh.Algorithm',6),('Mesh.Algorithm3D',1),('Mesh.ElementOrder',1),('Mesh.Binary',1),('Mesh.MshFileVersion',4.1)]:gmsh.option.setNumber(key,value)

ORIGINAL=Path('/workspace/shared/valve-gmsh-trial-20261023')
surface=json.loads((ORIGINAL/'evidence/surface.json').read_text())
assert digest(ORIGINAL/'surface.msh')==surface['msh_sha256']
result={'engineering_release':False,'diagnostic_only':True,'changed_options':{'General.AbortOnError':0},'source_sha256_before':digest(SOURCE)}
try:
 gmsh.merge(str(ORIGINAL/'surface.msh'))
 gmsh.model.mesh.generate(3)
except Exception as e: result['exception']=str(e)
finally:
 result['last_entity_errors']=gmsh.model.mesh.getLastEntityError()
 result['last_node_errors']=gmsh.model.mesh.getLastNodeError().tolist()
 result['logger']=gmsh.logger.get()
 result['surface_elements']=mesh_count(2)
 result['volume_elements']=mesh_count(3)
 gmsh.option.setNumber('Mesh.SaveAll',1)
 gmsh.write(str(ROOT/'failed-current.msh'))
 result['failed_current_sha256']=digest(ROOT/'failed-current.msh')
 result['source_sha256_after']=digest(SOURCE)
 result['elapsed_s']=time.monotonic()-start
 result['peak_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 save('diagnostic.json',result)
 gmsh.finalize()
