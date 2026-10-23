import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,json,numpy as np
from pathlib import Path
r=Path(__file__).resolve().parent
j=json.loads((r/'evidence/conflict-readback.json').read_text());n=j['nodes'];a=np.array(n['29162']['xyz']);b=np.array(n['29134']['xyz']);v0=np.array(n['30518']['xyz']);v1=np.array(n['30569']['xyz']);v2=np.array(n['30581']['xyz']);t,u,v=np.linalg.solve(np.column_stack([b-a,-(v1-v0),-(v2-v0)]),v0-a);q=a+t*(b-a)
gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize()
out={'intersection_mm':q.tolist(),'segment_t':t,'triangle_barycentric':[1-u-v,u,v],'surfaces':{}}
for sid in [64,108]:
 point,params=gmsh.model.getClosestPoint(2,sid,q)
 out['surfaces'][sid]={'type':gmsh.model.getType(2,sid),'bbox':gmsh.model.occ.getBoundingBox(2,sid),'closest_on_CAD_mm':point.tolist(),'intersection_to_CAD_distance_mm':float(np.linalg.norm(q-point))}
print(json.dumps(out,indent=2));(r/'evidence/analytic-local-check.json').write_text(json.dumps(out,indent=2)+'\n');gmsh.finalize()
