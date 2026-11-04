"""Bounded read-only reconstruction of one immutable saved ASCII mesh/field set.

Not a general OpenFOAM parser. Never executes captured source or writes evidence.
Only retained port faces, points and owner pressures enter the summary.
"""
import collections
import hashlib
import math
import os
from pathlib import Path
import re
import stat

PROFILE = 'native-simple-state21-ports/v1'
LOCK_SHA256 = '15ccdb0cb570ccfa321f83b4e9cf0b29654690bc4c329d15cbe757563f0e4736'
ROLES = {'boundary', 'faces', 'points', 'owner', 'p', 'phi', 'plan'}
MAX_LINE = 16384
MAX_TAIL = 4 * 1024 * 1024
MAX_COUNT = 2000000


def need(condition, message):
    if not condition:
        raise ValueError('Port geometry: ' + message)


def open_regular(value):
    """Walk with directory descriptors: parent symlink races cannot redirect reads."""
    need(type(value) is str and value.startswith('/') and not value.startswith('//') and
         str(Path(value)) == value and '..' not in Path(value).parts,
         'canonical absolute path required')
    parts = Path(value).parts[1:]
    need(bool(parts), 'file path required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        result = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    finally:
        os.close(fd)
    if not stat.S_ISREG(os.fstat(result).st_mode):
        os.close(result)
        raise ValueError('Port geometry: regular file required')
    return os.fdopen(result, 'rb')


def lines(path, pin):
    with open_regular(path) as f:
        before = os.fstat(f.fileno())
        need(before.st_size == pin['bytes'], 'source digest/size mismatch')
        h = hashlib.sha256(); size = 0
        while True:
            raw = f.readline(MAX_LINE + 1)
            if not raw:
                break
            need(len(raw) <= MAX_LINE, 'line bound exceeded')
            size += len(raw)
            need(size <= pin['bytes'], 'source grew beyond pinned size')
            h.update(raw)
            yield raw.decode('ascii').strip()
        after = os.fstat(f.fileno())
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'source changed while reading')
        need(size == pin['bytes'] and h.hexdigest() == pin['sha256'], 'source digest/size mismatch')


def tail(it):
    result = []; size = 0
    for s in it:
        size += len(s) + 1
        need(size <= MAX_TAIL, 'text bound exceeded')
        result.append(s)
    return '\n'.join(result)


def count(s):
    need(s.isdigit() and len(s) <= 7, 'invalid list count')
    n = int(s)
    need(0 < n <= MAX_COUNT, 'list count bound exceeded')
    return n


def finite(s):
    n = float(s)
    need(math.isfinite(n), 'nonfinite scalar')
    return n


def face(s):
    m = re.fullmatch(r'(\d+)\(([^()]*)\)', s)
    need(m is not None, 'invalid face')
    v = [int(x) for x in m[2].split()]
    need(len(v) == int(m[1]) == 3 and min(v) >= 0, 'selected face must be triangle')
    return v


def point(s):
    need(s.startswith('(') and s.endswith(')'), 'invalid point')
    v = tuple(finite(x) for x in s[1:-1].split())
    need(len(v) == 3, 'invalid point dimension')
    return v


def read_list(it, keep, decode):
    for s in it:
        if s.isdigit():
            n = count(s); break
    else:
        raise ValueError('Port geometry: missing list')
    need(next(it) == '(', 'missing list opener')
    result = {}
    for i in range(n):
        s = next(it)
        if i in keep:
            result[i] = decode(s)
    need(next(it).startswith(')'), 'missing list closer')
    tail(it)  # Exhaust the same descriptor and verify its hash before returning.
    need(len(result) == len(keep), 'selected index outside list')
    return n, result


def field(it, keep, dimensions):
    header = []; size = 0
    for s in it:
        size += len(s)
        need(size <= MAX_LINE, 'header bound exceeded')
        header.append(s)
        if s.startswith('internalField'):
            need(s == 'internalField   nonuniform List<scalar>', 'unexpected internal scalar field')
            break
    need(dimensions in '\n'.join(header), 'field dimensions mismatch')
    n = count(next(it)); need(next(it) == '(', 'missing field opener')
    values = {}
    for i in range(n):
        s = next(it)
        if i in keep:
            values[i] = finite(s)
    need(next(it).startswith(')'), 'missing field closer')
    rest = tail(it)
    need(len(values) == len(keep), 'owner index outside pressure field')
    return n, values, rest


sub = lambda a, b: tuple(x-y for x, y in zip(a, b))
cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
norm = lambda a: math.sqrt(sum(x*x for x in a))


