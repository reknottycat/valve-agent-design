"""Read the exported file, not the generator arrays. Fail closed on invalid geometry."""
from collections import Counter
from math import dist, fsum, sin, radians
import gmsh

HEX=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
PRI=((0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5))


def verify(path, ref):
    def require(ok, why):
        if not ok: raise ValueError('mesh rejected: '+why)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0); gmsh.open(str(path)); mesh=gmsh.model.mesh
        coords,xyz,_=mesh.getNodes(); pts=dict(zip(coords,zip(*[iter(xyz)]*3)))
        groups={gmsh.model.getPhysicalName(d,t):(d,t) for d,t in gmsh.model.getPhysicalGroups()}
        require(set(groups)=={'inlet','outlet','walls','wedgeMinus','wedgePlus','fluid'},'patch names')
        counts=Counter(); kinds=Counter(); total=0.; low=float('inf'); surf=Counter(); areas={}
        for name,(dim,tag) in groups.items():
            for entity in gmsh.model.getEntitiesForPhysicalGroup(dim,tag):
                types,tags,blocks=mesh.getElements(dim,entity)
                for k,ids,flat in zip(types,tags,blocks):
                    if dim==3:
                        require(k in (5,6),'unknown cell type'); kinds[int(k)]+=len(ids)
                        low=min(low,min(mesh.getElementQualities(ids,'minDetJac')))
                        total+=fsum(mesh.getElementQualities(ids,'volume'))
                        n=8 if k==5 else 6
                        for row in flat.reshape(-1,n):
                            for face in (HEX if k==5 else PRI): counts[tuple(sorted(row[i] for i in face))]+=1
                    else:
                        require(k in (2,3),'unknown boundary face'); n=3 if k==2 else 4
                        areas[name]=areas.get(name,0.)+fsum(mesh.getElementQualities(ids,'volume'))
                        for row in flat.reshape(-1,n):
                            surf[tuple(sorted(row))]+=1
                            if name.startswith('wedge'):
                                from math import tan
                                slope=tan(radians(2.5))*(1 if name=='wedgePlus' else -1)
                                require(all(abs(pts[v][2]-slope*pts[v][1])<1e-12 for v in row),'nonplanar wedge')
        require(sum(kinds.values())==ref['cells'] and set(kinds)=={5,6},'cell count or type')
        require(all(c in (1,2) for c in counts.values()) and surf==Counter({f:1 for f,c in counts.items() if c==1}),'boundary coverage or face incidence')
        require(low>0,'nonpositive Jacobian'); err=abs(total/ref['volume_reference_m3']-1); require(err<.001,'volume mismatch')
        for name in ('inlet','outlet'): require(abs(areas[name]/ref['inlet_area_m2']-1)<1e-8,'cap area: '+name)
        rs=[dist((y,z),(0.,0.)) for x,y,z in pts.values() if abs(x)<1e-12]; require(abs(max(rs)-ref['throat_radius_m'])<1e-12,'wrong throat')
        return dict(hexes=kinds[5],prisms=kinds[6],min_jacobian=float(low),volume_mesh_m3=total,volume_relative_error=err,mesh_geometry_check='PASS')
    finally: gmsh.finalize()
