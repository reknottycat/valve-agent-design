#!/usr/bin/env python3
"""Bounded topology-only tetrahedron agglomeration. Explicit gates survive python -O.
ESI OpenFOAM v1912 3D cellDeterminant: ONLY original internal faces on group shell.
This file does not authorize or execute a valve flow solve or manufacturing.
"""
from __future__ import annotations
import argparse, collections, hashlib, itertools, json, re, shutil, sys
from pathlib import Path
import numpy as np

class GateError(RuntimeError): pass

def gate(condition, message):
    if not condition: raise GateError(message)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, data): Path(path).write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
def body(path):
    text=Path(path).read_text()
    gate(re.search(r'format\s+ascii\s*;',text) is not None, f'not ASCII: {path}')
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    text=re.sub(r'//[^\n]*','',text)
    return re.sub(r'FoamFile\s*\{.*?\}','',text,count=1,flags=re.S).strip()
def read_list(path, mode='labels'):
    b=body(path); match=re.match(r'(\d+)\s*\((.*)\)\s*$',b,re.S)
    gate(match is not None,f'invalid list: {path}')
    n=int(match[1]); text=match[2]
    if mode=='points':
        result=np.fromstring(text.replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
    elif mode=='faces':
        items=re.findall(r'(\d+)\s*\(([^()]*)\)',text)
        result=[tuple(int(v) for v in s.split()) for k,s in items]
        gate(all(int(k)==len(f) for (k,s),f in zip(items,result)),'face size mismatch')
    else: result=np.fromstring(text,sep=' ',dtype=np.int64)
    gate(len(result)==n,f'list count mismatch: {path}')
    return result

def read_mesh(case):
    p=Path(case)/'constant/polyMesh'
    points=read_list(p/'points','points'); faces=read_list(p/'faces','faces')
    owner=read_list(p/'owner'); neighbour=read_list(p/'neighbour')
    patches=[]
    for name, content in re.findall(r'(\w+)\s*\{([^{}]*)\}',body(p/'boundary')):
        d=dict(re.findall(r'(\w+)\s+([^;]+);',content))
        patches.append(dict(name=name,type=d['type'].strip(),nFaces=int(d['nFaces']),startFace=int(d['startFace'])))
    return dict(points=points,faces=faces,owner=owner,neighbour=neighbour,patches=patches)

def triangle_areas(points, faces):
    arr=np.array(faces,dtype=np.int64)
    gate(arr.shape[1]==3,'source faces must be triangles')
    q=points[arr]
    return np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])*0.5

def source_identity(mesh, points, tets, source_triangles=None, source_tags=None, field_data=None):
    p=mesh['points']; faces=mesh['faces']; own=mesh['owner']; nei=mesh['neighbour']
    gate(p.shape==points.shape,'native/source point shape mismatch')
    point_delta=np.abs(p-points)
    one_ulp=np.maximum(np.abs(np.spacing(p)),np.abs(np.spacing(points)))
    gate(np.all(point_delta<=one_ulp),'native/source point coordinate or order identity failed (beyond one conversion ULP)')
    gate(len(own)==len(faces) and len(nei)<=len(faces),'native face addressing lengths')
    n=len(tets); nf=len(faces); ni=len(nei)
    gate(np.all(own>=0) and np.all(own<n) and np.all(nei>=0) and np.all(nei<n),'owner/neighbour range')
    gate(np.all(own[:ni]<nei),'owner < neighbour required')
    gate(np.all(np.bincount(np.r_[own,nei],minlength=n)==4),'native cell incidence is not four')
    facearr=np.array(faces,dtype=np.int64)
    gate(facearr.shape==(nf,3),'native source triangle shape')
    gate(np.all(facearr>=0) and np.all(facearr<len(p)),'face point range')
    sf=np.sort(facearr,axis=1)
    gate(np.all(sf[:,0]<sf[:,1]) and np.all(sf[:,1]<sf[:,2]),'degenerate face IDs')
    gate(len(np.unique(sf,axis=0))==nf,'duplicate native face')
    for indices,cells in [(np.arange(nf),own),(np.arange(ni),nei)]:
        tf=tets[cells]
        gate(np.all((facearr[indices,:,None]==tf[:,None,:]).any(axis=2)),'native face is not source-cell facet; cell identity failed')
    # Four unique global facets incident on each source tetrahedron prove exact cell identity.
    areas=triangle_areas(p,faces); mags=np.linalg.norm(areas,axis=1)
    gate(np.all(mags>0),'zero area triangle')
    centres=p[tets].mean(axis=1); fc=p[facearr].mean(axis=1)
    gate(np.all(np.einsum('ij,ij->i',areas,fc-centres[own])>0),'native source boundary/owner orientation reversed')
    gate(np.all(np.einsum('ij,ij->i',areas[:ni],fc[:ni]-centres[nei])<0),'native neighbour orientation reversed')
    start=ni
    for patch in mesh['patches']:
        gate(patch['startFace']==start,'non-contiguous patch ranges')
        gate(patch['type'] in ('patch','wall'),'only uncoupled physical patches supported')
        start+=patch['nFaces']
    gate(start==nf,'boundary coverage failed')
    if source_triangles is not None:
        st=np.sort(source_triangles,axis=1); native=sf[ni:]
        gate(len(st)==len(native),'source boundary triangle count differs')
        lookup={tuple(f):int(tag) for f,tag in zip(st,source_tags)}
        gate(len(lookup)==len(st),'source boundary triangle duplicate')
        gate(set(lookup)==set(map(tuple,native)),'source boundary triangle identity failed')
        for patch in mesh['patches']:
            tag=int(field_data[patch['name']][0]); a=patch['startFace']; b=a+patch['nFaces']
            gate(all(lookup[tuple(f)]==tag for f in sf[a:b]),'source boundary physical-patch identity failed')
    return dict(points=len(p),cells=n,faces=nf,internal_faces=ni,all_cells_have_four_original_facets=True,point_index_correspondence_verified=True,point_coordinates_bitwise_equal=bool(np.array_equal(p,points)),conversion_differing_scalars=int(np.count_nonzero(point_delta)),conversion_max_absolute_difference_m=float(point_delta.max()),conversion_max_ulp=float(np.max(point_delta/one_ulp)),boundary_physical_identity=source_triangles is not None)

