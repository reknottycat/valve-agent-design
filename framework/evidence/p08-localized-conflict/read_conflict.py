import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,json,numpy as np
from pathlib import Path
r=Path(__file__).resolve().parent
gmsh.initialize();gmsh.open(str(r/'failed-current.msh'))
ids=[29162,29134,30518,30569,30581]; result={'nodes':{},'containing_elements':[]}
for n in ids:
 c,pc,d,t=gmsh.model.mesh.getNode(n);result['nodes'][n]={'xyz':c.tolist(),'entity':[d,t]}
for d,t in gmsh.model.getEntities(2):
 types,tags,nds=gmsh.model.mesh.getElements(d,t)
 for typ,ts,ns in zip(types,tags,nds):
  if typ!=2:continue
  for et,verts in zip(ts,np.asarray(ns).reshape(-1,3)):
   match=set(int(v) for v in verts)&set(ids)
   if len(match)>=2:result['containing_elements'].append({'surface':t,'element':int(et),'nodes':[int(v) for v in verts]})
(r/'evidence/conflict-readback.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2));gmsh.finalize()
