import os,sys,pathlib,hashlib,json
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
sys.path.insert(0,'/workspace/shared/valve-gmsh-trial-20261023/vendor')
import gmsh
b=pathlib.Path(__file__).parent;s=pathlib.Path('/workspace/shared/valve-step-grading-volume-20261023/fresh-local-surface.msh')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(s)=='4e1b4168c9cfdd8d248a54dbbe2411c6fd7661305e479d77f53e3a0f07568a98'
gmsh.initialize();gmsh.open(str(s))
def snap():
 groups=[]
 for dim,tag in gmsh.model.getPhysicalGroups():
  ents=gmsh.model.getEntitiesForPhysicalGroup(dim,tag);cnt=sum(sum(len(t) for t in gmsh.model.mesh.getElements(dim,int(e))[1]) for e in ents)
  groups.append({'dim':int(dim),'tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),'elements':cnt})
 return groups
volents=gmsh.model.getEntitiesForPhysicalGroup(3,1).tolist();gmsh.model.removePhysicalGroups([(3,1)]);gmsh.model.addPhysicalGroup(3,volents,1001);gmsh.model.setPhysicalName(3,1001,'fluid_proxy')
before=snap();assert len([x for x in before if x['dim']==2])==132
out=b/'source-copy-ascii22-mm.msh';gmsh.option.setNumber('Mesh.Binary',0);gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.write(str(out));gmsh.clear();gmsh.open(str(out));after=snap();assert before==after
assert sum(x['elements'] for x in after if x['dim']==3)==759760
assert sha(s)=='4e1b4168c9cfdd8d248a54dbbe2411c6fd7661305e479d77f53e3a0f07568a98'
(b/'evidence/export.json').write_text(json.dumps({'source_sha256':sha(s),'copy_sha256':sha(out),'units':'mm','surface_groups_unchanged':True,'volume_tag_remap':{'1':1001},'reason':'1912 converter shares physical names across dimensions; preserve name fluid_proxy with unique ID','groups':after},indent=2));gmsh.finalize()