def determinant(area_vectors):
    a=np.asarray(area_vectors,dtype=float).reshape(-1,3)
    if len(a)==0: return 0.0
    avg=float(np.linalg.norm(a,axis=1).sum()/len(a))
    if avg<1e-150: return 0.0
    gate(np.isfinite(a).all() and np.isfinite(avg),'nonfinite determinant input')
    u=a/avg; m=u.T@u
    # Explicit symmetric tensor determinant matches the ESI expression. No clipping.
    d=m[0,0]*(m[1,1]*m[2,2]-m[1,2]*m[1,2])-m[0,1]*(m[0,1]*m[2,2]-m[1,2]*m[0,2])+m[0,2]*(m[0,1]*m[1,2]-m[1,1]*m[0,2])
    return float(abs(d)/8.0)

def topology(mesh,ncells):
    cf=[[] for _ in range(ncells)]; adj=[set() for _ in range(ncells)]
    for i,o in enumerate(mesh['owner']): cf[o].append(i)
    for i,n in enumerate(mesh['neighbour']):
        o=int(mesh['owner'][i]); cf[n].append(i); adj[o].add(int(n)); adj[n].add(o)
    return cf,adj

def shell(mesh, group, cf):
    group=set(group); counts=collections.Counter(f for c in group for f in cf[c])
    gate(all(v in (1,2) for v in counts.values()),'nonmanifold group face incidence')
    outward=[]
    for f,cnt in counts.items():
        if cnt==1:
            face=mesh['faces'][f]
            outward.append((f,face if int(mesh['owner'][f]) in group else tuple(reversed(face))))
    return outward

def validate_convex_shell(points, outward, tol=1e-11):
    gate(len(outward)>=4,'insufficient shell faces')
    edges=collections.Counter(); oriented=collections.Counter(); verts=set()
    faces=[]
    for fid,face in outward:
        gate(len(face)==3 and len(set(face))==3,'invalid shell triangle')
        faces.append(face); verts.update(face)
        for a,b in zip(face,face[1:]+face[:1]):
            edges[tuple(sorted((a,b)))]+=1; oriented[(a,b)]+=1
    gate(all(n==2 for n in edges.values()),'nonmanifold shell edges')
    gate(all(oriented[(a,b)]==oriented[(b,a)]==1 for a,b in edges),'inconsistent shell orientation')
    gate(len(verts)-len(edges)+len(faces)==2,'shell Euler characteristic is not sphere')
    allp=points[sorted(verts)]; worst=-float('inf'); volume=0.0; origin=allp.mean(axis=0)
    for face in faces:
        q=points[list(face)]; a=np.cross(q[1]-q[0],q[2]-q[0])*0.5; mag=float(np.linalg.norm(a))
        gate(mag>0,'degenerate shell face')
        distances=(allp-q[0])@(a/mag); mx=float(distances.max()); worst=max(worst,mx)
        gate(mx<=tol,f'nonconvex shell: vertex outside outward plane by {mx:.17g} m')
        volume+=float(np.dot(q[0]-origin,np.cross(q[1]-origin,q[2]-origin))/6)
    gate(volume>0,'shell signed volume not positive')
    return volume,worst

