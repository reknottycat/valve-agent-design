import os,sys,re,json,hashlib
os.environ['OPENBLAS_NUM_THREADS']='1';sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor')
import gmsh,numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
b=Path('/workspace/shared/valve-openfoam-quality-20261023/case/constant/polyMesh');out=Path(__file__).parent

def body(name):
 s=(b/name).read_text();return re.split(r'\n\s*\d+\s*\n\(',s,maxsplit=1)[1].rsplit(')',1)[0]
def labels(name):return np.fromstring(body(name),sep=' ',dtype=int)
pts=np.array([[float(v) for v in x.split()] for x in re.findall(r'\(([^()]+)\)',body('points'))])*1000
faces=np.array([[int(v) for v in x.split()] for x in re.findall(r'3\(([^()]+)\)',body('faces'))]);own=labels('owner');nei=labels('neighbour');assert len(faces)==len(own)
patches=[]
for name,block in re.findall(r'(\w+)\s*\{([^{}]+)\}',(b/'boundary').read_text()):
 n=re.search(r'nFaces\s+(\d+)',block);s=re.search(r'startFace\s+(\d+)',block)
 if n:patches.append((name,int(s[1]),int(n[1])))
patchid=np.zeros(len(faces),dtype=int)
for n,s,c in patches:patchid[s:s+c]=({'inlet':79,'outlet':34}[n] if n in ['inlet','outlet'] else int(n.rsplit('_',1)[1]))
source=Path('/workspace/shared/valve-two-pair-volume-20261023/fresh-local-surface.msh');gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();gmsh.merge(str(source));nt,cs,_=gmsh.model.mesh.getNodes();cs=np.array(cs).reshape(-1,3);dist,ix=cKDTree(cs).query(pts);assert dist.max()<1e-8
mapped=np.array(nt)[ix];ty,ids,nd=gmsh.model.mesh.getElements(3);tets=np.array(nd[0]).reshape(-1,4);ids=np.array(ids[0]);key={tuple(sorted(t)):i for i,t in enumerate(tets)}
cells=[set() for i in range(len(tets))]
for f,o in zip(faces,own):cells[o].update(mapped[f])
for f,n in zip(faces,nei):cells[n].update(mapped[f])
order=np.array([key[tuple(sorted(c))] for c in cells]);assert len(set(order.tolist()))==len(tets)
pos={int(t):p for t,p in zip(nt,cs)};xyz=np.array([[pos[int(n)] for n in t] for t in tets]);cent=xyz.mean(1);q=np.array(gmsh.model.mesh.getElementQualities(ids,'minSICN'));cellbound=[set() for i in cells]
for i in range(len(nei),len(faces)):cellbound[own[i]].add(int(patchid[i]))
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'native_cell_mapping':'Exact unordered tetra vertex connectivity after bijective coordinate matching; not assumed order','max_coordinate_match_error_mm':float(dist.max()),'sets':{}}
for name in ['underdeterminedCells','skewFaces','lowWeightFaces','lowVolRatioFaces','nonOrthoFaces']:
 vals=labels('sets/'+name);iscell=name.endswith('Cells');nc=vals if iscell else np.unique(np.r_[own[vals],nei[vals[vals<len(nei)]]]);gi=order[nc];hist={}
 for c in nc:
  for f in cellbound[c]:hist[str(f)]=hist.get(str(f),0)+1
 direct={} if iscell else {str(f):int((patchid[vals]==f).sum()) for f in np.unique(patchid[vals])}
 worst=nc[np.argsort(q[gi])[:10]]
 result['sets'][name]={'count':len(vals),'incident_cells':len(nc),'incident_cell_boundary_faces_nonexclusive':hist,'direct_face_patch_counts_0_internal':direct,'cell_centroid_z_quantiles_mm':np.percentile(cent[gi,2],[0,1,25,50,75,99,100]).tolist(),'minSICN_quantiles_incident_cells':np.percentile(q[gi],[0,1,50,99,100]).tolist(),'worst_minSICN_incident_cells':[{'native_cell':int(c),'gmsh_id':int(ids[order[c]]),'q':float(q[order[c]]),'centroid_mm':cent[order[c]].tolist(),'boundary_faces':sorted(cellbound[c])} for c in worst]}
result['cad_faces']={}
for f in range(118,127):
 lo,hi=gmsh.model.getParametrizationBounds(2,f);uv=np.array([[u,v] for u in np.linspace(lo[0],hi[0],21) for v in np.linspace(lo[1],hi[1],21)]);p=np.array(gmsh.model.getValue(2,f,uv.ravel())).reshape(-1,3);boundary=gmsh.model.getBoundary([(2,f)],False,False);ty,_,nd=gmsh.model.mesh.getElements(2,f);tri=np.array(nd[0]).reshape(-1,3);x=np.array([[pos[int(n)] for n in t] for t in tri]);edges=np.array([np.linalg.norm(x[:,a]-x[:,bb],axis=1) for a,bb in [(0,1),(0,2),(1,2)]]);area=np.linalg.norm(np.cross(x[:,1]-x[:,0],x[:,2]-x[:,0]),axis=1)/2;aspect=edges.max(0)**2/(2*area)
 result['cad_faces'][str(f)]={'type':gmsh.model.getType(2,f),'bbox_mm':gmsh.model.getBoundingBox(2,f),'sample_untrimmed_z_range_mm':[float(p[:,2].min()),float(p[:,2].max())],'boundary_curves':[{'tag':t,'type':gmsh.model.getType(d,t),'length_mm':gmsh.model.occ.getMass(d,t),'bbox_mm':gmsh.model.getBoundingBox(d,t)} for d,t in boundary],'surface_triangles':len(tri),'triangle_aspect_longest_edge_over_min_altitude_quantiles':np.percentile(aspect,[0,50,95,99,100]).tolist(),'edge_length_quantiles_mm':np.percentile(edges,[0,1,50,99,100]).tolist()}
# Domain membership is a bounded sampling test, not a global thickness certificate.
result['fluid_domain_samples']=[{'r_mm':r,'z_mm':z,'inside_volume1':bool(gmsh.model.isInside(3,1,[300+r,0,z]))} for r in [100,105,106,108,110,111,115] for z in [78.9,79.0001,79.01,79.1,79.35,80,82,83.4,83.6]]
(out/'report.json').write_text(json.dumps(result,indent=2));gmsh.finalize();print('DONE')
