import sys,json,numpy as np,math
from pathlib import Path
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor');import gmsh
from cone_law import *
r=Path(__file__).parent;gmsh.initialize();out={};targets=list(range(1,133))
for label,path in [('baseline',Path('/workspace/shared/valve-cone-grading-20261023/fresh-local-surface.msh')),('graded',r/'fresh-local-surface.msh')]:
 gmsh.clear();gmsh.open(str(path));nt,cs,_=gmsh.model.mesh.getNodes();pos={int(t):p for t,p in zip(nt,np.array(cs).reshape(-1,3))};out[label]={}
 for f in targets:
  _,ts,ns=gmsh.model.mesh.getElements(2,f);tri=np.array(ns[0]).reshape(-1,3);xyz=np.array([[pos[int(n)] for n in t] for t in tri]);ed=np.array([np.linalg.norm(xyz[:,a]-xyz[:,b],axis=1) for a,b in [(0,1),(0,2),(1,2)]]);area=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)/2;aspect=ed.max(0)**2/(2*area);seen={};rat=[]
  for i,t in enumerate(tri):
   for a,b in [(0,1),(0,2),(1,2)]:
    k=tuple(sorted([int(t[a]),int(t[b])]))
    if k in seen:
     j=seen[k];rat.append(max(ed[:,i].mean(),ed[:,j].mean())/min(ed[:,i].mean(),ed[:,j].mean()))
    else:seen[k]=i
  v={'triangles':len(tri),'aspect_quantiles_min_median_P95_P99_max':np.percentile(aspect,[0,50,95,99,100]).tolist(),'aspect_above10_descriptive':int((aspect>10).sum()),'adjacent_mean_edge_ratio_quantiles':np.percentile(rat,[0,50,95,99,100]).tolist(),'edge_length_quantiles_mm':np.percentile(ed,[0,5,50,95,100]).tolist()}
  if f in [120,124]:
   R0,R1=(110.52157987653936,111.74220957771) if f==120 else (105.47842012345052,104.25779042229)
   def dev(p):return np.abs(np.hypot(p[...,0]-300,p[...,1])-(R0+(R1-R0)*(p[...,2]-Z0)/(Z1-Z0)))
   v['cone_vertex_radial_error_max_mm']=float(dev(xyz).max());samples=np.concatenate([xyz,xyz.mean(1)[:,None,:],((xyz[:,0]+xyz[:,1])/2)[:,None,:],((xyz[:,0]+xyz[:,2])/2)[:,None,:],((xyz[:,1]+xyz[:,2])/2)[:,None,:]],axis=1);v['sampled_facet_radial_error_max_mm_NOT_full_facet_bound']=float(dev(samples).max());s=(xyz.mean(1)[:,2]-Z0)*L/(Z1-Z0);v['slant_band_edges']=[]
   for lo,hi in [(0,.25),(.25,.5),(.5,1),(1,2),(2,L+1e-9)]:
    m=(s>=lo)&(s<hi);v['slant_band_edges'].append({'slant_mm':[lo,hi],'triangles':int(m.sum()),'edge_percentiles':np.percentile(ed[:,m],[0,50,95,100]).tolist() if m.any() else []})
  out[label][str(f)]=v
(r/'evidence/comparison.json').write_text(json.dumps(out,indent=2));gmsh.finalize();print('done')
