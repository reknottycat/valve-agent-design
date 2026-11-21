import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,numpy as np,json,csv,hashlib,math
from pathlib import Path
r=Path(__file__).resolve().parent;source=Path('/workspace/shared/valve-two-pair-volume-20261023/fresh-local-surface.msh');sha=hashlib.sha256(source.read_bytes()).hexdigest();gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();gmsh.merge(str(source));types,tags,ns=gmsh.model.mesh.getElements(3);tet=np.array(ns[0]).reshape(-1,4);ids=np.array(tags[0]);nt,cs,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.array(cs).reshape(-1,3))};xyz=np.array([[pos[int(n)] for n in row] for row in tet]);cent=xyz.mean(axis=1);q=np.array(gmsh.model.mesh.getElementQualities(ids,'minSICN'));vol=np.einsum('ij,ij->i',np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),xyz[:,3]-xyz[:,0])/6;edge=np.array([np.linalg.norm(xyz[:,a]-xyz[:,b],axis=1) for a,b in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]]);areas=np.array([np.linalg.norm(np.cross(xyz[:,b]-xyz[:,a],xyz[:,c]-xyz[:,a]),axis=1)/2 for a,b,c in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]]);alt=3*vol/areas.max(axis=0);aspect=edge.max(axis=0)/alt
mapping=json.loads(Path('/workspace/shared/valve-two-pair-volume-20261023/evidence/geometry.json').read_text())['mapping'];family={m['gmsh_surface']:m['family'] for m in mapping};face_map={}
for _,f in gmsh.model.getEntities(2):
 ty,_,nd=gmsh.model.mesh.getElements(2,f)
 for t,ar in zip(ty,nd):
  if t==2:
   for row in ar.reshape(-1,3):face_map[tuple(sorted(int(n) for n in row))]=f
order=np.argsort(q);nlow=math.ceil(len(q)*.01);low=order[:nlow];tail_families={};records=[]
for rank,i in enumerate(low):
 bs=[]
 for a,b,c in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]:
  f=face_map.get(tuple(sorted(int(n) for n in tet[i,[a,b,c]])))
  if f is not None:bs.append(f)
 fam=sorted({family[f] for f in bs})
 for x in fam or ['no_boundary_face']:tail_families[x]=tail_families.get(x,0)+1
 if rank<100:
  projection=[]
  for _,f in gmsh.model.getEntities(2):
   p,uv=gmsh.model.getClosestPoint(2,f,cent[i]);inside=gmsh.model.isInside(2,f,uv,True)
   bbox=np.array(gmsh.model.occ.getBoundingBox(2,f)); in_bbox=np.all(p>=bbox[:3]-1e-6) and np.all(p<=bbox[3:]+1e-6)
   if inside and in_bbox:projection.append((float(np.linalg.norm(p-cent[i])),f))
  near=sorted(projection)[:3]
 else:near=[]
 records.append({'rank':rank+1,'element_id':int(ids[i]),'minSICN':float(q[i]),'signed_volume_mm3':float(vol[i]),'longest_edge_mm':float(edge[:,i].max()),'shortest_edge_mm':float(edge[:,i].min()),'minimum_altitude_mm':float(alt[i]),'defined_aspect_longest_edge_over_min_altitude':float(aspect[i]),'centroid_mm':cent[i].tolist(),'boundary_faces':bs,'boundary_families':fam,'nearest_CAD_projection_candidates_bbox_param_filtered':[{'face':f,'family':family[f],'distance_mm':d} for d,f in near]})
rho=np.hypot(cent[:,0]-300,cent[:,1]);z=cent[:,2];windows={'retainer_radial23p9_24_z104_106':(rho>=23.9)&(rho<=24)&(z>=104)&(z<=106),'guide_radial31_32_z96_197':(rho>=31)&(rho<=32)&(z>=96)&(z<=197)}
summary={'mesh_sha256_before':sha,'tetrahedra':len(q),'logged_ill_shaped_count':172,'logged_ill_shaped_ids_available':False,'diagnostic_thresholds_not_acceptance':{str(t):int((q<t).sum()) for t in [.005,.01,.02,.05,.1]},'lowest_one_percent_count':nlow,'lowest_one_percent_boundary_families_nonexclusive':tail_families,'quality_quantiles':np.percentile(q,[0,1,5,50,95,100]).tolist(),'aspect_definition':'longest tetra edge / minimum tetra altitude, NOT a standardized OpenFOAM metric','aspect_quantiles':np.percentile(aspect,[0,50,95,99,100]).tolist(),'geometric_windows_not_full_feature_classification':{name:{'all_count':int(mask.sum()),'lowest_1pct_count':int(mask[low].sum()),'q_min':float(q[mask].min()) if mask.any() else None} for name,mask in windows.items()},'worst_100':records[:100],'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==sha,'engineering_release':False};(r/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(r/'lowest-one-percent.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='worst_100'},indent=2));gmsh.finalize()
