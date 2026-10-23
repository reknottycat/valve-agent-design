import sys,json,math
from pathlib import Path
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh,numpy as np
sys.path.insert(0,'/workspace/shared/valve-cone-grading-volume-20261023');from volume_law import distance,CUTOFF
r=Path(__file__).parent;gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();out={'faces':{},'samples':[]};curves=set();adj=set()
for f in [37,39,41,43,45,47]:
 bd=gmsh.model.getBoundary([(2,f)],combined=False,oriented=False);curves.update(t for d,t in bd);lo,hi=gmsh.model.getParametrizationBounds(2,f);p=np.array(gmsh.model.getValue(2,f,[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2]));rho=math.hypot(p[0]-300,p[1]);th=math.atan2(p[1],p[0]-300)
 out['faces'][f]={'midpoint_mm':p.tolist(),'radius_mm':rho,'theta_rad':th,'param_bounds':[lo.tolist(),hi.tolist()],'boundary_curves':[t for d,t in bd]}
 for z in [21.94,21.975,22.01]:
  for delta in [-.1,-.01,.01,.1]:
   x=300+(rho+delta)*math.cos(th);y=(rho+delta)*math.sin(th);out['samples'].append({'face':f,'r_delta_mm':delta,'z_mm':z,'inside_proxy':bool(gmsh.model.isInside(3,1,[x,y,z])),'existing_volume_law_distance_mm':distance(x,y,z)})
for c in curves:adj.update(gmsh.model.getAdjacencies(1,c)[0].tolist())
out['all_step_curves']=sorted(curves);out['adjacent_conformal_faces']=sorted(adj);out['curve_audit']={c:{'type':gmsh.model.getType(1,c),'length_mm':gmsh.model.occ.getMass(1,c),'adjacent_faces':gmsh.model.getAdjacencies(1,c)[0].tolist(),'bbox_mm':gmsh.model.getBoundingBox(1,c)} for c in sorted(curves)}
out['adjacent_face_geometry']={f:{'type':gmsh.model.getType(2,f),'area_mm2':gmsh.model.occ.getMass(2,f),'all_boundary_curves':[t for d,t in gmsh.model.getBoundary([(2,f)],combined=False,oriented=False)],'bbox_mm':gmsh.model.getBoundingBox(2,f)} for f in sorted(adj)}
out['volume_law_cutoff_mm']=CUTOFF;out['limitations']='Domain point probes classify only these sample locations, not a global fluid thickness or manufacturing intent.'
(r/'audit.json').write_text(json.dumps(out,indent=2));gmsh.finalize()
