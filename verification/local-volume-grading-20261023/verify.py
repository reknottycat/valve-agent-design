import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,numpy as np,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;gmsh.initialize();gmsh.open(str(r/'fresh-local-surface.msh'));nt,cs,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.asarray(cs).reshape(-1,3))};res={'cylinders':{},'faces':{}};alltris=[]
for d,t in gmsh.model.getEntities(2):
 ty,ts,ns=gmsh.model.mesh.getElements(d,t);tri=np.concatenate([v.reshape(-1,3) for typ,v in zip(ty,ns) if typ==2]);alltris.append(tri)
 xyz=np.array([[pos[int(v)] for v in row] for row in tri]);areas=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)/2
 res['faces'][t]={'triangles':len(tri),'min_area_mm2':float(areas.min()),'degenerate_triangles':int((areas<=1e-12).sum())}
 if t not in [64,108,103,127]:continue
 R={64:32,108:31,103:24,127:23.9}[t];budget=.02 if t in [103,127] else .2;p=xyz[:,:,:2]-[300,0];mind=np.full(len(p),np.inf);crosses=[];edge_sags=[]
 for i,j in [(0,1),(1,2),(2,0)]:
  a=p[:,i];b=p[:,j];v=b-a;den=np.sum(v*v,axis=1);u=np.divide(-np.sum(a*v,axis=1),den,out=np.zeros(len(p)),where=den>0);u=np.clip(u,0,1);dist=np.linalg.norm(a+u[:,None]*v,axis=1);mind=np.minimum(mind,dist);crosses.append(a[:,0]*b[:,1]-a[:,1]*b[:,0]);edge_sags.extend((R-dist).tolist())
 crosses=np.array(crosses);inside=(np.all(crosses>=0,axis=0)|np.all(crosses<=0,axis=0));mind[inside]=0
 maxr=float(np.linalg.norm(p,axis=2).max());minr=float(mind.min());worst_idx=int(np.argmin(mind)); worst_nodes=[int(n) for n in tri[worst_idx]]; worst_info=[{'node':n,'xyz':pos[n].tolist(),'entity':list(gmsh.model.mesh.getNode(n)[2:])} for n in worst_nodes]; res['cylinders'][t]={'worst_triangle_nodes':worst_info,'radius_mm':R,'min_radius_entire_linear_facets_mm':minr,'max_radius_entire_linear_facets_mm':maxr,'max_inward_error_entire_facets_mm':R-minr,'max_inward_edge_error_mm':max(edge_sags),'max_vertex_radial_error_mm':float(np.abs(np.linalg.norm(p,axis=2)-R).max()),'budget_mm':budget,'facets_over_budget':int(((R-mind)>budget).sum()),'research_budget_pass':bool((R-minr)<=budget)}
tri=np.concatenate(alltris);edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True);res['edge_incidence_histogram']={str(int(k)):int((counts==k).sum()) for k in np.unique(counts)}
res['pair_radial_separation_lower_bound_mm']=res['cylinders'][64]['min_radius_entire_linear_facets_mm']-res['cylinders'][108]['max_radius_entire_linear_facets_mm'];res['retainer_radial_separation_lower_bound_mm']=res['cylinders'][103]['min_radius_entire_linear_facets_mm']-res['cylinders'][127]['max_radius_entire_linear_facets_mm'];res['pair_disjoint_by_radial_bounds']=res['pair_radial_separation_lower_bound_mm']>0
old=json.loads(Path('/workspace/shared/valve-gmsh-trial-20261023/evidence/surface.json').read_text());res['per_face_count_changes_from_old_fresh_baseline']={m['gmsh_surface']:res['faces'][m['gmsh_surface']]['triangles']-m['triangles'] for m in old['faces'] if res['faces'][m['gmsh_surface']]['triangles']!=m['triangles']};res['engineering_release']=False
(r/'evidence/verification.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='faces'},indent=2));gmsh.finalize()
