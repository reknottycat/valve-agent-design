import sys,json
from pathlib import Path
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor')
import gmsh,numpy as np
r=Path(__file__).parent;gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();gmsh.merge('/workspace/shared/valve-cone-grading-volume-20261023/fresh-local-surface.msh');nt,cs,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.array(cs).reshape(-1,3))};out={}
for f in [36,37,39,41,43,45,47,122]:
 _,_,nd=gmsh.model.mesh.getElements(2,f);tr=np.array(nd[0]).reshape(-1,3);x=np.array([[pos[int(n)] for n in t] for t in tr]);edges=np.array([np.linalg.norm(x[:,a]-x[:,b],axis=1) for a,b in [(0,1),(1,2),(2,0)]]);area=np.linalg.norm(np.cross(x[:,1]-x[:,0],x[:,2]-x[:,0]),axis=1)/2
 curves=[]
 for _,c in gmsh.model.getBoundary([(2,f)],combined=False,oriented=False):
  _,_,ns=gmsh.model.mesh.getElements(1,c);ex=np.array([[pos[int(n)] for n in e] for e in np.array(ns[0]).reshape(-1,2)]);el=np.linalg.norm(ex[:,1]-ex[:,0],axis=1);curves.append({'curve':c,'type':gmsh.model.getType(1,c),'adjacent_faces':gmsh.model.getAdjacencies(1,c)[0].tolist(),'mesh_edge_count':len(el),'mesh_edge_length_percentiles_mm':np.percentile(el,[0,50,100]).tolist()})
 out[f]={'type':gmsh.model.getType(2,f),'triangles':len(tr),'bbox_mm':gmsh.model.getBoundingBox(2,f),'triangle_aspect_percentiles':np.percentile(edges.max(0)**2/(2*area),[0,50,95,100]).tolist(),'edge_length_percentiles_mm':np.percentile(edges,[0,50,95,100]).tolist(),'uncombined_boundary':curves}
(r/'feature-scales.json').write_text(json.dumps(out,indent=2));gmsh.finalize()
