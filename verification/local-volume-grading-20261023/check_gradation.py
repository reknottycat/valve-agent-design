import sys,resource,json,gc
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
from pathlib import Path
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh,numpy as np
from volume_law import ARCS,CUTOFF,H0
r=Path(__file__).parent
def dist(x):
 rho=np.hypot(x[:,0]-300,x[:,1]);z=x[:,2];ds=[]
 for R,Z,a,lo,hi in ARCS:
  dr=rho-R;dz=z-Z;t=lo+(np.arctan2(dz,dr)-lo)%(2*np.pi);projection=abs(np.hypot(dr,dz)-a);end=np.minimum(np.hypot(rho-(R+a*np.cos(lo)),z-(Z+a*np.sin(lo))),np.hypot(rho-(R+a*np.cos(hi)),z-(Z+a*np.sin(hi))));ds.append(np.where(t<=hi,projection,end))
 return np.minimum(*ds)
bounds=[0,.1,.25,.5,1,2,5,10,CUTOFF,float('inf')];out={'classification':'distance of edge midpoint to finite toroidal surfaces; six edges per tetra, shared edges counted repeatedly','units':'mm','bins':bounds[:-1]+['infinity']};gmsh.initialize()
for label,path in [('previous',Path('/workspace/shared/valve-boundary-grading-volume-20261023/fresh-local-surface.msh')),('volume_graded',r/'fresh-local-surface.msh')]:
 gmsh.clear();gmsh.open(str(path));nt,co,_=gmsh.model.mesh.getNodes();coord=np.array(co).reshape(-1,3);nt=np.array(nt);order=np.argsort(nt);nt=nt[order];coord=coord[order];_,_,ns=gmsh.model.mesh.getElements(3);tet=np.array(ns[0]).reshape(-1,4);xyz=coord[np.searchsorted(nt,tet)];groups=[[] for _ in bounds[:-1]]
 for a,b in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
  midpoint=(xyz[:,a]+xyz[:,b])/2;d=dist(midpoint);length=np.linalg.norm(xyz[:,a]-xyz[:,b],axis=1)
  for i,(lo,hi) in enumerate(zip(bounds,bounds[1:])):groups[i].append(length[(d>=lo)&(d<hi)])
 out[label]=[]
 for i,arrs in enumerate(groups):
  v=np.concatenate(arrs);out[label].append({'distance_band_mm':[bounds[i],bounds[i+1] if np.isfinite(bounds[i+1]) else 'infinity'],'tetra_edge_occurrences':len(v),'edge_length_quantiles_mm':np.percentile(v,[0,5,50,95,100]).tolist() if len(v) else []})
 del xyz,groups,coord;gc.collect()
(r/'evidence/gradation-readback.json').write_text(json.dumps(out,indent=2));gmsh.finalize();print('gradation readback complete')
