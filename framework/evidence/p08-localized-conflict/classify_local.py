import resource
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,json,math
from pathlib import Path
r=Path(__file__).resolve().parent;gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize()
a=math.atan2(21.856025193,21.960384357);res={'samples':[],'oriented_volume_boundary':[list(t) for t in gmsh.model.getBoundary([(3,1)],oriented=True) if abs(t[1]) in [64,108]],'face_boundary_curves':{},'boundary_curve_adjacent_faces':{}}
for radius in [30.5,31.25,31.5,31.75,32.5]:
 xyz=[300+radius*math.cos(a),radius*math.sin(a),136.859083224];res['samples'].append({'radius_mm':radius,'xyz_mm':xyz,'inside_volume_1':gmsh.model.isInside(3,1,xyz)})
for sid in [64,108]:
 boundary=gmsh.model.getBoundary([(2,sid)],oriented=False);res['face_boundary_curves'][sid]=[t for d,t in boundary]
 for d,t in boundary:res['boundary_curve_adjacent_faces'][t]=gmsh.model.getAdjacencies(d,t)[0].tolist()
print(json.dumps(res,indent=2));(r/'evidence/local-domain-classification.json').write_text(json.dumps(res,indent=2)+'\n');gmsh.finalize()
