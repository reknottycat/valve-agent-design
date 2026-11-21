import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import collections,hashlib,json,resource,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
import gmsh,numpy as np
root=Path(__file__).resolve().parent;start=time.monotonic();p=root/'surface.msh';s=json.loads((root/'evidence/surface.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==s['msh_sha256']
gmsh.initialize(['readback','-nopopup']);gmsh.open(str(p));nt,xyz,_=gmsh.model.mesh.getNodes();xyz=np.array(xyz).reshape(-1,3);lookup={int(n):i for i,n in enumerate(nt)}
types,tags,nodes=gmsh.model.mesh.getElements(2);assert list(types)==[2];tri=np.array(nodes[0]).reshape(-1,3)
edges=collections.Counter();parent={int(n):int(n) for n in nt}
def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
for a,b,c in tri:
 a,b,c=int(a),int(b),int(c)
 for x,y in [(a,b),(b,c),(c,a)]:
  edges[tuple(sorted((x,y)))]+=1;rx,ry=find(x),find(y)
  if rx!=ry:parent[rx]=ry
incidence=collections.Counter(edges.values());components=len({find(int(n)) for n in tri.flat});groups=gmsh.model.getPhysicalGroups(2)
missing=[]
for face in s['faces']:
 group=face['source_face'];ents=gmsh.model.getEntitiesForPhysicalGroup(2,group)
 if len(ents)!=1 or int(ents[0])!=face['gmsh_surface'] or gmsh.model.getPhysicalName(2,group)!=face['role']:missing.append(group)
positions=xyz[np.array([lookup[int(n)] for n in tri.flat]).reshape(-1,3)]
vol=float(np.einsum('ij,ij->i',positions[:,0],np.cross(positions[:,1],positions[:,2])).sum()/6)
component_volumes=collections.defaultdict(float)
for face,points in zip(tri,positions):component_volumes[find(int(face[0]))]+=float(np.dot(points[0],np.cross(points[1],points[2]))/6)
report={'component_oriented_volumes_mm3':sorted(component_volumes.values()),'surface_sha256':s['msh_sha256'],'saved_msh_reopened':True,'triangles':len(tri),'nodes':len(nt),'physical_surface_groups':len(groups),'physical_group_mismatches':missing,'edge_incidence_counts':dict(incidence),'closed_two_manifold_edges':set(incidence)=={2},'connected_surface_components':components,'oriented_surface_volume_mm3':vol,'CAD_volume_mm3':64142426.1438,'relative_volume_difference':(vol-64142426.1438)/64142426.1438,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_s':time.monotonic()-start,'volume_mesh_created':False,'self_intersections_tested':False,'critical_passage_resolution_verified':False,'engineering_release':False}
(root/'evidence/surface-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));gmsh.finalize()