def candidate(mesh,group,cf,adj,areas,volumes):
    group=tuple(sorted(group)); seen={group[0]}
    while True:
        more=seen|set().union(*(adj[c]&set(group) for c in seen))
        if more==seen: break
        seen=more
    gate(seen==set(group),'disconnected candidate')
    ext=shell(mesh,group,cf); volume,worst=validate_convex_shell(mesh['points'],ext)
    sourcevol=float(volumes[list(group)].sum())
    gate(abs(volume-sourcevol)<=max(1e-24,sourcevol*2e-11),'candidate volume not equal source union')
    internal_ext=[f for f,_ in ext if f<len(mesh['neighbour'])]
    d=determinant(areas[internal_ext])
    gate(d>=0.001,f'candidate determinant below 0.001: {d}')
    return dict(cells=list(group),determinant=d,internal_exterior_faces=internal_ext,exterior_faces=[f for f,_ in ext],volume=sourcevol,max_halfspace_distance_m=worst)

def select_groups(mesh,tets,bad):
    gate(0<len(bad)<=100,'flagged set must contain 1..100 cells')
    cf,adj=topology(mesh,len(tets)); areas=triangle_areas(mesh['points'],mesh['faces'])
    p=mesh['points'][tets]
    volumes=np.abs(np.einsum('ij,ij->i',p[:,1]-p[:,0],np.cross(p[:,2]-p[:,0],p[:,3]-p[:,0])))/6
    gate(np.all(volumes>0),'source tetrahedron volume not positive')
    source_det={str(c):determinant(areas[[f for f in cf[c] if f<len(mesh['neighbour'])]]) for c in sorted(bad)}
    gate(all(v<0.001 for v in source_det.values()),'native flagged cell/source determinant mismatch')
    groups=set()
    for c in bad:
        for a in adj[c]:
            groups.add(tuple(sorted((c,a))))
            for b in (adj[c]|adj[a])-{c,a}: groups.add(tuple(sorted((c,a,b))))
    valid=[]; rejected=[]
    for group in sorted(groups,key=lambda g:(len(g),g)):
        try: valid.append(candidate(mesh,group,cf,adj,areas,volumes))
        except GateError as e: rejected.append(dict(cells=list(group),reason=str(e)))
    uncovered=set(bad); used=set(); selected=[]
    while uncovered:
        options={c:[g for g in valid if c in g['cells'] and not used.intersection(g['cells'])] for c in uncovered}
        c=min(uncovered,key=lambda c:(len(options[c]),c))
        gate(bool(options[c]),f'no disjoint valid candidate remains for flagged cell {c}')
        choice=min(options[c],key=lambda g:(len(g['cells']),-g['determinant'],g['cells']))
        selected.append(choice); used.update(choice['cells']); uncovered.difference_update(choice['cells'])
    return dict(flagged_cells=sorted(bad),flagged_source_determinants=source_det,enumerated_candidates=len(groups),valid_candidates=valid,rejected_candidates=rejected,selected_groups=selected,source_volume_m3=float(volumes.sum()))

def header(obj,cls): return f'FoamFile\n{{\n version 2.0; format ascii; class {cls}; location "constant/polyMesh"; object {obj};\n}}\n'
def write_labels(path,values):
    Path(path).write_text(header(Path(path).name,'labelList')+str(len(values))+'\n(\n'+'\n'.join(map(str,values))+'\n)\n')
