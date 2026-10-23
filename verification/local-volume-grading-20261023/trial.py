import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse, hashlib, json, time, resource, math
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
gmsh.initialize(['trial','-nopopup']);gmsh.logger.start();gmsh.option.setNumber('General.AbortOnError',0);gmsh.option.setNumber('General.NumThreads',1)
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

from collections import Counter
modified=Counter(); curves={abs(t) for d,t in gmsh.model.getBoundary([(2,64),(2,108)],combined=False,oriented=True)}; adjacency={t:gmsh.model.getAdjacencies(1,t)[0].tolist() for t in sorted(curves)};save('complete-boundary-audit.json',{'curves':sorted(curves),'adjacency':adjacency}); print('COMPLETE_BOUNDARY_AUDIT',json.dumps(adjacency),flush=True)
retainer_curves={abs(t) for d,t in gmsh.model.getBoundary([(2,103),(2,127)],combined=False,oriented=True)};save('retainer-boundary-audit.json',{'curves':sorted(retainer_curves),'uncombined_boundaries':{t:gmsh.model.getBoundary([(2,t)],combined=False,oriented=True) for t in [103,127]},'adjacency':{t:gmsh.model.getAdjacencies(1,t)[0].tolist() for t in sorted(retainer_curves)}})
from volume_law import distance as volume_distance, H0, SLOPE, CUTOFF
volume_stats={'calls':0,'modified':0,'far_field_calls':0,'modified_distance_min_mm':None,'modified_distance_max_mm':None,'newlaw_entities':{}}
def cb(d,t,x,y,z,lc):
 if d==3 and t==1:
  dd=volume_distance(x,y,z);volume_stats['calls']+=1
  if dd>=CUTOFF:volume_stats['far_field_calls']+=1;return lc
  size=min(lc,H0+SLOPE*dd)
  if size<lc:
   volume_stats['modified']+=1;volume_stats['newlaw_entities']['3:1']=volume_stats['modified']
   volume_stats['modified_distance_min_mm']=dd if volume_stats['modified_distance_min_mm'] is None else min(dd,volume_stats['modified_distance_min_mm'])
   volume_stats['modified_distance_max_mm']=dd if volume_stats['modified_distance_max_mm'] is None else max(dd,volume_stats['modified_distance_max_mm'])
  return size
 if (d==2 and t in {118,126}) or (d==1 and t in {280,282,294}):
  rho=math.hypot(x-300,y); distance=max(0.,rho-110.74996624095) if t in {118,280,282} else max(0.,105.25003375904-rho)
  size=math.pi/24+0.8*distance
  if lc>size:modified[f"{d}:{t}"]+=1
  return min(lc,size)
 if (d==2 and t in {103,127}) or (d==1 and t in retainer_curves):
  if lc>1:modified[f'{d}:{t}']+=1
  return min(lc,1.)
 if (d==2 and t in {64,108}) or (d==1 and t in curves):
  if lc>4:modified[f'{d}:{t}']+=1
  return min(lc,4.)
 return lc
gmsh.model.mesh.setSizeCallback(cb)
try:gmsh.model.mesh.generate(3)
except Exception as e:save('exception.json',{'error':str(e)})
gmsh.option.setNumber('Mesh.SaveAll',1);gmsh.write(str(ROOT/'fresh-local-surface.msh'))
fc={tag:sum(len(v) for v in gmsh.model.mesh.getElements(2,tag)[1]) for dim,tag in surfaces};count=sum(fc.values())
save('volume-callback-stats.json',volume_stats)
save('result.json',{'source_unchanged':digest(SOURCE)==PIN,'callback_modified_entities':dict(modified),'triangles':count,'per_face_counts':fc,'cost_gate':count<=200000,'elapsed_s':time.monotonic()-start,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'logger':gmsh.logger.get(),'engineering_release':False,'volume_generation_executed':True,'volume_elements':mesh_count(3),'last_entity_errors':gmsh.model.mesh.getLastEntityError(),'last_node_errors':gmsh.model.mesh.getLastNodeError().tolist(),'fresh_surface_no_imported_mesh':True})
gmsh.finalize()
