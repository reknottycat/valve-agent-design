"""Independent whole-domain mesh diagnostic, unchanged 57 mm STEP. Units: mm."""
import sys, hashlib, json, pathlib, math
import gmsh
import numpy as np
src = pathlib.Path(sys.argv[1]); dst = pathlib.Path(sys.argv[2]); dst.mkdir(exist_ok=False)
assert hashlib.sha256(src.read_bytes()).hexdigest() == 'a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787'
gmsh.initialize(); gmsh.logger.start(); result = {'cad_sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'solver_run': False}
try:
    for k,v in {'General.NumThreads':2,'Geometry.OCCFixDegenerated':0,'Geometry.OCCFixSmallEdges':0,'Geometry.OCCFixSmallFaces':0,'Geometry.OCCSewFaces':0,'Geometry.OCCMakeSolids':0,'Mesh.MeshSizeFromPoints':0,'Mesh.MeshSizeFromCurvature':12,'Mesh.MeshSizeExtendFromBoundary':0,'Mesh.MeshSizeMin':0.05,'Mesh.MeshSizeMax':12,'Mesh.Algorithm':6,'Mesh.Algorithm3D':1,'Mesh.MshFileVersion':2.2,'Mesh.Binary':0}.items(): gmsh.option.setNumber(k,v)
    gmsh.model.occ.importShapes(str(src)); gmsh.model.occ.synchronize(); faces=[t for _,t in gmsh.model.getEntities(2)]; vols=gmsh.model.getEntities(3); assert len(vols)==1 and len(faces)==132
    for n,t,x in [('inlet',79,-600),('outlet',34,1200)]:
        center=gmsh.model.occ.getCenterOfMass(2,t); assert abs(center[0]-x)<1e-5 and math.isclose(gmsh.model.occ.getMass(2,t),math.pi*100**2,rel_tol=1e-8)
        gmsh.model.addPhysicalGroup(2,[t],name=n)
    gmsh.model.addPhysicalGroup(2,[f for f in faces if f not in (34,79)],name='valve');gmsh.model.addPhysicalGroup(3,[vols[0][1]],name='fluid')
    # Restrict fine wall resolution to the guide and upper stem; include their trimming curves.
    near={64,108}; near.update(t for t in faces if (lambda b:b[0]>250 and b[3]<350 and b[1]>-50 and b[4]<50 and b[5]>91)(gmsh.model.getBoundingBox(2,t)))
    edges={t for _,t in gmsh.model.getBoundary([(2,f) for f in near],combined=False,oriented=False)}; fld=gmsh.model.mesh.field
    c=fld.add('MathEval'); fld.setString(c,'F','2.25'); restr=fld.add('Restrict');fld.setNumber(restr,'InField',c);fld.setNumbers(restr,'SurfacesList',sorted(near));fld.setNumbers(restr,'CurvesList',sorted(edges));fld.setAsBackgroundMesh(restr)
    # Physical distances (mm) to the circular lip edges located by the v21 tetrahedron audit.
    bands=[]
    for radius, z0, h in ((105.25,79,0.32),(110.75,79,0.32),(112.5,21.975,0.27)):
        field=fld.add('MathEval'); fld.setString(field,'F',f'{h}+0.32*Sqrt((Sqrt((x-300)^2+y^2)-{radius})^2+(z-{z0})^2)'); bands.append(field)
    comb=fld.add('Min');fld.setNumbers(comb,'FieldsList',[restr,*bands]);fld.setAsBackgroundMesh(comb)
    gmsh.model.mesh.generate(2)
    nt,xyz,_=gmsh.model.mesh.getNodes(); a=np.argsort(nt); nt,xyz=nt[a],xyz.reshape((-1,3))[a]; sag={}
    for f,r in [(64,32.),(108,31.)]:
        typ,tags,ns=gmsh.model.mesh.getElements(2,f);assert list(typ)==[2]; pts=xyz[np.searchsorted(nt,ns[0])].reshape((-1,3,3))[:,:,:2]-[300.,0.];assert np.max(np.abs(np.linalg.norm(pts,axis=2)-r))<1e-4
        # Cylindrical triangles are local angular arcs (< pi), so nearest projected point is on an edge.
        assert (np.sum(pts*pts[:,0:1],axis=2)>0).all(); end=np.roll(pts,-1,axis=1); vec=end-pts;v2=np.sum(vec*vec,axis=2); frac=np.clip(-np.sum(pts*vec,axis=2)/np.maximum(1e-28,v2),0,1); sag[str(f)]=float(r-np.linalg.norm(pts+vec*frac[:,:,None],axis=2).min());assert sag[str(f)]<0.2,sag
    result['guide_radial_sag_mm']=sag;print('surface gate:',sag,flush=True);gmsh.option.setNumber('Mesh.MeshOnlyEmpty',1);gmsh.model.mesh.generate(3)
    typ,tags,_=gmsh.model.mesh.getElements(3);assert list(typ)==[4] and len(tags[0])>0;result['tet_count']=len(tags[0]); q=gmsh.model.mesh.getElementQualities(tags[0],'minSICN');result['min_sicn']=float(np.min(q));assert result['min_sicn']>0
    points=[(-500,.17,.13),(1100,.17,.13),(320,.17,331),(280,.17,331),(331.5,.17,160),(268.5,.17,160)];result['point_to_tet']={}
    for p in points:
        assert gmsh.model.isInside(3,vols[0][1],p);eid,etype,*_=gmsh.model.mesh.getElementByCoordinates(*p,dim=3,strict=True);assert etype==4;result['point_to_tet'][str(p)]=int(eid)
    gmsh.write(str(dst/'volume_mm.msh'));result['mesh_written']=True
except BaseException as e:
    result['error']=repr(e);raise
finally:
    (dst/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);gmsh.finalize()