def write_candidate(source_case,target,mesh,ncells,selection):
    target=Path(target); gate(not target.exists(),'refuse to overwrite candidate output')
    target.mkdir(parents=True); (target/'RUNNING').write_text('Candidate invalid until all required external checks and identity audit pass.\n')
    out=target/'constant/polyMesh'; out.mkdir(parents=True)
    shutil.copytree(Path(source_case)/'system',target/'system')
    shutil.copy2(Path(source_case)/'constant/polyMesh/points',out/'points')
    representatives=np.arange(ncells)
    for g in selection['selected_groups']:
        representatives[g['cells']]=min(g['cells'])
    unique=sorted(set(representatives.tolist())); lookup={v:i for i,v in enumerate(unique)}
    mapping=np.array([lookup[int(r)] for r in representatives],dtype=np.int64)
    origown=mesh['owner']; orign=mesh['neighbour']; ni=len(orign)
    internal=[]; removed=[]
    for i in range(ni):
        o,n=int(mapping[origown[i]]),int(mapping[orign[i]])
        if o==n: removed.append(i); continue
        f=mesh['faces'][i]
        if o>n: o,n=n,o; f=tuple(reversed(f))
        internal.append((o,n,i,f))
    internal.sort(key=lambda v:(v[0],v[1],v[2]))
    faces=[v[3] for v in internal]+mesh['faces'][ni:]
    owner=[v[0] for v in internal]+mapping[origown[ni:]].tolist(); neighbour=[v[1] for v in internal]
    (out/'faces').write_text(header('faces','faceList')+str(len(faces))+'\n(\n'+'\n'.join(str(len(f))+'('+' '.join(map(str,f))+')' for f in faces)+'\n)\n')
    write_labels(out/'owner',owner); write_labels(out/'neighbour',neighbour)
    patches=[]; start=len(neighbour)
    for patch in mesh['patches']:
        patches.append(dict(patch,startFace=start)); start+=patch['nFaces']
    (out/'boundary').write_text(header('boundary','polyBoundaryMesh')+str(len(patches))+'\n(\n'+''.join(f"{p['name']} {{ type {p['type']}; nFaces {p['nFaces']}; startFace {p['startFace']}; }}\n" for p in patches)+')\n')
    (out/'cellZones').write_text(header('cellZones','regIOobject')+f'1\n(\nfluid\n{{ type cellZone; cellLabels List<label>\n{len(unique)}\n(\n'+'\n'.join(map(str,range(len(unique))))+'\n);\n}\n)\n')
    np.save(target/'source_to_candidate_cell.npy',mapping)
    save(target/'construction.json',dict(cells=len(unique),points=len(mesh['points']),faces=len(faces),internal_faces=len(neighbour),removed_internal_faces=removed,point_file_byte_identical=sha(out/'points')==sha(Path(source_case)/'constant/polyMesh/points'),selected_groups=selection['selected_groups']))
    return mapping

def oriented_key(face):
    face=tuple(face); return min(face[i:]+face[:i] for i in range(len(face)))
def oriented_boundary_union(triangles):
    gate(len(triangles)==2 and all(len(t)==3 for t in triangles),'quad requires two original triangles')
    counts=collections.Counter((a,b) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1]))
    shared=[e for e in counts if counts[(e[1],e[0])]]
    gate(len(shared)==2 and all(v==1 for v in counts.values()),'triangles do not share exactly one oppositely oriented edge')
    boundary=[e for e in counts if (e[1],e[0]) not in counts]
    gate(len(boundary)==4,'triangle union not quadrilateral')
    nxt=dict(boundary); gate(len(nxt)==4,'nonmanifold quad boundary')
    v=min(nxt); cycle=[v]
    for _ in range(3): cycle.append(nxt[cycle[-1]])
    gate(len(set(cycle))==4 and nxt[cycle[-1]]==v,'quad boundary not simple cycle')
    return tuple(cycle)

