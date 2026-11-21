import gmsh,json,math
from pathlib import Path
r=Path(__file__).resolve().parent;j=json.loads((r/'evidence/local-domain-classification.json').read_text());gmsh.initialize();gmsh.open(str(r/'failed-current.msh'));out=[]
for face,edges in j['face_boundary_curves'].items():
 radius=32 if face=='64' else 31
 for e in edges:
  types,tags,ns=gmsh.model.mesh.getElements(1,e);worst=0;count=0
  for typ,vs in zip(types,ns):
   if typ!=1:continue
   for a,b in zip(vs[::2],vs[1::2]):
    x=gmsh.model.mesh.getNode(int(a))[0];y=gmsh.model.mesh.getNode(int(b))[0];chord=math.hypot(x[0]-y[0],x[1]-y[1]);sag=radius-math.sqrt(max(0,radius**2-chord**2/4));worst=max(worst,sag);count+=1
  out.append({'face':int(face),'curve':e,'line_elements':count,'max_cylindrical_chord_sag_mm':worst})
(r/'evidence/boundary-chord-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));gmsh.finalize()
