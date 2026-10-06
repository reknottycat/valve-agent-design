#!/usr/bin/env python3
"""Mesh the validated exploratory master-model fluid domain, never launch a solver."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import cadquery as cq
import gmsh
import meshio
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'CLOUD/T04'))
from geometry_gate import step_length_unit


def require(condition,message):
    if not condition:raise RuntimeError(message)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mesh(output, size_m=.035):
    require(type(size_m) in (float,int) and math.isfinite(size_m) and .005<=size_m<=.1,'Mesh size outside bounded study range')
    base=HERE.parent
    params=base/'T11/parameters.json';source=base/'T12/build_lift_model.py';validator=base/'T22/validate_lift_model.py'
    build=json.loads((base/'T12/out/build_report.json').read_text())
    validation=json.loads((base/'T22/out/geometry_check.json').read_text())
    for report in (build,validation):
        require(report['parameters_sha256']==digest(params),'Stale parameter evidence')
        require(report['builder_code_sha256']==digest(source),'Stale builder evidence')
    require(validation['validator_code_sha256']==digest(validator),'Stale validation code evidence')
    require(validation['geometry_gate']=='PASS','Geometry gate not passed')
    path=base/'T12/out/open/fluid_domain_mm.step'
    require(build['asset_hashes']['open/fluid_domain_mm.step']==digest(path),'Changed fluid asset')
    require(step_length_unit(path)['unit']=='mm','STEP unit metadata must explicitly be millimetres')
    shape=cq.importers.importStep(str(path)).val()
    require(shape.isValid() and len(shape.Solids())==1,'Open flow region must be a valid single solid')
    p={k:v['value'] for k,v in json.loads(params.read_text())['values'].items()}
    xmin=-3*p['bore']*.001;xmax=(p['face_to_face']+3*p['bore'])*.001
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads',1)
        gmsh.model.add('C2_exploratory_open')
        entities=gmsh.model.occ.importShapes(str(path))
        # Gmsh OCC import uses the numeric mm convention by default: assert before applying exactly one scale.
        gmsh.model.occ.synchronize()
        box=gmsh.model.getBoundingBox(-1,-1)
        require(abs((box[3]-box[0])-(xmax-xmin)*1000)<.001,'Unexpected STEP importer unit convention')
        gmsh.model.occ.dilate(entities,0,0,0,.001,.001,.001);gmsh.model.occ.synchronize()
        volumes=gmsh.model.getEntities(3);require(len(volumes)==1,'Gmsh import split the fluid region')
        groups={'inlet':[],'outlet':[],'wall':[]}
        for dim,tag in gmsh.model.getBoundary(volumes,oriented=False):
            x0,y0,z0,x1,y1,z1=gmsh.model.getBoundingBox(dim,tag)
            if abs(x0-xmin)<1e-6 and abs(x1-xmin)<1e-6:groups['inlet'].append(tag)
            elif abs(x0-xmax)<1e-6 and abs(x1-xmax)<1e-6:groups['outlet'].append(tag)
            else:groups['wall'].append(tag)
        require(all(groups.values()),'Missing physical boundary')
        for tag,(name,faces) in enumerate(groups.items(),1):
            gmsh.model.addPhysicalGroup(2,faces,tag);gmsh.model.setPhysicalName(2,tag,name)
        gmsh.model.addPhysicalGroup(3,[v[1] for v in volumes],4);gmsh.model.setPhysicalName(3,4,'fluid')
        gmsh.option.setNumber('Mesh.MeshSizeMin',size_m/4)
        gmsh.option.setNumber('Mesh.MeshSizeMax',size_m)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',32)
        gmsh.option.setNumber('Mesh.ElementOrder',1)
        gmsh.option.setNumber('Mesh.MshFileVersion',4.1)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(out/'fluid_open_si.msh'))
    finally:gmsh.finalize()
    result=meshio.read(out/'fluid_open_si.msh');tet=result.get_cells_type('tetra')
    require(len(tet)>0,'No volume elements')
    pts=result.points[tet]
    determinant=np.linalg.det(np.stack((pts[:,1]-pts[:,0],pts[:,2]-pts[:,0],pts[:,3]-pts[:,0]),axis=1))
    require(bool(np.all(determinant>0)),'Non-positive tetrahedron determinant')
    require(set(result.field_data)=={'inlet','outlet','wall','fluid'},'Physical names lost')
    triangles=result.get_cell_data('gmsh:physical','triangle')
    require(set(triangles)=={1,2,3},'Surface physical tags lost')
    require(set(result.get_cell_data('gmsh:physical','tetra'))=={4},'Fluid physical tag lost')
    faces=np.sort(np.stack([tet[:,idx] for idx in ([0,1,2],[0,1,3],[0,2,3],[1,2,3])],axis=1).reshape(-1,3),axis=1)
    unique_faces,inverse,counts=np.unique(faces,axis=0,return_inverse=True,return_counts=True)
    require(bool(np.all(counts<=2)),'Nonmanifold tetrahedron face')
    boundary=unique_faces[counts==1]
    surface,surface_counts=np.unique(np.sort(result.get_cells_type('triangle'),axis=1),axis=0,return_counts=True)
    require(bool(np.all(surface_counts==1)),'Duplicated boundary triangle')
    require(np.array_equal(boundary,surface),'Boundary triangle coverage does not equal exterior tetrahedron faces')
    order=np.argsort(inverse,kind='stable');offsets=np.cumsum(counts)-counts;owners=np.repeat(np.arange(len(tet)),4)
    parent=np.arange(len(tet))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    for offset in offsets[counts==2]:
        a,b=find(owners[order[offset]]),find(owners[order[offset+1]])
        if a!=b:parent[b]=a
    components=len({find(i) for i in range(len(tet))})
    require(components==1,'Volume mesh disconnected across shared faces')
    cad_volume=shape.Volume(1e-9)*1e-9;mesh_volume=float(np.sum(determinant)/6)
    relative_error=abs(mesh_volume-cad_volume)/cad_volume
    require(relative_error<.01,'Mesh geometry volume differs by >=1%')
    r={'schema':'valve.c2-mesh/1.0','status':'EXPLORATORY_MESH_ONLY','solver_run':False,
       'engineering_compliance':'NOT_ASSESSED','manufacturing_authorized':False,
       'parameters_sha256':digest(params),'source_step_sha256':digest(path),
       'mesher_code_sha256':digest(__file__),
       'mesh_sha256':digest(out/'fluid_open_si.msh'),'gmsh_version':gmsh.__version__,
       'length_unit':'m','conversion':'STEP mm multiplied exactly once by0.001',
       'nodes':len(result.points),'tetrahedra':len(tet),'min_determinant_m3':float(np.min(determinant)),
       'shared_face_components':components,'nonmanifold_faces':int(np.count_nonzero(counts>2)),
       'boundary_coverage':'EXACT','boundary_faces':len(boundary),
       'cad_volume_m3':cad_volume,'mesh_volume_m3':mesh_volume,'relative_volume_error':relative_error,
       'geometry_volume_tolerance':.01,'max_mesh_size_m':size_m,
       'physical_names':{k:v.tolist() for k,v in result.field_data.items()},
       'boundary_triangle_counts':{name:int(np.count_nonzero(triangles==tag)) for tag,name in enumerate(groups,1)},
       'limitations':['No solver convergence or turbulence/wall-resolution acceptance established',
                      'Packing cavity cap and simplified wetted geometry are explicit study assumptions',
                      'No flow coefficient or pressure adequacy conclusion from this mesh']}
    (out/'mesh_report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'out');parser.add_argument('--size-m',type=float,default=.035)
    args=parser.parse_args();mesh(args.output,args.size_m)
