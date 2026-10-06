#!/usr/bin/env python3
"""Independent construction audit: compares serialized meshes, not builder internals."""
import argparse,collections,json
from pathlib import Path
import numpy as np
import repair_mesh as r

def audit(baseline,candidate):
    a=r.read_mesh(baseline); b=r.read_mesh(candidate)
    mapping=np.load(Path(candidate)/'source_to_candidate_cell.npy'); report=json.loads((Path(candidate)/'construction.json').read_text())
    r.gate(r.sha(Path(baseline)/'constant/polyMesh/points')==r.sha(Path(candidate)/'constant/polyMesh/points'),'agglomeration point file changed')
    r.gate(np.array_equal(a['points'],b['points']),'agglomeration coordinates changed')
    r.gate(len(mapping)==max(a['owner'].max(),a['neighbour'].max())+1,'cell mapping size mismatch')
    groups=collections.defaultdict(list)
    for old,new in enumerate(mapping): groups[int(new)].append(old)
    r.gate(set(groups)==set(range(len(groups))),'non-contiguous new cell ids')
    merged=[v for v in groups.values() if len(v)>1]
    planned=sorted(sorted(g['cells']) for g in report['selected_groups'])
    r.gate(sorted(merged)==planned,'serialized cell map does not match bounded selected groups')
    r.gate(all(len(g) in (2,3) for g in merged),'unbounded agglomeration group')
    ni=len(a['neighbour']); nbi=len(b['neighbour']); removed=[]; expected=[]
    for i in range(ni):
        o,n=int(mapping[a['owner'][i]]),int(mapping[a['neighbour'][i]])
        if o==n: removed.append(i); continue
        f=a['faces'][i]
        if o>n: o,n=n,o; f=tuple(reversed(f))
        expected.append((o,n,r.oriented_key(f)))
    actual=[(int(b['owner'][i]),int(b['neighbour'][i]),r.oriented_key(b['faces'][i])) for i in range(nbi)]
    r.gate(collections.Counter(actual)==collections.Counter(expected),'kept internal face/addressing identity failed')
    r.gate(actual==sorted(actual,key=lambda v:(v[0],v[1])),'internal face owner/neighbour sort failed')
    r.gate(removed==report['removed_internal_faces'],'removed internal face set mismatch')
    r.gate(a['faces'][ni:]==b['faces'][nbi:],'boundary triangles/order/orientation changed')
    r.gate(np.array_equal(mapping[a['owner'][ni:]],b['owner'][nbi:]),'boundary face owners not exactly remapped')
    r.gate([(p['name'],p['type'],p['nFaces']) for p in a['patches']]==[(p['name'],p['type'],p['nFaces']) for p in b['patches']],'boundary physical patch membership changed')
    cf,adj=r.topology(a,len(mapping)); areas=r.triangle_areas(a['points'],a['faces']); verified=[]
    for g in merged:
        ext=r.shell(a,g,cf); volume,worst=r.validate_convex_shell(a['points'],ext)
        candidate_cell=int(mapping[g[0]]); bf=[]
        for i in np.flatnonzero(b['owner']==candidate_cell): bf.append((int(i),b['faces'][i]))
        for i in np.flatnonzero(b['neighbour']==candidate_cell): bf.append((int(i),tuple(reversed(b['faces'][i]))))
        r.gate(collections.Counter(r.oriented_key(f) for _,f in ext)==collections.Counter(r.oriented_key(f) for _,f in bf),'serialized cell shell differs from original union')
        d=r.determinant(areas[[i for i,_ in ext if i<ni]])
        r.gate(d>=.001,'serialized cell determinant below threshold')
        verified.append(dict(original_cells=g,new_cell=candidate_cell,determinant=d,shell_volume_m3=volume,max_halfspace_distance_m=worst))
    return dict(point_file_byte_identical=True,all_boundary_triangles_orientation_order_and_patch_membership_exact=True,internal_change_only_removal_of_group_shared_faces=True,removed_internal_faces=removed,old_cells=len(mapping),new_cells=len(groups),merged_groups=verified,exact_geometric_partition_preserved=True,volume_statement='Every candidate cell shell is the exact oriented boundary of the original tetrahedron union. This is stronger than equality of rounded volume sums.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    from binding import audit_report
    result=audit_report('agglomeration',a.output,{'baseline':a.baseline,'candidate':a.candidate},lambda:audit(a.baseline,a.candidate));print(json.dumps(result,indent=2))
