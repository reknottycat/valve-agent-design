import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,numpy as np,json
from pathlib import Path
r=Path(__file__).resolve().parent;gmsh.initialize();gmsh.open(str(r/'fresh-local-surface.msh'));types,tags,ns=gmsh.model.mesh.getElements(3);out={'types':[int(t) for t in types],'engineering_release':False}
if len(types):
 assert list(types)==[4],types
 tet=np.asarray(ns[0]).reshape(-1,4);nt,co,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.asarray(co).reshape(-1,3))};xyz=np.array([[pos[int(t)] for t in row] for row in tet]);vol=np.einsum('ij,ij->i',np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),xyz[:,3]-xyz[:,0])/6
 q=gmsh.model.mesh.getElementQualities(tags[0],'minSICN');out.update({'nodes':len(nt),'unique_node_tags':len(set(nt.tolist())),'finite_coordinates':bool(np.isfinite(co).all()),'tetrahedra':len(tet),'signed_volume_min_mm3':float(vol.min()),'nonpositive_signed_volumes':int((vol<=0).sum()),'volume_sum_mm3':float(vol.sum()),'volume_relative_error_CAD':float(vol.sum()/64142426.1438-1),'quality_minSICN_percentiles':np.percentile(q,[0,1,5,50,95,100]).tolist(),'quality_nonpositive':int((np.array(q)<=0).sum())})
 f=np.sort(np.concatenate([tet[:,[0,1,2]],tet[:,[0,1,3]],tet[:,[0,2,3]],tet[:,[1,2,3]]]),axis=1);uniq,c=np.unique(f,axis=0,return_counts=True);bound=uniq[c==1];out['tet_face_incidence']={str(int(i)):int((c==i).sum()) for i in np.unique(c)}
 surf=[];roles={}
 for d,t in gmsh.model.getEntities(2):
  ty,ts,nd=gmsh.model.mesh.getElements(2,t)
  for typ,arr in zip(ty,nd):
   assert typ==2
   surf.extend(tuple(int(x) for x in row) for row in np.sort(arr.reshape(-1,3),axis=1))
  roles[t]={'physical':gmsh.model.getPhysicalGroupsForEntity(2,t).tolist(),'triangles':sum(len(x) for x in ts)}
 surface_set=set(surf);boundary_set=set(map(tuple,bound.tolist()));out['boundary_triangles_missing_from_surface']=len(boundary_set-surface_set);out['surface_triangles_not_on_tet_boundary']=len(surface_set-boundary_set);out['duplicate_surface_triangles']=len(surf)-len(surface_set);out['physical_roles']=roles
else:out['tetrahedra']=0
(r/'evidence/volume-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='physical_roles'},indent=2));gmsh.finalize()
