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
gmsh.initialize(['trial','-nopopup']);gmsh.option.setNumber('General.NumThreads',1)
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
if a.stage=='surface':
 gmsh.model.mesh.generate(2);counts=mesh_count(2);count=sum(counts.values())
 gmsh.write(str(ROOT/'surface.msh'))
 missing=[]
 for m in mapping:
  _,ts,_=gmsh.model.mesh.getElements(2,m['gmsh_surface'])
  m['triangles']=sum(len(t) for t in ts)
  if not m['triangles']:missing.append(m['source_face'])
 save('surface.json',{'elements':counts,'count':count,'missing_faces':missing,'faces':mapping,'msh_sha256':digest(ROOT/'surface.msh'),'bytes':(ROOT/'surface.msh').stat().st_size,'eligible_for_bounded_volume_trial':count<=50000 and not missing,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_s':time.monotonic()-start,'critical_passage_resolution_verified':False,'engineering_release':False})
 print('SURFACE_RESULT',count,not missing,flush=True)
else:
 surface=json.loads((ROOT/'evidence/surface.json').read_text());assert not surface['missing_faces'];assert surface['count']==157086;assert digest(ROOT/'surface.msh')==surface['msh_sha256']
 gmsh.merge(str(ROOT/'surface.msh'));gmsh.model.mesh.generate(3)
 counts=mesh_count(3);count=sum(counts.values());gmsh.write(str(ROOT/'candidate.msh'))
 types,tags,nodes=gmsh.model.mesh.getElements(3)
 assert list(types)==[4],types
 import numpy as np
 q=gmsh.model.mesh.getElementQualities(tags[0],'minSICN');v=gmsh.model.mesh.getElementQualities(tags[0],'volume')
 save('volume.json',{'elements':counts,'count':count,'quality_minSICN':{'min':float(np.min(q)),'percentiles':np.percentile(q,[0,1,5,50,95,100]).tolist(),'nonpositive':int(np.count_nonzero(np.asarray(q)<=0))},'volume_mm3_sum':float(np.sum(v)),'nonpositive_volume':int(np.count_nonzero(np.asarray(v)<=0)),'msh_sha256':digest(ROOT/'candidate.msh'),'bytes':(ROOT/'candidate.msh').stat().st_size,'within_exploratory_count_cap':count<=250000,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_s':time.monotonic()-start,'engineering_release':False,'native_checkMesh_executed':False,'critical_passage_resolution_verified':False})
 print('VOLUME_RESULT',count,flush=True)
assert digest(SOURCE)==PIN
gmsh.finalize()
