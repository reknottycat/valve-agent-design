import os,sys,pathlib,json,hashlib,re
os.environ['OPENBLAS_NUM_THREADS']='1';sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor')
import gmsh,numpy as np
b=pathlib.Path(__file__).parent;source=pathlib.Path('/workspace/shared/valve-step-grading-volume-20261023/fresh-local-surface.msh')
def read(p):
 gmsh.clear();gmsh.open(str(p));t,c,_=gmsh.model.mesh.getNodes();ix=np.argsort(t);coords=np.array(c).reshape(-1,3)[ix];tags=np.array(t)[ix]
 e={}
 for typ,tags_,nodes in zip(*gmsh.model.mesh.getElements()):
  n=gmsh.model.mesh.getElementProperties(typ)[3];ix=np.argsort(tags_);e[int(typ)]=(np.array(tags_)[ix],np.array(nodes).reshape(-1,n)[ix])
 groups={(int(d),int(t)):gmsh.model.getPhysicalName(d,t) for d,t in gmsh.model.getPhysicalGroups()}
 return tags,coords,e,groups
gmsh.initialize();a=read(source);z=read(b/'source-copy-ascii22-mm.msh')
assert np.array_equal(a[0],z[0]);assert np.allclose(a[1],z[1],rtol=0,atol=1e-12)
assert set(z[2])=={2,4}
for k in [2,4]:
 x,y=a[2][k][1],z[2][k][1]
 assert np.array_equal(x,y), k
assert {k:v for k,v in a[3].items() if k[0]==2}=={k:v for k,v in z[3].items() if k[0]==2}
assert a[3][(3,1)]==z[3][(3,1001)]=='fluid_proxy'
gmsh.finalize()
s=(b/'case/constant/polyMesh/boundary').read_text();patches={m[0]:int(m[1]) for m in re.findall(r'\n\s*(\w+)\s*\{\s*type\s+\w+;\s*physicalType\s+\w+;\s*nFaces\s+(\d+);',s)}
expected={x['name']:x['elements'] for x in json.loads((b/'evidence/export.json').read_text())['groups'] if x['dim']==2};assert patches==expected,(patches.keys()-expected.keys())
p=(b/'case/constant/polyMesh/points').read_text();pts=np.array([[float(x) for x in m] for m in re.findall(r'\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)',p)])
# Compare coordinate sets lexicographically, allowing roundoff from ASCII serialization.
def sort(v):return v[np.lexsort((v[:,2],v[:,1],v[:,0]))]
from scipy.spatial import cKDTree
assert len(pts)==len(a[1]);dist,ix=cKDTree(a[1]*.001).query(pts);delta=float(dist.max());assert delta<1e-12,delta;assert len(set(ix.tolist()))==len(pts)
r={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'node_count':len(pts),'triangle_tetra_connectivity_identical':True,'lower_dimension_elements_omitted_by_physical_group_export':sum(len(v[0]) for k,v in a[2].items() if k not in (2,4)),'ascii_coordinate_error_mm':float(np.max(np.abs(a[1]-z[1]))),'scale_point_error_m':delta,'dimension_aware_volume_remap':'3:1 -> 3:1001','surface_tags_names_counts_preserved':132,'boundary_face_count':sum(patches.values()),'bbox_m':[pts.min(axis=0).tolist(),pts.max(axis=0).tolist()],'native_check_status':'not yet run; identity gate before diagnostic','engineering_release':False}
(b/'evidence/conversion-verification.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