def summarize_port(p, faces, points, owners, pressures, flux, inlet):
    vectors = []; areas = []; centres = []; ps = []; edges = collections.Counter(); ids = set()
    for idx in range(p['startFace'], p['startFace'] + p['nFaces']):
        f = faces[idx]; a, b, c = [points[v] for v in f]
        av = tuple(v*.5 for v in cross(sub(b, a), sub(c, a))); area = norm(av)
        need(area > 0, 'degenerate triangle')
        vectors.append(av); areas.append(area)
        centres.append(tuple((a[k]+b[k]+c[k])/3 for k in range(3)))
        ps.append(pressures[owners[idx]] if inlet else 0.0)
        ids.update(f)
        for a, b in zip(f, f[1:]+f[:1]):
            edges[tuple(sorted((a, b)))] += 1
    need(all(v in (1, 2) for v in edges.values()), 'invalid port edge incidence')
    rim = {v for edge, n in edges.items() if n == 1 for v in edge}
    need(bool(rim), 'port rim missing')
    total = sum(areas); sv = tuple(sum(v[k] for v in vectors) for k in range(3))
    normal = tuple(v/norm(sv) for v in sv)
    centre = tuple(sum(a*c[k] for a, c in zip(areas, centres))/total for k in range(3))
    radii = [norm(sub(points[v], centre)) for v in rim]
    return dict(p, area_sum_m2=total, projected_area_m2=norm(sv), area_vector_m2=sv,
                normal=normal, area_weighted_centre_m=centre,
                vertex_bounds_m=[[min(points[v][k] for v in ids), max(points[v][k] for v in ids)] for k in range(3)],
                plane_max_distance_m=max(abs(sum(x*y for x,y in zip(sub(points[v],centre),normal))) for v in ids),
                face_normal_max_deviation=max(norm(sub(tuple(x/a for x in av),normal)) for av,a in zip(vectors,areas)),
                rim_vertex_count=len(rim), rim_radius_range_m=[min(radii),max(radii)],
                equal_area_diameter_m=2*math.sqrt(total/math.pi),
                pkin_area_mean_m2_s2=sum(a*v for a,v in zip(areas,ps))/total,
                pkin_face_range_m2_s2=[min(ps),max(ps)], phi_sum_m3_s=sum(flux))


def reconstruct(paths, lock, adapter):
    read = lambda role: iter(lines(paths[role], lock['files'][role]))
    boundary = tail(read('boundary')); patches = []
    for name, body in re.findall(r'(\w+)\s*\{([^{}]*)\}', boundary):
        if 'nFaces' in body:
            patches.append(dict(name=name, startFace=int(re.search(r'startFace\s+(\d+)', body)[1]),
                                nFaces=int(re.search(r'nFaces\s+(\d+)', body)[1])))
    need(len(patches) == 132, 'patch count mismatch')
    ports = {n: dict(patches[i], patch_id=i) for n,i in [('inlet',78),('outlet',33)]}
    need(all(p['name'] == n and p['nFaces'] == 136 for n,p in ports.items()), 'port identity mismatch')
    selected = {i for p in ports.values() for i in range(p['startFace'],p['startFace']+p['nFaces'])}
    nf, faces = read_list(read('faces'), selected, face)
    np, points = read_list(read('points'), {v for f in faces.values() for v in f}, point)
    no, owners = read_list(read('owner'), selected, int)
    need(no == nf and min(owners.values()) >= 0, 'invalid owner mapping')
    nc, pressures, ptail = field(read('p'), set(owners.values()), '[0 2 -2 0 0 0 0]')
    need(re.search(r'\binlet\s*\{\s*type\s+zeroGradient;\s*\}', ptail), 'inlet pressure reconstruction unsupported')
    need(re.search(r'\boutlet\s*\{\s*type\s+fixedValue;\s*value\s+uniform\s+0;\s*\}', ptail), 'outlet pressure reconstruction unsupported')
    ni, _, phitail = field(read('phi'), set(), '[0 3 -1 0 0 0 0]')
    for name, p in ports.items():
        m = re.search(r'\b'+name+r'\s*\{[^{}]*value\s+nonuniform List<scalar>\s+(\d+)\s*\(([^()]*)\)', phitail)
        need(m is not None and count(m[1]) == p['nFaces'], 'port flux count mismatch')
        flux = [finite(x) for x in m[2].split()]
        need(len(flux) == p['nFaces'], 'flux list mismatch')
        ports[name] = summarize_port(p, faces, points, owners, pressures, flux, name == 'inlet')
    plan = adapter._json(tail(read('plan')).encode('ascii'), 'authenticated research plan')
    a,b = ports['inlet'],ports['outlet']; qi,qo = a['phi_sum_m3_s'],b['phi_sum_m3_s']
    dp = a['pkin_area_mean_m2_s2']-b['pkin_area_mean_m2_s2']
    need(qi < 0 < qo and dp > 0, 'unexpected signed flow/pressure branch')
    nominal = plan['nominal_circle_area_m2']; diameter = plan['nominal_diameter_m']
    need(math.isclose(nominal, math.pi*diameter**2/4, rel_tol=1e-15), 'nominal reference arithmetic mismatch')
    for name,p in ports.items():
        need(math.isclose(p['area_weighted_centre_m'][0],plan['domain'][name+'_x_m'],rel_tol=1e-15), 'plan end-plane mismatch')
    speed = abs(qi)/a['area_sum_m2']; k = 2*dp/speed**2; nominal_speed = abs(qi)/nominal
    return {'mesh_counts':dict(points=np,faces=nf,cells=nc,internal_faces=ni,patches=len(patches)),
            'ports':ports, 'dpkin_m2_s2':dp, 'speed_reference_m_s':speed, 'K_mesh_area':k,
            'flux_reference':'abs(saved Qin), not Qout; older observation-contract Qout convention is not substituted',
            'relative_signed_flux_imbalance':abs(qi+qo)/max(abs(qi),abs(qo)),
            'pressure_reconstruction':'inlet zeroGradient owner-cell internal p; outlet fixedValue uniform 0; static area mean, not independent wall taps',
            'end_plane_separation_m':norm(sub(a['area_weighted_centre_m'],b['area_weighted_centre_m'])),
            'nominal_research_reference':{'status':'CLOSED_RESEARCH_INPUT', 'nominal_diameter_m':diameter,
                 'area_m2':nominal,'speed_m_s':nominal_speed,'K_same_saved_Qin_and_dp':2*dp/nominal_speed**2,
                 'K_increase_percent_reference_only':100*((nominal/a['area_sum_m2'])**2-1),
                 'formula':'K_nominal = K_mesh*(A_nominal/A_mesh)^2; same saved Qin and dpkin',
                 'plan_status':plan['status'],'pose':plan['pose'],'domain':plan['domain'],
                 'scope':'restrained 57 mm research pose and 3DN extensions each; not isolated-valve/product capacity'},
            'CAD_identity_authenticated':False,'engineering_release':False}


