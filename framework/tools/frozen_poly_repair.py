"""Independent gate for a connectivity-only repair of the frozen DN200 mesh (ASCII)."""
import hashlib
import math
import re
import struct


def rows(file):
    # OpenFOAM headers can contain comments; line after first naked length must open the list.
    for line in file:
        if re.fullmatch(rb'\s*\d+\s*',line):
            n=int(line);assert file.readline().strip()==b'(';break
    else:raise ValueError('List header absent')
    for _ in range(n):
        line=file.readline().strip()
        if not line: raise ValueError('Truncated native mesh list')
        yield line
    if file.readline().strip()!=b')': raise ValueError('Native mesh list length mismatch')


def envelope(case):
    mesh=case/'constant/polyMesh'; nodes=hashlib.sha256();count=0
    with (mesh/'points').open('rb') as f:
        for line in rows(f):
            v=tuple(map(float,line.strip(b'()').split()));assert len(v)==3 and all(map(math.isfinite,v));nodes.update(struct.pack('>ddd',*v));count+=1
    boundary=(mesh/'boundary').read_text();patches=[]
    for name,body in re.findall(r'(\w+)\s*\{([^{}]*)\}',boundary):
        if 'nFaces' not in body:continue
        def field(key):return re.search(r'\b'+key+r'\s+(\w+)\s*;',body)[1]
        patches.append((int(field('startFace')),int(field('nFaces')),name,field('type')))
    patches.sort();assert {(p[2],p[3]) for p in patches}=={('inlet','patch'),('outlet','patch'),('valve','wall')};assert len(patches)==3
    packed={};idx=0;bucket=[]
    with (mesh/'faces').open('rb') as f:
        for i,line in enumerate(rows(f)):
            if idx==0 and i<patches[0][0]:continue
            start,n,name,kind=patches[idx];assert start<=i<start+n
            m=re.fullmatch(rb'3\s*\(([^()]+)\)',line);assert m; a,b,c=map(int,m[1].split());assert len({a,b,c})==3 and min(a,b,c)>=0 and max(a,b,c)<count
            # Preserve orientation, allow cyclic permutations and reorderings inside each patch.
            bucket.append(struct.pack('>III',*min((a,b,c),(b,c,a),(c,a,b))))
            if i+1==start+n:
                h=hashlib.sha256();h.update(b''.join(sorted(bucket)));packed[name]=(kind,n,h.hexdigest());bucket=[];idx+=1
    assert idx==len(patches);return {'point_count':count,'ordered_xyz_sha256':nodes.hexdigest(),'oriented_boundary_faces':packed}


def nonortho(log):
    m=re.search(r'Number of severely non-orthogonal\s*\([^)]*\) faces:\s*(\d+)',log)
    if m:return int(m[1])
    # Foundation 11 only emits the count when nonzero. Confirm native check actually ran.
    mx=re.search(r'Mesh non-orthogonality Max:\s*([\d.eE+\-]+)',log)
    if mx and 0<=float(mx[1])<=70 and 'Non-orthogonality check OK.' in log:return 0
    raise ValueError('Native non-orthogonality count unavailable')


def volume(log):return float(re.search(r'Total volume = ([+\-\d.eE]+)\.',log)[1])


def compare(original, candidate, old_log, new_log):
    before,after=nonortho(old_log),nonortho(new_log)
    v0,v1=volume(old_log),volume(new_log)
    return {'same_boundary_and_points':original==candidate, 'same_discrete_volume':v0>0 and math.isclose(v0,v1,rel_tol=1e-8,abs_tol=0),
            'no_additional_severe_faces':after<=before, 'before_severe_faces':before,'after_severe_faces':after,'before_volume_m3':v0,'after_volume_m3':v1}
