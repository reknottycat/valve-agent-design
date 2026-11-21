import os,sys,re,json,hashlib
os.environ['OPENBLAS_NUM_THREADS']='1';sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor')
import gmsh,numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
b=Path('/workspace/shared/valve-cone-grading-native-20261023/case/constant/polyMesh');out=Path(__file__).parent

def body(name):
 s=(b/name).read_text();return re.split(r'\n\s*\d+\s*\n\(',s,maxsplit=1)[1].rsplit(')',1)[0]
def labels(name):
 if not (b/name).exists():return np.array([],dtype=int)
 return np.fromstring(body(name),sep=' ',dtype=int)
pts=np.array([[float(v) for v in x.split()] for x in re.findall(r'\(([^()]+)\)',body('points'))])*1000
faces=np.array([[int(v) for v in x.split()] for x in re.findall(r'3\(([^()]+)\)',body('faces'))]);own=labels('owner');nei=labels('neighbour');assert len(faces)==len(own)
patches=[]
for name,block in re.findall(r'(\w+)\s*\{([^{}]+)\}',(b/'boundary').read_text()):
 n=re.search(r'nFaces\s+(\d+)',block);s=re.search(r'startFace\s+(\d+)',block)
 if n:patches.append((name,int(s[1]),int(n[1])))
patchid=np.zeros(len(faces),dtype=int)
for n,s,c in patches:patchid[s:s+c]=({'inlet':79,'outlet':34}[n] if n in ['inlet','outlet'] else int(n.rsplit('_',1)[1]))
source=Path('/workspace/shared/valve-cone-grading-volume-20261023/fresh-local-surface.msh');gmsh.initialize();gmsh.model.occ.importShapes('/workspace/scratch/634aa36792d6/attachments/2618578e-bbba-4a39-81cb-899300c65163/AGR1_open_seal_omitted_proxy_main_mm.step');gmsh.model.occ.synchronize();gmsh.merge(str(source));nt,cs,_=gmsh.model.mesh.getNodes();cs=np.array(cs).reshape(-1,3);dist,ix=cKDTree(cs).query(pts);assert dist.max()<1e-8
mapped=np.array(nt)[ix];ty,ids,nd=gmsh.model.mesh.getElements(3);tets=np.array(nd[0]).reshape(-1,4);ids=np.array(ids[0]);key={tuple(sorted(t)):i for i,t in enumerate(tets)}
cells=[set() for i in range(len(tets))]
for f,o in zip(faces,own):cells[o].update(mapped[f])
for f,n in zip(faces,nei):cells[n].update(mapped[f])
order=np.array([key[tuple(sorted(c))] for c in cells]);assert len(set(order.tolist()))==len(tets)
pos={int(t):p for t,p in zip(nt,cs)};xyz=np.array([[pos[int(n)] for n in t] for t in tets]);cent=xyz.mean(1);q=np.array(gmsh.model.mesh.getElementQualities(ids,'minSICN'));cellbound=[set() for i in cells]
for i in range(len(nei),len(faces)):cellbound[own[i]].add(int(patchid[i]))
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'native_cell_mapping':'Exact unordered tetra vertex connectivity after bijective coordinate matching; not assumed order','max_coordinate_match_error_mm':float(dist.max()),'sets':{}}
for name in ['underdeterminedCells','skewFaces','lowWeightFaces','lowVolRatioFaces','nonOrthoFaces']:
 vals=labels('sets/'+name)
 if not len(vals):
  result['sets'][name]={'count':0};continue
 iscell=name.endswith('Cells');nc=vals if iscell else np.unique(np.r_[own[vals],nei[vals[vals<len(nei)]]]);gi=order[nc];hist={}
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