def verify_patch_merge(before,after,tol=1e-11):
    gate(np.array_equal(before['points'],after['points']),'patch merge moved, removed, added, or reordered points')
    ni=len(before['neighbour']); gate(len(after['neighbour'])==ni,'internal face count changed')
    gate(before['faces'][:ni]==after['faces'][:ni],'internal faces changed')
    gate(np.array_equal(before['owner'][:ni],after['owner'][:ni]),'internal owner changed')
    gate(np.array_equal(before['neighbour'],after['neighbour']),'internal neighbour changed')
    gate([(p['name'],p['type']) for p in before['patches']]==[(p['name'],p['type']) for p in after['patches']],'physical patch definitions changed')
    records=[]; kept=0
    for pb,pa in zip(before['patches'],after['patches']):
        bi=range(pb['startFace'],pb['startFace']+pb['nFaces']); ai=range(pa['startFace'],pa['startFace']+pa['nFaces'])
        original={(int(before['owner'][i]),oriented_key(before['faces'][i])):i for i in bi}
        gate(len(original)==pb['nFaces'],'duplicate original boundary face')
        used=set(); added=[]
        for i in ai:
            f=after['faces'][i]; key=(int(after['owner'][i]),oriented_key(f))
            if key in original:
                gate(original[key] not in used,'duplicated kept boundary face'); used.add(original[key]); kept+=1
            else: added.append(i)
        removed=set(bi)-used
        for i in added:
            f=after['faces'][i]; gate(len(f)==4,'new boundary face is not a quad')
            eligible=[j for j in removed if before['owner'][j]==after['owner'][i] and set(before['faces'][j])<=set(f)]
            gate(len(eligible)==2,'new quad lacks exactly two removed same-cell same-patch source triangles')
            triangles=[before['faces'][j] for j in eligible]
            union=oriented_boundary_union(triangles)
            gate(oriented_key(union)==oriented_key(f),'quad reverses or changes oriented boundary-edge union')
            p=before['points']; q=p[list(triangles[0])]; normal=np.cross(q[1]-q[0],q[2]-q[0]); normal/=np.linalg.norm(normal)
            distance=np.abs((p[list(f)]-q[0])@normal)
            gate(float(distance.max())<=tol,'merged triangles not coplanar within roundoff tolerance')
            normal2=np.cross(p[triangles[1][1]]-p[triangles[1][0]],p[triangles[1][2]]-p[triangles[1][0]])
            gate(np.dot(normal,normal2)>0,'source triangle orientation inconsistency')
            removed.difference_update(eligible)
            records.append(dict(patch=pa['name'],cell=int(after['owner'][i]),removed_triangle_ids=eligible,new_quad_id=i,quad_points=list(f),max_coplanarity_distance_m=float(distance.max())))
        gate(not removed,'unexplained removed boundary triangles')
    return dict(points_exactly_unchanged=True,internal_faces_and_addressing_exactly_unchanged=True,kept_boundary_faces=kept,merged_quads=records,merged_quad_count=len(records),no_external_geometry_change=True)

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='mode',required=True)
    build=sub.add_parser('build'); build.add_argument('--source',required=True); build.add_argument('--source-sha',required=True); build.add_argument('--baseline',required=True); build.add_argument('--output',required=True); build.add_argument('--evidence',required=True)
    merge=sub.add_parser('audit-merge'); merge.add_argument('--before',required=True); merge.add_argument('--after',required=True); merge.add_argument('--output',required=True)
    a=ap.parse_args()
    if a.mode=='audit-merge':
        from binding import audit_report
        evidence=audit_report('patch_merge',a.output,{'before':a.before,'after':a.after},lambda:verify_patch_merge(read_mesh(a.before),read_mesh(a.after)))
        print(json.dumps(evidence,indent=2)); return
    gate(sha(a.source)==a.source_sha,'source SHA256 mismatch')
    gate(not Path(a.output).exists(),'output exists; require fresh path')
    import meshio
    gm=meshio.read(a.source); tets=gm.cells_dict['tetra']; mesh=read_mesh(a.baseline)
    evidence=Path(a.evidence); evidence.mkdir(parents=True,exist_ok=True)
    identity=source_identity(mesh,gm.points,tets,gm.cells_dict['triangle'],gm.cell_data_dict['gmsh:physical']['triangle'],gm.field_data)
    save(evidence/'source_identity.json',identity); print('Exact source/native identity passed',flush=True)
    bad=set(map(int,read_list(Path(a.baseline)/'constant/polyMesh/sets/underdeterminedCells')))
    selection=select_groups(mesh,tets,bad); save(evidence/'selection.json',selection)
    mapping=write_candidate(a.baseline,a.output,mesh,len(tets),selection)
    save(evidence/'build_provenance.json',dict(source=str(Path(a.source).resolve()),source_sha256=sha(a.source),baseline=str(Path(a.baseline).resolve()),baseline_hashes={n:sha(Path(a.baseline)/'constant/polyMesh'/n) for n in ['points','faces','owner','neighbour','boundary','cellZones']},script_sha256=sha(__file__),python=sys.version,numpy=np.__version__,meshio=meshio.__version__,identity=identity,candidate=str(Path(a.output).resolve()),status='RUNNING_EXTERNAL_VALIDATION_REQUIRED'))
    print(json.dumps({k:selection[k] for k in ['flagged_cells','enumerated_candidates','selected_groups','source_volume_m3']},indent=2))
if __name__=='__main__': main()
