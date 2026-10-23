import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh,numpy as np
r=Path(__file__).parent;gmsh.initialize();out={}
for name,path in [('reviewed2d',Path('/workspace/shared/valve-step-grading-surface-20261023/fresh-local-surface.msh')),('actual3d',r/'fresh-local-surface.msh')]:
 gmsh.clear();gmsh.open(str(path));nt,cs,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.array(cs).reshape(-1,3))};faces={}
 for d,f in gmsh.model.getEntities(2):
  _,ts,ns=gmsh.model.mesh.getElements(2,f);rows=[]
  for tri in np.array(ns[0]).reshape(-1,3):rows.append(tuple(sorted(tuple(float(v) for v in pos[int(t)]) for t in tri)))
  faces[str(f)]={'triangles':len(rows),'coordinate_connectivity_sha256':hashlib.sha256(repr(sorted(rows)).encode()).hexdigest(),'physical_tags':gmsh.model.getPhysicalGroupsForEntity(2,f).tolist()}
 out[name]=faces
out['changed_faces']=[f for f in out['actual3d'] if out['actual3d'][f]!=out['reviewed2d'][f]];out['role_errors']=[f for f,v in out['actual3d'].items() if v['physical_tags']!=[int(f)]];out['actual_mesh_sha256']=hashlib.sha256((r/'fresh-local-surface.msh').read_bytes()).hexdigest();(r/'evidence/surface-identity.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['reviewed2d','actual3d']});gmsh.finalize()