# Full records for all native skew faces, with explicit owner/neighbour geometry.
result['all_native_skew_faces']=[]
for fi in labels('sets/skewFaces'):
 owner=int(own[fi]); neighbor=int(nei[fi]) if fi<len(nei) else None
 fx=pts[faces[fi]];fc=fx.mean(0);normal=np.cross(fx[1]-fx[0],fx[2]-fx[0]);area=float(np.linalg.norm(normal)/2);normal=normal/np.linalg.norm(normal);oc=cent[order[owner]];delta=fc-oc;normal_h=float(abs(np.dot(delta,normal)));tangent=float(np.linalg.norm(delta-np.dot(delta,normal)*normal));ed=np.array([np.linalg.norm(fx[a]-fx[b]) for a,b in [(0,1),(0,2),(1,2)]])
 result['all_native_skew_faces'].append({'native_face':int(fi),'kind':'internal' if neighbor is not None else 'boundary','source_CAD_face':int(patchid[fi]) or None,'vertices_mm':fx.tolist(),'face_centroid_mm':fc.tolist(),'unit_normal_from_stored_vertex_order':normal.tolist(),'area_mm2':area,'edge_lengths_mm':ed.tolist(),'triangle_ratio_longest_edge_over_min_altitude':float(ed.max()**2/(2*area)),'owner_native_cell':owner,'owner_gmsh_cell':int(ids[order[owner]]),'owner_centroid_mm':oc.tolist(),'owner_minSICN':float(q[order[owner]]),'owner_vertices_mm':xyz[order[owner]].tolist(),'owner_normal_height_mm':normal_h,'owner_tangential_offset_mm':tangent,'diagnostic_tangent_over_normal_not_native_skewness':tangent/normal_h,'neighbour_native_cell':neighbor,'neighbour_centroid_mm':cent[order[neighbor]].tolist() if neighbor is not None else None})
result['residual_feature_CAD']={}
for f in list(range(36,49))+[103,120,124,127]:
 result['residual_feature_CAD'][str(f)]={'type':gmsh.model.getType(2,f),'bbox_mm':gmsh.model.getBoundingBox(2,f),'area_mm2':gmsh.model.occ.getMass(2,f),'boundary_curves':[{'curve':t,'type':gmsh.model.getType(d,t),'length_mm':gmsh.model.occ.getMass(d,t),'bbox_mm':gmsh.model.getBoundingBox(d,t),'adjacent_faces':gmsh.model.getAdjacencies(d,t)[0].tolist()} for d,t in gmsh.model.getBoundary([(2,f)],False,False)]}
result['badset_unique_cells_touching_cones_or_tori']={}
for name in ['underdeterminedCells','skewFaces','lowWeightFaces','lowVolRatioFaces','nonOrthoFaces']:
 vals=labels('sets/'+name);nc=vals if name.endswith('Cells') else np.unique(np.r_[own[vals],nei[vals[vals<len(nei)]]]);result['badset_unique_cells_touching_cones_or_tori'][name]={'incident_cells':len(nc),'touches120or124':sum(bool(cellbound[c]&{120,124}) for c in nc),'touches119or125':sum(bool(cellbound[c]&{119,125}) for c in nc),'no_boundary_face':sum(not cellbound[c] for c in nc)}


# Number of actual boundary triangle faces per cell, not number of CAD roles.
bcount=np.bincount(own[len(nei):],minlength=len(tets))
internal_count=np.bincount(np.r_[own[:len(nei)],nei],minlength=len(tets))
assert np.all(bcount+internal_count==4)
struct={}
for name in ['underdeterminedCells','lowWeightFaces','lowVolRatioFaces','nonOrthoFaces']:
 vals=labels('sets/'+name); nc=vals if name.endswith('Cells') else np.unique(np.r_[own[vals],nei[vals[vals<len(nei)]]])
 groups={}
 for bc in np.unique(bcount[nc]):
  sub=nc[bcount[nc]==bc];hist={}
  for c in sub:
   for f in cellbound[c]:hist[str(f)]=hist.get(str(f),0)+1
  groups[str(int(bc))]={'count':len(sub),'boundary_roles_nonexclusive':hist,'minSICN_percentiles':np.percentile(q[order[sub]],[0,1,50,99,100]).tolist()}
 struct[name]=groups
result['actual_boundary_face_count_groups']=struct
result['all_mesh_boundary_face_count_histogram']={str(int(k)):int((bcount==k).sum()) for k in np.unique(bcount)}
result['lowdet_non_double_boundary_records']=[{'native_cell':int(c),'gmsh_id':int(ids[order[c]]),'boundary_triangle_count':int(bcount[c]),'CAD_boundary_roles':sorted(cellbound[c]),'centroid_mm':cent[order[c]].tolist(),'minSICN':float(q[order[c]])} for c in labels('sets/underdeterminedCells') if bcount[c]<2]
result['input_hashes']={str(p.relative_to(b)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(b.rglob('*')) if p.is_file()}

(out/'report.json').write_text(json.dumps(result,indent=2));gmsh.finalize();print('DONE')