def bind(declaration, observation, adapter):
    try:
        need(type(declaration) is dict and set(declaration) == {'profile','paths'}, 'requires exactly profile and paths')
        need(declaration['profile'] == PROFILE, 'unknown profile')
        paths = declaration['paths']
        need(type(paths) is dict and set(paths) == ROLES, 'requires exact seven geometry roles')
        raw = adapter._read(Path(__file__).with_name('state21-ports.lock.json'))
        need(adapter._digest(raw) == LOCK_SHA256, 'immutable port input lock mismatch')
        lock = adapter._json(raw, 'port input lock')
        need(sum(x['bytes'] for x in lock['files'].values()) < 120000000, 'aggregate byte limit exceeded')
        missing = []
        for role in sorted(ROLES):
            try:
                with open_regular(paths[role]) as f:
                    need(os.fstat(f.fileno()).st_size == lock['files'][role]['bytes'], 'source digest/size mismatch: '+role)
            except FileNotFoundError:
                missing.append('MISSING_SOURCE:'+role)
        result = {'profile':PROFILE,'status':'HOLD','source_binding_status':'HOLD',
                  'reconstruction_status':'HOLD','observer_crosscheck_status':'HOLD','missing_reasons':missing,
                  'measurement':None,'sources':[], 'integrity_scope':'selected boundary/points/faces/owner and saved21 p/phi plus frozen plan only; not full case, mesh quality, CAD/BOM, R1 or product authentication'}
        if missing:
            return result
        measurement = reconstruct(paths, lock, adapter)
        result.update(source_binding_status='PASS', reconstruction_status='PASS',measurement=measurement,
                      sources=[dict(role=r,path=paths[r],**lock['files'][r]) for r in sorted(ROLES)],
                      plan_provenance=lock['plan_provenance'])
        if observation is not None:
            a,b=measurement['ports']['inlet'],measurement['ports']['outlet']
            actual=[a['area_sum_m2'],b['area_sum_m2'],a['phi_sum_m3_s'],b['phi_sum_m3_s'],
                    a['pkin_area_mean_m2_s2'],b['pkin_area_mean_m2_s2'],measurement['dpkin_m2_s2'],measurement['K_mesh_area']]
            keys=('Ain_m2','Aout_m2','Qin_m3_s','Qout_m3_s','pinMean_m2_s2','poutMean_m2_s2','DeltaPkin_m2_s2','K')
            comparisons=[]
            for key,value in zip(keys,actual):
                expected=observation['inputs'][key]['value']
                need(math.isclose(value,expected,rel_tol=1e-12,abs_tol=1e-30), 'observer reconstruction mismatch: '+key)
                comparisons.append(dict(variable=key,reconstructed=value,observed=expected))
            result.update(observer_crosscheck_status='PASS',comparison=comparisons)
        else:
            result['missing_reasons'].append('AUTHENTICATED_OBSERVER_UNAVAILABLE')
        return result
    except (OSError, ValueError, KeyError, IndexError, TypeError, StopIteration, UnicodeError, OverflowError, ZeroDivisionError) as exc:
        raise adapter.AdapterError('Invalid port geometry binding: '+str(exc)) from exc
